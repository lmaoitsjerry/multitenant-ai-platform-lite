-- Add SendGrid subuser credential columns to tenant_settings
-- Run this in the Supabase SQL Editor
--
-- These columns store per-tenant SendGrid subuser credentials.
-- API keys are provisioned automatically during onboarding and loaded
-- at runtime by EmailSender (DB takes priority over YAML config).

ALTER TABLE tenant_settings ADD COLUMN IF NOT EXISTS sendgrid_api_key TEXT;
ALTER TABLE tenant_settings ADD COLUMN IF NOT EXISTS sendgrid_username TEXT;

-- Populate existing tenant subuser usernames
UPDATE tenant_settings SET sendgrid_username = 'africastay' WHERE tenant_id = 'africastay';
UPDATE tenant_settings SET sendgrid_username = 'beachresorts' WHERE tenant_id = 'beachresorts';
UPDATE tenant_settings SET sendgrid_username = 'safariexplorekvph' WHERE tenant_id = 'safariexplore-kvph';
UPDATE tenant_settings SET sendgrid_username = 'safarirunt0vc' WHERE tenant_id = 'safarirun-t0vc';

-- Populate existing tenant API keys (subuser-specific keys created earlier)
-- IMPORTANT: Run these manually with real keys — never commit keys to version control.
-- UPDATE tenant_settings SET sendgrid_api_key = '<africastay-subuser-key>' WHERE tenant_id = 'africastay';
-- UPDATE tenant_settings SET sendgrid_api_key = '<beachresorts-subuser-key>' WHERE tenant_id = 'beachresorts';
-- UPDATE tenant_settings SET sendgrid_api_key = '<safariexplore-subuser-key>' WHERE tenant_id = 'safariexplore-kvph';
-- UPDATE tenant_settings SET sendgrid_api_key = '<safarirun-subuser-key>' WHERE tenant_id = 'safarirun-t0vc';

-- Update email_from_email for platform domain users (Gmail users get @holidaytoday.co.za)
UPDATE tenant_settings SET email_from_email = 'safarirun@holidaytoday.co.za' WHERE tenant_id = 'safarirun-t0vc';

-- Set reply_to addresses (where replies should go)
UPDATE tenant_settings SET email_reply_to = 'sales@holidaytoday.co.za' WHERE tenant_id = 'africastay';
UPDATE tenant_settings SET email_reply_to = 'info@beachresorts.co.za' WHERE tenant_id = 'beachresorts';
UPDATE tenant_settings SET email_reply_to = 'demo@africastay.com' WHERE tenant_id = 'safariexplore-kvph';
UPDATE tenant_settings SET email_reply_to = 'jerry.akwenyu@gmail.com' WHERE tenant_id = 'safarirun-t0vc';
