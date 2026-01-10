# Data Protection Compliance Guide

## Overview

This document describes the GDPR (General Data Protection Regulation) and POPIA (Protection of Personal Information Act) compliance implementation for the Multi-Tenant AI Travel Platform.

**Last Updated:** January 2025
**Compliance Officer:** [To be assigned]
**Review Schedule:** Quarterly

---

## Table of Contents

1. [Personal Data Inventory](#1-personal-data-inventory)
2. [Data Subject Rights](#2-data-subject-rights)
3. [Consent Management](#3-consent-management)
4. [Data Processing Records](#4-data-processing-records)
5. [Third-Party Processors](#5-third-party-processors)
6. [Security Measures](#6-security-measures)
7. [Data Retention](#7-data-retention)
8. [Breach Response](#8-breach-response)
9. [API Reference](#9-api-reference)
10. [Compliance Checklist](#10-compliance-checklist)

---

## 1. Personal Data Inventory

### 1.1 Data Categories Collected

| Category | Data Fields | Purpose | Legal Basis |
|----------|-------------|---------|-------------|
| **Identity Data** | name, email | Account creation, service delivery | Contract |
| **Contact Data** | phone, address | Communication, bookings | Contract |
| **Transaction Data** | invoices, quotes, payments | Service delivery | Contract |
| **Usage Data** | login history, page views | Service improvement | Legitimate Interest |
| **Marketing Data** | preferences, opt-ins | Marketing communications | Consent |
| **Travel Data** | destinations, dates, travelers | Quote generation | Contract |

### 1.2 Data Storage Locations

| Data Type | Storage Location | Encryption | Access Control |
|-----------|------------------|------------|----------------|
| User accounts | Supabase Auth | At rest (AES-256) | JWT + RLS |
| Client records | Supabase (clients table) | At rest | Tenant RLS |
| Quotes/Invoices | Supabase | At rest | Tenant RLS |
| Call recordings | Supabase Storage | At rest + transit | Signed URLs |
| Audit logs | Supabase (data_audit_log) | At rest | Admin only |
| Analytics | BigQuery | At rest + transit | IAM |

### 1.3 Database Tables with PII

```sql
-- Tables containing personal data:

organization_users    -- email, name
user_invitations     -- email
clients              -- email, name, phone
quotes               -- customer_name, customer_email, customer_phone
invoices             -- customer_name, customer_email, customer_phone, billing_address
call_records         -- customer_phone
call_queue           -- customer_phone
support_tickets      -- email, name
consent_records      -- email (for consent tracking)
data_subject_requests -- email, name (for DSAR tracking)
```

---

## 2. Data Subject Rights

### 2.1 Rights Implemented

| Right | GDPR Article | Endpoint | Implementation |
|-------|--------------|----------|----------------|
| Right of Access | Art. 15 | `POST /privacy/dsar` | Full data export |
| Right to Rectification | Art. 16 | `POST /privacy/dsar` | Manual review |
| Right to Erasure | Art. 17 | `POST /privacy/erasure` | Anonymization |
| Right to Restrict | Art. 18 | `POST /privacy/dsar` | Processing freeze |
| Right to Portability | Art. 20 | `POST /privacy/export` | JSON/CSV export |
| Right to Object | Art. 21 | `POST /privacy/dsar` | Marketing opt-out |

### 2.2 Response Timelines

- **Standard requests:** 30 days (GDPR/POPIA requirement)
- **Complex requests:** Up to 60 days with notification
- **Identity verification:** Required before processing

### 2.3 DSAR Workflow

```
1. User submits request via Privacy Settings
2. System creates DSAR record with due date
3. Confirmation email sent to user
4. Admin notified of new request
5. Admin verifies identity if needed
6. Request processed (export/erasure/etc.)
7. User notified of completion
8. DSAR record archived
```

---

## 3. Consent Management

### 3.1 Consent Types

| Type | Required | Default | Withdrawable |
|------|----------|---------|--------------|
| `data_processing` | Yes | Required | No (service won't work) |
| `cookies_essential` | Yes | Required | No (session management) |
| `marketing_email` | No | Off | Yes |
| `marketing_sms` | No | Off | Yes |
| `marketing_phone` | No | Off | Yes |
| `analytics` | No | Off | Yes |
| `third_party_sharing` | No | Off | Yes |
| `cookies_analytics` | No | Off | Yes |
| `cookies_marketing` | No | Off | Yes |

### 3.2 Consent Records

Each consent record stores:

```json
{
  "tenant_id": "string",
  "email": "user@example.com",
  "consent_type": "marketing_email",
  "granted": true,
  "legal_basis": "consent",
  "source": "web",
  "ip_address": "192.168.1.1",
  "granted_at": "2025-01-09T10:30:00Z",
  "withdrawn_at": null
}
```

### 3.3 Consent Verification

```python
# Check consent before sending marketing emails
from src.tools.supabase_tool import SupabaseTool

def can_send_marketing_email(tenant_id: str, email: str) -> bool:
    supabase = SupabaseTool(config)
    result = supabase.client.rpc(
        'has_valid_consent',
        {'p_tenant_id': tenant_id, 'p_email': email, 'p_consent_type': 'marketing_email'}
    ).execute()
    return result.data
```

---

## 4. Data Processing Records

### 4.1 Audit Log Structure

All access to personal data is logged:

```json
{
  "tenant_id": "africastay",
  "user_id": "uuid",
  "user_email": "admin@africastay.com",
  "action": "view",
  "resource_type": "client",
  "resource_id": "client-uuid",
  "pii_fields_accessed": ["email", "name", "phone"],
  "ip_address": "192.168.1.1",
  "request_path": "/api/v1/crm/clients/client-uuid",
  "created_at": "2025-01-09T10:30:00Z"
}
```

### 4.2 Logged Actions

- `view` - Reading personal data
- `create` - Creating records with PII
- `update` - Modifying personal data
- `delete` - Removing personal data
- `export` - Downloading personal data
- `share` - Sharing data externally
- `anonymize` - Processing erasure requests

### 4.3 Audit Log Access

- **Retention:** 7 years (legal compliance)
- **Access:** Admin role only
- **Immutable:** Cannot be modified or deleted
- **Query Endpoint:** `GET /privacy/admin/audit-log`

---

## 5. Third-Party Processors

### 5.1 Sub-Processors

| Processor | Purpose | Data Shared | DPA Status |
|-----------|---------|-------------|------------|
| **Supabase** | Database, Auth | All data | EU Standard Clauses |
| **SendGrid** | Email delivery | email, name | DPA signed |
| **Google Cloud** | AI, BigQuery | Query patterns | DPA signed |
| **VAPI** (if enabled) | Voice AI | Phone, recordings | DPA signed |
| **Twilio** (if enabled) | Phone/SMS | Phone numbers | DPA signed |

### 5.2 Data Flow Diagram

```
User Browser ──► API Server ──► Supabase (Primary)
                    │
                    ├──► SendGrid (Email)
                    │
                    ├──► Google Cloud (AI/Analytics)
                    │
                    └──► VAPI/Twilio (Voice - if enabled)
```

### 5.3 Cross-Border Transfers

- **Primary data center:** EU (Supabase)
- **Analytics:** US (BigQuery with Standard Clauses)
- **Email:** US (SendGrid with DPA)

---

## 6. Security Measures

### 6.1 Technical Measures

| Measure | Implementation | Status |
|---------|---------------|--------|
| Encryption at rest | Supabase AES-256 | Active |
| Encryption in transit | TLS 1.3 | Active |
| Authentication | Supabase Auth + JWT | Active |
| Authorization | Row Level Security | Active |
| Rate limiting | Redis-based | Active |
| Input validation | Pydantic models | Active |
| SQL injection | Parameterized queries | Active |
| XSS prevention | Content-Type headers | Active |
| CORS | Whitelisted origins | Active |
| Tenant ID security | Cryptographic generation | Active |

### 6.2 Tenant Identifier Security

Tenant IDs are generated using cryptographically secure methods to prevent:
- **Enumeration attacks** - IDs cannot be guessed or predicted
- **Information disclosure** - Company names are not embedded in IDs
- **Correlation attacks** - IDs reveal no relationship between tenants

**Format:** `tn_{hash}_{random}`

```
Example: tn_a7f3b2c1_x9k2m4p7q1w3
         │  │        │
         │  │        └── 12-char cryptographically random (secrets.token_hex)
         │  └── 8-char SHA-256 hash (company + timestamp + salt)
         └── Prefix identifying tenant IDs
```

**Security Properties:**

| Property | Implementation |
|----------|---------------|
| Unpredictability | `secrets.token_hex()` - CSPRNG |
| Non-reversibility | SHA-256 hash with random salt |
| Uniqueness | Hash includes timestamp + salt |
| Collision resistance | 20 hex chars = 80 bits entropy |

**Code Reference:** `src/api/onboarding_routes.py:generate_tenant_id()`

### 6.3 Access Controls

| Role | CRM | Quotes | Invoices | Admin | Privacy |
|------|-----|--------|----------|-------|---------|
| User | Read own | Read own | Read own | No | Own data |
| Consultant | Full | Full | Full | No | Own data |
| Admin | Full | Full | Full | Yes | All |

### 6.4 Security Headers

```python
# Recommended headers (add to main.py)
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response
```

---

## 7. Data Retention

### 7.1 Retention Periods

| Data Type | Retention | Reason | Action After |
|-----------|-----------|--------|--------------|
| Quotes | 7 years | Tax compliance | Archive |
| Invoices | 7 years | Tax compliance | Archive |
| Client records | 7 years | Contract | Anonymize |
| Call recordings | 1 year | Quality assurance | Delete |
| Support tickets | 2 years | Service history | Anonymize |
| Audit logs | 7 years | Compliance | Archive |
| Notifications | 90 days | Housekeeping | Delete |

### 7.2 Automated Retention

Default retention policies are defined in migration `008_privacy_compliance.sql`:

```sql
INSERT INTO data_retention_policies (tenant_id, resource_type, retention_days, action_after_retention)
VALUES
    ('__default__', 'quote', 2555, 'archive'),
    ('__default__', 'invoice', 2555, 'archive'),
    ('__default__', 'client', 2555, 'anonymize'),
    ('__default__', 'call_record', 365, 'delete'),
    ('__default__', 'notification', 90, 'delete');
```

### 7.3 Data Anonymization

For erasure requests, PII is anonymized rather than deleted to preserve business records:

```python
def anonymize_client(client_id: str):
    """Anonymize PII while preserving record for reporting"""
    update = {
        "name": "REDACTED",
        "email": f"redacted-{uuid4()}@deleted.invalid",
        "phone": None,
        "notes": "Data subject exercised right to erasure",
        "is_anonymized": True,
        "anonymized_at": datetime.utcnow().isoformat()
    }
```

---

## 8. Breach Response

### 8.1 Breach Severity Levels

| Level | Definition | Response Time |
|-------|------------|---------------|
| **Low** | No PII exposed, technical issue only | 72 hours |
| **Medium** | Limited PII, contained quickly | 24 hours |
| **High** | Significant PII exposure | 4 hours |
| **Critical** | Mass PII exposure, ongoing | Immediate |

### 8.2 Response Procedure

```
1. DETECTION
   └── Automated monitoring or manual report

2. CONTAINMENT (within 1 hour)
   └── Stop breach, isolate affected systems

3. ASSESSMENT (within 4 hours)
   └── Scope, impact, affected individuals

4. NOTIFICATION (within 72 hours for high risk)
   ├── Information Regulator (POPIA) / DPA (GDPR)
   └── Affected data subjects (if high risk)

5. REMEDIATION
   └── Root cause analysis, fix, prevention

6. DOCUMENTATION
   └── Breach log entry, lessons learned
```

### 8.3 Breach Reporting

**South Africa (POPIA):**
- Information Regulator: inforeg@justice.gov.za
- Timeline: "As soon as reasonably possible"

**EU (GDPR):**
- Lead supervisory authority
- Timeline: 72 hours

### 8.4 Breach Log API

```bash
# Report a breach (admin only)
POST /privacy/admin/breach
{
  "breach_type": "confidentiality",
  "severity": "high",
  "description": "Unauthorized access to client database",
  "discovered_at": "2025-01-09T10:00:00Z",
  "affected_data_types": ["email", "phone"],
  "estimated_affected_count": 150
}
```

---

## 9. API Reference

### 9.1 User Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/privacy/consent` | GET | Get user's consent preferences |
| `/privacy/consent` | POST | Update a consent preference |
| `/privacy/consent/bulk` | POST | Update multiple consents |
| `/privacy/dsar` | GET | Get user's DSAR history |
| `/privacy/dsar` | POST | Submit new DSAR |
| `/privacy/dsar/{id}` | GET | Get DSAR status |
| `/privacy/export` | POST | Request data export |
| `/privacy/erasure` | POST | Request data erasure |

### 9.2 Admin Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/privacy/admin/dsars` | GET | List all DSARs |
| `/privacy/admin/dsar/{id}` | PATCH | Update DSAR status |
| `/privacy/admin/audit-log` | GET | View PII access logs |
| `/privacy/admin/breach` | POST | Report data breach |
| `/privacy/admin/breaches` | GET | List all breaches |

### 9.3 Example: Submit DSAR

```javascript
// Frontend
const response = await privacyApi.submitDSAR({
  request_type: 'access',  // access, erasure, portability, rectification, objection
  email: 'user@example.com',
  name: 'John Doe',
  details: 'I want to know what data you have about me'
});

// Response
{
  "success": true,
  "request_number": "DSAR-20250109-1234",
  "request_type": "access",
  "status": "pending",
  "due_date": "2025-02-08T10:30:00Z",
  "message": "Your access request has been submitted..."
}
```

---

## 10. Compliance Checklist

### 10.1 Initial Setup

- [ ] Run migration `008_privacy_compliance.sql`
- [ ] Enable PII audit middleware (`PII_AUDIT_ENABLED=true`)
- [ ] Configure retention policies per tenant
- [ ] Assign Data Protection Officer
- [ ] Set up breach notification contacts

### 10.2 Quarterly Review

- [ ] Review audit logs for anomalies
- [ ] Process pending DSARs
- [ ] Update data inventory if changed
- [ ] Review sub-processor agreements
- [ ] Test breach response procedure
- [ ] Update staff training records

### 10.3 Annual Tasks

- [ ] Full data protection impact assessment
- [ ] Review and update privacy policy
- [ ] Penetration testing
- [ ] Update compliance documentation
- [ ] Sub-processor audit

---

## Appendix A: Legal References

- **GDPR:** Regulation (EU) 2016/679
- **POPIA:** Act 4 of 2013 (South Africa)
- **CCPA:** California Consumer Privacy Act (if applicable)

## Appendix B: Contact Information

**Privacy Inquiries:**
privacy@[your-domain].com

**Data Protection Officer:**
[Name, Email, Phone]

**Breach Hotline:**
[Emergency contact]

---

*This document should be reviewed and approved by legal counsel before implementation.*
