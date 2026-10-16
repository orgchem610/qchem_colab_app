"""
common.gui_output
-----------------
GUI(gui.py / gui_uma.py)の「出力」(ダウンロード)まわりの、画面部品(ipywidgets)に依存しない関数群。
ipywidgetsがなくても単体テストできるよう、画面部品(common/gui_parts.py)から分けてある。

    - sanitize_filename_stem : ダウンロードするファイル名(拡張子なし)の整形
    - default_download_stem  : ファイル名の既定値(「入力ファイル名_result」)
    - xyz_download_items     : 最終構造・トラジェクトリのダウンロード項目(DownloadPanel.show に渡す)

アップロードされたファイルの取り出しなど、「入力」まわりの関数は common/gui_input.py にある
(v0.2.1で、以前の common/gui_helpers.py を、入力と出力に分けた)。
計算エンジン(PySCF・UMA)には依存しない。
"""

import os
import re

# ファイル名に使えない文字(Windows等で禁止されている文字)
_FORBIDDEN_FILENAME_CHARS = r'[\\/:*?"<>|]'


def sanitize_filename_stem(raw):
    """ファイル名(拡張子なし)として使えない文字を除去する。空なら 'result' にする。"""
    stem = re.sub(_FORBIDDEN_FILENAME_CHARS, "", (raw or "").strip())
    return stem or "result"


def default_download_stem(input_filename):
    """ダウンロードするファイル名の既定値(拡張子なし)を、入力ファイル名から作る。

    例: "water.xyz" -> "water_result"。入力ファイル名が使えない場合は "result"。
    """
    name = os.path.basename(str(input_filename or "").replace("\\", "/"))
    # 「.xyz」のように拡張子しかない名前には、ファイル名の本体がないものとして扱う
    stem = "" if re.fullmatch(r"\.[^.]*", name) else os.path.splitext(name)[0].lstrip(".")
    stem = re.sub(_FORBIDDEN_FILENAME_CHARS, "", stem).strip()
    return f"{stem}_result" if stem else "result"


def xyz_download_items(final_xyz_path, trajectory_path):
    """最終構造・最適化トラジェクトリの、ダウンロード項目を作る(PySCF版・UMA版で共通)。

    戻り値は DownloadPanel.show() に渡す形式のリスト。各要素は
    (説明, ファイルのパス, ダウンロード名の末尾, ボタンに表示する名前)。
    エンジンごとに違う項目(moldenや計算ログなど)は、呼び出し側でこのリストに足す。
    """
    return [
        ("最終構造(ColabReactionにそのままアップロード可能)",
         final_xyz_path, ".xyz", "最終構造"),
        ("最適化トラジェクトリ(多フレーム)",
         trajectory_path, "_traj.xyz", "トラジェクトリ"),
    ]
