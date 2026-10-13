"""
common.gui_helpers
------------------
GUI(gui.py / gui_uma.py)まわりの、画面部品(ipywidgets)に依存しない小さな関数群。
ipywidgetsがなくても単体テストできるよう、画面部品(common/gui_parts.py)から分けてある。

    - extract_uploaded_file      : アップロード(またはドロップ)された構造ファイルの取り出し
    - sanitize_filename_stem     : ダウンロードするファイル名(拡張子なし)の整形
    - default_download_stem      : ファイル名の既定値(「入力ファイル名_result」)

計算エンジン(PySCF・UMA)には依存しない。
"""

import os
import re

from common import io_reader


def extract_uploaded_file(upload_widget, dropped_file=None):
    """アップロードされたファイルの中身(bytes)とファイル名を取り出す。

    dropped_file({"name":..., "content":...})が渡された場合は、ドラッグ&ドロップ
    領域で受け取ったファイルを優先する。そうでなければ、ipywidgets 7.x / 8.x
    どちらのFileUpload.valueの形にも対応して取り出す。

    ファイル名(拡張子)は、.xyz以外の形式(.com/.gjf/.pdb)をASE経由で
    読み込む際に、どの形式として扱うかを判定するために必要。
    """
    if dropped_file is not None:
        return bytes(dropped_file["content"]), dropped_file["name"]

    value = upload_widget.value
    if not value:
        raise io_reader.StructureError(
            "構造ファイルがアップロードされていません。"
            "ドロップ領域にファイルをドラッグ&ドロップするか、「ファイルを選択」ボタンから"
            "ファイルを選択してください。"
        )

    # ipywidgets 8.x: tuple[dict] (各要素が name/type/size/content を持つ)
    if isinstance(value, (tuple, list)):
        first = value[0]
        if isinstance(first, dict):
            return bytes(first["content"]), first["name"]
        return bytes(first.content), first.name

    # ipywidgets 7.x: dict[filename] -> {"content": ..., ...}
    if isinstance(value, dict):
        filename, first = next(iter(value.items()))
        return bytes(first["content"]), filename

    raise RuntimeError(
        f"想定外の形式のFileUpload.valueを受け取りました(型: {type(value)})。"
        "ipywidgetsのバージョンを確認してください(7.x・8.xに対応しています)。"
    )


def sanitize_filename_stem(raw):
    """ファイル名(拡張子なし)として使えない文字を除去する。空なら 'result' にする。"""
    stem = re.sub(r'[\\/:*?"<>|]', "", (raw or "").strip())
    return stem or "result"


def default_download_stem(input_filename):
    """ダウンロードするファイル名の既定値(拡張子なし)を、入力ファイル名から作る。

    例: "water.xyz" -> "water_result"。入力ファイル名が使えない場合は "result"。
    """
    name = os.path.basename(str(input_filename or "").replace("\\", "/"))
    # 「.xyz」のように拡張子しかない名前には、ファイル名の本体がないものとして扱う
    stem = "" if re.fullmatch(r"\.[^.]*", name) else os.path.splitext(name)[0].lstrip(".")
    stem = re.sub(r'[\\/:*?"<>|]', "", stem).strip()
    return f"{stem}_result" if stem else "result"
