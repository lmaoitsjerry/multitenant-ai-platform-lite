# Email Auto-Quote Flow Documentation

This document explains how the tenant email auto-quoting system works in the Multi-Tenant AI Travel Platform.

## Overview

When a customer sends a travel inquiry email, the system automatically:
1. Receives the email via SendGrid Inbound Parse
2. Identifies which tenant the email belongs to
3. Parses the email to extract travel requirements
4. Generates a personalized quote PDF
5. Emails the quote back to the customer
6. Creates a client record in the CRM

---

## Architecture Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Customer Email │────▶│  SendGrid       │────▶│  Platform API   │
│                 │     │  Inbound Parse  │     │  /webhooks/     │
└─────────────────┘     └─────────────────┘     │  email/inbound  │
                                                 └────────┬────────┘
                                                          │
                        ┌─────────────────────────────────┼─────────────────────────────────┐
                        │                                 ▼                                 │
                        │  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐ │
                        │  │ Identify Tenant │──▶│  Parse Email    │──▶│  Find Hotels    │ │
                        │  │ (from address)  │   │  (AI Parser)    │   │  (BigQuery)     │ │
                        │  └─────────────────┘   └─────────────────┘   └────────┬────────┘ │
                        │                                                        │          │
                        │  ┌─────────────────┐   ┌─────────────────┐            │          │
                        │  │  Send to        │◀──│  Generate Quote │◀───────────┘          │
                        │  │  Customer       │   │  PDF            │                       │
                        │  └────────┬────────┘   └─────────────────┘                       │
                        │           │                                                       │
                        │  ┌────────▼────────┐   ┌─────────────────┐                       │
                        │  │  Save to        │──▶│  Add to CRM     │                       │
                        │  │  Supabase       │   │  Pipeline       │                       │
                        │  └─────────────────┘   └─────────────────┘                       │
                        │                                                                   │
                        │                        Quote Agent                                │
                        └───────────────────────────────────────────────────────────────────┘
```

---

## Components

### 1. Email Webhook Handler
**File:** `src/webhooks/email_webhook.py`

Receives inbound emails from SendGrid and routes them to the correct tenant.

**Endpoints:**
- `POST /webhooks/email/inbound` - Universal endpoint (detects tenant from email address)
- `POST /webhooks/email/inbound/{tenant_id}` - Tenant-specific endpoint
- `GET /webhooks/email/test/{tenant_id}` - Test endpoint for debugging

**Tenant Detection Strategies:**
1. **Subdomain routing:** `africastay@inbound.zorahai.com` → tenant: `africastay`
2. **Plus addressing:** `quotes+africastay@zorahai.com` → tenant: `africastay`
3. **X-Tenant-ID header:** Custom header in email
4. **Subject line tag:** `[TENANT:africastay]` in subject

### 2. Email Parser
**File:** `src/agents/universal_email_parser.py`

Extracts travel requirements from email body using pattern matching and fuzzy logic.

**Extracted Data:**
- Customer name
- Email address
- Phone number
- Destination (fuzzy matched against tenant's destinations)
- Check-in/check-out dates
- Number of adults and children
- Budget (if mentioned)
- Specific hotel requests

### 3. Quote Agent
**File:** `src/agents/quote_agent.py`

Orchestrates the complete quote generation process.

**Process:**
1. Validate and normalize customer data
2. Query BigQuery for matching hotels
3. Calculate pricing for each hotel option
4. Generate PDF quote
5. Send email with PDF attachment
6. Save quote to Supabase
7. Create/update CRM record

### 4. Email Sender
**File:** `src/utils/email_sender.py`

Handles sending emails via SendGrid or SMTP fallback.

**Features:**
- SendGrid API integration (preferred)
- SMTP fallback for testing
- PDF attachments
- HTML email templates with tenant branding
- CC to assigned consultant

---

## Tenant Configuration

Each tenant needs the following settings in their `client.yaml`:

```yaml
# Client identity
client:
  id: africastay
  name: Africa Stay Travel

# Email configuration
email:
  primary: quotes@africastay.com

  # SendGrid settings (required for auto-quote)
  sendgrid:
    api_key: ${AFRICASTAY_SENDGRID_API_KEY}
    from_email: quotes@africastay.com
    from_name: Africa Stay Travel
    reply_to: sales@africastay.com

# Branding (used in emails)
branding:
  company_name: Africa Stay Travel
  primary_color: '#FF6B6B'
  secondary_color: '#4ECDC4'
  email_signature: |
    Best regards,
    The Africa Stay Team

    📧 sales@africastay.com
    📞 +27 21 123 4567

# Destinations (for email parsing)
destinations:
  - name: Zanzibar
    code: ZNZ
    enabled: true
  - name: Cape Town
    code: CPT
    enabled: true
```

---

## SendGrid Setup

### 1. Create SendGrid Account/Subuser

Each tenant should have their own SendGrid subuser for isolation:

1. Log into SendGrid → Settings → Subuser Management
2. Create subuser for tenant (e.g., `africastay`)
3. Generate API key for the subuser

### 2. Domain Authentication

Verify the sender domain in SendGrid:

1. SendGrid → Settings → Sender Authentication
2. Add domain (e.g., `africastay.com`)
3. Add required DNS records:

```
CNAME   em1234.africastay.com       → u12345678.wl123.sendgrid.net
CNAME   s1._domainkey.africastay.com → s1.domainkey.u12345678.wl123.sendgrid.net
CNAME   s2._domainkey.africastay.com → s2.domainkey.u12345678.wl123.sendgrid.net
```

### 3. Inbound Parse Setup

Configure SendGrid to forward inbound emails to our webhook:

1. SendGrid → Settings → Inbound Parse
2. Add new host/URL:
   - **Receiving Domain:** `inbound.zorahai.com` (or tenant-specific subdomain)
   - **Destination URL:** `https://api.zorahai.com/webhooks/email/inbound`
   - **Check "POST the raw, full MIME message"** (optional)
   - **Check "Send raw"** (optional)

### 4. MX Record for Inbound

Add MX record to receive emails:

```
MX    inbound.zorahai.com    10    mx.sendgrid.net
```

Or for tenant-specific:
```
MX    quotes.africastay.com  10    mx.sendgrid.net
```

---

## DNS Records Summary

For each tenant domain, configure:

| Type  | Host                          | Value                                         | Purpose             |
|-------|-------------------------------|-----------------------------------------------|---------------------|
| MX    | inbound (or quotes)           | mx.sendgrid.net (priority 10)                 | Receive emails      |
| CNAME | em1234                        | u12345678.wl123.sendgrid.net                  | Domain verification |
| CNAME | s1._domainkey                 | s1.domainkey.u12345678.wl123.sendgrid.net     | DKIM signing        |
| CNAME | s2._domainkey                 | s2.domainkey.u12345678.wl123.sendgrid.net     | DKIM signing        |
| TXT   | @                             | v=spf1 include:sendgrid.net ~all              | SPF authorization   |

---

## Email Routing Options

### Option 1: Central Domain (Recommended)

All tenants use a subdomain of the platform domain:

- Tenant receives emails at: `africastay@inbound.zorahai.com`
- Single MX record for `inbound.zorahai.com`
- Tenant identified by local part

**Pros:** Simpler DNS, single inbound parse setup
**Cons:** Emails not from tenant's domain

### Option 2: Tenant Subdomains

Each tenant has their own subdomain:

- Tenant receives emails at: `quotes@quotes.africastay.com`
- MX record for each tenant subdomain
- Inbound parse for each subdomain

**Pros:** Professional appearance, tenant branding
**Cons:** More complex setup per tenant

### Option 3: Email Forwarding

Tenant forwards emails to the platform:

- Customer emails: `quotes@africastay.com`
- Tenant forwards to: `africastay@inbound.zorahai.com`
- Auto-forward rule in tenant's email system

**Pros:** Uses tenant's existing email
**Cons:** Relies on tenant's email forwarding

---

## Testing

### Test Endpoint

```bash
curl "https://api.zorahai.com/webhooks/email/test/africastay?email=test@example.com&subject=Quote%20for%20Zanzibar"
```

### Simulate Inbound Email

```bash
curl -X POST "https://api.zorahai.com/webhooks/email/inbound" \
  -F "from=John Doe <john@example.com>" \
  -F "to=africastay@inbound.zorahai.com" \
  -F "subject=Quote request for Zanzibar" \
  -F "text=Hi, I'm looking for a 7-night trip to Zanzibar for 2 adults in September."
```

---

## Troubleshooting

### Email Not Received

1. Check MX records: `dig MX inbound.zorahai.com`
2. Verify SendGrid Inbound Parse is configured
3. Check API logs for webhook calls
4. Verify tenant ID is correctly extracted

### Quote Not Generated

1. Check if destination was detected (logs show parsed data)
2. Verify BigQuery has hotel data for destination
3. Check quote agent logs for errors

### Email Not Sent

1. Verify SendGrid API key is valid
2. Check sender domain is authenticated
3. Review SendGrid activity logs

---

## Environment Variables

```bash
# Per-tenant SendGrid keys (stored in .env or secrets manager)
AFRICASTAY_SENDGRID_API_KEY=SG.xxxxx
BEACHRESORTS_SENDGRID_API_KEY=SG.yyyyy

# Or use a single key for all tenants
SENDGRID_API_KEY=SG.master_key
```

---

## Security Considerations

1. **Webhook Authentication:** Consider adding webhook signature verification
2. **Rate Limiting:** Implement rate limits on inbound endpoints
3. **Email Validation:** Validate sender addresses to prevent spam
4. **Attachment Handling:** Be careful with email attachments (malware risk)
5. **PII Protection:** Customer email data should be handled securely

---

## Files Reference

| File | Purpose |
|------|---------|
| `src/webhooks/email_webhook.py` | Inbound email webhook handler |
| `src/agents/universal_email_parser.py` | Email content parser |
| `src/agents/quote_agent.py` | Quote generation orchestrator |
| `src/utils/email_sender.py` | Email sending (SendGrid/SMTP) |
| `src/utils/pdf_generator.py` | Quote PDF generation |
| `config/loader.py` | Client configuration loading |
| `clients/{tenant}/client.yaml` | Per-tenant configuration |
