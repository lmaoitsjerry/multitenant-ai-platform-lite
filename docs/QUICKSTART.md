# Quick Start Guide

Get a client running in under 1 hour!

## Prerequisites

- Google Cloud Project with BigQuery and Vertex AI enabled
- Supabase project
- OpenAI API key
- Python 3.9+

## Step-by-Step Setup

### 1. Create Client Configuration (5 minutes)

```bash
# Copy template
cp clients/example/client.yaml.template clients/yourcompany/client.yaml

# Edit with your details
nano clients/yourcompany/client.yaml
```

Required fields:
- `client.id` - Unique identifier (lowercase, no spaces)
- `client.name` - Display name
- `infrastructure.gcp.project_id` - GCP project
- `infrastructure.gcp.dataset` - BigQuery dataset name
- `destinations` - List of travel destinations
- `email.primary` - Primary contact email
- `branding.company_name` - Company name
- `branding.primary_color` - Brand color (hex)

### 2. Set Environment Variables (2 minutes)

```bash
export OPENAI_API_KEY="sk-..."
export SUPABASE_KEY="..."
export SMTP_PASSWORD="..."
```

### 3. Run Automated Setup (20-30 minutes)

```bash
python scripts/setup_client.py setup \
    --client-id yourcompany \
    --config-file clients/yourcompany/client.yaml
```

This creates:
- ✅ BigQuery dataset + tables
- ✅ Vertex AI RAG corpus
- ✅ Supabase tables
- ✅ Environment file

### 4. Import Hotel Data (5-10 minutes)

```bash
python scripts/import_data.py \
    --client-id yourcompany \
    --type hotel_rates \
    --file data/your_rates.xlsx
```

Excel format:
```
destination | hotel_name | room_type | meal_plan | check_in_date | check_out_date | nights | total_7nights_pps
Zanzibar    | Sea Cliff  | Deluxe    | All Inc   | 2025-12-15    | 2025-12-22     | 7      | 12500
```

### 5. Upload Knowledge Base (10-15 minutes)

Upload documents to Vertex AI RAG corpus:
1. Go to GCP Console → Vertex AI → Search & Conversation
2. Find your corpus (generated in step 3)
3. Upload PDFs, docs about destinations, hotels, policies

### 6. Test Everything (5 minutes)

```bash
python scripts/validate_client.py --client-id yourcompany
```

### 7. Deploy (10 minutes)

```bash
# Build Docker image
docker build -t gcr.io/PROJECT/yourcompany-api .

# Deploy to Cloud Run
gcloud run deploy yourcompany-api \
    --image gcr.io/PROJECT/yourcompany-api \
    --set-env-vars CLIENT_ID=yourcompany \
    --region us-central1
```

## Total Time: **45-60 minutes** ✅

## Verify It's Working

```bash
# Test inbound agent
curl -X POST https://your-url/api/chat/inbound \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test", "message": "I want to visit Zanzibar"}'

# Should return branded response with your destinations
```

## Next Steps

1. **Customize Prompts**: Edit `clients/yourcompany/prompts/*.txt`
2. **Add Consultants**: Import to BigQuery consultants table
3. **Customize Templates**: Edit email/PDF templates
4. **Test Workflows**: Send test quotes

## Common Issues

**"No corpus_id configured"**
- RAG corpus creation takes time
- Update `client.yaml` with corpus ID from GCP Console

**"BigQuery permission denied"**
- Ensure service account has BigQuery Admin role

**"Email not sending"**
- Verify SMTP credentials in environment variables

## Support

See full documentation:
- Architecture: `docs/ARCHITECTURE.md`
- API Reference: `docs/API.md`
- Scripts: `scripts/README.md`
