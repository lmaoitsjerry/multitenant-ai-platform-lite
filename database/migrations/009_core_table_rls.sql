-- Migration: 009_core_table_rls.sql
-- Row Level Security for Core Business Tables
-- Adds defense-in-depth tenant isolation
-- Created: January 2025

-- ============================================================
-- OVERVIEW
-- ============================================================
-- This migration adds RLS policies to core business tables that
-- previously relied solely on code-level tenant filtering.
--
-- The backend uses service_role key, so these policies provide
-- defense-in-depth rather than primary access control.
--
-- Tables covered:
-- - quotes
-- - invoices
-- - invoice_travelers
-- - clients
-- - activities
-- - call_records
-- - outbound_call_queue
-- - inbound_tickets
-- - helpdesk_sessions
-- ============================================================


-- ============================================================
-- QUOTES TABLE
-- ============================================================

ALTER TABLE quotes ENABLE ROW LEVEL SECURITY;

-- Service role (backend) has full access
CREATE POLICY "Service role full access to quotes" ON quotes
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

-- Authenticated users can only access their tenant's quotes
CREATE POLICY "Tenant isolation for quotes" ON quotes
    FOR ALL TO authenticated
    USING (
        tenant_id::text IN (
            SELECT ou.tenant_id::text FROM organization_users ou
            WHERE ou.auth_user_id = auth.uid()
        )
    )
    WITH CHECK (
        tenant_id::text IN (
            SELECT ou.tenant_id::text FROM organization_users ou
            WHERE ou.auth_user_id = auth.uid()
        )
    );


-- ============================================================
-- INVOICES TABLE
-- ============================================================

ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;

-- Service role (backend) has full access
CREATE POLICY "Service role full access to invoices" ON invoices
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

-- Authenticated users can only access their tenant's invoices
CREATE POLICY "Tenant isolation for invoices" ON invoices
    FOR ALL TO authenticated
    USING (
        tenant_id::text IN (
            SELECT ou.tenant_id::text FROM organization_users ou
            WHERE ou.auth_user_id = auth.uid()
        )
    )
    WITH CHECK (
        tenant_id::text IN (
            SELECT ou.tenant_id::text FROM organization_users ou
            WHERE ou.auth_user_id = auth.uid()
        )
    );


-- ============================================================
-- INVOICE_TRAVELERS TABLE
-- ============================================================

-- Check if table exists before enabling RLS
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'invoice_travelers') THEN
        ALTER TABLE invoice_travelers ENABLE ROW LEVEL SECURITY;
    END IF;
END $$;

-- Service role (backend) has full access
CREATE POLICY "Service role full access to invoice_travelers" ON invoice_travelers
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

-- Authenticated users can only access travelers on their tenant's invoices
CREATE POLICY "Tenant isolation for invoice_travelers" ON invoice_travelers
    FOR ALL TO authenticated
    USING (
        invoice_id IN (
            SELECT id FROM invoices
            WHERE tenant_id::text IN (
                SELECT ou.tenant_id::text FROM organization_users ou
                WHERE ou.auth_user_id = auth.uid()
            )
        )
    )
    WITH CHECK (
        invoice_id IN (
            SELECT id FROM invoices
            WHERE tenant_id::text IN (
                SELECT ou.tenant_id::text FROM organization_users ou
                WHERE ou.auth_user_id = auth.uid()
            )
        )
    );


-- ============================================================
-- CLIENTS TABLE
-- ============================================================

ALTER TABLE clients ENABLE ROW LEVEL SECURITY;

-- Service role (backend) has full access
CREATE POLICY "Service role full access to clients" ON clients
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

-- Authenticated users can only access their tenant's clients
CREATE POLICY "Tenant isolation for clients" ON clients
    FOR ALL TO authenticated
    USING (
        tenant_id::text IN (
            SELECT ou.tenant_id::text FROM organization_users ou
            WHERE ou.auth_user_id = auth.uid()
        )
    )
    WITH CHECK (
        tenant_id::text IN (
            SELECT ou.tenant_id::text FROM organization_users ou
            WHERE ou.auth_user_id = auth.uid()
        )
    );


-- ============================================================
-- ACTIVITIES TABLE
-- ============================================================

ALTER TABLE activities ENABLE ROW LEVEL SECURITY;

-- Service role (backend) has full access
CREATE POLICY "Service role full access to activities" ON activities
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

-- Authenticated users can only access their tenant's activities
CREATE POLICY "Tenant isolation for activities" ON activities
    FOR ALL TO authenticated
    USING (
        tenant_id::text IN (
            SELECT ou.tenant_id::text FROM organization_users ou
            WHERE ou.auth_user_id = auth.uid()
        )
    )
    WITH CHECK (
        tenant_id::text IN (
            SELECT ou.tenant_id::text FROM organization_users ou
            WHERE ou.auth_user_id = auth.uid()
        )
    );


-- ============================================================
-- CALL_RECORDS TABLE
-- ============================================================

-- Check if table exists before enabling RLS
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'call_records') THEN
        ALTER TABLE call_records ENABLE ROW LEVEL SECURITY;
    END IF;
END $$;

CREATE POLICY "Service role full access to call_records" ON call_records
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Tenant isolation for call_records" ON call_records
    FOR ALL TO authenticated
    USING (
        tenant_id::text IN (
            SELECT ou.tenant_id::text FROM organization_users ou
            WHERE ou.auth_user_id = auth.uid()
        )
    )
    WITH CHECK (
        tenant_id::text IN (
            SELECT ou.tenant_id::text FROM organization_users ou
            WHERE ou.auth_user_id = auth.uid()
        )
    );


-- ============================================================
-- OUTBOUND_CALL_QUEUE TABLE
-- ============================================================

-- Check if table exists before enabling RLS
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'outbound_call_queue') THEN
        ALTER TABLE outbound_call_queue ENABLE ROW LEVEL SECURITY;
    END IF;
END $$;

CREATE POLICY "Service role full access to outbound_call_queue" ON outbound_call_queue
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Tenant isolation for outbound_call_queue" ON outbound_call_queue
    FOR ALL TO authenticated
    USING (
        tenant_id::text IN (
            SELECT ou.tenant_id::text FROM organization_users ou
            WHERE ou.auth_user_id = auth.uid()
        )
    )
    WITH CHECK (
        tenant_id::text IN (
            SELECT ou.tenant_id::text FROM organization_users ou
            WHERE ou.auth_user_id = auth.uid()
        )
    );


-- ============================================================
-- INBOUND_TICKETS TABLE
-- ============================================================

-- Check if table exists before enabling RLS
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'inbound_tickets') THEN
        ALTER TABLE inbound_tickets ENABLE ROW LEVEL SECURITY;
    END IF;
END $$;

CREATE POLICY "Service role full access to inbound_tickets" ON inbound_tickets
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Tenant isolation for inbound_tickets" ON inbound_tickets
    FOR ALL TO authenticated
    USING (
        tenant_id::text IN (
            SELECT ou.tenant_id::text FROM organization_users ou
            WHERE ou.auth_user_id = auth.uid()
        )
    )
    WITH CHECK (
        tenant_id::text IN (
            SELECT ou.tenant_id::text FROM organization_users ou
            WHERE ou.auth_user_id = auth.uid()
        )
    );


-- ============================================================
-- HELPDESK_SESSIONS TABLE
-- ============================================================

-- Check if table exists before enabling RLS
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'helpdesk_sessions') THEN
        ALTER TABLE helpdesk_sessions ENABLE ROW LEVEL SECURITY;
    END IF;
END $$;

CREATE POLICY "Service role full access to helpdesk_sessions" ON helpdesk_sessions
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Tenant isolation for helpdesk_sessions" ON helpdesk_sessions
    FOR ALL TO authenticated
    USING (
        tenant_id::text IN (
            SELECT ou.tenant_id::text FROM organization_users ou
            WHERE ou.auth_user_id = auth.uid()
        )
    )
    WITH CHECK (
        tenant_id::text IN (
            SELECT ou.tenant_id::text FROM organization_users ou
            WHERE ou.auth_user_id = auth.uid()
        )
    );


-- ============================================================
-- KNOWLEDGE_DOCUMENTS TABLE (if exists)
-- ============================================================

-- Check if table exists before enabling RLS
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'knowledge_documents') THEN
        ALTER TABLE knowledge_documents ENABLE ROW LEVEL SECURITY;
    END IF;
END $$;

CREATE POLICY "Service role full access to knowledge_documents" ON knowledge_documents
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Tenant isolation for knowledge_documents" ON knowledge_documents
    FOR ALL TO authenticated
    USING (
        tenant_id::text IN (
            SELECT ou.tenant_id::text FROM organization_users ou
            WHERE ou.auth_user_id = auth.uid()
        )
    )
    WITH CHECK (
        tenant_id::text IN (
            SELECT ou.tenant_id::text FROM organization_users ou
            WHERE ou.auth_user_id = auth.uid()
        )
    );


-- ============================================================
-- VERIFICATION QUERIES (run separately after migration)
-- ============================================================
--
-- Check RLS is enabled:
-- SELECT schemaname, tablename, rowsecurity
-- FROM pg_tables
-- WHERE schemaname = 'public'
--   AND tablename IN (
--     'quotes', 'invoices', 'invoice_travelers', 'clients',
--     'activities', 'call_records', 'outbound_call_queue',
--     'inbound_tickets', 'helpdesk_sessions', 'knowledge_documents'
--   );
--
-- View all policies:
-- SELECT tablename, policyname, permissive, roles, cmd, qual
-- FROM pg_policies
-- WHERE schemaname = 'public'
-- ORDER BY tablename, policyname;
