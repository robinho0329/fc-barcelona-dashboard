import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.update_current_snapshot import stat_rows  # noqa: E402


class CurrentSnapshotTest(unittest.TestCase):
    def test_keeps_only_barcelona_rows_and_metadata(self):
        data = {"TopLists": [{"StatList": [
            {"ParticipantName": "Other", "TeamId": 1, "StatValue": 9},
            {"ParticipantName": "Barca", "TeamId": 8634, "StatValue": 3,
             "MinutesPlayed": 180, "MatchesPlayed": 2},
        ]}]}
        self.assertEqual(stat_rows(data), [{
            "name": "Barca", "value": 3, "minutes": 180, "matches": 2,
        }])

    def test_empty_response_is_empty(self):
        self.assertEqual(stat_rows({"TopLists": []}), [])


if __name__ == "__main__":
    unittest.main()
