"""
Test Utilities

Helper functions and classes for testing:
- Mock factories
- Test data generators
- Assertion helpers
- Common test patterns

Usage:
    from tests.utils import MockFactory, generate_quote_data
"""

from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timedelta
import uuid
import random
import string


# ==================== Mock Factories ====================

class MockFactory:
    """Factory for creating various mock objects."""

    @staticmethod
    def create_supabase_response(data=None, error=None):
        """Create a mock Supabase response.

        Args:
            data: The data to return (list or dict)
            error: Optional error to include

        Returns:
            MagicMock: A mock Supabase response object
        """
        response = MagicMock()
        response.data = data if data is not None else []
        response.error = error
        return response

    @staticmethod
    def create_config(
        client_id='test_tenant',
        currency='USD',
        timezone='UTC',
        **kwargs
    ):
        """Create a mock ClientConfig.

        Args:
            client_id: Tenant identifier
            currency: Currency code
            timezone: Timezone string
            **kwargs: Additional attributes to set

        Returns:
            MagicMock: A mock config object
        """
        config = MagicMock()
        config.client_id = client_id
        config.currency = currency
        config.timezone = timezone
        config.supabase_url = kwargs.get('supabase_url', 'https://test.supabase.co')
        config.supabase_service_key = kwargs.get('supabase_service_key', 'test-key')
        config.supabase_anon_key = kwargs.get('supabase_anon_key', 'test-anon-key')
        config.company_name = kwargs.get('company_name', 'Test Company')
        config.company_email = kwargs.get('company_email', 'test@example.com')

        for key, value in kwargs.items():
            setattr(config, key, value)

        return config

    @staticmethod
    def create_user(
        user_id='user_123',
        email='test@example.com',
        role='admin',
        tenant_id='test_tenant',
        **kwargs
    ):
        """Create a mock user object.

        Args:
            user_id: User identifier
            email: User email
            role: User role (admin, user, etc.)
            tenant_id: Tenant identifier
            **kwargs: Additional attributes

        Returns:
            dict: A user dictionary
        """
        return {
            'id': user_id,
            'auth_user_id': f'auth_{user_id}',
            'email': email,
            'name': kwargs.get('name', 'Test User'),
            'role': role,
            'tenant_id': tenant_id,
            'is_active': kwargs.get('is_active', True),
            **kwargs
        }

    @staticmethod
    def create_chainable_mock():
        """Create a chainable mock for Supabase queries.

        Returns:
            MagicMock: A mock that returns itself for method chaining
        """
        mock = MagicMock()
        # Make all query builder methods return the mock itself
        for method in ['select', 'insert', 'update', 'delete', 'upsert',
                       'eq', 'neq', 'gt', 'gte', 'lt', 'lte', 'is_', 'in_',
                       'like', 'ilike', 'or_', 'order', 'limit', 'range',
                       'single', 'maybeSingle']:
            getattr(mock, method).return_value = mock
        return mock


# ==================== Data Generators ====================

def generate_id(prefix=''):
    """Generate a unique ID.

    Args:
        prefix: Optional prefix for the ID

    Returns:
        str: A unique ID string
    """
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    if prefix:
        return f"{prefix}-{datetime.now().strftime('%Y%m%d')}-{suffix}"
    return suffix


def generate_email(name=None):
    """Generate a random email address.

    Args:
        name: Optional name to use in the email

    Returns:
        str: An email address
    """
    if name:
        local_part = name.lower().replace(' ', '.')
    else:
        local_part = ''.join(random.choices(string.ascii_lowercase, k=8))
    return f"{local_part}@example.com"


def generate_quote_data(
    tenant_id='test_tenant',
    customer_name=None,
    customer_email=None,
    destination=None,
    **kwargs
):
    """Generate sample quote data.

    Args:
        tenant_id: Tenant identifier
        customer_name: Customer name
        customer_email: Customer email
        destination: Travel destination
        **kwargs: Additional quote fields

    Returns:
        dict: Quote data dictionary
    """
    customer_name = customer_name or f"Customer {generate_id()[:4]}"
    customer_email = customer_email or generate_email(customer_name)
    destinations = ['Cape Town', 'Kruger Park', 'Victoria Falls', 'Zanzibar']

    start_date = datetime.now() + timedelta(days=random.randint(30, 180))
    end_date = start_date + timedelta(days=random.randint(3, 14))

    return {
        'quote_id': generate_id('QT'),
        'tenant_id': tenant_id,
        'customer_name': customer_name,
        'customer_email': customer_email,
        'destination': destination or random.choice(destinations),
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'guests': kwargs.get('guests', random.randint(1, 6)),
        'total_amount': kwargs.get('total_amount', random.randint(1000, 10000)),
        'currency': kwargs.get('currency', 'USD'),
        'status': kwargs.get('status', 'draft'),
        'items': kwargs.get('items', [
            {'description': 'Accommodation', 'amount': random.randint(500, 3000)},
            {'description': 'Activities', 'amount': random.randint(200, 1000)},
        ]),
        'created_at': datetime.now().isoformat(),
        **{k: v for k, v in kwargs.items() if k not in ['guests', 'total_amount', 'currency', 'status', 'items']}
    }


def generate_invoice_data(
    tenant_id='test_tenant',
    customer_name=None,
    customer_email=None,
    **kwargs
):
    """Generate sample invoice data.

    Args:
        tenant_id: Tenant identifier
        customer_name: Customer name
        customer_email: Customer email
        **kwargs: Additional invoice fields

    Returns:
        dict: Invoice data dictionary
    """
    customer_name = customer_name or f"Customer {generate_id()[:4]}"
    customer_email = customer_email or generate_email(customer_name)

    total_amount = kwargs.get('total_amount', random.randint(500, 5000))

    return {
        'invoice_id': generate_id('INV'),
        'tenant_id': tenant_id,
        'customer_name': customer_name,
        'customer_email': customer_email,
        'total_amount': total_amount,
        'currency': kwargs.get('currency', 'USD'),
        'status': kwargs.get('status', 'draft'),
        'due_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
        'items': kwargs.get('items', [
            {'description': 'Service', 'amount': total_amount}
        ]),
        'created_at': datetime.now().isoformat(),
        **{k: v for k, v in kwargs.items() if k not in ['total_amount', 'currency', 'status', 'items']}
    }


def generate_client_data(
    tenant_id='test_tenant',
    name=None,
    email=None,
    **kwargs
):
    """Generate sample CRM client data.

    Args:
        tenant_id: Tenant identifier
        name: Client name
        email: Client email
        **kwargs: Additional client fields

    Returns:
        dict: Client data dictionary
    """
    name = name or f"Client {generate_id()[:4]}"
    email = email or generate_email(name)
    stages = ['QUOTED', 'NEGOTIATING', 'BOOKED', 'PAID', 'TRAVELLED', 'LOST']
    sources = ['website', 'email', 'referral', 'social']

    return {
        'client_id': generate_id('CL'),
        'tenant_id': tenant_id,
        'name': name,
        'email': email,
        'phone': kwargs.get('phone', f"+{random.randint(10000000000, 99999999999)}"),
        'pipeline_stage': kwargs.get('pipeline_stage', random.choice(stages[:4])),
        'source': kwargs.get('source', random.choice(sources)),
        'created_at': datetime.now().isoformat(),
        **{k: v for k, v in kwargs.items() if k not in ['phone', 'pipeline_stage', 'source']}
    }


def generate_ticket_data(
    tenant_id='test_tenant',
    customer_name=None,
    customer_email=None,
    **kwargs
):
    """Generate sample helpdesk ticket data.

    Args:
        tenant_id: Tenant identifier
        customer_name: Customer name
        customer_email: Customer email
        **kwargs: Additional ticket fields

    Returns:
        dict: Ticket data dictionary
    """
    customer_name = customer_name or f"Customer {generate_id()[:4]}"
    customer_email = customer_email or generate_email(customer_name)
    subjects = [
        'Question about booking',
        'Need to modify reservation',
        'Payment inquiry',
        'Request for information'
    ]
    priorities = ['low', 'normal', 'high', 'urgent']

    return {
        'ticket_id': generate_id('TKT'),
        'tenant_id': tenant_id,
        'customer_name': customer_name,
        'customer_email': customer_email,
        'subject': kwargs.get('subject', random.choice(subjects)),
        'message': kwargs.get('message', 'This is a test message.'),
        'status': kwargs.get('status', 'open'),
        'priority': kwargs.get('priority', random.choice(priorities[:3])),
        'created_at': datetime.now().isoformat(),
        **{k: v for k, v in kwargs.items() if k not in ['subject', 'message', 'status', 'priority']}
    }


# ==================== Assertion Helpers ====================

def assert_success_response(response, expected_status=200):
    """Assert that a response indicates success.

    Args:
        response: The HTTP response object
        expected_status: Expected HTTP status code

    Raises:
        AssertionError: If response doesn't indicate success
    """
    assert response.status_code == expected_status, \
        f"Expected {expected_status}, got {response.status_code}: {response.text}"

    if response.headers.get('content-type', '').startswith('application/json'):
        data = response.json()
        assert data.get('success', True) is True, \
            f"Expected success=True, got: {data}"


def assert_error_response(response, expected_status, expected_detail=None):
    """Assert that a response indicates an error.

    Args:
        response: The HTTP response object
        expected_status: Expected HTTP status code
        expected_detail: Optional expected detail message

    Raises:
        AssertionError: If response doesn't match expected error
    """
    assert response.status_code == expected_status, \
        f"Expected {expected_status}, got {response.status_code}: {response.text}"

    if expected_detail:
        data = response.json()
        assert expected_detail in str(data.get('detail', '')), \
            f"Expected '{expected_detail}' in detail, got: {data}"


def assert_list_response(response, min_length=0, max_length=None):
    """Assert that a response contains a list of items.

    Args:
        response: The HTTP response object
        min_length: Minimum expected list length
        max_length: Maximum expected list length

    Raises:
        AssertionError: If response doesn't contain expected list
    """
    assert_success_response(response)
    data = response.json()

    items = data.get('data', data.get('items', []))
    assert isinstance(items, list), f"Expected list, got {type(items)}"

    if min_length > 0:
        assert len(items) >= min_length, \
            f"Expected at least {min_length} items, got {len(items)}"

    if max_length is not None:
        assert len(items) <= max_length, \
            f"Expected at most {max_length} items, got {len(items)}"


# ==================== Context Managers ====================

class MockContext:
    """Context manager for common mocking patterns."""

    @staticmethod
    def authenticated_request(user=None, tenant_id='test_tenant'):
        """Create context for authenticated requests.

        Args:
            user: Optional user dict to use
            tenant_id: Tenant ID

        Returns:
            Context manager that patches auth
        """
        if user is None:
            user = MockFactory.create_user(tenant_id=tenant_id)

        return patch('src.middleware.auth_middleware.get_current_user',
                    return_value=user)

    @staticmethod
    def mocked_supabase():
        """Create context with mocked Supabase client.

        Returns:
            Context manager that patches Supabase
        """
        mock_client = MagicMock()
        mock_client.table.return_value = MockFactory.create_chainable_mock()

        return patch('src.tools.supabase_tool.get_cached_supabase_client',
                    return_value=mock_client)

    @staticmethod
    def mocked_config(config=None):
        """Create context with mocked config.

        Args:
            config: Optional config dict/mock

        Returns:
            Context manager that patches config loading
        """
        if config is None:
            config = MockFactory.create_config()

        return patch('src.api.routes.get_client_config',
                    return_value=config)


# ==================== Test Patterns ====================

def parametrize_auth_scenarios():
    """Return common auth test scenarios for parametrize.

    Returns:
        list: List of (headers, expected_status) tuples
    """
    return [
        ({}, 401),  # No auth
        ({'Authorization': 'Bearer invalid'}, 401),  # Invalid token
        ({'X-Client-ID': 'test'}, 401),  # Client ID without token
    ]


def parametrize_validation_scenarios(field_name, valid_value):
    """Return validation test scenarios for a field.

    Args:
        field_name: Name of the field to test
        valid_value: A valid value for the field

    Returns:
        list: List of (value, should_pass) tuples
    """
    return [
        (valid_value, True),
        ('', False),
        (None, False),
    ]


# ==================== Cleanup Utilities ====================

def clear_all_caches():
    """Clear all application caches.

    Call this in test cleanup to ensure isolation.
    """
    try:
        from src.services.auth_service import _user_cache
        _user_cache.clear()
    except ImportError:
        pass

    try:
        from src.services.tenant_config_service import TenantConfigService
        if hasattr(TenantConfigService, '_instance'):
            TenantConfigService._instance = None
    except ImportError:
        pass
