from datetime import datetime, timezone, timedelta
import random
from database import SessionLocal
import models


def backfill_sales_data():
    """
    Standalone script to populate sample transactions across the past 6 days
    for existing products in ShopSense DB, enabling rich 7-day sales trend visual analytics.
    Does NOT modify existing products, vendors, or seeded customer balances.
    """
    db = SessionLocal()
    try:
        print("==========================================================================")
        print("📈 SHOP SENSE SALES TREND HISTORICAL BACKFILL")
        print("==========================================================================\n")

        # 1. Query existing products
        products = db.query(models.Product).all()
        if not products:
            print("❌ No existing products found in database! Please seed or add products first.")
            return

        # 2. Use dedicated historical customers to preserve seeded customer tier boundaries
        hist_customers_data = [
            {"name": "Ananya Rao", "email": "ananya.rao@example.com"},
            {"name": "Dev Sharma", "email": "dev.sharma@example.com"},
            {"name": "Karan Verma", "email": "karan.verma@example.com"},
            {"name": "Neha Kapoor", "email": "neha.kapoor@example.com"}
        ]

        hist_customers = []
        for c_info in hist_customers_data:
            c = db.query(models.Customer).filter(models.Customer.email == c_info["email"]).first()
            if not c:
                c = models.Customer(name=c_info["name"], email=c_info["email"])
                db.add(c)
                db.commit()
                db.refresh(c)
            hist_customers.append(c)

        now_utc = datetime.now(timezone.utc)
        total_backfilled_count = 0
        total_backfilled_revenue = 0.0

        daily_summaries = []

        # 3. Iterate over the past 6 days (from 6 days ago up to yesterday)
        for days_ago in range(6, 0, -1):
            target_date = now_utc - timedelta(days=days_ago)
            date_str = target_date.strftime("%Y-%m-%d")
            day_name = target_date.strftime("%a")

            # Determine number of transactions for this day (1 to 3)
            random.seed(days_ago * 42)
            num_tx = random.randint(1, 3)

            day_tx_count = 0
            day_revenue = 0.0

            for i in range(num_tx):
                prod = random.choice(products)
                cust = random.choice(hist_customers)
                qty = random.choice([1, 1, 2])
                amount = round(prod.price * qty, 2)

                # Stagger timestamp during business hours
                staggered_time = target_date.replace(
                    hour=9 + (i * 4) % 12,
                    minute=random.randint(10, 50),
                    second=random.randint(10, 50)
                )

                tx = models.Transaction(
                    customer_id=cust.id,
                    product_id=prod.id,
                    quantity=qty,
                    total_amount=amount,
                    created_at=staggered_time
                )
                db.add(tx)

                # Add activity log entry
                vendor_name = prod.vendor.name if prod.vendor else "Vendor"
                log = models.ActivityLog(
                    event_type="sale_simulated",
                    description=f"Historical sale recorded: {vendor_name} sold {qty}x '{prod.name}' for ₹{amount:,.2f}.",
                    timestamp=staggered_time
                )
                db.add(log)

                day_tx_count += 1
                day_revenue += amount
                total_backfilled_count += 1
                total_backfilled_revenue += amount

            daily_summaries.append((date_str, day_name, day_tx_count, day_revenue))

        db.commit()

        # 4. Print Summary Table
        print("Date       | Day | Orders | Revenue Generated (₹ INR)")
        print("-" * 55)
        for date_str, day_name, count, rev in daily_summaries:
            print(f"{date_str} | {day_name} | {count} order(s) | ₹{rev:,.2f}")

        print("-" * 55)
        print(f"✅ SUCCESS: Backfilled {total_backfilled_count} transactions (Total: ₹{total_backfilled_revenue:,.2f}) across past 6 days!")
        print("==========================================================================")

    except Exception as e:
        db.rollback()
        print(f"❌ Error during backfill: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    backfill_sales_data()
