"""
Tests for Twilio VAPI Provisioner

Comprehensive test coverage for src/tools/twilio_vapi_provisioner.py:
- Initialization and credential handling
- Twilio operations (search, buy, list numbers)
- VAPI operations (import, assign)
- Combined provisioning workflow
- Address management for regulatory compliance
- Helper functions
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from base64 import b64encode

from tests.fixtures.twilio_vapi_fixtures import (
    MockHTTPResponse,
    TwilioResponseFactory,
    VAPIResponseFactory,
    MockRequestsSession,
    generate_available_numbers,
    generate_twilio_number,
    generate_address,
)


# ==================== Initialization Tests ====================

class TestTwilioVAPIProvisionerInit:
    """Tests for TwilioVAPIProvisioner initialization"""

    def test_init_with_credentials(self):
        """Test initialization with valid credentials"""
        from src.tools.twilio_vapi_provisioner import TwilioVAPIProvisioner

        provisioner = TwilioVAPIProvisioner(
            twilio_account_sid='ACtest123',
            twilio_auth_token='test_token',
            vapi_api_key='vapi_key'
        )

        assert provisioner.twilio_sid == 'ACtest123'
        assert provisioner.twilio_token == 'test_token'
        assert provisioner.vapi_key == 'vapi_key'

    def test_twilio_auth_header_created(self):
        """Test that Basic auth header is base64 encoded"""
        from src.tools.twilio_vapi_provisioner import TwilioVAPIProvisioner

        provisioner = TwilioVAPIProvisioner(
            twilio_account_sid='ACtest123',
            twilio_auth_token='test_token',
            vapi_api_key='vapi_key'
        )

        expected = b64encode(b'ACtest123:test_token').decode()
        assert provisioner.twilio_auth == expected

    def test_twilio_headers(self):
        """Test Twilio headers include auth and content-type"""
        from src.tools.twilio_vapi_provisioner import TwilioVAPIProvisioner

        provisioner = TwilioVAPIProvisioner(
            twilio_account_sid='ACtest123',
            twilio_auth_token='test_token',
            vapi_api_key='vapi_key'
        )

        headers = provisioner._twilio_headers()

        assert 'Authorization' in headers
        assert headers['Authorization'].startswith('Basic ')
        assert headers['Content-Type'] == 'application/x-www-form-urlencoded'

    def test_vapi_headers(self):
        """Test VAPI headers include Bearer token and content-type"""
        from src.tools.twilio_vapi_provisioner import TwilioVAPIProvisioner

        provisioner = TwilioVAPIProvisioner(
            twilio_account_sid='ACtest123',
            twilio_auth_token='test_token',
            vapi_api_key='vapi_key'
        )

        headers = provisioner._vapi_headers()

        assert headers['Authorization'] == 'Bearer vapi_key'
        assert headers['Content-Type'] == 'application/json'

    def test_country_codes_mapping(self):
        """Test COUNTRY_CODES dict has expected entries"""
        from src.tools.twilio_vapi_provisioner import TwilioVAPIProvisioner

        # Check expected country codes exist
        assert 'ZA' in TwilioVAPIProvisioner.COUNTRY_CODES
        assert 'US' in TwilioVAPIProvisioner.COUNTRY_CODES
        assert 'UK' in TwilioVAPIProvisioner.COUNTRY_CODES
        assert TwilioVAPIProvisioner.COUNTRY_CODES['UK'] == 'GB'


# ==================== Search Available Numbers Tests ====================

class TestSearchAvailableNumbers:
    """Tests for search_available_numbers method"""

    @pytest.fixture
    def provisioner(self):
        """Create provisioner for tests"""
        from src.tools.twilio_vapi_provisioner import TwilioVAPIProvisioner
        return TwilioVAPIProvisioner('ACtest', 'token', 'vapi_key')

    def test_search_numbers_success(self, provisioner):
        """Test successful number search returns formatted list"""
        numbers = generate_available_numbers(3, 'ZA')
        mock_response = TwilioResponseFactory.available_numbers(numbers)

        with patch('requests.get', return_value=mock_response):
            result = provisioner.search_available_numbers(country_code='ZA')

        assert len(result) == 3
        assert 'number' in result[0]
        assert 'locality' in result[0]
        assert 'capabilities' in result[0]

    def test_search_numbers_with_area_code(self, provisioner):
        """Test area code parameter is passed correctly"""
        numbers = generate_available_numbers(2, 'ZA', area_code='21')
        mock_response = TwilioResponseFactory.available_numbers(numbers)

        with patch('requests.get', return_value=mock_response) as mock_get:
            provisioner.search_available_numbers(country_code='ZA', area_code='21')

            # Verify area code was in params
            call_kwargs = mock_get.call_args
            assert call_kwargs.kwargs['params']['AreaCode'] == '21'

    def test_search_numbers_with_contains(self, provisioner):
        """Test contains parameter is passed correctly"""
        mock_response = TwilioResponseFactory.available_numbers([])

        with patch('requests.get', return_value=mock_response) as mock_get:
            provisioner.search_available_numbers(country_code='ZA', contains='777')

            call_kwargs = mock_get.call_args
            assert call_kwargs.kwargs['params']['Contains'] == '777'

    def test_search_numbers_empty_result(self, provisioner):
        """Test empty result when no numbers available"""
        mock_response = TwilioResponseFactory.available_numbers([])

        with patch('requests.get', return_value=mock_response):
            result = provisioner.search_available_numbers(country_code='ZA')

        assert result == []

    def test_search_numbers_api_error(self, provisioner):
        """Test returns empty list on API error"""
        mock_response = MockHTTPResponse(500, {'error': 'Server error'})

        with patch('requests.get', return_value=mock_response):
            result = provisioner.search_available_numbers(country_code='ZA')

        assert result == []

    def test_search_numbers_timeout(self, provisioner):
        """Test handles timeout gracefully"""
        import requests

        with patch('requests.get', side_effect=requests.Timeout('Connection timed out')):
            result = provisioner.search_available_numbers(country_code='ZA')

        assert result == []


# ==================== Buy Twilio Number Tests ====================

class TestBuyTwilioNumber:
    """Tests for buy_twilio_number method"""

    @pytest.fixture
    def provisioner(self):
        from src.tools.twilio_vapi_provisioner import TwilioVAPIProvisioner
        return TwilioVAPIProvisioner('ACtest', 'token', 'vapi_key')

    def test_buy_number_success(self, provisioner):
        """Test successful number purchase returns SID"""
        mock_response = TwilioResponseFactory.purchase_success('+27123456789', 'PN123')

        with patch('requests.post', return_value=mock_response):
            result = provisioner.buy_twilio_number('+27123456789')

        assert result['success'] is True
        assert result['sid'] == 'PN123'
        assert result['phone_number'] == '+27123456789'

    def test_buy_number_failure(self, provisioner):
        """Test returns error on API failure"""
        mock_response = TwilioResponseFactory.purchase_error('Number not available')

        with patch('requests.post', return_value=mock_response):
            result = provisioner.buy_twilio_number('+27123456789')

        assert result['success'] is False
        assert 'error' in result

    def test_buy_number_exception(self, provisioner):
        """Test handles exceptions gracefully"""
        with patch('requests.post', side_effect=Exception('Network error')):
            result = provisioner.buy_twilio_number('+27123456789')

        assert result['success'] is False
        assert 'Network error' in result['error']


# ==================== List Twilio Numbers Tests ====================

class TestListTwilioNumbers:
    """Tests for list_twilio_numbers method"""

    @pytest.fixture
    def provisioner(self):
        from src.tools.twilio_vapi_provisioner import TwilioVAPIProvisioner
        return TwilioVAPIProvisioner('ACtest', 'token', 'vapi_key')

    def test_list_numbers_success(self, provisioner):
        """Test successful listing returns formatted numbers"""
        numbers = [
            generate_twilio_number('+27123456789', 'PN001'),
            generate_twilio_number('+27123456790', 'PN002'),
        ]
        mock_response = TwilioResponseFactory.list_numbers(numbers)

        with patch('requests.get', return_value=mock_response):
            result = provisioner.list_twilio_numbers()

        assert len(result) == 2
        assert result[0]['sid'] == 'PN001'
        assert result[1]['number'] == '+27123456790'

    def test_list_numbers_empty(self, provisioner):
        """Test empty list when no numbers in account"""
        mock_response = TwilioResponseFactory.list_numbers([])

        with patch('requests.get', return_value=mock_response):
            result = provisioner.list_twilio_numbers()

        assert result == []

    def test_list_numbers_error(self, provisioner):
        """Test returns empty list on API error"""
        mock_response = MockHTTPResponse(500, {'error': 'Server error'})

        with patch('requests.get', return_value=mock_response):
            result = provisioner.list_twilio_numbers()

        assert result == []


# ==================== Import to VAPI Tests ====================

class TestImportToVAPI:
    """Tests for import_to_vapi method"""

    @pytest.fixture
    def provisioner(self):
        from src.tools.twilio_vapi_provisioner import TwilioVAPIProvisioner
        return TwilioVAPIProvisioner('ACtest', 'token', 'vapi_key')

    def test_import_success(self, provisioner):
        """Test successful import returns VAPI ID"""
        mock_response = VAPIResponseFactory.import_success('vapi_123', '+27123456789')

        with patch('requests.post', return_value=mock_response):
            result = provisioner.import_to_vapi('+27123456789')

        assert result['success'] is True
        assert result['vapi_id'] == 'vapi_123'

    def test_import_with_assistant(self, provisioner):
        """Test import includes assistantId in payload"""
        mock_response = VAPIResponseFactory.import_success('vapi_123', '+27123456789', 'ast_456')

        with patch('requests.post', return_value=mock_response) as mock_post:
            provisioner.import_to_vapi('+27123456789', assistant_id='ast_456')

            call_kwargs = mock_post.call_args
            payload = call_kwargs.kwargs['json']
            assert payload['assistantId'] == 'ast_456'

    def test_import_with_client_id(self, provisioner):
        """Test import includes serverUrl for webhook routing"""
        mock_response = VAPIResponseFactory.import_success('vapi_123', '+27123456789')

        with patch('requests.post', return_value=mock_response) as mock_post:
            provisioner.import_to_vapi('+27123456789', client_id='tenant_abc')

            call_kwargs = mock_post.call_args
            payload = call_kwargs.kwargs['json']
            assert 'serverUrl' in payload
            assert 'tenant_abc' in payload['serverUrl']

    def test_import_with_name(self, provisioner):
        """Test import includes name in payload"""
        mock_response = VAPIResponseFactory.import_success('vapi_123', '+27123456789')

        with patch('requests.post', return_value=mock_response) as mock_post:
            provisioner.import_to_vapi('+27123456789', name='Acme Inbound')

            call_kwargs = mock_post.call_args
            payload = call_kwargs.kwargs['json']
            assert payload['name'] == 'Acme Inbound'

    def test_import_failure(self, provisioner):
        """Test returns error on API failure"""
        mock_response = VAPIResponseFactory.import_error('Invalid number format')

        with patch('requests.post', return_value=mock_response):
            result = provisioner.import_to_vapi('+27123456789')

        assert result['success'] is False
        assert 'error' in result

    def test_import_exception(self, provisioner):
        """Test handles exceptions gracefully"""
        with patch('requests.post', side_effect=Exception('Connection refused')):
            result = provisioner.import_to_vapi('+27123456789')

        assert result['success'] is False
        assert 'Connection refused' in result['error']


# ==================== Assign VAPI Assistant Tests ====================

class TestAssignVAPIAssistant:
    """Tests for assign_vapi_assistant method"""

    @pytest.fixture
    def provisioner(self):
        from src.tools.twilio_vapi_provisioner import TwilioVAPIProvisioner
        return TwilioVAPIProvisioner('ACtest', 'token', 'vapi_key')

    def test_assign_success(self, provisioner):
        """Test successful assignment returns data"""
        data = {'id': 'vapi_123', 'assistantId': 'ast_456'}
        mock_response = VAPIResponseFactory.assign_success(data)

        with patch('requests.patch', return_value=mock_response):
            result = provisioner.assign_vapi_assistant('vapi_123', 'ast_456')

        assert result['success'] is True
        assert result['data']['assistantId'] == 'ast_456'

    def test_assign_with_server_url(self, provisioner):
        """Test assignment includes serverUrl for client routing"""
        mock_response = VAPIResponseFactory.assign_success({'id': 'vapi_123'})

        with patch('requests.patch', return_value=mock_response) as mock_patch:
            provisioner.assign_vapi_assistant('vapi_123', 'ast_456', client_id='tenant_abc')

            call_kwargs = mock_patch.call_args
            payload = call_kwargs.kwargs['json']
            assert 'serverUrl' in payload
            assert 'tenant_abc' in payload['serverUrl']

    def test_assign_failure(self, provisioner):
        """Test returns error on API failure"""
        mock_response = VAPIResponseFactory.assign_error('Invalid phone ID')

        with patch('requests.patch', return_value=mock_response):
            result = provisioner.assign_vapi_assistant('vapi_123', 'ast_456')

        assert result['success'] is False


# ==================== Provision Phone For Tenant Tests ====================

class TestProvisionPhoneForTenant:
    """Tests for provision_phone_for_tenant workflow"""

    @pytest.fixture
    def provisioner(self):
        from src.tools.twilio_vapi_provisioner import TwilioVAPIProvisioner
        return TwilioVAPIProvisioner('ACtest', 'token', 'vapi_key')

    def test_provision_full_workflow_success(self, provisioner):
        """Test complete provisioning flow: search -> buy -> import"""
        numbers = generate_available_numbers(3, 'ZA')
        search_response = TwilioResponseFactory.available_numbers(numbers)
        purchase_response = TwilioResponseFactory.purchase_success(numbers[0]['phone_number'], 'PN123')
        import_response = VAPIResponseFactory.import_success('vapi_123', numbers[0]['phone_number'])

        with patch('requests.get', return_value=search_response):
            with patch('requests.post', side_effect=[purchase_response, import_response]):
                result = provisioner.provision_phone_for_tenant(
                    country_code='ZA',
                    client_id='tenant_abc',
                    assistant_id='ast_456'
                )

        assert result['success'] is True
        assert result['twilio_sid'] == 'PN123'
        assert result['vapi_id'] == 'vapi_123'
        assert 'search' in result['steps']
        assert 'purchase' in result['steps']
        assert 'import' in result['steps']

    def test_provision_no_numbers_available(self, provisioner):
        """Test fails at search step when no numbers available"""
        search_response = TwilioResponseFactory.available_numbers([])

        with patch('requests.get', return_value=search_response):
            result = provisioner.provision_phone_for_tenant(
                country_code='ZA',
                client_id='tenant_abc',
                assistant_id='ast_456'
            )

        assert result['success'] is False
        assert 'No numbers available' in result['error']

    def test_provision_purchase_fails(self, provisioner):
        """Test fails at purchase step"""
        numbers = generate_available_numbers(1, 'ZA')
        search_response = TwilioResponseFactory.available_numbers(numbers)
        purchase_response = TwilioResponseFactory.purchase_error('Insufficient funds')

        with patch('requests.get', return_value=search_response):
            with patch('requests.post', return_value=purchase_response):
                result = provisioner.provision_phone_for_tenant(
                    country_code='ZA',
                    client_id='tenant_abc',
                    assistant_id='ast_456'
                )

        assert result['success'] is False
        assert 'purchase failed' in result['error'].lower()
        assert 'search' in result['steps']
        assert 'purchase' not in result['steps']

    def test_provision_import_fails(self, provisioner):
        """Test fails at import step (number purchased but not in VAPI)"""
        numbers = generate_available_numbers(1, 'ZA')
        search_response = TwilioResponseFactory.available_numbers(numbers)
        purchase_response = TwilioResponseFactory.purchase_success(numbers[0]['phone_number'], 'PN123')
        import_response = VAPIResponseFactory.import_error('VAPI error')

        with patch('requests.get', return_value=search_response):
            with patch('requests.post', side_effect=[purchase_response, import_response]):
                result = provisioner.provision_phone_for_tenant(
                    country_code='ZA',
                    client_id='tenant_abc',
                    assistant_id='ast_456'
                )

        assert result['success'] is False
        assert result['twilio_sid'] == 'PN123'  # Number was purchased
        assert result['vapi_id'] is None
        assert 'import' in result['steps'] or 'purchase' in result['steps']

    def test_provision_tracks_steps(self, provisioner):
        """Test steps list shows completed steps"""
        numbers = generate_available_numbers(1, 'ZA')
        search_response = TwilioResponseFactory.available_numbers(numbers)
        purchase_response = TwilioResponseFactory.purchase_success(numbers[0]['phone_number'], 'PN123')
        import_response = VAPIResponseFactory.import_success('vapi_123', numbers[0]['phone_number'])

        with patch('requests.get', return_value=search_response):
            with patch('requests.post', side_effect=[purchase_response, import_response]):
                result = provisioner.provision_phone_for_tenant(
                    country_code='ZA',
                    client_id='tenant_abc',
                    assistant_id='ast_456'
                )

        assert len(result['steps']) == 3
        assert result['steps'] == ['search', 'purchase', 'import']


# ==================== Address Management Tests ====================

class TestAddressManagement:
    """Tests for address registration and listing"""

    @pytest.fixture
    def provisioner(self):
        from src.tools.twilio_vapi_provisioner import TwilioVAPIProvisioner
        return TwilioVAPIProvisioner('ACtest', 'token', 'vapi_key')

    def test_register_address_success(self, provisioner):
        """Test successful address registration returns SID"""
        mock_response = TwilioResponseFactory.register_address_success('AD123')

        with patch('requests.post', return_value=mock_response):
            result = provisioner.register_address(
                customer_name='Acme Travel',
                street='123 Main St',
                city='Cape Town',
                region='Western Cape',
                postal_code='8001',
                country_code='ZA'
            )

        assert result['success'] is True
        assert result['address_sid'] == 'AD123'

    def test_register_address_failure(self, provisioner):
        """Test returns error on API failure"""
        mock_response = TwilioResponseFactory.register_address_error('Invalid address')

        with patch('requests.post', return_value=mock_response):
            result = provisioner.register_address(
                customer_name='Test',
                street='Invalid',
                city='Nowhere',
                region='NA',
                postal_code='00000',
                country_code='ZA'
            )

        assert result['success'] is False
        assert 'error' in result

    def test_register_address_exception(self, provisioner):
        """Test handles exceptions gracefully"""
        with patch('requests.post', side_effect=Exception('Network error')):
            result = provisioner.register_address(
                customer_name='Test',
                street='123 Main',
                city='Test City',
                region='Test',
                postal_code='12345',
                country_code='ZA'
            )

        assert result['success'] is False

    def test_list_addresses_success(self, provisioner):
        """Test successful listing returns formatted addresses"""
        addresses = [
            generate_address('AD001', 'ZA', 'Cape Town'),
            generate_address('AD002', 'ZA', 'Johannesburg'),
        ]
        mock_response = TwilioResponseFactory.list_addresses(addresses)

        with patch('requests.get', return_value=mock_response):
            result = provisioner.list_addresses()

        assert len(result) == 2
        assert result[0]['sid'] == 'AD001'
        assert result[1]['city'] == 'Johannesburg'

    def test_list_addresses_empty(self, provisioner):
        """Test returns empty list when no addresses"""
        mock_response = TwilioResponseFactory.list_addresses([])

        with patch('requests.get', return_value=mock_response):
            result = provisioner.list_addresses()

        assert result == []

    def test_get_address_for_country(self, provisioner):
        """Test finds address by country code"""
        addresses = [
            generate_address('AD001', 'ZA', 'Cape Town'),
            generate_address('AD002', 'GB', 'London'),
        ]
        mock_response = TwilioResponseFactory.list_addresses(addresses)

        with patch('requests.get', return_value=mock_response):
            result = provisioner.get_address_for_country('ZA')

        assert result == 'AD001'

    def test_get_address_for_country_not_found(self, provisioner):
        """Test returns None when no match"""
        addresses = [generate_address('AD001', 'ZA', 'Cape Town')]
        mock_response = TwilioResponseFactory.list_addresses(addresses)

        with patch('requests.get', return_value=mock_response):
            result = provisioner.get_address_for_country('US')

        assert result is None


# ==================== Buy With Address Tests ====================

class TestBuyWithAddress:
    """Tests for buy_twilio_number_with_address method"""

    @pytest.fixture
    def provisioner(self):
        from src.tools.twilio_vapi_provisioner import TwilioVAPIProvisioner
        return TwilioVAPIProvisioner('ACtest', 'token', 'vapi_key')

    def test_buy_with_address_success(self, provisioner):
        """Test includes AddressSid in purchase"""
        mock_response = TwilioResponseFactory.purchase_success('+27123456789', 'PN123')

        with patch('requests.post', return_value=mock_response) as mock_post:
            result = provisioner.buy_twilio_number_with_address('+27123456789', 'AD001')

            call_kwargs = mock_post.call_args
            data = call_kwargs.kwargs['data']
            assert data['AddressSid'] == 'AD001'

        assert result['success'] is True
        assert result['sid'] == 'PN123'

    def test_buy_with_address_failure(self, provisioner):
        """Test returns error on API failure"""
        mock_response = TwilioResponseFactory.purchase_error('Invalid address')

        with patch('requests.post', return_value=mock_response):
            result = provisioner.buy_twilio_number_with_address('+27123456789', 'AD001')

        assert result['success'] is False

    def test_buy_with_address_exception(self, provisioner):
        """Test handles exceptions gracefully"""
        with patch('requests.post', side_effect=Exception('Network error')):
            result = provisioner.buy_twilio_number_with_address('+27123456789', 'AD001')

        assert result['success'] is False


# ==================== Client Phone Onboarding Tests ====================

class TestClientPhoneOnboarding:
    """Tests for ClientPhoneOnboarding helper class"""

    @pytest.fixture
    def provisioner(self):
        from src.tools.twilio_vapi_provisioner import TwilioVAPIProvisioner
        return TwilioVAPIProvisioner('ACtest', 'token', 'vapi_key')

    @pytest.fixture
    def onboarding(self, provisioner):
        from src.tools.twilio_vapi_provisioner import ClientPhoneOnboarding
        return ClientPhoneOnboarding(provisioner)

    def test_register_client_address(self, onboarding):
        """Test delegates to provisioner register_address"""
        mock_response = TwilioResponseFactory.register_address_success('AD123')

        with patch('requests.post', return_value=mock_response):
            result = onboarding.register_client_address(
                client_id='tenant_abc',
                company_name='Acme Travel',
                street='123 Main St',
                city='Cape Town',
                region='Western Cape',
                postal_code='8001',
                country_code='ZA'
            )

        assert result['success'] is True
        assert result['address_sid'] == 'AD123'

    def test_get_number_options(self, onboarding):
        """Test returns formatted options for UI"""
        numbers = generate_available_numbers(3, 'ZA')
        mock_response = TwilioResponseFactory.available_numbers(numbers)

        with patch('requests.get', return_value=mock_response):
            result = onboarding.get_number_options(country_code='ZA')

        assert len(result) == 3
        assert 'number' in result[0]
        assert 'display' in result[0]
        assert 'capabilities' in result[0]

    def test_complete_phone_setup(self, onboarding):
        """Test delegates to provision_with_client_selection"""
        # Need to mock address lookup and purchase/import
        addresses = [generate_address('AD001', 'ZA', 'Cape Town')]
        address_response = TwilioResponseFactory.list_addresses(addresses)
        purchase_response = TwilioResponseFactory.purchase_success('+27123456789', 'PN123')
        import_response = VAPIResponseFactory.import_success('vapi_123', '+27123456789')

        with patch('requests.get', return_value=address_response):
            with patch('requests.post', side_effect=[purchase_response, import_response]):
                result = onboarding.complete_phone_setup(
                    client_id='tenant_abc',
                    assistant_id='ast_456',
                    selected_number='+27123456789',
                    country_code='ZA'
                )

        assert result['success'] is True


# ==================== Provision With Client Selection Tests ====================

class TestProvisionWithClientSelection:
    """Tests for provision_with_client_selection method"""

    @pytest.fixture
    def provisioner(self):
        from src.tools.twilio_vapi_provisioner import TwilioVAPIProvisioner
        return TwilioVAPIProvisioner('ACtest', 'token', 'vapi_key')

    def test_provision_with_address_sid(self, provisioner):
        """Test uses provided address_sid directly"""
        purchase_response = TwilioResponseFactory.purchase_success('+27123456789', 'PN123')
        import_response = VAPIResponseFactory.import_success('vapi_123', '+27123456789')

        with patch('requests.post', side_effect=[purchase_response, import_response]):
            result = provisioner.provision_with_client_selection(
                client_id='tenant_abc',
                assistant_id='ast_456',
                selected_number='+27123456789',
                address_sid='AD001'
            )

        assert result['success'] is True
        assert result['twilio_sid'] == 'PN123'
        assert result['vapi_id'] == 'vapi_123'

    def test_provision_without_address_finds_one(self, provisioner):
        """Test looks up address if not provided"""
        addresses = [generate_address('AD001', 'ZA', 'Cape Town')]
        address_response = TwilioResponseFactory.list_addresses(addresses)
        purchase_response = TwilioResponseFactory.purchase_success('+27123456789', 'PN123')
        import_response = VAPIResponseFactory.import_success('vapi_123', '+27123456789')

        with patch('requests.get', return_value=address_response):
            with patch('requests.post', side_effect=[purchase_response, import_response]):
                result = provisioner.provision_with_client_selection(
                    client_id='tenant_abc',
                    assistant_id='ast_456',
                    selected_number='+27123456789',
                    country_code='ZA'
                )

        assert result['success'] is True

    def test_provision_no_address_available(self, provisioner):
        """Test fails if no address registered for country"""
        address_response = TwilioResponseFactory.list_addresses([])

        with patch('requests.get', return_value=address_response):
            result = provisioner.provision_with_client_selection(
                client_id='tenant_abc',
                assistant_id='ast_456',
                selected_number='+27123456789',
                country_code='ZA'
            )

        assert result['success'] is False
        assert 'No registered address' in result['error']


# ==================== Helper Function Tests ====================

class TestHelperFunctions:
    """Tests for module-level helper functions"""

    def test_provision_tenant_phone_success(self):
        """Test quick helper works with env vars"""
        from src.tools.twilio_vapi_provisioner import provision_tenant_phone

        numbers = generate_available_numbers(1, 'ZA')
        search_response = TwilioResponseFactory.available_numbers(numbers)
        purchase_response = TwilioResponseFactory.purchase_success(numbers[0]['phone_number'], 'PN123')
        import_response = VAPIResponseFactory.import_success('vapi_123', numbers[0]['phone_number'])

        with patch.dict('os.environ', {
            'TWILIO_ACCOUNT_SID': 'ACtest',
            'TWILIO_AUTH_TOKEN': 'token',
            'VAPI_API_KEY': 'vapi_key'
        }):
            with patch('requests.get', return_value=search_response):
                with patch('requests.post', side_effect=[purchase_response, import_response]):
                    result = provision_tenant_phone(
                        client_id='tenant_abc',
                        assistant_id='ast_456'
                    )

        assert result['success'] is True

    def test_provision_tenant_phone_missing_credentials(self):
        """Test returns error without credentials"""
        from src.tools.twilio_vapi_provisioner import provision_tenant_phone

        with patch.dict('os.environ', {}, clear=True):
            result = provision_tenant_phone(
                client_id='tenant_abc',
                assistant_id='ast_456'
            )

        assert 'error' in result
        assert result['error'] == 'Missing credentials'

    def test_provision_tenant_phone_with_explicit_creds(self):
        """Test works with explicit credentials"""
        from src.tools.twilio_vapi_provisioner import provision_tenant_phone

        numbers = generate_available_numbers(1, 'ZA')
        search_response = TwilioResponseFactory.available_numbers(numbers)
        purchase_response = TwilioResponseFactory.purchase_success(numbers[0]['phone_number'], 'PN123')
        import_response = VAPIResponseFactory.import_success('vapi_123', numbers[0]['phone_number'])

        with patch('requests.get', return_value=search_response):
            with patch('requests.post', side_effect=[purchase_response, import_response]):
                result = provision_tenant_phone(
                    client_id='tenant_abc',
                    assistant_id='ast_456',
                    twilio_sid='ACtest',
                    twilio_token='token',
                    vapi_key='vapi_key'
                )

        assert result['success'] is True


# ==================== Phone Display Format Tests ====================

class TestPhoneDisplayFormat:
    """Tests for _format_phone_display method"""

    @pytest.fixture
    def provisioner(self):
        from src.tools.twilio_vapi_provisioner import TwilioVAPIProvisioner
        return TwilioVAPIProvisioner('ACtest', 'token', 'vapi_key')

    def test_format_phone_display_za(self, provisioner):
        """Test formats South African numbers"""
        result = provisioner._format_phone_display('+27123456789')
        assert result == '+27 12 345 6789'

    def test_format_phone_display_us(self, provisioner):
        """Test formats US/Canada numbers"""
        result = provisioner._format_phone_display('+15551234567')
        assert result == '+1 (555) 123-4567'

    def test_format_phone_display_other(self, provisioner):
        """Test returns number as-is for other countries"""
        result = provisioner._format_phone_display('+447700123456')
        assert result == '+447700123456'


# ==================== Get Pricing Tests ====================

class TestGetPricing:
    """Tests for get_pricing method"""

    @pytest.fixture
    def provisioner(self):
        from src.tools.twilio_vapi_provisioner import TwilioVAPIProvisioner
        return TwilioVAPIProvisioner('ACtest', 'token', 'vapi_key')

    def test_get_pricing_success(self, provisioner):
        """Test successful pricing retrieval"""
        mock_response = TwilioResponseFactory.pricing_info('ZA')

        with patch('requests.get', return_value=mock_response):
            result = provisioner.get_pricing('ZA')

        assert result['country'] == 'ZA'

    def test_get_pricing_error(self, provisioner):
        """Test returns error on API failure"""
        mock_response = MockHTTPResponse(404, {'error': 'Country not found'})

        with patch('requests.get', return_value=mock_response):
            result = provisioner.get_pricing('XX')

        assert 'error' in result

    def test_get_pricing_exception(self, provisioner):
        """Test handles exceptions gracefully"""
        with patch('requests.get', side_effect=Exception('Network error')):
            result = provisioner.get_pricing('ZA')

        assert 'error' in result
        assert 'Network error' in result['error']


# ==================== Available Numbers For Client Tests ====================

class TestAvailableNumbersForClient:
    """Tests for get_available_numbers_for_client method"""

    @pytest.fixture
    def provisioner(self):
        from src.tools.twilio_vapi_provisioner import TwilioVAPIProvisioner
        return TwilioVAPIProvisioner('ACtest', 'token', 'vapi_key')

    def test_get_available_numbers_formats_for_ui(self, provisioner):
        """Test returns formatted list with display field"""
        numbers = generate_available_numbers(3, 'ZA')
        mock_response = TwilioResponseFactory.available_numbers(numbers)

        with patch('requests.get', return_value=mock_response):
            result = provisioner.get_available_numbers_for_client(country_code='ZA')

        assert len(result) == 3
        for item in result:
            assert 'number' in item
            assert 'display' in item
            assert 'locality' in item
            assert 'capabilities' in item
            assert 'voice' in item['capabilities']
            assert 'sms' in item['capabilities']

    def test_get_available_numbers_with_area_code(self, provisioner):
        """Test passes area code to search"""
        numbers = generate_available_numbers(2, 'ZA', area_code='21')
        mock_response = TwilioResponseFactory.available_numbers(numbers)

        with patch('requests.get', return_value=mock_response) as mock_get:
            provisioner.get_available_numbers_for_client(country_code='ZA', area_code='21')

            call_kwargs = mock_get.call_args
            assert call_kwargs.kwargs['params']['AreaCode'] == '21'
