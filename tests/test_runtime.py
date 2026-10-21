"""
tests/test_runtime.py
---------------------
common_backend.runtime(GPUの有無の判定)の単体テスト。
nvidia-smi と torch は、代用の関数・モジュールに差し替えるため、GPUもtorchもない環境で動く。
"""

import os
import subprocess
import sys
import types
import unittest
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from qchem_colab_app.common_backend import runtime  # noqa: E402


class TestNvidiaGpuDetected(unittest.TestCase):
    def test_true_when_nvidia_smi_succeeds(self):
        with mock.patch.object(runtime.subprocess, "run", return_value=SimpleNamespace(returncode=0)) as run:
            self.assertTrue(runtime.nvidia_gpu_detected())
        self.assertEqual(run.call_args[0][0], ["nvidia-smi"])

    def test_false_when_nvidia_smi_fails(self):
        with mock.patch.object(runtime.subprocess, "run", return_value=SimpleNamespace(returncode=9)):
            self.assertFalse(runtime.nvidia_gpu_detected())

    def test_false_when_the_command_does_not_exist(self):
        with mock.patch.object(runtime.subprocess, "run", side_effect=FileNotFoundError):
            self.assertFalse(runtime.nvidia_gpu_detected())

    def test_false_when_the_command_times_out(self):
        with mock.patch.object(runtime.subprocess, "run",
                               side_effect=subprocess.TimeoutExpired("nvidia-smi", 15)):
            self.assertFalse(runtime.nvidia_gpu_detected())


def _fake_torch(cuda_available):
    module = types.ModuleType("torch")
    module.cuda = SimpleNamespace(is_available=lambda: cuda_available)
    return module


class TestTorchCudaAvailable(unittest.TestCase):
    def test_true_when_torch_can_use_cuda(self):
        with mock.patch.dict(sys.modules, {"torch": _fake_torch(True)}):
            self.assertIs(runtime.torch_cuda_available(), True)

    def test_false_when_torch_cannot_use_cuda(self):
        with mock.patch.dict(sys.modules, {"torch": _fake_torch(False)}):
            self.assertIs(runtime.torch_cuda_available(), False)

    def test_false_when_torch_is_not_installed(self):
        with mock.patch.dict(sys.modules, {"torch": None}):
            self.assertIs(runtime.torch_cuda_available(), False)


class TestTheTwoQuestionsAreIndependent(unittest.TestCase):
    def test_a_gpu_runtime_with_a_cpu_only_torch(self):
        with mock.patch.object(runtime.subprocess, "run", return_value=SimpleNamespace(returncode=0)), \
                mock.patch.dict(sys.modules, {"torch": _fake_torch(False)}):
            self.assertTrue(runtime.nvidia_gpu_detected())
            self.assertFalse(runtime.torch_cuda_available())


if __name__ == "__main__":
    unittest.main()
