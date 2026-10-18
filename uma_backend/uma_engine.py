"""
uma_backend.uma_engine
------------------
UMA(fairchem-core)で計算するための土台となるモジュール。

    - 計算デバイス(GPU/CPU)の判定
    - 学習済みモデル(predictor)の読み込み(同じモデルは使い回す)
    - ASEのAtomsとCalculatorの構築

Hugging Faceのトークン管理・UMAへのアクセス権の確認・UmaSetupError は、役割が違うため
uma_backend/uma_hf.py にある(v0.2.1で、このファイルから分けた)。

fairchem・torch・aseは、このファイルを読み込んだだけではimportしない
(各関数の中でimportする)。これにより、これらがインストールされていない環境でも
このモジュール自体は読み込め、単体テストできる。
"""

from uma_backend import uma_hf


# -----------------------------------------------------------------------------
# デバイス・モデル・Calculator
# -----------------------------------------------------------------------------

def get_device():
    """"cuda"(GPUあり)または"cpu"を返す。torchが無ければ"cpu"。"""
    try:
        import torch
    except ImportError:
        return "cpu"
    return "cuda" if torch.cuda.is_available() else "cpu"


def describe_device(device):
    """ログ表示用のデバイス説明文。"""
    if device == "cuda":
        try:
            import torch
            return f"GPU({torch.cuda.get_device_name(0)})"
        except Exception:
            return "GPU"
    return "CPU(GPUランタイムではないため、計算に時間がかかります)"


_PREDICTOR_CACHE = {}


def load_predictor(model_name, device):
    """学習済みモデル(predict unit)を読み込む。同じモデル・デバイスなら使い回す。

    初回はHugging Faceからモデルファイルをダウンロードするため、時間がかかる。
    """
    key = (model_name, device)
    if key not in _PREDICTOR_CACHE:
        try:
            from fairchem.core import pretrained_mlip
        except ImportError as e:
            raise uma_hf.UmaSetupError(
                "fairchem-core がインストールされていません。"
                "「3. 依存ライブラリのインストール」のセルを実行してください。"
                f"(内部エラー: {e})") from e
        try:
            _PREDICTOR_CACHE[key] = pretrained_mlip.get_predict_unit(model_name, device=device)
        except Exception as e:
            if type(e).__name__ == "GatedRepoError" or getattr(
                    getattr(e, "response", None), "status_code", None) in (401, 403):
                raise uma_hf.UmaSetupError(uma_hf.explain_hf_error(e)) from e
            raise
    return _PREDICTOR_CACHE[key]


def clear_predictor_cache():
    """読み込み済みモデルを解放する(GPUメモリを空けたいとき用)。"""
    _PREDICTOR_CACHE.clear()


def make_calculator(predictor, task_name="omol"):
    """ASEのCalculatorとして使えるFAIRChemCalculatorを作る。"""
    from fairchem.core import FAIRChemCalculator
    return FAIRChemCalculator(predictor, task_name=task_name)


def build_atoms(structure, charge, multiplicity):
    """common.io_reader.Structure から、電荷・スピン多重度付きのASE Atomsを作る。

    UMA(omolタスク)には、電荷を atoms.info["charge"]、スピン多重度を
    atoms.info["spin"] として渡す(fairchemのREADME・ColabReactionと同じ方式)。
    """
    from ase import Atoms
    atoms = Atoms(symbols=list(structure.symbols),
                  positions=[list(c) for c in structure.coords])
    atoms.info["charge"] = int(charge)
    atoms.info["spin"] = int(multiplicity)
    return atoms
