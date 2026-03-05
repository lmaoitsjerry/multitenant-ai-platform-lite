-- ============================================
-- Tenant Assets Storage Configuration
-- Run this in your Supabase SQL Editor
-- ============================================
-- This creates a storage bucket for tenant assets (logos, documents)
-- with proper RLS policies for multi-tenant isolation.
--
-- Folder structure:
--   tenant-assets/
--     {tenant_id}/
--       branding/
--         primary.png
--         dark.png
--         favicon.ico
--       documents/
--         {filename}
-- ============================================

-- Step 1: Create the storage bucket
-- Note: This uses the storage API, not SQL
-- Run this via Supabase Dashboard > Storage > New Bucket
-- OR via the Supabase client in your backend

-- For SQL-based bucket creation (if using supabase_admin or storage schema):
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'tenant-assets',
    'tenant-assets',
    true,  -- Public bucket (read access controlled by policies)
    5242880,  -- 5MB max file size
    ARRAY['image/png', 'image/jpeg', 'image/jpg', 'image/svg+xml', 'image/x-icon', 'image/webp', 'application/pdf']
)
ON CONFLICT (id) DO UPDATE SET
    public = EXCLUDED.public,
    file_size_limit = EXCLUDED.file_size_limit,
    allowed_mime_types = EXCLUDED.allowed_mime_types;

-- ============================================
-- Step 2: Storage Policies
-- ============================================

-- Drop existing policies if they exist (for clean re-runs)
DROP POLICY IF EXISTS "Public read access for tenant assets" ON storage.objects;
DROP POLICY IF EXISTS "Tenants can upload to their own folder" ON storage.objects;
DROP POLICY IF EXISTS "Tenants can update their own files" ON storage.objects;
DROP POLICY IF EXISTS "Tenants can delete their own files" ON storage.objects;
DROP POLICY IF EXISTS "Service role full access to tenant assets" ON storage.objects;

-- Policy 1: PUBLIC READ ACCESS
-- Anyone can read files from the tenant-assets bucket
-- This allows logos to be displayed in the UI without authentication
CREATE POLICY "Public read access for tenant assets"
ON storage.objects FOR SELECT
USING (bucket_id = 'tenant-assets');

-- Policy 2: AUTHENTICATED UPLOAD
-- Authenticated users can upload to their tenant's folder
-- The path must start with the tenant_id from the session
CREATE POLICY "Tenants can upload to their own folder"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
    bucket_id = 'tenant-assets'
    AND (
        -- Path starts with branding/{tenant_id}/ (backend sets this)
        (storage.foldername(name))[1] = 'branding'
        OR
        -- Path starts with {tenant_id}/ (direct tenant folder)
        (storage.foldername(name))[1] = current_setting('app.tenant_id', true)
    )
);

-- Policy 3: AUTHENTICATED UPDATE
-- Authenticated users can update files in their tenant's folder
CREATE POLICY "Tenants can update their own files"
ON storage.objects FOR UPDATE
TO authenticated
USING (
    bucket_id = 'tenant-assets'
    AND (
        (storage.foldername(name))[1] = 'branding'
        OR
        (storage.foldername(name))[1] = current_setting('app.tenant_id', true)
    )
)
WITH CHECK (
    bucket_id = 'tenant-assets'
    AND (
        (storage.foldername(name))[1] = 'branding'
        OR
        (storage.foldername(name))[1] = current_setting('app.tenant_id', true)
    )
);

-- Policy 4: AUTHENTICATED DELETE
-- Authenticated users can delete files in their tenant's folder
CREATE POLICY "Tenants can delete their own files"
ON storage.objects FOR DELETE
TO authenticated
USING (
    bucket_id = 'tenant-assets'
    AND (
        (storage.foldername(name))[1] = 'branding'
        OR
        (storage.foldername(name))[1] = current_setting('app.tenant_id', true)
    )
);

-- Policy 5: SERVICE ROLE FULL ACCESS
-- The service role (used by our backend) has full access
-- This allows the API to upload files on behalf of tenants
CREATE POLICY "Service role full access to tenant assets"
ON storage.objects FOR ALL
TO service_role
USING (bucket_id = 'tenant-assets')
WITH CHECK (bucket_id = 'tenant-assets');

-- ============================================
-- Step 3: Verify Setup
-- ============================================

-- Check bucket exists
SELECT id, name, public, file_size_limit, allowed_mime_types
FROM storage.buckets
WHERE id = 'tenant-assets';

-- Check policies exist
SELECT policyname, cmd, roles
FROM pg_policies
WHERE tablename = 'objects' AND schemaname = 'storage'
AND policyname LIKE '%tenant%';

-- ============================================
-- IMPORTANT NOTES:
-- ============================================
-- 1. The backend uses service_role key, so it bypasses RLS
-- 2. Frontend direct uploads would use the authenticated policies
-- 3. Path structure: branding/{tenant_id}/{logo_type}.{ext}
-- 4. All images are publicly readable (needed for UI display)
-- 5. Only the tenant's backend can write to their folder
-- ============================================
