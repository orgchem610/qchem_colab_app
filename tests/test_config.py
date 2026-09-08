"""
tests/test_config.py
----------------------
config/*.yaml が正しくパースでき、gui.py / engine.py が期待する
最低限のキーを持っていることを確認する単体テスト。

「設定ファイルを1行足すだけで機能追加できる」設計が壊れていないかを
継続的に確認する目的もある(例: label/keyフィールドの綴りミスなど)。
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from qcapp import load_yaml  # noqa: E402


class TestPurposesYaml(unittest.TestCase):
    def test_has_at_least_one_purpose(self):
        purposes = load_yaml("purposes.yaml")
        self.assertIsInstance(purposes, list)
        self.assertGreaterEqual(len(purposes), 1)
        for item in purposes:
            for key in ("key", "label"):
                self.assertIn(key, item)

    def test_geometry_optimization_purpose_exists(self):
        purposes = load_yaml("purposes.yaml")
        keys = [p["key"] for p in purposes]
        self.assertIn("geometry_optimization", keys)


class TestFunctionalsYaml(unittest.TestCase):
    def test_hf_is_registered(self):
        functionals = load_yaml("functionals.yaml")
        keys = {f["key"]: f for f in functionals}
        self.assertIn("hf", keys)
        self.assertEqual(keys["hf"]["engine"], "hf")

    def test_all_entries_have_required_fields(self):
        functionals = load_yaml("functionals.yaml")
        for item in functionals:
            for key in ("key", "label", "engine"):
                self.assertIn(key, item)
            self.assertIn(item["engine"], ("hf", "dft"))
            if item["engine"] == "dft":
                self.assertIsNotNone(item.get("xc"))


class TestBasisSetsYaml(unittest.TestCase):
    def test_321g_is_registered_in_main_group(self):
        basis_cfg = load_yaml("basis_sets.yaml")
        self.assertIn("main_group", basis_cfg)
        keys = [b["key"] for b in basis_cfg["main_group"]]
        self.assertIn("3-21g", keys)

    def test_transition_metal_ecp_category_exists_even_if_empty(self):
        basis_cfg = load_yaml("basis_sets.yaml")
        self.assertIn("transition_metal_ecp", basis_cfg)


class TestDefaultsYaml(unittest.TestCase):
    def test_frequency_default_is_true(self):
        defaults = load_yaml("defaults.yaml")
        self.assertTrue(defaults["gui_defaults"]["do_frequency"])

    def test_multiplicity_default_is_one(self):
        defaults = load_yaml("defaults.yaml")
        self.assertEqual(defaults["gui_defaults"]["multiplicity"], 1)

    def test_required_sections_exist(self):
        defaults = load_yaml("defaults.yaml")
        for section in ("scf", "geometry_optimization", "frequency", "validation", "gpu"):
            self.assertIn(section, defaults)


if __name__ == "__main__":
    unittest.main()
