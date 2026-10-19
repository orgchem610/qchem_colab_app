"""
tests/test_engine.py
--------------------
pyscf_backend.engine のうち、PySCF・GPUなしでテストできる部分(遷移金属の判定・GPUランタイムの判定)の単体テスト。
Mole・SCFの構築と実行は、PySCFが必要なため、Colab上での実機確認が必要(README.md参照)。
"""

import os
import subprocess
import sys
import unittest
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from qchem_colab_app.pyscf_backend import engine  # noqa: E402


def _structure(symbols):
    return SimpleNamespace(symbols=symbols, coords=[[0.0, 0.0, 0.0]] * len(symbols))


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


class TestGpuRuntimeDetected(unittest.TestCase):
    def test_true_when_nvidia_smi_succeeds(self):
        with mock.patch.object(engine.subprocess, "run", return_value=SimpleNamespace(returncode=0)) as run:
            self.assertTrue(engine.gpu_runtime_detected())
        self.assertEqual(run.call_args[0][0], ["nvidia-smi"])

    def test_false_when_nvidia_smi_fails(self):
        with mock.patch.object(engine.subprocess, "run", return_value=SimpleNamespace(returncode=9)):
            self.assertFalse(engine.gpu_runtime_detected())

    def test_false_when_the_command_does_not_exist(self):
        with mock.patch.object(engine.subprocess, "run", side_effect=FileNotFoundError):
            self.assertFalse(engine.gpu_runtime_detected())

    def test_false_when_the_command_times_out(self):
        with mock.patch.object(engine.subprocess, "run",
                               side_effect=subprocess.TimeoutExpired("nvidia-smi", 15)):
            self.assertFalse(engine.gpu_runtime_detected())


if __name__ == "__main__":
    unittest.main()
