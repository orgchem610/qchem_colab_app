"""
common_backend.ase_bridge
-------------------------
共通の構造(io_reader.Structure)を、ASE(Atomic Simulation Environment)のオブジェクトに変換する。
計算エンジン(UMA・PySCF)にも画面にも依存しない。

    - structure_to_atoms() : Structure -> ase.Atoms(元素記号と座標だけ)

電荷・スピン多重度を `atoms.info` のどのキーに入れるかは、計算器ごとの約束(例: fairchemのomolタスク)のため、
ここでは設定しない(uma_backend/uma_engine.py の build_atoms が設定する)。
aseは、関数の中でimportする。入っていない環境でも、このモジュール自体は読み込める。
"""


def structure_to_atoms(structure):
    """共通の構造(symbols・coords を持つ)から、ASE の Atoms を作る。座標の単位は Å。"""
    from ase import Atoms
    return Atoms(symbols=list(structure.symbols),
                 positions=[list(c) for c in structure.coords])
