"""Data loader module for reading raw MPLADS/eSAKSHI datasets safely and immutably.
"""

import os
from pathlib import Path
from typing import Optional, Union
import pandas as pd


class DataLoader:
    """Safe, immutable data loader for raw MPLADS datasets."""

    def __init__(self, raw_dir: Optional[Union[str, Path]] = None):
        if raw_dir is None:
            # Default to data/raw relative to workspace root
            current_dir = Path(__file__).resolve().parent
            # navigate from backend/app/data -> backend -> workspace root -> data/raw
            root_dir = current_dir.parents[2]
            self.raw_dir = root_dir / "data" / "raw"
        else:
            self.raw_dir = Path(raw_dir)

        if not self.raw_dir.exists():
            raise FileNotFoundError(f"Raw data directory does not exist: {self.raw_dir}")

    def list_raw_files(self) -> list[str]:
        """List all available raw data files in data/raw."""
        return [f.name for f in self.raw_dir.iterdir() if f.is_file()]

    def load_raw_csv(self, filename: str) -> pd.DataFrame:
        """Load a CSV file from data/raw/ immutably without modifying the source.
        
        Args:
            filename: Name of the CSV file inside data/raw/
            
        Returns:
            pd.DataFrame: A copy of the raw dataset.
        """
        filepath = self.raw_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Raw file not found: {filepath}")

        # Try utf-8 first, fallback to cp1252 or latin1 if needed
        try:
            df = pd.read_csv(filepath, encoding="utf-8", dtype=str)
        except UnicodeDecodeError:
            df = pd.read_csv(filepath, encoding="latin1", dtype=str)

        return df.copy()

    def load_mp_allocations_raw(self) -> pd.DataFrame:
        """Convenience loader for 'Allocated Limit for Honble MPs.csv'."""
        return self.load_raw_csv("Allocated Limit for Honble MPs.csv")
