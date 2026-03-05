// ============================================================
// fieldTransformers.js
// Central field name mapping for the entire platform.
// All API responses pass through normalizers here.
// All API requests pass through serializers here.
// ============================================================

// --- Case converters ---

export function snakeToCamel(str) {
  return str.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
}

export function camelToSnake(str) {
  return str.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`);
}

export function transformKeysSnakeToCamel(obj) {
  if (Array.isArray(obj)) return obj.map(transformKeysSnakeToCamel);
  if (obj !== null && typeof obj === 'object' && !(obj instanceof Date)) {
    return Object.fromEntries(
      Object.entries(obj).map(([key, value]) => [
        snakeToCamel(key),
        transformKeysSnakeToCamel(value),
      ])
    );
  }
  return obj;
}

export function transformKeysCamelToSnake(obj) {
  if (Array.isArray(obj)) return obj.map(transformKeysCamelToSnake);
  if (obj !== null && typeof obj === 'object' && !(obj instanceof Date)) {
    return Object.fromEntries(
      Object.entries(obj).map(([key, value]) => [
        camelToSnake(key),
        transformKeysCamelToSnake(value),
      ])
    );
  }
  return obj;
}

// --- Quote Status Normalizer (fixes M2) ---

const QUOTE_STATUS_MAP = {
  'Draft': 'draft',
  'DRAFT': 'draft',
  'generated': 'quoted',
  'Quoted': 'quoted',
  'Accepted': 'accepted',
  'Declined': 'declined',
  'rejected': 'declined',
  'Expired': 'expired',
  'Converted': 'converted',
};

export function normalizeQuoteStatus(status) {
  if (!status) return 'draft';
  return QUOTE_STATUS_MAP[status] || status.toLowerCase();
}

// --- Hotel Price Normalizer (fixes M9) ---

export function normalizeHotelPrice(hotel, nights = 1) {
  const perNight =
    hotel.rate_per_night ??
    hotel.price_per_night ??
    hotel.nightly_rate ??
    (hotel.total_price && nights > 0 ? hotel.total_price / nights : null) ??
    hotel.net_price ??
    0;
  return { ratePerNight: Number(perNight) || 0 };
}

// --- Activity Price Normalizer (fixes M7) ---

export function normalizeActivityPrice(activity) {
  const pricePerPerson =
    activity.price_per_person ??
    activity.price_adult ??
    activity.price ??
    0;
  return { pricePerPerson: Number(pricePerPerson) || 0 };
}

// --- Transfer Price Normalizer (fixes M8) ---

export function normalizeTransferPrice(transfer) {
  const price = transfer.price ?? transfer.price_per_transfer ?? 0;
  const pricingModel = transfer.pricing_model ??
    (transfer.price_per_person !== undefined ? 'per_person' : 'per_transfer');
  return {
    price: Number(price) || 0,
    pricingModel,
  };
}

// --- CRM Activity Serializer (fixes C2) ---

export function serializeCrmActivity(data) {
  return {
    activity_type: data.activityType || data.activity_type || data.type || 'note',
    description: data.description || data.note || data.content || '',
  };
}

// --- Quote Date Normalizer (fixes C4) ---

export function normalizeQuoteDates(quote) {
  return {
    ...quote,
    check_in: quote.check_in ?? quote.check_in_date ?? null,
    check_out: quote.check_out ?? quote.check_out_date ?? null,
  };
}

// --- Invoice Serializer (fixes M43, M44) ---

export function serializeQuoteToInvoice(quoteData) {
  const normalized = { ...quoteData };

  // Convert due_date string to due_days integer
  if (typeof normalized.due_date === 'string' && !normalized.due_days) {
    const dueDate = new Date(normalized.due_date);
    const now = new Date();
    const diffMs = dueDate - now;
    const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));
    normalized.due_days = Math.max(diffDays, 1);
    delete normalized.due_date;
  }

  if (!normalized.due_days) {
    normalized.due_days = 30;
  }

  return normalized;
}

// --- KB/Helpdesk Source Normalizer (fixes C6, M20) ---

export function normalizeKbSource(source) {
  return {
    ...source,
    title: source.title ?? source.filename ?? source.topic ?? 'Untitled',
    relevanceScore: source.relevance_score ?? source.score ?? 0,
  };
}

// --- Notification Preferences Serializer (fixes C9, M25) ---

export function serializeNotificationPrefs(prefs) {
  return {
    email_quote_request: prefs.emailNewQuote ?? prefs.email_quote_request ?? true,
    email_email_received: prefs.emailNewInquiry ?? prefs.email_email_received ?? true,
    email_invoice_overdue: prefs.emailInvoiceOverdue ?? prefs.email_invoice_overdue ?? true,
    email_digest_enabled: prefs.dailyDigest ?? prefs.email_digest_enabled ?? false,
  };
}
