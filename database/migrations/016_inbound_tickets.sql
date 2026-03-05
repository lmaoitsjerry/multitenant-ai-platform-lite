-- Migration: Create inbound_tickets table for enquiry triage
-- This table stores customer enquiries from email, web, phone, chat sources

-- Create inbound_tickets table
CREATE TABLE IF NOT EXISTS inbound_tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    ticket_id TEXT NOT NULL UNIQUE,
    customer_name VARCHAR(255),
    customer_email VARCHAR(255) NOT NULL,
    subject TEXT,
    message TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'in_progress', 'resolved', 'closed')),
    priority VARCHAR(10) NOT NULL DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    source VARCHAR(10) NOT NULL DEFAULT 'email' CHECK (source IN ('web', 'email', 'phone', 'chat')),
    assigned_to VARCHAR(255),
    notes TEXT,
    metadata JSONB DEFAULT '{}',
    conversation JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_inbound_tickets_tenant ON inbound_tickets(tenant_id);
CREATE INDEX IF NOT EXISTS idx_inbound_tickets_status ON inbound_tickets(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_inbound_tickets_created ON inbound_tickets(tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_inbound_tickets_email ON inbound_tickets(customer_email);

-- Enable RLS
ALTER TABLE inbound_tickets ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Service role has full access
DROP POLICY IF EXISTS inbound_tickets_service_policy ON inbound_tickets;
CREATE POLICY inbound_tickets_service_policy ON inbound_tickets
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- RLS Policy: Authenticated users can only access their tenant's tickets
DROP POLICY IF EXISTS inbound_tickets_tenant_policy ON inbound_tickets;
CREATE POLICY inbound_tickets_tenant_policy ON inbound_tickets
    FOR ALL
    TO authenticated
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

-- Comment on table
COMMENT ON TABLE inbound_tickets IS 'Customer enquiries from email, web, phone, and chat sources';
COMMENT ON COLUMN inbound_tickets.ticket_id IS 'Human-readable ticket ID: TKT-YYYYMMDD-XXXXXX';
COMMENT ON COLUMN inbound_tickets.conversation IS 'Array of {role, content, timestamp} message objects';
COMMENT ON COLUMN inbound_tickets.metadata IS 'Parsed travel details, source info, etc.';
