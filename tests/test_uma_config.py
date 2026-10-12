"""
tests/test_uma_config.py
------------------------
config/uma_defaults.yaml と config/uma_models.yaml のスキーマ(必要な項目・値の型・
他ファイルとの整合性)のテスト。設定ファイルを編集して項目を消したり、
存在しない最適化アルゴリズムを指定したりしたときに、実行前に気づけるようにする。
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from uma_app import load_yaml, uma_optimize  # noqa: E402


class TestUmaDefaults(unittest.TestCase):
    def setUp(self):
        self.cfg = load_yaml("uma_defaults.yaml")

    def test_required_sections_exist(self):
        for section in ("gui_defaults", "uma", "geometry_optimization", "frequency", "validation"):
            self.assertIn(section, self.cfg)

    def test_gui_defaults(self):
        gui = self.cfg["gui_defaults"]
        self.assertIsInstance(gui["charge"], int)
        self.assertGreaterEqual(gui["multiplicity"], 1)
        self.assertIsInstance(gui["do_frequency"], bool)

    def test_default_model_is_one_of_the_listed_models(self):
        keys = [m["key"] for m in load_yaml("uma_models.yaml")]
        self.assertIn(self.cfg["gui_defaults"]["model"], keys)

    def test_task_name_is_set(self):
        self.assertTrue(self.cfg["uma"]["task_name"])

    def test_optimizer_settings_are_valid(self):
        opt = self.cfg["geometry_optimization"]
        self.assertIn(opt["optimizer"], uma_optimize.ALLOWED_OPTIMIZERS)
        self.assertGreater(opt["fmax_ev_per_angstrom"], 0)
        self.assertGreaterEqual(opt["max_steps"], 1)

    def test_frequency_and_validation_settings_are_positive(self):
        freq = self.cfg["frequency"]
        for key in ("displacement_angstrom", "warn_natoms", "small_imaginary_cm1"):
            self.assertGreater(freq[key], 0)
        self.assertGreater(self.cfg["validation"]["min_interatomic_distance_angstrom"], 0)


class TestUmaModels(unittest.TestCase):
    def setUp(self):
        self.models = load_yaml("uma_models.yaml")

    def test_every_model_has_label_and_key(self):
        self.assertGreaterEqual(len(self.models), 1)
        for m in self.models:
            self.assertTrue(m["label"])
            self.assertTrue(m["key"])

    def test_keys_are_unique(self):
        keys = [m["key"] for m in self.models]
        self.assertEqual(len(keys), len(set(keys)))

    def test_archived_model_is_not_offered(self):
        # uma-s-1(初版)はモデルカード上でアーカイブ扱い(既知の不具合あり)のため載せない
        self.assertNotIn("uma-s-1", [m["key"] for m in self.models])


class TestRequirementsUma(unittest.TestCase):
    """requirements-uma.txt の方針(コメントに理由あり)が崩れていないかの確認。"""

    @staticmethod
    def _names():
        import re
        path = os.path.join(os.path.dirname(__file__), "..", "requirements-uma.txt")
        with open(path, encoding="utf-8") as f:
            lines = [ln.strip() for ln in f if ln.strip() and not ln.strip().startswith("#")]
        return [re.split(r"[<>=!~\[ ]", ln)[0].lower() for ln in lines]

    def test_core_packages_are_listed(self):
        names = self._names()
        for required in ("fairchem-core", "ase", "huggingface_hub", "pyyaml", "py3dmol"):
            self.assertIn(required, names)

    def test_ipywidgets_is_not_pinned(self):
        # ipywidgets 8.x にすると、Colab標準のGUI表示の仕組み(7.x向け)で画面部品が
        # 表示されなくなるため、指定しない(理由は requirements-uma.txt のコメント参照)。
        self.assertNotIn("ipywidgets", self._names())

    def test_torch_is_not_listed(self):
        # torchはColab標準のものを使い、fairchem-coreのインストールに任せる
        self.assertNotIn("torch", self._names())


class TestMissingFile(unittest.TestCase):
    def test_missing_yaml_raises_a_helpful_error(self):
        with self.assertRaises(FileNotFoundError) as ctx:
            load_yaml("does_not_exist.yaml")
        self.assertIn("config/", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
