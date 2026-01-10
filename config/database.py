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
    """Centralized database table name management"""
    
    def __init__(self, config: ClientConfig):
        """
        Initialize with client configuration
        
        Args:
            config: ClientConfig instance
        """
        self.config = config
        self.project = config.gcp_project_id
        self.dataset = config.dataset_name
    
    # ==================== BigQuery Tables ====================
    
    @property
    def hotel_rates(self) -> str:
        """Hotel pricing rates table"""
        return f"`{self.project}.{self.dataset}.hotel_rates`"
    
    @property
    def hotel_media(self) -> str:
        """Hotel images and descriptions"""
        return f"`{self.project}.{self.dataset}.hotel_media`"
    
    @property
    def hotel_settings(self) -> str:
        """Hotel configuration settings"""
        return f"`{self.project}.{self.dataset}.hotel_settings`"
    
    @property
    def flight_prices(self) -> str:
        """Flight pricing data"""
        return f"`{self.project}.{self.dataset}.flight_prices`"
    
    @property
    def consultants(self) -> str:
        """Sales consultants table"""
        return f"`{self.project}.{self.dataset}.consultants`"
    
    @property
    def quotes(self) -> str:
        """Generated quotes table"""
        return f"`{self.project}.{self.dataset}.quotes`"
    
    @property
    def cost_metrics(self) -> str:
        """AI cost tracking metrics"""
        return f"`{self.project}.{self.dataset}.cost_metrics`"
    
    @property
    def document_metadata(self) -> str:
        """RAG document metadata"""
        return f"`{self.project}.{self.dataset}.document_metadata`"
    
    @property
    def document_indexing_status(self) -> str:
        """Document indexing status tracking"""
        return f"`{self.project}.{self.dataset}.document_indexing_status`"
    
    # ==================== Helper Methods ====================
    
    def get_table(self, table_name: str) -> str:
        """
        Get fully qualified table name
        
        Args:
            table_name: Simple table name (e.g., 'hotel_rates')
        
        Returns:
            Fully qualified table name with backticks
        """
        return f"`{self.project}.{self.dataset}.{table_name}`"
    
    def __repr__(self) -> str:
        return f"DatabaseTables(project='{self.project}', dataset='{self.dataset}')"


class SupabaseTables:
    """Supabase table name constants"""
    
    # These don't need client-specific naming
    EMPLOYEES = "employees"
    INBOUND_TICKETS = "inbound_tickets"
    HELPDESK_CONVERSATIONS = "helpdesk_conversations"
    OUTBOUND_CALL_QUEUE = "outbound_call_queue"
    CALL_RECORDS = "call_records"
    KNOWLEDGE_BASE_FILES = "knowledge_base_files"
