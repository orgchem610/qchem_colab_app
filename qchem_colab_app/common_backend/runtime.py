"""
common_backend.runtime
----------------------
計算を実行する環境(GPUの有無)の判定。画面にも計算エンジンにも依存しない。

    - nvidia_gpu_detected()  : NVIDIAのGPUが割り当てられているか(`nvidia-smi`が成功するか)
    - torch_cuda_available() : PyTorchがCUDA(GPU)を使えるか

2つは、答える問いが違う。GPUランタイムでも、CPU版のtorchが入っていれば、前者は True、後者は False になる。
    - PySCF版は、GPU4PySCFを読み込む前に、GPUを試すかどうかを決めるため、torchが入っていなくても
      動く nvidia_gpu_detected() を使う(pyscf_backend/pipeline.py)。
    - UMA版は、推論がtorchで動くため、torchがCUDAを使えるかを見る torch_cuda_available() を使う
      (uma_backend/uma_pipeline.py)。
torchは、関数の中でimportする。入っていない環境でも、このモジュール自体は読み込める。
"""

import subprocess


def nvidia_gpu_detected():
    """GPUランタイム(NVIDIA GPU)が割り当てられているかを、nvidia-smi の成否で判定する。

    CPUのみのランタイムでは、nvidia-smi コマンド自体が存在せず FileNotFoundError になるため、
    その場合は False を返す。コマンドが失敗・タイムアウトした場合も False。
    """
    try:
        return subprocess.run(["nvidia-smi"], capture_output=True, timeout=15).returncode == 0
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return False


def torch_cuda_available():
    """PyTorchがCUDA(GPU)を使えるか。torchが入っていなければ False。"""
    try:
        import torch
    except ImportError:
        return False
    return bool(torch.cuda.is_available())
