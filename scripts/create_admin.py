#!/usr/bin/env python3
"""
Script to create an admin user for testing.

Usage:
    python scripts/create_admin.py
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.session import async_session_maker
from app.models.user import User, UserRole


async def create_admin_user():
    """Create a default admin user for testing."""
    
    admin_email = "admin@marketpulse.com"
    admin_username = "admin"
    admin_password = "Admin@1234"  # Change this for production!
    
    async with async_session_maker() as db:
        # Check if admin already exists
        result = await db.execute(
            select(User).where(User.email == admin_email)
        )
        existing_admin = result.scalar_one_or_none()
        
        if existing_admin:
            print(f"✅ Admin user already exists: {admin_email}")
            print(f"   Role: {existing_admin.role}")
            return
        
        # Create new admin user
        admin_user = User(
            email=admin_email,
            username=admin_username,
            hashed_password=hash_password(admin_password),
            role=UserRole.ADMIN,
            is_active=True
        )
        
        db.add(admin_user)
        await db.commit()
        await db.refresh(admin_user)
        
        print("🎉 Admin user created successfully!")
        print(f"   Email: {admin_email}")
        print(f"   Username: {admin_username}")
        print(f"   Password: {admin_password}")
        print(f"   Role: {admin_user.role}")
        print(f"\n⚠️  IMPORTANT: Change the password in production!")
        print(f"\n📝 Test admin endpoints at: http://localhost:8000/docs")
        print(f"   1. Login with admin credentials")
        print(f"   2. Copy the access_token from response")
        print(f"   3. Click 'Authorize' button in Swagger")
        print(f"   4. Enter: Bearer <your_access_token>")
        print(f"   5. Test /api/v1/admin/* endpoints")


if __name__ == "__main__":
    asyncio.run(create_admin_user())
