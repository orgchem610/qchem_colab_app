"""
tests/test_engine.py
--------------------
qcapp.engine のうち、PySCF・GPUなしでテストできる部分(GPUランタイムの判定)の単体テスト。
Mole・SCFの構築と実行は、PySCFが必要なため、Colab上での実機確認が必要(README.md参照)。
"""

import os
import subprocess
import sys
import unittest
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from qcapp import engine  # noqa: E402


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
