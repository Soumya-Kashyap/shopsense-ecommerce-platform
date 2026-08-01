from fastapi.testclient import TestClient
from main import app
from database import SessionLocal, engine, Base
import models
from auth import hash_password

client = TestClient(app)


def test_auth_and_status_management():
    print("🧪 Running ShopSense Auth & Status Management Test Suite...\n")

    # 1. Admin Login Test (POST /login)
    admin_login_res = client.post("/login", json={
        "email": "admin@shopsense.com",
        "password": "admin"
    })
    assert admin_login_res.status_code == 200, f"Admin login failed: {admin_login_res.text}"
    admin_data = admin_login_res.json()
    assert admin_data["role"] == "admin"
    assert admin_data["status"] == "active"
    assert "access_token" in admin_data
    print("  ✓ Admin Login (admin@shopsense.com / admin) passed! Token generated.")

    # 2. Invalid Credentials Test
    bad_login_res = client.post("/login", json={
        "email": "admin@shopsense.com",
        "password": "wrongpassword"
    })
    assert bad_login_res.status_code == 401
    assert bad_login_res.json()["detail"] == "Invalid credentials"
    print("  ✓ Invalid Credentials validation (401 Unauthorized) passed!")

    # 3. New Vendor Registration Test (POST /vendors/register)
    reg_payload = {
        "name": "Apex Electronics",
        "email": "contact@apexelectronics.com",
        "password": "securepassword123",
        "phone": "+1-800-APEX-01"
    }
    reg_res = client.post("/vendors/register", json=reg_payload)
    assert reg_res.status_code == 201, f"Registration failed: {reg_res.text}"
    vendor_reg_data = reg_res.json()
    vendor_id = vendor_reg_data["id"]
    assert vendor_reg_data["status"] == "pending"
    assert vendor_reg_data["role"] == "vendor"
    assert "password_hash" not in vendor_reg_data  # Should not expose password hash
    print(f"  ✓ Vendor Registration passed! Vendor ID #{vendor_id} created with default status='pending'.")

    # 4. Pending Vendor Login Test
    pending_login_res = client.post("/login", json={
        "email": "contact@apexelectronics.com",
        "password": "securepassword123"
    })
    assert pending_login_res.status_code == 200
    assert pending_login_res.json()["status"] == "pending"
    print("  ✓ Pending Vendor Login passed!")

    # 5. Admin Changes Vendor Status to 'suspended' (PUT /vendors/{id}/status)
    status_suspend_res = client.put(f"/vendors/{vendor_id}/status", json={"status": "suspended"})
    assert status_suspend_res.status_code == 200
    assert status_suspend_res.json()["status"] == "suspended"
    print(f"  ✓ Admin updated Vendor #{vendor_id} status to 'suspended'.")

    # 6. Suspended Vendor Login Attempt (Must be rejected with 403)
    suspended_login_res = client.post("/login", json={
        "email": "contact@apexelectronics.com",
        "password": "securepassword123"
    })
    assert suspended_login_res.status_code == 403
    assert "suspended" in suspended_login_res.json()["detail"].lower()
    print("  ✓ Suspended Vendor Login rejection (403 Forbidden) passed!")

    # 7. Admin Reactivates Vendor to 'active'
    status_active_res = client.put(f"/vendors/{vendor_id}/status", json={"status": "active"})
    assert status_active_res.status_code == 200
    assert status_active_res.json()["status"] == "active"
    print(f"  ✓ Admin updated Vendor #{vendor_id} status to 'active'.")

    # 8. Reactivated Vendor Login Attempt (Must succeed)
    active_login_res = client.post("/login", json={
        "email": "contact@apexelectronics.com",
        "password": "securepassword123"
    })
    assert active_login_res.status_code == 200
    assert active_login_res.json()["status"] == "active"
    print("  ✓ Reactivated Vendor Login passed!")

    # 9. List All Vendors (GET /vendors/)
    list_vendors_res = client.get("/vendors/")
    assert list_vendors_res.status_code == 200
    vendors_list = list_vendors_res.json()
    assert len(vendors_list) >= 3
    print(f"  ✓ List All Vendors (GET /vendors/) returned {len(vendors_list)} total accounts.")

    print("\n🎉 ALL AUTHENTICATION AND STATUS MANAGEMENT TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    test_auth_and_status_management()
