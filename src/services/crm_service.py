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
import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
import uuid

from config.loader import ClientConfig


def get_redis_client():
    """Get Redis client for caching, returns None if unavailable."""
    try:
        import redis
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            return redis.from_url(redis_url)
        return None
    except Exception:
        return None

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
        """Search and list clients with enriched data using batch queries"""
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

            if not clients:
                return []

            # Collect emails and client_ids for batch queries
            client_emails = [c.get('email') for c in clients if c.get('email')]
            client_ids = [c.get('client_id') for c in clients if c.get('client_id')]

            # Batch query 1: Get latest quotes for all clients in one query
            quotes_by_email = {}
            if client_emails:
                try:
                    quotes_result = self.supabase.client.table('quotes')\
                        .select("customer_email, destination, total_price, created_at")\
                        .eq('tenant_id', self.config.client_id)\
                        .in_('customer_email', client_emails)\
                        .order('created_at', desc=True)\
                        .execute()

                    # Group by email, keeping only the latest (first due to order)
                    for quote in (quotes_result.data or []):
                        email = quote.get('customer_email')
                        if email and email not in quotes_by_email:
                            quotes_by_email[email] = quote
                except Exception as e:
                    logger.debug(f"Could not batch fetch quotes: {e}")

            # Batch query 2: Get latest activities for all clients in one query
            activities_by_client = {}
            if client_ids:
                try:
                    activities_result = self.supabase.client.table('activities')\
                        .select("client_id, created_at")\
                        .eq('tenant_id', self.config.client_id)\
                        .in_('client_id', client_ids)\
                        .order('created_at', desc=True)\
                        .execute()

                    # Group by client_id, keeping only the latest (first due to order)
                    for activity in (activities_result.data or []):
                        cid = activity.get('client_id')
                        if cid and cid not in activities_by_client:
                            activities_by_client[cid] = activity
                except Exception as e:
                    logger.debug(f"Could not batch fetch activities: {e}")

            # Enrich clients with batch query results
            enriched_clients = []
            for client in clients:
                enriched = {**client}

                # Map total_value to value for frontend
                enriched['value'] = client.get('total_value', 0)

                # Get latest quote from batch result
                email = client.get('email')
                if email and email in quotes_by_email:
                    latest_quote = quotes_by_email[email]
                    enriched['destination'] = latest_quote.get('destination')
                    if latest_quote.get('total_price'):
                        enriched['value'] = latest_quote.get('total_price')

                # Get last activity from batch result
                client_id = client.get('client_id')
                if client_id and client_id in activities_by_client:
                    enriched['last_activity'] = activities_by_client[client_id].get('created_at')
                else:
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
        """Get pipeline stage summary with counts and values using database aggregation.

        Uses optimized queries:
        - Query 1: Get client counts by stage (lightweight - only pipeline_stage column)
        - Query 2: Get active pipeline clients with emails (for value calculation)
        - Query 3: Get quote totals only for active clients (batch query with in_())

        This is much more efficient than fetching all rows for large datasets.
        Results are cached in Redis for 60 seconds.
        """
        if not self.supabase or not self.supabase.client:
            return {}

        # Try to get from cache first
        cache_key = f"crm:pipeline_summary:{self.config.client_id}"
        redis_client = get_redis_client()
        if redis_client:
            try:
                cached = redis_client.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception:
                pass  # Continue without cache

        try:
            # Query 1: Get clients with pipeline stages (lightweight - minimal columns)
            clients_result = self.supabase.client.table('clients')\
                .select("pipeline_stage")\
                .eq('tenant_id', self.config.client_id)\
                .execute()

            clients = clients_result.data or []

            # Count clients per stage
            stage_counts = {}
            for stage in PipelineStage:
                stage_counts[stage.value] = 0

            for c in clients:
                stage = c.get('pipeline_stage')
                if stage in stage_counts:
                    stage_counts[stage] += 1

            # Query 2: Get emails of clients in active pipeline stages only
            # Skip LOST and TRAVELLED as they don't need value calculations
            active_stages = [PipelineStage.QUOTED.value, PipelineStage.NEGOTIATING.value,
                             PipelineStage.BOOKED.value, PipelineStage.PAID.value]

            active_clients = self.supabase.client.table('clients')\
                .select("email, pipeline_stage")\
                .eq('tenant_id', self.config.client_id)\
                .in_('pipeline_stage', active_stages)\
                .execute()

            active_client_data = active_clients.data or []
            active_client_emails = [c.get('email') for c in active_client_data if c.get('email')]

            # Initialize stage values
            stage_values = {stage.value: 0 for stage in PipelineStage}

            # Query 3: Get quote totals for active clients only (batch query)
            if active_client_emails:
                quotes_result = self.supabase.client.table('quotes')\
                    .select("customer_email, total_price")\
                    .eq('tenant_id', self.config.client_id)\
                    .in_('customer_email', active_client_emails)\
                    .execute()

                # Build email -> total value map
                email_values = {}
                for quote in (quotes_result.data or []):
                    email = (quote.get('customer_email') or '').lower().strip()
                    price = quote.get('total_price') or 0
                    if email and price:
                        email_values[email] = email_values.get(email, 0) + price

                # Calculate stage values from active clients
                for c in active_client_data:
                    email = (c.get('email') or '').lower().strip()
                    stage = c.get('pipeline_stage')
                    if email and stage:
                        stage_values[stage] += email_values.get(email, 0)

            # Build summary
            summary = {}
            for stage in PipelineStage:
                summary[stage.value] = {
                    'count': stage_counts.get(stage.value, 0),
                    'value': stage_values.get(stage.value, 0)
                }

            logger.info(f"[Pipeline] Summary: {len(clients)} clients, {len(active_client_emails)} active")

            # Cache the result in Redis (60 second TTL)
            if redis_client and summary:
                try:
                    redis_client.setex(cache_key, 60, json.dumps(summary))
                except Exception:
                    pass  # Continue without caching

            return summary

        except Exception as e:
            logger.error(f"Failed to get pipeline summary: {e}")
            return {}

    def get_client_stats(self) -> Dict[str, Any]:
        """Get overall CRM statistics.

        Total value is calculated from quotes linked to clients.
        Results are cached in Redis for 60 seconds.
        """
        if not self.supabase or not self.supabase.client:
            return {}

        # Try to get from cache first
        cache_key = f"crm:client_stats:{self.config.client_id}"
        redis_client = get_redis_client()
        if redis_client:
            try:
                cached = redis_client.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception:
                pass  # Continue without cache

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

            result = {
                'total_clients': len(clients),
                'total_value': total_quote_value,
                'by_stage': {
                    stage.value: len([c for c in clients if c.get('pipeline_stage') == stage.value])
                    for stage in PipelineStage
                },
                'by_source': self._count_by_field(clients, 'source')
            }

            # Cache the result in Redis (60 second TTL)
            if redis_client and result:
                try:
                    redis_client.setex(cache_key, 60, json.dumps(result))
                except Exception:
                    pass  # Continue without caching

            return result

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