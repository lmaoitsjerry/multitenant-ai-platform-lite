import { describe, it, expect } from 'vitest';
import {
  snakeToCamel,
  camelToSnake,
  transformKeysSnakeToCamel,
  transformKeysCamelToSnake,
  normalizeQuoteStatus,
  normalizeHotelPrice,
  normalizeActivityPrice,
  normalizeTransferPrice,
  serializeCrmActivity,
  normalizeQuoteDates,
  serializeQuoteToInvoice,
  normalizeKbSource,
  serializeNotificationPrefs,
} from './fieldTransformers';

// --- Case Converters ---

describe('snakeToCamel', () => {
  it('converts simple snake_case', () => {
    expect(snakeToCamel('hello_world')).toBe('helloWorld');
  });

  it('converts multi-segment snake_case', () => {
    expect(snakeToCamel('check_in_date')).toBe('checkInDate');
  });

  it('returns already camelCase unchanged', () => {
    expect(snakeToCamel('helloWorld')).toBe('helloWorld');
  });

  it('handles single word', () => {
    expect(snakeToCamel('hello')).toBe('hello');
  });
});

describe('camelToSnake', () => {
  it('converts simple camelCase', () => {
    expect(camelToSnake('helloWorld')).toBe('hello_world');
  });

  it('converts multi-hump camelCase', () => {
    expect(camelToSnake('checkInDate')).toBe('check_in_date');
  });

  it('returns already snake_case unchanged', () => {
    expect(camelToSnake('hello_world')).toBe('hello_world');
  });

  it('handles single word', () => {
    expect(camelToSnake('hello')).toBe('hello');
  });
});

describe('transformKeysSnakeToCamel', () => {
  it('transforms flat object keys', () => {
    expect(transformKeysSnakeToCamel({ check_in_date: '2025-01-01', total_price: 100 }))
      .toEqual({ checkInDate: '2025-01-01', totalPrice: 100 });
  });

  it('transforms nested object keys', () => {
    const input = { hotel_name: 'Beach', room_info: { room_type: 'Deluxe' } };
    const output = transformKeysSnakeToCamel(input);
    expect(output.hotelName).toBe('Beach');
    expect(output.roomInfo.roomType).toBe('Deluxe');
  });

  it('transforms arrays of objects', () => {
    const input = [{ first_name: 'A' }, { first_name: 'B' }];
    const output = transformKeysSnakeToCamel(input);
    expect(output).toEqual([{ firstName: 'A' }, { firstName: 'B' }]);
  });

  it('handles null and primitives', () => {
    expect(transformKeysSnakeToCamel(null)).toBeNull();
    expect(transformKeysSnakeToCamel(42)).toBe(42);
    expect(transformKeysSnakeToCamel('hello')).toBe('hello');
  });
});

describe('transformKeysCamelToSnake', () => {
  it('transforms flat object keys', () => {
    expect(transformKeysCamelToSnake({ checkInDate: '2025-01-01', totalPrice: 100 }))
      .toEqual({ check_in_date: '2025-01-01', total_price: 100 });
  });

  it('handles null and primitives', () => {
    expect(transformKeysCamelToSnake(null)).toBeNull();
    expect(transformKeysCamelToSnake(42)).toBe(42);
  });
});

// --- Quote Status Normalizer (M2) ---

describe('normalizeQuoteStatus', () => {
  it('normalizes "Draft" to "draft"', () => {
    expect(normalizeQuoteStatus('Draft')).toBe('draft');
  });

  it('normalizes "DRAFT" to "draft"', () => {
    expect(normalizeQuoteStatus('DRAFT')).toBe('draft');
  });

  it('normalizes "generated" to "quoted"', () => {
    expect(normalizeQuoteStatus('generated')).toBe('quoted');
  });

  it('normalizes "Quoted" to "quoted"', () => {
    expect(normalizeQuoteStatus('Quoted')).toBe('quoted');
  });

  it('normalizes "rejected" to "declined"', () => {
    expect(normalizeQuoteStatus('rejected')).toBe('declined');
  });

  it('normalizes "Accepted" to "accepted"', () => {
    expect(normalizeQuoteStatus('Accepted')).toBe('accepted');
  });

  it('normalizes "Converted" to "converted"', () => {
    expect(normalizeQuoteStatus('Converted')).toBe('converted');
  });

  it('lowercases unknown statuses', () => {
    expect(normalizeQuoteStatus('PENDING')).toBe('pending');
  });

  it('returns "draft" for null/undefined', () => {
    expect(normalizeQuoteStatus(null)).toBe('draft');
    expect(normalizeQuoteStatus(undefined)).toBe('draft');
    expect(normalizeQuoteStatus('')).toBe('draft');
  });

  it('passes through already-canonical values', () => {
    expect(normalizeQuoteStatus('sent')).toBe('sent');
    expect(normalizeQuoteStatus('viewed')).toBe('viewed');
  });
});

// --- Hotel Price Normalizer (M9) ---

describe('normalizeHotelPrice', () => {
  it('uses rate_per_night as primary', () => {
    expect(normalizeHotelPrice({ rate_per_night: 150 })).toEqual({ ratePerNight: 150 });
  });

  it('falls back to price_per_night', () => {
    expect(normalizeHotelPrice({ price_per_night: 200 })).toEqual({ ratePerNight: 200 });
  });

  it('falls back to nightly_rate', () => {
    expect(normalizeHotelPrice({ nightly_rate: 180 })).toEqual({ ratePerNight: 180 });
  });

  it('calculates from total_price and nights', () => {
    expect(normalizeHotelPrice({ total_price: 700 }, 7)).toEqual({ ratePerNight: 100 });
  });

  it('falls back to net_price', () => {
    expect(normalizeHotelPrice({ net_price: 120 })).toEqual({ ratePerNight: 120 });
  });

  it('returns 0 for empty hotel', () => {
    expect(normalizeHotelPrice({})).toEqual({ ratePerNight: 0 });
  });

  it('prioritizes rate_per_night over fallbacks', () => {
    expect(normalizeHotelPrice({ rate_per_night: 150, price_per_night: 200, total_price: 1000 }))
      .toEqual({ ratePerNight: 150 });
  });
});

// --- Activity Price Normalizer (M7) ---

describe('normalizeActivityPrice', () => {
  it('uses price_per_person as primary', () => {
    expect(normalizeActivityPrice({ price_per_person: 50 })).toEqual({ pricePerPerson: 50 });
  });

  it('falls back to price_adult', () => {
    expect(normalizeActivityPrice({ price_adult: 45 })).toEqual({ pricePerPerson: 45 });
  });

  it('falls back to price', () => {
    expect(normalizeActivityPrice({ price: 30 })).toEqual({ pricePerPerson: 30 });
  });

  it('returns 0 for empty activity', () => {
    expect(normalizeActivityPrice({})).toEqual({ pricePerPerson: 0 });
  });

  it('prioritizes price_per_person over fallbacks', () => {
    expect(normalizeActivityPrice({ price_per_person: 50, price_adult: 45, price: 30 }))
      .toEqual({ pricePerPerson: 50 });
  });
});

// --- Transfer Price Normalizer (M8) ---

describe('normalizeTransferPrice', () => {
  it('extracts price and defaults to per_transfer', () => {
    expect(normalizeTransferPrice({ price: 25 })).toEqual({ price: 25, pricingModel: 'per_transfer' });
  });

  it('falls back to price_per_transfer', () => {
    expect(normalizeTransferPrice({ price_per_transfer: 30 })).toEqual({ price: 30, pricingModel: 'per_transfer' });
  });

  it('detects per_person pricing model', () => {
    expect(normalizeTransferPrice({ price: 15, price_per_person: 15 }))
      .toEqual({ price: 15, pricingModel: 'per_person' });
  });

  it('uses explicit pricing_model', () => {
    expect(normalizeTransferPrice({ price: 20, pricing_model: 'per_person' }))
      .toEqual({ price: 20, pricingModel: 'per_person' });
  });

  it('returns 0 for empty transfer', () => {
    expect(normalizeTransferPrice({})).toEqual({ price: 0, pricingModel: 'per_transfer' });
  });
});

// --- CRM Activity Serializer (C2) ---

describe('serializeCrmActivity', () => {
  it('maps activityType and description', () => {
    expect(serializeCrmActivity({ activityType: 'call', description: 'Called client' }))
      .toEqual({ activity_type: 'call', description: 'Called client' });
  });

  it('falls back from type to activity_type', () => {
    expect(serializeCrmActivity({ type: 'email', note: 'Sent email' }))
      .toEqual({ activity_type: 'email', description: 'Sent email' });
  });

  it('defaults to note type and empty description', () => {
    expect(serializeCrmActivity({})).toEqual({ activity_type: 'note', description: '' });
  });
});

// --- Quote Date Normalizer (C4) ---

describe('normalizeQuoteDates', () => {
  it('prefers check_in over check_in_date', () => {
    const result = normalizeQuoteDates({ check_in: '2025-06-01', check_in_date: '2025-05-01' });
    expect(result.check_in).toBe('2025-06-01');
  });

  it('falls back to check_in_date when check_in is missing', () => {
    const result = normalizeQuoteDates({ check_in_date: '2025-06-01', check_out_date: '2025-06-08' });
    expect(result.check_in).toBe('2025-06-01');
    expect(result.check_out).toBe('2025-06-08');
  });

  it('returns null when no date fields exist', () => {
    const result = normalizeQuoteDates({ destination: 'Zanzibar' });
    expect(result.check_in).toBeNull();
    expect(result.check_out).toBeNull();
  });

  it('preserves other fields', () => {
    const result = normalizeQuoteDates({ destination: 'Zanzibar', check_in: '2025-06-01' });
    expect(result.destination).toBe('Zanzibar');
    expect(result.check_in).toBe('2025-06-01');
  });
});

// --- Invoice Serializer (M43, M44) ---

describe('serializeQuoteToInvoice', () => {
  it('converts due_date string to due_days integer', () => {
    const futureDate = new Date();
    futureDate.setDate(futureDate.getDate() + 14);
    const result = serializeQuoteToInvoice({ due_date: futureDate.toISOString() });
    expect(result.due_days).toBeGreaterThanOrEqual(13);
    expect(result.due_days).toBeLessThanOrEqual(15);
    expect(result.due_date).toBeUndefined();
  });

  it('defaults to 30 days when no due info', () => {
    const result = serializeQuoteToInvoice({});
    expect(result.due_days).toBe(30);
  });

  it('preserves existing due_days', () => {
    const result = serializeQuoteToInvoice({ due_days: 7 });
    expect(result.due_days).toBe(7);
  });

  it('ensures minimum 1 day', () => {
    const pastDate = new Date();
    pastDate.setDate(pastDate.getDate() - 5);
    const result = serializeQuoteToInvoice({ due_date: pastDate.toISOString() });
    expect(result.due_days).toBe(1);
  });
});

// --- KB Source Normalizer (C6, M20) ---

describe('normalizeKbSource', () => {
  it('uses title when present', () => {
    expect(normalizeKbSource({ title: 'My Doc', score: 0.9 }))
      .toEqual(expect.objectContaining({ title: 'My Doc', relevanceScore: 0.9 }));
  });

  it('falls back from filename to title', () => {
    const result = normalizeKbSource({ filename: 'doc.pdf', score: 0.8 });
    expect(result.title).toBe('doc.pdf');
  });

  it('falls back from topic to title', () => {
    const result = normalizeKbSource({ topic: 'Zanzibar Hotels' });
    expect(result.title).toBe('Zanzibar Hotels');
  });

  it('defaults to Untitled', () => {
    const result = normalizeKbSource({});
    expect(result.title).toBe('Untitled');
  });

  it('uses relevance_score when present', () => {
    const result = normalizeKbSource({ relevance_score: 0.95 });
    expect(result.relevanceScore).toBe(0.95);
  });

  it('falls back from score to relevanceScore', () => {
    const result = normalizeKbSource({ score: 0.7 });
    expect(result.relevanceScore).toBe(0.7);
  });

  it('defaults relevanceScore to 0', () => {
    const result = normalizeKbSource({});
    expect(result.relevanceScore).toBe(0);
  });
});

// --- Notification Preferences Serializer (C9, M25) ---

describe('serializeNotificationPrefs', () => {
  it('maps camelCase prefs to snake_case', () => {
    const result = serializeNotificationPrefs({
      emailNewQuote: true,
      emailNewInquiry: false,
      emailInvoiceOverdue: true,
      dailyDigest: false,
    });
    expect(result).toEqual({
      email_quote_request: true,
      email_email_received: false,
      email_invoice_overdue: true,
      email_digest_enabled: false,
    });
  });

  it('falls back to snake_case field names', () => {
    const result = serializeNotificationPrefs({
      email_quote_request: false,
      email_email_received: true,
      email_invoice_overdue: false,
      email_digest_enabled: true,
    });
    expect(result).toEqual({
      email_quote_request: false,
      email_email_received: true,
      email_invoice_overdue: false,
      email_digest_enabled: true,
    });
  });

  it('defaults to sensible values', () => {
    const result = serializeNotificationPrefs({});
    expect(result).toEqual({
      email_quote_request: true,
      email_email_received: true,
      email_invoice_overdue: true,
      email_digest_enabled: false,
    });
  });
});
