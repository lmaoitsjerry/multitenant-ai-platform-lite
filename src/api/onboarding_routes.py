"""
Tenant Onboarding Routes (Lite Edition)

Complete onboarding wizard for new tenants:
- Generate AI agent system prompts from plain English descriptions
- Provision tenant infrastructure (Supabase, SendGrid)
- Configure email and AI helpdesk
- Create SendGrid subuser for tenant email isolation

Note: Voice AI features (VAPI, phone provisioning) are Pro/Enterprise only.
"""

import os
from dotenv import load_dotenv

# Ensure environment variables are loaded (for Supabase credentials, etc.)
load_dotenv()
import re
import logging
import yaml
import uuid
import random
import string
import hashlib
import secrets
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel, Field, EmailStr, ConfigDict

logger = logging.getLogger(__name__)

# Import SendGrid provisioner for tenant email isolation
try:
    from src.services.provisioning_service import SendGridProvisioner
    SENDGRID_PROVISIONING_AVAILABLE = True
except ImportError:
    SENDGRID_PROVISIONING_AVAILABLE = False
    logger.warning("SendGrid provisioning not available")

# Try Google GenAI - try API key first, then Vertex AI
GENAI_AVAILABLE = False
genai_client = None
genai_model = None  # For google-generativeai library

# First try google-generativeai with API key (simpler)
google_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if google_api_key:
    try:
        import google.generativeai as genai_sdk
        genai_sdk.configure(api_key=google_api_key)
        genai_model = genai_sdk.GenerativeModel('gemini-1.5-flash')
        GENAI_AVAILABLE = True
        logger.info("Google GenAI initialized with API key")
    except Exception as e:
        logger.warning(f"Failed to initialize with API key: {e}")

# Fallback to Vertex AI (same as inbound/outbound agents)
if not GENAI_AVAILABLE:
    try:
        from google import genai
        gcp_project = os.getenv("GCP_PROJECT_ID", "zorah-475411")
        gcp_region = os.getenv("GCP_REGION", "us-central1")
        genai_client = genai.Client(
            vertexai=True,
            project=gcp_project,
            location=gcp_region
        )
        GENAI_AVAILABLE = True
        logger.info(f"Google GenAI initialized with Vertex AI (project: {gcp_project})")
    except ImportError:
        logger.warning("Google GenAI not installed. Run: pip install google-genai")
    except Exception as e:
        logger.error(f"Failed to initialize Google GenAI: {e}")

onboarding_router = APIRouter(prefix="/api/v1/admin/onboarding", tags=["Onboarding"])


# ==================== Brand Themes ====================

BRAND_THEMES = [
    {
        "id": "ocean-blue",
        "name": "Ocean Blue",
        "description": "Professional and trustworthy",
        "primary": "#0EA5E9",
        "secondary": "#0284C7",
        "accent": "#38BDF8"
    },
    {
        "id": "safari-gold",
        "name": "Safari Gold",
        "description": "Warm and adventurous",
        "primary": "#D97706",
        "secondary": "#B45309",
        "accent": "#FBBF24"
    },
    {
        "id": "sunset-orange",
        "name": "Sunset Orange",
        "description": "Energetic and vibrant",
        "primary": "#EA580C",
        "secondary": "#C2410C",
        "accent": "#FB923C"
    },
    {
        "id": "forest-green",
        "name": "Forest Green",
        "description": "Natural and eco-friendly",
        "primary": "#059669",
        "secondary": "#047857",
        "accent": "#34D399"
    },
    {
        "id": "royal-purple",
        "name": "Royal Purple",
        "description": "Luxurious and premium",
        "primary": "#7C3AED",
        "secondary": "#6D28D9",
        "accent": "#A78BFA"
    },
    {
        "id": "classic-black",
        "name": "Classic Black",
        "description": "Elegant and sophisticated",
        "primary": "#1F2937",
        "secondary": "#111827",
        "accent": "#6B7280"
    },
    {
        "id": "rose-pink",
        "name": "Rose Pink",
        "description": "Modern and stylish",
        "primary": "#DB2777",
        "secondary": "#BE185D",
        "accent": "#F472B6"
    },
    {
        "id": "teal-modern",
        "name": "Teal Modern",
        "description": "Fresh and contemporary",
        "primary": "#0D9488",
        "secondary": "#0F766E",
        "accent": "#2DD4BF"
    }
]


# ==================== Pydantic Models ====================

class GeneratePromptRequest(BaseModel):
    """Request to generate AI system prompt from description"""
    description: str = Field(..., min_length=20, description="Plain English description of desired AI agent")
    agent_type: str = Field(..., pattern="^(inbound|outbound)$")
    company_name: Optional[str] = None
    agent_name: Optional[str] = None


class GeneratePromptResponse(BaseModel):
    """Generated system prompt response"""
    system_prompt: str
    agent_name: str
    suggestions: List[str] = []


class BrandTheme(BaseModel):
    """Brand theme selection"""
    theme_id: str
    primary: str
    secondary: str
    accent: str


class CompanyProfile(BaseModel):
    """Step 1: Company profile information"""
    company_name: str = Field(..., min_length=2, max_length=100)
    support_email: EmailStr
    support_phone: Optional[str] = None
    website_url: Optional[str] = None
    timezone: str = Field(default="Africa/Johannesburg")
    currency: str = Field(default="ZAR")
    brand_theme: BrandTheme
    logo_url: Optional[str] = None


class AgentConfig(BaseModel):
    """Step 2: AI agent configuration"""
    inbound_description: str = Field(..., min_length=20)
    inbound_prompt: str
    inbound_agent_name: str = Field(default="Sarah")
    inbound_voice_id: Optional[str] = None
    outbound_description: Optional[str] = None
    outbound_prompt: Optional[str] = None
    outbound_agent_name: str = Field(default="Michael")
    outbound_voice_id: Optional[str] = None


class OutboundSettings(BaseModel):
    """Step 3: Outbound call settings"""
    enabled: bool = Field(default=True)
    timing: str = Field(default="next_business_day")
    call_window_start: str = Field(default="09:00")
    call_window_end: str = Field(default="17:00")
    call_days: List[str] = Field(default=["mon", "tue", "wed", "thu", "fri"])
    max_attempts: int = Field(default=2, ge=1, le=5)
    min_quote_value: float = Field(default=0)


class EmailSettings(BaseModel):
    """Step 4: Email configuration"""
    from_name: str
    email_signature: str = ""
    auto_send_quotes: bool = Field(default=True)
    quote_validity_days: int = Field(default=14)
    follow_up_days: int = Field(default=3)
    from_email: Optional[str] = None
    # Note: SendGrid subuser is auto-created during onboarding for tenant isolation


class KnowledgeBaseConfig(BaseModel):
    """Step 5: Knowledge base setup"""
    categories: List[str] = Field(default=["Destinations", "Hotels", "Visa Info", "FAQs", "Company Policies"])
    skip_initial_setup: bool = Field(default=True)


class OnboardingRequest(BaseModel):
    """Complete onboarding request"""
    company: CompanyProfile
    agents: AgentConfig
    outbound: OutboundSettings
    email: EmailSettings
    knowledge_base: KnowledgeBaseConfig
    provision_phone: bool = Field(default=True)
    phone_country: str = Field(default="ZA")

    # Admin user credentials (required for first login)
    admin_email: Optional[str] = None
    admin_password: Optional[str] = None
    admin_name: Optional[str] = None

    # Infrastructure (provided by admin or auto-generated)
    gcp_project_id: Optional[str] = None
    supabase_url: Optional[str] = None
    supabase_anon_key: Optional[str] = None
    supabase_service_key: Optional[str] = None


class OnboardingResponse(BaseModel):
    """Onboarding completion response"""
    model_config = ConfigDict(ser_json_exclude_none=False)  # Include user even if None

    success: bool
    tenant_id: str
    message: str
    resources: Dict[str, Any]
    errors: List[str] = []
    # Auth tokens for auto-login after onboarding
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_at: Optional[int] = None
    # User object for auto-login (frontend needs this to initialize session)
    user: Optional[Dict[str, Any]] = None


class VoiceOption(BaseModel):
    """Available voice option"""
    id: str
    name: str
    gender: str
    accent: Optional[str] = None
    provider: str
    sample_url: Optional[str] = None


# ==================== Helper Functions ====================

def generate_tenant_id(company_name: str) -> str:
    """
    Generate a cryptographically secure tenant ID.

    Format: tn_{hash}_{random}
    - Prefix 'tn_' identifies it as a tenant ID
    - 8-char hash derived from company name + timestamp (for correlation)
    - 12-char cryptographically random suffix (unpredictable)

    Example: tn_a7f3b2c1_x9k2m4p7q1w3

    Security properties:
    - Cannot be guessed from company name alone
    - Cryptographically random component prevents enumeration
    - Not reversible to company name
    """
    # Create hash component from company name + current timestamp + random salt
    # This provides correlation for debugging but cannot be reversed
    salt = secrets.token_hex(8)
    timestamp = str(datetime.utcnow().timestamp())
    hash_input = f"{company_name.lower()}{timestamp}{salt}"
    hash_digest = hashlib.sha256(hash_input.encode()).hexdigest()[:8]

    # Generate cryptographically secure random component
    # Using secrets module which is suitable for security-sensitive applications
    random_component = secrets.token_hex(6)  # 12 hex characters

    return f"tn_{hash_digest}_{random_component}"


# ==================== Prompt Generation ====================

PROMPT_GENERATION_TEMPLATE = """You are an expert at creating system prompts for AI travel consultants.

The user wants to create an AI agent for their travel agency with the following requirements:

Company: {company_name}
Agent Type: {agent_type} ({agent_type_description})
Agent Name: {agent_name}

User's Description:
{description}

Create a comprehensive system prompt for this AI agent. The prompt should:
1. Define the agent's personality and communication style based on the description
2. Include specific instructions for the agent type
3. Be professional but match the tone requested
4. Include handling for common scenarios
5. Have clear boundaries on what the agent can/cannot do

For INBOUND agents, include:
- Greeting and introduction
- How to qualify leads (destination, dates, budget, travelers)
- When to offer to send a quote
- How to handle objections
- Escalation procedures

For OUTBOUND agents, include:
- How to introduce themselves (following up on a quote)
- How to gauge customer interest
- Handling common objections
- When to offer alternatives or discounts
- How to close or schedule callbacks

Return ONLY the system prompt text, nothing else. No headers, no markdown, just the prompt."""


@onboarding_router.post("/generate-prompt", response_model=GeneratePromptResponse)
async def generate_agent_prompt(request: GeneratePromptRequest):
    """
    Generate an optimized AI system prompt from a plain English description.
    Uses Google Vertex AI (Gemini) to convert the user's description into a professional system prompt.
    """
    if not GENAI_AVAILABLE or not genai_client:
        raise HTTPException(
            status_code=500,
            detail="Google GenAI not available. Please check GCP configuration."
        )

    # Build the prompt
    agent_type_desc = "handles incoming customer inquiries" if request.agent_type == "inbound" else "makes follow-up calls to customers who received quotes"
    generation_prompt = PROMPT_GENERATION_TEMPLATE.format(
        company_name=request.company_name or "Travel Agency",
        agent_type=request.agent_type,
        agent_type_description=agent_type_desc,
        agent_name=request.agent_name or "the agent",
        description=request.description
    )

    try:
        # Use either API key model or Vertex AI client
        if genai_model:
            # Using google-generativeai with API key
            response = genai_model.generate_content(generation_prompt)
            system_prompt = response.text.strip()
            logger.info(f"Generated prompt using Gemini API for {request.company_name}")
        elif genai_client:
            # Using Vertex AI
            response = genai_client.models.generate_content(
                model="gemini-2.0-flash-001",
                contents=generation_prompt
            )
            system_prompt = response.text.strip()
            logger.info(f"Generated prompt using Vertex AI for {request.company_name}")
        else:
            raise HTTPException(
                status_code=500,
                detail="No GenAI client available"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prompt generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate prompt: {str(e)}"
        )

    # Suggest agent name if not provided
    agent_name = request.agent_name
    if not agent_name:
        agent_name = "Sarah" if request.agent_type == "inbound" else "Michael"

    return GeneratePromptResponse(
        system_prompt=system_prompt,
        agent_name=agent_name,
        suggestions=[
            "Consider adding specific product knowledge",
            "You can customize the greeting message",
            "Add company-specific policies as needed"
        ]
    )


# ==================== Brand Themes Endpoint ====================

@onboarding_router.get("/themes")
async def get_brand_themes():
    """Get available brand theme options"""
    return {"themes": BRAND_THEMES}


# ==================== Voice Options ====================

@onboarding_router.get("/voices", response_model=List[VoiceOption])
async def get_available_voices():
    """
    Get available VAPI voice options.

    Note: Voice AI features (VAPI) are only available in Pro/Enterprise plans.
    This endpoint returns an empty list for Lite mode.
    """
    # Voice features are Pro/Enterprise only - return empty list for Lite
    return []


# ==================== SendGrid Subuser Creation ====================

async def provision_sendgrid_subuser(
    tenant_id: str,
    contact_email: str,
    from_email: str,
    from_name: str,
    company_name: str
) -> Dict[str, Any]:
    """
    Create a SendGrid subuser for tenant email isolation.

    Args:
        tenant_id: Unique tenant identifier
        contact_email: Admin contact email
        from_email: Sender email address
        from_name: Sender display name
        company_name: Company name for sender identity

    Returns:
        Dict with success status, api_key, and any errors
    """
    if not SENDGRID_PROVISIONING_AVAILABLE:
        logger.warning("SendGrid provisioning not available - skipping subuser creation")
        return {"success": False, "error": "SendGrid provisioning not available"}

    master_key = os.getenv("SENDGRID_MASTER_API_KEY")
    if not master_key:
        logger.warning("SENDGRID_MASTER_API_KEY not configured - tenant will use default email")
        return {"success": False, "error": "Master API key not configured"}

    try:
        provisioner = SendGridProvisioner(master_key)

        # Create subuser with sanitized tenant_id
        subuser_result = provisioner.create_subuser(
            username=tenant_id,
            email=contact_email
        )

        if not subuser_result.get("success"):
            error_msg = subuser_result.get("error", "Unknown error")
            # Check if subuser already exists
            if "already exists" in str(error_msg).lower():
                logger.info(f"SendGrid subuser {tenant_id} already exists")
            else:
                logger.error(f"SendGrid subuser creation failed: {error_msg}")
                return {"success": False, "error": error_msg}

        # Create API key for the subuser
        api_key_result = provisioner.create_api_key(
            name=f"{tenant_id}-mail-api-key",
            subuser=tenant_id
        )

        if not api_key_result.get("success"):
            logger.error(f"SendGrid API key creation failed: {api_key_result.get('error')}")
            return {"success": False, "error": api_key_result.get("error")}

        api_key = api_key_result["data"]["api_key"]

        # Create verified sender identity
        sender_result = provisioner.add_verified_sender(
            from_email=from_email,
            from_name=from_name,
            reply_to=contact_email,
            nickname=company_name,
            address="123 Main St",  # Placeholder - can be updated later
            city="Cape Town",
            country="South Africa",
            subuser=tenant_id
        )

        if not sender_result.get("success"):
            logger.warning(f"Verified sender creation failed: {sender_result.get('error')}")
            # Don't fail the whole process - sender can be verified later

        # Try to assign an IP (optional - may not be available)
        ip_result = provisioner.assign_ip_to_subuser(tenant_id)
        ip_address = ip_result.get("ip") if ip_result.get("success") else None

        logger.info(f"SendGrid subuser provisioned successfully for {tenant_id}")

        return {
            "success": True,
            "subuser": tenant_id,
            "api_key": api_key,
            "ip_address": ip_address,
            "sender_verified": sender_result.get("success", False)
        }

    except Exception as e:
        logger.error(f"SendGrid provisioning error: {e}")
        return {"success": False, "error": str(e)}


# ==================== Complete Onboarding ====================

@onboarding_router.post("/complete", response_model=OnboardingResponse)
async def complete_onboarding(request: OnboardingRequest):
    """
    Complete the full tenant onboarding process.
    Auto-generates tenant ID from company name.
    """
    # Generate tenant ID from company name
    tenant_id = generate_tenant_id(request.company.company_name)

    errors = []
    resources = {
        "tenant_id": tenant_id,
        "config_created": False,
        "database_ready": False,
        "sendgrid_subuser": None,
        "sendgrid_api_key_created": False
    }

    # Track if SendGrid API key was provisioned (for config update)
    provisioned_sendgrid_key = None

    try:
        # Step 1: Provision SendGrid subuser for tenant email isolation
        # Always create a subuser for tenant isolation
        logger.info(f"Provisioning SendGrid subuser for {tenant_id}")
        from_email = request.email.from_email or request.company.support_email
        from_name = request.email.from_name or request.company.company_name

        sendgrid_result = await provision_sendgrid_subuser(
            tenant_id=tenant_id,
            contact_email=request.company.support_email,
            from_email=from_email,
            from_name=from_name,
            company_name=request.company.company_name
        )

        if sendgrid_result.get("success"):
            resources["sendgrid_subuser"] = sendgrid_result.get("subuser")
            resources["sendgrid_api_key_created"] = True
            provisioned_sendgrid_key = sendgrid_result.get("api_key")
            logger.info(f"SendGrid subuser created: {tenant_id}")
        else:
            # Log warning but don't fail - tenant can use platform default email
            logger.warning(f"SendGrid provisioning failed: {sendgrid_result.get('error')}")
            errors.append(f"SendGrid: {sendgrid_result.get('error')} - using platform default")

        # Step 2: Create tenant directory and config
        logger.info(f"Creating tenant configuration for {tenant_id}")
        config_created = await create_tenant_config(
            tenant_id,
            request,
            sendgrid_api_key=provisioned_sendgrid_key
        )
        resources["config_created"] = config_created

        if not config_created:
            errors.append("Failed to create tenant configuration")
            return OnboardingResponse(
                success=False,
                tenant_id=tenant_id,
                message="Onboarding failed at configuration step",
                resources=resources,
                errors=errors
            )

        # Step 3: Voice features (VAPI) - Not available in Lite mode
        # Pro/Enterprise features: Voice AI agents, phone provisioning
        # For Lite mode, we skip all VAPI/voice provisioning
        logger.info(f"Lite mode - voice features not available, skipping VAPI provisioning for {tenant_id}")

        # Step 4: Initialize database records (tenants, tenant_settings, tenant_branding)
        logger.info(f"Initializing database records for {tenant_id}")
        try:
            from config.loader import get_config, clear_config_cache
            from src.tools.supabase_tool import SupabaseTool

            # Clear cache and load fresh config
            clear_config_cache(tenant_id)
            config = get_config(tenant_id)
            db = SupabaseTool(config)

            # Create tenants registry record
            try:
                tenants_data = {
                    "id": tenant_id,
                    "name": request.company.company_name,
                    "short_name": re.sub(r'[^a-z]', '', request.company.company_name.lower())[:50] or "tenant",
                    "status": "active",
                    "plan": "lite",
                    "admin_email": request.admin_email,
                    "support_email": request.company.support_email,
                    "max_users": 5,
                    "max_monthly_quotes": 100,
                    "max_storage_gb": 1,
                }
                tenants_result = db.client.table("tenants").upsert(tenants_data, on_conflict="id").execute()
                if tenants_result.data:
                    resources["tenant_registered"] = True
                    logger.info(f"Created tenants registry record for {tenant_id}")
            except Exception as reg_err:
                # Table might not exist yet - not critical, log and continue
                logger.warning(f"Could not create tenants registry record (table may not exist): {reg_err}")

            # Create tenant_settings record
            settings_result = db.update_tenant_settings(
                company_name=request.company.company_name,
                support_email=request.company.support_email,
                support_phone=request.company.support_phone,
                website=request.company.website_url,
                currency=request.company.currency,
                timezone=request.company.timezone,
                email_from_name=request.email.from_name,
                email_from_email=request.email.from_email or request.company.support_email,
            )

            if settings_result:
                resources["tenant_settings_created"] = True
                logger.info(f"Created tenant_settings record for {tenant_id}")
            else:
                logger.warning(f"Failed to create tenant_settings for {tenant_id}")

            # Create tenant_branding record
            branding_result = db.create_branding(
                preset_theme=request.company.brand_theme.theme_id,
                colors={
                    "primary": request.company.brand_theme.primary,
                    "secondary": request.company.brand_theme.secondary,
                    "accent": request.company.brand_theme.accent,
                }
            )

            if branding_result:
                resources["tenant_branding_created"] = True
                logger.info(f"Created tenant_branding record for {tenant_id}")
            else:
                logger.warning(f"Failed to create tenant_branding for {tenant_id}")

            resources["database_ready"] = True

        except Exception as e:
            logger.error(f"Database initialization failed for {tenant_id}: {e}")
            errors.append(f"Database initialization: {str(e)}")
            # Don't fail onboarding - YAML config will be used as fallback

        # Step 6: Create admin user and get auth tokens for auto-login
        auth_tokens = {}
        if request.admin_email and request.admin_password:
            logger.info(f"Creating admin user for {tenant_id}")
            try:
                from src.services.auth_service import AuthService
                from config.loader import get_config, clear_config_cache

                # Clear any cached config to ensure we load the fresh one
                clear_config_cache(tenant_id)

                # Load the newly created config
                config = get_config(tenant_id)

                # Get Supabase credentials from tenant config
                service_key = config.supabase_service_key
                if not service_key:
                    logger.error(f"Missing Supabase service key for {tenant_id}")
                    raise ValueError("Supabase service key not configured")

                auth_service = AuthService(
                    supabase_url=config.supabase_url,
                    supabase_key=service_key
                )

                success, result = await auth_service.create_auth_user(
                    email=request.admin_email,
                    password=request.admin_password,
                    name=request.admin_name or "Admin",
                    tenant_id=tenant_id,
                    role="admin"
                )

                if success:
                    resources["admin_user_created"] = True
                    resources["admin_email"] = request.admin_email
                    logger.info(f"Admin user created: {request.admin_email}")

                    # Step 6b: Auto-login to get tokens for frontend
                    logger.info(f"Generating auth tokens for {request.admin_email}")
                    login_success, login_result = await auth_service.login(
                        email=request.admin_email,
                        password=request.admin_password,
                        tenant_id=tenant_id
                    )

                    if login_success:
                        user_data = login_result.get("user")
                        logger.info(f"Login result user: {user_data}")  # Debug
                        auth_tokens = {
                            "access_token": login_result.get("access_token"),
                            "refresh_token": login_result.get("refresh_token"),
                            "expires_at": login_result.get("expires_at"),
                            "user": user_data,  # Include user for frontend session
                        }
                        resources["auto_login"] = True
                        logger.info(f"Auth tokens generated for auto-login (user: {bool(user_data)})")
                    else:
                        logger.warning(f"Auto-login failed: {login_result.get('error')}")
                        resources["auto_login"] = False
                else:
                    errors.append(f"Admin user creation: {result.get('error', 'Unknown error')}")
                    resources["admin_user_created"] = False

            except Exception as e:
                logger.error(f"Admin user creation failed: {e}")
                errors.append(f"Admin user: {str(e)}")
                resources["admin_user_created"] = False

        # Determine success
        success = resources["config_created"] and len(errors) == 0
        partial_success = resources["config_created"] and len(errors) > 0

        if success:
            message = "Tenant onboarding completed successfully!"
        elif partial_success:
            message = f"Tenant created with {len(errors)} warning(s). Some features may need manual configuration."
        else:
            message = "Onboarding failed. Please check errors and try again."

        return OnboardingResponse(
            success=success or partial_success,
            tenant_id=tenant_id,
            message=message,
            resources=resources,
            errors=errors,
            access_token=auth_tokens.get("access_token"),
            refresh_token=auth_tokens.get("refresh_token"),
            expires_at=auth_tokens.get("expires_at"),
            user=auth_tokens.get("user")  # Include user for frontend session initialization
        )

    except Exception as e:
        logger.error(f"Onboarding failed for {tenant_id}: {e}")
        return OnboardingResponse(
            success=False,
            tenant_id=tenant_id,
            message=f"Onboarding failed: {str(e)}",
            resources=resources,
            errors=errors + [str(e)]
        )


# ==================== Helper Functions ====================

async def create_tenant_config(
    tenant_id: str,
    request: OnboardingRequest,
    sendgrid_api_key: Optional[str] = None
) -> bool:
    """Create tenant directory and config.yaml file

    Args:
        tenant_id: Unique tenant identifier
        request: Onboarding request data
        sendgrid_api_key: Provisioned or provided SendGrid API key
    """
    base_path = Path(__file__).parent.parent.parent / "clients" / tenant_id
    base_path.mkdir(parents=True, exist_ok=True)

    # Create prompts directory
    prompts_dir = base_path / "prompts"
    prompts_dir.mkdir(exist_ok=True)

    # Save prompts to files
    inbound_prompt_path = prompts_dir / "inbound.txt"
    with open(inbound_prompt_path, 'w') as f:
        f.write(request.agents.inbound_prompt)

    if request.agents.outbound_prompt:
        outbound_prompt_path = prompts_dir / "outbound.txt"
        with open(outbound_prompt_path, 'w') as f:
            f.write(request.agents.outbound_prompt)

    # Generate short_name: lowercase letters only from company name
    short_name = re.sub(r'[^a-z]', '', request.company.company_name.lower())
    if not short_name:
        short_name = "tenant"  # Fallback if no letters in company name

    # Build config structure
    config = {
        "client": {
            "id": tenant_id,
            "name": request.company.company_name,
            "short_name": short_name,
            "timezone": request.company.timezone,
            "currency": request.company.currency
        },
        "branding": {
            "company_name": request.company.company_name,
            "primary_color": request.company.brand_theme.primary,
            "secondary_color": request.company.brand_theme.secondary,
            "accent_color": request.company.brand_theme.accent,
            "theme_id": request.company.brand_theme.theme_id,
            "logo_url": request.company.logo_url,
            "email_signature": request.email.email_signature
        },
        "infrastructure": {
            "gcp": {
                "project_id": request.gcp_project_id or os.getenv("GCP_PROJECT_ID", "zorah-ai-platform"),
                "region": "us-central1",
                "dataset": f"{tenant_id.replace('-', '_')}_data"
            },
            "supabase": {
                "url": request.supabase_url or os.getenv("SUPABASE_URL", ""),
                "anon_key": request.supabase_anon_key or os.getenv("SUPABASE_ANON_KEY", ""),
                "service_key": request.supabase_service_key or os.getenv("SUPABASE_SERVICE_KEY", "")
            },
            "openai": {
                "api_key": "${OPENAI_API_KEY}",
                "model": "gpt-4o-mini"
            }
        },
        "email": {
            "primary": request.email.from_email or request.company.support_email,
            "smtp": {
                "host": "smtp.sendgrid.net",
                "port": 587,
                "username": "apikey",
                "password": sendgrid_api_key or "${SENDGRID_API_KEY}"
            },
            "imap": {
                "host": "imap.gmail.com",
                "port": 993
            },
            "sendgrid": {
                "api_key": sendgrid_api_key or "${SENDGRID_API_KEY}",
                "from_email": request.email.from_email or request.company.support_email,
                "from_name": request.email.from_name,
                "reply_to": request.company.support_email
            }
        },
        "outbound": {
            "enabled": request.outbound.enabled,
            "timing": request.outbound.timing,
            "call_window": {
                "start": request.outbound.call_window_start,
                "end": request.outbound.call_window_end
            },
            "call_days": request.outbound.call_days,
            "max_attempts": request.outbound.max_attempts,
            "min_quote_value": request.outbound.min_quote_value
        },
        "quotes": {
            "auto_send": request.email.auto_send_quotes,
            "validity_days": request.email.quote_validity_days,
            "follow_up_days": request.email.follow_up_days
        },
        "agents": {
            "inbound": {
                "enabled": True,
                "name": request.agents.inbound_agent_name,
                "prompt_file": "prompts/inbound.txt"
            },
            "helpdesk": {
                "enabled": True,
                "prompt_file": "prompts/inbound.txt"
            }
        },
        "knowledge_base": {
            "categories": request.knowledge_base.categories
        },
        # Default African destinations - all tenants use shared pricing from africastay_analytics
        "destinations": [
            {
                "name": "Zanzibar",
                "code": "ZNZ",
                "enabled": True,
                "aliases": ["Stone Town", "Zanzibar Island"]
            },
            {
                "name": "Kenya",
                "code": "KEN",
                "enabled": True,
                "aliases": ["Masai Mara", "Nairobi", "Diani Beach", "Amboseli", "Samburu", "Mombasa"]
            },
            {
                "name": "Mauritius",
                "code": "MRU",
                "enabled": True,
                "aliases": ["Port Louis"]
            },
            {
                "name": "Cape Town",
                "code": "CPT",
                "enabled": True,
                "aliases": ["Western Cape", "V&A Waterfront"]
            },
            {
                "name": "Seychelles",
                "code": "SEZ",
                "enabled": True,
                "aliases": ["Mahe", "Praslin", "La Digue"]
            },
            {
                "name": "Maldives",
                "code": "MLE",
                "enabled": True,
                "aliases": ["Male"]
            },
            {
                "name": "Tanzania",
                "code": "TZA",
                "enabled": True,
                "aliases": ["Serengeti", "Ngorongoro", "Kilimanjaro", "Arusha"]
            },
            {
                "name": "South Africa",
                "code": "ZAF",
                "enabled": True,
                "aliases": ["Johannesburg", "Kruger", "Garden Route", "Durban"]
            },
            {
                "name": "Victoria Falls",
                "code": "VFA",
                "enabled": True,
                "aliases": ["Vic Falls", "Zimbabwe", "Livingstone"]
            },
            {
                "name": "Botswana",
                "code": "BWA",
                "enabled": True,
                "aliases": ["Chobe", "Okavango Delta", "Kasane"]
            },
            {
                "name": "Mozambique",
                "code": "MOZ",
                "enabled": True,
                "aliases": ["Vilanculos", "Bazaruto", "Inhambane", "Tofo"]
            },
            {
                "name": "Rwanda",
                "code": "RWA",
                "enabled": True,
                "aliases": ["Kigali", "Gorilla Trekking"]
            },
            {
                "name": "Uganda",
                "code": "UGA",
                "enabled": True,
                "aliases": ["Kampala", "Bwindi"]
            }
        ],
        "consultants": []
    }

    # Write config.yaml
    config_path = base_path / "client.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    logger.info(f"Created tenant config at {config_path}")
    return True


# ==================== Status Endpoint ====================

@onboarding_router.get("/status/{tenant_id}")
async def get_onboarding_status(tenant_id: str):
    """Check onboarding status for a tenant"""
    config_path = Path(__file__).parent.parent.parent / "clients" / tenant_id / "client.yaml"

    if not config_path.exists():
        return {
            "tenant_id": tenant_id,
            "exists": False,
            "status": "not_started"
        }

    try:
        from config.loader import ClientConfig
        config = ClientConfig(tenant_id)

        return {
            "tenant_id": tenant_id,
            "exists": True,
            "status": "completed",
            "config": {
                "company_name": config.company_name,
                "sendgrid_configured": bool(config.sendgrid_api_key)
            }
        }
    except Exception as e:
        return {
            "tenant_id": tenant_id,
            "exists": True,
            "status": "error",
            "error": str(e)
        }
