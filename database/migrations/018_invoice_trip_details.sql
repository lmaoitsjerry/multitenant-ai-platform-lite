-- Migration: Add trip details columns to invoices table
-- These columns store travel-specific information from quotes

-- Add destination column
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS destination TEXT;

-- Add check-in date column
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS check_in TEXT;

-- Add check-out date column
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS check_out TEXT;

-- Add nights column
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS nights INTEGER;

-- Add customer_phone column if missing
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS customer_phone TEXT;

-- Add paid_amount column for tracking partial payments
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS paid_amount DECIMAL(12,2) DEFAULT 0;

-- Add paid_at timestamp
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS paid_at TIMESTAMPTZ;

-- Add payment_reference column
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS payment_reference TEXT;

-- Add updated_at column
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_invoices_destination ON invoices(destination);
CREATE INDEX IF NOT EXISTS idx_invoices_check_in ON invoices(check_in);
