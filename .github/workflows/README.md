# GitHub Actions Workflows

## CI Workflow (ci.yml)

Runs on every push to main/master and on pull requests.

### Jobs

1. **test**: Runs Python tests
   - Python 3.11
   - Linting with flake8
   - Tests with pytest

2. **docker-build**: Verifies Docker image builds
   - Uses BuildKit caching for speed
   - Does not push (verification only)

## Deploy Workflow (deploy.yml)

Deploys to Google Cloud Run after successful CI workflow completion.

### Required Secrets

Set these in GitHub repository settings (Settings > Secrets and variables > Actions):

| Secret | Description | Example |
|--------|-------------|---------|
| `GCP_PROJECT_ID` | Google Cloud project ID | `my-project-123456` |
| `WIF_PROVIDER` | Workload Identity provider | `projects/123456/locations/global/workloadIdentityPools/github/providers/github` |
| `WIF_SERVICE_ACCOUNT` | Service account email | `github-deploy@my-project.iam.gserviceaccount.com` |

### Setting up Workload Identity Federation

1. Create a Workload Identity Pool:
   ```bash
   gcloud iam workload-identity-pools create "github" \
     --location="global" \
     --display-name="GitHub Actions"
   ```

2. Create a Provider in the pool:
   ```bash
   gcloud iam workload-identity-pools providers create-oidc "github" \
     --location="global" \
     --workload-identity-pool="github" \
     --display-name="GitHub" \
     --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
     --issuer-uri="https://token.actions.githubusercontent.com"
   ```

3. Create a service account and grant permissions:
   ```bash
   gcloud iam service-accounts create github-deploy \
     --display-name="GitHub Deploy"

   gcloud projects add-iam-policy-binding PROJECT_ID \
     --member="serviceAccount:github-deploy@PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/run.admin"

   gcloud projects add-iam-policy-binding PROJECT_ID \
     --member="serviceAccount:github-deploy@PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/artifactregistry.writer"
   ```

4. Allow the service account to be impersonated:
   ```bash
   gcloud iam service-accounts add-iam-policy-binding \
     github-deploy@PROJECT_ID.iam.gserviceaccount.com \
     --role="roles/iam.workloadIdentityUser" \
     --member="principalSet://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github/attribute.repository/OWNER/REPO"
   ```

## Manual Deployment

The deploy workflow can also be triggered manually via the GitHub Actions UI (workflow_dispatch).

## Environment Variables

The deployment sets these environment variables on Cloud Run:

| Variable | Value | Description |
|----------|-------|-------------|
| `LOG_LEVEL` | `INFO` | Application log level |

Additional environment variables should be configured directly in Cloud Run or via Secret Manager.
