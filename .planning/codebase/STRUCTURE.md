# Directory Structure

```
multitenant-ai-platform-lite/
├── main.py                     # FastAPI app entry point
├── config/
│   ├── loader.py               # Config loading utilities
│   └── clients/                # Per-tenant configs
│       └── africastay.yaml     # Example tenant config
├── src/
│   ├── api/                    # API routes
│   │   ├── routes.py           # Main route registration
│   │   ├── auth_routes.py      # Authentication
│   │   ├── helpdesk_routes.py  # AI helpdesk
│   │   ├── admin_*.py          # Admin platform routes
│   │   └── ...
│   ├── services/               # Business logic
│   │   ├── auth_service.py     # Auth operations
│   │   ├── faiss_helpdesk_service.py  # FAISS vector search
│   │   └── crm_service.py      # CRM operations
│   ├── middleware/             # Request middleware
│   │   ├── auth_middleware.py  # JWT validation
│   │   └── rate_limiter.py     # Rate limiting
│   ├── tools/                  # External integrations
│   │   ├── supabase_tool.py    # Database operations
│   │   └── bigquery_tool.py    # BigQuery operations
│   ├── agents/                 # AI agents
│   │   ├── quote_agent.py      # Quote generation
│   │   └── universal_email_parser.py
│   ├── webhooks/               # Webhook handlers
│   │   └── email_webhook.py    # SendGrid inbound
│   └── utils/                  # Utilities
│       ├── pdf_generator.py    # PDF creation
│       └── email_sender.py     # Email sending
├── frontend/
│   ├── tenant-dashboard/       # Tenant-facing React app
│   │   ├── src/
│   │   │   ├── pages/          # Page components
│   │   │   ├── services/       # API client
│   │   │   └── context/        # React contexts
│   │   └── package.json
│   └── internal-admin/         # Admin React app
│       ├── src/
│       │   ├── pages/          # Admin pages
│       │   └── services/       # Admin API client
│       └── package.json
├── requirements.txt            # Python dependencies
└── .env                        # Environment variables
```

## Key Entry Points
- **Backend**: `main.py` starts Uvicorn server
- **Tenant Frontend**: `frontend/tenant-dashboard/`
- **Admin Frontend**: `frontend/internal-admin/`
