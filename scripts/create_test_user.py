#!/usr/bin/env python3
"""
Create Test User Script

Creates a user that can login to the frontend dashboard.
This creates both the Supabase auth.users record and organization_users record.

Usage:
    python scripts/create_test_user.py --tenant tn_6bc9d287_84ce19011671 --email admin@test.com --password Test123!

    # With custom name and role
    python scripts/create_test_user.py --tenant tn_6bc9d287_84ce19011671 --email admin@test.com --password Test123! --name "Admin User" --role admin
"""

import os
import sys
import asyncio
import argparse

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(project_root, ".env"))


async def create_user(tenant_id: str, email: str, password: str, name: str, role: str):
    """Create a user for the specified tenant."""
    from config.loader import get_config
    from src.services.auth_service import AuthService

    print(f"\n{'='*60}")
    print(f"Creating user for tenant: {tenant_id}")
    print(f"{'='*60}")

    # Verify tenant config exists
    try:
        config = get_config(tenant_id)
        print(f"[OK] Tenant config found: {config.company_name}")
    except FileNotFoundError:
        print(f"[ERROR] Tenant configuration not found: {tenant_id}")
        print(f"\nAvailable tenants:")
        from config.loader import list_clients
        for client in list_clients()[:10]:
            print(f"  - {client}")
        if len(list_clients()) > 10:
            print(f"  ... and {len(list_clients()) - 10} more")
        return False

    # Get Supabase credentials
    supabase_url = config.supabase_url or os.getenv("SUPABASE_URL")
    supabase_key = config.supabase_service_key or os.getenv("SUPABASE_SERVICE_KEY")

    if not supabase_url:
        print("[ERROR] SUPABASE_URL not configured")
        return False
    if not supabase_key:
        print("[ERROR] SUPABASE_SERVICE_KEY not configured")
        return False

    print(f"[OK] Supabase URL: {supabase_url[:40]}...")

    # Create auth service
    auth_service = AuthService(
        supabase_url=supabase_url,
        supabase_key=supabase_key
    )

    print(f"\nCreating user:")
    print(f"  Email: {email}")
    print(f"  Name: {name}")
    print(f"  Role: {role}")
    print(f"  Tenant: {tenant_id}")

    # Create the user
    success, result = await auth_service.create_auth_user(
        email=email,
        password=password,
        name=name,
        tenant_id=tenant_id,
        role=role
    )

    if success:
        user = result.get("user", {})
        already_existed = result.get("already_existed", False)

        if already_existed:
            print(f"\n[OK] User already exists and is linked to this tenant")
        else:
            print(f"\n[OK] User created successfully!")

        print(f"\nUser Details:")
        print(f"  ID: {user.get('id')}")
        print(f"  Email: {user.get('email')}")
        print(f"  Name: {user.get('name')}")
        print(f"  Role: {user.get('role')}")
        print(f"  Tenant: {user.get('tenant_id')}")

        print(f"\n{'='*60}")
        print("LOGIN CREDENTIALS")
        print(f"{'='*60}")
        print(f"  Email: {email}")
        print(f"  Password: {password}")
        print(f"\nFrontend URL: http://localhost:5173")
        print(f"{'='*60}")

        return True
    else:
        print(f"\n[ERROR] Failed to create user: {result.get('error')}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Create a test user for the frontend dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Create admin user for default tenant
    python scripts/create_test_user.py --tenant tn_6bc9d287_84ce19011671 --email admin@test.com --password Test123!

    # Create consultant user
    python scripts/create_test_user.py --tenant africastay --email consultant@test.com --password Test123! --role consultant
        """
    )

    parser.add_argument(
        "--tenant", "-t",
        required=True,
        help="Tenant ID (e.g., tn_6bc9d287_84ce19011671 or africastay)"
    )
    parser.add_argument(
        "--email", "-e",
        required=True,
        help="User email address"
    )
    parser.add_argument(
        "--password", "-p",
        required=True,
        help="User password (min 6 characters)"
    )
    parser.add_argument(
        "--name", "-n",
        default="Test Admin",
        help="User display name (default: Test Admin)"
    )
    parser.add_argument(
        "--role", "-r",
        choices=["admin", "user", "consultant"],
        default="admin",
        help="User role (default: admin)"
    )

    args = parser.parse_args()

    # Validate password
    if len(args.password) < 6:
        print("[ERROR] Password must be at least 6 characters")
        sys.exit(1)

    # Run async function
    success = asyncio.run(create_user(
        tenant_id=args.tenant,
        email=args.email,
        password=args.password,
        name=args.name,
        role=args.role
    ))

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
