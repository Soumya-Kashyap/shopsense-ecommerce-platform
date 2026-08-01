from datetime import datetime, timezone, timedelta
from database import SessionLocal, engine, Base
import models
from auth import hash_password


def seed_database():
    """
    Reseeds the ShopSense database with Administrator, 5 Vendors, initial Products (in ₹ INR),
    Transactions, and Activity Log events with staggered UTC timestamps.
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("🌱 Reseeding ShopSense database with INR currency & precise activity timestamps...")

        # 1. System Administrator
        admin = models.Vendor(
            name="ShopSense Administrator",
            email="admin@shopsense.com",
            password_hash=hash_password("admin"),
            role="admin",
            status="active",
            phone="+1-800-ADMIN-01"
        )
        db.add(admin)
        db.commit()

        # 2. 5 Vendors
        vendors_data = [
            {"name": "Samsung", "email": "contact@samsung.com", "password": "vendor123", "status": "active", "phone": "+91-800-SAMSUNG"},
            {"name": "Sony", "email": "contact@sony.com", "password": "vendor123", "status": "active", "phone": "+91-800-222-7669"},
            {"name": "JBL", "email": "contact@jbl.com", "password": "vendor123", "status": "active", "phone": "+91-800-336-4525"},
            {"name": "boAt", "email": "contact@boat.com", "password": "vendor123", "status": "pending", "phone": "+91-022-4946-1882"},
            {"name": "Noise", "email": "contact@noise.com", "password": "vendor123", "status": "pending", "phone": "+91-88003-15444"},
        ]

        vendor_instances = {}
        for v_info in vendors_data:
            v_model = models.Vendor(
                name=v_info["name"],
                email=v_info["email"],
                password_hash=hash_password(v_info["password"]),
                role="vendor",
                status=v_info["status"],
                phone=v_info["phone"]
            )
            db.add(v_model)
            db.commit()
            db.refresh(v_model)
            vendor_instances[v_info["name"]] = v_model

        # 3. Initial Electronics Products in Indian Rupees (₹ INR)
        products = [
            # Samsung
            models.Product(
                vendor_id=vendor_instances["Samsung"].id,
                name="Galaxy Buds Pro Wireless Earbuds",
                price=12999.00,
                stock_qty=45,
                description="Intelligent Active Noise Cancellation earbuds with immersive studio sound quality.",
                category="VISION: Audio & Acoustics",
                tags="#WirelessTech,#NoiseCancel,#PremiumQuality,#Samsung"
            ),
            models.Product(
                vendor_id=vendor_instances["Samsung"].id,
                name="55-inch QLED 4K Smart TV",
                price=74999.00,
                stock_qty=18,
                description="Quantum Processor 4K with 100% Color Volume and Motion Xcelerator Turbo+.",
                category="VISION: Electronics",
                tags="#UltraHD,#SmartTV,#QLED,#Samsung"
            ),
            # Sony
            models.Product(
                vendor_id=vendor_instances["Sony"].id,
                name="WH-1000XM5 Wireless Headphones",
                price=29999.00,
                stock_qty=25,
                description="Industry-leading noise canceling with two processors and 8 microphones.",
                category="VISION: Audio & Acoustics",
                tags="#NoiseCancel,#SonyAudio,#WirelessTech,#HighResAudio"
            ),
            # JBL
            models.Product(
                vendor_id=vendor_instances["JBL"].id,
                name="Flip 6 Waterproof Speaker",
                price=9999.00,
                stock_qty=5,  # Low stock test (< 10)
                description="Bold sound for every adventure with 2-way speaker system and IP67 rating.",
                category="VISION: Audio & Acoustics",
                tags="#JBLSound,#Waterproof,#BluetoothSpeaker"
            ),
        ]
        db.add_all(products)
        db.commit()
        for p in products:
            db.refresh(p)

        # 4. Customers & Transactions
        c1 = models.Customer(name="Rahul Sharma", email="rahul.sharma@example.com")
        c2 = models.Customer(name="Priya Patel", email="priya.patel@example.com")
        db.add_all([c1, c2])
        db.commit()
        db.refresh(c1)
        db.refresh(c2)

        transactions = [
            models.Transaction(customer_id=c1.id, product_id=products[0].id, quantity=2, total_amount=round(2 * products[0].price, 2)),
            models.Transaction(customer_id=c2.id, product_id=products[1].id, quantity=1, total_amount=round(1 * products[1].price, 2)),
            models.Transaction(customer_id=c1.id, product_id=products[2].id, quantity=1, total_amount=round(1 * products[2].price, 2)),
            models.Transaction(customer_id=c2.id, product_id=products[3].id, quantity=2, total_amount=round(2 * products[3].price, 2)),
        ]
        db.add_all(transactions)
        db.commit()

        # 5. Staggered UTC Time-stamped Activity Logs (with distinct seconds)
        base_time = datetime.now(timezone.utc) - timedelta(minutes=15)
        activity_logs = [
            models.ActivityLog(event_type="vendor_registered", description="System initialized with Samsung, Sony, JBL, boAt, and Noise.", timestamp=base_time),
            models.ActivityLog(event_type="status_changed", description="Vendor 'boAt' status set to PENDING.", timestamp=base_time + timedelta(seconds=12)),
            models.ActivityLog(event_type="status_changed", description="Vendor 'Noise' status set to PENDING.", timestamp=base_time + timedelta(seconds=28)),
            models.ActivityLog(event_type="product_added", description="Sony added 'WH-1000XM5 Wireless Headphones' (₹29,999.00).", timestamp=base_time + timedelta(minutes=5, seconds=14)),
            models.ActivityLog(event_type="product_added", description="Samsung added '55-inch QLED 4K Smart TV' (₹74,999.00).", timestamp=base_time + timedelta(minutes=10, seconds=45)),
        ]
        db.add_all(activity_logs)
        db.commit()

        print("\n✅ Reseed complete! Platform revenue and distinct HH:MM:SS activity logs initialized.")

    except Exception as e:
        db.rollback()
        print(f"❌ Error reseeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
