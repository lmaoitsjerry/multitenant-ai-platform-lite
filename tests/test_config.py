
import unittest
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.loader import ClientConfig
from config.database import DatabaseTables

class TestConfiguration(unittest.TestCase):
    def test_missing_client(self):
        """Test that loading a non-existent client raises an error"""
        with self.assertRaises(Exception):
            ClientConfig('non_existent_client')

if __name__ == '__main__':
    unittest.main()
