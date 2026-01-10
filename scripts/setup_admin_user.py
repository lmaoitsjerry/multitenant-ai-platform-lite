"""
Setup Admin User Script

Creates the initial admin user for a tenant.
Run this after setting up the database tables.

Usage:
    python scripts/setup_admin_user.py --email admin@example.com --password SecurePass123! --name "Admin User" --tenant africastay
"""

import os
import sys
import argparse

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
from config.loader import get_config


def create_tables_if_not_exist(supabase_client):
    """Create the organization_users and user_invitations tables if they don't exist"""

    # Check if organization_users table exists by trying to select from it
    try:
        supabase_client.table("organization_users").select("id").limit(1).execute()
        print("[OK] organization_users table exists")
        return True
    except Exception as e:
        error_str = str(e).lower()
        if "does not exist" in error_str or "relation" in error_str or "pgrst205" in error_str:
            print("[X] organization_users table does not exist")
            print("\nPlease run the following SQL in Supabase SQL Editor:")
            print("-" * 60)
            print("""
-- Organization Users Table
CREATE TABLE IF NOT EXISTS organization_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(50) NOT NULL,
    auth_user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'user')),
    is_active BOOLEAN DEFAULT true,
    invited_by UUID REFERENCES organization_users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_login_at TIMESTAMPTZ,
    UNIQUE(tenant_id, email)
);

CREATE INDEX IF NOT EXISTS idx_org_users_tenant ON organization_users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_org_users_auth_id ON organization_users(auth_user_id);

-- User Invitations Table
CREATE TABLE IF NOT EXISTS user_invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(50) NOT NULL,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    token VARCHAR(64) NOT NULL UNIQUE,
    invited_by UUID REFERENCES organization_users(id),
    expires_at TIMESTAMPTZ NOT NULL,
    accepted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, email)
);

CREATE INDEX IF NOT EXISTS idx_invitations_token ON user_invitations(token);

-- Enable RLS
ALTER TABLE organization_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_invitations ENABLE ROW LEVEL SECURITY;

-- RLS Policies for organization_users
CREATE POLICY "Service role can manage all users" ON organization_users
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Users can view own organization" ON organization_users
    FOR SELECT USING (
        tenant_id IN (
            SELECT tenant_id FROM organization_users
            WHERE auth_user_id = auth.uid()
        )
    );

-- RLS Policies for user_invitations
CREATE POLICY "Service role can manage all invitations" ON user_invitations
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Admins can view org invitations" ON user_invitations
    FOR SELECT USING (
        tenant_id IN (
            SELECT tenant_id FROM organization_users
            WHERE auth_user_id = auth.uid() AND role = 'admin'
        )
    );
""")
            print("-" * 60)
            print("\n[X] Please create the tables first, then run this script again.")
            return False
        else:
            print(f"Error checking table: {e}")
            return False


def create_admin_user(tenant_id: str, email: str, password: str, name: str):
    """Create an admin user for the specified tenant"""

    print(f"\nSetting up admin user for tenant: {tenant_id}")
    print(f"Email: {email}")
    print(f"Name: {name}")
    print("-" * 40)

    # Get tenant config
    try:
        config = get_config(tenant_id)
    except FileNotFoundError:
        print(f"[X] Error: Tenant '{tenant_id}' not found")
        print(f"  Available tenants: Check the 'clients/' directory")
        return False

    # Create Supabase client with service role key
    supabase = create_client(config.supabase_url, config.supabase_service_key)

    # Check if tables exist
    if not create_tables_if_not_exist(supabase):
        return False

    # Check if user already exists in organization_users
    existing = supabase.table("organization_users").select("*").eq(
        "tenant_id", tenant_id
    ).eq("email", email).execute()

    if existing.data:
        print(f"[OK] User {email} already exists in {tenant_id}")
        print(f"  User ID: {existing.data[0]['id']}")
        print(f"  Role: {existing.data[0]['role']}")
        return True

    # Create user in Supabase Auth
    print("\n1. Creating user in Supabase Auth...")
    try:
        auth_response = supabase.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,  # Skip email verification
            "user_metadata": {
                "name": name,
                "tenant_id": tenant_id
            }
        })

        if not auth_response.user:
            print("[X] Failed to create auth user")
            return False

        auth_user_id = auth_response.user.id
        print(f"   [OK] Auth user created: {auth_user_id}")

    except Exception as e:
        error_msg = str(e)
        if "already been registered" in error_msg.lower():
            print(f"   [!] User already exists in Auth, fetching ID...")
            # Try to get the existing auth user
            users = supabase.auth.admin.list_users()
            auth_user_id = None
            for user in users:
                if user.email == email:
                    auth_user_id = user.id
                    break

            if not auth_user_id:
                print("[X] Could not find existing auth user")
                return False
            print(f"   [OK] Found existing auth user: {auth_user_id}")
        else:
            print(f"[X] Error creating auth user: {e}")
            return False

    # Create organization user record
    print("\n2. Creating organization user record...")
    try:
        org_user = supabase.table("organization_users").insert({
            "tenant_id": tenant_id,
            "auth_user_id": str(auth_user_id),
            "email": email,
            "name": name,
            "role": "admin",
            "is_active": True
        }).execute()

        if org_user.data:
            print(f"   [OK] Organization user created: {org_user.data[0]['id']}")
        else:
            print("[X] Failed to create organization user")
            return False

    except Exception as e:
        if "duplicate key" in str(e).lower():
            print(f"   [!] User already exists in organization_users")
        else:
            print(f"[X] Error creating organization user: {e}")
            return False

    print("\n" + "=" * 50)
    print("[OK] Admin user setup complete!")
    print("=" * 50)
    print(f"\nYou can now log in with:")
    print(f"  Email: {email}")
    print(f"  Password: {password}")
    print(f"  Tenant: {tenant_id}")
    print(f"\nFrontend URL: http://localhost:5173/login")

    return True


def main():
    parser = argparse.ArgumentParser(description="Setup admin user for a tenant")
    parser.add_argument("--email", required=True, help="Admin email address")
    parser.add_argument("--password", required=True, help="Admin password (min 8 chars)")
    parser.add_argument("--name", required=True, help="Admin display name")
    parser.add_argument("--tenant", default="africastay", help="Tenant ID (default: africastay)")

    args = parser.parse_args()

    # Validate password
    if len(args.password) < 8:
        print("Error: Password must be at least 8 characters")
        sys.exit(1)

    success = create_admin_user(
        tenant_id=args.tenant,
        email=args.email,
        password=args.password,
        name=args.name
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
