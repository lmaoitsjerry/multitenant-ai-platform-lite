"""
Supabase Tool - Multi-Tenant Version

Handles operational data in Supabase (PostgreSQL):
- Outbound call queue
- Call records
- Inbound tickets
- Invoices
- Helpdesk sessions

Usage:
    from config.loader import ClientConfig
    from src.tools.supabase_tool import SupabaseTool

    config = ClientConfig('africastay')
    sb = SupabaseTool(config)
    
    # Queue a call
    sb.queue_outbound_call({...})
    
    # Create ticket
    sb.create_ticket({...})
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Callable, TypeVar
from datetime import datetime, timedelta
import uuid
from functools import wraps

from config.loader import ClientConfig

T = TypeVar('T')


def run_sync(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator that runs a synchronous function in a thread pool.
    Use this for all Supabase operations to avoid blocking the event loop.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await asyncio.to_thread(func, *args, **kwargs)
    return wrapper


async def execute_async(operation: Callable[[], T]) -> T:
    """
    Execute a synchronous Supabase operation in a thread pool.
    Usage: result = await execute_async(lambda: client.table('x').select('*').execute())
    """
    return await asyncio.to_thread(operation)

logger = logging.getLogger(__name__)

try:
    from supabase import create_client, Client
except ImportError:
    create_client = None
    Client = None
    logger.warning("Supabase not installed. Supabase operations will not work.")

# ==================== Client Cache ====================
# Cache Supabase clients to avoid reinitializing on every request
_supabase_client_cache: Dict[str, Client] = {}


def get_cached_supabase_client(supabase_url: str, supabase_key: str, client_id: str) -> Optional[Client]:
    """Get or create a cached Supabase client"""
    cache_key = f"{client_id}:{supabase_url[:20]}"

    if cache_key not in _supabase_client_cache:
        if create_client:
            try:
                _supabase_client_cache[cache_key] = create_client(supabase_url, supabase_key)
                logger.info(f"Supabase client created and cached for {client_id}")
            except Exception as e:
                logger.error(f"Failed to create Supabase client: {e}")
                return None
        else:
            return None

    return _supabase_client_cache.get(cache_key)


class SupabaseTool:
    """Supabase operations for operational data"""

    # Table names (these could also be in config if needed)
    TABLE_CALL_QUEUE = "outbound_call_queue"
    TABLE_CALL_RECORDS = "call_records"
    TABLE_TICKETS = "inbound_tickets"
    TABLE_INVOICES = "invoices"
    TABLE_INVOICE_TRAVELERS = "invoice_travelers"
    TABLE_HELPDESK_SESSIONS = "helpdesk_sessions"
    TABLE_CLIENTS = "clients"
    TABLE_ACTIVITIES = "activities"
    TABLE_QUOTES = "quotes"

    def __init__(self, config: ClientConfig):
        """
        Initialize Supabase tool with client configuration

        Args:
            config: ClientConfig instance
        """
        self.config = config
        self.tenant_id = config.client_id  # For row-level filtering

        # Use cached client to avoid reinitializing on every request
        self.client = get_cached_supabase_client(
            config.supabase_url,
            config.supabase_service_key or config.supabase_anon_key,
            config.client_id
        )

        if not self.client and create_client is None:
            logger.warning("Supabase library not available")

    # ==================== Call Queue Operations ====================

    def queue_outbound_call(
        self,
        client_name: str,
        client_email: str,
        phone_number: str,
        quote_details: Dict[str, Any],
        consultant_id: Optional[str] = None,
        consultant_email: Optional[str] = None,
        scheduled_time: Optional[datetime] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Add call to outbound queue
        
        Args:
            client_name: Customer name
            client_email: Customer email
            phone_number: Phone number to call
            quote_details: Quote data for call script
            consultant_id: Assigned consultant ID
            consultant_email: Consultant email
            scheduled_time: When to make the call (defaults to now)
            
        Returns:
            Created queue record or None
        """
        if not self.client:
            return None
        
        try:
            record = {
                'tenant_id': self.tenant_id,
                'client_name': client_name,
                'client_email': client_email,
                'phone_number': phone_number,
                'quote_details': quote_details,
                'call_status': 'queued',
                'scheduled_call_time': (scheduled_time or datetime.utcnow()).isoformat(),
                'consultant_id': consultant_id,
                'consultant_email': consultant_email,
                'created_at': datetime.utcnow().isoformat()
            }
            
            result = self.client.table(self.TABLE_CALL_QUEUE).insert(record).execute()
            
            if result.data:
                logger.info(f"✅ Call queued for {phone_number}")
                return result.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Failed to queue call: {e}")
            return None

    def get_pending_calls(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get calls ready to be made"""
        if not self.client:
            return []
        
        try:
            now = datetime.utcnow().isoformat()
            
            result = self.client.table(self.TABLE_CALL_QUEUE)\
                .select("*")\
                .eq('tenant_id', self.tenant_id)\
                .eq('call_status', 'queued')\
                .lte('scheduled_call_time', now)\
                .order('scheduled_call_time')\
                .limit(limit)\
                .execute()
            
            return result.data or []
            
        except Exception as e:
            logger.error(f"Failed to get pending calls: {e}")
            return []

    def update_call_status(
        self,
        queue_id: str,
        status: str,
        call_id: Optional[str] = None,
        outcome: Optional[str] = None
    ) -> bool:
        """Update call queue status"""
        if not self.client:
            return False
        
        try:
            update_data = {
                'call_status': status,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            if call_id:
                update_data['call_id'] = call_id
            if outcome:
                update_data['outcome'] = outcome
            
            self.client.table(self.TABLE_CALL_QUEUE)\
                .update(update_data)\
                .eq('id', queue_id)\
                .eq('tenant_id', self.tenant_id)\
                .execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update call status: {e}")
            return False

    def save_call_record(
        self,
        call_id: str,
        phone_number: str,
        transcript: str,
        outcome: str,
        duration_seconds: int,
        customer_name: Optional[str] = None,
        customer_email: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Save completed call record"""
        if not self.client:
            return None
        
        try:
            record = {
                'tenant_id': self.tenant_id,
                'call_id': call_id,
                'phone_number': phone_number,
                'customer_name': customer_name,
                'customer_email': customer_email,
                'transcript': transcript,
                'outcome': outcome,
                'duration_seconds': duration_seconds,
                'metadata': metadata or {},
                'created_at': datetime.utcnow().isoformat()
            }
            
            result = self.client.table(self.TABLE_CALL_RECORDS).insert(record).execute()
            
            if result.data:
                logger.info(f"✅ Call record saved: {call_id}")
                return result.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Failed to save call record: {e}")
            return None

    # ==================== Ticket Operations ====================

    def create_ticket(
        self,
        customer_name: str,
        customer_email: str,
        subject: str,
        message: str,
        source: str = 'web',
        priority: str = 'normal',
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create inbound ticket
        
        Args:
            customer_name: Customer name
            customer_email: Customer email
            subject: Ticket subject
            message: Initial message
            source: Source (web, email, phone, chat)
            priority: Priority (low, normal, high, urgent)
            metadata: Additional metadata
            
        Returns:
            Created ticket or None
        """
        if not self.client:
            return None
        
        try:
            ticket_id = f"TKT-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
            
            record = {
                'tenant_id': self.tenant_id,
                'ticket_id': ticket_id,
                'customer_name': customer_name,
                'customer_email': customer_email,
                'subject': subject,
                'message': message,
                'source': source,
                'priority': priority,
                'status': 'open',
                'metadata': metadata or {},
                'created_at': datetime.utcnow().isoformat()
            }
            
            result = self.client.table(self.TABLE_TICKETS).insert(record).execute()
            
            if result.data:
                logger.info(f"✅ Ticket created: {ticket_id}")
                return result.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Failed to create ticket: {e}")
            return None

    def get_tickets(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get tickets with optional filtering"""
        if not self.client:
            return []
        
        try:
            query = self.client.table(self.TABLE_TICKETS)\
                .select("*")\
                .eq('tenant_id', self.tenant_id)
            
            if status:
                query = query.eq('status', status)
            
            result = query\
                .order('created_at', desc=True)\
                .range(offset, offset + limit - 1)\
                .execute()
            
            return result.data or []
            
        except Exception as e:
            logger.error(f"Failed to get tickets: {e}")
            return []

    def update_ticket(
        self,
        ticket_id: str,
        status: Optional[str] = None,
        assigned_to: Optional[str] = None,
        notes: Optional[str] = None
    ) -> bool:
        """Update ticket"""
        if not self.client:
            return False
        
        try:
            update_data = {'updated_at': datetime.utcnow().isoformat()}
            
            if status:
                update_data['status'] = status
            if assigned_to:
                update_data['assigned_to'] = assigned_to
            if notes:
                update_data['notes'] = notes
            
            self.client.table(self.TABLE_TICKETS)\
                .update(update_data)\
                .eq('ticket_id', ticket_id)\
                .eq('tenant_id', self.tenant_id)\
                .execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update ticket: {e}")
            return False

    # ==================== Invoice Operations ====================

    def create_invoice(
        self,
        customer_name: str,
        customer_email: str,
        items: List[Dict[str, Any]],
        total_amount: float,
        currency: str = 'ZAR',
        due_date: Optional[datetime] = None,
        notes: Optional[str] = None,
        quote_id: Optional[str] = None,
        customer_phone: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create invoice (optionally from quote)

        Args:
            customer_name: Customer name
            customer_email: Customer email
            items: List of invoice items
            total_amount: Total invoice amount
            currency: Currency code
            due_date: Payment due date
            notes: Additional notes
            quote_id: Related quote ID (optional for manual invoices)
            customer_phone: Customer phone (optional)

        Returns:
            Created invoice or None
        """
        if not self.client:
            return None
        
        try:
            invoice_id = f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
            
            if not due_date:
                due_date = datetime.utcnow() + timedelta(days=7)
            
            record = {
                'tenant_id': self.tenant_id,
                'invoice_id': invoice_id,
                'quote_id': quote_id,  # Can be None for manual invoices
                'customer_name': customer_name,
                'customer_email': customer_email,
                'customer_phone': customer_phone,
                'items': items,
                'total_amount': total_amount,
                'currency': currency,
                'status': 'draft',
                'due_date': due_date.isoformat(),
                'notes': notes,
                'created_at': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Creating invoice with record: {record}")
            result = self.client.table(self.TABLE_INVOICES).insert(record).execute()

            if result.data:
                logger.info(f"✅ Invoice created: {invoice_id}")
                return result.data[0]
            logger.error(f"Invoice insert returned no data")
            return None

        except Exception as e:
            logger.error(f"Failed to create invoice: {e}", exc_info=True)
            raise  # Re-raise to let caller handle it

    def get_invoice(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        """Get invoice by ID"""
        if not self.client:
            return None
        
        try:
            result = self.client.table(self.TABLE_INVOICES)\
                .select("*")\
                .eq('invoice_id', invoice_id)\
                .eq('tenant_id', self.tenant_id)\
                .single()\
                .execute()
            
            return result.data
            
        except Exception as e:
            logger.error(f"Failed to get invoice: {e}")
            return None

    def update_invoice_status(
        self,
        invoice_id: str,
        status: str,
        payment_date: Optional[datetime] = None,
        payment_reference: Optional[str] = None
    ) -> bool:
        """Update invoice status"""
        if not self.client:
            return False
        
        try:
            update_data = {
                'status': status,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            if payment_date:
                update_data['payment_date'] = payment_date.isoformat()
            if payment_reference:
                update_data['payment_reference'] = payment_reference
            
            self.client.table(self.TABLE_INVOICES)\
                .update(update_data)\
                .eq('invoice_id', invoice_id)\
                .eq('tenant_id', self.tenant_id)\
                .execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update invoice status: {e}")
            return False

    def list_invoices(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List invoices with optional filtering, enriched with destination"""
        if not self.client:
            return []

        try:
            query = self.client.table(self.TABLE_INVOICES)\
                .select("*")\
                .eq('tenant_id', self.tenant_id)

            if status:
                query = query.eq('status', status)

            result = query\
                .order('created_at', desc=True)\
                .range(offset, offset + limit - 1)\
                .execute()

            invoices = result.data or []

            # First pass: try to get destination from items
            quote_ids_needed = []
            for invoice in invoices:
                if not invoice.get('destination'):
                    items = invoice.get('items', [])
                    if items and isinstance(items, list) and len(items) > 0:
                        invoice['destination'] = items[0].get('destination')

                    # Still no destination? Need to fetch from quote
                    if not invoice.get('destination') and invoice.get('quote_id'):
                        quote_ids_needed.append(invoice['quote_id'])

            # Batch fetch all missing destinations in ONE query (avoid N+1)
            if quote_ids_needed:
                try:
                    quote_result = self.client.table(self.TABLE_QUOTES)\
                        .select("quote_id, destination")\
                        .eq('tenant_id', self.tenant_id)\
                        .in_('quote_id', quote_ids_needed)\
                        .execute()

                    # Build lookup map
                    dest_map = {q['quote_id']: q.get('destination') for q in (quote_result.data or [])}

                    # Apply destinations to invoices
                    for invoice in invoices:
                        if not invoice.get('destination') and invoice.get('quote_id'):
                            invoice['destination'] = dest_map.get(invoice['quote_id'])
                except Exception as e:
                    logger.debug(f"Could not batch fetch quote destinations: {e}")

            return invoices

        except Exception as e:
            logger.error(f"Failed to list invoices: {e}")
            return []

    # ==================== CRM Client Operations ====================

    def create_client(
        self,
        email: str,
        name: str,
        phone: Optional[str] = None,
        source: str = 'quote',
        consultant_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create CRM client record
        
        Args:
            email: Client email (unique per tenant)
            name: Client name
            phone: Client phone
            source: Lead source
            consultant_id: Assigned consultant
            metadata: Additional data
            
        Returns:
            Created client or None
        """
        if not self.client:
            return None
        
        try:
            client_id = str(uuid.uuid4())
            
            record = {
                'tenant_id': self.tenant_id,
                'client_id': client_id,
                'email': email.lower(),
                'name': name,
                'phone': phone,
                'source': source,
                'pipeline_stage': 'QUOTED',
                'consultant_id': consultant_id,
                'metadata': metadata or {},
                'created_at': datetime.utcnow().isoformat(),
                'last_contact_at': datetime.utcnow().isoformat()
            }
            
            result = self.client.table(self.TABLE_CLIENTS).insert(record).execute()
            
            if result.data:
                logger.info(f"✅ CRM client created: {email}")
                return result.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Failed to create client: {e}")
            return None

    def get_client_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get client by email"""
        if not self.client:
            return None
        
        try:
            result = self.client.table(self.TABLE_CLIENTS)\
                .select("*")\
                .eq('tenant_id', self.tenant_id)\
                .eq('email', email.lower())\
                .single()\
                .execute()
            
            return result.data
            
        except Exception as e:
            # Client not found is not an error
            return None

    def update_client_stage(
        self,
        client_id: str,
        stage: str,
        notes: Optional[str] = None
    ) -> bool:
        """Update client pipeline stage"""
        if not self.client:
            return False
        
        valid_stages = ['QUOTED', 'NEGOTIATING', 'BOOKED', 'PAID', 'TRAVELLED', 'LOST']
        if stage not in valid_stages:
            logger.error(f"Invalid stage: {stage}")
            return False
        
        try:
            update_data = {
                'pipeline_stage': stage,
                'last_contact_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            self.client.table(self.TABLE_CLIENTS)\
                .update(update_data)\
                .eq('client_id', client_id)\
                .eq('tenant_id', self.tenant_id)\
                .execute()
            
            # Log activity
            if notes:
                self.log_activity(client_id, 'stage_change', f"Stage changed to {stage}: {notes}")
            else:
                self.log_activity(client_id, 'stage_change', f"Stage changed to {stage}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update client stage: {e}")
            return False

    def log_activity(
        self,
        client_id: str,
        activity_type: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Log CRM activity"""
        if not self.client:
            return False
        
        try:
            record = {
                'tenant_id': self.tenant_id,
                'client_id': client_id,
                'activity_type': activity_type,
                'description': description,
                'metadata': metadata or {},
                'created_at': datetime.utcnow().isoformat()
            }
            
            self.client.table(self.TABLE_ACTIVITIES).insert(record).execute()
            return True
            
        except Exception as e:
            logger.error(f"Failed to log activity: {e}")
            return False

    def get_client_activities(
        self,
        client_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get activities for a client"""
        if not self.client:
            return []
        
        try:
            result = self.client.table(self.TABLE_ACTIVITIES)\
                .select("*")\
                .eq('tenant_id', self.tenant_id)\
                .eq('client_id', client_id)\
                .order('created_at', desc=True)\
                .limit(limit)\
                .execute()
            
            return result.data or []
            
        except Exception as e:
            logger.error(f"Failed to get activities: {e}")
            return []

    # ==================== Helpdesk Operations ====================

    def create_helpdesk_session(
        self,
        employee_email: str,
        employee_name: str
    ) -> Optional[Dict[str, Any]]:
        """Create helpdesk chat session"""
        if not self.client:
            return None
        
        try:
            session_id = str(uuid.uuid4())
            
            record = {
                'tenant_id': self.tenant_id,
                'session_id': session_id,
                'employee_email': employee_email,
                'employee_name': employee_name,
                'messages': [],
                'status': 'active',
                'created_at': datetime.utcnow().isoformat()
            }
            
            result = self.client.table(self.TABLE_HELPDESK_SESSIONS).insert(record).execute()
            
            if result.data:
                return result.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Failed to create helpdesk session: {e}")
            return None

    def add_helpdesk_message(
        self,
        session_id: str,
        role: str,
        content: str
    ) -> bool:
        """Add message to helpdesk session"""
        if not self.client:
            return False

        try:
            # Get current session
            result = self.client.table(self.TABLE_HELPDESK_SESSIONS)\
                .select("messages")\
                .eq('session_id', session_id)\
                .eq('tenant_id', self.tenant_id)\
                .single()\
                .execute()

            if not result.data:
                return False

            messages = result.data.get('messages', [])
            messages.append({
                'role': role,
                'content': content,
                'timestamp': datetime.utcnow().isoformat()
            })

            self.client.table(self.TABLE_HELPDESK_SESSIONS)\
                .update({'messages': messages, 'updated_at': datetime.utcnow().isoformat()})\
                .eq('session_id', session_id)\
                .eq('tenant_id', self.tenant_id)\
                .execute()

            return True

        except Exception as e:
            logger.error(f"Failed to add helpdesk message: {e}")
            return False

    # ==================== Branding Operations ====================

    TABLE_BRANDING = "tenant_branding"

    def get_branding(self) -> Optional[Dict[str, Any]]:
        """
        Get tenant branding configuration

        Returns:
            Branding record or None if not found
        """
        if not self.client:
            return None

        try:
            result = self.client.table(self.TABLE_BRANDING)\
                .select("*")\
                .eq('tenant_id', self.tenant_id)\
                .single()\
                .execute()

            return result.data

        except Exception as e:
            # No branding record is normal for new tenants
            logger.debug(f"No branding found for {self.tenant_id}: {e}")
            return None

    def create_branding(
        self,
        preset_theme: str = "professional_blue",
        colors: Optional[Dict[str, str]] = None,
        fonts: Optional[Dict[str, str]] = None,
        logo_url: Optional[str] = None,
        logo_dark_url: Optional[str] = None,
        favicon_url: Optional[str] = None,
        dark_mode_enabled: bool = False,
        custom_css: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create branding configuration for tenant

        Args:
            preset_theme: Theme preset name
            colors: Color overrides
            fonts: Font overrides
            logo_url: Primary logo URL
            logo_dark_url: Dark mode logo URL
            favicon_url: Favicon URL
            dark_mode_enabled: Enable dark mode
            custom_css: Custom CSS overrides

        Returns:
            Created branding record or None
        """
        if not self.client:
            return None

        try:
            record = {
                'tenant_id': self.tenant_id,
                'preset_theme': preset_theme,
                'dark_mode_enabled': dark_mode_enabled,
                'logo_url': logo_url,
                'logo_dark_url': logo_dark_url,
                'favicon_url': favicon_url,
                'custom_css': custom_css,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }

            # Add color fields if provided
            if colors:
                for key, value in colors.items():
                    db_key = f"color_{key}"
                    record[db_key] = value

            # Add font fields if provided
            if fonts:
                if fonts.get('heading'):
                    record['font_family_heading'] = fonts['heading']
                if fonts.get('body'):
                    record['font_family_body'] = fonts['body']

            result = self.client.table(self.TABLE_BRANDING).insert(record).execute()

            if result.data:
                logger.info(f"Branding created for {self.tenant_id}")
                return result.data[0]
            return None

        except Exception as e:
            logger.error(f"Failed to create branding: {e}")
            return None

    def update_branding(
        self,
        preset_theme: Optional[str] = None,
        colors: Optional[Dict[str, str]] = None,
        fonts: Optional[Dict[str, str]] = None,
        logo_url: Optional[str] = None,
        logo_dark_url: Optional[str] = None,
        favicon_url: Optional[str] = None,
        dark_mode_enabled: Optional[bool] = None,
        custom_css: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update tenant branding configuration

        Args:
            preset_theme: Theme preset name
            colors: Color overrides (partial update supported)
            fonts: Font overrides (partial update supported)
            logo_url: Primary logo URL
            logo_dark_url: Dark mode logo URL
            favicon_url: Favicon URL
            dark_mode_enabled: Enable dark mode
            custom_css: Custom CSS overrides

        Returns:
            Updated branding record or None
        """
        if not self.client:
            return None

        try:
            # Check if branding exists
            existing = self.get_branding()

            if not existing:
                # Create new branding
                return self.create_branding(
                    preset_theme=preset_theme or "professional_blue",
                    colors=colors,
                    fonts=fonts,
                    logo_url=logo_url,
                    logo_dark_url=logo_dark_url,
                    favicon_url=favicon_url,
                    dark_mode_enabled=dark_mode_enabled or False,
                    custom_css=custom_css
                )

            # Build update data
            update_data = {'updated_at': datetime.utcnow().isoformat()}

            if preset_theme is not None:
                update_data['preset_theme'] = preset_theme
            if dark_mode_enabled is not None:
                update_data['dark_mode_enabled'] = dark_mode_enabled
            if logo_url is not None:
                update_data['logo_url'] = logo_url
            if logo_dark_url is not None:
                update_data['logo_dark_url'] = logo_dark_url
            if favicon_url is not None:
                update_data['favicon_url'] = favicon_url
            if custom_css is not None:
                update_data['custom_css'] = custom_css

            # Add color fields if provided
            if colors:
                for key, value in colors.items():
                    db_key = f"color_{key}"
                    update_data[db_key] = value

            # Add font fields if provided
            if fonts:
                if fonts.get('heading'):
                    update_data['font_family_heading'] = fonts['heading']
                if fonts.get('body'):
                    update_data['font_family_body'] = fonts['body']

            result = self.client.table(self.TABLE_BRANDING)\
                .update(update_data)\
                .eq('tenant_id', self.tenant_id)\
                .execute()

            if result.data:
                logger.info(f"Branding updated for {self.tenant_id}")
                return result.data[0]
            return None

        except Exception as e:
            logger.error(f"Failed to update branding: {e}")
            return None

    def delete_branding(self) -> bool:
        """
        Delete tenant branding (reset to defaults)

        Returns:
            True if deleted, False otherwise
        """
        if not self.client:
            return False

        try:
            self.client.table(self.TABLE_BRANDING)\
                .delete()\
                .eq('tenant_id', self.tenant_id)\
                .execute()

            logger.info(f"Branding deleted for {self.tenant_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete branding: {e}")
            return False

    def upload_logo_to_storage(
        self,
        file_content: bytes,
        file_name: str,
        logo_type: str = "primary"
    ) -> Optional[str]:
        """
        Upload logo to Supabase Storage

        Args:
            file_content: File bytes
            file_name: Original file name
            logo_type: Type of logo (primary, dark, favicon)

        Returns:
            Public URL of uploaded file or None

        Raises:
            Exception: With detailed error message if upload fails
        """
        if not self.client:
            raise Exception("Supabase client not initialized")

        # Determine file extension
        ext = file_name.split('.')[-1].lower() if '.' in file_name else 'png'

        # Build storage path
        storage_path = f"branding/{self.tenant_id}/{logo_type}.{ext}"

        try:
            # Get storage bucket
            bucket = self.client.storage.from_("tenant-assets")

            # Try to remove existing file first (ignore errors)
            try:
                bucket.remove([storage_path])
            except Exception:
                pass

            # Upload new file
            result = bucket.upload(
                path=storage_path,
                file=file_content,
                file_options={"content-type": f"image/{ext}"}
            )

            # Get public URL
            public_url = bucket.get_public_url(storage_path)

            logger.info(f"Logo uploaded: {public_url}")
            return public_url

        except Exception as e:
            error_msg = str(e)
            # Check for common Supabase storage errors
            if "bucket" in error_msg.lower() and "not found" in error_msg.lower():
                logger.error(f"Storage bucket 'tenant-assets' does not exist. Please create it in Supabase dashboard.")
                raise Exception("Storage bucket 'tenant-assets' not found. Please create it in Supabase Storage settings.")
            elif "permission" in error_msg.lower() or "policy" in error_msg.lower():
                logger.error(f"Storage permission error: {e}")
                raise Exception("Storage permission denied. Check bucket policies in Supabase.")
            else:
                logger.error(f"Failed to upload logo: {e}")
                raise Exception(f"Upload failed: {error_msg}")

    # ==================== Tenant Settings Methods ====================

    TABLE_TENANT_SETTINGS = "tenant_settings"

    def get_tenant_settings(self) -> Optional[Dict[str, Any]]:
        """
        Get tenant settings (email, banking, etc.)

        Returns:
            Settings record or None if not found
        """
        if not self.client:
            return None

        try:
            result = self.client.table(self.TABLE_TENANT_SETTINGS)\
                .select("*")\
                .eq("tenant_id", self.tenant_id)\
                .single()\
                .execute()

            return result.data

        except Exception as e:
            # Table might not exist or no record yet
            logger.debug(f"No tenant settings found: {e}")
            return None

    def update_tenant_settings(
        self,
        # Company settings
        company_name: Optional[str] = None,
        support_email: Optional[str] = None,
        support_phone: Optional[str] = None,
        website: Optional[str] = None,
        currency: Optional[str] = None,
        timezone: Optional[str] = None,
        # Email settings
        email_from_name: Optional[str] = None,
        email_from_email: Optional[str] = None,
        email_reply_to: Optional[str] = None,
        quotes_email: Optional[str] = None,
        # Banking settings
        bank_name: Optional[str] = None,
        bank_account_name: Optional[str] = None,
        bank_account_number: Optional[str] = None,
        bank_branch_code: Optional[str] = None,
        bank_swift_code: Optional[str] = None,
        payment_reference_prefix: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update tenant settings

        Returns:
            Updated settings record or None on failure
        """
        if not self.client:
            return None

        # Build update data
        update_data = {"tenant_id": self.tenant_id, "updated_at": "now()"}

        # Company settings
        if company_name is not None:
            update_data["company_name"] = company_name
        if support_email is not None:
            update_data["support_email"] = support_email
        if support_phone is not None:
            update_data["support_phone"] = support_phone
        if website is not None:
            update_data["website"] = website
        if currency is not None:
            update_data["currency"] = currency
        if timezone is not None:
            update_data["timezone"] = timezone

        # Email settings
        if email_from_name is not None:
            update_data["email_from_name"] = email_from_name
        if email_from_email is not None:
            update_data["email_from_email"] = email_from_email
        if email_reply_to is not None:
            update_data["email_reply_to"] = email_reply_to
        if quotes_email is not None:
            update_data["quotes_email"] = quotes_email
        if bank_name is not None:
            update_data["bank_name"] = bank_name
        if bank_account_name is not None:
            update_data["bank_account_name"] = bank_account_name
        if bank_account_number is not None:
            update_data["bank_account_number"] = bank_account_number
        if bank_branch_code is not None:
            update_data["bank_branch_code"] = bank_branch_code
        if bank_swift_code is not None:
            update_data["bank_swift_code"] = bank_swift_code
        if payment_reference_prefix is not None:
            update_data["payment_reference_prefix"] = payment_reference_prefix

        try:
            # Check if settings exist
            existing = self.get_tenant_settings()

            if existing:
                # Update existing
                result = self.client.table(self.TABLE_TENANT_SETTINGS)\
                    .update(update_data)\
                    .eq("tenant_id", self.tenant_id)\
                    .execute()
            else:
                # Create new
                result = self.client.table(self.TABLE_TENANT_SETTINGS)\
                    .insert(update_data)\
                    .execute()

            if result.data:
                return result.data[0]
            return None

        except Exception as e:
            logger.error(f"Failed to update tenant settings: {e}")
            return None

    # ==================== User Management Methods ====================

    TABLE_ORGANIZATION_USERS = "organization_users"
    TABLE_USER_INVITATIONS = "user_invitations"

    def get_organization_users(self, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """
        Get all users in the current tenant organization.

        Args:
            include_inactive: Include deactivated users

        Returns:
            List of user records
        """
        try:
            query = self.client.table(self.TABLE_ORGANIZATION_USERS)\
                .select("*")\
                .eq("tenant_id", self.tenant_id)\
                .order("created_at", desc=False)

            if not include_inactive:
                query = query.eq("is_active", True)

            result = query.execute()
            return result.data or []

        except Exception as e:
            logger.error(f"Failed to get organization users: {e}")
            return []

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific user by ID.

        Args:
            user_id: User's UUID

        Returns:
            User record or None
        """
        try:
            result = self.client.table(self.TABLE_ORGANIZATION_USERS)\
                .select("*")\
                .eq("id", user_id)\
                .eq("tenant_id", self.tenant_id)\
                .single()\
                .execute()

            return result.data

        except Exception as e:
            logger.error(f"Failed to get user by ID: {e}")
            return None

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Get user by email within the current tenant.

        Args:
            email: User's email address

        Returns:
            User record or None
        """
        try:
            result = self.client.table(self.TABLE_ORGANIZATION_USERS)\
                .select("*")\
                .eq("email", email)\
                .eq("tenant_id", self.tenant_id)\
                .execute()

            if result.data and len(result.data) > 0:
                return result.data[0]
            return None

        except Exception as e:
            logger.error(f"Failed to get user by email: {e}")
            return None

    def create_organization_user(
        self,
        auth_user_id: str,
        email: str,
        name: str,
        role: str = "user",
        invited_by: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new organization user record.

        Args:
            auth_user_id: Supabase auth.users ID
            email: User's email
            name: User's display name
            role: User role (admin/user)
            invited_by: ID of inviting user

        Returns:
            Created user record or None
        """
        try:
            record = {
                "tenant_id": self.tenant_id,
                "auth_user_id": auth_user_id,
                "email": email,
                "name": name,
                "role": role,
                "is_active": True,
                "invited_by": invited_by
            }

            result = self.client.table(self.TABLE_ORGANIZATION_USERS)\
                .insert(record)\
                .execute()

            return result.data[0] if result.data else None

        except Exception as e:
            logger.error(f"Failed to create organization user: {e}")
            return None

    def update_organization_user(
        self,
        user_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update an organization user.

        Args:
            user_id: User's UUID
            updates: Fields to update (name, role, is_active, phone)

        Returns:
            Updated user record or None if failed
        """
        try:
            # Only allow specific fields to be updated
            allowed_fields = {"name", "role", "is_active", "phone"}
            safe_updates = {k: v for k, v in updates.items() if k in allowed_fields}

            if not safe_updates:
                return None

            result = self.client.table(self.TABLE_ORGANIZATION_USERS)\
                .update(safe_updates)\
                .eq("id", user_id)\
                .eq("tenant_id", self.tenant_id)\
                .execute()

            return result.data[0] if result.data else None

        except Exception as e:
            logger.error(f"Failed to update organization user: {e}")
            return None

    def deactivate_user(self, user_id: str) -> bool:
        """
        Deactivate a user (soft delete).

        Args:
            user_id: User's UUID

        Returns:
            True if successful
        """
        result = self.update_organization_user(user_id, {"is_active": False})
        return result is not None

    # ==================== Invitation Methods ====================

    def create_invitation(
        self,
        email: str,
        name: str,
        role: str = "user",
        invited_by: str = None,
        expires_hours: int = 48
    ) -> Optional[Dict[str, Any]]:
        """
        Create a user invitation.

        Args:
            email: Email to invite
            name: Name of invitee
            role: Role to assign (admin/user)
            invited_by: ID of inviting user
            expires_hours: Hours until invitation expires

        Returns:
            Invitation record or None
        """
        import secrets
        from datetime import datetime, timedelta

        try:
            # Check if user already exists
            existing = self.get_user_by_email(email)
            if existing:
                logger.warning(f"User with email {email} already exists")
                return None

            # Check for existing invitation
            existing_invite = self.client.table(self.TABLE_USER_INVITATIONS)\
                .select("*")\
                .eq("email", email)\
                .eq("tenant_id", self.tenant_id)\
                .is_("accepted_at", "null")\
                .execute()

            if existing_invite.data:
                # Delete existing unaccepted invitation
                self.client.table(self.TABLE_USER_INVITATIONS)\
                    .delete()\
                    .eq("email", email)\
                    .eq("tenant_id", self.tenant_id)\
                    .is_("accepted_at", "null")\
                    .execute()

            # Generate secure token
            token = secrets.token_urlsafe(48)

            # Calculate expiration
            expires_at = (datetime.utcnow() + timedelta(hours=expires_hours)).isoformat()

            record = {
                "tenant_id": self.tenant_id,
                "email": email,
                "name": name,
                "role": role,
                "token": token,
                "invited_by": invited_by,
                "expires_at": expires_at
            }

            result = self.client.table(self.TABLE_USER_INVITATIONS)\
                .insert(record)\
                .execute()

            return result.data[0] if result.data else None

        except Exception as e:
            logger.error(f"Failed to create invitation: {e}")
            return None

    def get_invitations(self, include_accepted: bool = False) -> List[Dict[str, Any]]:
        """
        Get all invitations for the current tenant.

        Args:
            include_accepted: Include already accepted invitations

        Returns:
            List of invitation records
        """
        try:
            query = self.client.table(self.TABLE_USER_INVITATIONS)\
                .select("*")\
                .eq("tenant_id", self.tenant_id)\
                .order("created_at", desc=True)

            if not include_accepted:
                query = query.is_("accepted_at", "null")

            result = query.execute()
            return result.data or []

        except Exception as e:
            logger.error(f"Failed to get invitations: {e}")
            return []

    def get_invitation_by_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Get invitation by token (for accepting).

        Args:
            token: Invitation token

        Returns:
            Invitation record or None
        """
        try:
            result = self.client.table(self.TABLE_USER_INVITATIONS)\
                .select("*")\
                .eq("token", token)\
                .single()\
                .execute()

            return result.data

        except Exception as e:
            logger.error(f"Failed to get invitation by token: {e}")
            return None

    def accept_invitation(self, token: str, auth_user_id: str) -> bool:
        """
        Mark an invitation as accepted.

        Args:
            token: Invitation token
            auth_user_id: The Supabase auth user ID of the new user

        Returns:
            True if successful
        """
        try:
            from datetime import datetime

            self.client.table(self.TABLE_USER_INVITATIONS)\
                .update({"accepted_at": datetime.utcnow().isoformat()})\
                .eq("token", token)\
                .execute()

            return True

        except Exception as e:
            logger.error(f"Failed to accept invitation: {e}")
            return False

    def cancel_invitation(self, invitation_id: str) -> bool:
        """
        Cancel/delete a pending invitation.

        Args:
            invitation_id: Invitation UUID

        Returns:
            True if successful
        """
        try:
            self.client.table(self.TABLE_USER_INVITATIONS)\
                .delete()\
                .eq("id", invitation_id)\
                .eq("tenant_id", self.tenant_id)\
                .is_("accepted_at", "null")\
                .execute()

            return True

        except Exception as e:
            logger.error(f"Failed to cancel invitation: {e}")
            return False

    # ==================== Template Settings Operations ====================

    TABLE_TEMPLATES = "tenant_templates"

    def get_template_settings(self) -> Optional[Dict[str, Any]]:
        """
        Get tenant template settings for quotes and invoices

        Returns:
            Template settings dict or None
        """
        if not self.client:
            return None

        try:
            result = self.client.table(self.TABLE_TEMPLATES)\
                .select("*")\
                .eq('tenant_id', self.tenant_id)\
                .single()\
                .execute()

            if result.data:
                # Parse JSON fields if stored as strings
                data = result.data
                settings = {
                    "quote": data.get("quote_settings", {}),
                    "invoice": data.get("invoice_settings", {})
                }
                return settings

            return None

        except Exception as e:
            logger.debug(f"No template settings found for {self.tenant_id}: {e}")
            return None

    def update_template_settings(self, settings: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update tenant template settings

        Args:
            settings: Dict with 'quote' and 'invoice' settings

        Returns:
            Updated settings or None
        """
        if not self.client:
            return None

        try:
            # Check if record exists
            existing = self.get_template_settings()

            record = {
                'tenant_id': self.tenant_id,
                'quote_settings': settings.get('quote', {}),
                'invoice_settings': settings.get('invoice', {}),
                'updated_at': datetime.utcnow().isoformat()
            }

            if not existing:
                # Insert new record
                record['created_at'] = datetime.utcnow().isoformat()
                result = self.client.table(self.TABLE_TEMPLATES).insert(record).execute()
            else:
                # Update existing
                result = self.client.table(self.TABLE_TEMPLATES)\
                    .update(record)\
                    .eq('tenant_id', self.tenant_id)\
                    .execute()

            if result.data:
                logger.info(f"Template settings updated for {self.tenant_id}")
                return settings

            return settings  # Return input even if DB failed

        except Exception as e:
            logger.error(f"Failed to update template settings: {e}")
            return settings  # Return input on error for graceful degradation