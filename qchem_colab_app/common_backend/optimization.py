"""
common_backend.optimization
---------------------------
構造最適化の結果を入れる入れ物(PySCF版・UMA版の共通の親クラス)。

    - OptimizationResult : 元素記号・エネルギー・座標の履歴・収束状態・所要時間

PySCFにも、ASEにも、UMAにも依存しない。PySCF版(pyscf_backend/optimize.py)とUMA版
(uma_backend/uma_optimize.py)は、それぞれ、この親クラスを継承した子クラス(同じ名前の
OptimizationResult)で、エンジン固有の項目を足す。これにより、画面(gui/parts.py の
EnergyStructureViewer)や出力関数(common_backend/writer_xyz.py)は、エンジンを区別せずに、
共通の項目だけを使える。振動数解析の結果(common_backend/vibration.py の FrequencyResult)と同じ構成である。
"""


class OptimizationResult:
    """構造最適化の結果。PySCF版・UMA版で共通の項目を持つ(エンジン固有の項目は、子クラスで足す)。

    symbols         : 元素記号のリスト 例: ["O", "H", "H"]
    energies        : 各ステップのエネルギー [Hartree]
    coords_history  : 各ステップの座標 [Å]。要素は [[x, y, z], ...]
    converged       : 収束したか
    elapsed_seconds : 所要時間 [秒]
    """

    def __init__(self):
        self.symbols = []
        self.energies = []
        self.coords_history = []
        self.converged = False
        self.elapsed_seconds = 0.0
