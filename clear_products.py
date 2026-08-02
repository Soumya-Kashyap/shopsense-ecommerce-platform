from datetime import datetime, timezone
from database import SessionLocal, engine
import models


def clear_products_and_transactions():
    """
    Safely wipes all Product listings and Transaction records from the ShopSense database.
    Keeps all Vendor profiles, Customer accounts, and Admin user accounts completely intact.
    Logs an ActivityLog event recording the maintenance operation.
    """
    db = SessionLocal()
    try:
        print("🧹 Clearing all Products and Transactions from ShopSense database...")

        # 1. Delete all transactions first (child rows)
        num_transactions_deleted = db.query(models.Transaction).delete()

        # 2. Delete all products (parent rows)
        num_products_deleted = db.query(models.Product).delete()

        # 3. Log Activity Event
        log_entry = models.ActivityLog(
            event_type="database_cleaned",
            description=f"Admin maintenance: Cleared {num_products_deleted} products and {num_transactions_deleted} transactions. Ready for fresh products.",
            timestamp=datetime.now(timezone.utc)
        )
        db.add(log_entry)

        db.commit()
        print(f"✅ Successfully wiped {num_products_deleted} products and {num_transactions_deleted} transactions!")
        print("🔒 All Vendors, Customers, and Admin accounts remain intact.\n")

    except Exception as e:
        db.rollback()
        print(f"❌ Error clearing products: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    clear_products_and_transactions()
