"""
Quote Agent - Multi-Tenant Version

Orchestrates the full quote generation flow:
1. Parse customer requirements
2. Find matching hotels
3. Calculate pricing
4. Generate PDF
5. Send email
6. Save to Supabase
7. Auto-add to CRM

Usage:
    from config.loader import ClientConfig
    from src.agents.quote_agent import QuoteAgent

    config = ClientConfig('africastay')
    agent = QuoteAgent(config)

    result = agent.generate_quote({
        'name': 'John Doe',
        'email': 'john@example.com',
        'destination': 'Zanzibar',
        'check_in': '2025-06-15',
        'check_out': '2025-06-22',
        'adults': 2,
        'children': 0
    })
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import uuid
import json

from config.loader import ClientConfig
from config.database import DatabaseTables
from src.tools.bigquery_tool import BigQueryTool
from src.utils.pdf_generator import PDFGenerator
from src.utils.email_sender import EmailSender

logger = logging.getLogger(__name__)


class QuoteAgent:
    """Orchestrates quote generation for travel inquiries"""

    def __init__(self, config: ClientConfig):
        """
        Initialize quote agent with client configuration
        """
        self.config = config
        self.db = DatabaseTables(config)
        self.bq_tool = BigQueryTool(config)
        self.pdf_generator = PDFGenerator(config)
        self.email_sender = EmailSender(config)
        
        # Initialize Supabase for quote storage
        self.supabase = None
        try:
            from src.tools.supabase_tool import SupabaseTool
            self.supabase = SupabaseTool(config)
        except Exception as e:
            logger.warning(f"Supabase not available: {e}")

        # Initialize CRM service
        self.crm = None
        try:
            from src.services.crm_service import CRMService
            self.crm = CRMService(config)
        except Exception as e:
            logger.warning(f"CRM service not available: {e}")

        # Settings
        self.max_hotels_per_quote = 3
        self.default_nights = 7

        logger.info(f"Quote agent initialized for {config.client_id}")

    def generate_quote(
        self,
        customer_data: Dict[str, Any],
        send_email: bool = True,
        assign_consultant: bool = True,
        selected_hotels: Optional[List[str]] = None,
        initial_status: str = "generated"
    ) -> Dict[str, Any]:
        """
        Generate a complete quote for customer

        Args:
            customer_data: Customer travel requirements
            send_email: Whether to send quote email
            assign_consultant: Whether to assign a consultant
            selected_hotels: Optional list of hotel names to include (user selection)
            initial_status: Initial quote status - 'draft' or 'generated' (default).
                           Use initial_status='draft' for email auto-quotes that require
                           consultant review before sending.
        """
        try:
            logger.info(f"Generating quote for {customer_data.get('email')}")
            if selected_hotels:
                logger.info(f"User selected hotels: {selected_hotels}")

            # Generate quote ID
            quote_id = self._generate_quote_id()

            # Validate and normalize input
            normalized = self._normalize_customer_data(customer_data)

            # Find matching hotels - use different approach for user-selected vs auto-select
            if selected_hotels:
                # User selected specific hotels - use relaxed date filtering
                logger.info(f"User selected {len(selected_hotels)} hotels: {selected_hotels}")
                hotels = self.bq_tool.find_rates_by_hotel_names(
                    hotel_names=selected_hotels,
                    nights=normalized['nights'],
                    check_in=normalized['check_in'],
                    check_out=normalized['check_out']
                )
                logger.info(f"Found {len(hotels)} rate records for selected hotels")
            else:
                # Auto-select mode - use destination-based query with date filtering
                hotels = self._find_hotels(normalized)
                logger.info(f"Found {len(hotels)} hotels from database for {normalized['destination']}")

            if not hotels:
                logger.warning(f"No hotels found for {normalized['destination']}")
                return {
                    'success': False,
                    'quote_id': quote_id,
                    'error': f"No available hotels found for {normalized['destination']}",
                    'status': 'no_availability'
                }

            # Calculate pricing for each hotel
            hotel_options = self._calculate_hotel_options(hotels, normalized)

            if not hotel_options:
                return {
                    'success': False,
                    'quote_id': quote_id,
                    'error': 'Failed to calculate pricing',
                    'status': 'pricing_error'
                }

            # Select top hotels (limit to max)
            final_hotels = hotel_options[:self.max_hotels_per_quote]

            # Assign consultant if requested
            consultant = None
            if assign_consultant:
                consultant = self.bq_tool.get_next_consultant_round_robin()

            # Build quote object
            quote = {
                'quote_id': quote_id,
                'customer_name': normalized['name'],
                'customer_email': normalized['email'],
                'customer_phone': normalized.get('phone'),
                'destination': normalized['destination'],
                'check_in_date': normalized['check_in'],
                'check_out_date': normalized['check_out'],
                'nights': normalized['nights'],
                'adults': normalized['adults'],
                'children': normalized.get('children', 0),
                'children_ages': normalized.get('children_ages') or [],
                'hotels': final_hotels,
                'total_price': final_hotels[0]['total_price'] if final_hotels else 0,
                'consultant': consultant,
                'status': initial_status,  # Use initial_status ('draft' or 'generated')
                'created_at': datetime.utcnow().isoformat()
            }

            # Generate PDF
            pdf_bytes = None
            try:
                pdf_bytes = self.pdf_generator.generate_quote_pdf(quote, final_hotels, normalized)
                quote['pdf_generated'] = True
            except Exception as e:
                logger.error(f"PDF generation failed: {e}")
                quote['pdf_generated'] = False

            # Send email if requested and PDF was generated (skip for draft quotes)
            email_sent = False
            email_error = None
            if initial_status != 'draft' and send_email and pdf_bytes:
                try:
                    email_sent = self.email_sender.send_quote_email(
                        customer_email=normalized['email'],
                        customer_name=normalized['name'],
                        quote_pdf_data=pdf_bytes,
                        destination=normalized['destination']
                    )
                    if email_sent:
                        quote['sent_at'] = datetime.utcnow().isoformat()
                except Exception as e:
                    logger.error(f"Email sending failed: {e}")
                    email_error = str(e)

            # Update status based on initial_status and email result
            if initial_status == 'draft':
                quote['email_sent'] = False
                quote['status'] = 'draft'
            else:
                quote['email_sent'] = email_sent
                quote['status'] = 'sent' if email_sent else 'generated'

            # Auto-queue follow-up call for next business day if email was sent (skip for drafts)
            call_queued = False
            if initial_status != 'draft' and email_sent and normalized.get('phone'):
                call_queued = self._schedule_follow_up_call(
                    quote_id=quote_id,
                    customer_name=normalized['name'],
                    customer_email=normalized['email'],
                    customer_phone=normalized['phone'],
                    destination=normalized['destination']
                )

            quote['call_queued'] = call_queued

            # Save quote to Supabase
            saved = self._save_quote_to_supabase(quote)

            # Auto-add to CRM
            crm_result = self._add_to_crm(normalized, quote_id)

            # Trigger notification for new quote
            try:
                from src.api.notifications_routes import NotificationService
                notification_service = NotificationService(self.config)
                notification_service.notify_quote_request(
                    customer_name=normalized['name'],
                    destination=normalized['destination'],
                    quote_id=quote_id
                )
            except Exception as e:
                logger.warning(f"Failed to send notification: {e}")

            logger.info(f"Quote {quote_id} generated successfully (email_sent={email_sent})")

            return {
                'success': True,
                'quote_id': quote_id,
                'quote': quote,
                'hotels_count': len(final_hotels),  # Use actual hotels in quote, not selection
                'email_sent': email_sent,
                'email_error': email_error,
                'consultant': consultant,
                'status': quote['status'],
                'crm_added': crm_result.get('success', False) if crm_result else False,
                'call_queued': call_queued
            }

        except Exception as e:
            logger.error(f"Quote generation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'status': 'error'
            }

    def _add_to_crm(self, customer_data: Dict[str, Any], quote_id: str) -> Optional[Dict[str, Any]]:
        """
        Add customer to CRM automatically
        - First quote: QUOTED stage
        - Subsequent quotes: NEGOTIATING stage
        """
        if not self.crm:
            return None

        try:
            from src.services.crm_service import PipelineStage
            
            # Check if client already exists
            existing = self.crm.get_client_by_email(customer_data['email'])
            
            if existing:
                # Client exists - check if we should move to NEGOTIATING
                current_stage = existing.get('pipeline_stage', 'QUOTED')
                quote_count = existing.get('quote_count', 1) + 1
                
                # Update quote count
                self.crm.update_client(
                    client_id=existing['client_id'],
                    quote_count=quote_count
                )
                
                # Move to NEGOTIATING if this is their 2nd+ quote and still in QUOTED
                if quote_count >= 2 and current_stage == 'QUOTED':
                    self.crm.update_stage(
                        client_id=existing['client_id'],
                        stage=PipelineStage.NEGOTIATING
                    )
                    logger.info(f"Client {customer_data['email']} moved to NEGOTIATING (quote #{quote_count})")
                
                # Log activity
                if self.supabase:
                    self.supabase.log_activity(
                        client_id=existing['client_id'],
                        activity_type='quote_generated',
                        description=f"Quote {quote_id} generated for {customer_data.get('destination', 'destination')}",
                        metadata={'quote_id': quote_id}
                    )
                
                return {'success': True, 'created': False, 'client_id': existing['client_id']}
            else:
                # Create new client in QUOTED stage
                result = self.crm.get_or_create_client(
                    email=customer_data['email'],
                    name=customer_data['name'],
                    phone=customer_data.get('phone'),
                    source='quote'
                )
                
                if result:
                    # Log activity
                    if self.supabase:
                        self.supabase.log_activity(
                            client_id=result['client_id'],
                            activity_type='quote_generated',
                            description=f"Quote {quote_id} generated for {customer_data.get('destination', 'destination')}",
                            metadata={'quote_id': quote_id}
                        )
                    
                    logger.info(f"New client {customer_data['email']} added to CRM in QUOTED stage")
                    return {'success': True, 'created': True, 'client_id': result['client_id']}
                
                return {'success': False}
                
        except Exception as e:
            logger.error(f"Failed to add to CRM: {e}")
            return {'success': False, 'error': str(e)}

    def _generate_quote_id(self) -> str:
        """Generate unique quote ID"""
        timestamp = datetime.utcnow().strftime('%Y%m%d')
        unique = uuid.uuid4().hex[:6].upper()
        return f"QT-{timestamp}-{unique}"

    def _normalize_customer_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize and validate customer data"""
        normalized = {
            'name': data.get('name', 'Valued Customer'),
            'email': data.get('email', ''),
            'phone': data.get('phone'),
            'destination': data.get('destination', ''),
            'adults': int(data.get('adults', 2)),
            'children': int(data.get('children', 0)),
            'children_ages': data.get('children_ages') or [],
            'budget': data.get('budget') or data.get('total_budget'),
        }

        # Parse dates
        check_in = data.get('check_in')
        check_out = data.get('check_out')

        if check_in:
            if isinstance(check_in, str):
                normalized['check_in'] = check_in
            else:
                normalized['check_in'] = check_in.strftime('%Y-%m-%d')
        else:
            default_date = datetime.utcnow() + timedelta(days=30)
            normalized['check_in'] = default_date.strftime('%Y-%m-%d')

        if check_out:
            if isinstance(check_out, str):
                normalized['check_out'] = check_out
            else:
                normalized['check_out'] = check_out.strftime('%Y-%m-%d')
        else:
            check_in_date = datetime.strptime(normalized['check_in'], '%Y-%m-%d')
            default_checkout = check_in_date + timedelta(days=self.default_nights)
            normalized['check_out'] = default_checkout.strftime('%Y-%m-%d')

        # Calculate nights
        check_in_dt = datetime.strptime(normalized['check_in'], '%Y-%m-%d')
        check_out_dt = datetime.strptime(normalized['check_out'], '%Y-%m-%d')
        normalized['nights'] = (check_out_dt - check_in_dt).days

        # Validate destination against config
        valid_destinations = self.config.destination_names
        if normalized['destination'] not in valid_destinations:
            for dest in valid_destinations:
                if dest.lower() == normalized['destination'].lower():
                    normalized['destination'] = dest
                    break

        return normalized

    def _find_hotels(self, customer_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find matching hotels for customer requirements"""
        has_children = customer_data.get('children', 0) > 0 or bool(customer_data.get('children_ages'))

        hotels = self.bq_tool.find_matching_hotels(
            destination=customer_data['destination'],
            check_in=customer_data['check_in'],
            check_out=customer_data['check_out'],
            nights=customer_data['nights'],
            adults=customer_data['adults'],
            children_ages=customer_data.get('children_ages'),
            budget_per_person=customer_data.get('budget'),
            has_children=has_children
        )

        return hotels

    def _calculate_hotel_options(
        self,
        hotels: List[Dict[str, Any]],
        customer_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Calculate pricing for hotel options"""
        options = []
        seen_hotels = set()

        for hotel in hotels:
            hotel_name = hotel.get('hotel_name')

            if hotel_name in seen_hotels:
                continue

            pricing = self.bq_tool.calculate_quote_price(
                rate_id=hotel.get('rate_id'),
                adults=customer_data['adults'],
                children_ages=customer_data.get('children_ages'),
                flight_price_pp=0,
                single_adults=0
            )

            if not pricing:
                continue

            option = {
                'name': hotel_name,
                'hotel_name': hotel_name,
                'rating': hotel.get('hotel_rating', '4*'),
                'room_type': hotel.get('room_type', 'Standard Room'),
                'meal_plan': hotel.get('meal_plan', 'Bed & Breakfast'),
                'price_per_person': pricing['per_person_rates']['adult_sharing'],
                'total_price': pricing['totals']['grand_total'],
                'includes_flights': False,
                'includes_transfers': True,
                'rate_id': hotel.get('rate_id'),
                'pricing_breakdown': pricing
            }

            options.append(option)
            seen_hotels.add(hotel_name)

            if len(options) >= self.max_hotels_per_quote * 2:
                break

        options.sort(key=lambda x: x['total_price'])
        return options

    def _save_quote_to_supabase(self, quote: Dict[str, Any]) -> bool:
        """Save quote to Supabase"""
        if not self.supabase or not self.supabase.client:
            logger.warning("Supabase not available for quote storage")
            return False

        try:
            record = {
                'tenant_id': self.config.client_id,
                'quote_id': quote['quote_id'],
                'customer_name': quote['customer_name'],
                'customer_email': quote['customer_email'],
                'customer_phone': quote.get('customer_phone'),
                'destination': quote['destination'],
                'check_in_date': quote['check_in_date'],
                'check_out_date': quote['check_out_date'],
                'nights': quote['nights'],
                'adults': quote['adults'],
                'children': quote.get('children', 0),
                'children_ages': quote.get('children_ages', []),
                'hotels': quote.get('hotels', []),
                'total_price': quote.get('total_price', 0),
                'status': quote['status'],
                'email_sent': quote.get('email_sent', False),
                'pdf_generated': quote.get('pdf_generated', False),
                'consultant_id': quote['consultant']['consultant_id'] if quote.get('consultant') else None,
                'created_at': quote['created_at'],
                'sent_at': quote.get('sent_at'),
            }

            result = self.supabase.client.table('quotes').insert(record).execute()
            
            if result.data:
                logger.info(f"Quote {quote['quote_id']} saved to Supabase")
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to save quote to Supabase: {e}")
            return False

    def get_quote(self, quote_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve quote by ID from Supabase"""
        if not self.supabase or not self.supabase.client:
            return None

        try:
            result = self.supabase.client.table('quotes')\
                .select("*")\
                .eq('tenant_id', self.config.client_id)\
                .eq('quote_id', quote_id)\
                .single()\
                .execute()

            if result.data:
                return result.data
            return None

        except Exception as e:
            logger.error(f"Failed to get quote: {e}")
            return None

    def list_quotes(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List quotes from Supabase"""
        if not self.supabase or not self.supabase.client:
            return []

        try:
            query = self.supabase.client.table('quotes')\
                .select("*")\
                .eq('tenant_id', self.config.client_id)\
                .order('created_at', desc=True)\
                .range(offset, offset + limit - 1)

            if status:
                query = query.eq('status', status)

            result = query.execute()
            return result.data or []

        except Exception as e:
            logger.error(f"Failed to list quotes: {e}")
            return []

    def update_quote_status(self, quote_id: str, status: str) -> bool:
        """Update quote status"""
        if not self.supabase or not self.supabase.client:
            return False

        try:
            update_data = {
                'status': status,
                'updated_at': datetime.utcnow().isoformat()
            }

            # Add timestamp for specific statuses
            if status == 'sent':
                update_data['sent_at'] = datetime.utcnow().isoformat()
            elif status == 'viewed':
                update_data['viewed_at'] = datetime.utcnow().isoformat()
            elif status == 'accepted':
                update_data['accepted_at'] = datetime.utcnow().isoformat()

            self.supabase.client.table('quotes')\
                .update(update_data)\
                .eq('tenant_id', self.config.client_id)\
                .eq('quote_id', quote_id)\
                .execute()
            return True
        except Exception as e:
            logger.error(f"Failed to update quote status: {e}")
            return False

    def _schedule_follow_up_call(
        self,
        quote_id: str,
        customer_name: str,
        customer_email: str,
        customer_phone: str,
        destination: str
    ) -> bool:
        """
        Schedule an automated follow-up call for the next business day.

        Call is scheduled for 10:00 AM in the tenant's timezone.
        Skips weekends (Saturday/Sunday).
        """
        if not self.supabase:
            logger.warning("Cannot schedule call: Supabase not available")
            return False

        try:
            # Calculate next business day at 10:00 AM
            scheduled_time = self._get_next_business_day_10am()

            # Queue the call
            result = self.supabase.queue_outbound_call(
                client_name=customer_name,
                client_email=customer_email,
                phone_number=customer_phone,
                quote_details={
                    'quote_id': quote_id,
                    'destination': destination,
                    'auto_scheduled': True,
                    'reason': 'quote_follow_up'
                },
                consultant_id=None,  # Will be assigned when call is made
                scheduled_time=scheduled_time
            )

            if result:
                logger.info(
                    f"Scheduled follow-up call for {customer_name} ({customer_phone}) "
                    f"at {scheduled_time.isoformat()} for quote {quote_id}"
                )
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to schedule follow-up call: {e}")
            return False

    def _get_next_business_day_10am(self) -> datetime:
        """
        Calculate the next business day at 10:00 AM.

        Uses tenant's timezone for calculation.
        Skips Saturday and Sunday.
        If today is before 10 AM on a weekday, schedules for today.
        """
        try:
            import pytz
            tz = pytz.timezone(self.config.timezone)
        except:
            # Fallback to UTC if timezone not available
            import pytz
            tz = pytz.UTC

        now = datetime.now(tz)
        target_hour = 10  # 10:00 AM

        # Start with today
        candidate = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)

        # If it's already past 10 AM, move to tomorrow
        if now.hour >= target_hour:
            candidate += timedelta(days=1)

        # Skip weekends (Saturday=5, Sunday=6)
        while candidate.weekday() >= 5:
            candidate += timedelta(days=1)

        # Convert to UTC for storage
        return candidate.astimezone(pytz.UTC).replace(tzinfo=None)

    def _get_next_business_day(self, days_ahead: int = 1) -> datetime:
        """
        Get next business day, optionally N days ahead.

        Args:
            days_ahead: Minimum days ahead (default 1 = tomorrow)

        Returns:
            Next business day at 10:00 AM in tenant timezone
        """
        try:
            import pytz
            tz = pytz.timezone(self.config.timezone)
        except:
            import pytz
            tz = pytz.UTC

        now = datetime.now(tz)
        candidate = now + timedelta(days=days_ahead)
        candidate = candidate.replace(hour=10, minute=0, second=0, microsecond=0)

        # Skip weekends
        while candidate.weekday() >= 5:
            candidate += timedelta(days=1)

        return candidate.astimezone(pytz.UTC).replace(tzinfo=None)
