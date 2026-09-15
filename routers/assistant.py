import os
import re

from dotenv import load_dotenv
from fastapi import APIRouter, Depends
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db

load_dotenv()

router = APIRouter(
    prefix="/assistant",
    tags=["AI Shopping Assistant (RAG)"]
)


def extract_search_signals(question: str):
    """
    Parses user natural language question to extract price constraints and keyword search signals.
    """
    q_lower = question.lower()

    max_price: float | None = None
    price_match = re.search(r'(?:under|below|less than|budget|within|<|<=|₹)\s*(\d[\d,.]*)', q_lower)
    if price_match:
        try:
            val_str = price_match.group(1).replace(',', '')
            max_price = float(val_str)
        except ValueError:
            max_price = None

    keywords = []
    category_signal: str | None = None

    if any(w in q_lower for w in ["earbud", "earbuds", "headphone", "headphones", "sound", "speaker", "speakers", "audio"]):
        category_signal = "Audio"
        keywords.extend(["earbuds", "speaker", "audio", "sound", "headphone"])
    elif any(w in q_lower for w in ["watch", "smartwatch", "wearable", "wearables", "band"]):
        category_signal = "Wearables"
        keywords.extend(["watch", "smartwatch", "wearable"])
    elif any(w in q_lower for w in ["phone", "smartphone", "mobile", "electronics", "gadget"]):
        category_signal = "Electronics"
        keywords.extend(["phone", "galaxy", "electronics", "ultra"])
    elif any(w in q_lower for w in ["apparel", "shirt", "wear", "fashion", "clothing"]):
        category_signal = "Fashion"
        keywords.extend(["fashion", "shirt", "apparel"])

    return max_price, category_signal, keywords


def retrieve_matching_products(db: Session, max_price: float | None, category_signal: str | None, keywords: list[str], limit: int = 4):
    """
    Retrieves real products from shopsense.db based on category/price filters, ordered by units sold.
    """
    query = (
        db.query(
            models.Product.id.label("product_id"),
            models.Product.name.label("product_name"),
            models.Product.vendor_id.label("vendor_id"),
            models.Vendor.name.label("vendor_name"),
            models.Product.category.label("category"),
            models.Product.price.label("price"),
            models.Product.stock_qty.label("stock_qty"),
            models.Product.description.label("description"),
            func.coalesce(func.sum(models.Transaction.quantity), 0).label("units_sold"),
            func.coalesce(func.sum(models.Transaction.total_amount), 0.0).label("total_revenue")
        )
        .join(models.Vendor, models.Product.vendor_id == models.Vendor.id)
        .outerjoin(models.Transaction, models.Product.id == models.Transaction.product_id)
    )

    if max_price is not None and max_price > 0:
        query = query.filter(models.Product.price <= max_price)

    if keywords:
        or_conditions = []
        for kw in keywords:
            or_conditions.append(models.Product.name.ilike(f"%{kw}%"))
            or_conditions.append(models.Product.category.ilike(f"%{kw}%"))
            or_conditions.append(models.Product.tags.ilike(f"%{kw}%"))
        query = query.filter(or_(*or_conditions))

    results = (
        query.group_by(
            models.Product.id,
            models.Product.name,
            models.Product.vendor_id,
            models.Vendor.name,
            models.Product.category,
            models.Product.price,
            models.Product.stock_qty,
            models.Product.description
        )
        .order_by(desc("units_sold"), models.Product.price.asc())
        .limit(limit)
        .all()
    )

    return results


def get_top_selling_fallback_products(db: Session, limit: int = 3):
    return retrieve_matching_products(db, max_price=None, category_signal=None, keywords=[], limit=limit)


@router.post(
    "/ask",
    response_model=schemas.AssistantAnswerResponse,
    summary="Ask AI Shopping Assistant (RAG)",
    description="Retrieval-Augmented Generation (RAG) shopping assistant endpoint. Extracts search signals from natural language queries, retrieves matching database products, and prompts Groq LLM (llama-3.1-8b-instant) to generate grounded recommendations.",
    response_description="Assistant response text payload with list of retrieved real product cards"
)
def ask_ai_shopping_assistant(payload: schemas.AssistantQuestionRequest, db: Session = Depends(get_db)):
    question_text = payload.question.strip()
    max_price, category_signal, keywords = extract_search_signals(question_text)

    matched_raw = retrieve_matching_products(db, max_price, category_signal, keywords)
    fallback_used = False

    if not matched_raw:
        matched_raw = get_top_selling_fallback_products(db, limit=3)
        fallback_used = True

    matched_products_formatted = []
    for item in matched_raw:
        matched_products_formatted.append({
            "product_id": item.product_id,
            "product_name": item.product_name,
            "vendor_id": item.vendor_id,
            "vendor_name": item.vendor_name,
            "category": item.category or "Electronics",
            "price": float(item.price),
            "units_sold": int(item.units_sold),
            "total_revenue": round(float(item.total_revenue), 2)
        })

    groq_api_key = os.getenv("GROQ_API_KEY")

    if fallback_used:
        llm_answer = (
            f"I couldn't find products matching your exact request for '{question_text}', "
            f"but here are the top-selling items currently trending on ShopSense!"
        )
        return {
            "answer": llm_answer,
            "matched_products": matched_products_formatted,
            "fallback_used": True
        }

    context_items = []
    for idx, p in enumerate(matched_raw, start=1):
        context_items.append(
            f"Product #{idx}: {p.product_name}\n"
            f"- Vendor: {p.vendor_name}\n"
            f"- Category: {p.category or 'Electronics'}\n"
            f"- Price: ₹{float(p.price):,.2f}\n"
            f"- Stock: {p.stock_qty} units available\n"
            f"- Popularity: {p.units_sold} units sold\n"
            f"- Description: {p.description or 'High performance product'}\n"
        )
    context_str = "\n".join(context_items)

    system_prompt = (
        "You are ShopSense AI, an expert and enthusiastic e-commerce shopping assistant.\n"
        "Rules:\n"
        "1. Recommend ONLY from the provided real products context below.\n"
        "2. Do NOT invent, hallucinate, or reference products outside of this list.\n"
        "3. Highlight key features, value for money, and mention exact prices in ₹ INR.\n"
        "4. Keep your answer helpful, concise (2-4 paragraphs), and friendly."
    )

    user_prompt = (
        f"Customer Question: \"{question_text}\"\n\n"
        f"Retrieved Real Products Context:\n{context_str}\n\n"
        f"Please provide your recommendation based strictly on the above products."
    )

    llm_answer = ""
    if groq_api_key:
        try:
            import groq
            client = groq.Groq(api_key=groq_api_key)
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=400
            )
            if completion.choices and completion.choices[0].message.content:
                llm_answer = completion.choices[0].message.content.strip()
        except Exception as err:
            print(f"Groq API call warning: {err}")
            llm_answer = ""

    if not llm_answer:
        p_names = [f"'{p['product_name']}' (₹{p['price']:,.2f})" for p in matched_products_formatted]
        llm_answer = (
            "Here are the top-rated recommendations matching your request on ShopSense: "
            + ", ".join(p_names) + ". Check out the product cards below for details!"
        )

    return {
        "answer": llm_answer,
        "matched_products": matched_products_formatted,
        "fallback_used": fallback_used
    }
