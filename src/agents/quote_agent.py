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
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, date
import uuid
import json

from config.loader import ClientConfig
from config.database import DatabaseTables
from src.tools.bigquery_tool import BigQueryTool
from src.utils.pdf_generator import PDFGenerator
from src.utils.email_sender import EmailSender
from src.utils.field_normalizers import normalize_quote_status

logger = logging.getLogger(__name__)


def run_async(coro):
    """Helper to run async code from sync context"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If there's a running loop, create a new task
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


class QuoteAgent:
    """Orchestrates quote generation for travel inquiries"""

    def __init__(self, config: ClientConfig):
        """
        Initialize quote agent with client configuration.

        Heavy dependencies (BigQuery, PDF, Email) are lazy-loaded on first use
        to keep list/get operations fast.
        """
        self.config = config
        self.db = DatabaseTables(config)

        # Lazy-initialized heavy dependencies (set to sentinel)
        self._bq_tool = None
        self._pdf_generator = None
        self._email_sender = None

        # Initialize Supabase for quote storage (lightweight, needed for all ops)
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

        # Initialize Rates Engine client for live pricing
        self.rates_client = None
        try:
            from src.services.travel_platform_rates_client import get_travel_platform_rates_client
            self.rates_client = get_travel_platform_rates_client()
            logger.info("Rates Engine client initialized")
        except Exception as e:
            logger.warning(f"Rates Engine client not available: {e}")

        # Settings
        self.max_hotels_per_quote = 3
        self.default_nights = 7

        logger.info(f"Quote agent initialized for {config.client_id}")

    @property
    def bq_tool(self):
        """Lazy-load BigQuery tool (slow init, only needed for quote generation)."""
        if self._bq_tool is None:
            self._bq_tool = BigQueryTool(self.config)
        return self._bq_tool

    @property
    def pdf_generator(self):
        """Lazy-load PDF generator (only needed for quote generation/resend)."""
        if self._pdf_generator is None:
            self._pdf_generator = PDFGenerator(self.config)
        return self._pdf_generator

    @property
    def email_sender(self):
        """Lazy-load email sender (only needed for sending quotes)."""
        if self._email_sender is None:
            self._email_sender = EmailSender(self.config)
        return self._email_sender

    def generate_quote(
        self,
        customer_data: Dict[str, Any],
        send_email: bool = True,
        assign_consultant: bool = True,
        selected_hotels: Optional[List[str]] = None,
        initial_status: str = "quoted",
        use_live_rates: bool = True
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
            use_live_rates: Whether to use live Juniper rates (default: True).
                           If False, falls back to BigQuery cached rates.
        """
        try:
            logger.info(f"Generating quote for {customer_data.get('email')} (live_rates={use_live_rates})")
            if selected_hotels:
                logger.info(f"User selected hotels: {selected_hotels}")

            # Generate quote ID
            quote_id = self._generate_quote_id()

            # Validate and normalize input
            normalized = self._normalize_customer_data(customer_data)

            # Find matching hotels - use live rates or BigQuery based on flag
            hotels = []
            hotel_options = []

            if use_live_rates and self.rates_client:
                # Use live Juniper rates via Rates Engine
                logger.info(f"Using live rates for {normalized['destination']}")
                hotel_options = self._find_hotels_live(normalized, selected_hotels)
                if hotel_options:
                    logger.info(f"Found {len(hotel_options)} hotels from live rates")
                else:
                    logger.warning("No live rates available, falling back to BigQuery")
                    use_live_rates = False

            if not use_live_rates or not hotel_options:
                # Fallback to BigQuery cached rates
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

                # Calculate pricing for each hotel (BigQuery path)
                hotel_options = self._calculate_hotel_options(hotels, normalized)

            # Check we have hotel options from either path
            if not hotel_options:
                return {
                    'success': False,
                    'quote_id': quote_id,
                    'error': 'Failed to find available hotels with pricing',
                    'status': 'no_availability'
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
                'total_price': sum(h.get('total_price', 0) for h in final_hotels) if final_hotels else 0,
                'consultant': consultant,
                'status': normalize_quote_status(initial_status),
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
                        destination=normalized['destination'],
                        quote_details={
                            'check_in': normalized.get('check_in'),
                            'check_out': normalized.get('check_out'),
                            'adults': normalized.get('adults', 0),
                            'children': normalized.get('children', 0),
                            'nights': normalized.get('nights', 0),
                            'room_count': len(normalized.get('rooms', [{}])),
                        },
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
                quote['status'] = 'sent' if email_sent else 'quoted'

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

            # Save quote to Supabase — must succeed for quote_id to be valid
            saved = self._save_quote_to_supabase(quote)
            if not saved:
                logger.error(f"Quote {quote_id} generated but failed to save to Supabase")
                return {
                    'success': False,
                    'error': 'Quote generated but failed to save. Please try again.',
                    'quote_id': None,
                }

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
            logger.error(f"Quote generation failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': 'Quote generation failed. Please try again.',
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
            logger.error(f"Failed to add to CRM: {e}", exc_info=True)
            return {'success': False, 'error': 'Failed to add client to CRM'}

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

        # Validate dates are not in the past — advance to next year if needed
        check_in_dt = datetime.strptime(normalized['check_in'], '%Y-%m-%d')
        check_out_dt = datetime.strptime(normalized['check_out'], '%Y-%m-%d')
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        if check_in_dt < today:
            # Advance to same month/day in the next valid year
            while check_in_dt < today:
                check_in_dt = check_in_dt.replace(year=check_in_dt.year + 1)
            nights_delta = check_out_dt - datetime.strptime(normalized['check_in'], '%Y-%m-%d')
            check_out_dt = check_in_dt + nights_delta
            normalized['check_in'] = check_in_dt.strftime('%Y-%m-%d')
            normalized['check_out'] = check_out_dt.strftime('%Y-%m-%d')
            logger.info(f"Adjusted past dates to future: {normalized['check_in']} - {normalized['check_out']}")

        # Calculate nights
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

    def _find_hotels_live(
        self,
        customer_data: Dict[str, Any],
        selected_hotels: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find matching hotels using live Juniper rates via Rates Engine.

        Args:
            customer_data: Normalized customer data with destination, dates, etc.
            selected_hotels: Optional list of specific hotel names to include

        Returns:
            List of hotel options formatted for quote generation
        """
        if not self.rates_client:
            logger.warning("Rates client not available for live search")
            return []

        try:
            # Parse dates
            check_in = datetime.strptime(customer_data['check_in'], '%Y-%m-%d').date()
            check_out = datetime.strptime(customer_data['check_out'], '%Y-%m-%d').date()

            # Call rates engine async
            logger.info(
                f"Live rates search: destination={customer_data['destination']}, "
                f"dates={check_in} to {check_out}, adults={customer_data['adults']}"
            )

            result = run_async(
                self.rates_client.search_hotels(
                    destination=customer_data['destination'],
                    check_in=check_in,
                    check_out=check_out,
                    adults=customer_data['adults'],
                    children_ages=customer_data.get('children_ages', []),
                    max_hotels=100  # Get more to filter/select from
                )
            )

            if not result.get('success') or not result.get('hotels'):
                logger.warning(f"No live rates found: {result.get('error', 'No hotels returned')}")
                return []

            # Transform hotels to quote format
            hotel_options = []
            nights = customer_data['nights']
            total_guests = customer_data['adults'] + customer_data.get('children', 0)

            for hotel in result['hotels']:
                hotel_name = hotel.get('hotel_name', 'Unknown Hotel')

                # Filter by selected hotels if provided
                if selected_hotels:
                    # Fuzzy match - check if any selected hotel name matches
                    matched = False
                    hotel_name_lower = hotel_name.lower()
                    for selected in selected_hotels:
                        if selected.lower() in hotel_name_lower or hotel_name_lower in selected.lower():
                            matched = True
                            break
                    if not matched:
                        continue

                # Get hotel details
                stars = hotel.get('stars') or 4
                rating = f"{stars}*"
                image_url = hotel.get('image_url')

                # Process each room option
                options = hotel.get('options', [])
                if not options:
                    # Use cheapest_price if no options array
                    if hotel.get('cheapest_price'):
                        options = [{
                            'room_type': 'Standard Room',
                            'meal_plan': hotel.get('cheapest_meal_plan', 'Bed & Breakfast'),
                            'price_total': hotel.get('cheapest_price'),
                            'price_per_night': hotel.get('cheapest_price') / max(nights, 1),
                            'currency': 'ZAR'
                        }]
                    else:
                        continue  # Skip hotels with no pricing

                for option in options:
                    room_type = option.get('room_type', 'Standard Room')
                    meal_plan = option.get('meal_plan', 'Bed & Breakfast')
                    total_price = option.get('price_total', 0)
                    price_per_night = option.get('price_per_night', 0)
                    currency = option.get('currency', 'ZAR')

                    if total_price <= 0:
                        continue

                    # Calculate per-person price
                    price_per_person = total_price / max(total_guests, 1)

                    # Build pricing breakdown for PDF template
                    pricing_breakdown = {
                        'per_person_rates': {
                            'adult_sharing': round(price_per_person, 2)
                        },
                        'totals': {
                            'accommodation': round(total_price, 2),
                            'flights': 0,
                            'transfers': 0,
                            'grand_total': round(total_price, 2)
                        },
                        'nights': nights,
                        'currency': currency
                    }

                    hotel_option = {
                        'name': hotel_name,
                        'hotel_name': hotel_name,
                        'rating': rating,
                        'room_type': room_type,
                        'meal_plan': meal_plan,
                        'price_per_person': round(price_per_person, 2),
                        'total_price': round(total_price, 2),
                        'price_per_night': round(price_per_night, 2),
                        'includes_flights': False,
                        'includes_transfers': False,  # Live rates = accommodation only
                        'rate_id': hotel.get('hotel_id'),
                        'currency': currency,
                        'image_url': image_url,
                        'pricing_breakdown': pricing_breakdown,
                        'source': 'live_rates'  # Mark as live rates for tracking
                    }

                    hotel_options.append(hotel_option)

            # Sort by total price (cheapest first)
            hotel_options.sort(key=lambda x: x['total_price'])

            # If budget specified, prefer hotels closest to budget
            budget = customer_data.get('budget')
            if budget:
                try:
                    budget_value = float(budget)
                    # Sort by proximity to budget (prefer slightly under to over)
                    hotel_options.sort(key=lambda x: abs(x['price_per_person'] - budget_value))
                except (ValueError, TypeError):
                    pass  # Keep price-based sort

            # Deduplicate by hotel name (keep best option per hotel)
            seen_hotels = set()
            unique_options = []
            for option in hotel_options:
                if option['hotel_name'] not in seen_hotels:
                    unique_options.append(option)
                    seen_hotels.add(option['hotel_name'])

            logger.info(f"Live rates: {len(unique_options)} unique hotel options")
            return unique_options

        except Exception as e:
            logger.error(f"Live rates search failed: {e}", exc_info=True)
            return []

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
                'check_in': quote.get('check_in_date', quote.get('check_in', '')),
                'check_out': quote.get('check_out_date', quote.get('check_out', '')),
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
            logger.warning(f"[GET_QUOTE] Supabase not available for quote {quote_id}")
            return None

        try:
            result = self.supabase.client.table('quotes')\
                .select("*")\
                .eq('tenant_id', self.config.client_id)\
                .eq('quote_id', quote_id)\
                .limit(1)\
                .execute()

            if result.data and len(result.data) > 0:
                return result.data[0]

            # Fallback: try by UUID id column (in case some paths pass UUID)
            result = self.supabase.client.table('quotes')\
                .select("*")\
                .eq('tenant_id', self.config.client_id)\
                .eq('id', quote_id)\
                .limit(1)\
                .execute()

            if result.data and len(result.data) > 0:
                logger.info(f"[GET_QUOTE] Found quote by UUID id instead of quote_id: {quote_id}")
                return result.data[0]

            logger.warning(f"[GET_QUOTE] Quote not found: quote_id={quote_id}, tenant={self.config.client_id}")
            return None

        except Exception as e:
            logger.error(f"Failed to get quote {quote_id}: {e}")
            return None

    def list_quotes(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List quotes from Supabase"""
        logger.info(f"[QUOTE_LIST] Fetching quotes for tenant_id={self.config.client_id}, status={status}, limit={limit}")

        if not self.supabase or not self.supabase.client:
            logger.warning("[QUOTE_LIST] Supabase client not available")
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
            quotes = result.data or []
            logger.info(f"[QUOTE_LIST] Found {len(quotes)} quotes for tenant {self.config.client_id}")

            # Debug: log first quote's tenant_id if exists
            if quotes:
                logger.info(f"[QUOTE_LIST] First quote: id={quotes[0].get('quote_id')}, tenant={quotes[0].get('tenant_id')}, status={quotes[0].get('status')}")

            return quotes

        except Exception as e:
            logger.error(f"[QUOTE_LIST] Failed to list quotes: {e}")
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
        except (ValueError, TypeError) as e:
            logger.debug(f"Failed to parse date range: {e}")
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
        except (ValueError, TypeError) as e:
            logger.debug(f"Failed to parse date string: {e}")
            import pytz
            tz = pytz.UTC

        now = datetime.now(tz)
        candidate = now + timedelta(days=days_ahead)
        candidate = candidate.replace(hour=10, minute=0, second=0, microsecond=0)

        # Skip weekends
        while candidate.weekday() >= 5:
            candidate += timedelta(days=1)

        return candidate.astimezone(pytz.UTC).replace(tzinfo=None)

    def send_draft_quote(self, quote_id: str) -> Dict[str, Any]:
        """
        Send a draft quote to the customer.

        Retrieves a draft quote, regenerates the PDF, sends it via email,
        updates the status to 'sent', and schedules a follow-up call if
        the customer has a phone number.

        Args:
            quote_id: The quote ID to send

        Returns:
            Dict with success, quote_id, sent_at, customer_email, error (if any)
        """
        try:
            logger.info(f"Sending draft quote: {quote_id}")

            # 1. Retrieve the quote
            quote = self.get_quote(quote_id)
            if not quote:
                logger.error(f"Quote not found: {quote_id}")
                return {
                    'success': False,
                    'quote_id': quote_id,
                    'error': 'Quote not found'
                }

            # 2. Validate quote exists and status is 'draft'
            current_status = quote.get('status', '')
            if current_status != 'draft':
                logger.error(f"Quote {quote_id} is not a draft (status={current_status})")
                return {
                    'success': False,
                    'quote_id': quote_id,
                    'error': f"Quote is not a draft (current status: {current_status})"
                }

            # 3. Extract quote data
            customer_email = quote.get('customer_email')
            customer_name = quote.get('customer_name', 'Valued Customer')
            customer_phone = quote.get('customer_phone')
            destination = quote.get('destination', 'your destination')
            hotels = quote.get('hotels', [])

            if not customer_email:
                return {
                    'success': False,
                    'quote_id': quote_id,
                    'error': 'Quote has no customer email'
                }

            # Build customer data for PDF generation
            customer_data = {
                'name': customer_name,
                'email': customer_email,
                'phone': customer_phone,
                'destination': destination,
                'check_in': quote.get('check_in_date', ''),
                'check_out': quote.get('check_out_date', ''),
                'nights': quote.get('nights', 7),
                'adults': quote.get('adults', 2),
                'children': quote.get('children', 0),
                'children_ages': quote.get('children_ages', [])
            }

            # 4. Regenerate PDF
            pdf_bytes = None
            try:
                pdf_bytes = self.pdf_generator.generate_quote_pdf(quote, hotels, customer_data)
                logger.info(f"PDF regenerated for quote {quote_id}")
            except Exception as e:
                logger.error(f"PDF generation failed for quote {quote_id}: {e}", exc_info=True)
                return {
                    'success': False,
                    'quote_id': quote_id,
                    'error': 'PDF generation failed'
                }

            if not pdf_bytes:
                return {
                    'success': False,
                    'quote_id': quote_id,
                    'error': 'PDF generation returned empty result'
                }

            # 5. Send email using EmailSender
            email_sent = False
            try:
                email_sent = self.email_sender.send_quote_email(
                    customer_email=customer_email,
                    customer_name=customer_name,
                    quote_pdf_data=pdf_bytes,
                    destination=destination,
                    quote_id=quote_id
                )
            except Exception as e:
                logger.error(f"Email sending failed for quote {quote_id}: {e}", exc_info=True)
                return {
                    'success': False,
                    'quote_id': quote_id,
                    'error': 'Email sending failed'
                }

            if not email_sent:
                return {
                    'success': False,
                    'quote_id': quote_id,
                    'error': 'Email sending failed (SendGrid returned error)'
                }

            # 6. Update quote status to 'sent'
            sent_at = datetime.utcnow().isoformat()
            status_updated = self.update_quote_status(quote_id, 'sent')
            if not status_updated:
                logger.warning(f"Failed to update quote status to 'sent' for {quote_id}")

            # 7. Schedule follow-up call if customer has phone number
            call_queued = False
            if customer_phone:
                call_queued = self._schedule_follow_up_call(
                    quote_id=quote_id,
                    customer_name=customer_name,
                    customer_email=customer_email,
                    customer_phone=customer_phone,
                    destination=destination
                )

            # 8. Create notification for "quote sent"
            try:
                from src.api.notifications_routes import NotificationService
                notification_service = NotificationService(self.config)
                notification_service.notify_quote_sent(
                    customer_name=customer_name,
                    customer_email=customer_email,
                    destination=destination,
                    quote_id=quote_id
                )
            except Exception as e:
                logger.warning(f"Failed to send quote sent notification: {e}")

            logger.info(f"Draft quote {quote_id} sent successfully to {customer_email}")

            return {
                'success': True,
                'quote_id': quote_id,
                'sent_at': sent_at,
                'customer_email': customer_email,
                'status': 'sent',
                'call_queued': call_queued
            }

        except Exception as e:
            logger.error(f"Error sending draft quote {quote_id}: {e}", exc_info=True)
            return {
                'success': False,
                'quote_id': quote_id,
                'error': 'Failed to send quote'
            }

    def resend_quote(self, quote_id: str) -> Dict[str, Any]:
        """
        Resend an existing quote to the customer.

        Unlike send_draft_quote, this works on quotes of any status.
        It regenerates the PDF and sends the email, but does NOT change the status.

        Args:
            quote_id: The quote ID to resend

        Returns:
            Dict with success, quote_id, sent_at, customer_email, error (if any)
        """
        try:
            logger.info(f"Resending quote: {quote_id}")

            # 1. Retrieve the quote
            quote = self.get_quote(quote_id)
            if not quote:
                logger.error(f"Quote not found: {quote_id}")
                return {
                    'success': False,
                    'quote_id': quote_id,
                    'error': 'Quote not found'
                }

            # 2. Extract quote data
            customer_email = quote.get('customer_email')
            customer_name = quote.get('customer_name', 'Valued Customer')
            destination = quote.get('destination', 'your destination')
            hotels = quote.get('hotels', [])

            if not customer_email:
                return {
                    'success': False,
                    'quote_id': quote_id,
                    'error': 'Quote has no customer email'
                }

            # Build customer data for PDF generation
            customer_data = {
                'name': customer_name,
                'email': customer_email,
                'phone': quote.get('customer_phone'),
                'destination': destination,
                'check_in': quote.get('check_in_date', ''),
                'check_out': quote.get('check_out_date', ''),
                'nights': quote.get('nights', 7),
                'adults': quote.get('adults', 2),
                'children': quote.get('children', 0),
                'children_ages': quote.get('children_ages', [])
            }

            # 3. Regenerate PDF
            pdf_bytes = None
            try:
                pdf_bytes = self.pdf_generator.generate_quote_pdf(quote, hotels, customer_data)
                logger.info(f"PDF regenerated for quote {quote_id}")
            except Exception as e:
                logger.error(f"PDF generation failed for quote {quote_id}: {e}", exc_info=True)
                return {
                    'success': False,
                    'quote_id': quote_id,
                    'error': 'PDF generation failed'
                }

            if not pdf_bytes:
                return {
                    'success': False,
                    'quote_id': quote_id,
                    'error': 'PDF generation returned no data'
                }

            # 4. Send email via tenant's SendGrid
            try:
                self.email_sender.send_quote_email(
                    customer_email=customer_email,
                    customer_name=customer_name,
                    quote_pdf_data=pdf_bytes,
                    destination=destination,
                    quote_id=quote_id
                )
                logger.info(f"Quote {quote_id} resent to {customer_email}")
            except Exception as e:
                logger.error(f"Email send failed for quote {quote_id}: {e}", exc_info=True)
                return {
                    'success': False,
                    'quote_id': quote_id,
                    'error': 'Email sending failed'
                }

            sent_at = datetime.now().isoformat()

            return {
                'success': True,
                'quote_id': quote_id,
                'sent_at': sent_at,
                'customer_email': customer_email,
                'message': f'Quote resent to {customer_email}'
            }

        except Exception as e:
            logger.error(f"Error resending quote {quote_id}: {e}", exc_info=True)
            return {
                'success': False,
                'quote_id': quote_id,
                'error': 'Failed to resend quote'
            }
