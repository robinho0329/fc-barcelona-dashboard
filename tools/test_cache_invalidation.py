"""Regression checks for timestamp-based data cache invalidation.

Run with:
    python tools/test_cache_invalidation.py
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import _lib  # noqa: E402


INITIAL_MTIME_NS = 1_700_000_000_000_000_000
UPDATED_MTIME_NS = INITIAL_MTIME_NS + 2_000_000_000


def set_mtime(path: Path, stamp_ns: int) -> None:
    os.utime(path, ns=(stamp_ns, stamp_ns))


class CacheInvalidationTest(unittest.TestCase):
    def test_parquet_change_invalidates_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.parquet"
            pd.DataFrame({"value": [1]}).to_parquet(path, index=False)
            set_mtime(path, INITIAL_MTIME_NS)
            self.assertEqual(_lib.load_parquet(path)["value"].tolist(), [1])

            pd.DataFrame({"value": [2]}).to_parquet(path, index=False)
            set_mtime(path, INITIAL_MTIME_NS)
            self.assertEqual(_lib.load_parquet(path)["value"].tolist(), [1])

            set_mtime(path, UPDATED_MTIME_NS)
            self.assertEqual(_lib.load_parquet(path)["value"].tolist(), [2])

    def test_json_change_invalidates_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.json"
            path.write_text(json.dumps({"value": 1}), encoding="utf-8")
            set_mtime(path, INITIAL_MTIME_NS)
            self.assertEqual(_lib.load_json(path), {"value": 1})

            path.write_text(json.dumps({"value": 2}), encoding="utf-8")
            set_mtime(path, INITIAL_MTIME_NS)
            self.assertEqual(_lib.load_json(path), {"value": 1})

            set_mtime(path, UPDATED_MTIME_NS)
            self.assertEqual(_lib.load_json(path), {"value": 2})

    def test_directory_file_change_invalidates_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_root = Path(tmp)
            directory = data_root / "parts"
            directory.mkdir()
            path = directory / "sample.parquet"
            original_processed = _lib.PROCESSED
            _lib.PROCESSED = data_root / "processed"
            try:
                pd.DataFrame({"value": [1]}).to_parquet(path, index=False)
                set_mtime(path, INITIAL_MTIME_NS)
                self.assertEqual(_lib.load_dir("parts")["value"].tolist(), [1])

                pd.DataFrame({"value": [2]}).to_parquet(path, index=False)
                set_mtime(path, INITIAL_MTIME_NS)
                self.assertEqual(_lib.load_dir("parts")["value"].tolist(), [1])

                set_mtime(path, UPDATED_MTIME_NS)
                self.assertEqual(_lib.load_dir("parts")["value"].tolist(), [2])
            finally:
                _lib.PROCESSED = original_processed


if __name__ == "__main__":
    unittest.main()
