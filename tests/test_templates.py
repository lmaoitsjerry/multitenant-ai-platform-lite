
import unittest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.loader import ClientConfig
from src.utils.template_renderer import TemplateRenderer
from src.utils.pdf_generator import PDFGenerator

class TestTemplates(unittest.TestCase):
    def setUp(self):
        self.config = ClientConfig('example')
        self.renderer = TemplateRenderer(self.config)

    def test_email_template_rendering(self):
        """Test that email templates render with correct context"""
        context = {
            'customer_name': 'Test User',
            'destination': 'Zanzibar',
            'quote': {'price': 1000}
        }
        
        # We need to make sure the template exists or mock it.
        # Since we created templates/emails/quote.html, we can test it.
        try:
            rendered = self.renderer.render_template('emails/quote.html', context)
            self.assertIn('Test User', rendered)
            self.assertIn('Zanzibar', rendered)
            self.assertIn(self.config.company_name, rendered) # Branding
            self.assertIn(self.config.primary_color, rendered) # Branding color
        except Exception as e:
            self.fail(f"Template rendering failed: {e}")

    def test_agent_prompt_rendering(self):
        """Test that agent prompts render correctly"""
        # Test inbound prompt
        prompt = self.renderer.render_agent_prompt('inbound')
        self.assertIn(self.config.company_name, prompt)
        self.assertIn('Zanzibar', prompt)

    @patch('src.utils.pdf_generator.HTML')
    def test_pdf_generation(self, mock_html):
        """Test PDF generation logic (mocking WeasyPrint)"""
        # Mock the write_pdf method
        mock_html_instance = MagicMock()
        mock_html.return_value = mock_html_instance
        mock_html_instance.write_pdf.return_value = b'%PDF-1.4...'

        pdf_gen = PDFGenerator(self.config)
        quote_data = {
            'customer_name': 'Test User',
            'destination': 'Zanzibar',
            'hotels': [],
            'quote_id': '123'
        }
        
        pdf_bytes = pdf_gen.generate_quote_pdf(quote_data)
        
        self.assertTrue(len(pdf_bytes) > 0)
        mock_html.assert_called() # Verify WeasyPrint was called

if __name__ == '__main__':
    unittest.main()
