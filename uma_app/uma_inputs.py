"""
uma_app.uma_inputs
------------------
GUIの入力欄まわりの、画面部品(ipywidgets)に依存しない小さな関数群。
単体テストできるよう、gui_uma.py から切り出してある。

    - 電荷の入力・表示(正の値は「+1」のように符号付きで表示する)
    - ダウンロードするファイル名の既定値(「入力ファイル名_result」)
"""

import os
import re
import unicodedata


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
