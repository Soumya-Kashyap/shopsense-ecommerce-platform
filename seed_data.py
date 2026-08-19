from datetime import datetime, timezone, timedelta
from database import SessionLocal, engine, Base
import models
from auth import hash_password
from routers.reviews import analyze_review_sentiment


def seed_database():
    """
    Reseeds the ShopSense database with Administrator, 5 Vendors, initial Products (in ₹ INR),
    Customers spanning High/Medium/Low Value segments, Transactions, Reviews, and Activity Logs.
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("🌱 Reseeding ShopSense database with INR currency, Customer Segments, Reviews & Activity Logs...")

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

        # 4. Customers & Transactions (High Value, Medium Value, Low Value)
        c1 = models.Customer(name="Rahul Sharma", email="rahul.sharma@example.com")    # High Value (₹1,30,996)
        c2 = models.Customer(name="Priya Patel", email="priya.patel@example.com")      # Medium Value (₹49,997)
        c3 = models.Customer(name="Vikram Singh", email="vikram.singh@example.com")    # Low Value (₹9,999)
        db.add_all([c1, c2, c3])
        db.commit()
        for c in [c1, c2, c3]:
            db.refresh(c)

        transactions = [
            # Rahul Sharma (c1): QLED TV (₹74,999) + 2x Galaxy Buds (₹25,998) + XM5 Headphones (₹29,999) = ₹1,30,996 (High Value)
            models.Transaction(customer_id=c1.id, product_id=products[1].id, quantity=1, total_amount=74999.00),
            models.Transaction(customer_id=c1.id, product_id=products[0].id, quantity=2, total_amount=25998.00),
            models.Transaction(customer_id=c1.id, product_id=products[2].id, quantity=1, total_amount=29999.00),
            # Priya Patel (c2): XM5 Headphones (₹29,999) + 2x JBL Flip 6 (₹19,998) = ₹49,997 (Medium Value)
            models.Transaction(customer_id=c2.id, product_id=products[2].id, quantity=1, total_amount=29999.00),
            models.Transaction(customer_id=c2.id, product_id=products[3].id, quantity=2, total_amount=19998.00),
            # Vikram Singh (c3): 1x JBL Flip 6 (₹9,999) = ₹9,999 (Low Value)
            models.Transaction(customer_id=c3.id, product_id=products[3].id, quantity=1, total_amount=9999.00),
        ]
        db.add_all(transactions)
        db.commit()

        # 5. Customer Product Reviews with Sentiment Analysis
        seeded_reviews = [
            # Sony Headphones (products[2])
            {"product": products[2], "name": "Rahul Sharma", "rating": 5, "text": "Amazing noise cancellation and crystal clear audio quality! Best headphones I have ever bought."},
            {"product": products[2], "name": "Priya Patel", "rating": 4, "text": "Great battery life and very comfortable. A bit overpriced but overall excellent performance."},
            {"product": products[2], "name": "Aarav Gupta", "rating": 2, "text": "Disappointed with the carrying case. The hinge feels cheap and flimsy."},
            # JBL Speaker (products[3])
            {"product": products[3], "name": "Vikram Singh", "rating": 5, "text": "Love the bass! Superb waterproof design for pool parties."},
            {"product": products[3], "name": "Priya Patel", "rating": 3, "text": "Decent sound quality, but charging takes a bit longer than expected."},
            # Samsung TV (products[1])
            {"product": products[1], "name": "Rahul Sharma", "rating": 5, "text": "Stunning 4K display and smooth picture clarity! Perfect for movies and gaming."},
        ]

        review_objects = []
        for r_info in seeded_reviews:
            score, label, pros, cons = analyze_review_sentiment(r_info["text"])
            rev = models.Review(
                product_id=r_info["product"].id,
                customer_name=r_info["name"],
                review_text=r_info["text"],
                rating=r_info["rating"],
                sentiment_score=score,
                sentiment_label=label,
                pros=pros,
                cons=cons
            )
            review_objects.append(rev)

        db.add_all(review_objects)
        db.commit()

        # 6. UTC Time-stamped Activity Logs
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

        print("\n✅ Reseed complete! Platform revenue, Customer Segments, Reviews & Activity Logs initialized.")

    except Exception as e:
        db.rollback()
        print(f"❌ Error reseeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
