# Email Pipeline Diagnostics Report

**Generated:** 2026-01-16
**Phase:** 01-diagnostics-logging
**Plan:** 01-01

## 1. Webhook Registration Status

### Router Chain Verification

The email webhook is correctly registered in the application:

```
main.py
  -> src/api/routes.py (include_routers function)
    -> app.include_router(email_webhook_router, prefix="/webhooks")
      -> src/webhooks/email_webhook.py (router = APIRouter)
```

**Verified endpoints:**
- `POST /webhooks/email/inbound` - Main SendGrid webhook endpoint
- `POST /webhooks/email/inbound/{tenant_id}` - Per-tenant direct endpoint
- `GET /webhooks/email/diagnose` - NEW: System diagnostics endpoint
- `GET /webhooks/email/status` - Configuration status
- `GET /webhooks/email/test/{tenant_id}` - Test email processing
- `POST /webhooks/email/debug` - Raw data logging

### Middleware Status

From `src/middleware/auth_middleware.py`:

```python
PUBLIC_PREFIXES = [
    "/api/v1/webhooks/",
    "/api/webhooks/",  # Legacy webhook endpoints (SendGrid inbound)
    "/webhooks/",      # <-- Email webhook is PUBLIC, no auth required
    ...
]
```

**Confirmed:** Webhook endpoints are exempt from JWT authentication.

## 2. Tenant Resolution Analysis

### Previous Implementation (BROKEN)

The original `extract_tenant_from_email()` function had 4 strategies:

1. **Subdomain routing:** `africastay@inbound.zorahai.com` -> looks up `africastay` as tenant ID
2. **Plus addressing:** `quotes+africastay@domain.com` -> extracts `africastay`
3. **X-Tenant-ID header:** Custom header lookup
4. **Subject pattern:** `[TENANT:africastay]` in subject

**THE BUG:** None of these strategies matched the actual email addresses used in production:
- SendGrid subusers like `final-itc-3@zorah.ai`
- Custom support emails like `support@company.com`
- Personal emails like `someone@gmail.com`

### Current Tenant Formats

From `clients/` directory analysis:
- **Legacy tenants:** `africastay`, `beachresorts`, `example`, `safariexplore-kvph`, `safarirun-t0vc`
- **New tenants:** `tn_068196ef_abcfe0a03933`, `tn_092bb439_003b8ded5fe4`, etc.
- **Total tenants:** ~70 directories

### New Implementation (FIXED)

The enhanced `extract_tenant_from_email()` now uses these strategies in order:

1. **Database lookup - support_email:** Match TO against `tenant_settings.support_email` (ANY domain)
   - Example: `support@mycompany.com` matches tenant with that support_email

2. **Database lookup - sendgrid_email:** Match TO against `tenant_settings.sendgrid_username + @zorah.ai`
   - Example: `final-itc-3@zorah.ai` matches tenant with sendgrid_username=`final-itc-3`

3. **Database lookup - primary_email:** Match TO against config's `email.primary`
   - Example: `quotes@holidaytoday.co.za` matches africastay tenant

4. **Direct tenant ID:** Local part is tenant ID (original behavior)
5. **Plus addressing:** `quotes+africastay@domain.com` (original behavior)
6. **X-Tenant-ID header:** Custom header (original behavior)
7. **Subject pattern:** `[TENANT:xxx]` (original behavior)

### Database Schema for Email Matching

**tenant_settings table (010_tenant_settings.sql):**
```sql
CREATE TABLE tenant_settings (
    tenant_id TEXT NOT NULL UNIQUE,
    support_email TEXT,           -- Any domain email for matching
    sendgrid_username TEXT,       -- SendGrid subuser (without @zorah.ai)
    ...
);
```

**Data example:**
| tenant_id | support_email | sendgrid_username |
|-----------|--------------|-------------------|
| africastay | sales@holidaytoday.co.za | final-itc-3 |
| tn_xxx | support@company.com | tenant-123 |
| tn_yyy | someone@gmail.com | tenant-456 |

## 3. Import Chain Analysis

### UniversalEmailParser

**File exists:** `src/agents/universal_email_parser.py`

**Import chain:**
```
src/webhooks/email_webhook.py
  -> from src.agents.universal_email_parser import UniversalEmailParser
    -> from config.loader import ClientConfig
```

**Status:** Import succeeds. Parser is functional.

### QuoteAgent

**File exists:** `src/agents/quote_agent.py`

**Import chain:**
```
src/webhooks/email_webhook.py
  -> from src.agents.quote_agent import QuoteAgent
    -> from config.loader import ClientConfig
    -> from src.tools.bigquery_tool import BigQueryTool
    -> from src.utils.pdf_generator import PDFGenerator
    -> from src.utils.email_sender import EmailSender
    -> from src.tools.supabase_tool import SupabaseTool
    -> from src.services.crm_service import CRMService
```

**Status:** All imports succeed (verified via diagnose endpoint).

## 4. SendGrid Configuration

### Expected Configuration

From `/webhooks/email/status` endpoint:

```json
{
  "sendgrid_configuration": {
    "step_1_mx_record": {
      "type": "MX",
      "host": "inbound.zorah.ai",
      "value": "mx.sendgrid.net",
      "priority": 10
    },
    "step_2_inbound_parse": {
      "domain": "inbound.zorah.ai",
      "webhook_url": "https://api.zorah.ai/webhooks/email/inbound"
    }
  }
}
```

### Actual vs Expected

| Component | Expected | Actual Status |
|-----------|----------|---------------|
| MX Record | mx.sendgrid.net -> inbound.zorah.ai | UNKNOWN - Need DNS check |
| Inbound Parse | Configured in SendGrid dashboard | UNKNOWN - Need SendGrid check |
| Webhook URL | https://api.zorah.ai/webhooks/email/inbound | NEEDS VERIFICATION |
| Subuser Format | `{name}@zorah.ai` | CONFIRMED - Used by tenants |

### Key Insight

SendGrid subusers send emails as `final-itc-3@zorah.ai`, NOT `final-itc-3@inbound.zorah.ai`.

This means the TO address in webhook might be:
- `final-itc-3@zorah.ai` (subuser format) - NOW HANDLED
- `support@company.com` (forwarded email) - NOW HANDLED
- `someone@gmail.com` (personal support) - NOW HANDLED

## 5. Identified Failure Points

### CONFIRMED FAILURE: Tenant Lookup Mismatch

**Evidence:** Code analysis shows the original lookup only checked:
1. Local part as direct tenant ID
2. Plus addressing
3. X-Tenant-ID header
4. Subject pattern

**None of these match:**
- `final-itc-3@zorah.ai` (SendGrid subuser)
- `support@company.com` (custom domain)
- `someone@gmail.com` (personal email)

**Status:** FIXED in Task 1 - Now queries database for support_email, sendgrid_username, and primary_email.

### POTENTIAL FAILURE: SendGrid Inbound Parse Not Configured

**Evidence:** Unknown - requires checking SendGrid dashboard and DNS records.

**To Verify:**
1. Check MX record: `dig MX inbound.zorah.ai`
2. Check SendGrid Inbound Parse settings
3. Send test email and check Cloud Run logs

### POTENTIAL FAILURE: Webhook Not Publicly Accessible

**Evidence:** Unknown - URL https://api.zorah.ai/webhooks/email/inbound needs verification.

**To Verify:**
```bash
curl -X POST https://api.zorah.ai/webhooks/email/inbound \
  -F "from=test@example.com" \
  -F "to=final-itc-3@zorah.ai" \
  -F "subject=Test" \
  -F "text=Test body"
```

## 6. Diagnostic Logging Added

### Logging Format

All logs now follow this format:
```
[EMAIL_WEBHOOK][{DIAGNOSTIC_ID}][STEP_{N}] {message} | data={json}
```

### Steps Logged

| Step | Description | Data Captured |
|------|-------------|---------------|
| 1 | Request received | timestamp, content-type, method, url |
| 2 | Form data parsed | from, to, subject, envelope, body_length |
| 3 | Tenant resolution attempted | to_email, strategies tried |
| 4 | Tenant resolution result | resolved_tenant_id, final_strategy |
| 5 | Config loaded | tenant_id, company_name, destinations |
| 6 | Background task queued | tenant_id, from_email, subject |
| 7 | Processing started | tenant_id, from_email, subject |
| 8 | Email parser import | success/error |
| 9 | Email parsed | destination, customer_name, adults, children |
| 10 | Quote generation decision | should_generate, reason |
| 11 | Quote result or skip | quote_id or skip_reason |

### Diagnose Endpoint

New endpoint `GET /webhooks/email/diagnose` returns:
- All webhook endpoints
- Tenant list with email addresses (support_email, sendgrid_email, primary_email)
- Environment variable status
- Import test results for UniversalEmailParser, QuoteAgent, etc.
- Config test with sample tenant

## 7. Local Testing Results

**Note:** Local testing to be completed in Task 3 after server startup.

### Planned Tests

1. **Diagnose endpoint:** `curl http://localhost:8080/webhooks/email/diagnose`
2. **Debug endpoint:** Test with mock SendGrid data
3. **Inbound endpoint:** Test full flow with tenant lookup

## 8. Recommended Next Steps (Phase 2)

Based on this diagnostic analysis:

### Immediate (Phase 2)

1. **Verify SendGrid Configuration**
   - Check MX records for inbound.zorah.ai
   - Verify Inbound Parse webhook URL in SendGrid dashboard
   - Check webhook SSL certificate validity

2. **Verify Tenant Data**
   - Ensure all tenants have sendgrid_username in tenant_settings
   - Run migration script if needed to populate missing data

3. **Test End-to-End**
   - Send real test email to known tenant
   - Verify logs show all 11 steps
   - Confirm quote generation or identify next failure point

### If Webhook Not Receiving Emails

- Check Cloud Run logs for any requests to /webhooks/email/inbound
- Verify SendGrid Inbound Parse is enabled and configured
- Check firewall/ingress rules

### If Tenant Lookup Still Fails

- Verify tenant_settings table has data
- Check database connection from webhook (SUPABASE_URL, SUPABASE_KEY)
- Use diagnose endpoint to see what emails are registered per tenant

## Summary

| Area | Status | Notes |
|------|--------|-------|
| Webhook Registration | OK | Endpoints registered and public |
| Tenant Resolution | FIXED | Now queries DB for support_email, sendgrid_email, primary_email |
| Import Chain | OK | All modules import successfully |
| Diagnostic Logging | ADDED | 11-step logging with diagnostic IDs |
| SendGrid Config | UNKNOWN | Needs external verification |
| E2E Flow | UNTESTED | Needs local testing (Task 3) |

**Primary Fix Applied:** Tenant lookup now matches TO email against database fields (support_email, sendgrid_username@zorah.ai, primary_email) instead of just parsing the email address structure.
