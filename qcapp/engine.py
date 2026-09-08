"""
qcapp.engine
------------
PySCF の Mole オブジェクト・SCF オブジェクトの構築、
および SCF 実行(収束チェック・自動リトライ)を担当するモジュール。

GPU4PySCF がインストールされ、かつ実際に初期化に成功した場合はGPUで、
それ以外の場合は自動的に通常のCPU版PySCFにフォールバックして計算する
(「条件付きでGPU4PySCF、ダメならCPUに自動フォールバック」という方針)。

注意:
  GPU4PySCFはColab側のCUDAドライバのバージョンに強く依存するパッケージであり、
  かつパッケージ自体のバージョニング(gpu4pyscf / gpu4pyscf-cuda11x /
  gpu4pyscf-cuda12x)が頻繁に変わっているため、このモジュールでは
  「使えたら使う、ダメなら黙ってCPUに切り替える」というベストエフォートの
  実装にしている。requirements.txt でもGPU4PySCFはあえて厳密にバージョン
  固定していない(詳細はrequirements.txtのコメント参照)。
"""

import warnings

from qcapp import load_yaml
from qcapp.io_reader import Structure


class SCFConvergenceError(RuntimeError):
    """SCF計算が収束しなかったときの例外。日本語の説明文を持つ。"""
    pass


def _load_functional(functional_key: str) -> dict:
    functionals = load_yaml("functionals.yaml")
    for item in functionals:
        if item["key"] == functional_key:
            return item
    raise ValueError(f"計算手法 '{functional_key}' は config/functionals.yaml に登録されていません。")


def _load_basis(basis_key: str) -> dict:
    basis_sets = load_yaml("basis_sets.yaml")
    for group in ("main_group", "transition_metal_ecp"):
        for item in basis_sets.get(group) or []:
            if item["key"] == basis_key:
                return item
    raise ValueError(f"基底関数 '{basis_key}' は config/basis_sets.yaml に登録されていません。")


def build_mole(structure: Structure, charge: int, multiplicity: int, basis_key: str, verbose: int = 0):
    """io_reader.Structure から pyscf.gto.Mole を構築する。"""
    from pyscf import gto

    basis_info = _load_basis(basis_key)

    mol = gto.Mole()
    mol.atom = [[sym, tuple(xyz)] for sym, xyz in zip(structure.symbols, structure.coords)]
    mol.unit = "Angstrom"
    mol.basis = basis_info["pyscf_basis"]
    if basis_info.get("ecp"):
        mol.ecp = basis_info["ecp"]
    mol.charge = charge
    mol.spin = multiplicity - 1  # PySCFのspinは (n_alpha - n_beta) = multiplicity - 1 の意味
    mol.verbose = verbose
    mol.build()
    return mol


def _try_import_gpu4pyscf():
    """GPU4PySCFのインポートを試みる。成功すればモジュールを、失敗すればNoneを返す。"""
    try:
        import gpu4pyscf  # noqa: F401
        return gpu4pyscf
    except Exception:
        return None


def build_scf(mol, functional_key: str, try_gpu: bool = True):
    """SCF(HFまたはDFT)オブジェクトを構築する。

    Returns
    -------
    (mf, used_gpu, message) のタプル。
      mf       : pyscf または gpu4pyscf のSCFオブジェクト
      used_gpu : GPUを使えたかどうか(bool)
      message  : GPU利用可否についてGUIに表示するための日本語メッセージ
    """
    functional = _load_functional(functional_key)
    is_closed_shell = (mol.spin == 0)

    if try_gpu:
        gpu4pyscf = _try_import_gpu4pyscf()
        if gpu4pyscf is not None:
            try:
                if functional["engine"] == "hf":
                    from gpu4pyscf import scf as gpu_scf
                    mf = gpu_scf.RHF(mol) if is_closed_shell else gpu_scf.UHF(mol)
                else:
                    from gpu4pyscf import dft as gpu_dft
                    mf = gpu_dft.RKS(mol) if is_closed_shell else gpu_dft.UKS(mol)
                    mf.xc = functional["xc"]
                return mf, True, "GPU (GPU4PySCF) が検出されたため、GPUで計算します。"
            except Exception as e:
                warnings.warn(f"GPU4PySCFの初期化に失敗したため、CPUにフォールバックします: {e}")
        else:
            pass  # GPU4PySCF未インストール。下のCPU分岐に進む。

    from pyscf import scf as cpu_scf
    if functional["engine"] == "hf":
        mf = cpu_scf.RHF(mol) if is_closed_shell else cpu_scf.UHF(mol)
    else:
        from pyscf import dft as cpu_dft
        mf = cpu_dft.RKS(mol) if is_closed_shell else cpu_dft.UKS(mol)
        mf.xc = functional["xc"]

    return mf, False, "CPU (通常のPySCF) で計算します。"


def run_scf(mf, defaults: dict):
    """SCFを実行し、収束しなければ収束条件を緩めて1回だけ自動リトライする。

    それでも収束しない場合は SCFConvergenceError を、原因の当たりと
    対策を添えた日本語メッセージ付きで送出する。
    """
    scf_cfg = defaults["scf"]
    mf.conv_tol = scf_cfg["conv_tol"]
    mf.max_cycle = scf_cfg["max_cycle"]
    mf.kernel()

    if mf.converged:
        return mf

    warnings.warn("1回目のSCFが収束しませんでした。収束条件を緩め、レベルシフトを付与して再計算します。")
    mf.conv_tol = scf_cfg["retry_conv_tol"]
    mf.max_cycle = scf_cfg["retry_max_cycle"]
    try:
        mf.level_shift = scf_cfg["retry_level_shift"]
    except Exception:
        pass
    mf.kernel()

    if not mf.converged:
        raise SCFConvergenceError(
            "SCF計算が収束しませんでした。\n"
            "考えられる原因と対策:\n"
            "  ・初期構造が実際の分子構造から大きくかけ離れている\n"
            "      → GaussViewやAvogadroなどで一度構造を目視確認してください。\n"
            "  ・電荷やスピン多重度の設定が誤っている\n"
            "      → 分子の総電子数と設定値が矛盾していないか確認してください。\n"
            "  ・基底関数が対象元素に対応していない、あるいは小さすぎる\n"
            "      → 基底関数の選択を見直してください。\n"
            "これらを確認しても解決しない場合は、初期構造ファイルを"
            "変更するか、別の初期構造から再度お試しください。"
        )
    return mf
