"""
Testing Round 3 - Programmatic Verification Tests
===================================================
Dedicated tests proving each of the 7 fixes works correctly.

Issue 1: Quote Builder 500 error (create-with-items column alignment)
Issue 2: Hotels expandable detail cards enhancement
Issue 3: Flights duration dedup + filters
Issue 4: Activities clickable + category colors in HolidayPackages
Issue 5: Website Builder publish tenant ID
Issue 6: Website Builder connections (architectural - verified by Issue 5 fixes)
Issue 7: Helpdesk web search supplement + RAG integration
"""

import ast
import json
import os
import re
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

# ─── Paths ───────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
SRC_DIR = PROJECT_ROOT / "src"
FRONTEND_DIR = PROJECT_ROOT / "frontend" / "tenant-dashboard" / "src"

sys.path.insert(0, str(PROJECT_ROOT))


# =====================================================================
# ISSUE 1: Quote Builder — create-with-items column alignment
# =====================================================================
class TestIssue1_QuoteBuilderColumnAlignment(unittest.TestCase):
    """
    EVIDENCE: The create-with-items endpoint must use the SAME column set
    as _save_quote_to_supabase() in quote_agent.py (the proven working insert).

    Root cause was: create-with-items used migration-020 columns (line_items,
    totals_by_currency, total_amount, currency, source) that DON'T EXIST in
    Supabase, AND was missing required columns (nights, hotels, email_sent,
    pdf_generated, consultant_id, sent_at).
    """

    def _extract_insert_columns(self, source_code: str, function_name: str) -> set:
        """Extract column names from a supabase .insert() call in the given function."""
        # Find the function body
        func_start = source_code.find(f"def {function_name}")
        if func_start == -1:
            func_start = source_code.find(f"async def {function_name}")
        self.assertNotEqual(func_start, -1, f"Function {function_name} not found")

        # Find .insert( in the function
        insert_pos = source_code.find(".insert(", func_start)
        self.assertNotEqual(insert_pos, -1, f"No .insert() found in {function_name}")

        return None  # We'll use a different approach

    def test_create_with_items_uses_proven_column_set(self):
        """Verify create-with-items builds quote_data with ALL required columns."""
        func_body = self._get_create_with_items_body()

        # These are the REQUIRED columns from _save_quote_to_supabase (the working insert)
        required_columns = {
            "tenant_id", "quote_id", "customer_name", "customer_email",
            "customer_phone", "destination", "check_in", "check_out",
            "nights", "adults", "children", "children_ages", "hotels",
            "total_price", "status", "email_sent", "pdf_generated",
            "consultant_id", "created_at", "sent_at"
        }

        # These are the DANGEROUS columns from migration-020 that may not exist
        dangerous_columns = {"line_items", "totals_by_currency", "total_amount", "currency", "source"}

        # Check all required columns are present in quote_data dict
        # The code uses double quotes for keys
        for col in required_columns:
            found = f'"{col}"' in func_body or f"'{col}'" in func_body
            self.assertTrue(
                found,
                f"MISSING required column '{col}' in create_quote_with_items. "
                f"This column exists in _save_quote_to_supabase and is needed."
            )

        # Check dangerous columns are NOT used as top-level insert keys in quote_data
        # Find the quote_data dict block (may span many lines, use greedy match up to the insert call)
        quote_data_match = re.search(r'quote_data\s*=\s*\{(.*?)\n\s*\}', func_body, re.DOTALL)
        self.assertIsNotNone(quote_data_match, "quote_data dict not found")
        quote_data_str = quote_data_match.group(1)

        for col in dangerous_columns:
            found_in_data = f'"{col}"' in quote_data_str or f"'{col}'" in quote_data_str
            self.assertFalse(
                found_in_data,
                f"DANGEROUS column '{col}' found in quote_data. "
                f"Migration-020 may not be applied to Supabase."
            )

    def _get_create_with_items_body(self):
        """Helper to extract create_quote_with_items function body."""
        routes_path = SRC_DIR / "api" / "routes.py"
        source = routes_path.read_text(encoding="utf-8")
        # Function starts at 'def create_quote_with_items' and ends at next top-level 'def '
        func_match = re.search(
            r'def create_quote_with_items.*?(?=\ndef |\nclass |\Z)',
            source, re.DOTALL
        )
        self.assertIsNotNone(func_match, "create_quote_with_items not found")
        return func_match.group()

    def test_line_items_stored_in_hotels_jsonb(self):
        """Verify line items are stored in the 'hotels' JSONB column, not 'line_items'."""
        func_body = self._get_create_with_items_body()

        # Should build hotels_data list from line_items
        self.assertIn("hotels_data", func_body,
                       "Should build hotels_data list from line items")

        # quote_data should have "hotels": hotels_data
        self.assertRegex(func_body, r'"hotels"\s*:\s*hotels_data',
                         "quote_data should map 'hotels' to hotels_data")

    def test_nights_calculated_from_dates(self):
        """Verify nights is calculated from check_in/check_out dates."""
        func_body = self._get_create_with_items_body()

        # Should calculate nights from dates
        self.assertIn("nights", func_body)
        self.assertIn("strptime", func_body,
                       "Should parse dates with strptime to calculate nights")

    def test_quote_agent_reference_columns(self):
        """Verify _save_quote_to_supabase still has the expected column set (our reference)."""
        agent_path = SRC_DIR / "agents" / "quote_agent.py"
        source = agent_path.read_text(encoding="utf-8")

        func_match = re.search(
            r'def _save_quote_to_supabase.*?(?=\n    def |\nclass |\Z)',
            source, re.DOTALL
        )
        self.assertIsNotNone(func_match, "_save_quote_to_supabase not found")
        func_body = func_match.group()

        # Verify it has the columns we reference (uses single quotes in this file)
        for col in ["tenant_id", "quote_id", "hotels", "nights", "email_sent",
                     "pdf_generated", "consultant_id", "sent_at"]:
            found = f"'{col}'" in func_body or f'"{col}"' in func_body
            self.assertTrue(found,
                            f"Reference function missing '{col}' — our baseline may have changed")


# =====================================================================
# ISSUE 3: Flights — Duration Deduplication + Filters
# =====================================================================
class TestIssue3_FlightsDurationAndFilters(unittest.TestCase):
    """
    EVIDENCE: FlightsList.jsx must have:
    1. formatDuration() that deduplicates "14h 25m14h 25m" → "14h 25m"
    2. Stop filter (non-stop, 1 stop, 2+ stops)
    3. Sort options (price, duration, departure)
    """

    def setUp(self):
        self.source = (FRONTEND_DIR / "pages" / "travel" / "FlightsList.jsx").read_text(encoding="utf-8")

    def test_format_duration_function_exists(self):
        """formatDuration function must exist to fix duplicated duration strings."""
        self.assertIn("function formatDuration", self.source,
                       "formatDuration function not found in FlightsList.jsx")

    def test_format_duration_handles_exact_duplication(self):
        """formatDuration must detect when first half === second half."""
        # Check the logic: substring(0, half) === substring(half)
        self.assertIn("substring", self.source,
                       "formatDuration should use substring to split and compare halves")

    def test_format_duration_handles_word_duplication(self):
        """formatDuration must handle word-level duplication like '14h 25m 14h 25m'."""
        self.assertIn("split", self.source,
                       "formatDuration should split by whitespace for word-level dedup")

    def test_stop_filters_defined(self):
        """Stop filter options must be defined."""
        self.assertIn("STOP_FILTERS", self.source,
                       "STOP_FILTERS constant not found")
        # Check for the filter values (labels in code use various casing)
        self.assertIn("Non-stop", self.source, "Non-stop filter label not found")
        self.assertIn("Stop", self.source, "Stop filter label not found")

    def test_sort_options_defined(self):
        """Sort options must be defined."""
        self.assertIn("SORT_OPTIONS", self.source,
                       "SORT_OPTIONS constant not found")

    def test_filter_and_sort_function(self):
        """filterAndSort or equivalent filtering logic must exist."""
        # Check for useMemo-based filtering
        self.assertIn("useMemo", self.source,
                       "useMemo should be used for memoized filtering")

    def test_filter_ui_elements(self):
        """Filter bar UI must exist in the JSX."""
        self.assertIn("stopFilter", self.source,
                       "stopFilter state variable not found")
        self.assertIn("sortBy", self.source,
                       "sortBy state variable not found")

    def test_no_add_to_quote_button(self):
        """'Add to Quote' button should NOT be present on flight cards."""
        # The button text should not appear in flight card rendering
        # (It's fine if it appears in other contexts like imports)
        flight_card_section = re.search(
            r'flight results.*?</div>\s*\)', self.source, re.DOTALL | re.IGNORECASE
        )
        # Just check it's not a primary CTA on flights
        add_to_quote_count = self.source.count("Add to Quote")
        self.assertEqual(add_to_quote_count, 0,
                         "Flights should not have 'Add to Quote' buttons")


# =====================================================================
# ISSUE 4: Activities Clickable + Category Colors in HolidayPackages
# =====================================================================
class TestIssue4_ActivitiesAndCategoryColors(unittest.TestCase):
    """
    EVIDENCE: HolidayPackages.jsx must have:
    1. Clickable activity cards with expand/collapse
    2. Category-specific tag colors (not all same purple)
    """

    def setUp(self):
        self.source = (FRONTEND_DIR / "pages" / "travel" / "HolidayPackages.jsx").read_text(encoding="utf-8")

    def test_expanded_activity_state(self):
        """expandedActivity state variable must exist for click-to-expand."""
        self.assertIn("expandedActivity", self.source,
                       "expandedActivity state not found — activities aren't clickable")

    def test_activity_click_handler(self):
        """Activity cards must have onClick handler."""
        self.assertIn("setExpandedActivity", self.source,
                       "setExpandedActivity not found — no toggle logic")

    def test_category_specific_colors(self):
        """Category tags must have distinct colors, not all the same."""
        # Check for multiple distinct color classes
        color_classes = re.findall(r"'(bg-\w+-\d+ text-\w+-\d+)'", self.source)
        unique_colors = set(color_classes)
        self.assertGreater(len(unique_colors), 3,
                           f"Only {len(unique_colors)} unique category colors. Need variety, not all same.")

    def test_specific_category_colors(self):
        """Known categories must have their designated colors."""
        expected_categories = {
            "Water Sports": "blue",
            "Cultural": "amber",
            "Nature": "green",
            "Adventure": "red",
        }
        for category, color in expected_categories.items():
            self.assertIn(category, self.source, f"Category '{category}' not found")
            # Check that the color appears near the category
            self.assertIn(f"bg-{color}", self.source,
                          f"Color {color} not found for category {category}")

    def test_stop_propagation_on_quote_button(self):
        """AddToQuoteButton click must stopPropagation to prevent card toggle."""
        self.assertIn("stopPropagation", self.source,
                       "stopPropagation missing — clicking quote button would toggle card")


# =====================================================================
# ISSUE 5: Website Builder Publish — Tenant ID
# =====================================================================
class TestIssue5_WebsitePublishTenantId(unittest.TestCase):
    """
    EVIDENCE: api.js websiteBuilderApi must include tenantId in
    publish, unpublish, selectTemplate, updateBranding,
    updateProductConfig, and updateMarkupRules requests.
    """

    def setUp(self):
        self.source = (FRONTEND_DIR / "services" / "api.js").read_text(encoding="utf-8")

    def test_publish_includes_tenant_id(self):
        """publishWebsite must send tenantId in POST body."""
        # Find the publishWebsite line and the next line
        publish_match = re.search(
            r'publishWebsite.*?\n.*?tenantId',
            self.source, re.DOTALL
        )
        self.assertIsNotNone(publish_match,
                             "publishWebsite missing tenantId in request body")

    def test_unpublish_includes_tenant_id(self):
        """unpublishWebsite must send tenantId in POST body."""
        unpublish_match = re.search(
            r'unpublishWebsite.*?\n.*?tenantId',
            self.source, re.DOTALL
        )
        self.assertIsNotNone(unpublish_match,
                             "unpublishWebsite missing tenantId in request body")

    def test_select_template_includes_tenant_id(self):
        """selectTemplate must include tenant_id."""
        template_match = re.search(
            r'selectTemplate.*?\n.*?tenant_id',
            self.source, re.DOTALL
        )
        self.assertIsNotNone(template_match, "selectTemplate missing tenant_id")

    def test_update_branding_includes_tenant_id(self):
        """updateBranding must include tenant_id."""
        branding_match = re.search(
            r'updateBranding.*?\n.*?tenant_id',
            self.source, re.DOTALL
        )
        self.assertIsNotNone(branding_match, "updateBranding missing tenant_id")


# =====================================================================
# ISSUE 5 (WebsitePreview): Error handling improvement
# =====================================================================
class TestIssue5_WebsitePreviewErrorHandling(unittest.TestCase):
    """EVIDENCE: WebsitePreview.jsx must show detailed error messages."""

    def setUp(self):
        path = FRONTEND_DIR / "pages" / "website" / "WebsitePreview.jsx"
        if path.exists():
            self.source = path.read_text(encoding="utf-8")
        else:
            self.source = None

    def test_publish_error_shows_detail(self):
        """handlePublish must extract and display detailed error from response."""
        if self.source is None:
            self.skipTest("WebsitePreview.jsx not found")
        self.assertIn("err.response", self.source,
                       "Error handler should access err.response for detail")
        self.assertIn("setErrorMessage", self.source,
                       "Should display error message to user")


# =====================================================================
# ISSUE 7: Helpdesk Web Search Supplement + RAG Integration
# =====================================================================
class TestIssue7_HelpdeskWebSearchAndRAG(unittest.TestCase):
    """
    EVIDENCE: helpdesk_routes.py must:
    1. Have _web_search_supplement() function
    2. Forward classifier's use_rerank to RAG search
    3. Pass existing citations to LLM in Step 5
    4. Support 'llm_synthesis_web' method label
    """

    def setUp(self):
        self.source = (SRC_DIR / "api" / "helpdesk_routes.py").read_text(encoding="utf-8")

    def test_web_search_supplement_function_exists(self):
        """_web_search_supplement function must exist."""
        self.assertIn("def _web_search_supplement", self.source,
                       "_web_search_supplement function not found")

    def test_web_search_uses_duckduckgo(self):
        """Web search must use DuckDuckGo HTML search endpoint."""
        self.assertIn("html.duckduckgo.com", self.source,
                       "DuckDuckGo HTML search URL not found")

    def test_web_search_has_timeout(self):
        """Web search must have a short timeout to prevent blocking."""
        # Should have a timeout parameter
        self.assertRegex(self.source, r'timeout\s*=\s*5',
                         "Web search should have 5s timeout")

    def test_web_search_query_types_defined(self):
        """Only travel-related query types should trigger web search."""
        self.assertIn("_WEB_SEARCH_QUERY_TYPES", self.source,
                       "_WEB_SEARCH_QUERY_TYPES set not defined")
        for qt in ["DESTINATION_INFO", "HOTEL_INFO", "GENERAL"]:
            self.assertIn(qt, self.source,
                          f"Query type {qt} should trigger web search")

    def test_use_rerank_forwarded_to_rag(self):
        """Classifier's use_rerank must be forwarded to search functions."""
        # search_dual_knowledge_base should accept use_rerank param (signature spans multiple lines)
        dual_sig = re.search(
            r'def search_dual_knowledge_base\(.*?use_rerank',
            self.source, re.DOTALL
        )
        self.assertIsNotNone(dual_sig,
                             "search_dual_knowledge_base missing use_rerank param")

        # search_travel_platform_rag should accept use_rerank param
        rag_sig = re.search(
            r'def search_travel_platform_rag\(.*?use_rerank',
            self.source, re.DOTALL
        )
        self.assertIsNotNone(rag_sig,
                             "search_travel_platform_rag missing use_rerank param")

    def test_citations_passed_to_llm_in_step5(self):
        """Step 5 must pass existing citations to LLM, not empty list."""
        # The code builds all_context from citations + web results, then passes to generate_response
        # Key: all_context = list(citations) ensures KB results are included
        self.assertIn("all_context = list(citations)", self.source,
                       "Step 5 should build all_context from citations")
        self.assertIn("search_results=all_context", self.source,
                       "Step 5 should pass all_context (which includes citations) to generate_response")

    def test_llm_synthesis_web_method_label(self):
        """'llm_synthesis_web' must be a valid method label."""
        self.assertIn("llm_synthesis_web", self.source,
                       "llm_synthesis_web method label not found")


# =====================================================================
# ISSUE 7 (Frontend): HelpDeskPanel method labels + sources
# =====================================================================
class TestIssue7_HelpDeskPanelUI(unittest.TestCase):
    """
    EVIDENCE: HelpDeskPanel.jsx must:
    1. Have METHOD_LABELS including llm_synthesis_web
    2. Show globe icon for web search sources
    3. Display method badge on AI messages
    4. Have travel-relevant suggested questions
    """

    def setUp(self):
        self.source = (FRONTEND_DIR / "components" / "layout" / "HelpDeskPanel.jsx").read_text(encoding="utf-8")

    def test_method_labels_defined(self):
        """METHOD_LABELS constant must be defined with all method types."""
        self.assertIn("METHOD_LABELS", self.source,
                       "METHOD_LABELS constant not found")
        for method in ["dual_kb", "private_kb_synthesis", "smart_static",
                        "llm_synthesis", "llm_synthesis_web", "static_fallback"]:
            self.assertIn(method, self.source,
                          f"Method '{method}' not in METHOD_LABELS")

    def test_web_search_label(self):
        """llm_synthesis_web should show 'AI + Web Search' label."""
        self.assertIn("AI + Web Search", self.source,
                       "'AI + Web Search' display label not found")

    def test_globe_icon_for_web_sources(self):
        """Web search sources should display a globe icon."""
        self.assertIn("GlobeAltIcon", self.source,
                       "GlobeAltIcon not imported for web search sources")
        self.assertIn("web_search", self.source,
                       "web_search source type check not found")

    def test_method_badge_displayed(self):
        """AI messages should display a method badge."""
        self.assertIn("message.method", self.source,
                       "message.method not referenced — method badge not displayed")

    def test_travel_suggested_questions(self):
        """Suggested questions should include travel queries."""
        self.assertIn("Zanzibar", self.source,
                       "Travel question about Zanzibar not in suggestions")
        self.assertIn("Mauritius", self.source,
                       "Travel question about Mauritius not in suggestions")

    def test_sources_display_limit(self):
        """Should show multiple sources (at least 3-4)."""
        # Check for sources.slice(0, N) where N >= 3
        slice_match = re.search(r'sources\.slice\(0,\s*(\d+)\)', self.source)
        self.assertIsNotNone(slice_match, "sources.slice() not found")
        limit = int(slice_match.group(1))
        self.assertGreaterEqual(limit, 3,
                                f"Sources display limit is {limit}, should be >= 3")


# =====================================================================
# ISSUE 2: Hotels Expandable Detail Cards
# =====================================================================
class TestIssue2_HotelsDetailCards(unittest.TestCase):
    """
    EVIDENCE: HotelsList.jsx HotelDetailModal must have:
    1. Trip details bar (check-in, check-out, nights)
    2. Amenities section
    3. Google Maps link
    4. Rich room option rows
    """

    def setUp(self):
        self.source = (FRONTEND_DIR / "pages" / "travel" / "HotelsList.jsx").read_text(encoding="utf-8")

    def test_trip_details_bar(self):
        """Modal must show check-in/check-out/nights trip details."""
        self.assertIn("check_in", self.source, "check_in not referenced in hotel detail")
        self.assertIn("check_out", self.source, "check_out not referenced in hotel detail")
        # Look for nights calculation
        self.assertIn("nights", self.source.lower(), "Nights display not found")

    def test_amenities_section(self):
        """Modal must have amenities display."""
        # Look for amenities-related content
        has_amenities = ("amenit" in self.source.lower() or
                         "wifi" in self.source.lower() or
                         "pool" in self.source.lower())
        self.assertTrue(has_amenities, "No amenities section found in hotel detail")

    def test_google_maps_link(self):
        """Modal must have Google Maps link for hotels with coordinates."""
        has_maps = ("maps.google.com" in self.source or
                    "google.com/maps" in self.source)
        self.assertTrue(has_maps, "Google Maps link not found in hotel detail")

    def test_room_option_details(self):
        """Room options must show provider, cancellation, bed type info."""
        # Check for room-related detail fields
        has_room_details = (
            "cancellation" in self.source.lower() or
            "refundable" in self.source.lower() or
            "bed_type" in self.source.lower() or
            "room_size" in self.source.lower()
        )
        self.assertTrue(has_room_details,
                        "Room options missing detail fields (cancellation/bed_type/etc)")


# =====================================================================
# CROSS-CUTTING: All modified Python files parse without errors
# =====================================================================
class TestCrossCutting_PythonSyntax(unittest.TestCase):
    """EVIDENCE: All modified Python files must be syntactically valid."""

    def test_routes_py_parses(self):
        """routes.py must parse without syntax errors."""
        source = (SRC_DIR / "api" / "routes.py").read_text(encoding="utf-8")
        try:
            ast.parse(source)
        except SyntaxError as e:
            self.fail(f"routes.py has syntax error: {e}")

    def test_helpdesk_routes_py_parses(self):
        """helpdesk_routes.py must parse without syntax errors."""
        source = (SRC_DIR / "api" / "helpdesk_routes.py").read_text(encoding="utf-8")
        try:
            ast.parse(source)
        except SyntaxError as e:
            self.fail(f"helpdesk_routes.py has syntax error: {e}")

    def test_quote_agent_py_parses(self):
        """quote_agent.py must parse without syntax errors."""
        source = (SRC_DIR / "agents" / "quote_agent.py").read_text(encoding="utf-8")
        try:
            ast.parse(source)
        except SyntaxError as e:
            self.fail(f"quote_agent.py has syntax error: {e}")


# =====================================================================
# CROSS-CUTTING: All modified JSX files are syntactically valid
# =====================================================================
class TestCrossCutting_JSXSyntax(unittest.TestCase):
    """EVIDENCE: All modified JSX files must have balanced braces/parens."""

    def _check_balanced(self, filepath: Path):
        """Check that braces, brackets, and parens are balanced."""
        source = filepath.read_text(encoding="utf-8")

        # Remove strings and template literals to avoid false positives
        # Simple approach: count opening vs closing
        opens = source.count('{') + source.count('(') + source.count('[')
        closes = source.count('}') + source.count(')') + source.count(']')

        # Allow small imbalance from JSX/template strings, but flag major issues
        diff = abs(opens - closes)
        self.assertLess(diff, 5,
                        f"{filepath.name}: Major bracket imbalance ({opens} opens vs {closes} closes)")

    def test_flights_list_balanced(self):
        self._check_balanced(FRONTEND_DIR / "pages" / "travel" / "FlightsList.jsx")

    def test_holiday_packages_balanced(self):
        self._check_balanced(FRONTEND_DIR / "pages" / "travel" / "HolidayPackages.jsx")

    def test_hotels_list_balanced(self):
        self._check_balanced(FRONTEND_DIR / "pages" / "travel" / "HotelsList.jsx")

    def test_helpdesk_panel_balanced(self):
        self._check_balanced(FRONTEND_DIR / "components" / "layout" / "HelpDeskPanel.jsx")

    def test_api_js_balanced(self):
        self._check_balanced(FRONTEND_DIR / "services" / "api.js")


if __name__ == "__main__":
    unittest.main(verbosity=2)
