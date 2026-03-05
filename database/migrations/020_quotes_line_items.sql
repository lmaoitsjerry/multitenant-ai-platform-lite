-- Migration 020: Add shopping cart columns to quotes table
-- These columns support the create-with-items endpoint (shopping cart flow).
-- Uses IF NOT EXISTS so it's safe to re-run.

ALTER TABLE quotes ADD COLUMN IF NOT EXISTS line_items JSONB;
ALTER TABLE quotes ADD COLUMN IF NOT EXISTS totals_by_currency JSONB;
ALTER TABLE quotes ADD COLUMN IF NOT EXISTS total_amount NUMERIC;
ALTER TABLE quotes ADD COLUMN IF NOT EXISTS currency TEXT DEFAULT 'ZAR';
ALTER TABLE quotes ADD COLUMN IF NOT EXISTS source TEXT;
