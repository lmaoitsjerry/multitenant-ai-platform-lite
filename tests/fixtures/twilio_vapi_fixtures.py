"""
Twilio/VAPI Mock Fixtures

Provides reusable mock infrastructure for Twilio and VAPI API testing:
- MockHTTPResponse: Simulates requests.Response objects
- TwilioResponseFactory: Factory methods for Twilio API responses
- VAPIResponseFactory: Factory methods for VAPI API responses
- MockRequestsSession: Pattern-based response matching for requests
- Data generators: Factory functions for realistic test data

Usage:
    from tests.fixtures.twilio_vapi_fixtures import (
        MockHTTPResponse,
        TwilioResponseFactory,
        VAPIResponseFactory,
        create_mock_provisioner,
        generate_available_numbers,
    )

    # Create mocked response
    response = TwilioResponseFactory.available_numbers([
        {'number': '+27123456789', 'locality': 'Cape Town'}
    ])

    # Create fully configured mock provisioner
    provisioner = create_mock_provisioner(
        twilio_responses={'search': response},
        vapi_responses={}
    )
"""

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch


class MockHTTPResponse:
    """
    Simulates a requests.Response object.

    Attributes:
        status_code: HTTP status code (e.g., 200, 404)
        text: Response body as string
        _json_data: Parsed JSON data

    Example:
        response = MockHTTPResponse(200, {'available_phone_numbers': [...]})
        assert response.status_code == 200
        assert response.json() == {'available_phone_numbers': [...]}
    """

    def __init__(self, status_code: int, data: Dict = None):
        """
        Initialize mock HTTP response.

        Args:
            status_code: HTTP status code
            data: Response data (will be JSON serialized for text property)
        """
        self.status_code = status_code
        self._json_data = data or {}
        self.text = json.dumps(self._json_data) if data else ""

    def json(self) -> Dict:
        """Return parsed JSON data."""
        return self._json_data

    def __repr__(self):
        return f"MockHTTPResponse(status_code={self.status_code})"


class TwilioResponseFactory:
    """
    Factory for creating Twilio API response objects.

    Provides static methods for common Twilio API responses:
    - Available numbers search
    - Number purchase
    - Number listing
    - Address registration
    - Pricing information

    Example:
        response = TwilioResponseFactory.available_numbers([
            {'phone_number': '+27123456789', 'locality': 'Cape Town'}
        ])
    """

    @staticmethod
    def available_numbers(numbers: List[Dict]) -> MockHTTPResponse:
        """
        Create search results response for available numbers.

        Args:
            numbers: List of number dictionaries with phone_number, locality, etc.

        Returns:
            MockHTTPResponse with available_phone_numbers list
        """
        return MockHTTPResponse(200, {
            'available_phone_numbers': numbers,
            'uri': '/2010-04-01/Accounts/ACxxx/AvailablePhoneNumbers/ZA/Local.json'
        })

    @staticmethod
    def purchase_success(phone_number: str, sid: str) -> MockHTTPResponse:
        """
        Create successful purchase response.

        Args:
            phone_number: The purchased phone number
            sid: The Twilio SID for the number

        Returns:
            MockHTTPResponse with purchase details
        """
        return MockHTTPResponse(201, {
            'phone_number': phone_number,
            'sid': sid,
            'friendly_name': phone_number,
            'account_sid': 'ACxxx',
            'date_created': datetime.utcnow().isoformat(),
            'capabilities': {'voice': True, 'sms': True}
        })

    @staticmethod
    def purchase_error(error_message: str, code: int = 400) -> MockHTTPResponse:
        """
        Create failed purchase response.

        Args:
            error_message: Error description
            code: HTTP status code (default 400)

        Returns:
            MockHTTPResponse with error details
        """
        return MockHTTPResponse(code, {
            'code': code,
            'message': error_message,
            'status': code
        })

    @staticmethod
    def list_numbers(numbers: List[Dict]) -> MockHTTPResponse:
        """
        Create list account numbers response.

        Args:
            numbers: List of number dictionaries with phone_number, sid, etc.

        Returns:
            MockHTTPResponse with incoming_phone_numbers list
        """
        return MockHTTPResponse(200, {
            'incoming_phone_numbers': numbers,
            'uri': '/2010-04-01/Accounts/ACxxx/IncomingPhoneNumbers.json',
            'page': 0,
            'page_size': 50
        })

    @staticmethod
    def register_address_success(sid: str, friendly_name: str = None) -> MockHTTPResponse:
        """
        Create successful address registration response.

        Args:
            sid: The address SID
            friendly_name: Optional friendly name

        Returns:
            MockHTTPResponse with address details
        """
        return MockHTTPResponse(201, {
            'sid': sid,
            'friendly_name': friendly_name or 'Business Address',
            'validated': True,
            'account_sid': 'ACxxx',
            'date_created': datetime.utcnow().isoformat()
        })

    @staticmethod
    def register_address_error(error_message: str) -> MockHTTPResponse:
        """
        Create failed address registration response.

        Args:
            error_message: Error description

        Returns:
            MockHTTPResponse with error details
        """
        return MockHTTPResponse(400, {
            'code': 400,
            'message': error_message,
            'status': 400
        })

    @staticmethod
    def list_addresses(addresses: List[Dict]) -> MockHTTPResponse:
        """
        Create list addresses response.

        Args:
            addresses: List of address dictionaries

        Returns:
            MockHTTPResponse with addresses list
        """
        return MockHTTPResponse(200, {
            'addresses': addresses,
            'uri': '/2010-04-01/Accounts/ACxxx/Addresses.json'
        })

    @staticmethod
    def pricing_info(country: str) -> MockHTTPResponse:
        """
        Create country pricing response.

        Args:
            country: ISO country code

        Returns:
            MockHTTPResponse with pricing information
        """
        return MockHTTPResponse(200, {
            'country': country,
            'iso_country': country,
            'phone_number_prices': [
                {
                    'type': 'local',
                    'base_price': '1.00',
                    'current_price': '1.00'
                }
            ]
        })


class VAPIResponseFactory:
    """
    Factory for creating VAPI API response objects.

    Provides static methods for common VAPI API responses:
    - Phone number import
    - Assistant assignment
    - Error responses

    Example:
        response = VAPIResponseFactory.import_success('vapi_123', '+27123456789')
    """

    @staticmethod
    def import_success(vapi_id: str, number: str, assistant_id: str = None) -> MockHTTPResponse:
        """
        Create successful phone number import response.

        Args:
            vapi_id: The VAPI phone number ID
            number: The phone number
            assistant_id: Optional assigned assistant ID

        Returns:
            MockHTTPResponse with import details
        """
        data = {
            'id': vapi_id,
            'number': number,
            'provider': 'twilio',
            'createdAt': datetime.utcnow().isoformat()
        }
        if assistant_id:
            data['assistantId'] = assistant_id
        return MockHTTPResponse(201, data)

    @staticmethod
    def import_error(error_message: str, code: int = 400) -> MockHTTPResponse:
        """
        Create failed import response.

        Args:
            error_message: Error description
            code: HTTP status code

        Returns:
            MockHTTPResponse with error details
        """
        return MockHTTPResponse(code, {
            'error': error_message,
            'statusCode': code
        })

    @staticmethod
    def assign_success(data: Dict) -> MockHTTPResponse:
        """
        Create successful assistant assignment response.

        Args:
            data: Updated phone number data

        Returns:
            MockHTTPResponse with assignment details
        """
        return MockHTTPResponse(200, data)

    @staticmethod
    def assign_error(error_message: str, code: int = 400) -> MockHTTPResponse:
        """
        Create failed assignment response.

        Args:
            error_message: Error description
            code: HTTP status code

        Returns:
            MockHTTPResponse with error details
        """
        return MockHTTPResponse(code, {
            'error': error_message,
            'statusCode': code
        })


# ==================== Data Generators ====================

def generate_available_numbers(
    n: int = 5,
    country_code: str = 'ZA',
    area_code: str = None
) -> List[Dict[str, Any]]:
    """
    Generate list of available phone numbers for search results.

    Args:
        n: Number of numbers to generate
        country_code: Country code (ZA, US, GB, etc.)
        area_code: Optional area code prefix

    Returns:
        List of available number dictionaries

    Example:
        numbers = generate_available_numbers(5, 'ZA')
        # Returns 5 South African phone numbers
    """
    prefix_map = {
        'ZA': '+27',
        'US': '+1',
        'GB': '+44',
        'AU': '+61',
        'CA': '+1',
        'DE': '+49',
        'FR': '+33',
    }

    locality_map = {
        'ZA': ['Cape Town', 'Johannesburg', 'Durban', 'Pretoria', 'Port Elizabeth'],
        'US': ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix'],
        'GB': ['London', 'Manchester', 'Birmingham', 'Leeds', 'Glasgow'],
        'AU': ['Sydney', 'Melbourne', 'Brisbane', 'Perth', 'Adelaide'],
        'CA': ['Toronto', 'Vancouver', 'Montreal', 'Calgary', 'Ottawa'],
        'DE': ['Berlin', 'Munich', 'Hamburg', 'Frankfurt', 'Cologne'],
        'FR': ['Paris', 'Lyon', 'Marseille', 'Toulouse', 'Nice'],
    }

    prefix = prefix_map.get(country_code, '+1')
    localities = locality_map.get(country_code, ['Unknown'])

    numbers = []
    for i in range(n):
        # Generate realistic phone number
        if area_code:
            phone = f"{prefix}{area_code}{str(1000000 + i).zfill(7)}"
        else:
            phone = f"{prefix}{str(100000000 + i * 1111)}"

        numbers.append({
            'phone_number': phone,
            'friendly_name': phone,
            'locality': localities[i % len(localities)],
            'region': country_code,
            'iso_country': country_code,
            'capabilities': {
                'voice': True,
                'SMS': True,
                'MMS': country_code in ['US', 'CA']
            },
            'address_requirements': 'any' if country_code in ['ZA', 'GB'] else 'none'
        })

    return numbers


def generate_twilio_number(
    phone: str,
    sid: str,
    friendly_name: str = None,
    date_created: str = None
) -> Dict[str, Any]:
    """
    Generate a single Twilio incoming phone number record.

    Args:
        phone: Phone number in E.164 format
        sid: Twilio phone number SID
        friendly_name: Optional friendly name
        date_created: Optional creation date

    Returns:
        Twilio incoming phone number dictionary

    Example:
        number = generate_twilio_number('+27123456789', 'PN123')
    """
    return {
        'phone_number': phone,
        'sid': sid,
        'friendly_name': friendly_name or phone,
        'date_created': date_created or datetime.utcnow().isoformat(),
        'account_sid': 'ACxxx',
        'capabilities': {'voice': True, 'sms': True}
    }


def generate_address(
    sid: str,
    country: str = 'ZA',
    city: str = 'Cape Town',
    customer_name: str = 'Test Company',
    validated: bool = True
) -> Dict[str, Any]:
    """
    Generate a Twilio address record.

    Args:
        sid: Address SID
        country: ISO country code
        city: City name
        customer_name: Business name
        validated: Whether address is validated

    Returns:
        Twilio address dictionary

    Example:
        addr = generate_address('AD123', 'ZA', 'Cape Town')
    """
    return {
        'sid': sid,
        'friendly_name': f'{customer_name} - {city}',
        'customer_name': customer_name,
        'street': '123 Main Street',
        'city': city,
        'region': 'Western Cape' if country == 'ZA' else 'Region',
        'postal_code': '8001',
        'iso_country': country,
        'validated': validated,
        'account_sid': 'ACxxx',
        'date_created': datetime.utcnow().isoformat()
    }


# ==================== Mock Session ====================

class MockRequestsSession:
    """
    Pattern-based mock for requests library.

    Matches URLs against patterns and returns configured responses.
    Supports GET, POST, and PATCH methods.

    Example:
        session = MockRequestsSession()
        session.add_response('GET', r'AvailablePhoneNumbers.*Local',
                            TwilioResponseFactory.available_numbers([...]))
        session.add_response('POST', r'IncomingPhoneNumbers',
                            TwilioResponseFactory.purchase_success(...))

        # In test:
        with patch('requests.get', session.get):
            with patch('requests.post', session.post):
                result = provisioner.search_available_numbers('ZA')
    """

    def __init__(self):
        """Initialize mock session with empty response mappings."""
        self._get_responses: List[tuple] = []  # (pattern, response)
        self._post_responses: List[tuple] = []
        self._patch_responses: List[tuple] = []
        self._default_response = MockHTTPResponse(404, {'error': 'Not found'})

        # Track calls for assertions
        self.get_calls: List[Dict] = []
        self.post_calls: List[Dict] = []
        self.patch_calls: List[Dict] = []

    def add_response(
        self,
        method: str,
        url_pattern: str,
        response: MockHTTPResponse
    ) -> 'MockRequestsSession':
        """
        Add a response for a URL pattern.

        Args:
            method: HTTP method (GET, POST, PATCH)
            url_pattern: Regex pattern to match against URL
            response: MockHTTPResponse to return

        Returns:
            Self for chaining
        """
        pattern = re.compile(url_pattern, re.IGNORECASE)

        if method.upper() == 'GET':
            self._get_responses.append((pattern, response))
        elif method.upper() == 'POST':
            self._post_responses.append((pattern, response))
        elif method.upper() == 'PATCH':
            self._patch_responses.append((pattern, response))

        return self

    def _find_response(
        self,
        responses: List[tuple],
        url: str
    ) -> MockHTTPResponse:
        """Find matching response for URL."""
        for pattern, response in responses:
            if pattern.search(url):
                return response
        return self._default_response

    def get(self, url: str, **kwargs) -> MockHTTPResponse:
        """Mock GET request."""
        self.get_calls.append({'url': url, 'kwargs': kwargs})
        return self._find_response(self._get_responses, url)

    def post(self, url: str, **kwargs) -> MockHTTPResponse:
        """Mock POST request."""
        self.post_calls.append({'url': url, 'kwargs': kwargs})
        return self._find_response(self._post_responses, url)

    def patch(self, url: str, **kwargs) -> MockHTTPResponse:
        """Mock PATCH request."""
        self.patch_calls.append({'url': url, 'kwargs': kwargs})
        return self._find_response(self._patch_responses, url)

    def set_default_response(self, response: MockHTTPResponse) -> None:
        """Set default response for unmatched URLs."""
        self._default_response = response

    def clear_calls(self) -> None:
        """Clear recorded calls."""
        self.get_calls.clear()
        self.post_calls.clear()
        self.patch_calls.clear()


# ==================== Factory Function ====================

def create_mock_provisioner(
    twilio_responses: Dict[str, MockHTTPResponse] = None,
    vapi_responses: Dict[str, MockHTTPResponse] = None,
    twilio_sid: str = 'ACtest123',
    twilio_token: str = 'test_token',
    vapi_key: str = 'test_vapi_key'
):
    """
    Create a TwilioVAPIProvisioner with mocked requests.

    Args:
        twilio_responses: Dict of response_type -> MockHTTPResponse for Twilio
            Keys: 'search', 'purchase', 'list', 'address_register', 'address_list', 'pricing'
        vapi_responses: Dict of response_type -> MockHTTPResponse for VAPI
            Keys: 'import', 'assign'
        twilio_sid: Mock Twilio account SID
        twilio_token: Mock Twilio auth token
        vapi_key: Mock VAPI API key

    Returns:
        Tuple of (provisioner, mock_session) where mock_session has call history

    Example:
        provisioner, session = create_mock_provisioner(
            twilio_responses={
                'search': TwilioResponseFactory.available_numbers([...]),
                'purchase': TwilioResponseFactory.purchase_success(...)
            },
            vapi_responses={
                'import': VAPIResponseFactory.import_success(...)
            }
        )

        # Use provisioner in tests
        result = provisioner.search_available_numbers('ZA')

        # Check what was called
        assert len(session.get_calls) == 1
    """
    from src.tools.twilio_vapi_provisioner import TwilioVAPIProvisioner

    session = MockRequestsSession()

    # Configure Twilio responses
    twilio_responses = twilio_responses or {}

    if 'search' in twilio_responses:
        session.add_response('GET', r'AvailablePhoneNumbers.*Local', twilio_responses['search'])

    if 'purchase' in twilio_responses:
        session.add_response('POST', r'IncomingPhoneNumbers\.json', twilio_responses['purchase'])

    if 'list' in twilio_responses:
        session.add_response('GET', r'IncomingPhoneNumbers\.json', twilio_responses['list'])

    if 'address_register' in twilio_responses:
        session.add_response('POST', r'Addresses\.json', twilio_responses['address_register'])

    if 'address_list' in twilio_responses:
        session.add_response('GET', r'Addresses\.json', twilio_responses['address_list'])

    if 'pricing' in twilio_responses:
        session.add_response('GET', r'AvailablePhoneNumbers/\w+\.json', twilio_responses['pricing'])

    # Configure VAPI responses
    vapi_responses = vapi_responses or {}

    if 'import' in vapi_responses:
        session.add_response('POST', r'api\.vapi\.ai/phone-number', vapi_responses['import'])

    if 'assign' in vapi_responses:
        session.add_response('PATCH', r'api\.vapi\.ai/phone-number', vapi_responses['assign'])

    # Create provisioner
    provisioner = TwilioVAPIProvisioner(twilio_sid, twilio_token, vapi_key)

    return provisioner, session


# ==================== Response Templates ====================

AVAILABLE_NUMBERS_ZA = generate_available_numbers(5, 'ZA')
AVAILABLE_NUMBERS_US = generate_available_numbers(5, 'US')

TWILIO_NUMBERS_LIST = [
    generate_twilio_number('+27123456789', 'PN001'),
    generate_twilio_number('+27123456790', 'PN002'),
    generate_twilio_number('+27123456791', 'PN003'),
]

ADDRESSES_LIST = [
    generate_address('AD001', 'ZA', 'Cape Town', 'Acme Travel'),
    generate_address('AD002', 'ZA', 'Johannesburg', 'Globe Tours'),
    generate_address('AD003', 'GB', 'London', 'UK Travel Ltd'),
]
