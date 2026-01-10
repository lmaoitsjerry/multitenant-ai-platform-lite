"""
Template Renderer - Jinja2 Templates for Emails and PDFs

Provides template rendering with client-specific branding.

Usage:
    from config.loader import ClientConfig
    from src.utils.template_renderer import TemplateRenderer
    
    config = ClientConfig('africastay')
    renderer = TemplateRenderer(config)
    
    html = renderer.render_template('emails/quote.html', {
        'customer_name': 'John Doe',
        'destination': 'Zanzibar'
    })
"""

from jinja2 import Environment, FileSystemLoader, Template
from pathlib import Path
from typing import Dict, Any
import logging

from config.loader import ClientConfig

logger = logging.getLogger(__name__)


class TemplateRenderer:
    """Render Jinja2 templates with client-specific context"""
    
    def __init__(self, config: ClientConfig):
        """
        Initialize template renderer
        
        Args:
            config: ClientConfig instance
        """
        self.config = config
        
        # Set up Jinja2 environment
        template_dir = Path(__file__).parent.parent.parent / "templates"
        self.env = Environment(loader=FileSystemLoader(str(template_dir)))
        
        # Build base context with client info
        self.base_context = {
            'client': {
                'name': config.name,
                'short_name': config.short_name,
                'timezone': config.timezone,
            },
            'branding': {
                'company_name': config.company_name,
                'logo_url': config.logo_url,
                'primary_color': config.primary_color,
                'secondary_color': config.secondary_color,
                'email_signature': config.email_signature,
            },
            'email': {
                'primary': config.primary_email,
            },
            'destinations': config.destinations,
        }
        
        logger.info(f"Template renderer initialized for {config.client_id}")
    
    def render_template(self, template_name: str, context: Dict[str, Any] = None) -> str:
        """
        Render a template with context
        
        Args:
            template_name: Template file path (e.g., 'emails/quote.html')
            context: Additional context variables
        
        Returns:
            Rendered template string
        """
        try:
            # Merge base context with provided context
            full_context = {**self.base_context}
            if context:
                full_context.update(context)
            
            # Load and render template
            template = self.env.get_template(template_name)
            rendered = template.render(**full_context)
            
            logger.info(f"✅ Rendered template: {template_name}")
            return rendered
            
        except Exception as e:
            logger.error(f"❌ Failed to render template {template_name}: {e}")
            raise
    
    def render_string(self, template_string: str, context: Dict[str, Any] = None) -> str:
        """
        Render a template from string
        
        Args:
            template_string: Template content as string
            context: Context variables
        
        Returns:
            Rendered string
        """
        try:
            # Merge contexts
            full_context = {**self.base_context}
            if context:
                full_context.update(context)
            
            # Render from string
            template = Template(template_string)
            rendered = template.render(**full_context)
            
            return rendered
            
        except Exception as e:
            logger.error(f"❌ Failed to render template string: {e}")
            raise
    
    def render_agent_prompt(self, agent_type: str, context: Dict[str, Any] = None) -> str:
        """
        Render agent prompt from client-specific file
        
        Args:
            agent_type: 'inbound', 'helpdesk', or 'outbound'
            context: Additional context variables
        
        Returns:
            Rendered prompt string
        """
        try:
            # Load prompt file from client directory
            prompt_path = self.config.get_prompt_path(agent_type)
            
            with open(prompt_path, 'r') as f:
                prompt_template = f.read()
            
            # Render with context
            rendered = self.render_string(prompt_template, context)
            
            logger.info(f"✅ Rendered {agent_type} agent prompt")
            return rendered
            
        except Exception as e:
            logger.error(f"❌ Failed to render {agent_type} agent prompt: {e}")
            raise
