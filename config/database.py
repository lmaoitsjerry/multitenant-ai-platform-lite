"""
Database Table Name Abstraction

Provides centralized table name management for BigQuery and Supabase.
All table references should go through this module.

Usage:
    from config.database import DatabaseTables
    from config.loader import ClientConfig
    
    config = ClientConfig('africastay')
    db = DatabaseTables(config)
    
    query = f"SELECT * FROM `{db.hotel_rates}`"
"""

from config.loader import ClientConfig


class DatabaseTables:
    """Centralized database table name management

    Uses two datasets:
    - shared_pricing_dataset: For hotel rates, pricing, flights (same for all tenants)
    - dataset (tenant-specific): For quotes, analytics, cost metrics (per-tenant isolation)
    """

    def __init__(self, config: ClientConfig):
        """
        Initialize with client configuration

        Args:
            config: ClientConfig instance
        """
        self.config = config
        self.project = config.gcp_project_id
        self.dataset = config.dataset_name  # Tenant-specific
        self.pricing_dataset = config.shared_pricing_dataset  # Shared across tenants

    # ==================== Shared Pricing Tables (All Tenants) ====================
    # These tables use the shared_pricing_dataset (default: africastay_analytics)

    @property
    def hotel_rates(self) -> str:
        """Hotel pricing rates table (SHARED across all tenants)"""
        return f"`{self.project}.{self.pricing_dataset}.hotel_rates`"

    @property
    def hotel_media(self) -> str:
        """Hotel images and descriptions (SHARED across all tenants)"""
        return f"`{self.project}.{self.pricing_dataset}.hotel_media`"

    @property
    def hotel_settings(self) -> str:
        """Hotel configuration settings (SHARED across all tenants)"""
        return f"`{self.project}.{self.pricing_dataset}.hotel_settings`"

    @property
    def flight_prices(self) -> str:
        """Flight pricing data (SHARED across all tenants)"""
        return f"`{self.project}.{self.pricing_dataset}.flight_prices`"

    # ==================== Tenant-Specific Tables ====================
    # These tables use the tenant's own dataset for data isolation

    @property
    def consultants(self) -> str:
        """Sales consultants table (tenant-specific)"""
        return f"`{self.project}.{self.dataset}.consultants`"

    @property
    def quotes(self) -> str:
        """Generated quotes table (tenant-specific)"""
        return f"`{self.project}.{self.dataset}.quotes`"

    @property
    def cost_metrics(self) -> str:
        """AI cost tracking metrics (tenant-specific)"""
        return f"`{self.project}.{self.dataset}.cost_metrics`"

    @property
    def document_metadata(self) -> str:
        """RAG document metadata (tenant-specific)"""
        return f"`{self.project}.{self.dataset}.document_metadata`"

    @property
    def document_indexing_status(self) -> str:
        """Document indexing status tracking (tenant-specific)"""
        return f"`{self.project}.{self.dataset}.document_indexing_status`"

    # ==================== Helper Methods ====================

    def get_table(self, table_name: str) -> str:
        """
        Get fully qualified table name from tenant dataset

        Args:
            table_name: Simple table name (e.g., 'quotes')

        Returns:
            Fully qualified table name with backticks
        """
        return f"`{self.project}.{self.dataset}.{table_name}`"

    def get_shared_table(self, table_name: str) -> str:
        """
        Get fully qualified table name from shared pricing dataset

        Args:
            table_name: Simple table name (e.g., 'hotel_rates')

        Returns:
            Fully qualified table name with backticks
        """
        return f"`{self.project}.{self.pricing_dataset}.{table_name}`"
    
    def __repr__(self) -> str:
        return f"DatabaseTables(project='{self.project}', tenant_dataset='{self.dataset}', pricing_dataset='{self.pricing_dataset}')"


class SupabaseTables:
    """Supabase table name constants"""
    
    # These don't need client-specific naming
    EMPLOYEES = "employees"
    INBOUND_TICKETS = "inbound_tickets"
    HELPDESK_CONVERSATIONS = "helpdesk_conversations"
    OUTBOUND_CALL_QUEUE = "outbound_call_queue"
    CALL_RECORDS = "call_records"
    KNOWLEDGE_BASE_FILES = "knowledge_base_files"
