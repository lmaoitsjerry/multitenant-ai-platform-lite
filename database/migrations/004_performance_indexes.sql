-- Migration: Performance Indexes for Production
-- Date: 2025-01-07
-- Description: Adds indexes to optimize common query patterns for the multi-tenant platform
--
-- These indexes improve performance for:
-- - Dashboard stats queries
-- - Quote/Invoice analytics
-- - CRM pipeline queries
-- - Call analytics
-- - Date range filtering (common pattern across all queries)

-- =====================================================
-- QUOTES TABLE INDEXES
-- =====================================================

-- Composite index for tenant + date range queries (most common query pattern)
CREATE INDEX IF NOT EXISTS idx_quotes_tenant_created
    ON quotes(tenant_id, created_at DESC);

-- Index for status filtering
CREATE INDEX IF NOT EXISTS idx_quotes_status
    ON quotes(status);

-- Composite index for tenant + status queries
CREATE INDEX IF NOT EXISTS idx_quotes_tenant_status
    ON quotes(tenant_id, status);

-- =====================================================
-- INVOICES TABLE INDEXES
-- =====================================================

-- Composite index for tenant + date range queries
CREATE INDEX IF NOT EXISTS idx_invoices_tenant_created
    ON invoices(tenant_id, created_at DESC);

-- Index for status filtering
CREATE INDEX IF NOT EXISTS idx_invoices_status
    ON invoices(status);

-- Composite index for tenant + status queries (common for aging reports)
CREATE INDEX IF NOT EXISTS idx_invoices_tenant_status
    ON invoices(tenant_id, status);

-- Index for due date (aging calculations)
CREATE INDEX IF NOT EXISTS idx_invoices_due_date
    ON invoices(due_date);

-- =====================================================
-- CLIENTS TABLE INDEXES
-- =====================================================

-- Composite index for tenant + date range queries
CREATE INDEX IF NOT EXISTS idx_clients_tenant_created
    ON clients(tenant_id, created_at DESC);

-- Index for pipeline stage filtering
CREATE INDEX IF NOT EXISTS idx_clients_pipeline_stage
    ON clients(pipeline_stage);

-- Composite index for tenant + pipeline queries
CREATE INDEX IF NOT EXISTS idx_clients_tenant_stage
    ON clients(tenant_id, pipeline_stage);

-- =====================================================
-- CALL_RECORDS TABLE INDEXES
-- =====================================================

-- Composite index for tenant + date range queries
CREATE INDEX IF NOT EXISTS idx_call_records_tenant_created
    ON call_records(tenant_id, created_at DESC);

-- Index for call status filtering
CREATE INDEX IF NOT EXISTS idx_call_records_status
    ON call_records(call_status);

-- Composite index for tenant + status queries
CREATE INDEX IF NOT EXISTS idx_call_records_tenant_status
    ON call_records(tenant_id, call_status);

-- =====================================================
-- OUTBOUND_CALL_QUEUE TABLE INDEXES
-- =====================================================

-- Index for tenant filtering
CREATE INDEX IF NOT EXISTS idx_call_queue_tenant
    ON outbound_call_queue(tenant_id);

-- Index for status filtering
CREATE INDEX IF NOT EXISTS idx_call_queue_status
    ON outbound_call_queue(call_status);

-- Composite index for tenant + status queries (for queue management)
CREATE INDEX IF NOT EXISTS idx_call_queue_tenant_status
    ON outbound_call_queue(tenant_id, call_status);

-- Index for scheduled time (for scheduling queries)
CREATE INDEX IF NOT EXISTS idx_call_queue_scheduled
    ON outbound_call_queue(scheduled_for)
    WHERE scheduled_for IS NOT NULL;

-- =====================================================
-- ACTIVITIES TABLE INDEXES
-- =====================================================

-- Composite index for tenant + date ordering (for recent activities)
CREATE INDEX IF NOT EXISTS idx_activities_tenant_created
    ON activities(tenant_id, created_at DESC);

-- Index for client filtering
CREATE INDEX IF NOT EXISTS idx_activities_client
    ON activities(client_id);

-- =====================================================
-- KNOWLEDGE_BASE TABLE INDEXES (if exists)
-- =====================================================

-- These may fail if table doesn't exist - that's OK
DO $$
BEGIN
    CREATE INDEX IF NOT EXISTS idx_knowledge_tenant
        ON knowledge_base(tenant_id);
EXCEPTION WHEN undefined_table THEN
    RAISE NOTICE 'knowledge_base table does not exist - skipping index';
END $$;

-- =====================================================
-- VERIFICATION QUERY
-- =====================================================
-- Run this to verify indexes were created:
-- SELECT tablename, indexname FROM pg_indexes
-- WHERE schemaname = 'public'
-- AND indexname LIKE 'idx_%'
-- ORDER BY tablename, indexname;
