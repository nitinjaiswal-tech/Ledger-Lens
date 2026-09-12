"""Data cleaning and transformation pipeline for MPLADS datasets.
Maintains provenance: RAW DATA -> VALIDATION -> CLEANING -> PROCESSED DATA.
"""

import json
import re
from pathlib import Path
from typing import Optional, Tuple, Union
import numpy as np
import pandas as pd

from .loader import DataLoader
from .validators import (
    MPAllocationCleanedRecord,
    MPAllocationRawRecord,
    SummaryTotalsMetadata,
)


class DataCleaner:
    """Standardized cleaner and preprocessor for MPLADS datasets."""

    # Explicit column rename map documenting exact transformations
    COLUMN_RENAME_MAP = {
        "Sr. No.": "sr_no",
        "State": "state",
        "Hon'ble Members of Parliaments": "mp_name",
        "Constituency": "constituency",
        "Allocated AMOUNT ( ₹ )": "allocated_amount_inr",
    }

    def __init__(
        self,
        loader: Optional[DataLoader] = None,
        processed_dir: Optional[Union[str, Path]] = None,
    ):
        self.loader = loader or DataLoader()
        if processed_dir is None:
            current_dir = Path(__file__).resolve().parent
            root_dir = current_dir.parents[2]
            self.processed_dir = root_dir / "data" / "processed"
        else:
            self.processed_dir = Path(processed_dir)

        self.processed_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def standardize_column_names(df: pd.DataFrame) -> pd.DataFrame:
        """Rename dataframe columns according to standard snake_case naming scheme."""
        df_renamed = df.copy()
        
        rename_dict = {}
        for col in df_renamed.columns:
            if col in DataCleaner.COLUMN_RENAME_MAP:
                rename_dict[col] = DataCleaner.COLUMN_RENAME_MAP[col]
            else:
                clean_name = re.sub(r"[^\w\s]", "", col).strip()
                clean_name = re.sub(r"\s+", "_", clean_name).lower()
                rename_dict[col] = clean_name
                
        return df_renamed.rename(columns=rename_dict)

    @staticmethod
    def parse_inr_currency(val: Union[str, float, int, None]) -> Tuple[float, bool, bool]:
        """Safely parse Indian currency strings containing Rupee symbols and comma groupings.
        
        Returns:
            Tuple[float, bool, bool]: (cleaned_amount, is_missing, is_invalid)
        """
        if val is None or pd.isna(val):
            return 0.0, True, False

        val_str = str(val).strip()
        if val_str == "" or val_str.lower() in ("nan", "none", "null", "-"):
            return 0.0, True, False

        clean_str = re.sub(r"[^\d.]", "", val_str)

        try:
            amount = float(clean_str)
            if amount < 0:
                return amount, False, True
            return round(amount, 2), False, False
        except (ValueError, TypeError):
            return 0.0, False, True

    def process_mp_allocations(
        self, raw_df: Optional[pd.DataFrame] = None
    ) -> Tuple[pd.DataFrame, SummaryTotalsMetadata]:
        """Execute full cleaning and validation pipeline for MP allocations.
        
        Returns:
            Tuple[pd.DataFrame, SummaryTotalsMetadata]: Cleaned DataFrame and reconciled summary metadata.
        """
        if raw_df is None:
            raw_df = self.loader.load_mp_allocations_raw()

        # Step 1: Standardize column names
        df = self.standardize_column_names(raw_df)

        # Step 2: Separate Grand Total trailer summary row from operational data
        is_grand_total = (
            df["sr_no"].astype(str).str.strip().str.lower() == "grand total"
        )
        trailer_rows = df[is_grand_total].copy()
        data_rows = df[~is_grand_total].copy()

        # Extract official grand total from trailer
        official_grand_total = 0.0
        if not trailer_rows.empty:
            raw_gt_val = trailer_rows["allocated_amount_inr"].values[0]
            official_grand_total, _, _ = self.parse_inr_currency(raw_gt_val)

        # Step 3: Parse currency amounts and generate quality flags
        parsed_amounts = []
        missing_amount_flags = []
        invalid_amount_flags = []

        for val in data_rows["allocated_amount_inr"]:
            amt, is_miss, is_inv = self.parse_inr_currency(val)
            parsed_amounts.append(amt)
            missing_amount_flags.append(is_miss)
            invalid_amount_flags.append(is_inv)

        data_rows["allocated_amount_inr"] = parsed_amounts
        data_rows["is_missing_amount"] = missing_amount_flags
        data_rows["is_invalid_amount"] = invalid_amount_flags

        # Step 4: Text standardization & sequence indexing
        data_rows["sr_no"] = pd.to_numeric(data_rows["sr_no"], errors="coerce").fillna(0).astype(int)
        data_rows["state"] = data_rows["state"].astype(str).str.strip()
        data_rows["mp_name"] = data_rows["mp_name"].astype(str).str.strip()
        data_rows["constituency"] = data_rows["constituency"].astype(str).str.strip()

        # Step 5: Extract reservation tags and clean constituency names
        is_sc_list = []
        is_st_list = []
        constituency_clean_list = []

        for c_name in data_rows["constituency"]:
            is_sc = bool(re.search(r"\(SC\)", c_name, re.IGNORECASE))
            is_st = bool(re.search(r"\(ST\)", c_name, re.IGNORECASE))
            cleaned_c = re.sub(r"\((SC|ST)\)", "", c_name, flags=re.IGNORECASE)
            cleaned_c = re.sub(r"_[A-Z]{2}$", "", cleaned_c)
            cleaned_c = re.sub(r"\s+", " ", cleaned_c).strip()

            is_sc_list.append(is_sc)
            is_st_list.append(is_st)
            constituency_clean_list.append(cleaned_c)

        data_rows["is_reserved_sc"] = is_sc_list
        data_rows["is_reserved_st"] = is_st_list
        data_rows["constituency_clean"] = constituency_clean_list

        # Step 6: Identify duplicate constituencies (domain duplicate check)
        constituency_counts = data_rows["constituency"].value_counts()
        duplicate_constituencies = set(
            constituency_counts[constituency_counts > 1].index
        )
        data_rows["is_duplicate_constituency"] = data_rows["constituency"].isin(
            duplicate_constituencies
        )

        # Step 7: Composite data quality issue flag
        data_rows["is_data_quality_issue"] = (
            data_rows["is_missing_amount"]
            | data_rows["is_invalid_amount"]
            | data_rows["is_duplicate_constituency"]
        )

        # Step 8: Validate records with Pydantic
        validated_records = []
        for row_dict in data_rows.to_dict(orient="records"):
            record = MPAllocationCleanedRecord(**row_dict)
            validated_records.append(record.model_dump())

        cleaned_df = pd.DataFrame(validated_records)

        # Step 9: Reconcile calculated sum against official grand total
        calculated_sum = round(float(cleaned_df["allocated_amount_inr"].sum()), 2)
        reconciliation_delta = round(calculated_sum - official_grand_total, 2)
        is_reconciled = abs(reconciliation_delta) <= 0.01

        summary_meta = SummaryTotalsMetadata(
            source_filename="Allocated Limit for Honble MPs.csv",
            official_grand_total_inr=official_grand_total,
            calculated_sum_inr=calculated_sum,
            total_mp_records=len(cleaned_df),
            is_sum_reconciled=bool(is_reconciled),
            reconciliation_delta=reconciliation_delta,
        )

        return cleaned_df, summary_meta

    def save_processed(
        self,
        df: pd.DataFrame,
        summary_meta: SummaryTotalsMetadata,
        base_name: str = "allocated_limit_mps_cleaned",
    ) -> Tuple[Path, Path, Path]:
        """Persist processed dataset and metadata into data/processed/."""
        csv_path = self.processed_dir / f"{base_name}.csv"
        parquet_path = self.processed_dir / f"{base_name}.parquet"
        meta_path = self.processed_dir / "summary_totals_metadata.json"

        # Save CSV
        df.to_csv(csv_path, index=False, encoding="utf-8")
        
        # Save Parquet for fast analytics
        df.to_parquet(parquet_path, index=False)

        # Save JSON metadata
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(summary_meta.model_dump(), f, indent=2)

        return csv_path, parquet_path, meta_path
