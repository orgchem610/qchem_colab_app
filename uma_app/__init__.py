"""
uma_app: 機械学習ポテンシャルUMAを計算エンジンとする構造最適化・振動数解析のコアパッケージ

このパッケージは、ColabApp_UMA.ipynb(+ ルート直下の gui_uma.py)から呼び出される、
UMA(ASE + fairchem-core)に固有の処理をまとめたものです。

【依存関係の方針】(README.md「将来的な構成: UMA利用版」「common/qcappに分けた理由」参照)
    - 計算エンジンに依存しない共通部品は、リポジトリ直下の common/ から使う。
    - PySCF専用の qcapp/ には一切依存しない(PySCFがインストールされていない
      UMA用の環境でも動くようにするため)。そのため、設定ファイルの読み込み関数と
      バージョン番号は、qcapp と共有せず、このファイルに独立して持っている。
    - 設定ファイルは、PySCF版と同じ config/ ディレクトリに、uma_ で始まる
      別名のファイルとして置いている(PySCF版の設定には影響しない)。

【バージョン番号】
    __version__ はリポジトリ全体のリリース番号(Gitタグ)と同じ値にします。
    qcapp/__init__.py の __version__ とも必ず同じ値にしてください
    (食い違うと tests/test_version_sync.py が失敗します)。
"""

from pathlib import Path

import yaml

__version__ = "0.2.0"

# uma_app/ の1つ上がリポジトリのルート、config/ がその直下にある前提
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"


def load_yaml(filename: str):
    """config/ディレクトリ配下のYAMLファイルを読み込んで返す。

    Parameters
    ----------
    filename : str
        例: "uma_defaults.yaml"
    """
    path = CONFIG_DIR / filename
    if not path.exists():
        raise FileNotFoundError(
            f"設定ファイルが見つかりません: {path}\n"
            "config/ 以下にYAMLファイルが正しく配置されているか確認してください。"
        )
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
