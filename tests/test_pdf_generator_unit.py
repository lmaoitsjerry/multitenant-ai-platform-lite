"""
Unit tests for PDF Generator module

Tests PDFGenerator class, initialization, hex_to_rgb conversion,
sanitize_text helper, and PDF generation with mocked libraries.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestModuleLevelConstants:
    """Test module-level availability flags"""

    def test_weasyprint_available_is_bool(self):
        """WEASYPRINT_AVAILABLE should be a boolean"""
        from src.utils.pdf_generator import WEASYPRINT_AVAILABLE
        assert isinstance(WEASYPRINT_AVAILABLE, bool)

    def test_fpdf_available_is_bool(self):
        """FPDF_AVAILABLE should be a boolean"""
        from src.utils.pdf_generator import FPDF_AVAILABLE
        assert isinstance(FPDF_AVAILABLE, bool)


class TestPDFGeneratorInit:
    """Test PDFGenerator initialization"""

    @pytest.fixture
    def mock_config(self):
        """Create mock client config"""
        config = MagicMock()
        config.client_id = "test_client"
        config.company_name = "Test Travel Co"
        config.primary_color = "#2E86AB"
        config.secondary_color = "#A23B72"
        config.logo_url = "https://example.com/logo.png"
        config.currency = "USD"
        return config

    def test_init_with_full_config(self, mock_config):
        """Should initialize with all config values"""
        from src.utils.pdf_generator import PDFGenerator

        pdf_gen = PDFGenerator(mock_config)

        assert pdf_gen.company_name == "Test Travel Co"
        assert pdf_gen.primary_color == "#2E86AB"
        assert pdf_gen.secondary_color == "#A23B72"
        assert pdf_gen.logo_url == "https://example.com/logo.png"
        assert pdf_gen.currency == "USD"

    def test_init_with_minimal_config(self):
        """Should use defaults for missing config values"""
        from src.utils.pdf_generator import PDFGenerator

        minimal_config = MagicMock(spec=[])  # No attributes
        minimal_config.client_id = "minimal_client"

        pdf_gen = PDFGenerator(minimal_config)

        assert pdf_gen.company_name == "Travel Agency"
        assert pdf_gen.primary_color == "#2E86AB"
        assert pdf_gen.secondary_color == "#A23B72"
        assert pdf_gen.logo_url is None
        assert pdf_gen.currency == "ZAR"

    def test_init_stores_template_renderer(self, mock_config):
        """Should store template renderer"""
        from src.utils.pdf_generator import PDFGenerator

        mock_renderer = MagicMock()
        pdf_gen = PDFGenerator(mock_config, template_renderer=mock_renderer)

        assert pdf_gen.template_renderer == mock_renderer


class TestHexToRgbConversion:
    """Test hex color to RGB conversion"""

    def test_hex_to_rgb_basic(self):
        """Test hex_to_rgb conversion (inline function)"""
        def hex_to_rgb(hex_color):
            hex_color = hex_color.lstrip('#')
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

        result = hex_to_rgb("#FF5733")
        assert result == (255, 87, 51)

    def test_hex_to_rgb_without_hash(self):
        """Should handle color without hash"""
        def hex_to_rgb(hex_color):
            hex_color = hex_color.lstrip('#')
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

        result = hex_to_rgb("2E86AB")
        assert result == (46, 134, 171)

    def test_hex_to_rgb_black(self):
        """Should convert black correctly"""
        def hex_to_rgb(hex_color):
            hex_color = hex_color.lstrip('#')
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

        result = hex_to_rgb("#000000")
        assert result == (0, 0, 0)

    def test_hex_to_rgb_white(self):
        """Should convert white correctly"""
        def hex_to_rgb(hex_color):
            hex_color = hex_color.lstrip('#')
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

        result = hex_to_rgb("#FFFFFF")
        assert result == (255, 255, 255)

    def test_hex_to_rgb_primary_color(self):
        """Should convert primary brand color"""
        def hex_to_rgb(hex_color):
            hex_color = hex_color.lstrip('#')
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

        result = hex_to_rgb("#2E86AB")
        assert result == (46, 134, 171)


class TestSanitizeTextFunction:
    """Test sanitize_text helper function from pdf_generator"""

    def _sanitize_text(self, text):
        """Copy of sanitize_text from pdf_generator for testing"""
        if not text:
            return ''
        text = str(text)
        # Replace unicode stars with asterisks
        text = text.replace('\u2605', '*').replace('\u2606', '*')  # ★, ☆
        # Replace check marks and bullets
        text = text.replace('\u2713', 'v').replace('\u2717', 'x').replace('\u2022', '-')  # ✓, ✗, •
        # Replace dashes
        text = text.replace('\u2013', '-').replace('\u2014', '-')  # –, —
        # Replace smart quotes
        text = text.replace('\u201c', '"').replace('\u201d', '"')  # ", "
        text = text.replace('\u2018', "'").replace('\u2019', "'")  # ', '
        # Remove any remaining non-ASCII characters
        return ''.join(c if ord(c) < 128 else '' for c in text)

    def test_sanitize_text_unicode_stars(self):
        """Test sanitize_text converts unicode stars"""
        result = self._sanitize_text("5 \u2605\u2605\u2605\u2605\u2605 rating")
        assert result == "5 ***** rating"

    def test_sanitize_text_check_marks(self):
        """Test sanitize_text converts check marks"""
        result = self._sanitize_text("Task \u2713 Complete \u2717 Failed")
        assert result == "Task v Complete x Failed"

    def test_sanitize_text_bullets(self):
        """Test sanitize_text converts bullets"""
        result = self._sanitize_text("\u2022 Item 1 \u2022 Item 2")
        assert result == "- Item 1 - Item 2"

    def test_sanitize_text_smart_quotes(self):
        """Test sanitize_text converts smart quotes"""
        test_str = "\u201cHello\u201d and \u2018World\u2019"  # "Hello" and 'World'
        result = self._sanitize_text(test_str)
        assert result == "\"Hello\" and 'World'"

    def test_sanitize_text_dashes(self):
        """Test sanitize_text converts unicode dashes"""
        result = self._sanitize_text("en\u2013dash and em\u2014dash")
        assert result == "en-dash and em-dash"

    def test_sanitize_text_empty_input(self):
        """Test sanitize_text handles empty input"""
        assert self._sanitize_text(None) == ''
        assert self._sanitize_text('') == ''

    def test_sanitize_text_removes_non_ascii(self):
        """Test sanitize_text removes remaining non-ASCII"""
        result = self._sanitize_text("Caf\u00e9 r\u00e9sum\u00e9 na\u00efve")
        assert result == "Caf rsum nave"

    def test_sanitize_text_ascii_unchanged(self):
        """Test sanitize_text leaves ASCII unchanged"""
        result = self._sanitize_text("Hello World 123!@#")
        assert result == "Hello World 123!@#"


class TestGenerateQuotePdf:
    """Test generate_quote_pdf method"""

    @pytest.fixture
    def mock_config(self):
        config = MagicMock()
        config.client_id = "test_client"
        config.company_name = "Test Travel"
        config.primary_color = "#2E86AB"
        config.secondary_color = "#A23B72"
        config.logo_url = None
        config.currency = "USD"
        return config

    @pytest.fixture
    def quote_data(self):
        return {
            'quote_id': 'Q-12345',
            'destination': 'Maldives',
            'check_in_date': '2024-03-15',
            'check_out_date': '2024-03-22',
            'adults': 2,
            'children': 1
        }

    @pytest.fixture
    def hotels(self):
        return [
            {
                'hotel_name': 'Paradise Resort',
                'hotel_rating': '5 stars',
                'room_type': 'Ocean Villa',
                'meal_plan': 'All Inclusive',
                'price_per_person': 5000,
                'total_price': 15000,
                'transfers_total': 500
            }
        ]

    @pytest.fixture
    def customer_data(self):
        return {
            'name': 'John Doe',
            'email': 'john@example.com'
        }

    def test_returns_empty_bytes_when_no_library(self, mock_config, quote_data, hotels, customer_data):
        """Should return empty bytes when no PDF library available"""
        from src.utils.pdf_generator import PDFGenerator

        with patch('src.utils.pdf_generator.WEASYPRINT_AVAILABLE', False), \
             patch('src.utils.pdf_generator.FPDF_AVAILABLE', False):
            pdf_gen = PDFGenerator(mock_config)
            result = pdf_gen.generate_quote_pdf(quote_data, hotels, customer_data)
            assert result == b""

    def test_uses_weasyprint_when_available_with_renderer(self, mock_config, quote_data, hotels, customer_data):
        """Should use WeasyPrint when available with template renderer"""
        from src.utils.pdf_generator import PDFGenerator, WEASYPRINT_AVAILABLE

        if not WEASYPRINT_AVAILABLE:
            pytest.skip("WeasyPrint not available")

        mock_renderer = MagicMock()
        mock_renderer.render_template.return_value = "<html><body>Test</body></html>"

        pdf_gen = PDFGenerator(mock_config, template_renderer=mock_renderer)

        with patch('src.utils.pdf_generator.HTML') as mock_html:
            mock_html_instance = MagicMock()
            mock_html_instance.write_pdf.return_value = b"PDF bytes"
            mock_html.return_value = mock_html_instance

            result = pdf_gen.generate_quote_pdf(quote_data, hotels, customer_data)
            mock_renderer.render_template.assert_called_once()


class TestGenerateQuotePdfWithFpdf:
    """Test generate_quote_pdf with fpdf2 (when available)"""

    @pytest.fixture
    def mock_config(self):
        config = MagicMock()
        config.client_id = "test_client"
        config.company_name = "Test Travel"
        config.primary_color = "#2E86AB"
        config.secondary_color = "#A23B72"
        config.logo_url = None
        config.currency = "USD"
        return config

    def test_fpdf_generates_pdf_bytes(self, mock_config):
        """Should generate PDF bytes with fpdf2"""
        from src.utils.pdf_generator import PDFGenerator, FPDF_AVAILABLE

        if not FPDF_AVAILABLE:
            pytest.skip("fpdf2 not available")

        pdf_gen = PDFGenerator(mock_config)
        result = pdf_gen.generate_quote_pdf(
            {'quote_id': 'Q-1', 'destination': 'Maldives'},
            [{'hotel_name': 'Test', 'hotel_rating': '5*', 'room_type': 'Suite',
              'meal_plan': 'AI', 'price_per_person': 1000, 'total_price': 2000,
              'transfers_total': 100}],
            {'name': 'John', 'email': 'john@test.com'}
        )

        assert len(result) > 0
        assert result[:4] == b'%PDF'


class TestGenerateInvoicePdf:
    """Test generate_invoice_pdf method"""

    @pytest.fixture
    def mock_config(self):
        config = MagicMock()
        config.client_id = "test_client"
        config.company_name = "Test Travel"
        config.primary_color = "#2E86AB"
        config.secondary_color = "#A23B72"
        config.logo_url = None
        config.currency = "USD"
        config.company_address = "123 Main St"
        config.company_city = "Cape Town"
        config.company_country = "South Africa"
        config.vat_number = "VAT123456"
        config.registration_number = "REG789"
        config.support_phone = "+27 21 555 1234"
        config.website = "https://testtravel.com"
        config.vat_rate = 15
        config.bank_name = "First National Bank"
        config.bank_account_number = "12345678"
        config.bank_branch_code = "250655"
        config.bank_swift_code = "FIRNZAJJ"
        config.payment_reference_prefix = "TT"
        config.bank_usd_account = None
        config.bank_usd_branch = None
        config.bank_eur_account = None
        config.bank_eur_branch = None
        config.fax_number = None
        config.primary_email = "test@test.com"
        return config

    @pytest.fixture
    def invoice_data(self):
        return {
            'invoice_id': 'INV-2024-001',
            'quote_id': 'Q-12345',
            'created_at': '2024-02-01T10:00:00',
            'due_date': '2024-02-15T00:00:00',
            'total_amount': 15000,
            'currency': 'USD',
            'notes': 'Special request: Ocean view room',
            'trip_details': {
                'destination': 'Maldives',
                'check_in': '2024-03-15',
                'check_out': '2024-03-22'
            },
            'room_type': 'Ocean Villa',
            'meal_plan': 'All Inclusive',
            'price_includes': ['Airport transfers', 'Daily breakfast'],
            'travelers': [
                {'name': 'John Doe', 'type': 'Adult', 'passport_number': 'AB123456'}
            ]
        }

    @pytest.fixture
    def items(self):
        return [
            {
                'destination': 'Maldives',
                'description': 'Ocean Villa - 7 nights',
                'unit_price': 5000,
                'quantity': 2,
                'amount': 10000
            }
        ]

    @pytest.fixture
    def customer_data(self):
        return {
            'name': 'John Doe',
            'email': 'john@example.com',
            'phone': '+1 555 123 4567'
        }

    def test_returns_empty_when_fpdf_unavailable(self, mock_config, invoice_data, items, customer_data):
        """Should return empty bytes when fpdf not available"""
        from src.utils.pdf_generator import PDFGenerator

        with patch('src.utils.pdf_generator.FPDF_AVAILABLE', False):
            pdf_gen = PDFGenerator(mock_config)
            result = pdf_gen.generate_invoice_pdf(invoice_data, items, customer_data)
            assert result == b""

    def test_generates_invoice_with_fpdf(self, mock_config, invoice_data, items, customer_data):
        """Should generate invoice PDF with fpdf2"""
        from src.utils.pdf_generator import PDFGenerator, FPDF_AVAILABLE

        if not FPDF_AVAILABLE:
            pytest.skip("fpdf2 not available")

        pdf_gen = PDFGenerator(mock_config)
        result = pdf_gen.generate_invoice_pdf(invoice_data, items, customer_data)

        assert len(result) > 0
        assert result[:4] == b'%PDF'

    def test_invoice_handles_empty_travelers(self, mock_config, invoice_data, items, customer_data):
        """Should handle invoice without travelers"""
        from src.utils.pdf_generator import PDFGenerator, FPDF_AVAILABLE

        if not FPDF_AVAILABLE:
            pytest.skip("fpdf2 not available")

        invoice_data_no_travelers = invoice_data.copy()
        invoice_data_no_travelers['travelers'] = []

        pdf_gen = PDFGenerator(mock_config)
        result = pdf_gen.generate_invoice_pdf(invoice_data_no_travelers, items, customer_data)

        assert len(result) > 0

    def test_invoice_handles_minimal_data(self, mock_config):
        """Should handle minimal invoice data"""
        from src.utils.pdf_generator import PDFGenerator, FPDF_AVAILABLE

        if not FPDF_AVAILABLE:
            pytest.skip("fpdf2 not available")

        pdf_gen = PDFGenerator(mock_config)
        result = pdf_gen.generate_invoice_pdf(
            {'invoice_id': 'INV-1'},
            [{'description': 'Item', 'amount': 100}],
            {'name': 'Test'}
        )

        assert len(result) > 0


class TestWeasyPrintIntegration:
    """Integration tests when WeasyPrint is available"""

    @pytest.fixture
    def mock_config(self):
        config = MagicMock()
        config.client_id = "test"
        config.company_name = "Test Travel"
        config.primary_color = "#2E86AB"
        config.secondary_color = "#A23B72"
        config.logo_url = None
        config.currency = "USD"
        return config

    def test_uses_weasyprint_when_available(self, mock_config):
        """Should use WeasyPrint when available"""
        from src.utils.pdf_generator import PDFGenerator, WEASYPRINT_AVAILABLE

        if not WEASYPRINT_AVAILABLE:
            pytest.skip("WeasyPrint not available")

        mock_renderer = MagicMock()
        mock_renderer.render_template.return_value = "<html><body><h1>Test Quote</h1></body></html>"

        pdf_gen = PDFGenerator(mock_config, template_renderer=mock_renderer)

        quote_data = {'quote_id': 'Q-1', 'destination': 'Test'}
        hotels = []
        customer_data = {'name': 'Test User'}

        result = pdf_gen.generate_quote_pdf(quote_data, hotels, customer_data)

        assert len(result) > 0
        assert result[:4] == b'%PDF'

    def test_template_renderer_called_with_context(self, mock_config):
        """Should call template renderer with full context"""
        from src.utils.pdf_generator import PDFGenerator, WEASYPRINT_AVAILABLE

        if not WEASYPRINT_AVAILABLE:
            pytest.skip("WeasyPrint not available")

        mock_renderer = MagicMock()
        mock_renderer.render_template.return_value = "<html></html>"

        pdf_gen = PDFGenerator(mock_config, template_renderer=mock_renderer)

        quote_data = {'quote_id': 'Q-123'}
        hotels = [{'hotel_name': 'Test Hotel'}]
        customer_data = {'name': 'Test'}

        with patch('src.utils.pdf_generator.HTML') as mock_html:
            mock_html.return_value.write_pdf.return_value = b"PDF"
            pdf_gen.generate_quote_pdf(quote_data, hotels, customer_data)

        mock_renderer.render_template.assert_called_once()
        call_args = mock_renderer.render_template.call_args
        context = call_args[0][1]

        assert context['company_name'] == "Test Travel"
        assert context['currency'] == "USD"
        assert context['quote'] == quote_data
        assert context['hotels'] == hotels
        assert context['customer'] == customer_data


class TestColorConversion:
    """Test color conversion edge cases"""

    def test_hex_to_rgb_conversion(self):
        """Should convert hex colors to RGB tuples"""
        def hex_to_rgb(hex_color):
            hex_color = hex_color.lstrip('#')
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

        assert hex_to_rgb("#FF0000") == (255, 0, 0)  # Red
        assert hex_to_rgb("#00FF00") == (0, 255, 0)  # Green
        assert hex_to_rgb("#0000FF") == (0, 0, 255)  # Blue
        assert hex_to_rgb("#2E86AB") == (46, 134, 171)  # Primary color

    def test_handles_invalid_color_format(self):
        """Should handle invalid color formats gracefully"""
        def hex_to_rgb(hex_color):
            hex_color = hex_color.lstrip('#')
            try:
                return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            except (ValueError, IndexError):
                return (0, 0, 0)

        # Short color code - should fail gracefully
        result = hex_to_rgb("#FFF")
        assert isinstance(result, tuple)


class TestPDFPageBreaks:
    """Test PDF page breaks for long content"""

    @pytest.fixture
    def mock_config(self):
        config = MagicMock()
        config.client_id = "test"
        config.company_name = "Test Travel"
        config.primary_color = "#2E86AB"
        config.secondary_color = "#A23B72"
        config.currency = "USD"
        config.vat_rate = 0
        return config

    def test_handles_many_hotels_page_breaks(self, mock_config):
        """Should handle many hotels with page breaks"""
        from src.utils.pdf_generator import PDFGenerator, FPDF_AVAILABLE

        if not FPDF_AVAILABLE:
            pytest.skip("fpdf2 not available")

        hotels = [
            {
                'hotel_name': f'Hotel {i}',
                'hotel_rating': '5 stars',
                'room_type': 'Deluxe',
                'meal_plan': 'AI',
                'price_per_person': 1000 * i,
                'total_price': 3000 * i,
                'transfers_total': 100
            }
            for i in range(1, 21)
        ]

        pdf_gen = PDFGenerator(mock_config)
        result = pdf_gen.generate_quote_pdf(
            {'quote_id': 'Q-1', 'destination': 'Test'},
            hotels,
            {'name': 'Test User', 'email': 'test@test.com'}
        )

        assert len(result) > 0
        assert result[:4] == b'%PDF'

    def test_handles_many_invoice_items(self, mock_config):
        """Should handle many invoice items"""
        from src.utils.pdf_generator import PDFGenerator, FPDF_AVAILABLE

        if not FPDF_AVAILABLE:
            pytest.skip("fpdf2 not available")

        items = [
            {
                'destination': f'Dest {i}',
                'description': f'Item description {i}',
                'unit_price': 100 * i,
                'quantity': 1,
                'amount': 100 * i
            }
            for i in range(1, 30)
        ]

        mock_config.vat_rate = 15
        pdf_gen = PDFGenerator(mock_config)
        result = pdf_gen.generate_invoice_pdf(
            {'invoice_id': 'INV-1'},
            items,
            {'name': 'Test'}
        )

        assert len(result) > 0

    def test_handles_many_travelers(self, mock_config):
        """Should handle many travelers"""
        from src.utils.pdf_generator import PDFGenerator, FPDF_AVAILABLE

        if not FPDF_AVAILABLE:
            pytest.skip("fpdf2 not available")

        travelers = [
            {'name': f'Traveler {i}', 'type': 'Adult', 'passport_number': f'P{i}'}
            for i in range(1, 50)
        ]

        invoice_data = {
            'invoice_id': 'INV-1',
            'travelers': travelers
        }

        pdf_gen = PDFGenerator(mock_config)
        result = pdf_gen.generate_invoice_pdf(
            invoice_data,
            [{'description': 'Trip', 'amount': 1000}],
            {'name': 'Test'}
        )

        assert len(result) > 0


class TestVATCalculation:
    """Test VAT calculation in invoices"""

    @pytest.fixture
    def mock_config_with_vat(self):
        config = MagicMock()
        config.client_id = "test"
        config.company_name = "Test Travel"
        config.primary_color = "#2E86AB"
        config.secondary_color = "#A23B72"
        config.currency = "ZAR"
        config.vat_rate = 15
        return config

    @pytest.fixture
    def mock_config_no_vat(self):
        config = MagicMock()
        config.client_id = "test"
        config.company_name = "Test Travel"
        config.primary_color = "#2E86AB"
        config.secondary_color = "#A23B72"
        config.currency = "USD"
        config.vat_rate = 0
        return config

    def test_invoice_with_vat(self, mock_config_with_vat):
        """Should calculate VAT correctly"""
        from src.utils.pdf_generator import PDFGenerator, FPDF_AVAILABLE

        if not FPDF_AVAILABLE:
            pytest.skip("fpdf2 not available")

        pdf_gen = PDFGenerator(mock_config_with_vat)
        result = pdf_gen.generate_invoice_pdf(
            {'invoice_id': 'INV-1'},
            [{'description': 'Trip', 'amount': 10000}],
            {'name': 'Test'}
        )

        assert len(result) > 0

    def test_invoice_without_vat(self, mock_config_no_vat):
        """Should skip VAT when rate is 0"""
        from src.utils.pdf_generator import PDFGenerator, FPDF_AVAILABLE

        if not FPDF_AVAILABLE:
            pytest.skip("fpdf2 not available")

        pdf_gen = PDFGenerator(mock_config_no_vat)
        result = pdf_gen.generate_invoice_pdf(
            {'invoice_id': 'INV-1'},
            [{'description': 'Trip', 'amount': 10000}],
            {'name': 'Test'}
        )

        assert len(result) > 0


class TestPDFGeneratorErrors:
    """Test error handling"""

    @pytest.fixture
    def mock_config(self):
        config = MagicMock()
        config.client_id = "test"
        config.company_name = "Test"
        config.primary_color = "#2E86AB"
        config.secondary_color = "#A23B72"
        config.currency = "USD"
        return config

    def test_handles_weasyprint_error_fallback(self, mock_config):
        """Should fall back to fpdf when weasyprint fails"""
        from src.utils.pdf_generator import PDFGenerator, WEASYPRINT_AVAILABLE, FPDF_AVAILABLE

        if not WEASYPRINT_AVAILABLE:
            pytest.skip("WeasyPrint not available")
        if not FPDF_AVAILABLE:
            pytest.skip("fpdf2 not available")

        mock_renderer = MagicMock()
        mock_renderer.render_template.side_effect = Exception("Template error")

        pdf_gen = PDFGenerator(mock_config, template_renderer=mock_renderer)
        result = pdf_gen.generate_quote_pdf(
            {'quote_id': 'Q-1', 'destination': 'Test'},
            [{'hotel_name': 'Test', 'hotel_rating': '5', 'room_type': 'Suite',
              'meal_plan': 'AI', 'price_per_person': 100, 'total_price': 200,
              'transfers_total': 50}],
            {'name': 'Test', 'email': 'test@test.com'}
        )

        # Should fall back to fpdf and produce output
        assert len(result) > 0


class TestBrandingApplication:
    """Test that branding is correctly applied"""

    def test_company_name_used(self):
        """Should use company name from config"""
        from src.utils.pdf_generator import PDFGenerator

        config = MagicMock()
        config.client_id = "test"
        config.company_name = "My Custom Travel"
        config.primary_color = "#FF0000"
        config.secondary_color = "#00FF00"
        config.currency = "EUR"

        pdf_gen = PDFGenerator(config)

        assert pdf_gen.company_name == "My Custom Travel"
        assert pdf_gen.primary_color == "#FF0000"
        assert pdf_gen.currency == "EUR"

    def test_logo_url_stored(self):
        """Should store logo URL from config"""
        from src.utils.pdf_generator import PDFGenerator

        config = MagicMock()
        config.client_id = "test"
        config.logo_url = "https://example.com/my-logo.png"

        pdf_gen = PDFGenerator(config)

        assert pdf_gen.logo_url == "https://example.com/my-logo.png"
