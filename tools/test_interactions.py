"""Bounded AppTest checks for the three release-critical interactive pages."""
from pathlib import Path
import sys
import unittest

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def page(name: str) -> AppTest:
    return AppTest.from_file(str(ROOT / "views" / f"{name}.py"), default_timeout=120).run()


class InteractionTest(unittest.TestCase):
    def assert_clean(self, app: AppTest) -> None:
        self.assertEqual([], list(app.exception))

    def test_network_season_change_and_restrictive_link_filter(self) -> None:
        app = page("network")
        app.selectbox[0].set_value("2005/06").run()
        self.assert_clean(app)
        self.assertEqual("2005/06", app.selectbox[0].value)
        app.slider[0].set_value(10).run()
        self.assert_clean(app)
        self.assertTrue(any("최소 연결 횟수를 낮춰" in item.value for item in app.info))

    def test_shots_season_player_and_map_only_toggle(self) -> None:
        app = page("shots")
        app.selectbox[0].set_value("1973/74").run()
        self.assert_clean(app)
        self.assertEqual("1973/74", app.selectbox[0].value)
        player = app.selectbox[1].options[1]
        app.selectbox[1].set_value(player).run()
        self.assert_clean(app)
        summary_before = [item.value for item in app.markdown if "metric-card" in item.value]
        app.checkbox[0].check().run()
        self.assert_clean(app)
        summary_after = [item.value for item in app.markdown if "metric-card" in item.value]
        self.assertEqual(summary_before, summary_after)

    def test_players_filters_and_empty_search(self) -> None:
        app = page("players")
        app.radio[0].set_value("라리가 (상세)").run()
        app.selectbox[0].set_value("1993/94").run()
        app.selectbox[1].set_value("공격수").run()
        self.assert_clean(app)
        app.text_input[0].set_value("__no_such_player__").run()
        self.assert_clean(app)
        self.assertTrue(any("조건에 맞는 선수가 없습니다" in item.value for item in app.info))


if __name__ == "__main__":
    unittest.main()
