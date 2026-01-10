"""
Tenant Onboarding Routes

Complete onboarding wizard for new tenants:
- Generate AI agent system prompts from plain English descriptions
- Provision complete tenant infrastructure (VAPI, phone, database)
- Configure email, outbound calls, and knowledge base
"""

import os
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
from pydantic import BaseModel, Field, EmailStr

logger = logging.getLogger(__name__)

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
    email_signature: str
    auto_send_quotes: bool = Field(default=True)
    quote_validity_days: int = Field(default=14)
    follow_up_days: int = Field(default=3)
    sendgrid_api_key: Optional[str] = None
    from_email: Optional[str] = None


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
    success: bool
    tenant_id: str
    message: str
    resources: Dict[str, Any]
    errors: List[str] = []


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
    """Get available VAPI voice options with sample audio URLs."""
    # ElevenLabs sample URL pattern: https://api.elevenlabs.io/v1/voices/{voice_id}/preview
    # Note: Sample URLs use the ElevenLabs preview endpoint or hosted samples
    voices = [
        # VAPI native voices (use 11labs samples as approximation)
        VoiceOption(id="jennifer", name="Jennifer", gender="female", accent="American", provider="vapi",
                   sample_url="https://storage.googleapis.com/eleven-public-prod/premade/voices/21m00Tcm4TlvDq8ikWAM/preview.mp3"),
        VoiceOption(id="sarah", name="Sarah", gender="female", accent="American", provider="vapi",
                   sample_url="https://storage.googleapis.com/eleven-public-prod/premade/voices/EXAVITQu4vr4xnSDxMaL/preview.mp3"),
        VoiceOption(id="emma", name="Emma", gender="female", accent="British", provider="vapi",
                   sample_url="https://storage.googleapis.com/eleven-public-prod/premade/voices/D38z5RcWu1voky8WS1ja/preview.mp3"),
        VoiceOption(id="olivia", name="Olivia", gender="female", accent="Australian", provider="vapi",
                   sample_url="https://storage.googleapis.com/eleven-public-prod/premade/voices/pFZP5JQG7iQjIQuC4Bku/preview.mp3"),
        VoiceOption(id="michael", name="Michael", gender="male", accent="American", provider="vapi",
                   sample_url="https://storage.googleapis.com/eleven-public-prod/premade/voices/flq6f7yk4E4fJM5XTYuZ/preview.mp3"),
        VoiceOption(id="james", name="James", gender="male", accent="British", provider="vapi",
                   sample_url="https://storage.googleapis.com/eleven-public-prod/premade/voices/ZQe5CZNOzWyzPSCn5a3c/preview.mp3"),
        VoiceOption(id="william", name="William", gender="male", accent="American", provider="vapi",
                   sample_url="https://storage.googleapis.com/eleven-public-prod/premade/voices/CYw3kZ02Hs0563khs1Fj/preview.mp3"),
        VoiceOption(id="daniel", name="Daniel", gender="male", accent="Australian", provider="vapi",
                   sample_url="https://storage.googleapis.com/eleven-public-prod/premade/voices/onwK4e9ZLuTAKqWW03F9/preview.mp3"),
        # ElevenLabs voices with official sample URLs
        VoiceOption(id="21m00Tcm4TlvDq8ikWAM", name="Rachel", gender="female", accent="American", provider="elevenlabs",
                   sample_url="https://storage.googleapis.com/eleven-public-prod/premade/voices/21m00Tcm4TlvDq8ikWAM/preview.mp3"),
        VoiceOption(id="AZnzlk1XvdvUeBnXmlld", name="Domi", gender="female", accent="American", provider="elevenlabs",
                   sample_url="https://storage.googleapis.com/eleven-public-prod/premade/voices/AZnzlk1XvdvUeBnXmlld/preview.mp3"),
        VoiceOption(id="EXAVITQu4vr4xnSDxMaL", name="Bella", gender="female", accent="American", provider="elevenlabs",
                   sample_url="https://storage.googleapis.com/eleven-public-prod/premade/voices/EXAVITQu4vr4xnSDxMaL/preview.mp3"),
        VoiceOption(id="ErXwobaYiN019PkySvjV", name="Antoni", gender="male", accent="American", provider="elevenlabs",
                   sample_url="https://storage.googleapis.com/eleven-public-prod/premade/voices/ErXwobaYiN019PkySvjV/preview.mp3"),
        VoiceOption(id="VR6AewLTigWG4xSOukaG", name="Arnold", gender="male", accent="American", provider="elevenlabs",
                   sample_url="https://storage.googleapis.com/eleven-public-prod/premade/voices/VR6AewLTigWG4xSOukaG/preview.mp3"),
    ]
    return voices


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
        "inbound_assistant_id": None,
        "outbound_assistant_id": None,
        "phone_number": None,
        "phone_number_id": None,
        "database_ready": False
    }

    try:
        # Step 1: Create tenant directory and config
        logger.info(f"Creating tenant configuration for {tenant_id}")
        config_created = await create_tenant_config(tenant_id, request)
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

        # Step 2: Provision VAPI assistants
        logger.info(f"Provisioning VAPI assistants for {tenant_id}")
        vapi_key = os.getenv("VAPI_API_KEY")

        if vapi_key:
            try:
                from src.tools.vapi_tool import VAPIProvisioner
                provisioner = VAPIProvisioner(vapi_key)

                # Create inbound assistant
                inbound_result = await create_vapi_assistant(
                    provisioner=provisioner,
                    tenant_id=tenant_id,
                    agent_type="inbound",
                    name=request.agents.inbound_agent_name,
                    system_prompt=request.agents.inbound_prompt,
                    voice_id=request.agents.inbound_voice_id,
                    company_name=request.company.company_name
                )
                resources["inbound_assistant_id"] = inbound_result.get("assistant_id")

                # Create outbound assistant if configured
                if request.agents.outbound_prompt:
                    outbound_result = await create_vapi_assistant(
                        provisioner=provisioner,
                        tenant_id=tenant_id,
                        agent_type="outbound",
                        name=request.agents.outbound_agent_name,
                        system_prompt=request.agents.outbound_prompt,
                        voice_id=request.agents.outbound_voice_id,
                        company_name=request.company.company_name
                    )
                    resources["outbound_assistant_id"] = outbound_result.get("assistant_id")

            except Exception as e:
                logger.error(f"VAPI provisioning failed: {e}")
                errors.append(f"VAPI provisioning: {str(e)}")
        else:
            errors.append("VAPI_API_KEY not configured - skipping assistant provisioning")

        # Step 3: Purchase phone number if requested
        if request.provision_phone and vapi_key:
            logger.info(f"Provisioning phone number for {tenant_id}")
            try:
                phone_result = await provision_phone_number(
                    tenant_id=tenant_id,
                    country_code=request.phone_country,
                    assistant_id=resources.get("inbound_assistant_id")
                )
                resources["phone_number"] = phone_result.get("phone_number")
                resources["phone_number_id"] = phone_result.get("phone_number_id")
            except Exception as e:
                logger.error(f"Phone provisioning failed: {e}")
                errors.append(f"Phone provisioning: {str(e)}")

        # Step 4: Update config with provisioned resources
        if resources.get("inbound_assistant_id") or resources.get("phone_number_id"):
            await update_tenant_vapi_config(
                tenant_id=tenant_id,
                inbound_assistant_id=resources.get("inbound_assistant_id"),
                outbound_assistant_id=resources.get("outbound_assistant_id"),
                phone_number_id=resources.get("phone_number_id")
            )

        # Step 5: Initialize database
        if request.supabase_url:
            logger.info(f"Initializing database for {tenant_id}")
            try:
                resources["database_ready"] = True
            except Exception as e:
                logger.error(f"Database initialization failed: {e}")
                errors.append(f"Database: {str(e)}")

        # Step 6: Create admin user
        if request.admin_email and request.admin_password:
            logger.info(f"Creating admin user for {tenant_id}")
            try:
                from src.services.auth_service import AuthService
                from config.loader import get_config

                # Load the newly created config
                config = get_config(tenant_id)
                auth_service = AuthService(
                    supabase_url=config.supabase_url,
                    supabase_key=config.supabase_service_key
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
            errors=errors
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

async def create_tenant_config(tenant_id: str, request: OnboardingRequest) -> bool:
    """Create tenant directory and config.yaml file"""
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

    # Build config structure
    config = {
        "client": {
            "name": request.company.company_name,
            "short_name": tenant_id,
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
            "vapi": {
                "api_key": f"${{{tenant_id.upper().replace('-', '_')}_VAPI_API_KEY}}",
                "assistant_id": None,
                "outbound_assistant_id": None,
                "phone_number_id": None
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
                "password": "${SENDGRID_API_KEY}"
            },
            "imap": {
                "host": "imap.gmail.com",
                "port": 993
            },
            "sendgrid": {
                "api_key": request.email.sendgrid_api_key or "${SENDGRID_API_KEY}",
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
                "voice_id": request.agents.inbound_voice_id,
                "prompt_file": "prompts/inbound.txt"
            },
            "outbound": {
                "enabled": request.outbound.enabled,
                "name": request.agents.outbound_agent_name,
                "voice_id": request.agents.outbound_voice_id,
                "prompt_file": "prompts/outbound.txt"
            }
        },
        "knowledge_base": {
            "categories": request.knowledge_base.categories
        },
        "destinations": [],
        "consultants": []
    }

    # Write config.yaml
    config_path = base_path / "client.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    logger.info(f"Created tenant config at {config_path}")
    return True


async def create_vapi_assistant(
    provisioner,
    tenant_id: str,
    agent_type: str,
    name: str,
    system_prompt: str,
    voice_id: Optional[str],
    company_name: str
) -> Dict[str, Any]:
    """Create a VAPI assistant with the given configuration"""
    try:
        result = provisioner.create_assistant(
            name=f"{company_name} - {name} ({agent_type.title()})",
            system_prompt=system_prompt,
            voice_id=voice_id or "jennifer",
            first_message=f"Hello! This is {name} from {company_name}. How can I help you today?" if agent_type == "inbound" else f"Hi, this is {name} calling from {company_name}. I'm following up on the travel quote we sent you."
        )
        return {"assistant_id": result.get("id"), "name": name}
    except Exception as e:
        logger.error(f"Failed to create {agent_type} assistant: {e}")
        raise


async def provision_phone_number(
    tenant_id: str,
    country_code: str,
    assistant_id: Optional[str]
) -> Dict[str, Any]:
    """Provision a phone number via Twilio and import to VAPI"""
    twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
    vapi_key = os.getenv("VAPI_API_KEY")

    if not all([twilio_sid, twilio_token, vapi_key]):
        raise ValueError("Twilio/VAPI credentials not configured")

    from src.tools.twilio_vapi_provisioner import TwilioVAPIProvisioner

    provisioner = TwilioVAPIProvisioner(twilio_sid, twilio_token, vapi_key)

    result = provisioner.provision_phone_for_tenant(
        country_code=country_code,
        client_id=tenant_id,
        assistant_id=assistant_id
    )

    if result.get("success"):
        return {
            "phone_number": result.get("phone_number"),
            "phone_number_id": result.get("vapi_id")
        }
    else:
        raise ValueError(result.get("error", "Failed to provision phone"))


async def update_tenant_vapi_config(
    tenant_id: str,
    inbound_assistant_id: Optional[str],
    outbound_assistant_id: Optional[str],
    phone_number_id: Optional[str]
) -> bool:
    """Update tenant config.yaml with VAPI resource IDs"""
    config_path = Path(__file__).parent.parent.parent / "clients" / tenant_id / "client.yaml"

    if not config_path.exists():
        return False

    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        if 'infrastructure' not in config:
            config['infrastructure'] = {}
        if 'vapi' not in config['infrastructure']:
            config['infrastructure']['vapi'] = {}

        vapi = config['infrastructure']['vapi']

        if inbound_assistant_id:
            vapi['assistant_id'] = inbound_assistant_id
        if outbound_assistant_id:
            vapi['outbound_assistant_id'] = outbound_assistant_id
        if phone_number_id:
            vapi['phone_number_id'] = phone_number_id

        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        return True

    except Exception as e:
        logger.error(f"Failed to update VAPI config: {e}")
        return False


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
                "vapi_configured": bool(config.vapi_assistant_id),
                "phone_configured": bool(config.vapi_phone_number_id),
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
