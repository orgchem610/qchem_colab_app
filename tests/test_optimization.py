"""
tests/test_optimization.py
--------------------------
common_backend.optimization(構造最適化の結果の、PySCF版・UMA版の共通の親クラス)の単体テスト。
子クラス(pyscf_backend.optimize・uma_backend.uma_optimize の OptimizationResult)が、
共通の項目を親から引き継ぎ、エンジン固有の項目だけを足していることも確認する。
PySCF・ASE・UMAは使わない(子クラスのモジュールは、これらを関数の中でだけ読み込む)。
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from qchem_colab_app.common_backend import optimization, writer_xyz  # noqa: E402
from qchem_colab_app.pyscf_backend import optimize  # noqa: E402
from qchem_colab_app.uma_backend import uma_optimize  # noqa: E402

COMMON_ITEMS = ("symbols", "energies", "coords_history", "converged", "elapsed_seconds")
COORDS = [[0.0, 0.0, 0.0], [0.96, 0.0, 0.0], [-0.24, 0.93, 0.0]]


class TestOptimizationResult(unittest.TestCase):
    def test_it_starts_empty(self):
        result = optimization.OptimizationResult()
        self.assertEqual(result.symbols, [])
        self.assertEqual(result.energies, [])
        self.assertEqual(result.coords_history, [])
        self.assertFalse(result.converged)
        self.assertEqual(result.elapsed_seconds, 0.0)

    def test_two_results_do_not_share_their_lists(self):
        first, second = optimization.OptimizationResult(), optimization.OptimizationResult()
        first.energies.append(-76.0)
        first.coords_history.append(COORDS)
        self.assertEqual(second.energies, [])
        self.assertEqual(second.coords_history, [])


class TestResultOfPyscf(unittest.TestCase):
    def test_it_extends_the_common_result_with_the_pyscf_items(self):
        result = optimize.OptimizationResult()
        self.assertIsInstance(result, optimization.OptimizationResult)
        for name in COMMON_ITEMS:
            self.assertTrue(hasattr(result, name), name)
        self.assertIsNone(result.mol_final)
        self.assertFalse(result.used_gpu)
        self.assertEqual(result.gpu_message, "")
        self.assertIsNone(result.dm0_guess)

    def test_the_common_items_work_in_the_subclass(self):
        result = optimize.OptimizationResult()
        result.energies.append(-76.0)
        self.assertEqual(result.energies, [-76.0])
        self.assertEqual(optimize.OptimizationResult().energies, [])


class TestResultOfUma(unittest.TestCase):
    def test_it_extends_the_common_result_with_the_uma_items(self):
        result = uma_optimize.OptimizationResult()
        self.assertIsInstance(result, optimization.OptimizationResult)
        for name in COMMON_ITEMS:
            self.assertTrue(hasattr(result, name), name)
        self.assertEqual(result.energies_ev, [])
        self.assertEqual(result.fmax_history, [])
        self.assertIsNone(result.fmax_target)
        self.assertEqual(result.optimizer_name, "")
        self.assertEqual(result.max_steps, 0)

    def test_final_fmax_is_the_last_value_of_the_history(self):
        result = uma_optimize.OptimizationResult()
        self.assertIsNone(result.final_fmax)
        result.fmax_history = [0.9, 0.2, 0.008]
        self.assertEqual(result.final_fmax, 0.008)

    def test_the_two_engines_do_not_share_their_own_items(self):
        self.assertFalse(hasattr(optimize.OptimizationResult(), "fmax_history"))
        self.assertFalse(hasattr(uma_optimize.OptimizationResult(), "mol_final"))


class TestEitherEngineResultIsAccepted(unittest.TestCase):
    """共通の出力関数は、どちらのエンジンの結果も、同じように受け取れる(エンジンを区別しない)。"""

    def _fill(self, result):
        result.symbols = ["O", "H", "H"]
        result.coords_history = [COORDS, COORDS]
        result.energies = [-76.0, -76.1]
        return result

    def test_the_same_trajectory_is_written_for_both_engines(self):
        texts = []
        for result in (self._fill(optimize.OptimizationResult()), self._fill(uma_optimize.OptimizationResult())):
            with tempfile.TemporaryDirectory() as out_dir:
                _, traj_path = writer_xyz.write_optimization_outputs(out_dir, result.symbols, COORDS, "c", result)
                with open(traj_path, encoding="utf-8") as f:
                    texts.append(f.read())
        self.assertEqual(texts[0], texts[1])


if __name__ == "__main__":
    unittest.main()
