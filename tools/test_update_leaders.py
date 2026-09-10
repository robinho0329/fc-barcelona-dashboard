import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.update_leaders import extract_stat  # noqa: E402


class UpdateLeadersTest(unittest.TestCase):
    def test_filters_team_and_sorts(self):
        data = {"TopLists": [{"StatName": "goals", "StatList": [
            {"ParticipantName": "Other", "TeamId": 1, "StatValue": 9},
            {"ParticipantName": "B", "TeamId": 8634, "StatValue": 2},
            {"ParticipantName": "A", "TeamId": 8634, "StatValue": 3},
        ]}]}
        self.assertEqual(extract_stat(data, "goals"),
                         [{"Player": "A", "value": 3}, {"Player": "B", "value": 2}])

    def test_missing_table_fails(self):
        with self.assertRaisesRegex(ValueError, "표가 없습니다"):
            extract_stat({"TopLists": []}, "goal_assist")


if __name__ == "__main__":
    unittest.main()
