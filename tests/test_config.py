
import unittest
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.loader import ClientConfig
from config.database import DatabaseTables

class TestConfiguration(unittest.TestCase):
    def setUp(self):
        # Use the example client for testing
        self.client_id = 'example'
        self.config = ClientConfig(self.client_id)

    def test_client_config_loading(self):
        """Test that client config loads correctly"""
        # The client_id passed to constructor matches the folder name 'example'
        # The id inside yaml is 'example_client'
        self.assertEqual(self.config.client_id, 'example') 
        self.assertEqual(self.config.name, 'Example Travel Agency')
        self.assertEqual(self.config.gcp_project_id, 'your-gcp-project-123456')
        self.assertEqual(self.config.dataset_name, 'example_analytics')
        self.assertEqual(self.config.primary_email, 'sales@example.com')

    def test_destinations_loading(self):
        """Test that destinations are loaded correctly"""
        destinations = self.config.destination_names
        self.assertIn('Bali', destinations)
        self.assertIn('Maldives', destinations)
        self.assertTrue(len(destinations) >= 2)

    def test_database_abstraction(self):
        """Test that database tables are correctly abstracted"""
        db = DatabaseTables(self.config)

        # hotel_rates uses shared_pricing_dataset (africastay_analytics)
        expected_rates = '`your-gcp-project-123456.africastay_analytics.hotel_rates`'
        self.assertEqual(db.hotel_rates, expected_rates)

        # consultants uses tenant-specific dataset (example_analytics)
        expected_consultants = '`your-gcp-project-123456.example_analytics.consultants`'
        self.assertEqual(db.consultants, expected_consultants)

    def test_missing_client(self):
        """Test that loading a non-existent client raises an error"""
        with self.assertRaises(Exception):
            ClientConfig('non_existent_client')

if __name__ == '__main__':
    unittest.main()
