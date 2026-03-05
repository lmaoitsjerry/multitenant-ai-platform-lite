-- Additional Performance Indexes for Multi-Tenant AI Platform
-- Run these in Supabase SQL Editor AFTER the main performance_indexes.sql
-- These indexes address specific performance bottlenecks identified in the audit

-- ============================================
-- Leaderboard Query Optimization
-- ============================================

-- For consultant leaderboard queries that filter by paid status and date range
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_invoices_leaderboard
ON invoices(tenant_id, consultant_id, status, created_at)
WHERE status = 'paid';

-- ============================================
-- Analytics Query Optimization
-- ============================================

-- For analytics dashboard date range queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_quotes_analytics
ON quotes(tenant_id, created_at DESC, status);

-- For revenue analytics by consultant
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_invoices_revenue_analytics
ON invoices(tenant_id, consultant_id, paid_at, total_amount)
WHERE status = 'paid';

-- ============================================
-- Count Query Optimization
-- ============================================

-- For faster ticket counting without full table scan
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_support_tickets_count
ON support_tickets(tenant_id, status);

-- For faster quote status counting
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_quotes_status_count
ON quotes(tenant_id, status);

-- ============================================
-- Active Records Partial Indexes
-- ============================================

-- For CRM pipeline view - only show active deals
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_crm_clients_active_pipeline
ON crm_clients(tenant_id, pipeline_stage, updated_at DESC)
WHERE pipeline_stage NOT IN ('LOST', 'TRAVELLED');

-- For pending invoices dashboard widget
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_invoices_pending
ON invoices(tenant_id, created_at DESC)
WHERE status IN ('pending', 'sent');

-- ============================================
-- Text Search Optimization
-- ============================================

-- Enable trigram extension for fuzzy text search (if not already enabled)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- For searching quotes by customer name
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_quotes_customer_name_trgm
ON quotes USING GIN (customer_name gin_trgm_ops);

-- For searching clients by name
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_crm_clients_name_trgm
ON crm_clients USING GIN (name gin_trgm_ops);

-- ============================================
-- Update Table Statistics
-- ============================================

-- Force statistics update for query planner optimization
ANALYZE quotes;
ANALYZE invoices;
ANALYZE crm_clients;
ANALYZE support_tickets;
ANALYZE organization_users;
ANALYZE tenant_branding;

-- ============================================
-- Verification Queries
-- ============================================

-- Run these to verify indexes were created successfully:
/*
SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_indexes
WHERE tablename IN ('quotes', 'invoices', 'crm_clients', 'support_tickets')
AND schemaname = 'public'
ORDER BY tablename, indexname;
*/

-- Check for unused indexes (run after a few days of usage):
/*
SELECT
    schemaname,
    relname,
    indexrelname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
AND idx_scan = 0
ORDER BY relname;
*/
