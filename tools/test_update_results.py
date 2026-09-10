import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.update_results import merge_openfootball, read_rows, validate_update  # noqa: E402

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

    def test_merges_openfootball_names_and_scores(self):
        old = HEADER + b"SP1,01/09/2026,Barcelona,Valencia,2,0,H\n"
        source = """= Spain Primera División 2026/27
  Sun Sep 6
    16:15  Valencia CF             v FC Barcelona             0-5 (0-2)
  Sun Jan 10
    20:00  FC Barcelona            v Real Madrid CF           3-1 (1-1)
""".encode()
        rows = read_rows(merge_openfootball(old, source))
        self.assertEqual((rows[-2]["Date"], rows[-2]["HomeTeam"], rows[-2]["AwayTeam"],
                          rows[-2]["FTR"]), ("06/09/2026", "Valencia", "Barcelona", "A"))
        self.assertEqual(rows[-1]["Date"], "10/01/2027")


if __name__ == "__main__":
    unittest.main()
