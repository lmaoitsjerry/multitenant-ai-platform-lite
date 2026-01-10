-- ============================================
-- Notifications System
-- Run this in your Supabase SQL Editor
-- ============================================

-- ============================================
-- Table: notifications
-- Stores user notifications for real-time events
-- ============================================
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(50) NOT NULL,
    user_id UUID REFERENCES organization_users(id) ON DELETE CASCADE,

    -- Notification type (used for categorization and icons)
    type VARCHAR(50) NOT NULL CHECK (type IN (
        'quote_request',      -- New quote request received
        'email_received',     -- New email inquiry
        'invoice_paid',       -- Payment received
        'invoice_overdue',    -- Invoice past due date
        'booking_confirmed',  -- Booking confirmed
        'client_added',       -- New client added
        'team_invite',        -- Team member invitation
        'system',             -- System notification
        'mention'             -- User was mentioned
    )),

    -- Content
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,

    -- Related entity (for navigation)
    entity_type VARCHAR(50),  -- 'quote', 'invoice', 'client', 'email'
    entity_id VARCHAR(100),   -- ID of the related entity

    -- Metadata (for additional context)
    metadata JSONB DEFAULT '{}',

    -- Status
    read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- If user_id is NULL, notification is for all tenant users
    CONSTRAINT valid_notification CHECK (
        (user_id IS NOT NULL) OR (type IN ('system'))
    )
);

-- ============================================
-- Table: notification_preferences
-- User preferences for notification delivery
-- ============================================
CREATE TABLE IF NOT EXISTS notification_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(50) NOT NULL,
    user_id UUID NOT NULL REFERENCES organization_users(id) ON DELETE CASCADE,

    -- Email notification preferences (by type)
    email_quote_request BOOLEAN DEFAULT TRUE,
    email_email_received BOOLEAN DEFAULT TRUE,
    email_invoice_paid BOOLEAN DEFAULT TRUE,
    email_invoice_overdue BOOLEAN DEFAULT TRUE,
    email_booking_confirmed BOOLEAN DEFAULT TRUE,
    email_client_added BOOLEAN DEFAULT FALSE,  -- Default off for less important
    email_team_invite BOOLEAN DEFAULT TRUE,
    email_system BOOLEAN DEFAULT TRUE,
    email_mention BOOLEAN DEFAULT TRUE,

    -- Push notification preferences (future use)
    push_enabled BOOLEAN DEFAULT TRUE,

    -- Digest settings
    email_digest_enabled BOOLEAN DEFAULT FALSE,
    email_digest_frequency VARCHAR(20) DEFAULT 'daily' CHECK (email_digest_frequency IN ('realtime', 'hourly', 'daily', 'weekly')),

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(tenant_id, user_id)
);

-- ============================================
-- Indexes for Performance
-- ============================================

-- Fast lookup by tenant and user
CREATE INDEX IF NOT EXISTS idx_notifications_tenant_user
ON notifications(tenant_id, user_id, created_at DESC);

-- Fast lookup for unread notifications
CREATE INDEX IF NOT EXISTS idx_notifications_unread
ON notifications(tenant_id, user_id, read, created_at DESC)
WHERE read = FALSE;

-- Fast lookup by entity (for deduplication/linking)
CREATE INDEX IF NOT EXISTS idx_notifications_entity
ON notifications(tenant_id, entity_type, entity_id);

-- Preferences lookup
CREATE INDEX IF NOT EXISTS idx_notification_prefs_user
ON notification_preferences(tenant_id, user_id);

-- ============================================
-- Row Level Security
-- ============================================

ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE notification_preferences ENABLE ROW LEVEL SECURITY;

-- Service role has full access
CREATE POLICY "Service role full access to notifications" ON notifications
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role full access to notification_preferences" ON notification_preferences
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

-- Users can only see their own notifications
CREATE POLICY "Users see own notifications" ON notifications
    FOR SELECT TO authenticated
    USING (
        user_id = (SELECT id FROM organization_users WHERE auth_user_id = auth.uid() LIMIT 1)
        OR user_id IS NULL  -- System-wide notifications
    );

-- Users can update (mark read) their own notifications
CREATE POLICY "Users update own notifications" ON notifications
    FOR UPDATE TO authenticated
    USING (
        user_id = (SELECT id FROM organization_users WHERE auth_user_id = auth.uid() LIMIT 1)
    );

-- Users can manage their own preferences
CREATE POLICY "Users manage own preferences" ON notification_preferences
    FOR ALL TO authenticated
    USING (
        user_id = (SELECT id FROM organization_users WHERE auth_user_id = auth.uid() LIMIT 1)
    );

-- ============================================
-- Functions
-- ============================================

-- Function to create a notification
CREATE OR REPLACE FUNCTION create_notification(
    p_tenant_id VARCHAR(50),
    p_user_id UUID,
    p_type VARCHAR(50),
    p_title VARCHAR(255),
    p_message TEXT,
    p_entity_type VARCHAR(50) DEFAULT NULL,
    p_entity_id VARCHAR(100) DEFAULT NULL,
    p_metadata JSONB DEFAULT '{}'
)
RETURNS UUID AS $$
DECLARE
    v_notification_id UUID;
BEGIN
    INSERT INTO notifications (
        tenant_id, user_id, type, title, message,
        entity_type, entity_id, metadata
    ) VALUES (
        p_tenant_id, p_user_id, p_type, p_title, p_message,
        p_entity_type, p_entity_id, p_metadata
    )
    RETURNING id INTO v_notification_id;

    RETURN v_notification_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to create notifications for all tenant users
CREATE OR REPLACE FUNCTION create_tenant_notification(
    p_tenant_id VARCHAR(50),
    p_type VARCHAR(50),
    p_title VARCHAR(255),
    p_message TEXT,
    p_entity_type VARCHAR(50) DEFAULT NULL,
    p_entity_id VARCHAR(100) DEFAULT NULL,
    p_metadata JSONB DEFAULT '{}'
)
RETURNS INTEGER AS $$
DECLARE
    v_count INTEGER := 0;
    v_user RECORD;
BEGIN
    FOR v_user IN
        SELECT id FROM organization_users
        WHERE tenant_id = p_tenant_id AND is_active = TRUE
    LOOP
        PERFORM create_notification(
            p_tenant_id, v_user.id, p_type, p_title, p_message,
            p_entity_type, p_entity_id, p_metadata
        );
        v_count := v_count + 1;
    END LOOP;

    RETURN v_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to mark notifications as read
CREATE OR REPLACE FUNCTION mark_notifications_read(
    p_notification_ids UUID[]
)
RETURNS INTEGER AS $$
DECLARE
    v_count INTEGER;
BEGIN
    UPDATE notifications
    SET read = TRUE, read_at = NOW()
    WHERE id = ANY(p_notification_ids)
    AND read = FALSE;

    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get unread count
CREATE OR REPLACE FUNCTION get_unread_notification_count(
    p_tenant_id VARCHAR(50),
    p_user_id UUID
)
RETURNS INTEGER AS $$
BEGIN
    RETURN (
        SELECT COUNT(*)::INTEGER
        FROM notifications
        WHERE tenant_id = p_tenant_id
        AND (user_id = p_user_id OR user_id IS NULL)
        AND read = FALSE
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================
-- Trigger: Auto-update updated_at
-- ============================================

CREATE TRIGGER update_notification_preferences_updated_at
    BEFORE UPDATE ON notification_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- Default notification preferences on user creation
-- ============================================

CREATE OR REPLACE FUNCTION create_default_notification_preferences()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO notification_preferences (tenant_id, user_id)
    VALUES (NEW.tenant_id, NEW.id)
    ON CONFLICT (tenant_id, user_id) DO NOTHING;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER create_notification_prefs_on_user_create
    AFTER INSERT ON organization_users
    FOR EACH ROW
    EXECUTE FUNCTION create_default_notification_preferences();

-- ============================================
-- Verification
-- ============================================

-- Check tables were created
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('notifications', 'notification_preferences');
