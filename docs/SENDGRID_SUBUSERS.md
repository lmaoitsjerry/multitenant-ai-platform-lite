# SendGrid Subuser System - Technical Documentation

## Overview

This document explains how the multi-tenant travel platform uses SendGrid subusers to provide email isolation for each tenant. Each tenant gets their own SendGrid subuser, API key, and sender identity, ensuring complete email separation.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   MASTER SENDGRID ACCOUNT                   │
│                (Your Main SendGrid Account)                 │
│                                                             │
│   API Key: SENDGRID_MASTER_API_KEY                         │
│   Permissions: Subuser Management, API Key Creation        │
│                                                             │
├────────────────┬────────────────┬────────────────┬─────────┤
│   SUBUSER 1    │   SUBUSER 2    │   SUBUSER 3    │   ...   │
│  (Tenant A)    │  (Tenant B)    │  (Tenant C)    │         │
│                │                │                │         │
│  API Key A     │  API Key B     │  API Key C     │         │
│  Sender ID A   │  Sender ID B   │  Sender ID C   │         │
│  IP Pool A     │  IP Pool B     │  IP Pool C     │         │
└────────────────┴────────────────┴────────────────┴─────────┘
```

## Why Subusers?

1. **Email Reputation Isolation** - If one tenant has deliverability issues (spam complaints, bounces), it doesn't affect other tenants
2. **Separate Analytics** - Each tenant can see only their own email statistics
3. **API Key Isolation** - Tenant-specific API keys that only work for that tenant's sending
4. **Compliance** - Each tenant maintains their own sender identity (CAN-SPAM compliance)

## Prerequisites

### Master Account Requirements

1. **SendGrid Pro Plan or higher** - Subuser feature requires Pro+ plan
2. **Subuser Management Permission** - Master API key needs these scopes:
   - `subusers.create`
   - `subusers.read`
   - `subusers.update`
   - `api_keys.create`
   - `sender_verification.create`
   - `whitelabel.domains.create` (optional, for domain authentication)
   - `ips.read` (for IP assignment)
   - `ips.pools.update` (for IP assignment)

### Environment Variables

```bash
# .env file
SENDGRID_MASTER_API_KEY=SG.xxxxx...  # Master account API key with subuser permissions
```

## How It Works

### 1. Tenant Onboarding Flow

When a new tenant completes onboarding:

```
┌─────────────────────────────────────────────────────────────┐
│                    ONBOARDING WIZARD                        │
│                                                             │
│  1. Tenant fills company profile                            │
│  2. Tenant provides admin email                             │
│  3. System generates tenant_id (e.g., tn_abc123_def456)    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              SENDGRID PROVISIONING (Automatic)              │
│                                                             │
│  Step 1: Create Subuser                                     │
│    POST /v3/subusers                                        │
│    Username: tn_abc123_def456 (sanitized tenant_id)        │
│    Email: admin@tenant.com                                  │
│    Password: auto-generated                                 │
│                                                             │
│  Step 2: Create API Key for Subuser                         │
│    POST /v3/api_keys                                        │
│    Header: on-behalf-of: tn_abc123_def456                  │
│    Scopes: mail.send, sender_verification_eligible         │
│                                                             │
│  Step 3: Create Verified Sender                             │
│    POST /v3/verified_senders                                │
│    Header: on-behalf-of: tn_abc123_def456                  │
│    From Email: sales@tenant.com                             │
│    From Name: Tenant Company Name                           │
│    Reply To: admin@tenant.com                               │
│                                                             │
│  Step 4: Assign IP (Optional)                               │
│    PUT /v3/subusers/{username}/ips                          │
│    Assigns dedicated IP from pool                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   RESULT STORED IN CONFIG                   │
│                                                             │
│  clients/{tenant_id}/client.yaml:                          │
│    email:                                                   │
│      sendgrid:                                              │
│        api_key: SG.tenant_specific_key...                  │
│        from_email: sales@tenant.com                         │
│        from_name: Tenant Company Name                       │
│        reply_to: admin@tenant.com                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2. Email Sending Flow

When the system sends emails (quotes, invoices, etc.):

```
┌─────────────────────────────────────────────────────────────┐
│                     EMAIL SERVICE                           │
│                                                             │
│  1. Load tenant config                                      │
│     config = get_config(tenant_id)                         │
│                                                             │
│  2. Get tenant's SendGrid credentials                       │
│     api_key = config.sendgrid_api_key                      │
│     from_email = config.sendgrid_from_email                │
│     from_name = config.sendgrid_from_name                  │
│                                                             │
│  3. Create SendGrid client with tenant's API key           │
│     sg = sendgrid.SendGridAPIClient(api_key)              │
│                                                             │
│  4. Send email (uses tenant's subuser account)             │
│     sg.send(message)                                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Code Reference

### SendGridProvisioner Class

Location: `src/services/provisioning_service.py`

```python
class SendGridProvisioner:
    """Handles SendGrid subuser and API key creation"""

    def __init__(self, master_api_key: str):
        """Initialize with master SendGrid API key"""
        self.api_key = master_api_key
        self.base_url = "https://api.sendgrid.com/v3"
        self.headers = {
            "Authorization": f"Bearer {master_api_key}",
            "Content-Type": "application/json"
        }

    def create_subuser(self, username, email, password=None, ips=None):
        """Create a SendGrid subuser"""
        # POST /v3/subusers

    def create_api_key(self, name, scopes=None, subuser=None):
        """Create an API key for a subuser"""
        # POST /v3/api_keys with on-behalf-of header

    def add_verified_sender(self, from_email, from_name, ...):
        """Add a verified sender identity"""
        # POST /v3/verified_senders with on-behalf-of header

    def assign_ip_to_subuser(self, subuser, ip_address=None):
        """Assign an IP address to a subuser"""
        # PUT /v3/subusers/{username}/ips
```

### Usage in Onboarding

Location: `src/api/onboarding_routes.py`

```python
async def provision_sendgrid_subuser(
    tenant_id: str,
    contact_email: str,
    from_email: str,
    from_name: str,
    company_name: str
) -> Dict[str, Any]:
    """
    Create a SendGrid subuser for tenant email isolation.

    Returns:
        Dict with success status, api_key, and any errors
    """
    provisioner = SendGridProvisioner(master_key)

    # Step 1: Create subuser
    subuser_result = provisioner.create_subuser(
        username=tenant_id,
        email=contact_email
    )

    # Step 2: Create API key for the subuser
    api_key_result = provisioner.create_api_key(
        name=f"{tenant_id}-mail-api-key",
        subuser=tenant_id
    )

    # Step 3: Create verified sender identity
    sender_result = provisioner.add_verified_sender(
        from_email=from_email,
        from_name=from_name,
        reply_to=contact_email,
        nickname=company_name,
        subuser=tenant_id
    )

    # Step 4: Try to assign an IP (optional)
    ip_result = provisioner.assign_ip_to_subuser(tenant_id)

    return {
        "success": True,
        "subuser": tenant_id,
        "api_key": api_key_result["data"]["api_key"],
        "ip_address": ip_result.get("ip")
    }
```

## Config Storage

Each tenant's SendGrid credentials are stored in their config file:

```yaml
# clients/{tenant_id}/client.yaml
email:
  primary: sales@tenant.com
  smtp:
    host: smtp.sendgrid.net
    port: 587
    username: apikey
    password: SG.tenant_specific_api_key_here
  sendgrid:
    api_key: SG.tenant_specific_api_key_here
    from_email: sales@tenant.com
    from_name: Tenant Company Name
    reply_to: admin@tenant.com
```

## Troubleshooting

### Common Issues

1. **"Subuser already exists"**
   - The tenant_id was already used to create a subuser
   - Solution: The code handles this gracefully and continues

2. **"Permission denied"**
   - Master API key lacks required scopes
   - Solution: Regenerate master API key with full subuser management permissions

3. **"No IPs available"**
   - All IPs in the pool are assigned
   - Solution: Purchase additional IPs or use shared IP pool

4. **"Sender verification required"**
   - SendGrid requires email verification for new senders
   - Solution: Check the from_email inbox for verification link

### Debugging

Check provisioning logs:
```bash
# Look for SendGrid-related logs
grep -i "sendgrid" /var/log/platform.log

# Expected success log:
# INFO - SendGrid subuser created: tn_abc123_def456
# INFO - SendGrid API key created: tn_abc123_def456-mail-api-key
# INFO - Verified sender created: sales@tenant.com
```

## Security Considerations

1. **API Key Storage**
   - Tenant API keys are stored in their client.yaml files
   - These files should have restricted filesystem permissions
   - Never commit API keys to version control

2. **Master Key Protection**
   - SENDGRID_MASTER_API_KEY should only be in .env (not committed)
   - Limit access to production environment

3. **Subuser Isolation**
   - Each subuser can only send as their verified senders
   - Subusers cannot access other subusers' data
   - Subusers cannot modify the master account

## Appendix: SendGrid API Reference

### Create Subuser
```bash
POST https://api.sendgrid.com/v3/subusers
Authorization: Bearer {MASTER_API_KEY}

{
  "username": "tenant_id",
  "email": "admin@tenant.com",
  "password": "auto_generated_password",
  "ips": []
}
```

### Create API Key for Subuser
```bash
POST https://api.sendgrid.com/v3/api_keys
Authorization: Bearer {MASTER_API_KEY}
on-behalf-of: {subuser_username}

{
  "name": "tenant-mail-api-key",
  "scopes": ["mail.send", "sender_verification_eligible"]
}
```

### Create Verified Sender
```bash
POST https://api.sendgrid.com/v3/verified_senders
Authorization: Bearer {MASTER_API_KEY}
on-behalf-of: {subuser_username}

{
  "nickname": "Company Name",
  "from_email": "sales@company.com",
  "from_name": "Company Name",
  "reply_to": "admin@company.com",
  "address": "123 Main St",
  "city": "Cape Town",
  "country": "South Africa"
}
```

### Assign IP to Subuser
```bash
PUT https://api.sendgrid.com/v3/subusers/{username}/ips
Authorization: Bearer {MASTER_API_KEY}

["192.168.1.1"]
```

---

*Last updated: January 2026*
