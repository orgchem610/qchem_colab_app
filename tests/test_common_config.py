"""
tests/test_common_config.py
---------------------------
common.config(config/ のYAMLファイルの読み込み)の単体テスト。
pyscf_backend・uma_backend が、同じ関数・同じ場所を使っていること(別名になっていること)も確認する。
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pyscf_backend  # noqa: E402
import uma_backend  # noqa: E402
from common import config  # noqa: E402


class TestLoadYaml(unittest.TestCase):
    def test_config_directory_is_the_one_in_the_repository_root(self):
        self.assertTrue(config.CONFIG_DIR.is_dir())
        self.assertEqual(config.CONFIG_DIR.parent, config.PROJECT_ROOT)
        self.assertTrue((config.PROJECT_ROOT / "gui.py").exists())

    def test_existing_file_is_parsed(self):
        defaults = config.load_yaml("defaults.yaml")
        self.assertIn("gui_defaults", defaults)

    def test_missing_file_raises_a_helpful_error(self):
        with self.assertRaises(FileNotFoundError) as ctx:
            config.load_yaml("does_not_exist.yaml")
        message = str(ctx.exception)
        self.assertIn("does_not_exist.yaml", message)
        self.assertIn("config/", message)


class TestAliases(unittest.TestCase):
    def test_both_packages_use_the_common_function_and_paths(self):
        for package in (pyscf_backend, uma_backend):
            self.assertIs(package.load_yaml, config.load_yaml)
            self.assertEqual(package.CONFIG_DIR, config.CONFIG_DIR)
            self.assertEqual(package.PROJECT_ROOT, config.PROJECT_ROOT)


if __name__ == "__main__":
    unittest.main()
