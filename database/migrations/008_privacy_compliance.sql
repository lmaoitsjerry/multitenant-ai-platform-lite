-- Migration: 008_privacy_compliance.sql
-- GDPR/POPIA Privacy Compliance Infrastructure
-- Created: 2025-01-09

-- ============================================================
-- CONSENT RECORDS
-- Track user consent for data processing activities
-- ============================================================
CREATE TABLE IF NOT EXISTS consent_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,

    -- Subject identification
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    email TEXT NOT NULL,

    -- Consent details
    consent_type TEXT NOT NULL CHECK (consent_type IN (
        'marketing_email',
        'marketing_sms',
        'marketing_phone',
        'data_processing',
        'third_party_sharing',
        'analytics',
        'cookies_essential',
        'cookies_functional',
        'cookies_analytics',
        'cookies_marketing'
    )),
    granted BOOLEAN NOT NULL DEFAULT false,

    -- Legal basis (GDPR Article 6)
    legal_basis TEXT CHECK (legal_basis IN (
        'consent',
        'contract',
        'legal_obligation',
        'vital_interests',
        'public_task',
        'legitimate_interests'
    )),

    -- Consent metadata
    consent_version TEXT,
    consent_text TEXT,
    source TEXT NOT NULL DEFAULT 'web' CHECK (source IN (
        'web', 'mobile', 'email', 'phone', 'in_person', 'api'
    )),
    ip_address INET,
    user_agent TEXT,

    -- Timestamps
    granted_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    withdrawn_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Ensure unique consent per type per email per tenant
    UNIQUE(tenant_id, email, consent_type)
);

-- Index for lookups
CREATE INDEX idx_consent_tenant_email ON consent_records(tenant_id, email);
CREATE INDEX idx_consent_type ON consent_records(consent_type, granted);
CREATE INDEX idx_consent_expiry ON consent_records(expires_at) WHERE expires_at IS NOT NULL;

-- RLS for tenant isolation
ALTER TABLE consent_records ENABLE ROW LEVEL SECURITY;

CREATE POLICY consent_tenant_isolation ON consent_records
    FOR ALL USING (
        tenant_id = current_setting('app.tenant_id', true)
        OR current_setting('app.is_admin', true) = 'true'
    );


-- ============================================================
-- DATA SUBJECT REQUESTS (DSAR)
-- Handle GDPR Article 15-22 rights requests
-- ============================================================
CREATE TABLE IF NOT EXISTS data_subject_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,

    -- Request identification
    request_number TEXT NOT NULL,

    -- Subject identification
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    email TEXT NOT NULL,
    name TEXT,

    -- Request details
    request_type TEXT NOT NULL CHECK (request_type IN (
        'access',           -- Right of access (Art. 15)
        'rectification',    -- Right to rectification (Art. 16)
        'erasure',          -- Right to erasure (Art. 17)
        'restriction',      -- Right to restriction (Art. 18)
        'portability',      -- Right to data portability (Art. 20)
        'objection',        -- Right to object (Art. 21)
        'automated_decision' -- Automated decision-making (Art. 22)
    )),

    -- Status tracking
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN (
        'pending',
        'verified',
        'in_progress',
        'completed',
        'rejected',
        'cancelled'
    )),

    -- Identity verification
    verification_method TEXT CHECK (verification_method IN (
        'email', 'phone', 'document', 'in_person', 'existing_account'
    )),
    verified_at TIMESTAMPTZ,
    verified_by UUID REFERENCES auth.users(id),

    -- Request handling
    assigned_to UUID REFERENCES auth.users(id),
    notes TEXT,
    rejection_reason TEXT,

    -- Data export (for access/portability requests)
    export_file_url TEXT,
    export_generated_at TIMESTAMPTZ,
    export_expires_at TIMESTAMPTZ,

    -- Compliance deadlines (30 days under GDPR/POPIA)
    due_date TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(tenant_id, request_number)
);

-- Generate request number function
CREATE OR REPLACE FUNCTION generate_dsar_number()
RETURNS TRIGGER AS $$
BEGIN
    NEW.request_number := 'DSAR-' || TO_CHAR(NOW(), 'YYYYMMDD') || '-' ||
                          LPAD(FLOOR(RANDOM() * 10000)::TEXT, 4, '0');
    NEW.due_date := NOW() + INTERVAL '30 days';
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_dsar_number
    BEFORE INSERT ON data_subject_requests
    FOR EACH ROW
    WHEN (NEW.request_number IS NULL)
    EXECUTE FUNCTION generate_dsar_number();

-- Indexes
CREATE INDEX idx_dsar_tenant ON data_subject_requests(tenant_id);
CREATE INDEX idx_dsar_email ON data_subject_requests(email);
CREATE INDEX idx_dsar_status ON data_subject_requests(status, due_date);
CREATE INDEX idx_dsar_due_date ON data_subject_requests(due_date) WHERE status NOT IN ('completed', 'rejected', 'cancelled');

-- RLS
ALTER TABLE data_subject_requests ENABLE ROW LEVEL SECURITY;

CREATE POLICY dsar_tenant_isolation ON data_subject_requests
    FOR ALL USING (
        tenant_id = current_setting('app.tenant_id', true)
        OR current_setting('app.is_admin', true) = 'true'
    );


-- ============================================================
-- DATA AUDIT LOG
-- Track all access to personal data for compliance
-- ============================================================
CREATE TABLE IF NOT EXISTS data_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,

    -- Actor information
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    user_email TEXT,
    user_role TEXT,

    -- Action details
    action TEXT NOT NULL CHECK (action IN (
        'view',
        'create',
        'update',
        'delete',
        'export',
        'share',
        'anonymize'
    )),

    -- Target information
    resource_type TEXT NOT NULL,  -- 'client', 'quote', 'invoice', etc.
    resource_id TEXT,

    -- Data details
    pii_fields_accessed TEXT[],   -- Array of field names accessed
    old_values JSONB,             -- Previous values (for updates)
    new_values JSONB,             -- New values (for creates/updates)

    -- Request context
    ip_address INET,
    user_agent TEXT,
    request_path TEXT,
    request_method TEXT,

    -- Additional context
    reason TEXT,                  -- Business justification if required
    dsar_id UUID REFERENCES data_subject_requests(id),

    -- Timestamp (immutable)
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Partitioning for large audit logs (optional, by month)
-- Note: Enable if log volume is high
-- CREATE TABLE data_audit_log_2025_01 PARTITION OF data_audit_log
--     FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

-- Indexes for audit queries
CREATE INDEX idx_audit_tenant ON data_audit_log(tenant_id, created_at DESC);
CREATE INDEX idx_audit_user ON data_audit_log(user_id, created_at DESC);
CREATE INDEX idx_audit_resource ON data_audit_log(resource_type, resource_id);
CREATE INDEX idx_audit_action ON data_audit_log(action, created_at DESC);
CREATE INDEX idx_audit_pii ON data_audit_log USING GIN(pii_fields_accessed);

-- RLS
ALTER TABLE data_audit_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY audit_tenant_isolation ON data_audit_log
    FOR ALL USING (
        tenant_id = current_setting('app.tenant_id', true)
        OR current_setting('app.is_admin', true) = 'true'
    );

-- Prevent updates/deletes on audit log (immutable)
CREATE POLICY audit_immutable ON data_audit_log
    FOR UPDATE USING (false);

CREATE POLICY audit_no_delete ON data_audit_log
    FOR DELETE USING (false);


-- ============================================================
-- DATA RETENTION POLICIES
-- Define how long data should be retained per type
-- ============================================================
CREATE TABLE IF NOT EXISTS data_retention_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,

    -- Policy definition
    resource_type TEXT NOT NULL,  -- 'client', 'quote', 'invoice', 'call_record', etc.
    retention_days INTEGER NOT NULL,

    -- Policy details
    description TEXT,
    legal_basis TEXT,             -- Why this retention period

    -- Actions after retention
    action_after_retention TEXT NOT NULL DEFAULT 'anonymize' CHECK (action_after_retention IN (
        'delete',
        'anonymize',
        'archive'
    )),

    -- Exclusions
    exclude_if_active BOOLEAN DEFAULT true,  -- Don't delete active records
    exclude_conditions JSONB,      -- Custom exclusion rules

    -- Policy status
    is_active BOOLEAN DEFAULT true,

    -- Audit
    created_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(tenant_id, resource_type)
);

-- RLS
ALTER TABLE data_retention_policies ENABLE ROW LEVEL SECURITY;

CREATE POLICY retention_tenant_isolation ON data_retention_policies
    FOR ALL USING (
        tenant_id = current_setting('app.tenant_id', true)
        OR current_setting('app.is_admin', true) = 'true'
    );

-- Insert default retention policies
INSERT INTO data_retention_policies (tenant_id, resource_type, retention_days, description, legal_basis, action_after_retention) VALUES
    ('__default__', 'quote', 2555, 'Quotes retained for 7 years for tax compliance', 'legal_obligation', 'archive'),
    ('__default__', 'invoice', 2555, 'Invoices retained for 7 years for tax compliance', 'legal_obligation', 'archive'),
    ('__default__', 'client', 2555, 'Client records retained for 7 years (or until erasure request)', 'contract', 'anonymize'),
    ('__default__', 'call_record', 365, 'Call records retained for 1 year', 'legitimate_interests', 'delete'),
    ('__default__', 'support_ticket', 730, 'Support tickets retained for 2 years', 'contract', 'anonymize'),
    ('__default__', 'audit_log', 2555, 'Audit logs retained for 7 years for compliance', 'legal_obligation', 'archive'),
    ('__default__', 'notification', 90, 'Notifications deleted after 90 days', 'legitimate_interests', 'delete')
ON CONFLICT DO NOTHING;


-- ============================================================
-- DATA BREACH LOG
-- Document security incidents as required by GDPR Article 33
-- ============================================================
CREATE TABLE IF NOT EXISTS data_breach_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,

    -- Breach identification
    breach_number TEXT NOT NULL,

    -- Breach details
    breach_type TEXT NOT NULL CHECK (breach_type IN (
        'confidentiality',    -- Unauthorized disclosure
        'integrity',          -- Unauthorized modification
        'availability'        -- Loss of access
    )),
    severity TEXT NOT NULL CHECK (severity IN (
        'low',
        'medium',
        'high',
        'critical'
    )),

    -- Timing
    discovered_at TIMESTAMPTZ NOT NULL,
    occurred_at TIMESTAMPTZ,
    contained_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,

    -- Impact assessment
    description TEXT NOT NULL,
    affected_data_types TEXT[],   -- ['email', 'phone', 'passport']
    estimated_affected_count INTEGER,
    actual_affected_count INTEGER,

    -- Risk assessment
    risk_to_individuals TEXT CHECK (risk_to_individuals IN (
        'unlikely',
        'possible',
        'likely',
        'certain'
    )),

    -- Notifications (GDPR requires within 72 hours)
    authority_notified BOOLEAN DEFAULT false,
    authority_notified_at TIMESTAMPTZ,
    authority_reference TEXT,

    subjects_notified BOOLEAN DEFAULT false,
    subjects_notified_at TIMESTAMPTZ,
    notification_method TEXT,

    -- Response
    immediate_actions TEXT,
    root_cause TEXT,
    remediation_steps TEXT,
    preventive_measures TEXT,

    -- Documentation
    reported_by UUID REFERENCES auth.users(id),
    handled_by UUID REFERENCES auth.users(id),
    attachments JSONB,            -- File references

    -- Status
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN (
        'open',
        'investigating',
        'contained',
        'resolved',
        'closed'
    )),

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(tenant_id, breach_number)
);

-- Generate breach number
CREATE OR REPLACE FUNCTION generate_breach_number()
RETURNS TRIGGER AS $$
BEGIN
    NEW.breach_number := 'BREACH-' || TO_CHAR(NOW(), 'YYYYMMDD') || '-' ||
                         LPAD(FLOOR(RANDOM() * 1000)::TEXT, 3, '0');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_breach_number
    BEFORE INSERT ON data_breach_log
    FOR EACH ROW
    WHEN (NEW.breach_number IS NULL)
    EXECUTE FUNCTION generate_breach_number();

-- Indexes
CREATE INDEX idx_breach_tenant ON data_breach_log(tenant_id);
CREATE INDEX idx_breach_status ON data_breach_log(status, severity);
CREATE INDEX idx_breach_date ON data_breach_log(discovered_at DESC);

-- RLS
ALTER TABLE data_breach_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY breach_tenant_isolation ON data_breach_log
    FOR ALL USING (
        tenant_id = current_setting('app.tenant_id', true)
        OR current_setting('app.is_admin', true) = 'true'
    );


-- ============================================================
-- HELPER FUNCTIONS
-- ============================================================

-- Function to check if user has valid consent
CREATE OR REPLACE FUNCTION has_valid_consent(
    p_tenant_id TEXT,
    p_email TEXT,
    p_consent_type TEXT
) RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM consent_records
        WHERE tenant_id = p_tenant_id
          AND email = p_email
          AND consent_type = p_consent_type
          AND granted = true
          AND withdrawn_at IS NULL
          AND (expires_at IS NULL OR expires_at > NOW())
    );
END;
$$ LANGUAGE plpgsql STABLE;

-- Function to get all consents for a user
CREATE OR REPLACE FUNCTION get_user_consents(
    p_tenant_id TEXT,
    p_email TEXT
) RETURNS TABLE (
    consent_type TEXT,
    granted BOOLEAN,
    granted_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        cr.consent_type,
        cr.granted AND cr.withdrawn_at IS NULL AND (cr.expires_at IS NULL OR cr.expires_at > NOW()),
        cr.granted_at,
        cr.expires_at
    FROM consent_records cr
    WHERE cr.tenant_id = p_tenant_id
      AND cr.email = p_email;
END;
$$ LANGUAGE plpgsql STABLE;

-- Function to log PII access
CREATE OR REPLACE FUNCTION log_pii_access(
    p_tenant_id TEXT,
    p_user_id UUID,
    p_user_email TEXT,
    p_action TEXT,
    p_resource_type TEXT,
    p_resource_id TEXT,
    p_pii_fields TEXT[],
    p_ip_address INET DEFAULT NULL,
    p_user_agent TEXT DEFAULT NULL
) RETURNS UUID AS $$
DECLARE
    v_log_id UUID;
BEGIN
    INSERT INTO data_audit_log (
        tenant_id, user_id, user_email, action,
        resource_type, resource_id, pii_fields_accessed,
        ip_address, user_agent
    ) VALUES (
        p_tenant_id, p_user_id, p_user_email, p_action,
        p_resource_type, p_resource_id, p_pii_fields,
        p_ip_address, p_user_agent
    )
    RETURNING id INTO v_log_id;

    RETURN v_log_id;
END;
$$ LANGUAGE plpgsql;


-- ============================================================
-- UPDATE TRIGGERS
-- ============================================================

CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_consent_updated
    BEFORE UPDATE ON consent_records
    FOR EACH ROW EXECUTE FUNCTION update_modified_column();

CREATE TRIGGER tr_dsar_updated
    BEFORE UPDATE ON data_subject_requests
    FOR EACH ROW EXECUTE FUNCTION update_modified_column();

CREATE TRIGGER tr_retention_updated
    BEFORE UPDATE ON data_retention_policies
    FOR EACH ROW EXECUTE FUNCTION update_modified_column();

CREATE TRIGGER tr_breach_updated
    BEFORE UPDATE ON data_breach_log
    FOR EACH ROW EXECUTE FUNCTION update_modified_column();


-- ============================================================
-- GRANTS
-- ============================================================
GRANT ALL ON consent_records TO authenticated;
GRANT ALL ON data_subject_requests TO authenticated;
GRANT ALL ON data_audit_log TO authenticated;
GRANT ALL ON data_retention_policies TO authenticated;
GRANT ALL ON data_breach_log TO authenticated;
