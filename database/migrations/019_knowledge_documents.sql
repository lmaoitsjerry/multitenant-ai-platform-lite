-- Migration: Knowledge Documents Storage in Supabase
-- Moves tenant knowledge documents from filesystem to Supabase

-- Create knowledge_documents table
CREATE TABLE IF NOT EXISTS knowledge_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    document_id TEXT NOT NULL UNIQUE,
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_size INTEGER DEFAULT 0,
    storage_path TEXT,  -- Path in Supabase Storage bucket

    -- Metadata
    title TEXT,
    category TEXT DEFAULT 'general',
    tags TEXT[] DEFAULT '{}',
    visibility TEXT DEFAULT 'public' CHECK (visibility IN ('public', 'private')),

    -- Content for search (extracted text)
    content TEXT,
    content_chunks JSONB DEFAULT '[]',
    chunk_count INTEGER DEFAULT 0,

    -- Status
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'indexed', 'error')),
    error_message TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    indexed_at TIMESTAMPTZ,

    -- Constraints
    CONSTRAINT fk_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);

-- Create indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_knowledge_docs_tenant ON knowledge_documents(tenant_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_docs_category ON knowledge_documents(category);
CREATE INDEX IF NOT EXISTS idx_knowledge_docs_status ON knowledge_documents(status);
CREATE INDEX IF NOT EXISTS idx_knowledge_docs_visibility ON knowledge_documents(visibility);
CREATE INDEX IF NOT EXISTS idx_knowledge_docs_created ON knowledge_documents(created_at DESC);

-- Full-text search index on content
CREATE INDEX IF NOT EXISTS idx_knowledge_docs_content_search
ON knowledge_documents USING gin(to_tsvector('english', COALESCE(content, '')));

-- RLS policies
ALTER TABLE knowledge_documents ENABLE ROW LEVEL SECURITY;

-- Tenants can only see their own documents
CREATE POLICY knowledge_documents_tenant_isolation ON knowledge_documents
    FOR ALL
    USING (tenant_id = current_setting('app.tenant_id', true));

-- Create storage bucket for knowledge documents (run in Supabase dashboard or via API)
-- Note: Storage bucket creation typically done via Supabase dashboard:
-- 1. Go to Storage in Supabase dashboard
-- 2. Create bucket named 'knowledge-documents'
-- 3. Set it to private (authenticated access only)

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_knowledge_docs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for updated_at
DROP TRIGGER IF EXISTS trigger_knowledge_docs_updated_at ON knowledge_documents;
CREATE TRIGGER trigger_knowledge_docs_updated_at
    BEFORE UPDATE ON knowledge_documents
    FOR EACH ROW
    EXECUTE FUNCTION update_knowledge_docs_updated_at();

-- Comment
COMMENT ON TABLE knowledge_documents IS 'Tenant knowledge base documents for RAG/helpdesk';
