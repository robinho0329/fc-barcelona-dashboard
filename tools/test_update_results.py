import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.update_results import validate_update  # noqa: E402

HEADER = b"Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR\n"


class UpdateResultsTest(unittest.TestCase):
    def test_accepts_appended_completed_match(self):
        old = b"\xef\xbb\xbf" + HEADER + b"SP1,01/09/2026,Barcelona,Valencia,2,0,H\n"
        new = old + b"SP1,08/09/2026,Sevilla,Barcelona,1,1,D\n"
        self.assertEqual(validate_update(old, new), (1, 2))

    def test_rejects_removed_match(self):
        old = (HEADER + b"SP1,01/09/2026,Barcelona,Valencia,2,0,H\n"
               b"SP1,08/09/2026,Sevilla,Barcelona,1,1,D\n")
        new = HEADER + b"SP1,01/09/2026,Barcelona,Valencia,2,0,H\n"
        with self.assertRaisesRegex(ValueError, "사라졌습니다"):
            validate_update(old, new)


if __name__ == "__main__":
    unittest.main()
