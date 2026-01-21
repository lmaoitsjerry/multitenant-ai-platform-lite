"""
PDF Generator - Multi-Tenant Version

Generates PDFs using WeasyPrint (preferred) or fpdf2 (fallback for Windows).
Each tenant's branding is applied to the generated PDFs.
"""

import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Try WeasyPrint first
WEASYPRINT_AVAILABLE = False
try:
    from weasyprint import HTML, CSS
    # Test if GTK3 is available by trying to import
    HTML(string="<html></html>")
    WEASYPRINT_AVAILABLE = True
    logger.info("WeasyPrint with GTK3 is available")
except Exception as e:
    logger.warning(f"WeasyPrint not available: {e}")

# Fallback to fpdf2
FPDF_AVAILABLE = False
try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
    logger.info("fpdf2 is available as fallback")
except ImportError:
    logger.warning("fpdf2 not installed. Run: pip install fpdf2")


class PDFGenerator:
    """Generate PDFs with client branding"""

    def __init__(self, config, template_renderer=None):
        """
        Initialize PDF generator
        
        Args:
            config: ClientConfig instance
            template_renderer: Optional TemplateRenderer instance
        """
        self.config = config
        self.template_renderer = template_renderer
        
        # Branding
        self.company_name = getattr(config, 'company_name', 'Travel Agency')
        self.primary_color = getattr(config, 'primary_color', '#2E86AB')
        self.secondary_color = getattr(config, 'secondary_color', '#A23B72')
        self.logo_url = getattr(config, 'logo_url', None)
        self.currency = getattr(config, 'currency', 'ZAR')
        
        logger.info(f"PDF generator initialized for {config.client_id}")

    def generate_quote_pdf(
        self,
        quote_data: Dict[str, Any],
        hotels: list,
        customer_data: Dict[str, Any]
    ) -> bytes:
        """
        Generate a quote PDF
        
        Args:
            quote_data: Quote information (id, dates, etc.)
            hotels: List of hotel options with pricing
            customer_data: Customer information
            
        Returns:
            PDF as bytes
        """
        if WEASYPRINT_AVAILABLE and self.template_renderer:
            return self._generate_with_weasyprint(quote_data, hotels, customer_data)
        elif FPDF_AVAILABLE:
            return self._generate_with_fpdf(quote_data, hotels, customer_data)
        else:
            logger.error("No PDF library available!")
            return b""

    def _generate_with_weasyprint(
        self,
        quote_data: Dict[str, Any],
        hotels: list,
        customer_data: Dict[str, Any]
    ) -> bytes:
        """Generate PDF using WeasyPrint (HTML/CSS)"""
        try:
            context = {
                'company_name': self.company_name,
                'primary_color': self.primary_color,
                'secondary_color': self.secondary_color,
                'logo_url': self.logo_url,
                'currency': self.currency,
                'quote': quote_data,
                'hotels': hotels,
                'customer': customer_data
            }
            
            html_content = self.template_renderer.render_template('pdf/quote.html', context)
            pdf_bytes = HTML(string=html_content).write_pdf()
            
            logger.info(f"✅ PDF generated with WeasyPrint: {len(pdf_bytes)} bytes")
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"WeasyPrint PDF generation failed: {e}")
            # Fall back to fpdf
            if FPDF_AVAILABLE:
                return self._generate_with_fpdf(quote_data, hotels, customer_data)
            return b""

    def _generate_with_fpdf(
        self,
        quote_data: Dict[str, Any],
        hotels: list,
        customer_data: Dict[str, Any]
    ) -> bytes:
        """Generate PDF using fpdf2 (pure Python)"""
        try:
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()
            
            # Convert hex color to RGB
            def hex_to_rgb(hex_color):
                hex_color = hex_color.lstrip('#')
                return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            
            primary_rgb = hex_to_rgb(self.primary_color)
            
            # Header
            pdf.set_fill_color(*primary_rgb)
            pdf.rect(0, 0, 210, 40, 'F')
            
            pdf.set_text_color(255, 255, 255)
            pdf.set_font('Helvetica', 'B', 24)
            pdf.set_xy(10, 12)
            pdf.cell(190, 10, self.company_name, align='C')
            
            pdf.set_font('Helvetica', '', 12)
            pdf.set_xy(10, 25)
            pdf.cell(190, 10, 'Travel Quote', align='C')
            
            # Reset text color
            pdf.set_text_color(0, 0, 0)
            
            # Quote details
            pdf.set_xy(10, 50)
            pdf.set_font('Helvetica', 'B', 14)
            pdf.cell(190, 10, f"Quote: {quote_data.get('quote_id', 'N/A')}")
            
            pdf.set_font('Helvetica', '', 11)
            pdf.set_xy(10, 62)
            pdf.cell(190, 7, f"Customer: {customer_data.get('name', 'N/A')}")
            pdf.set_xy(10, 69)
            pdf.cell(190, 7, f"Email: {customer_data.get('email', 'N/A')}")
            pdf.set_xy(10, 76)
            pdf.cell(190, 7, f"Destination: {quote_data.get('destination', 'N/A')}")
            pdf.set_xy(10, 83)
            pdf.cell(190, 7, f"Dates: {quote_data.get('check_in_date', 'N/A')} to {quote_data.get('check_out_date', 'N/A')}")
            pdf.set_xy(10, 90)
            pdf.cell(190, 7, f"Guests: {quote_data.get('adults', 0)} Adults, {quote_data.get('children', 0)} Children")
            
            # Hotels section
            pdf.set_xy(10, 105)
            pdf.set_font('Helvetica', 'B', 14)
            pdf.set_text_color(*primary_rgb)
            pdf.cell(190, 10, 'Accommodation Options')
            pdf.set_text_color(0, 0, 0)
            
            y_position = 118
            
            for i, hotel in enumerate(hotels, 1):
                if y_position > 250:
                    pdf.add_page()
                    y_position = 20
                
                # Hotel box
                pdf.set_fill_color(248, 249, 250)
                pdf.rect(10, y_position - 3, 190, 45, 'F')
                
                # Hotel name
                pdf.set_font('Helvetica', 'B', 12)
                pdf.set_xy(15, y_position)
                hotel_name = hotel.get('hotel_name', 'Hotel')
                rating = hotel.get('hotel_rating', '')
                pdf.cell(180, 7, f"Option {i}: {hotel_name} ({rating})")
                
                # Details
                pdf.set_font('Helvetica', '', 10)
                pdf.set_xy(15, y_position + 8)
                pdf.cell(90, 6, f"Room: {hotel.get('room_type', 'Standard')}")
                pdf.set_xy(105, y_position + 8)
                pdf.cell(90, 6, f"Meal Plan: {hotel.get('meal_plan', 'N/A')}")
                
                # Pricing
                pdf.set_xy(15, y_position + 16)
                total_price = hotel.get('total_price', 0)
                pdf.cell(90, 6, f"Per Person: {self.currency} {hotel.get('price_per_person', 0):,.0f}")
                
                pdf.set_font('Helvetica', 'B', 11)
                pdf.set_xy(15, y_position + 24)
                pdf.set_text_color(*primary_rgb)
                pdf.cell(90, 6, f"Total: {self.currency} {total_price:,.0f}")
                pdf.set_text_color(0, 0, 0)
                
                # Transfers
                pdf.set_font('Helvetica', '', 9)
                pdf.set_xy(15, y_position + 32)
                transfers = hotel.get('transfers_total', 0)
                pdf.cell(180, 5, f"(Includes transfers: {self.currency} {transfers:,.0f})")
                
                y_position += 52
            
            # Footer
            pdf.set_y(-30)
            pdf.set_font('Helvetica', 'I', 9)
            pdf.set_text_color(128, 128, 128)
            pdf.cell(0, 10, f'Quote generated by {self.company_name}', align='C')
            pdf.set_y(-22)
            pdf.cell(0, 10, 'Prices subject to availability. Valid for 7 days.', align='C')
            
            # Output
            pdf_bytes = pdf.output()
            
            logger.info(f"✅ PDF generated with fpdf2: {len(pdf_bytes)} bytes")
            return bytes(pdf_bytes)
            
        except Exception as e:
            logger.error(f"fpdf2 PDF generation failed: {e}")
            import traceback
            traceback.print_exc()
            return b""

    def generate_invoice_pdf(
        self,
        invoice_data: Dict[str, Any],
        items: list,
        customer_data: Dict[str, Any]
    ) -> bytes:
        """
        Generate an invoice PDF
        
        Args:
            invoice_data: Invoice information
            items: Line items
            customer_data: Customer information
            
        Returns:
            PDF as bytes
        """
        if FPDF_AVAILABLE:
            return self._generate_invoice_fpdf(invoice_data, items, customer_data)
        return b""

    def _generate_invoice_fpdf(
        self,
        invoice_data: Dict[str, Any],
        items: list,
        customer_data: Dict[str, Any]
    ) -> bytes:
        """
        Generate a comprehensive invoice PDF using fpdf2
        Based on Nova Invoice template layout

        Args:
            invoice_data: Invoice information including:
                - invoice_id: Invoice number
                - quote_id: Related quote ID
                - created_at: Invoice date
                - due_date: Payment due date
                - total_amount: Total amount
                - currency: Currency code
                - notes: Additional notes
                - trip_details: Optional dict with destination, check_in, check_out, nights
                - travelers: Optional list of traveler details
                - room_type: Room type
                - meal_plan: Meal plan/basis
                - price_includes: List of inclusions
            items: List of line items [{description, quantity, unit_price, amount}]
            customer_data: Customer information (name, email, phone)

        Returns:
            PDF as bytes
        """
        try:
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=25)
            pdf.add_page()

            def sanitize_text(text):
                """Remove or replace unicode characters not supported by Helvetica"""
                if not text:
                    return ''
                text = str(text)
                # Replace unicode stars with asterisks
                text = text.replace('★', '*').replace('☆', '*')
                # Replace other common unicode characters
                text = text.replace('✓', 'v').replace('✗', 'x').replace('•', '-')
                text = text.replace('–', '-').replace('—', '-')
                text = text.replace('"', '"').replace('"', '"')
                text = text.replace(''', "'").replace(''', "'")
                # Remove any remaining non-ASCII characters
                return ''.join(c if ord(c) < 128 else '' for c in text)

            def hex_to_rgb(hex_color):
                hex_color = hex_color.lstrip('#')
                return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

            primary_rgb = hex_to_rgb(self.primary_color)

            # ==================== COMPANY HEADER (Right-aligned) ====================
            # Company logo/name area
            pdf.set_font('Helvetica', 'B', 16)
            pdf.set_text_color(*primary_rgb)
            pdf.set_xy(100, 10)
            pdf.cell(100, 8, sanitize_text(self.company_name), align='R')

            # Company details
            pdf.set_font('Helvetica', '', 9)
            pdf.set_text_color(80, 80, 80)

            company_address = getattr(self.config, 'company_address', None) or ''
            company_city = getattr(self.config, 'company_city', None) or ''
            company_country = getattr(self.config, 'company_country', None) or 'South Africa'
            vat_number = getattr(self.config, 'vat_number', None) or ''
            reg_number = getattr(self.config, 'registration_number', None) or ''
            company_phone = getattr(self.config, 'support_phone', None) or ''
            company_website = getattr(self.config, 'website', None) or ''

            y_header = 20
            if company_address:
                pdf.set_xy(100, y_header)
                pdf.cell(100, 5, company_address, align='R')
                y_header += 5
            if company_city:
                pdf.set_xy(100, y_header)
                pdf.cell(100, 5, f"{company_city}, {company_country}", align='R')
                y_header += 5
            if vat_number:
                pdf.set_xy(100, y_header)
                pdf.cell(100, 5, f"VAT No. {vat_number}", align='R')
                y_header += 5
            if reg_number:
                pdf.set_xy(100, y_header)
                pdf.cell(100, 5, f"Reg Nr. {reg_number}", align='R')
                y_header += 5
            if company_phone:
                pdf.set_xy(100, y_header)
                pdf.cell(100, 5, f"Tel: {company_phone}", align='R')
                y_header += 5
            if company_website:
                pdf.set_xy(100, y_header)
                pdf.cell(100, 5, company_website, align='R')

            # ==================== INVOICE TITLE ====================
            pdf.set_font('Helvetica', 'B', 24)
            pdf.set_text_color(*primary_rgb)
            pdf.set_xy(10, 15)
            pdf.cell(80, 10, 'INVOICE')

            # Invoice number
            pdf.set_font('Helvetica', '', 11)
            pdf.set_text_color(0, 0, 0)
            invoice_id = invoice_data.get('invoice_id', 'N/A')
            pdf.set_xy(10, 28)
            pdf.cell(80, 6, f"Invoice #: {invoice_id}")

            created_at = invoice_data.get('created_at', '')
            if created_at and 'T' in str(created_at):
                created_at = str(created_at).split('T')[0]
            pdf.set_xy(10, 35)
            pdf.cell(80, 6, f"Date: {created_at}")

            due_date = invoice_data.get('due_date', '')
            if due_date and 'T' in str(due_date):
                due_date = str(due_date).split('T')[0]
            pdf.set_xy(10, 42)
            pdf.cell(80, 6, f"Due Date: {due_date}")

            # Divider line
            pdf.set_draw_color(*primary_rgb)
            pdf.line(10, 55, 200, 55)

            # ==================== CUSTOMER SECTION ====================
            y_pos = 62

            pdf.set_font('Helvetica', 'B', 10)
            pdf.set_text_color(*primary_rgb)
            pdf.set_xy(10, y_pos)
            pdf.cell(40, 6, 'BILL TO:')

            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Helvetica', '', 10)

            pdf.set_xy(10, y_pos + 8)
            pdf.cell(90, 5, f"Name: {customer_data.get('name', 'N/A')}")
            pdf.set_xy(10, y_pos + 14)
            pdf.cell(90, 5, f"Email: {customer_data.get('email', 'N/A')}")
            if customer_data.get('phone'):
                pdf.set_xy(10, y_pos + 20)
                pdf.cell(90, 5, f"Phone: {customer_data.get('phone', '')}")

            y_pos += 32

            # ==================== LINE ITEMS TABLE ====================
            # Table header
            pdf.set_fill_color(*primary_rgb)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font('Helvetica', 'B', 9)
            pdf.set_xy(10, y_pos)
            pdf.cell(10, 8, '#', border=0, fill=True, align='C')
            pdf.cell(35, 8, 'Destination', border=0, fill=True)
            pdf.cell(70, 8, 'Description', border=0, fill=True)
            pdf.cell(25, 8, 'Unit Price', border=0, fill=True, align='R')
            pdf.cell(15, 8, 'Qty', border=0, fill=True, align='C')
            pdf.cell(35, 8, 'Total', border=0, fill=True, align='R')

            y_pos += 8
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Helvetica', '', 9)

            subtotal = 0
            row_fill = False

            for i, item in enumerate(items, 1):
                if y_pos > 220:
                    pdf.add_page()
                    y_pos = 20

                if row_fill:
                    pdf.set_fill_color(248, 249, 250)
                else:
                    pdf.set_fill_color(255, 255, 255)

                destination = sanitize_text(str(item.get('destination', '')))[:20]
                description = sanitize_text(str(item.get('description', '')))[:40]
                unit_price = float(item.get('unit_price', item.get('amount', 0)))
                quantity = int(item.get('quantity', 1))
                amount = float(item.get('amount', unit_price * quantity))
                subtotal += amount

                pdf.set_xy(10, y_pos)
                pdf.cell(10, 7, str(i), border=0, fill=True, align='C')
                pdf.cell(35, 7, destination, border=0, fill=True)
                pdf.cell(70, 7, description, border=0, fill=True)
                pdf.cell(25, 7, f"{self.currency} {unit_price:,.0f}", border=0, fill=True, align='R')
                pdf.cell(15, 7, str(quantity), border=0, fill=True, align='C')
                pdf.cell(35, 7, f"{self.currency} {amount:,.0f}", border=0, fill=True, align='R')

                y_pos += 7
                row_fill = not row_fill

            # ==================== TRIP DETAILS (Below items) ====================
            trip_details = invoice_data.get('trip_details', {})
            destination = trip_details.get('destination') or invoice_data.get('destination', '')
            check_in = trip_details.get('check_in') or invoice_data.get('check_in_date', '')
            check_out = trip_details.get('check_out') or invoice_data.get('check_out_date', '')
            room_type = invoice_data.get('room_type', '')
            meal_plan = invoice_data.get('meal_plan', '')
            price_includes = invoice_data.get('price_includes', [])

            if check_in or check_out or room_type or meal_plan:
                y_pos += 5
                pdf.set_font('Helvetica', '', 9)
                pdf.set_text_color(80, 80, 80)

                if check_in:
                    pdf.set_xy(15, y_pos)
                    pdf.cell(180, 5, f"Check in: {check_in}")
                    y_pos += 5
                if check_out:
                    pdf.set_xy(15, y_pos)
                    pdf.cell(180, 5, f"Check out: {check_out}")
                    y_pos += 5
                if room_type:
                    pdf.set_xy(15, y_pos)
                    pdf.cell(180, 5, f"Room Type: {sanitize_text(room_type)}")
                    y_pos += 5
                if meal_plan:
                    pdf.set_xy(15, y_pos)
                    pdf.cell(180, 5, f"Meal Basis: {sanitize_text(meal_plan)}")
                    y_pos += 5

                # Price Includes
                if price_includes:
                    y_pos += 3
                    pdf.set_xy(15, y_pos)
                    pdf.set_font('Helvetica', 'B', 9)
                    pdf.cell(180, 5, "Price Includes:")
                    y_pos += 5
                    pdf.set_font('Helvetica', '', 9)
                    for inclusion in price_includes:
                        pdf.set_xy(20, y_pos)
                        pdf.cell(175, 5, f"- {sanitize_text(inclusion)}")
                        y_pos += 5

            pdf.set_text_color(0, 0, 0)

            # ==================== TRAVELERS ====================
            travelers = invoice_data.get('travelers', [])
            if travelers:
                y_pos += 8
                if y_pos > 230:
                    pdf.add_page()
                    y_pos = 20

                pdf.set_font('Helvetica', 'B', 9)
                pdf.set_text_color(*primary_rgb)
                pdf.set_xy(10, y_pos)
                pdf.cell(190, 6, 'TRAVELER DETAILS (Names/DOB as per passports)')

                y_pos += 7
                pdf.set_text_color(0, 0, 0)
                pdf.set_font('Helvetica', '', 9)

                for i, traveler in enumerate(travelers, 1):
                    if y_pos > 250:
                        pdf.add_page()
                        y_pos = 20

                    name = sanitize_text(traveler.get('name', f'Traveler {i}'))
                    traveler_type = sanitize_text(traveler.get('type', 'Adult'))
                    passport = sanitize_text(traveler.get('passport_number', ''))
                    dob = sanitize_text(traveler.get('date_of_birth', ''))
                    nationality = sanitize_text(traveler.get('nationality', ''))

                    info = f"{i}. {name} ({traveler_type})"
                    if dob:
                        info += f" - DOB: {dob}"
                    if passport:
                        info += f" - Passport: {passport}"
                    if nationality:
                        info += f" - {nationality}"

                    pdf.set_xy(15, y_pos)
                    pdf.cell(180, 5, info)
                    y_pos += 5

            # ==================== TOTALS ====================
            y_pos += 10
            if y_pos > 240:
                pdf.add_page()
                y_pos = 20

            # Divider
            pdf.set_draw_color(*primary_rgb)
            pdf.line(120, y_pos, 200, y_pos)

            y_pos += 5
            pdf.set_font('Helvetica', '', 10)
            pdf.set_xy(120, y_pos)
            pdf.cell(50, 6, 'SubTotal:', align='R')
            pdf.cell(30, 6, f"{self.currency} {subtotal:,.0f}", align='R')

            # VAT (if applicable)
            vat_rate = getattr(self.config, 'vat_rate', 0)
            vat_amount = subtotal * (vat_rate / 100) if vat_rate else 0

            if vat_amount > 0:
                y_pos += 6
                pdf.set_xy(120, y_pos)
                pdf.cell(50, 6, f'VAT ({vat_rate}%):', align='R')
                pdf.cell(30, 6, f"{self.currency} {vat_amount:,.0f}", align='R')

            total = subtotal + vat_amount

            # Total
            y_pos += 8
            pdf.set_fill_color(*primary_rgb)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font('Helvetica', 'B', 12)
            pdf.set_xy(120, y_pos)
            pdf.cell(50, 10, 'TOTAL:', border=0, fill=True, align='R')
            pdf.cell(30, 10, f"{self.currency} {total:,.0f}", border=0, fill=True, align='R')
            pdf.set_text_color(0, 0, 0)

            y_pos += 18

            # ==================== NOTES / DISCLAIMERS ====================
            notes = invoice_data.get('notes', '')
            if y_pos > 200:
                pdf.add_page()
                y_pos = 20

            pdf.set_font('Helvetica', 'I', 8)
            pdf.set_text_color(100, 100, 100)
            pdf.set_xy(10, y_pos)
            pdf.multi_cell(190, 4, "PLEASE NOTE: ALL QUOTES ARE SUBJECT TO RATE OF EXCHANGE FLUCTUATIONS. FULL PAYMENT SECURES THIS RATE. PLEASE CALL US FOR UPDATED INVOICE AMOUNT BEFORE MAKING FINAL PAYMENT.")
            y_pos += 14

            pdf.set_xy(10, y_pos)
            pdf.multi_cell(190, 4, "Families travelling with Children: The New Immigration Regulation dictates that as from 01 June 2015 children under the age of 18yrs old require UNABRIDGED BIRTH CERTIFICATES, along with their passports, when travelling. Should you be travelling with/making a reservation for children, please ensure that you apply for these certificates timeously. All Passports must be valid for at least 6 months after your return to South Africa and have at least 2 or more blank pages.")
            y_pos += 18

            if notes:
                pdf.set_xy(10, y_pos)
                pdf.multi_cell(190, 4, f"Notes: {sanitize_text(notes)}")
                y_pos += 10

            # ==================== BANKING DETAILS (Nova Template Layout) ====================
            y_pos += 5
            if y_pos > 230:
                pdf.add_page()
                y_pos = 20

            # Draw a light separator line
            pdf.set_draw_color(200, 200, 200)
            pdf.line(10, y_pos - 2, 200, y_pos - 2)

            # Get banking configuration (use 'or' to handle None values)
            bank_name = getattr(self.config, 'bank_name', None) or 'First National Bank'
            bank_zar_account = getattr(self.config, 'bank_account_number', None) or ''
            bank_zar_branch = getattr(self.config, 'bank_branch_code', None) or ''
            bank_usd_account = getattr(self.config, 'bank_usd_account', None) or ''
            bank_usd_branch = getattr(self.config, 'bank_usd_branch', None) or ''
            bank_eur_account = getattr(self.config, 'bank_eur_account', None) or ''
            bank_eur_branch = getattr(self.config, 'bank_eur_branch', None) or ''
            swift_code = getattr(self.config, 'bank_swift_code', None) or ''
            ref_prefix = getattr(self.config, 'payment_reference_prefix', None) or 'AFS'
            fax_number = getattr(self.config, 'fax_number', None) or ''
            primary_email = getattr(self.config, 'primary_email', None) or ''

            # Row 1: Company name (left) | Bank name (right)
            pdf.set_font('Helvetica', 'B', 8)
            pdf.set_text_color(0, 0, 0)
            pdf.set_xy(10, y_pos)
            pdf.cell(80, 4, self.company_name)

            pdf.set_xy(100, y_pos)
            pdf.cell(100, 4, bank_name, align='R')

            y_pos += 5
            pdf.set_font('Helvetica', '', 8)

            # Row 2: Phone (left) | ZAR Account (right)
            if company_phone:
                pdf.set_xy(10, y_pos)
                pdf.cell(80, 4, f"Tel: {company_phone}")

            if bank_zar_account:
                pdf.set_xy(100, y_pos)
                pdf.cell(100, 4, f"ZAR Account: {bank_zar_account}  Branch: {bank_zar_branch}", align='R')

            y_pos += 4

            # Row 3: Fax (left) | USD Account (right)
            if fax_number:
                pdf.set_xy(10, y_pos)
                pdf.cell(80, 4, f"Fax: {fax_number}")

            if bank_usd_account:
                pdf.set_xy(100, y_pos)
                pdf.cell(100, 4, f"USD Account: {bank_usd_account}  Branch: {bank_usd_branch}", align='R')

            y_pos += 4

            # Row 4: Email (left) | EUR Account (right)
            if primary_email:
                pdf.set_xy(10, y_pos)
                pdf.cell(80, 4, primary_email)

            if bank_eur_account:
                pdf.set_xy(100, y_pos)
                pdf.cell(100, 4, f"EUR Account: {bank_eur_account}  Branch: {bank_eur_branch}", align='R')

            y_pos += 4

            # Row 5: Website (left) | SWIFT Code (right)
            if company_website:
                pdf.set_xy(10, y_pos)
                pdf.cell(80, 4, company_website)

            if swift_code:
                pdf.set_xy(100, y_pos)
                pdf.cell(100, 4, f"SWIFT Code: {swift_code} (for international payments)", align='R')

            y_pos += 7

            # Payment reference instruction (centered, highlighted)
            pdf.set_font('Helvetica', 'B', 9)
            pdf.set_text_color(*primary_rgb)
            pdf.set_xy(10, y_pos)
            pdf.cell(190, 5, f"PLEASE USE THE INV. ({ref_prefix}) NUMBER AS THE BENEFICIARY REFERENCE WHEN MAKING PAYMENT", align='C')

            pdf_bytes = pdf.output()
            logger.info(f"✅ Invoice PDF generated (Nova template): {len(pdf_bytes)} bytes")
            return bytes(pdf_bytes)

        except Exception as e:
            logger.error(f"Invoice PDF generation failed: {e}")
            import traceback
            traceback.print_exc()
            return b""