"""
qcapp.writer_molden
--------------------
最終構造・分子軌道をMolden形式(.molden)で書き出すモジュール。

Molden形式を共通出力フォーマットとして採用している理由:
GaussView・MacMolPlt・Avogadro・Multiwfnなど、対応ソフトが幅広く、
構造とMO(分子軌道)の両方を1つのファイルに含められるため。
"""


def write_molden(mf, filepath: str) -> None:
    """収束済みのCPU版SCFオブジェクトからMoldenファイルを書き出す。

    Parameters
    ----------
    mf : 収束済み(mf.converged == True)の pyscf CPU SCF オブジェクト
    filepath : 出力先のパス(例: "final_structure.molden")
    """
    from pyscf.tools import molden

    # PySCFのバージョンによって用意されている簡便関数の名前が異なる可能性が
    # あるため、複数の候補を順番に試す(頑健性重視の実装)。
    # 全て失敗した場合は、最も低レベルなAPI(header + orbital_coeff)で書き出す。
    for func_name in ("from_scf", "dump_scf"):
        func = getattr(molden, func_name, None)
        if callable(func):
            func(mf, filepath)
            return

    with open(filepath, "w", encoding="utf-8") as f:
        molden.header(mf.mol, f)
        molden.orbital_coeff(mf.mol, f, mf.mo_coeff, ene=mf.mo_energy, occ=mf.mo_occ)
