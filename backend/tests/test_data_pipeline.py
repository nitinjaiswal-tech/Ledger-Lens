"""Unit and integration tests for the Phase 1 Data Pipeline.
Compatible with standard library unittest and pytest.
"""

import unittest
import numpy as np
import pandas as pd
from pathlib import Path

from app.data.loader import DataLoader
from app.data.cleaner import DataCleaner
from app.data.validators import (
    MPAllocationCleanedRecord,
    MPAllocationRawRecord,
    SummaryTotalsMetadata,
)


class TestDataPipeline(unittest.TestCase):
    """Test suite for data loading, cleaning, validation, and serialization."""

    def setUp(self):
        self.loader = DataLoader()
        self.cleaner = DataCleaner(loader=self.loader)

    def test_loader_raw_files_exist(self):
        """Verify that raw files can be listed and the target file is present."""
        files = self.loader.list_raw_files()
        self.assertIn("Allocated Limit for Honble MPs.csv", files)

    def test_loader_load_raw_csv(self):
        """Verify raw CSV loading preserves 544 rows and original columns."""
        df = self.loader.load_mp_allocations_raw()
        self.assertEqual(df.shape[0], 544)
        self.assertEqual(df.shape[1], 5)
        self.assertIn("Sr. No.", df.columns)
        self.assertIn("Allocated AMOUNT ( ₹ )", df.columns)

    def test_currency_parser(self):
        """Verify robust parsing of Indian currency formats and edge cases."""
        # Standard Indian format
        amt, is_miss, is_inv = DataCleaner.parse_inr_currency("14,70,00,000")
        self.assertEqual(amt, 147000000.0)
        self.assertFalse(is_miss)
        self.assertFalse(is_inv)

        # With Rupee symbol & decimals
        amt, is_miss, is_inv = DataCleaner.parse_inr_currency("₹ 83,33,99,05,622.01")
        self.assertEqual(amt, 83339905622.01)
        self.assertFalse(is_miss)
        self.assertFalse(is_inv)

        # Empty / Missing
        amt, is_miss, is_inv = DataCleaner.parse_inr_currency("")
        self.assertTrue(is_miss)
        amt, is_miss, is_inv = DataCleaner.parse_inr_currency(None)
        self.assertTrue(is_miss)

        # Invalid string
        amt, is_miss, is_inv = DataCleaner.parse_inr_currency("INVALID_TEXT")
        self.assertTrue(is_inv)

    def test_cleaner_process_mp_allocations(self):
        """Test full cleaning pipeline, trailer separation, and sum reconciliation."""
        cleaned_df, summary_meta = self.cleaner.process_mp_allocations()

        # Verify 543 individual MP records (Grand Total excluded from data table)
        self.assertEqual(len(cleaned_df), 543)
        self.assertEqual(summary_meta.total_mp_records, 543)
        self.assertTrue(summary_meta.is_sum_reconciled)
        self.assertAlmostEqual(summary_meta.reconciliation_delta, 0.0, places=2)

        # Verify column presence
        expected_cols = [
            "sr_no",
            "state",
            "mp_name",
            "constituency",
            "constituency_clean",
            "allocated_amount_inr",
            "is_reserved_sc",
            "is_reserved_st",
            "is_missing_amount",
            "is_invalid_amount",
            "is_duplicate_constituency",
            "is_data_quality_issue",
        ]
        for col in expected_cols:
            self.assertIn(col, cleaned_df.columns)

        # Verify exactly 1 record has missing amount in official data (CHAVAN VASANTRAO BALWANTRAO, NANDED)
        self.assertEqual(cleaned_df["is_missing_amount"].sum(), 1)
        self.assertEqual(cleaned_df["is_invalid_amount"].sum(), 0)

        # Verify duplicate constituency flag (NANDED appears 2 times)
        self.assertEqual(cleaned_df["is_duplicate_constituency"].sum(), 2)
        
        # Verify data quality issue composite flag
        self.assertEqual(cleaned_df["is_data_quality_issue"].sum(), 2)

    def test_save_processed_files(self):
        """Test saving processed data to CSV, Parquet, and JSON."""
        cleaned_df, summary_meta = self.cleaner.process_mp_allocations()
        csv_path, parquet_path, meta_path = self.cleaner.save_processed(
            cleaned_df, summary_meta
        )

        self.assertTrue(csv_path.exists())
        self.assertTrue(parquet_path.exists())
        self.assertTrue(meta_path.exists())

        # Validate saved CSV can be re-loaded accurately
        reloaded = pd.read_csv(csv_path)
        self.assertEqual(len(reloaded), 543)
        self.assertTrue(np.isclose(reloaded["allocated_amount_inr"].sum(), 83339905622.01))


if __name__ == "__main__":
    unittest.main()
