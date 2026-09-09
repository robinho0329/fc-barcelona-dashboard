"""Focused checks for release-facing caveats and labels."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ReleaseCopyTest(unittest.TestCase):
    def test_network_does_not_claim_actual_positions_or_default_unknown_to_midfield(self) -> None:
        text = (ROOT / "views" / "network.py").read_text(encoding="utf-8")
        self.assertNotIn("실제 라인업과 같은 순서", text)
        self.assertNotIn('positions.get(name) or "MF"', text)
        self.assertIn('(\"UNK\", \"미분류\")', text)

    def test_model_states_single_holdout_limit(self) -> None:
        text = (ROOT / "views" / "model.py").read_text(encoding="utf-8")
        self.assertNotIn("줄 세우는 능력은 분명히 있다", text)
        self.assertIn("다른 시즌에서도 같은 판별력이 이어진다는 보장은 없다", text)
        self.assertIn("반복 검증은 하지 않았다", text)


if __name__ == "__main__":
    unittest.main()
