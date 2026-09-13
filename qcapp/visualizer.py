"""
qcapp.visualizer
------------------
common.plot_common(計算エンジンに依存しない汎用部分)と
qcapp.visualizer_pyscf(PySCF固有の部分)を1つの名前空間にまとめた
ファサードモジュール。

qcapp/ と common/ を分割した際、gui.py側の呼び出し箇所
(`visualizer.plot_energy_convergence(...)` 等、10箇所以上)を
1つ1つ書き換えずに済むよう、このファイルを経由してどちらの関数も
`visualizer.関数名(...)` の形でそのまま呼べるようにしている。

新しくUMA専用の可視化コードを書く場合は、このファサードではなく
common.plot_common を直接importすること
(qcapp.visualizer_pyscf側の関数はPySCF専用のため使えない)。
"""

from common.plot_common import (  # noqa: F401
    plot_energy_convergence,
    energy_convergence_png,
    energy_convergence_html,
    render_trajectory,
    render_vibration,
)
from qcapp.visualizer_pyscf import (  # noqa: F401
    get_homo_lumo_indices,
    render_orbital,
    compute_mulliken_charges,
    compute_esp_at_atoms,
    atomic_charges_table_html,
    add_atom_charge_labels,
    add_atom_charge_spheres,
    add_atom_esp_spheres,
    render_charges,
    render_density,
)
