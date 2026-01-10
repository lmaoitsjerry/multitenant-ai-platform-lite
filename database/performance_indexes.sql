-- Performance Indexes for Multi-Tenant AI Platform
-- Run these in Supabase SQL Editor to improve query performance

-- ==================== Core Tables ====================

-- Quotes table indexes
CREATE INDEX IF NOT EXISTS idx_quotes_tenant ON quotes(tenant_id);
CREATE INDEX IF NOT EXISTS idx_quotes_tenant_created ON quotes(tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_quotes_status ON quotes(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_quotes_client_email ON quotes(tenant_id, client_email);
CREATE INDEX IF NOT EXISTS idx_quotes_quote_id ON quotes(quote_id);

-- Invoices table indexes
CREATE INDEX IF NOT EXISTS idx_invoices_tenant ON invoices(tenant_id);
CREATE INDEX IF NOT EXISTS idx_invoices_tenant_created ON invoices(tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_invoices_quote_id ON invoices(quote_id);
CREATE INDEX IF NOT EXISTS idx_invoices_client_email ON invoices(tenant_id, client_email);

-- CRM Clients table indexes
CREATE INDEX IF NOT EXISTS idx_crm_clients_tenant ON crm_clients(tenant_id);
CREATE INDEX IF NOT EXISTS idx_crm_clients_email ON crm_clients(tenant_id, email);
CREATE INDEX IF NOT EXISTS idx_crm_clients_stage ON crm_clients(tenant_id, pipeline_stage);
CREATE INDEX IF NOT EXISTS idx_crm_clients_consultant ON crm_clients(tenant_id, consultant_id);

-- Call History table indexes
CREATE INDEX IF NOT EXISTS idx_call_history_tenant ON call_history(tenant_id);
CREATE INDEX IF NOT EXISTS idx_call_history_tenant_created ON call_history(tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_call_history_status ON call_history(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_call_history_customer_phone ON call_history(tenant_id, customer_phone);

-- Support Tickets (Inbound) table indexes
CREATE INDEX IF NOT EXISTS idx_support_tickets_tenant ON support_tickets(tenant_id);
CREATE INDEX IF NOT EXISTS idx_support_tickets_status ON support_tickets(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_support_tickets_created ON support_tickets(tenant_id, created_at DESC);

-- ==================== User & Auth Tables ====================

-- Organization Users indexes
CREATE INDEX IF NOT EXISTS idx_org_users_tenant ON organization_users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_org_users_auth ON organization_users(auth_user_id);
CREATE INDEX IF NOT EXISTS idx_org_users_email ON organization_users(tenant_id, email);
CREATE INDEX IF NOT EXISTS idx_org_users_role ON organization_users(tenant_id, role);

-- User Invitations indexes
CREATE INDEX IF NOT EXISTS idx_invitations_tenant ON user_invitations(tenant_id);
CREATE INDEX IF NOT EXISTS idx_invitations_email ON user_invitations(tenant_id, email);
CREATE INDEX IF NOT EXISTS idx_invitations_token ON user_invitations(invitation_token);

-- ==================== Knowledge Base ====================

-- Knowledge documents indexes
CREATE INDEX IF NOT EXISTS idx_knowledge_docs_tenant ON knowledge_documents(tenant_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_docs_visibility ON knowledge_documents(tenant_id, visibility);
CREATE INDEX IF NOT EXISTS idx_knowledge_docs_category ON knowledge_documents(tenant_id, category);

-- ==================== Branding & Settings ====================

-- Branding indexes
CREATE INDEX IF NOT EXISTS idx_branding_tenant ON tenant_branding(tenant_id);

-- ==================== Performance Tracking ====================

-- Leaderboard/Performance indexes (for consultant performance queries)
CREATE INDEX IF NOT EXISTS idx_quotes_consultant ON quotes(tenant_id, consultant_id);
CREATE INDEX IF NOT EXISTS idx_invoices_consultant ON invoices(tenant_id, consultant_id);
CREATE INDEX IF NOT EXISTS idx_invoices_paid ON invoices(tenant_id, status) WHERE status = 'paid';

-- ==================== Helpdesk ====================

-- Helpdesk sessions indexes
CREATE INDEX IF NOT EXISTS idx_helpdesk_sessions_tenant ON helpdesk_sessions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_helpdesk_sessions_employee ON helpdesk_sessions(tenant_id, employee_email);

-- Helpdesk messages indexes
CREATE INDEX IF NOT EXISTS idx_helpdesk_messages_session ON helpdesk_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_helpdesk_messages_created ON helpdesk_messages(session_id, created_at);

-- ==================== Composite Indexes for Common Queries ====================

-- For dashboard stats queries
CREATE INDEX IF NOT EXISTS idx_quotes_tenant_status_created ON quotes(tenant_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_invoices_tenant_status_created ON invoices(tenant_id, status, created_at DESC);

-- For leaderboard period queries
CREATE INDEX IF NOT EXISTS idx_invoices_tenant_paid_date ON invoices(tenant_id, paid_at) WHERE status = 'paid';

-- ==================== Full Text Search Indexes ====================

-- For searching quotes by destination or client name
-- Note: Requires pg_trgm extension
-- CREATE EXTENSION IF NOT EXISTS pg_trgm;
-- CREATE INDEX IF NOT EXISTS idx_quotes_destination_trgm ON quotes USING GIN (destination gin_trgm_ops);
-- CREATE INDEX IF NOT EXISTS idx_quotes_client_name_trgm ON quotes USING GIN (client_name gin_trgm_ops);

-- ==================== Verification ====================

-- Run this to check your indexes were created:
-- SELECT indexname, indexdef FROM pg_indexes WHERE tablename IN ('quotes', 'invoices', 'crm_clients', 'call_history') ORDER BY tablename, indexname;
