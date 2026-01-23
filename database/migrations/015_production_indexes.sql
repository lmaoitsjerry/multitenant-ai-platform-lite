-- Migration: Production Performance Indexes
-- Date: 2026-01-23
-- Phase: 16 - Critical Fixes
-- Description: Adds composite indexes for CRM batch queries and common production patterns

-- =====================================================
-- QUOTES TABLE INDEXES (for CRM batch enrichment)
-- =====================================================

-- Composite index for batch quote lookup by tenant + customer_email
-- Used by CRM search_clients batch query
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_quotes_tenant_customer_email
    ON quotes(tenant_id, customer_email, created_at DESC);

-- =====================================================
-- ACTIVITIES TABLE INDEXES (for CRM batch enrichment)
-- =====================================================

-- Composite index for batch activity lookup by tenant + client_id
-- Used by CRM search_clients batch query
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_activities_tenant_client_created
    ON activities(tenant_id, client_id, created_at DESC);

-- =====================================================
-- CLIENTS TABLE INDEXES (for CRM search)
-- =====================================================

-- Composite index for client email lookup (used in CRM deduplication)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_clients_tenant_email
    ON clients(tenant_id, email);

-- =====================================================
-- INVOICES TABLE INDEXES (additional for reporting)
-- =====================================================

-- Composite index for invoice lookup by tenant + status + date
-- Used by financial reports
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_invoices_tenant_status_created
    ON invoices(tenant_id, status, created_at DESC);

-- =====================================================
-- VERIFICATION
-- =====================================================
-- Run this to verify indexes were created:
/*
SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_indexes
WHERE indexname IN (
    'idx_quotes_tenant_customer_email',
    'idx_activities_tenant_client_created',
    'idx_clients_tenant_email',
    'idx_invoices_tenant_status_created'
)
ORDER BY tablename, indexname;
*/

-- Update statistics for query planner
ANALYZE quotes;
ANALYZE activities;
ANALYZE clients;
ANALYZE invoices;
