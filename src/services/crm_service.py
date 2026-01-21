"""
CRM Service - Multi-Tenant Version

Provides CRM functionality including:
- Client management
- Pipeline stages
- Activity logging
- Quote tracking

Usage:
    from config.loader import ClientConfig
    from src.services.crm_service import CRMService, PipelineStage

    config = ClientConfig('africastay')
    crm = CRMService(config)
    
    client = crm.get_or_create_client(
        email='john@example.com',
        name='John Doe',
        source='quote'
    )
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
import uuid

from config.loader import ClientConfig

logger = logging.getLogger(__name__)


class PipelineStage(Enum):
    """CRM Pipeline stages"""
    QUOTED = "QUOTED"
    NEGOTIATING = "NEGOTIATING"
    BOOKED = "BOOKED"
    PAID = "PAID"
    TRAVELLED = "TRAVELLED"
    LOST = "LOST"


class CRMService:
    """CRM operations for client management"""

    def __init__(self, config: ClientConfig):
        """
        Initialize CRM service with client configuration
        """
        self.config = config
        self.supabase = None
        
        try:
            from src.tools.supabase_tool import SupabaseTool
            self.supabase = SupabaseTool(config)
        except Exception as e:
            logger.warning(f"Supabase not available for CRM: {e}")

        logger.info(f"CRM service initialized for {config.client_id}")

    def get_or_create_client(
        self,
        email: str,
        name: str,
        phone: Optional[str] = None,
        source: str = "manual",
        consultant_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get existing client or create new one
        New clients start in QUOTED stage
        """
        if not self.supabase or not self.supabase.client:
            logger.error("Supabase client not available for client creation")
            return None

        try:
            # Check if client exists
            existing = self.get_client_by_email(email)

            if existing:
                logger.info(f"Client already exists for email {email}: {existing.get('client_id') or existing.get('id')}")
                return {**existing, 'created': False}

            # Create new client
            client_id = f"CLI-{uuid.uuid4().hex[:8].upper()}"
            
            record = {
                'tenant_id': self.config.client_id,
                'client_id': client_id,
                'email': email,
                'name': name,
                'phone': phone,
                'source': source,
                'consultant_id': consultant_id,
                'pipeline_stage': PipelineStage.QUOTED.value,
                'quote_count': 1,
                'total_value': 0,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }

            logger.info(f"Creating new client: {client_id} for tenant {self.config.client_id}")
            result = self.supabase.client.table('clients').insert(record).execute()

            if result.data:
                logger.info(f"Successfully created client: {result.data[0].get('client_id')}")
                return {**result.data[0], 'created': True}
            logger.error(f"Insert returned no data for client {client_id}")
            return None

        except Exception as e:
            logger.error(f"Failed to get/create client: {e}")
            return None

    def get_client_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get client by email address"""
        if not self.supabase or not self.supabase.client:
            return None

        try:
            result = self.supabase.client.table('clients')\
                .select("*")\
                .eq('tenant_id', self.config.client_id)\
                .eq('email', email)\
                .limit(1)\
                .execute()

            if result.data and len(result.data) > 0:
                return result.data[0]
            return None

        except Exception as e:
            logger.error(f"Failed to get client by email: {e}")
            return None

    def get_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get client by ID (supports both CLI-XXXXXXXX format and UUID)"""
        if not self.supabase or not self.supabase.client:
            return None

        try:
            # Determine if this is a CLI-XXXXXXXX format or UUID
            is_cli_format = client_id.startswith('CLI-')

            if is_cli_format:
                # Query by client_id column (CLI-XXXXXXXX format)
                result = self.supabase.client.table('clients')\
                    .select("*")\
                    .eq('tenant_id', self.config.client_id)\
                    .eq('client_id', client_id)\
                    .single()\
                    .execute()
            else:
                # Query by id column (UUID format) for backwards compatibility
                result = self.supabase.client.table('clients')\
                    .select("*")\
                    .eq('tenant_id', self.config.client_id)\
                    .eq('id', client_id)\
                    .single()\
                    .execute()

            return result.data

        except Exception as e:
            logger.error(f"Failed to get client: {e}")
            return None

    def _get_client_id_filter(self, client_id: str) -> tuple:
        """Helper to determine the correct column and value for client ID queries.
        Returns (column_name, value) tuple for use in .eq() calls.
        Supports both CLI-XXXXXXXX format and UUID format for backwards compatibility.
        """
        if client_id.startswith('CLI-'):
            return ('client_id', client_id)
        else:
            return ('id', client_id)

    def update_client(
        self,
        client_id: str,
        name: Optional[str] = None,
        phone: Optional[str] = None,
        consultant_id: Optional[str] = None,
        quote_count: Optional[int] = None,
        total_value: Optional[float] = None
    ) -> bool:
        """Update client details"""
        if not self.supabase or not self.supabase.client:
            return False

        try:
            update_data = {'updated_at': datetime.utcnow().isoformat()}

            if name is not None:
                update_data['name'] = name
            if phone is not None:
                update_data['phone'] = phone
            if consultant_id is not None:
                update_data['consultant_id'] = consultant_id
            if quote_count is not None:
                update_data['quote_count'] = quote_count
            if total_value is not None:
                update_data['total_value'] = total_value

            id_col, id_val = self._get_client_id_filter(client_id)
            self.supabase.client.table('clients')\
                .update(update_data)\
                .eq('tenant_id', self.config.client_id)\
                .eq(id_col, id_val)\
                .execute()

            return True

        except Exception as e:
            logger.error(f"Failed to update client: {e}")
            return False

    def update_stage(self, client_id: str, stage: PipelineStage) -> bool:
        """Update client pipeline stage"""
        if not self.supabase or not self.supabase.client:
            return False

        try:
            id_col, id_val = self._get_client_id_filter(client_id)
            self.supabase.client.table('clients')\
                .update({
                    'pipeline_stage': stage.value,
                    'updated_at': datetime.utcnow().isoformat()
                })\
                .eq('tenant_id', self.config.client_id)\
                .eq(id_col, id_val)\
                .execute()

            # Log stage change activity
            self.supabase.log_activity(
                client_id=client_id,
                activity_type='stage_change',
                description=f'Pipeline stage changed to {stage.value}'
            )

            return True

        except Exception as e:
            logger.error(f"Failed to update stage: {e}")
            return False

    def search_clients(
        self,
        query: Optional[str] = None,
        stage: Optional[PipelineStage] = None,
        consultant_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Search and list clients with enriched data"""
        if not self.supabase or not self.supabase.client:
            return []

        try:
            q = self.supabase.client.table('clients')\
                .select("*")\
                .eq('tenant_id', self.config.client_id)\
                .order('created_at', desc=True)\
                .range(offset, offset + limit - 1)

            if stage:
                q = q.eq('pipeline_stage', stage.value)

            if consultant_id:
                q = q.eq('consultant_id', consultant_id)

            result = q.execute()
            clients = result.data or []

            # Filter by query if provided (client-side for now)
            if query:
                query_lower = query.lower()
                clients = [
                    c for c in clients
                    if query_lower in c.get('name', '').lower()
                    or query_lower in c.get('email', '').lower()
                    or query_lower in (c.get('phone') or '').lower()
                ]

            # Enrich clients with quote and activity data
            enriched_clients = []
            for client in clients:
                enriched = {**client}
                
                # Map total_value to value for frontend
                enriched['value'] = client.get('total_value', 0)
                
                # Get latest quote for destination and value
                try:
                    quote_result = self.supabase.client.table('quotes')\
                        .select("destination, total_price, created_at")\
                        .eq('tenant_id', self.config.client_id)\
                        .eq('customer_email', client.get('email'))\
                        .order('created_at', desc=True)\
                        .limit(1)\
                        .execute()
                    
                    if quote_result.data and len(quote_result.data) > 0:
                        latest_quote = quote_result.data[0]
                        enriched['destination'] = latest_quote.get('destination')
                        # Update value if we have quote total
                        if latest_quote.get('total_price'):
                            enriched['value'] = latest_quote.get('total_price')
                except Exception as e:
                    logger.debug(f"Could not fetch quote for client {client.get('client_id')}: {e}")
                
                # Get last activity timestamp
                try:
                    activity_result = self.supabase.client.table('activities')\
                        .select("created_at")\
                        .eq('tenant_id', self.config.client_id)\
                        .eq('client_id', client.get('client_id'))\
                        .order('created_at', desc=True)\
                        .limit(1)\
                        .execute()
                    
                    if activity_result.data and len(activity_result.data) > 0:
                        enriched['last_activity'] = activity_result.data[0].get('created_at')
                    else:
                        # Fall back to updated_at if no activities
                        enriched['last_activity'] = client.get('updated_at')
                except Exception as e:
                    logger.debug(f"Could not fetch activity for client {client.get('client_id')}: {e}")
                    enriched['last_activity'] = client.get('updated_at')
                
                enriched_clients.append(enriched)

            return enriched_clients

        except Exception as e:
            logger.error(f"Failed to search clients: {e}")
            return []

    def get_activities(self, client_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get activities for a client (supports both CLI-XXXXXXXX and UUID formats)"""
        if not self.supabase or not self.supabase.client:
            return []

        try:
            # Activities are stored with client_id in CLI-XXXXXXXX format,
            # but we also support UUID lookup for backwards compatibility
            id_col, id_val = self._get_client_id_filter(client_id)

            result = self.supabase.client.table('activities')\
                .select("*")\
                .eq('tenant_id', self.config.client_id)\
                .eq(id_col, id_val)\
                .order('created_at', desc=True)\
                .limit(limit)\
                .execute()

            return result.data or []

        except Exception as e:
            logger.error(f"Failed to get activities: {e}")
            return []

    def get_pipeline_summary(self) -> Dict[str, Any]:
        """Get pipeline stage summary with counts and values.

        Values are calculated from quotes linked to clients by email,
        since total_value on clients may not always be updated.
        """
        if not self.supabase or not self.supabase.client:
            return {}

        try:
            # Get all clients with their pipeline stages and emails
            clients_result = self.supabase.client.table('clients')\
                .select("email, pipeline_stage")\
                .eq('tenant_id', self.config.client_id)\
                .execute()

            clients = clients_result.data or []
            logger.info(f"[Pipeline] Found {len(clients)} clients")

            # Get all quotes to calculate values
            quotes_result = self.supabase.client.table('quotes')\
                .select("customer_email, total_price")\
                .eq('tenant_id', self.config.client_id)\
                .execute()

            quotes = quotes_result.data or []
            logger.info(f"[Pipeline] Found {len(quotes)} quotes")

            # Log first few quotes for debugging
            for i, q in enumerate(quotes[:3]):
                logger.info(f"[Pipeline] Quote {i}: email={q.get('customer_email')}, total_price={q.get('total_price')}")

            # Build a map of email -> total quote value
            email_values = {}
            for quote in quotes:
                # Handle both 'customer_email' and potential variations
                email = (quote.get('customer_email') or quote.get('email') or '').lower().strip()
                price = quote.get('total_price') or quote.get('price') or 0
                if email and price:
                    email_values[email] = email_values.get(email, 0) + price

            logger.info(f"[Pipeline] Email->Value map: {len(email_values)} entries")
            for email, value in list(email_values.items())[:3]:
                logger.info(f"[Pipeline]   {email}: {value}")

            # Log client emails for comparison
            client_emails = [(c.get('email') or '').lower().strip() for c in clients]
            logger.info(f"[Pipeline] Client emails: {client_emails[:5]}")

            # Calculate summary by stage
            summary = {}
            for stage in PipelineStage:
                stage_clients = [c for c in clients if c.get('pipeline_stage') == stage.value]
                # Sum quote values for clients in this stage
                stage_value = 0
                for c in stage_clients:
                    client_email = (c.get('email') or '').lower().strip()
                    client_value = email_values.get(client_email, 0)
                    if client_value > 0:
                        logger.debug(f"Pipeline: Client {client_email} in {stage.value} has value {client_value}")
                    stage_value += client_value

                summary[stage.value] = {
                    'count': len(stage_clients),
                    'value': stage_value
                }
                if stage_value > 0:
                    logger.info(f"Pipeline summary: {stage.value} has {len(stage_clients)} clients, value {stage_value}")

            return summary

        except Exception as e:
            logger.error(f"Failed to get pipeline summary: {e}")
            return {}

    def get_client_stats(self) -> Dict[str, Any]:
        """Get overall CRM statistics.

        Total value is calculated from quotes linked to clients.
        """
        if not self.supabase or not self.supabase.client:
            return {}

        try:
            # Get all clients
            clients_result = self.supabase.client.table('clients')\
                .select("*")\
                .eq('tenant_id', self.config.client_id)\
                .execute()

            clients = clients_result.data or []

            # Get total value from quotes
            quotes_result = self.supabase.client.table('quotes')\
                .select("total_price")\
                .eq('tenant_id', self.config.client_id)\
                .execute()

            quotes = quotes_result.data or []
            total_quote_value = sum(q.get('total_price', 0) or 0 for q in quotes)

            return {
                'total_clients': len(clients),
                'total_value': total_quote_value,
                'by_stage': {
                    stage.value: len([c for c in clients if c.get('pipeline_stage') == stage.value])
                    for stage in PipelineStage
                },
                'by_source': self._count_by_field(clients, 'source')
            }

        except Exception as e:
            logger.error(f"Failed to get client stats: {e}")
            return {}

    def _count_by_field(self, items: List[Dict], field: str) -> Dict[str, int]:
        """Helper to count items by a field value"""
        counts = {}
        for item in items:
            value = item.get(field, 'unknown')
            counts[value] = counts.get(value, 0) + 1
        return counts