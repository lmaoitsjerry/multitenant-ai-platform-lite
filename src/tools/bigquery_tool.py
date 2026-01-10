"""
BigQuery Tool - Multi-Tenant Version

Refactored to use ClientConfig and DatabaseTables abstraction.
No hardcoded dataset names or table references.

Usage:
    from config.loader import ClientConfig
    from src.tools.bigquery_tool import BigQueryTool

    config = ClientConfig('africastay')
    bq = BigQueryTool(config)
    hotels = bq.find_matching_hotels('Zanzibar', ...)
"""

from google.cloud import bigquery
from typing import List, Dict, Any, Optional
import logging

from config.loader import ClientConfig
from config.database import DatabaseTables

logger = logging.getLogger(__name__)


class BigQueryTool:
    """BigQuery operations for customer data and analytics"""

    def __init__(self, config: ClientConfig):
        """
        Initialize BigQuery tool with client configuration

        Args:
            config: ClientConfig instance
        """
        self.config = config
        self.db = DatabaseTables(config)

        try:
            self.client = bigquery.Client(project=config.gcp_project_id)
            self.project_id = config.gcp_project_id
            logger.info(f"BigQuery client initialized for {config.client_id}")
        except Exception as e:
            logger.error(f"BigQuery init error: {e}")
            self.client = None

    def find_matching_hotels(
        self,
        destination: str,
        check_in: str,
        check_out: str,
        nights: int,
        adults: int,
        children_ages: Optional[List[int]] = None,
        budget_per_person: Optional[int] = None,
        meal_plan_pref: Optional[str] = None,
        has_children: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Find ALL room/meal combinations for hotels matching customer requirements

        Args:
            destination: Destination name
            check_in: Check-in date (YYYY-MM-DD)
            check_out: Check-out date (YYYY-MM-DD)
            nights: Number of nights
            adults: Number of adults
            children_ages: List of children ages
            budget_per_person: Budget per person
            meal_plan_pref: Preferred meal plan
            has_children: Whether the group includes children

        Returns:
            List of matching hotel rate records
        """
        if not self.client:
            return []

        # Get destination search terms (name + aliases from config)
        search_terms = self.config.get_destination_search_terms(destination)
        logger.info(f"Searching hotels for destinations: {search_terms}")

        # Query only the hotel_rates table - simplified to avoid missing columns
        query = f"""
        SELECT
            r.rate_id,
            r.hotel_name,
            r.hotel_rating,
            r.room_type,
            r.meal_plan,
            r.total_7nights_pps,
            r.total_7nights_single,
            r.total_7nights_child,
            r.check_in_date,
            r.check_out_date,
            r.nights
        FROM {self.db.hotel_rates} r
        WHERE
            UPPER(r.destination) IN UNNEST(@destinations)
            AND r.is_active = TRUE
            AND r.nights = @nights
            -- Customer dates must fall within rate validity period
            AND @check_in >= r.check_in_date
            AND @check_in <= r.check_out_date
        """

        # Add optional meal plan filter
        if meal_plan_pref:
            query += f" AND r.meal_plan = '{meal_plan_pref}'"

        # Add deduplication BEFORE ORDER BY
        query += """
        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY r.hotel_name, r.check_in_date, r.check_out_date, r.room_type, r.meal_plan
            ORDER BY r.rate_id DESC
        ) = 1
        ORDER BY
            -- Priority 1: Exact date match
            CASE WHEN @check_in = r.check_in_date AND @check_out = r.check_out_date THEN 1
            -- Priority 2: Customer dates within rate period
                 WHEN @check_in >= r.check_in_date AND @check_out <= r.check_out_date THEN 2
            -- Priority 3: Same month/day (ignore year)
                 WHEN EXTRACT(MONTH FROM @check_in) = EXTRACT(MONTH FROM r.check_in_date)
                  AND EXTRACT(DAY FROM @check_in) = EXTRACT(DAY FROM r.check_in_date) THEN 3
            -- Priority 4: Closest month
                 ELSE 4 + ABS(EXTRACT(MONTH FROM @check_in) - EXTRACT(MONTH FROM r.check_in_date))
            END,
            r.total_7nights_pps ASC
        LIMIT 50
        """

        try:
            # Convert search terms to uppercase for case-insensitive matching
            destinations_upper = [d.upper() for d in search_terms]

            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ArrayQueryParameter("destinations", "STRING", destinations_upper),
                    bigquery.ScalarQueryParameter("check_in", "DATE", check_in),
                    bigquery.ScalarQueryParameter("check_out", "DATE", check_out),
                    bigquery.ScalarQueryParameter("nights", "INTEGER", nights)
                ]
            )
            results = self.client.query(query, job_config=job_config).result()
            hotels = [dict(row) for row in results]
            logger.info(f"Found {len(hotels)} hotels for {destination}")
            return hotels
        except Exception as e:
            logger.error(f"Error finding matching hotels: {e}")
            return []

    def search_hotels_by_name(
        self,
        search_term: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for hotels by name or keyword (for helpdesk queries)

        Args:
            search_term: Hotel name or keyword to search
            limit: Maximum number of results

        Returns:
            List of hotels with basic info and sample pricing
        """
        if not self.client:
            return []

        query = f"""
        SELECT DISTINCT
            hotel_name,
            hotel_rating,
            destination,
            MIN(total_7nights_pps) as min_price_pps,
            MAX(total_7nights_pps) as max_price_pps,
            STRING_AGG(DISTINCT meal_plan, ', ' LIMIT 5) as meal_plans,
            STRING_AGG(DISTINCT room_type, ', ' LIMIT 5) as room_types
        FROM {self.db.hotel_rates}
        WHERE
            is_active = TRUE
            AND (
                LOWER(hotel_name) LIKE LOWER(@search_term)
                OR LOWER(destination) LIKE LOWER(@search_term)
            )
        GROUP BY hotel_name, hotel_rating, destination
        ORDER BY hotel_name
        LIMIT @limit
        """

        try:
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("search_term", "STRING", f"%{search_term}%"),
                    bigquery.ScalarQueryParameter("limit", "INTEGER", limit)
                ]
            )
            results = self.client.query(query, job_config=job_config).result()
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error searching hotels: {e}")
            return []

    def get_hotel_info(
        self,
        hotel_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed info about a specific hotel (for helpdesk queries)

        Args:
            hotel_name: Exact or partial hotel name

        Returns:
            Hotel info with pricing, room types, meal plans
        """
        if not self.client:
            return None

        query = f"""
        SELECT
            hotel_name,
            hotel_rating,
            destination,
            MIN(total_7nights_pps) as min_price_pps,
            MAX(total_7nights_pps) as max_price_pps,
            MIN(total_7nights_single) as min_single_price,
            MIN(total_7nights_child) as min_child_price,
            STRING_AGG(DISTINCT meal_plan, ', ' LIMIT 10) as available_meal_plans,
            STRING_AGG(DISTINCT room_type, ', ' LIMIT 10) as available_room_types,
            MIN(nights) as min_nights,
            MAX(nights) as max_nights,
            COUNT(DISTINCT rate_id) as rate_count
        FROM {self.db.hotel_rates}
        WHERE
            is_active = TRUE
            AND LOWER(hotel_name) LIKE LOWER(@hotel_name)
        GROUP BY hotel_name, hotel_rating, destination
        LIMIT 1
        """

        try:
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("hotel_name", "STRING", f"%{hotel_name}%")
                ]
            )
            results = list(self.client.query(query, job_config=job_config).result())
            return dict(results[0]) if results else None
        except Exception as e:
            logger.error(f"Error getting hotel info: {e}")
            return None

    def calculate_quote_price(
        self,
        rate_id: str,
        adults: int,
        children_ages: Optional[List[int]] = None,
        flight_price_pp: int = 0,
        single_adults: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate per-person pricing for quote

        Returns per-person rates for adults, children, and infants separately
        - Infants (<2) = R 1,000 flat fee
        - Children (2-12) = child hotel + flight + transfer
        - Adults (12+) = adult hotel + flight + transfer

        Args:
            rate_id: Hotel rate ID
            adults: Number of adults
            children_ages: List of children ages
            flight_price_pp: Flight price per person
            single_adults: Number of adults in single rooms

        Returns:
            Dictionary with pricing breakdown or None if error
        """
        if not self.client:
            return None

        query = f"""
        SELECT
            total_7nights_pps,
            total_7nights_single,
            total_7nights_child
        FROM {self.db.hotel_rates}
        WHERE rate_id = @rate_id
        LIMIT 1
        """

        try:
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("rate_id", "STRING", rate_id)
                ]
            )
            results = self.client.query(query, job_config=job_config).result()
            rate = next(results, None)

            if not rate:
                return None

            # MIXED ROOM CONFIGURATION LOGIC
            per_child_rate = int(rate.total_7nights_child) if rate.total_7nights_child else 0
            per_infant_rate = 1000  # Flat rate

            # Count travelers by type
            num_adults_sharing = adults
            num_adults_single = single_adults
            num_children = 0
            num_infants = 0

            if children_ages:
                for age in children_ages:
                    if age < 2:
                        num_infants += 1
                    else:
                        num_children += 1

            # PRICING LOGIC
            if single_adults > 0:
                # MIXED ROOMS: Some single, some sharing
                num_adults_sharing = adults - single_adults
                num_adults_single = single_adults

                per_adult_sharing_rate = int(rate.total_7nights_pps) if rate.total_7nights_pps else 0
                per_adult_single_rate = int(rate.total_7nights_single) if rate.total_7nights_single else (int(rate.total_7nights_pps) if rate.total_7nights_pps else 0)

                total_sharing_adults_cost = per_adult_sharing_rate * num_adults_sharing
                total_single_adults_cost = per_adult_single_rate * num_adults_single
                total_adults_cost = total_sharing_adults_cost + total_single_adults_cost

            elif adults == 1 and (not children_ages or len(children_ages) == 0):
                # SINGLE TRAVELER: 1 adult, no children
                num_adults_single = 1
                num_adults_sharing = 0
                per_adult_single_rate = int(rate.total_7nights_single) if rate.total_7nights_single else (int(rate.total_7nights_pps) if rate.total_7nights_pps else 0)
                per_adult_sharing_rate = 0
                total_adults_cost = per_adult_single_rate

            else:
                # ALL SHARING: Default scenario
                num_adults_sharing = adults
                num_adults_single = 0
                per_adult_sharing_rate = int(rate.total_7nights_pps) if rate.total_7nights_pps else 0
                per_adult_single_rate = 0
                total_adults_cost = per_adult_sharing_rate * num_adults_sharing

            # Calculate child/infant costs
            total_children_cost = per_child_rate * num_children
            total_infants_cost = per_infant_rate * num_infants
            grand_total = total_adults_cost + total_children_cost + total_infants_cost

            return {
                'per_person_rates': {
                    'adult_sharing': per_adult_sharing_rate if 'per_adult_sharing_rate' in locals() else (int(rate.total_7nights_pps) if rate.total_7nights_pps else 0),
                    'adult_single': per_adult_single_rate if 'per_adult_single_rate' in locals() else (int(rate.total_7nights_single) if rate.total_7nights_single else 0),
                    'child': per_child_rate,
                    'infant': per_infant_rate
                },
                'traveler_counts': {
                    'adults_sharing': num_adults_sharing,
                    'adults_single': num_adults_single,
                    'children': num_children,
                    'infants': num_infants
                },
                'totals': {
                    'adults': total_adults_cost,
                    'children': total_children_cost,
                    'infants': total_infants_cost,
                    'grand_total': grand_total
                },
                'breakdown': {
                    'adult_hotel': int(rate.total_7nights_pps) if rate.total_7nights_pps else 0,
                    'child_hotel': int(rate.total_7nights_child) if rate.total_7nights_child else 0,
                    'adult_transfer': 0,  # Already included in totals
                    'child_transfer': 0,  # Already included in totals
                    'flight_pp': 0  # Already included in totals
                }
            }
        except Exception as e:
            logger.error(f"Error calculating quote price: {e}")
            return None

    def get_next_consultant_round_robin(self) -> Optional[Dict[str, Any]]:
        """
        Get next consultant using round-robin assignment

        Returns:
            Consultant dictionary or None
        """
        if not self.client:
            return None

        # Return None if consultants table doesn't exist - we'll handle this gracefully
        try:
            query = f"""
            SELECT consultant_id, name, email
            FROM {self.db.consultants}
            WHERE is_active = TRUE
            ORDER BY COALESCE(last_assigned, TIMESTAMP('2000-01-01')) ASC
            LIMIT 1
            """

            results = self.client.query(query).result()
            consultant = next(results, None)

            if consultant:
                # Update last_assigned timestamp
                try:
                    update_query = f"""
                    UPDATE {self.db.consultants}
                    SET last_assigned = CURRENT_TIMESTAMP()
                    WHERE consultant_id = '{consultant.consultant_id}'
                    """
                    self.client.query(update_query).result()
                except Exception:
                    pass  # Silent fail on update

                return dict(consultant)
            return None

        except Exception as e:
            logger.warning(f"Consultant lookup failed (table may not exist): {e}")
            return None

    def get_flight_price(self, destination: str, check_in_date: str) -> int:
        """
        Get flight price for destination and date

        Args:
            destination: Destination name
            check_in_date: Check-in date (YYYY-MM-DD)

        Returns:
            Flight price per person (integer)
        """
        if not self.client:
            return 0

        try:
            query = f"""
            SELECT price_per_person
            FROM {self.db.flight_prices}
            WHERE UPPER(destination) = UPPER(@destination)
            ORDER BY ABS(DATE_DIFF(@check_in, departure_date, DAY)) ASC
            LIMIT 1
            """

            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("destination", "STRING", destination),
                    bigquery.ScalarQueryParameter("check_in", "DATE", check_in_date)
                ]
            )
            results = self.client.query(query, job_config=job_config).result()
            flight = next(results, None)

            if flight:
                return int(flight.price_per_person)
            return 0

        except Exception as e:
            logger.warning(f"Flight price lookup failed (table may not exist): {e}")
            return 0
