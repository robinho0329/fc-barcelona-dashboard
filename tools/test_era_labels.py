"""Editorial era labels must not be stored in data-only caches."""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class EraLabelsTest(unittest.TestCase):
    def test_labels_and_cache_boundary(self):
        tree = ast.parse((ROOT / "views/tikitaka.py").read_text(encoding="utf-8"))
        selected = [n for n in tree.body if
                    isinstance(n, ast.Assign) and any(
                        isinstance(t, ast.Name) and t.id == "ERA_OF" for t in n.targets)
                    or isinstance(n, ast.FunctionDef) and n.name == "era_of"]
        scope = dict(GOLD="gold", BLAU="blue", GRANA="red",
                     ORDER=[f"{y}/{str(y + 1)[-2:]}" for y in range(1993, 2027)])
        exec(compile(ast.Module(body=selected, type_ignores=[]), "eras", "exec"), scope)
        for season, expected in [("2011/12", "과르디올라"),
                                 ("2012/13", "티토·마르티노"),
                                 ("2013/14", "티토·마르티노"),
                                 ("2014/15", "MSN"), ("2016/17", "MSN")]:
            self.assertEqual(scope["era_of"](season)[0], expected)
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name in {"build_index", "possession_series"}:
                self.assertFalse(any(isinstance(n, ast.Name) and n.id == "era_of"
                                     for n in ast.walk(node)), node.name)


if __name__ == "__main__":
    unittest.main()
