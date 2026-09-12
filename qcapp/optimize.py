"""
qcapp.optimize
--------------
PySCF の geomeTRIC 連携(pyscf.geomopt.geometric_solver)を用いた構造最適化。

内部座標を用いる geomeTRIC を採用している理由:
単純なデカルト座標でのBFGS法などに比べ、有機分子のような柔らかい構造でも
少ないステップ数で収束しやすく、Gaussian等の実務的な量子化学計算ソフトでも
広く使われている実装方式であるため。「振動数計算までの合計時間の計測」を
実運用に近い条件で行うという目的にも合致する。

【実装上の注意】(初回実行時に確認していただきたい点)
pyscf.geomopt.geometric_solver.optimize() の callback に渡される辞書(envs)の
キー名は、PySCFのバージョンによって細部が異なる可能性がある。
本開発環境ではネットワーク制限のためPySCFを実際にインストールして
動作確認することができなかったため、_make_callback() は複数の候補キー名を
試す作りにしてあるが、実際のColab環境で最初に実行した際、
「最適化ステップ数」に対して「記録されたエネルギー履歴の数」が
明らかに少ない(例:1点しかない)場合は、このファイルの _make_callback()
内のキー名(envs.get(...)の引数)を調整する必要がある可能性が高い。
"""

import time
import warnings


class OptimizationResult:
    def __init__(self):
        self.mol_final = None
        self.used_gpu = False
        self.gpu_message = ""
        self.energies = []        # 各ステップのエネルギー(Hartree)
        self.coords_history = []  # 各ステップの座標(Å)。要素は [[x,y,z], ...]
        self.symbols = []
        self.converged = False
        self.elapsed_seconds = 0.0
        self.dm0_guess = None     # 最終ステップの密度行列(CPU再計算の初期値用、取得できない場合はNone)


def _to_numpy(arr):
    """cupy配列(GPU4PySCF使用時)・numpy配列のどちらが来ても素直にnumpy配列にする。"""
    import numpy as np
    if hasattr(arr, "get"):  # cupy.ndarrayはCPUへ転送する.get()メソッドを持つ
        return arr.get()
    return np.asarray(arr)


def _make_callback(result: "OptimizationResult"):
    """geomeTRICの各ステップで呼ばれるコールバック関数を作る(頑健性重視の実装)。"""

    def callback(envs):
        try:
            energy = envs.get("energy", envs.get("e_tot"))
            mol_step = envs.get("mol")

            if mol_step is not None:
                coords = mol_step.atom_coords(unit="Angstrom")
                symbols = [mol_step.atom_symbol(i) for i in range(mol_step.natm)]
                if not result.symbols:
                    result.symbols = list(symbols)
            else:
                coords = envs.get("coords")

            if energy is not None:
                result.energies.append(float(energy))
            if coords is not None:
                result.coords_history.append([list(c) for c in coords])
        except Exception as e:
            # 1ステップ分の記録に失敗しても最適化自体は止めない
            warnings.warn(f"最適化ステップの履歴記録に失敗しました(計算自体は継続します): {e}")

    return callback


def run_geometry_optimization(mol, functional_key: str, defaults: dict, try_gpu: bool = True) -> "OptimizationResult":
    """構造最適化を実行し、エネルギー・座標の履歴と所要時間を記録して返す。"""
    from pyscf.geomopt.geometric_solver import optimize
    from qcapp import engine

    result = OptimizationResult()
    result.symbols = [mol.atom_symbol(i) for i in range(mol.natm)]

    mf, used_gpu, gpu_message = engine.build_scf(mol, functional_key, try_gpu=try_gpu)
    result.used_gpu = used_gpu
    result.gpu_message = gpu_message

    opt_cfg = defaults["geometry_optimization"]
    callback = _make_callback(result)

    t0 = time.perf_counter()
    try:
        try:
            # convergence_set は geomeTRIC 側の収束基準プリセット("GAU"など)。
            # PySCFのバージョンによってはこのキーワード引数を受け付けない
            # 場合があるため、まず渡してみて失敗したら外して再試行する。
            mol_final = optimize(
                mf, maxsteps=opt_cfg["max_cycle"],
                convergence_set=opt_cfg.get("convergence_set", "GAU"),
                callback=callback,
            )
        except TypeError:
            mol_final = optimize(mf, maxsteps=opt_cfg["max_cycle"], callback=callback)
        result.converged = True
    except Exception as e:
        raise RuntimeError(
            "構造最適化が収束しませんでした。\n"
            f"(内部エラー: {e})\n"
            "考えられる対策:\n"
            "  ・初期構造を見直す(明らかにおかしい結合長・結合角がないか)\n"
            "  ・電荷・スピン多重度の設定を見直す\n"
            "  ・config/defaults.yaml の geometry_optimization.max_cycle を増やす"
        ) from e
    result.elapsed_seconds = time.perf_counter() - t0
    result.mol_final = mol_final

    # CPU側での再計算(engine.pyでの分子軌道・電荷・振動数解析用のSCF)を
    # 高速化するため、最後に使われた密度行列を初期値の候補として保持しておく。
    # 同じ幾何構造でのSCFなので、既定の初期値(原子密度の重ね合わせ)より
    # 収束が大幅に速くなることが期待できる。取得できなくても
    # (=Noneのままでも)以降の処理には支障がない、あくまで高速化用のヒント。
    try:
        result.dm0_guess = _to_numpy(mf.make_rdm1())
    except Exception:
        result.dm0_guess = None

    # コールバックで最終ステップを取り損ねている場合に備え、
    # 最後に必ず「最終構造」を明示的に記録しておく(エネルギーは後段で
    # CPU上で計算し直すため、ここでは座標のみ保証する)。
    final_coords = [list(c) for c in mol_final.atom_coords(unit="Angstrom")]
    if not result.coords_history or result.coords_history[-1] != final_coords:
        result.coords_history.append(final_coords)

    return result
