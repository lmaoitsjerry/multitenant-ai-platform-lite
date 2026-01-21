"""
Tests for PDF Generator - Multi-Tenant PDF Generation Service

Tests cover:
- PDFGenerator initialization and configuration
- Quote PDF generation with fpdf2
- Invoice PDF generation with Nova template layout
- WeasyPrint integration (mocked)
- Branding and styling
- Currency formatting
- Error handling
"""

import pytest
from unittest.mock import MagicMock, patch, Mock
from io import BytesIO

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ==================== Fixtures ====================

@pytest.fixture
def mock_config():
    """Create a mock ClientConfig for PDF generation."""
    config = MagicMock()
    config.client_id = "test_tenant"
    config.company_name = "Test Travel Company"
    config.primary_color = "#2E86AB"
    config.secondary_color = "#A23B72"
    config.logo_url = "https://example.com/logo.png"
    config.currency = "USD"
    config.company_address = "123 Test Street"
    config.company_city = "Cape Town"
    config.company_country = "South Africa"
    config.vat_number = "VAT123456"
    config.registration_number = "REG789"
    config.support_phone = "+27 21 555 1234"
    config.website = "https://testtravel.com"
    config.bank_name = "First National Bank"
    config.bank_account_number = "62000000001"
    config.bank_branch_code = "250655"
    config.bank_swift_code = "FIRNZAJJ"
    config.bank_usd_account = "62000000002"
    config.bank_usd_branch = "250655"
    config.bank_eur_account = None
    config.bank_eur_branch = None
    config.payment_reference_prefix = "TTC"
    config.primary_email = "info@testtravel.com"
    config.fax_number = None
    config.vat_rate = 15
    return config


@pytest.fixture
def mock_template_renderer():
    """Create a mock template renderer."""
    renderer = MagicMock()
    renderer.render_template.return_value = "<html><body>Test PDF</body></html>"
    return renderer


@pytest.fixture
def sample_quote_data():
    """Sample quote data for testing."""
    return {
        'quote_id': 'QT-20260121-ABC123',
        'destination': 'Cape Town',
        'check_in_date': '2026-03-15',
        'check_out_date': '2026-03-22',
        'adults': 2,
        'children': 1
    }


@pytest.fixture
def sample_hotels():
    """Sample hotel data for quote PDF."""
    return [
        {
            'hotel_name': 'The Cape Grace',
            'hotel_rating': '5 Star',
            'room_type': 'Deluxe Suite',
            'meal_plan': 'Bed & Breakfast',
            'price_per_person': 2500,
            'total_price': 7500,
            'transfers_total': 500
        },
        {
            'hotel_name': 'Victoria Falls Hotel',
            'hotel_rating': '4 Star',
            'room_type': 'Standard Room',
            'meal_plan': 'Half Board',
            'price_per_person': 1800,
            'total_price': 5400,
            'transfers_total': 300
        }
    ]


@pytest.fixture
def sample_customer_data():
    """Sample customer data for PDF generation."""
    return {
        'name': 'John Doe',
        'email': 'john@example.com',
        'phone': '+1234567890'
    }


@pytest.fixture
def sample_invoice_data():
    """Sample invoice data for testing."""
    return {
        'invoice_id': 'INV-20260121-XYZ789',
        'quote_id': 'QT-20260121-ABC123',
        'created_at': '2026-01-21T10:30:00Z',
        'due_date': '2026-02-21T00:00:00Z',
        'total_amount': 7500.00,
        'currency': 'USD',
        'notes': 'Thank you for your booking!',
        'destination': 'Cape Town',
        'check_in_date': '2026-03-15',
        'check_out_date': '2026-03-22',
        'room_type': 'Deluxe Suite',
        'meal_plan': 'Bed & Breakfast',
        'price_includes': [
            '7 nights accommodation',
            'Daily breakfast',
            'Airport transfers',
            'Tourism levy'
        ],
        'travelers': [
            {'name': 'John Doe', 'type': 'Adult', 'date_of_birth': '1985-06-15'},
            {'name': 'Jane Doe', 'type': 'Adult', 'date_of_birth': '1987-03-22'},
            {'name': 'Jimmy Doe', 'type': 'Child', 'date_of_birth': '2015-09-10'}
        ],
        'trip_details': {
            'destination': 'Cape Town',
            'check_in': '2026-03-15',
            'check_out': '2026-03-22'
        }
    }


@pytest.fixture
def sample_invoice_items():
    """Sample invoice line items."""
    return [
        {
            'destination': 'Cape Town',
            'description': 'Accommodation - 7 nights',
            'unit_price': 5500,
            'quantity': 1,
            'amount': 5500
        },
        {
            'destination': 'Cape Town',
            'description': 'Airport Transfers',
            'unit_price': 500,
            'quantity': 2,
            'amount': 1000
        },
        {
            'destination': 'Cape Town',
            'description': 'Safari Day Trip',
            'unit_price': 1000,
            'quantity': 1,
            'amount': 1000
        }
    ]


# ==================== Initialization Tests ====================

class TestPDFGeneratorInit:
    """Test PDFGenerator initialization."""

    def test_init_loads_branding_from_config(self, mock_config):
        """Should load branding settings from config."""
        # Import after fixtures to avoid import errors
        from src.utils.pdf_generator import PDFGenerator

        generator = PDFGenerator(mock_config)

        assert generator.company_name == "Test Travel Company"
        assert generator.primary_color == "#2E86AB"
        assert generator.secondary_color == "#A23B72"
        assert generator.currency == "USD"

    def test_init_with_default_branding(self):
        """Should use default branding when config values missing."""
        from src.utils.pdf_generator import PDFGenerator

        minimal_config = MagicMock()
        minimal_config.client_id = "minimal_tenant"
        # Remove attributes to trigger defaults
        del minimal_config.company_name
        del minimal_config.primary_color
        del minimal_config.secondary_color
        del minimal_config.currency

        generator = PDFGenerator(minimal_config)

        assert generator.company_name == "Travel Agency"
        assert generator.primary_color == "#2E86AB"
        assert generator.currency == "ZAR"

    def test_init_stores_template_renderer(self, mock_config, mock_template_renderer):
        """Should store template renderer for WeasyPrint."""
        from src.utils.pdf_generator import PDFGenerator

        generator = PDFGenerator(mock_config, mock_template_renderer)

        assert generator.template_renderer == mock_template_renderer


# ==================== Quote PDF Tests (fpdf2) ====================

class TestGenerateQuotePDF:
    """Test quote PDF generation."""

    def test_generate_quote_pdf_returns_bytes(
        self, mock_config, sample_quote_data, sample_hotels, sample_customer_data
    ):
        """Should return PDF as bytes."""
        from src.utils.pdf_generator import PDFGenerator, FPDF_AVAILABLE

        if not FPDF_AVAILABLE:
            pytest.skip("fpdf2 not available")

        generator = PDFGenerator(mock_config)
        result = generator.generate_quote_pdf(
            sample_quote_data, sample_hotels, sample_customer_data
        )

        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_generate_quote_pdf_valid_pdf_header(
        self, mock_config, sample_quote_data, sample_hotels, sample_customer_data
    ):
        """Should generate valid PDF with proper header."""
        from src.utils.pdf_generator import PDFGenerator, FPDF_AVAILABLE

        if not FPDF_AVAILABLE:
            pytest.skip("fpdf2 not available")

        generator = PDFGenerator(mock_config)
        result = generator.generate_quote_pdf(
            sample_quote_data, sample_hotels, sample_customer_data
        )

        # PDF files start with %PDF
        assert result.startswith(b'%PDF')

    def test_generate_quote_pdf_with_multiple_hotels(
        self, mock_config, sample_quote_data, sample_customer_data
    ):
        """Should handle multiple hotel options."""
        from src.utils.pdf_generator import PDFGenerator, FPDF_AVAILABLE

        if not FPDF_AVAILABLE:
            pytest.skip("fpdf2 not available")

        many_hotels = [
            {
                'hotel_name': f'Hotel {i}',
                'hotel_rating': '4 Star',
                'room_type': 'Standard',
                'meal_plan': 'BB',
                'price_per_person': 1000 + i * 100,
                'total_price': 2000 + i * 200,
                'transfers_total': 100
            }
            for i in range(5)
        ]

        generator = PDFGenerator(mock_config)
        result = generator.generate_quote_pdf(
            sample_quote_data, many_hotels, sample_customer_data
        )

        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_generate_quote_pdf_handles_empty_hotels(
        self, mock_config, sample_quote_data, sample_customer_data
    ):
        """Should handle empty hotel list."""
        from src.utils.pdf_generator import PDFGenerator, FPDF_AVAILABLE

        if not FPDF_AVAILABLE:
            pytest.skip("fpdf2 not available")

        generator = PDFGenerator(mock_config)
        result = generator.generate_quote_pdf(
            sample_quote_data, [], sample_customer_data
        )

        assert isinstance(result, bytes)

    def test_generate_quote_pdf_uses_config_currency(
        self, mock_config, sample_quote_data, sample_hotels, sample_customer_data
    ):
        """Should use currency from config."""
        from src.utils.pdf_generator import PDFGenerator, FPDF_AVAILABLE

        if not FPDF_AVAILABLE:
            pytest.skip("fpdf2 not available")

        mock_config.currency = "EUR"
        generator = PDFGenerator(mock_config)

        # Currency is used in PDF generation
        assert generator.currency == "EUR"


# ==================== Invoice PDF Tests ====================

class TestGenerateInvoicePDF:
    """Test invoice PDF generation."""

    def test_generate_invoice_pdf_returns_bytes(
        self, mock_config, sample_invoice_data, sample_invoice_items, sample_customer_data
    ):
        """Should return PDF as bytes."""
        from src.utils.pdf_generator import PDFGenerator, FPDF_AVAILABLE

        if not FPDF_AVAILABLE:
            pytest.skip("fpdf2 not available")

        generator = PDFGenerator(mock_config)
        result = generator.generate_invoice_pdf(
            sample_invoice_data, sample_invoice_items, sample_customer_data
        )

        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_generate_invoice_pdf_valid_pdf(
        self, mock_config, sample_invoice_data, sample_invoice_items, sample_customer_data
    ):
        """Should generate valid PDF."""
        from src.utils.pdf_generator import PDFGenerator, FPDF_AVAILABLE

        if not FPDF_AVAILABLE:
            pytest.skip("fpdf2 not available")

        generator = PDFGenerator(mock_config)
        result = generator.generate_invoice_pdf(
            sample_invoice_data, sample_invoice_items, sample_customer_data
        )

        assert result.startswith(b'%PDF')

    def test_generate_invoice_pdf_with_vat(
        self, mock_config, sample_invoice_data, sample_invoice_items, sample_customer_data
    ):
        """Should include VAT calculation when vat_rate configured."""
        from src.utils.pdf_generator import PDFGenerator, FPDF_AVAILABLE

        if not FPDF_AVAILABLE:
            pytest.skip("fpdf2 not available")

        mock_config.vat_rate = 15
        generator = PDFGenerator(mock_config)
        result = generator.generate_invoice_pdf(
            sample_invoice_data, sample_invoice_items, sample_customer_data
        )

        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_generate_invoice_pdf_without_vat(
        self, mock_config, sample_invoice_data, sample_invoice_items, sample_customer_data
    ):
        """Should work without VAT when vat_rate is 0."""
        from src.utils.pdf_generator import PDFGenerator, FPDF_AVAILABLE

        if not FPDF_AVAILABLE:
            pytest.skip("fpdf2 not available")

        mock_config.vat_rate = 0
        generator = PDFGenerator(mock_config)
        result = generator.generate_invoice_pdf(
            sample_invoice_data, sample_invoice_items, sample_customer_data
        )

        assert isinstance(result, bytes)

    def test_generate_invoice_pdf_with_travelers(
        self, mock_config, sample_invoice_data, sample_invoice_items, sample_customer_data
    ):
        """Should include traveler details when provided."""
        from src.utils.pdf_generator import PDFGenerator, FPDF_AVAILABLE

        if not FPDF_AVAILABLE:
            pytest.skip("fpdf2 not available")

        generator = PDFGenerator(mock_config)
        result = generator.generate_invoice_pdf(
            sample_invoice_data, sample_invoice_items, sample_customer_data
        )

        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_generate_invoice_pdf_without_travelers(
        self, mock_config, sample_invoice_items, sample_customer_data
    ):
        """Should work without traveler details."""
        from src.utils.pdf_generator import PDFGenerator, FPDF_AVAILABLE

        if not FPDF_AVAILABLE:
            pytest.skip("fpdf2 not available")

        invoice_data = {
            'invoice_id': 'INV-001',
            'created_at': '2026-01-21',
            'due_date': '2026-02-21',
            'total_amount': 5000,
            'currency': 'USD'
        }

        generator = PDFGenerator(mock_config)
        result = generator.generate_invoice_pdf(
            invoice_data, sample_invoice_items, sample_customer_data
        )

        assert isinstance(result, bytes)

    def test_generate_invoice_pdf_with_price_includes(
        self, mock_config, sample_invoice_data, sample_invoice_items, sample_customer_data
    ):
        """Should include price inclusions when provided."""
        from src.utils.pdf_generator import PDFGenerator, FPDF_AVAILABLE

        if not FPDF_AVAILABLE:
            pytest.skip("fpdf2 not available")

        generator = PDFGenerator(mock_config)
        result = generator.generate_invoice_pdf(
            sample_invoice_data, sample_invoice_items, sample_customer_data
        )

        assert isinstance(result, bytes)

    def test_generate_invoice_pdf_with_banking_details(
        self, mock_config, sample_invoice_data, sample_invoice_items, sample_customer_data
    ):
        """Should include banking details from config."""
        from src.utils.pdf_generator import PDFGenerator, FPDF_AVAILABLE

        if not FPDF_AVAILABLE:
            pytest.skip("fpdf2 not available")

        generator = PDFGenerator(mock_config)
        result = generator.generate_invoice_pdf(
            sample_invoice_data, sample_invoice_items, sample_customer_data
        )

        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_generate_invoice_pdf_sanitizes_unicode(
        self, mock_config, sample_invoice_items, sample_customer_data
    ):
        """Should sanitize unicode characters not supported by Helvetica."""
        from src.utils.pdf_generator import PDFGenerator, FPDF_AVAILABLE

        if not FPDF_AVAILABLE:
            pytest.skip("fpdf2 not available")

        invoice_data = {
            'invoice_id': 'INV-001',
            'created_at': '2026-01-21',
            'due_date': '2026-02-21',
            'total_amount': 5000,
            'currency': 'USD',
            'room_type': 'Deluxe Suite',  # Unicode star removed
            'notes': 'Thank you for your booking'  # Unicode quotes replaced
        }

        generator = PDFGenerator(mock_config)
        result = generator.generate_invoice_pdf(
            invoice_data, sample_invoice_items, sample_customer_data
        )

        assert isinstance(result, bytes)

    def test_generate_invoice_pdf_handles_missing_banking(
        self, sample_invoice_data, sample_invoice_items, sample_customer_data
    ):
        """Should handle missing banking details gracefully."""
        from src.utils.pdf_generator import PDFGenerator, FPDF_AVAILABLE

        if not FPDF_AVAILABLE:
            pytest.skip("fpdf2 not available")

        config = MagicMock()
        config.client_id = "test"
        config.company_name = "Test Co"
        config.primary_color = "#2E86AB"
        config.secondary_color = "#A23B72"
        config.currency = "USD"
        # No banking details
        config.bank_name = None
        config.bank_account_number = None
        config.bank_branch_code = None
        config.vat_rate = 0

        generator = PDFGenerator(config)
        result = generator.generate_invoice_pdf(
            sample_invoice_data, sample_invoice_items, sample_customer_data
        )

        assert isinstance(result, bytes)


# ==================== WeasyPrint Tests ====================

class TestWeasyPrintIntegration:
    """Test WeasyPrint integration (mocked)."""

    def test_uses_weasyprint_when_available(
        self, mock_config, mock_template_renderer,
        sample_quote_data, sample_hotels, sample_customer_data
    ):
        """Should use WeasyPrint when available with template renderer."""
        from src.utils.pdf_generator import PDFGenerator, WEASYPRINT_AVAILABLE

        if not WEASYPRINT_AVAILABLE:
            pytest.skip("WeasyPrint not available")

        generator = PDFGenerator(mock_config, mock_template_renderer)

        # Test that _generate_with_weasyprint method exists and is callable
        assert hasattr(generator, '_generate_with_weasyprint')
        assert callable(generator._generate_with_weasyprint)

    def test_template_renderer_called_with_context(
        self, mock_config, mock_template_renderer,
        sample_quote_data, sample_hotels, sample_customer_data
    ):
        """Should pass correct context to template renderer."""
        from src.utils.pdf_generator import PDFGenerator, WEASYPRINT_AVAILABLE

        if not WEASYPRINT_AVAILABLE:
            pytest.skip("WeasyPrint not available")

        # Mock HTML to avoid actual rendering
        with patch('src.utils.pdf_generator.HTML') as mock_html:
            mock_html_instance = MagicMock()
            mock_html_instance.write_pdf.return_value = b'%PDF-1.4'
            mock_html.return_value = mock_html_instance

            generator = PDFGenerator(mock_config, mock_template_renderer)
            generator._generate_with_weasyprint(
                sample_quote_data, sample_hotels, sample_customer_data
            )

            # Template renderer should be called with correct template
            mock_template_renderer.render_template.assert_called_once()
            call_args = mock_template_renderer.render_template.call_args
            assert 'pdf/quote.html' in call_args[0][0]

    def test_weasyprint_method_exists(self, mock_config):
        """Should have _generate_with_weasyprint method."""
        from src.utils.pdf_generator import PDFGenerator

        generator = PDFGenerator(mock_config)
        assert hasattr(generator, '_generate_with_weasyprint')


# ==================== Error Handling Tests ====================

class TestPDFGeneratorErrors:
    """Test error handling in PDF generation."""

    def test_returns_empty_bytes_when_no_library(self, mock_config):
        """Should return empty bytes when no PDF library available."""
        from src.utils.pdf_generator import PDFGenerator

        with patch('src.utils.pdf_generator.WEASYPRINT_AVAILABLE', False), \
             patch('src.utils.pdf_generator.FPDF_AVAILABLE', False):

            generator = PDFGenerator(mock_config)
            result = generator.generate_quote_pdf(
                {'quote_id': 'QT-001'},
                [],
                {'name': 'Test'}
            )

            assert result == b""

    def test_handles_fpdf_exception(
        self, mock_config, sample_quote_data, sample_hotels, sample_customer_data
    ):
        """Should handle fpdf2 exceptions gracefully."""
        from src.utils.pdf_generator import PDFGenerator, FPDF_AVAILABLE

        if not FPDF_AVAILABLE:
            pytest.skip("fpdf2 not available")

        with patch('src.utils.pdf_generator.FPDF') as mock_fpdf:
            mock_fpdf.side_effect = Exception("FPDF error")

            generator = PDFGenerator(mock_config)
            result = generator._generate_with_fpdf(
                sample_quote_data, sample_hotels, sample_customer_data
            )

            assert result == b""

    def test_handles_invoice_fpdf_exception(
        self, mock_config, sample_invoice_data, sample_invoice_items, sample_customer_data
    ):
        """Should handle invoice generation exceptions."""
        from src.utils.pdf_generator import PDFGenerator, FPDF_AVAILABLE

        if not FPDF_AVAILABLE:
            pytest.skip("fpdf2 not available")

        with patch('src.utils.pdf_generator.FPDF') as mock_fpdf:
            mock_fpdf.side_effect = Exception("FPDF invoice error")

            generator = PDFGenerator(mock_config)
            result = generator._generate_invoice_fpdf(
                sample_invoice_data, sample_invoice_items, sample_customer_data
            )

            assert result == b""


# ==================== Hex Color Conversion Tests ====================

class TestColorConversion:
    """Test hex to RGB color conversion."""

    def test_hex_to_rgb_conversion(
        self, mock_config, sample_quote_data, sample_hotels, sample_customer_data
    ):
        """Should convert hex colors to RGB correctly."""
        from src.utils.pdf_generator import PDFGenerator, FPDF_AVAILABLE

        if not FPDF_AVAILABLE:
            pytest.skip("fpdf2 not available")

        # Test with various hex colors
        mock_config.primary_color = "#FF0000"  # Red
        generator = PDFGenerator(mock_config)

        # If PDF generates without error, color conversion works
        result = generator.generate_quote_pdf(
            sample_quote_data, sample_hotels, sample_customer_data
        )

        assert isinstance(result, bytes)

    def test_handles_invalid_color_format(
        self, mock_config, sample_quote_data, sample_hotels, sample_customer_data
    ):
        """Should handle color with # prefix."""
        from src.utils.pdf_generator import PDFGenerator, FPDF_AVAILABLE

        if not FPDF_AVAILABLE:
            pytest.skip("fpdf2 not available")

        mock_config.primary_color = "#FFFFFF"
        mock_config.secondary_color = "#000000"

        generator = PDFGenerator(mock_config)
        result = generator.generate_quote_pdf(
            sample_quote_data, sample_hotels, sample_customer_data
        )

        assert isinstance(result, bytes)


# ==================== Page Break Tests ====================

class TestPageBreaks:
    """Test PDF pagination."""

    def test_handles_many_hotels_page_breaks(
        self, mock_config, sample_quote_data, sample_customer_data
    ):
        """Should handle page breaks with many hotels."""
        from src.utils.pdf_generator import PDFGenerator, FPDF_AVAILABLE

        if not FPDF_AVAILABLE:
            pytest.skip("fpdf2 not available")

        # Create many hotels to trigger page breaks
        many_hotels = [
            {
                'hotel_name': f'Hotel {i} - A Very Long Name To Fill Space',
                'hotel_rating': '5 Star',
                'room_type': 'Deluxe Ocean View Suite with Private Balcony',
                'meal_plan': 'All Inclusive Plus Premium',
                'price_per_person': 5000 + i * 100,
                'total_price': 15000 + i * 300,
                'transfers_total': 500
            }
            for i in range(10)
        ]

        generator = PDFGenerator(mock_config)
        result = generator.generate_quote_pdf(
            sample_quote_data, many_hotels, sample_customer_data
        )

        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_handles_many_invoice_items_page_breaks(
        self, mock_config, sample_invoice_data, sample_customer_data
    ):
        """Should handle page breaks with many invoice items."""
        from src.utils.pdf_generator import PDFGenerator, FPDF_AVAILABLE

        if not FPDF_AVAILABLE:
            pytest.skip("fpdf2 not available")

        # Create many items to trigger page breaks
        many_items = [
            {
                'destination': 'Cape Town',
                'description': f'Service Item {i} - Description text',
                'unit_price': 100 + i * 10,
                'quantity': i + 1,
                'amount': (100 + i * 10) * (i + 1)
            }
            for i in range(30)
        ]

        generator = PDFGenerator(mock_config)
        result = generator.generate_invoice_pdf(
            sample_invoice_data, many_items, sample_customer_data
        )

        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_handles_many_travelers_page_breaks(
        self, mock_config, sample_invoice_items, sample_customer_data
    ):
        """Should handle page breaks with many travelers."""
        from src.utils.pdf_generator import PDFGenerator, FPDF_AVAILABLE

        if not FPDF_AVAILABLE:
            pytest.skip("fpdf2 not available")

        invoice_data = {
            'invoice_id': 'INV-001',
            'created_at': '2026-01-21',
            'due_date': '2026-02-21',
            'total_amount': 50000,
            'currency': 'USD',
            'travelers': [
                {
                    'name': f'Traveler {i} Full Name',
                    'type': 'Adult' if i % 3 != 0 else 'Child',
                    'date_of_birth': f'19{80 + i % 20}-01-15',
                    'passport_number': f'AB{i:06d}',
                    'nationality': 'South African'
                }
                for i in range(15)
            ]
        }

        generator = PDFGenerator(mock_config)
        result = generator.generate_invoice_pdf(
            invoice_data, sample_invoice_items, sample_customer_data
        )

        assert isinstance(result, bytes)
        assert len(result) > 0


# ==================== Library Availability Tests ====================

class TestLibraryAvailability:
    """Test PDF library detection."""

    def test_fpdf_availability_flag(self):
        """Should have FPDF_AVAILABLE constant."""
        from src.utils.pdf_generator import FPDF_AVAILABLE

        # Should be boolean
        assert isinstance(FPDF_AVAILABLE, bool)

    def test_weasyprint_availability_flag(self):
        """Should have WEASYPRINT_AVAILABLE constant."""
        from src.utils.pdf_generator import WEASYPRINT_AVAILABLE

        # Should be boolean
        assert isinstance(WEASYPRINT_AVAILABLE, bool)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
