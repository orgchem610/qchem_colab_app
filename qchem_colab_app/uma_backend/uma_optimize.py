"""
uma_backend.uma_optimize
--------------------
ASEの最適化アルゴリズム(LBFGS等)とUMAを使った構造最適化。

結果を入れる入れ物(OptimizationResult)は、PySCF版(qchem_colab_app/pyscf_backend/optimize.py)と同じ
共通の親クラス(common_backend/optimization.py の OptimizationResult)を継承し、UMA固有の項目を足す。
これにより、gui/・common_backend/ の可視化・出力関数(エネルギー推移・構造表示・xyz出力)をそのまま使える。

    energies        : 各ステップのエネルギー [Hartree]  (UMA/ASEはeVで返すので換算する。親クラスの項目)
    coords_history  : 各ステップの座標 [Å]               (親クラスの項目)
    symbols         : 元素記号のリスト                    (親クラスの項目)

【収束判定】
ASEの慣例どおり、「各原子にかかる力の大きさ(3成分のノルム)の最大値(fmax)」が
指定値以下になれば収束とみなす。最大ステップ数に達しても収束しなかった場合は、
例外にはせず converged=False の結果を返す(それまでの履歴は確認できるため)。

【履歴の記録】
ASEの observer(opt.attach)は、バージョンによって初期構造で呼ばれるかどうかが
異なりうるため、(1)最適化の前に初期構造を、(2)最適化の後に最終構造を、
自分で必ず記録し、同じ座標が連続して記録された場合は重複を除いている。
"""

import time

import numpy as np

from qchem_colab_app.common_backend import energy, optimization

ALLOWED_OPTIMIZERS = ("LBFGS", "BFGS", "FIRE")


class OptimizationResult(optimization.OptimizationResult):
    """UMA版の構造最適化の結果。共通の項目に、UMA(ASE)の項目を足す。

    energies_ev    : 各ステップのエネルギー [eV]
    fmax_history   : 各ステップの力の最大値 [eV/Å]
    fmax_target    : 収束条件の力の最大値 [eV/Å]
    optimizer_name : 使った最適化アルゴリズム名
    max_steps      : 最大ステップ数
    final_fmax     : 最後のステップの力の最大値 [eV/Å](fmax_history から求める)
    """

    def __init__(self):
        super().__init__()
        self.energies_ev = []
        self.fmax_history = []
        self.fmax_target = None
        self.optimizer_name = ""
        self.max_steps = 0

    @property
    def final_fmax(self):
        return self.fmax_history[-1] if self.fmax_history else None


def run_geometry_optimization(atoms, calculator, opt_cfg, progress=None):
    """UMAで構造最適化を実行し、履歴付きの結果を返す。

    Parameters
    ----------
    atoms : charge/spinがinfoに設定済みのASE Atoms(uma_engine.build_atoms()の戻り値)
    calculator : uma_engine.make_calculator()の戻り値
    opt_cfg : config/uma_defaults.yaml の geometry_optimization 節
    progress : 各ステップごとに progress(step, energy_hartree, fmax_ev_per_angstrom)
               を呼ぶ関数(省略可)。長い計算の途中経過をGUIに出すために使う。
    """
    name = opt_cfg.get("optimizer", "LBFGS")
    if name not in ALLOWED_OPTIMIZERS:
        raise ValueError(
            f"未対応の最適化アルゴリズム '{name}' が設定されています"
            f"(対応: {', '.join(ALLOWED_OPTIMIZERS)})。config/uma_defaults.yaml を確認してください。")

    from ase import optimize as ase_optimize
    optimizer_cls = getattr(ase_optimize, name)
    fmax_target = float(opt_cfg["fmax_ev_per_angstrom"])
    max_steps = int(opt_cfg["max_steps"])

    result = OptimizationResult()
    result.symbols = [str(s) for s in atoms.get_chemical_symbols()]
    result.fmax_target = fmax_target
    result.optimizer_name = name
    result.max_steps = max_steps

    work = atoms.copy()          # 呼び出し元のAtomsは変更しない(infoは引き継がれる)
    work.calc = calculator

    def record():
        positions = np.array(work.get_positions(), dtype=float)
        if result.coords_history and np.array_equal(positions, np.asarray(result.coords_history[-1])):
            return                                   # 同じ構造の重複記録を避ける
        energy_ev = float(work.get_potential_energy())
        forces = np.asarray(work.get_forces(), dtype=float)
        fmax_now = float(np.linalg.norm(forces, axis=1).max()) if len(forces) else 0.0
        result.coords_history.append(positions.tolist())
        result.energies_ev.append(energy_ev)
        result.energies.append(energy_ev / energy.HARTREE_TO_EV)
        result.fmax_history.append(fmax_now)
        if progress is not None:
            progress(len(result.energies) - 1, result.energies[-1], fmax_now)

    t0 = time.perf_counter()
    record()                                         # 初期構造
    optimizer = optimizer_cls(work, logfile=None)
    optimizer.attach(record, interval=1)
    optimizer.run(fmax=fmax_target, steps=max_steps)
    record()                                         # 最終構造(念のため)
    result.elapsed_seconds = time.perf_counter() - t0

    result.converged = result.final_fmax is not None and result.final_fmax <= fmax_target
    return result
