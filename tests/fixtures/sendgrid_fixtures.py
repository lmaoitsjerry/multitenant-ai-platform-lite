"""
SendGrid Mock Fixtures

Provides reusable mock infrastructure for SendGrid API testing:
- MockSendGridResponse: Simulates SendGrid API response objects
- MockSendGridClient: Simulates SendGrid API client with fluent interface
- Data generators: Factory functions for realistic test data
- API response templates: Pre-built JSON response structures

Usage:
    from tests.fixtures.sendgrid_fixtures import (
        create_mock_sendgrid_service,
        generate_subusers,
        MockSendGridClient,
    )

    # Create mocked service
    mock_service = create_mock_sendgrid_service(available=True)

    # Generate test data
    subusers = generate_subusers(n=5)
"""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from unittest.mock import MagicMock


class MockSendGridResponse:
    """
    Simulates SendGrid API response object.

    Attributes:
        status_code: HTTP status code (e.g., 200, 404)
        body: Response body as string (typically JSON)
    """

    def __init__(self, status_code: int, body: str):
        self.status_code = status_code
        self.body = body

    def __repr__(self):
        return f"MockSendGridResponse(status_code={self.status_code})"


class MockSendGridClientEndpoint:
    """
    Helper class for fluent interface method chaining.

    Supports patterns like:
        client.subusers._(username).stats.get(query_params={...})
    """

    def __init__(self, responses: Dict[str, MockSendGridResponse] = None):
        self._responses = responses or {}
        self._path = []

    def _(self, identifier: str) -> 'MockSendGridClientEndpoint':
        """Handle dynamic path segments like _(username)."""
        new_endpoint = MockSendGridClientEndpoint(self._responses)
        new_endpoint._path = self._path + [identifier]
        return new_endpoint

    def __getattr__(self, name: str) -> 'MockSendGridClientEndpoint':
        """Handle chained attribute access like .subusers.stats."""
        new_endpoint = MockSendGridClientEndpoint(self._responses)
        new_endpoint._path = self._path + [name]
        return new_endpoint

    def get(self, query_params: Dict = None) -> MockSendGridResponse:
        """Execute GET request and return mocked response."""
        path_key = '/'.join(self._path)
        if path_key in self._responses:
            return self._responses[path_key]
        # Default success response
        return MockSendGridResponse(200, '[]')

    def patch(self, request_body: Dict = None) -> MockSendGridResponse:
        """Execute PATCH request and return mocked response."""
        path_key = '/'.join(self._path)
        if path_key in self._responses:
            return self._responses[path_key]
        # Default success response for PATCH
        return MockSendGridResponse(204, '')

    def post(self, request_body: Dict = None) -> MockSendGridResponse:
        """Execute POST request and return mocked response."""
        path_key = '/'.join(self._path)
        if path_key in self._responses:
            return self._responses[path_key]
        # Default success response for POST
        return MockSendGridResponse(201, '{}')


class MockSendGridClient:
    """
    Simulates SendGrid API client with fluent interface.

    Supports:
        - client.subusers.get() - List subusers
        - client.subusers._(username).stats.get(query_params=...) - Get subuser stats
        - client.subusers._(username).patch(request_body=...) - Enable/disable subuser
        - client.stats.get(query_params=...) - Get global stats

    Example:
        mock_client = MockSendGridClient()
        mock_client.set_response('subusers', MockSendGridResponse(200, '[...]'))
        response = mock_client.client.subusers.get()
    """

    def __init__(self):
        self._responses: Dict[str, MockSendGridResponse] = {}
        self.client = MockSendGridClientEndpoint(self._responses)

    def set_response(self, path: str, response: MockSendGridResponse):
        """
        Set a canned response for a specific path.

        Args:
            path: API path like 'subusers' or 'subusers/testuser/stats'
            response: MockSendGridResponse to return
        """
        self._responses[path] = response
        # Update the endpoint responses
        self.client._responses = self._responses

    def set_subusers_response(self, subusers: List[Dict]):
        """Convenience method to set subusers list response."""
        self.set_response('subusers', MockSendGridResponse(200, json.dumps(subusers)))

    def set_subuser_stats_response(self, username: str, stats: List[Dict]):
        """Convenience method to set stats response for a specific subuser."""
        path = f'subusers/{username}/stats'
        self.set_response(path, MockSendGridResponse(200, json.dumps(stats)))

    def set_global_stats_response(self, stats: List[Dict]):
        """Convenience method to set global stats response."""
        self.set_response('stats', MockSendGridResponse(200, json.dumps(stats)))

    def set_subuser_patch_response(self, username: str, success: bool = True):
        """Convenience method to set patch response for enable/disable."""
        path = f'subusers/{username}'
        status = 204 if success else 400
        self.set_response(path, MockSendGridResponse(status, ''))


def generate_subusers(n: int = 3, prefix: str = 'tenant') -> List[Dict[str, Any]]:
    """
    Generate list of subuser dictionaries.

    Args:
        n: Number of subusers to generate
        prefix: Prefix for username (default: 'tenant')

    Returns:
        List of subuser dicts with username, email, disabled, id fields
    """
    return [
        {
            'username': f'{prefix}_{i}',
            'email': f'{prefix}{i}@example.com',
            'disabled': False,
            'id': i
        }
        for i in range(n)
    ]


def generate_subuser_stats(
    username: str,
    days: int = 30,
    base_requests: int = 100,
    variance: float = 0.3
) -> List[Dict[str, Any]]:
    """
    Generate daily stats response for a subuser.

    Args:
        username: Subuser username (for reference)
        days: Number of days of stats to generate
        base_requests: Base number of email requests per day
        variance: Variance in daily metrics (0-1)

    Returns:
        List of daily stat dictionaries matching SendGrid API format
    """
    import random

    stats = []
    base_date = datetime.now() - timedelta(days=days)

    for day in range(days):
        date = (base_date + timedelta(days=day)).strftime('%Y-%m-%d')

        # Generate metrics with some randomness
        requests = int(base_requests * (1 + random.uniform(-variance, variance)))
        delivered = int(requests * random.uniform(0.90, 0.98))
        opens = int(delivered * random.uniform(0.20, 0.40))
        unique_opens = int(opens * random.uniform(0.70, 0.90))
        clicks = int(opens * random.uniform(0.10, 0.30))
        unique_clicks = int(clicks * random.uniform(0.60, 0.80))
        bounces = requests - delivered
        spam_reports = int(delivered * random.uniform(0, 0.01))
        unsubscribes = int(delivered * random.uniform(0, 0.02))
        blocks = int(requests * random.uniform(0, 0.02))
        invalid_emails = int(requests * random.uniform(0, 0.01))

        stats.append({
            'date': date,
            'stats': [{
                'metrics': {
                    'requests': requests,
                    'delivered': delivered,
                    'opens': opens,
                    'unique_opens': unique_opens,
                    'clicks': clicks,
                    'unique_clicks': unique_clicks,
                    'bounces': bounces,
                    'spam_reports': spam_reports,
                    'unsubscribes': unsubscribes,
                    'blocks': blocks,
                    'invalid_emails': invalid_emails
                }
            }]
        })

    return stats


def generate_global_stats(
    days: int = 30,
    total_requests: int = 10000
) -> List[Dict[str, Any]]:
    """
    Generate platform-wide email statistics.

    Args:
        days: Number of days of stats to generate
        total_requests: Approximate total requests across all days

    Returns:
        List of daily stat dictionaries for global/aggregated stats
    """
    import random

    stats = []
    base_date = datetime.now() - timedelta(days=days)
    daily_requests = total_requests // days

    for day in range(days):
        date = (base_date + timedelta(days=day)).strftime('%Y-%m-%d')

        requests = int(daily_requests * random.uniform(0.8, 1.2))
        delivered = int(requests * random.uniform(0.92, 0.98))
        opens = int(delivered * random.uniform(0.25, 0.45))
        unique_opens = int(opens * random.uniform(0.65, 0.85))
        clicks = int(opens * random.uniform(0.15, 0.35))
        unique_clicks = int(clicks * random.uniform(0.55, 0.75))
        bounces = requests - delivered
        spam_reports = int(delivered * random.uniform(0, 0.005))
        unsubscribes = int(delivered * random.uniform(0, 0.01))
        blocks = int(requests * random.uniform(0, 0.015))

        stats.append({
            'date': date,
            'stats': [{
                'metrics': {
                    'requests': requests,
                    'delivered': delivered,
                    'opens': opens,
                    'unique_opens': unique_opens,
                    'clicks': clicks,
                    'unique_clicks': unique_clicks,
                    'bounces': bounces,
                    'spam_reports': spam_reports,
                    'unsubscribes': unsubscribes,
                    'blocks': blocks
                }
            }]
        })

    return stats


def create_mock_sendgrid_service(
    available: bool = True,
    subusers: List[Dict] = None,
    global_stats: Dict = None,
    subuser_stats: Dict = None
) -> MagicMock:
    """
    Create a configured SendGridAdminService mock.

    Args:
        available: Whether the service should report as available
        subusers: List of subusers to return from list_subusers()
        global_stats: Dict to return from get_global_stats()
        subuser_stats: Dict to return from get_subuser_stats()

    Returns:
        MagicMock configured to behave like SendGridAdminService
    """
    mock_service = MagicMock()
    mock_service.is_available.return_value = available

    if subusers is not None:
        mock_service.list_subusers.return_value = subusers
    else:
        mock_service.list_subusers.return_value = []

    if global_stats is not None:
        mock_service.get_global_stats.return_value = global_stats
    else:
        mock_service.get_global_stats.return_value = {
            'period_days': 30,
            'totals': {
                'requests': 0,
                'delivered': 0,
                'opens': 0,
                'bounces': 0,
                'open_rate': 0,
                'delivery_rate': 0
            }
        }

    if subuser_stats is not None:
        mock_service.get_subuser_stats.return_value = subuser_stats
    else:
        mock_service.get_subuser_stats.return_value = {'error': 'No mock configured'}

    # Default enable/disable behavior
    mock_service.disable_subuser.return_value = True
    mock_service.enable_subuser.return_value = True

    return mock_service


# ==================== API Response Templates ====================

SUBUSER_LIST_RESPONSE = [
    {
        'username': 'tenant_acme',
        'email': 'acme@travel.com',
        'disabled': False,
        'id': 1001
    },
    {
        'username': 'tenant_globex',
        'email': 'globex@travel.com',
        'disabled': False,
        'id': 1002
    },
    {
        'username': 'tenant_inactive',
        'email': 'inactive@travel.com',
        'disabled': True,
        'id': 1003
    }
]

SUBUSER_STATS_RESPONSE = [
    {
        'date': '2026-01-01',
        'stats': [{
            'metrics': {
                'requests': 150,
                'delivered': 145,
                'opens': 50,
                'unique_opens': 40,
                'clicks': 15,
                'unique_clicks': 12,
                'bounces': 5,
                'spam_reports': 0,
                'unsubscribes': 1,
                'blocks': 0,
                'invalid_emails': 0
            }
        }]
    },
    {
        'date': '2026-01-02',
        'stats': [{
            'metrics': {
                'requests': 200,
                'delivered': 195,
                'opens': 80,
                'unique_opens': 65,
                'clicks': 25,
                'unique_clicks': 20,
                'bounces': 3,
                'spam_reports': 1,
                'unsubscribes': 0,
                'blocks': 2,
                'invalid_emails': 0
            }
        }]
    }
]

GLOBAL_STATS_RESPONSE = [
    {
        'date': '2026-01-01',
        'stats': [{
            'metrics': {
                'requests': 5000,
                'delivered': 4850,
                'opens': 2000,
                'unique_opens': 1500,
                'clicks': 500,
                'unique_clicks': 400,
                'bounces': 100,
                'spam_reports': 5,
                'unsubscribes': 20,
                'blocks': 50
            }
        }]
    },
    {
        'date': '2026-01-02',
        'stats': [{
            'metrics': {
                'requests': 5500,
                'delivered': 5350,
                'opens': 2200,
                'unique_opens': 1700,
                'clicks': 550,
                'unique_clicks': 450,
                'bounces': 80,
                'spam_reports': 3,
                'unsubscribes': 15,
                'blocks': 70
            }
        }]
    }
]
