"""
qchem_colab_app.common_backend.config
-------------------------------------
config/ ディレクトリ配下のYAMLファイルを読み込む共通関数。

PySCF版(pyscf_backend)・UMA版(uma_backend)のどちらも、同じ config/ ディレクトリの設定ファイルを
読むため、読み込みの処理をここに1つだけ置いている(以前は、2つのパッケージの
__init__.py に同じ内容が重複していた)。pyscf_backend.load_yaml・uma_backend.load_yaml は、
この関数をそのまま使えるようにした別名で、呼び出し側は変わらない。
"""

from pathlib import Path

import yaml

# このファイルは <リポジトリ>/qchem_colab_app/common_backend/ にあり、3つ上がリポジトリのルート、
# config/ がその直下にある前提(v0.2.2で、最上位パッケージ qchem_colab_app の下に移したため、2つから3つになった)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"


def load_yaml(filename: str):
    """config/ディレクトリ配下のYAMLファイルを読み込んで返す。

    Parameters
    ----------
    filename : str
        例: "purposes.yaml"、"uma_defaults.yaml"

    Returns
    -------
    読み込んだ内容(list または dict。ファイルの中身に依存)
    """
    path = CONFIG_DIR / filename
    if not path.exists():
        raise FileNotFoundError(
            f"設定ファイルが見つかりません: {path}\n"
            "config/ 以下にYAMLファイルが正しく配置されているか確認してください。"
        )
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
