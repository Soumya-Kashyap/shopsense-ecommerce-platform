from datetime import datetime, timezone
import re
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas

router = APIRouter(
    tags=["Reviews & Sentiment"]
)

# Sentiment Dictionaries
POSITIVE_KEYWORDS = {
    "great", "excellent", "love", "loved", "amazing", "outstanding", "best", "perfect",
    "good", "superb", "fast", "easy", "durable", "stunning", "impressed", "worth",
    "awesome", "nice", "flawless", "clear", "crisp", "smooth", "high-quality", "fantastic",
    "brilliant", "solid", "comfortable", "sleek", "vibrant", "happy", "recommend"
}

NEGATIVE_KEYWORDS = {
    "bad", "terrible", "broken", "disappointed", "disappointing", "poor", "worst",
    "defective", "slow", "hate", "fail", "failed", "horrible", "overpriced", "cheap",
    "noisy", "scratch", "issue", "issues", "return", "returned", "regret", "faulty",
    "clunky", "fragile", "heavy", "drain", "uncomfortable", "junk"
}


def analyze_review_sentiment(review_text: str):
    """
    Rule-based Sentiment Analysis & AI Feature Extraction:
    - Calculates sentiment score between -1.0 and +1.0 based on keyword frequency.
    - Classifies sentiment as Positive, Neutral, or Negative.
    - Extracts 1-2 positive key phrases/features as Pros and negative ones as Cons.
    """
    text_lower = review_text.lower()
    words = re.findall(r'\b[a-z0-9\-]+\b', text_lower)

    pos_count = sum(1 for w in words if w in POSITIVE_KEYWORDS)
    neg_count = sum(1 for w in words if w in NEGATIVE_KEYWORDS)

    total_matched = pos_count + neg_count
    if total_matched == 0:
        score = 0.0
    else:
        score = round((pos_count - neg_count) / max(total_matched, 1), 2)
        score = max(-1.0, min(1.0, score))

    if score > 0.15:
        label = "Positive"
    elif score < -0.15:
        label = "Negative"
    else:
        label = "Neutral"

    # Extract pros/cons based on matched keywords and simple clause parsing
    clauses = re.split(r'[,.!\n;]+', review_text)
    pros_list = []
    cons_list = []

    for clause in clauses:
        clause_str = clause.strip()
        if not clause_str:
            continue
        c_lower = clause_str.lower()
        c_words = set(re.findall(r'\b[a-z0-9\-]+\b', c_lower))

        if c_words.intersection(POSITIVE_KEYWORDS) and len(pros_list) < 2:
            pros_list.append(clause_str[:60])
        elif c_words.intersection(NEGATIVE_KEYWORDS) and len(cons_list) < 2:
            cons_list.append(clause_str[:60])

    if not pros_list and pos_count > 0:
        matched_pos = [w for w in words if w in POSITIVE_KEYWORDS][:2]
        pros_list = [f"Good {w}" for w in matched_pos]
    if not cons_list and neg_count > 0:
        matched_neg = [w for w in words if w in NEGATIVE_KEYWORDS][:2]
        cons_list = [f"Issue with {w}" for w in matched_neg]

    pros_str = "; ".join(pros_list) if pros_list else "Great overall experience"
    cons_str = "; ".join(cons_list) if cons_list else "None reported"

    return score, label, pros_str, cons_str


@router.post("/products/{product_id}/reviews", response_model=schemas.ReviewResponse, status_code=status.HTTP_201_CREATED)
def create_product_review(product_id: int, review: schemas.ReviewCreate, db: Session = Depends(get_db)):
    """
    POST /products/{product_id}/reviews:
    Creates a new customer review, analyzes sentiment text, extracts pros/cons,
    and logs an activity log event.
    """
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found."
        )

    score, label, pros, cons = analyze_review_sentiment(review.review_text)

    db_review = models.Review(
        product_id=product_id,
        customer_name=review.customer_name.strip(),
        review_text=review.review_text.strip(),
        rating=review.rating,
        sentiment_score=score,
        sentiment_label=label,
        pros=pros,
        cons=cons,
        created_at=datetime.now(timezone.utc)
    )
    db.add(db_review)

    # Activity Log
    vendor_name = product.vendor.name if product.vendor else "Vendor"
    log_entry = models.ActivityLog(
        event_type="review_added",
        description=f"Review posted for '{product.name}' by {review.customer_name} (Rating: {review.rating}★, Sentiment: {label}).",
        timestamp=datetime.now(timezone.utc)
    )
    db.add(log_entry)

    db.commit()
    db.refresh(db_review)
    return db_review


@router.get("/products/{product_id}/reviews", response_model=schemas.ProductReviewsResponse)
def get_product_reviews(product_id: int, db: Session = Depends(get_db)):
    """
    GET /products/{product_id}/reviews:
    Returns all customer reviews for a product plus aggregate sentiment metrics:
    - Average rating
    - % Positive, % Neutral, % Negative
    - Top Pros and Cons summary
    """
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found."
        )

    reviews = (
        db.query(models.Review)
        .filter(models.Review.product_id == product_id)
        .order_by(models.Review.created_at.desc())
        .all()
    )

    total_reviews = len(reviews)
    if total_reviews == 0:
        return {
            "product_id": product_id,
            "reviews": [],
            "aggregate": {
                "total_reviews": 0,
                "average_rating": 0.0,
                "positive_percentage": 0.0,
                "neutral_percentage": 0.0,
                "negative_percentage": 0.0,
                "top_pros": ["No reviews yet"],
                "top_cons": ["No reviews yet"]
            }
        }

    avg_rating = round(sum(r.rating for r in reviews) / total_reviews, 1)
    pos_count = sum(1 for r in reviews if r.sentiment_label == "Positive")
    neu_count = sum(1 for r in reviews if r.sentiment_label == "Neutral")
    neg_count = sum(1 for r in reviews if r.sentiment_label == "Negative")

    pos_pct = round((pos_count / total_reviews) * 100, 1)
    neu_pct = round((neu_count / total_reviews) * 100, 1)
    neg_pct = round((neg_count / total_reviews) * 100, 1)

    # Collect combined top pros/cons across reviews
    all_pros = [r.pros for r in reviews if r.pros and r.pros != "Great overall experience"]
    all_cons = [r.cons for r in reviews if r.cons and r.cons != "None reported"]

    top_pros = all_pros[:3] if all_pros else ["High satisfaction", "Good build quality"]
    top_cons = all_cons[:3] if all_cons else ["Minor preference variations"]

    return {
        "product_id": product_id,
        "reviews": reviews,
        "aggregate": {
            "total_reviews": total_reviews,
            "average_rating": avg_rating,
            "positive_percentage": pos_pct,
            "neutral_percentage": neu_pct,
            "negative_percentage": neg_pct,
            "top_pros": top_pros,
            "top_cons": top_cons
        }
    }
