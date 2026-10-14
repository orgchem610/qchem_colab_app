"""
uma_app.uma_engine
------------------
UMA(fairchem-core)を使うための土台となるモジュール。

    - Hugging Faceのトークン管理・UMAへのアクセス権の確認
    - 計算デバイス(GPU/CPU)の判定
    - 学習済みモデル(predictor)の読み込み(同じモデルは使い回す)
    - ASEのAtomsとCalculatorの構築

fairchem・torch・aseは、このファイルを読み込んだだけではimportしない
(各関数の中でimportする)。これにより、これらがインストールされていない環境でも
このモジュール自体は読み込め、エラーメッセージの整形等を単体テストできる。

【UMAの利用条件】(詳細は uma_notice.py 参照)
UMAの学習済みモデル(facebook/UMA)は、Hugging Face上で利用条件への同意が必要な
「ゲート付きリポジトリ」。モデルを使う人自身がHugging Faceのアカウントを作り、
利用条件に同意し、アクセストークンを発行する必要がある。このアプリは
モデルファイルを同梱・再配布せず、利用者のColab上でHugging Faceから直接取得する。
トークンはノートブックのセルに書き込まず、ノートブックの「2.」のセル(getpass)か
Colabのシークレットで受け取り、環境変数 HF_TOKEN(Hugging Face公式の標準の受け渡し方法)
にだけ設定する。このモジュールは、トークンの入力方法を知らず、環境変数 HF_TOKEN だけを
見る(login_from_environment)。そのため、入力セルの作りを変えても、このモジュールや
gui_uma.py を変更する必要がない。GUIの入力欄(ipywidgets)でトークンを受け取る方式は、
入力値がウィジェットの状態として保持され、保存されるノートブックに残りうるため採用しない。
"""

import os

MODEL_REPO_ID = "facebook/UMA"
HF_TOKEN_ENV = "HF_TOKEN"        # トークンの受け渡しに使う環境変数名(Hugging Face公式の標準)
LICENSE_FILENAME = "LICENSE"   # アクセス確認用に取得する小さなファイル(約6.5 kB)


class UmaSetupError(RuntimeError):
    """UMAを使うための準備(トークン・アクセス権・インストール)に問題があるときの例外。
    メッセージはそのままGUIのログに表示する前提で、日本語で分かりやすく書いている。
    """


# -----------------------------------------------------------------------------
# Hugging Face: トークンとアクセス権
# -----------------------------------------------------------------------------

def login_with_token(token):
    """Hugging Faceのアクセストークンを設定してログインする。

    トークンは環境変数HF_TOKENにも設定する(fairchemが内部でモデルを
    ダウンロードする際に参照されるため)。トークン自体を画面やログに出力しないこと。
    """
    token = (token or "").strip()
    if not token:
        raise UmaSetupError(
            "Hugging Faceのトークンが空です。ノートブックの"
            "「2. Hugging Faceのトークンを入力し、UMAへのアクセスを確認する」のセルをもう一度実行し、"
            "発行したトークン(hf_ で始まる文字列)を入力してください。")
    os.environ["HF_TOKEN"] = token
    try:
        from huggingface_hub import login
    except ImportError as e:
        raise UmaSetupError(
            "huggingface_hub がインストールされていません。"
            "「3. 依存ライブラリのインストール」のセルを実行してください。"
            f"(内部エラー: {e})") from e
    try:
        login(token=token, add_to_git_credential=False)
    except TypeError:
        # huggingface_hubの版によっては add_to_git_credential 引数を受け付けない場合がある
        login(token=token)


def login_from_environment():
    """環境変数 HF_TOKEN のトークンで、Hugging Faceにログインする。

    ノートブックの「2.」のセルは、受け取ったトークンを環境変数 HF_TOKEN にだけ設定する。
    この関数がそれを読み取ってログインする(トークンは、この関数の中の一時的な
    ローカル変数としてのみ扱い、モジュールの変数やファイルには保持しない)。
    """
    token = os.environ.get(HF_TOKEN_ENV, "")
    if not token.strip():
        raise UmaSetupError(
            "Hugging Faceのトークンが設定されていません。"
            "ノートブックの「2. Hugging Faceのトークンを入力し、UMAへのアクセスを確認する」のセルを"
            "実行してください。")
    login_with_token(token)


def has_hf_token():
    """Hugging Faceのトークンが設定済みか(環境変数、または保存済みログイン)。"""
    if os.environ.get("HF_TOKEN"):
        return True
    try:
        from huggingface_hub import get_token
        return bool(get_token())
    except Exception:
        return False


def explain_hf_error(error):
    """Hugging Face関連の例外を、利用者向けの日本語メッセージに整形して返す。"""
    name = type(error).__name__
    status = getattr(getattr(error, "response", None), "status_code", None)
    detail = f"(内部エラー: {name}: {error})"

    if name == "GatedRepoError" or status in (401, 403):
        return (
            "UMAのモデルにアクセスできませんでした。次の点を確認してください。\n"
            f"  1. https://huggingface.co/{MODEL_REPO_ID} を開き、利用条件に同意して"
            "アクセス申請を完了していること(承認まで時間がかかる場合があります)\n"
            "  2. 申請したのと同じHugging Faceアカウントでトークンを発行していること\n"
            "  3. トークンの権限に「Read」が含まれていること\n"
            "  4. トークンを間違って入力していないこと(ノートブックの「2.」のセルを、"
            "「FORCE_REENTER」にチェックを入れて実行し直してください)\n"
            + detail)
    if name in ("LocalEntryNotFoundError", "ConnectionError", "Timeout", "ConnectTimeout",
                "ReadTimeout", "OfflineModeIsEnabled") or status in (500, 502, 503, 504):
        return (
            "Hugging Faceに接続できませんでした。ネットワークの状態を確認し、"
            "しばらくしてからもう一度お試しください。\n" + detail)
    return "Hugging Faceからの取得に失敗しました。\n" + detail


def check_model_access():
    """UMAへのアクセス権があるかを、LICENSEファイル(小さなファイル)の取得で確認する。

    モデル本体(大きなファイル)を取得し始める前に、トークンの誤りや利用条件への
    未同意を、短い待ち時間で分かりやすく利用者に伝えるための確認。
    成功すると、取得したLICENSEファイルのパスを返す。
    """
    if not has_hf_token():
        raise UmaSetupError(
            "Hugging Faceのトークンが設定されていません。"
            "ノートブックの「2. Hugging Faceのトークンを入力し、UMAへのアクセスを確認する」のセルを"
            "実行してください。")
    try:
        from huggingface_hub import hf_hub_download
    except ImportError as e:
        raise UmaSetupError(
            "huggingface_hub がインストールされていません。"
            "「3. 依存ライブラリのインストール」のセルを実行してください。"
            f"(内部エラー: {e})") from e
    try:
        return hf_hub_download(repo_id=MODEL_REPO_ID, filename=LICENSE_FILENAME)
    except Exception as e:
        raise UmaSetupError(explain_hf_error(e)) from e


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
            raise UmaSetupError(
                "fairchem-core がインストールされていません。"
                "「3. 依存ライブラリのインストール」のセルを実行してください。"
                f"(内部エラー: {e})") from e
        try:
            _PREDICTOR_CACHE[key] = pretrained_mlip.get_predict_unit(model_name, device=device)
        except Exception as e:
            if type(e).__name__ == "GatedRepoError" or getattr(
                    getattr(e, "response", None), "status_code", None) in (401, 403):
                raise UmaSetupError(explain_hf_error(e)) from e
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
