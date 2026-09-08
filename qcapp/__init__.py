"""
qcapp: Google Colab上で動作する量子化学計算プロトタイプのコアパッケージ

このパッケージは、ColabApp.ipynb から呼び出される実処理をまとめたものです。
ノートブック自体にはロジックを書かず、ここに切り出すことで
    - 過去バージョンとの差分をGitで追いやすくする
    - 単体でのテスト・デバッグをしやすくする
    - 将来の機能追加(B3LYPや他の基底関数の追加など)を
      設定ファイル(config/*.yaml)の編集だけで完結させる
ことを狙っています。

バージョン情報:
  __version__ はこのプロトタイプの版数です。CHANGELOG.md と対応しています。
"""

from pathlib import Path
import yaml

__version__ = "0.1.0"  # v0.1.0 = HF / 3-21G のみの最小プロトタイプ

# qchem_colab_app/ がプロジェクトのルート、config/ がその直下にある前提
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"


def load_yaml(filename: str):
    """config/ディレクトリ配下のYAMLファイルを読み込んで返す共通関数。

    Parameters
    ----------
    filename : str
        例: "purposes.yaml"

    Returns
    -------
    読み込んだ内容(list または dict。ファイルの中身に依存)

    Notes
    -----
    設定ファイルが1か所からしか読まれないようにすることで、
    「GUI用のYAML読み込みロジック」と「計算エンジン用のYAML読み込みロジック」が
    将来ズレてしまう(=保守性が下がる)ことを防いでいます。
    """
    path = CONFIG_DIR / filename
    if not path.exists():
        raise FileNotFoundError(
            f"設定ファイルが見つかりません: {path}\n"
            f"qchem_colab_app/config/ 以下にYAMLファイルが正しく配置されているか確認してください。"
        )
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
