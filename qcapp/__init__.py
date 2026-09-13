"""
qcapp: PySCFを計算エンジンとするab initio量子化学計算のコアパッケージ

このパッケージは、ColabApp.ipynb から呼び出される、PySCFに固有の実処理を
まとめたものです。ノートブック自体にはロジックを書かず、ここに切り出すことで
    - 過去バージョンとの差分をGitで追いやすくする
    - 単体でのテスト・デバッグをしやすくする
    - 計算手法・基底関数の追加を設定ファイル(config/*.yaml)の編集だけで
      完結させる(ただし、構造最適化以外の新しい「計算目的」自体の追加には
      新しいコードが必要。詳細はREADME.md参照)
ことを狙っています。

計算エンジン(PySCF)に依存しない汎用コード(構造の読み込み・検証・xyz出力・
可視化の基本部分)は、このパッケージの外、リポジトリ直下の`common/`パッケージに
分離しています(将来追加予定のUMA版アプリとも共有するため)。

バージョン情報:
  __version__ はこのプロトタイプの版数です。
"""

from pathlib import Path
import yaml

__version__ = "0.1.12"  # 現在のGitタグと合わせて更新すること(更新を忘れやすいので要注意)

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
