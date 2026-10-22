"""
tests/test_engine.py
--------------------
pyscf_backend.engine のうち、PySCF・GPUなしでテストできる部分(遷移金属の判定)の単体テスト。
Mole・SCFの構築と実行は、PySCFが必要なため、Colab上での実機確認が必要(README.md参照)。
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from qchem_colab_app.common_backend import io_reader  # noqa: E402
from qchem_colab_app.pyscf_backend import engine  # noqa: E402


def _structure(symbols):
    return io_reader.Structure(symbols=list(symbols), coords=[[0.0, 0.0, 0.0]] * len(symbols))


class TestContainsTransitionMetal(unittest.TestCase):
    def test_organic_molecule_is_false(self):
        self.assertFalse(engine.contains_transition_metal(_structure(["C", "H", "H", "H", "O"])))

    def test_iron_complex_is_true(self):
        self.assertTrue(engine.contains_transition_metal(_structure(["Fe", "C", "O"])))

    def test_each_row_of_the_d_block_is_detected(self):
        for symbol in ("Sc", "Zn", "Y", "Cd", "Hf", "Pt", "Hg"):
            self.assertTrue(engine.contains_transition_metal(_structure(["C", symbol])), symbol)

    def test_main_group_elements_next_to_the_d_block_are_not_detected(self):
        for symbol in ("Ca", "Ga", "Sr", "In", "Xe"):
            self.assertFalse(engine.contains_transition_metal(_structure([symbol])), symbol)

    def test_empty_structure_is_false(self):
        self.assertFalse(engine.contains_transition_metal(_structure([])))


class TestGpuDetectionIsNotHere(unittest.TestCase):
    def test_gpu_runtime_detection_lives_in_common_backend(self):
        # GPUランタイムの判定は common_backend.runtime(tests/test_runtime.py が検査)にあり、engineには置かない
        self.assertFalse(hasattr(engine, "gpu_runtime_detected"))
        self.assertFalse(hasattr(engine, "subprocess"))


if __name__ == "__main__":
    unittest.main()
