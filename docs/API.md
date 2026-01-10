# API Reference

REST API endpoints for the multi-tenant platform.

## Base URL

```
https://your-deployment.run.app
```

## Authentication

Currently no authentication (add as needed per client).

---

## Inbound Agent (Customer Chat)

### POST /api/chat/inbound

Customer-facing conversational agent.

**Request:**
```json
{
  "session_id": "unique_session_id",
  "message": "I want to visit Zanzibar for 7 nights"
}
```

**Response:**
```json
{
  "output": "I'd be happy to help you plan your Zanzibar vacation! ...",
  "session_id": "unique_session_id",
  "success": true
}
```

---

## Helpdesk Agent (Employee Support)

### POST /api/chat/helpdesk

Employee-facing support agent.

**Request:**
```json
{
  "session_id": "employee_session_123",
  "message": "What is our commission structure?"
}
```

**Response:**
```json
{
  "output": "Our commission structure is...",
  "session_id": "employee_session_123",
  "success": true
}
```

---

## Quote Generation

### POST /api/quote/generate

Generate travel quote from customer inquiry.

**Request:**
```json
{
  "customer_name": "John Doe",
  "customer_email": "john@example.com",
  "destination": "Zanzibar",
  "check_in": "2025-12-15",
  "check_out": "2025-12-22",
  "adults": 2,
  "children": 0,
  "budget": 25000
}
```

**Response:**
```json
{
  "quote_id": "QT-ABC123",
  "hotels": [
    {
      "name": "Sea Cliff Resort",
      "total_price": 24500,
      "price_per_person": 12250
    }
  ],
  "pdf_url": "https://storage.../quote.pdf"
}
```

---

## Email Parsing

### POST /api/email/parse

Parse incoming email inquiry.

**Request:**
```json
{
  "subject": "Zanzibar Inquiry",
  "body": "Hi, I want to visit Zanzibar with my wife..."
}
```

**Response:**
```json
{
  "customer_name": "John Doe",
  "destination": "Zanzibar",
  "adults": 2,
  "children": 0
}
```

---

## Configuration

All endpoints use the client configuration based on `CLIENT_ID` environment variable.

Different clients get:
- Different RAG knowledge bases
- Different destinations
- Different branding
- Different email templates

**Same API, multiple clients!**
