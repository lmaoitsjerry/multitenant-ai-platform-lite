"""
LLM Email Parser - Uses OpenAI for intelligent email parsing

Falls back to UniversalEmailParser (rule-based) on any failure.
Uses GPT-4o-mini for cost efficiency (~$0.15/1M input tokens).
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from config.loader import ClientConfig

logger = logging.getLogger(__name__)


class LLMEmailParser:
    """LLM-powered email parser with rule-based fallback"""

    def __init__(self, config: ClientConfig):
        self.config = config
        self.destinations = config.destination_names
        self.openai_api_key = os.getenv('OPENAI_API_KEY')

        # Initialize rule-based parser as fallback
        from src.agents.universal_email_parser import UniversalEmailParser
        self.fallback_parser = UniversalEmailParser(config)

        logger.info(f"LLM parser initialized with {len(self.destinations)} destinations")

    def parse(self, email_body: str, subject: str = "") -> Dict[str, Any]:
        """
        Parse email using LLM with fallback to rule-based.

        Returns dict with:
        - destination: str
        - check_in: str (YYYY-MM-DD) or None
        - check_out: str (YYYY-MM-DD) or None
        - adults: int
        - children: int
        - children_ages: List[int]
        - budget: int or None
        - budget_is_per_person: bool
        - name: str
        - email: str
        - phone: str or None
        - is_travel_inquiry: bool
        - parse_method: str ('llm' or 'fallback')
        """
        full_text = f"Subject: {subject}\n\n{email_body}"

        # Try LLM parsing first
        if self.openai_api_key:
            try:
                result = self._parse_with_llm(full_text)
                if result and result.get('destination'):
                    result['parse_method'] = 'llm'
                    logger.info(f"LLM parsed: {result.get('destination')} | "
                               f"{result.get('adults', 2)}A+{result.get('children', 0)}C")
                    return result
            except Exception as e:
                logger.warning(f"LLM parsing failed, using fallback: {e}")
        else:
            logger.info("No OPENAI_API_KEY, using fallback parser")

        # Fallback to rule-based parser
        result = self.fallback_parser.parse(email_body, subject)
        result['parse_method'] = 'fallback'
        return result

    def _parse_with_llm(self, full_text: str) -> Optional[Dict[str, Any]]:
        """Parse email using OpenAI GPT-4o-mini"""
        import openai

        # Build destination list for context
        dest_list = ', '.join(self.destinations[:20])  # Limit for prompt size

        system_prompt = f"""You are an email parser for a travel agency. Extract travel inquiry details from customer emails.

Available destinations: {dest_list}

Return a JSON object with these fields (use null for unknown):
- destination: string (must match one of the available destinations, or closest match)
- check_in: string (YYYY-MM-DD format) or null
- check_out: string (YYYY-MM-DD format) or null
- adults: integer (default 2 if not specified)
- children: integer (default 0 if not specified)
- children_ages: array of integers (empty if not specified)
- budget: integer (total budget in local currency, e.g., ZAR) or null
- budget_is_per_person: boolean (true if budget was specified per person)
- name: string (customer name) or "Valued Customer"
- email: string (customer email) or null
- phone: string (customer phone) or null
- is_travel_inquiry: boolean (true if this is about travel/vacation)
- special_requests: string (any special requirements mentioned) or null

Rules:
1. If dates mention a month without year, assume next occurrence of that month
2. If nights are mentioned without specific dates, set check_out = check_in + nights
3. Convert "2 pax" to adults=2, "2 adults 1 child" to adults=2, children=1
4. Budget might be in format "R50000" (ZAR) or "50k" - convert to integer
5. Match destination to closest available option (e.g., "Zanzibar" matches "Zanzibar")

Return ONLY valid JSON, no markdown or explanation."""

        try:
            client = openai.OpenAI(api_key=self.openai_api_key)

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": full_text[:4000]}  # Limit input size
                ],
                temperature=0.1,  # Low temperature for consistent extraction
                max_tokens=500,
                response_format={"type": "json_object"},
                timeout=10.0  # 10 second timeout
            )

            result_text = response.choices[0].message.content
            result = json.loads(result_text)

            # Validate and normalize result
            return self._normalize_llm_result(result)

        except json.JSONDecodeError as e:
            logger.error(f"LLM returned invalid JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return None

    def _normalize_llm_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize LLM output to expected format"""
        normalized = {
            'destination': result.get('destination') or self.destinations[0] if self.destinations else 'Unknown',
            'check_in': result.get('check_in'),
            'check_out': result.get('check_out'),
            'adults': int(result.get('adults', 2)),
            'children': int(result.get('children', 0)),
            'children_ages': result.get('children_ages', []),
            'budget': None,
            'budget_is_per_person': bool(result.get('budget_is_per_person', False)),
            'name': result.get('name', 'Valued Customer'),
            'email': result.get('email'),
            'phone': result.get('phone'),
            'is_travel_inquiry': bool(result.get('is_travel_inquiry', True)),
            'special_requests': result.get('special_requests')
        }

        # Handle budget conversion
        budget = result.get('budget')
        if budget is not None:
            try:
                if isinstance(budget, str):
                    budget = budget.replace('R', '').replace(',', '').replace('k', '000')
                normalized['budget'] = int(float(budget))
            except (ValueError, TypeError):
                normalized['budget'] = None

        # Map destination to closest match if not exact
        if normalized['destination'] not in self.destinations:
            normalized['destination'] = self._find_closest_destination(normalized['destination'])

        # Also set total_budget for compatibility
        if normalized['budget']:
            normalized['total_budget'] = normalized['budget']

        return normalized

    def _find_closest_destination(self, destination: str) -> str:
        """Find closest matching destination from available list"""
        if not destination or not self.destinations:
            return self.destinations[0] if self.destinations else 'Unknown'

        from difflib import SequenceMatcher

        dest_lower = destination.lower()
        best_match = self.destinations[0]
        best_ratio = 0.0

        for d in self.destinations:
            ratio = SequenceMatcher(None, dest_lower, d.lower()).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = d

        # Only use match if reasonably confident
        if best_ratio >= 0.6:
            return best_match

        return self.destinations[0] if self.destinations else 'Unknown'
