"""
tests/test_runtime.py
---------------------
common_backend.runtime(GPUの有無の判定)の単体テスト。
nvidia-smi の結果は、実物の subprocess.CompletedProcess で作る(コマンド自体は実行しない)。
torchは、入っていれば実物を使い、CUDAの有無を返す関数だけを差し替える(GPUがない環境でも、GPUがある場合を確認できる)。
torchが入っていない環境では、torchを使うテストだけをスキップする。
"""

import os
import subprocess
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import real_molecules as rm  # noqa: E402
from qchem_colab_app.common_backend import runtime  # noqa: E402

SKIP_NO_TORCH = "torchがインストールされていないためスキップ"


def _completed(returncode):
    """nvidia-smi を実行したときの戻り値(実物の CompletedProcess)。"""
    return subprocess.CompletedProcess(args=["nvidia-smi"], returncode=returncode)


class TestNvidiaGpuDetected(unittest.TestCase):
    def test_true_when_nvidia_smi_succeeds(self):
        with mock.patch.object(runtime.subprocess, "run", return_value=_completed(0)) as run:
            self.assertTrue(runtime.nvidia_gpu_detected())
        self.assertEqual(run.call_args[0][0], ["nvidia-smi"])

    def test_false_when_nvidia_smi_fails(self):
        with mock.patch.object(runtime.subprocess, "run", return_value=_completed(9)):
            self.assertFalse(runtime.nvidia_gpu_detected())

    def test_false_when_the_command_does_not_exist(self):
        with mock.patch.object(runtime.subprocess, "run", side_effect=FileNotFoundError):
            self.assertFalse(runtime.nvidia_gpu_detected())

    def test_false_when_the_command_times_out(self):
        with mock.patch.object(runtime.subprocess, "run",
                               side_effect=subprocess.TimeoutExpired("nvidia-smi", 15)):
            self.assertFalse(runtime.nvidia_gpu_detected())


class TestTorchCudaAvailable(unittest.TestCase):
    @unittest.skipUnless(rm.HAS_TORCH, SKIP_NO_TORCH)
    def test_true_when_torch_can_use_cuda(self):
        import torch
        with mock.patch.object(torch.cuda, "is_available", return_value=True):
            self.assertIs(runtime.torch_cuda_available(), True)

    @unittest.skipUnless(rm.HAS_TORCH, SKIP_NO_TORCH)
    def test_false_when_torch_cannot_use_cuda(self):
        import torch
        with mock.patch.object(torch.cuda, "is_available", return_value=False):
            self.assertIs(runtime.torch_cuda_available(), False)

    def test_false_when_torch_is_not_installed(self):
        with mock.patch.dict(sys.modules, {"torch": None}):
            self.assertIs(runtime.torch_cuda_available(), False)


@unittest.skipUnless(rm.HAS_TORCH, SKIP_NO_TORCH)
class TestTheTwoQuestionsAreIndependent(unittest.TestCase):
    def test_a_gpu_runtime_with_a_cpu_only_torch(self):
        import torch
        with mock.patch.object(runtime.subprocess, "run", return_value=_completed(0)), \
                mock.patch.object(torch.cuda, "is_available", return_value=False):
            self.assertTrue(runtime.nvidia_gpu_detected())
            self.assertFalse(runtime.torch_cuda_available())


if __name__ == "__main__":
    unittest.main()
