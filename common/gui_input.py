"""
common.gui_input
----------------
GUI(gui.py / gui_uma.py)の「入力」まわりの、画面部品(ipywidgets)に依存しない関数群。
ipywidgetsがなくても単体テストできるよう、画面部品(common/gui_parts.py)から分けてある。

    - extract_uploaded_file    : アップロード(またはドロップ)された構造ファイルの取り出し
    - read_uploaded_structure  : 取り出した構造ファイルの読み込み(検証はしない。受け取った構造の表示用)
    - describe_structure       : 読み込んだ構造の概要(ファイル名・原子数・組成)の文字列
    - load_uploaded_structure  : 取り出した構造ファイルの読み込みと、計算前の検証
    - format_charge / parse_charge / ChargeInputError
                               : 電荷の表示(正の値は「+1」の形)と、入力欄の文字列の読み取り

ダウンロードするファイル名など、「出力」まわりの関数は common/gui_output.py にある
(v0.2.1で、以前の common/gui_helpers.py を、入力と出力に分けた)。
計算エンジン(PySCF・UMA)には依存しない。
"""

import os
import re
import tempfile
import unicodedata

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


def read_uploaded_structure(content, filename):
    """アップロードされた構造ファイルの中身(bytes)を読み込み、Structure を返す。

    拡張子で形式を判定するため、一時ファイルにも同じ拡張子を付ける(拡張子がなければ .xyz とみなす)。
    一時ファイルは、読み込み後に削除する。原子間距離や電荷・多重度の検証はしない
    (受け取った構造をすぐ表示するときに使う。計算前の検証は load_uploaded_structure)。
    読み込めない場合は、io_reader.StructureError を送出する。
    """
    extension = os.path.splitext(str(filename or ""))[1] or ".xyz"
    fd, tmp_path = tempfile.mkstemp(suffix=extension)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(content)
        return io_reader.read_structure(tmp_path)
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def describe_structure(structure, filename):
    """読み込んだ構造の概要(ファイル名・原子数・組成)を、1行の文字列にする。"""
    return (f"ファイル: {filename}  原子数: {len(structure.symbols)}  組成: "
            f"{', '.join(sorted(set(structure.symbols)))}")


def load_uploaded_structure(content, filename, charge, multiplicity, min_distance, log=print):
    """アップロードされた構造ファイルの中身(bytes)を読み込み、計算できる構造かを検証して返す。

    PySCF版・UMA版のどちらも、計算の前に同じ入力チェックを行う。
        1. 構造ファイルを読み込む(read_uploaded_structure)
        2. 読み込んだ構造の概要(ファイル名・原子数・組成)を log に出す
        3. 原子どうしが近すぎないか(min_distance[Å]未満の原子対がないか)を検証する
        4. 電荷とスピン多重度が、電子数と矛盾しないか検証する
    読み込み・検証に失敗した場合は、io_reader.StructureError(または ValueError)を送出する。
    それ以降の処理(遷移金属の判定など、エンジンごとに異なる確認)は、呼び出し側で行う。
    """
    structure = read_uploaded_structure(content, filename)
    log(f"[入力構造] {describe_structure(structure, filename)}")

    io_reader.validate_structure(structure, min_distance)
    io_reader.validate_charge_and_multiplicity(structure, charge, multiplicity)
    return structure


class ChargeInputError(ValueError):
    """電荷として読み取れない入力のときの例外。メッセージはそのままGUIに表示できる。"""


def format_charge(value):
    """電荷の整数を表示用の文字列にする。正の値は +1、0は 0、負の値は -1 のように表示する。"""
    value = int(value)
    return f"{value:+d}" if value > 0 else str(value)


def parse_charge(text):
    """入力欄の文字列を電荷(整数)に変換する。

    「1」「+1」「-1」「0」のほか、全角の数字・記号(「＋１」「－１」)や、
    符号と数字の間の空白(「+ 1」)も受け付ける。
    整数として読み取れない場合は ChargeInputError を送出する。
    """
    # NFKCで全角の数字・「＋」「－」を半角にそろえる。U+2212(−)・長音(ー)はマイナスとして扱う。
    normalized = unicodedata.normalize("NFKC", str(text if text is not None else ""))
    normalized = normalized.replace("\u2212", "-").replace("ー", "-")
    # 空白は、前後と「符号と数字の間」だけ許す(「1 2」を「12」と解釈してしまわないため)
    match = re.fullmatch(r"\s*([+-]?)\s*([0-9]+)\s*", normalized)
    if match is None:
        raise ChargeInputError(
            "電荷は整数で入力してください(例: 0, 1, +1, -1)。直前の値に戻しました。")
    return int(match.group(1) + match.group(2))
