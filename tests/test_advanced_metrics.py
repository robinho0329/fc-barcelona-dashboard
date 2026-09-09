import unittest

import pandas as pd

from views._advanced_metrics import per_appearance, rate_label


class PerAppearanceTests(unittest.TestCase):
    def test_axis_label_does_not_call_a_percentage_per_game(self):
        self.assertEqual(rate_label("패스"), "경기당 패스")
        self.assertEqual(rate_label("패스 성공률"), "패스 성공률")

    def test_last_event_minute_is_not_treated_as_playing_time(self):
        rows = pd.DataFrame([
            {"player": "starter", "match_id": 1, "season": "2020/21", "minutes_seen": 10,
             "passes": 20, "passes_completed": 15},
            {"player": "sub", "match_id": 1, "season": "2020/21", "minutes_seen": 90,
             "passes": 10, "passes_completed": 8},
            {"player": "starter", "match_id": 2, "season": "2020/21", "minutes_seen": 90,
             "passes": 40, "passes_completed": 30},
        ])

        result = per_appearance(rows, {"패스": "passes"}, min_appearances=1)

        self.assertEqual(result.loc["starter", "경기"], 2)
        self.assertEqual(result.loc["starter", "패스"], 30)
        self.assertEqual(result.loc["sub", "패스"], 10)
        self.assertEqual(result.loc["starter", "패스 성공률"], 75)

    def test_filter_uses_recorded_matches(self):
        rows = pd.DataFrame([
            {"player": "regular", "match_id": match_id, "season": "2020/21",
             "passes": 1, "passes_completed": 1}
            for match_id in (1, 2)
        ] + [{"player": "cameo", "match_id": 1, "season": "2020/21",
              "passes": 1, "passes_completed": 1}])

        result = per_appearance(rows, {"패스": "passes"}, min_appearances=2)

        self.assertEqual(result.index.tolist(), ["regular"])


if __name__ == "__main__":
    unittest.main()
