"""
tests/test_requirements.py
--------------------------
requirements.txt(PySCF版)と requirements-uma.txt(UMA版)の方針が、崩れていないかの確認。
各ファイルのコメントに、その理由を書いてある。
"""

import os
import re
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")


def _package_names(filename):
    with open(os.path.join(ROOT, filename), encoding="utf-8") as f:
        lines = [ln.strip() for ln in f if ln.strip() and not ln.strip().startswith("#")]
    return [re.split(r"[<>=!~\[ ]", ln)[0].lower() for ln in lines]


class TestIpywidgetsIsNotPinned(unittest.TestCase):
    """ipywidgets 8.x にすると、Colab標準のGUI表示の仕組み(7.x向け)で画面部品が
    表示されなくなる(「コードスニペット」のパネルが開くだけになる)ため、どちらの
    ファイルでも指定しない。"""

    def test_pyscf_requirements(self):
        self.assertNotIn("ipywidgets", _package_names("requirements.txt"))

    def test_uma_requirements(self):
        self.assertNotIn("ipywidgets", _package_names("requirements-uma.txt"))


class TestRequirementsUma(unittest.TestCase):
    def test_core_packages_are_listed(self):
        names = _package_names("requirements-uma.txt")
        for required in ("fairchem-core", "ase", "huggingface_hub", "pyyaml", "py3dmol"):
            self.assertIn(required, names)

    def test_torch_is_not_listed(self):
        # torchはColab標準のものを使い、fairchem-coreのインストールに任せる
        self.assertNotIn("torch", _package_names("requirements-uma.txt"))

    def test_pyscf_only_packages_are_not_listed(self):
        names = _package_names("requirements-uma.txt")
        for pyscf_only in ("pyscf", "geometric"):
            self.assertNotIn(pyscf_only, names)


class TestRequirementsPyscf(unittest.TestCase):
    def test_core_packages_are_listed(self):
        names = _package_names("requirements.txt")
        for required in ("pyscf", "geometric", "pyyaml", "ase", "py3dmol"):
            self.assertIn(required, names)


if __name__ == "__main__":
    unittest.main()
