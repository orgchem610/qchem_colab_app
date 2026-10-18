"""
tests/test_uma_optimize.py
--------------------------
uma_backend.uma_optimize の単体テスト。

UMAそのものは使わず、ASE付属の簡易ポテンシャル(EMT)で「履歴の記録・単位換算・
収束判定・入力チェック」のロジックだけを確認する。ASEが入っていない環境では、
ASEを必要とするテストは自動的にスキップされる。
UMAを使った実際の最適化は、Colab上での実機確認が必要。
"""

import importlib.util
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from uma_backend import uma_optimize  # noqa: E402

HAS_ASE = importlib.util.find_spec("ase") is not None


class TestInputCheck(unittest.TestCase):
    def test_unsupported_optimizer_name_is_rejected_before_anything_runs(self):
        with self.assertRaises(ValueError) as ctx:
            uma_optimize.run_geometry_optimization(
                None, None, {"optimizer": "MDMin", "fmax_ev_per_angstrom": 0.05, "max_steps": 10})
        self.assertIn("未対応の最適化アルゴリズム", str(ctx.exception))


class TestConstants(unittest.TestCase):
    def test_hartree_per_ev(self):
        self.assertAlmostEqual(1.0 / uma_optimize.HARTREE_PER_EV, 27.211386245988, places=9)


@unittest.skipUnless(HAS_ASE, "ASEがインストールされていないためスキップ")
class TestWithEMT(unittest.TestCase):
    CFG = {"optimizer": "LBFGS", "fmax_ev_per_angstrom": 0.05, "max_steps": 300}

    @staticmethod
    def _cluster():
        from ase import Atoms
        # 少しゆがんだCu3の三角形(EMTがつり合いの構造へ緩和する)
        atoms = Atoms("Cu3", positions=[[0.0, 0.0, 0.0], [2.9, 0.0, 0.0], [1.3, 2.0, 0.1]])
        atoms.info["charge"] = 0
        atoms.info["spin"] = 1
        return atoms

    def _run(self, cfg=None, progress=None):
        from ase.calculators.emt import EMT
        atoms = self._cluster()
        before = atoms.get_positions().copy()
        result = uma_optimize.run_geometry_optimization(
            atoms, EMT(), cfg or self.CFG, progress=progress)
        return atoms, before, result

    def test_energy_decreases_and_run_converges(self):
        _, _, result = self._run()
        self.assertTrue(result.converged)
        self.assertGreaterEqual(len(result.energies), 2)
        self.assertLess(result.energies[-1], result.energies[0])
        self.assertLessEqual(result.final_fmax, self.CFG["fmax_ev_per_angstrom"])

    def test_histories_have_the_same_length_and_no_duplicate_frames(self):
        _, _, result = self._run()
        n = len(result.energies)
        self.assertEqual(len(result.coords_history), n)
        self.assertEqual(len(result.fmax_history), n)
        self.assertEqual(len(result.energies_ev), n)
        for a, b in zip(result.coords_history[:-1], result.coords_history[1:]):
            self.assertNotEqual(a, b)

    def test_hartree_energies_are_converted_from_ev(self):
        _, _, result = self._run()
        for e_ev, e_ha in zip(result.energies_ev, result.energies):
            self.assertAlmostEqual(e_ha, e_ev * uma_optimize.HARTREE_PER_EV, places=12)

    def test_input_atoms_are_not_modified(self):
        atoms, before, _ = self._run()
        self.assertEqual(atoms.get_positions().tolist(), before.tolist())

    def test_symbols_and_metadata_are_recorded(self):
        _, _, result = self._run()
        self.assertEqual(result.symbols, ["Cu", "Cu", "Cu"])
        self.assertEqual(result.optimizer_name, "LBFGS")
        self.assertEqual(result.max_steps, 300)
        self.assertEqual(result.fmax_target, 0.05)

    def test_not_converged_when_steps_run_out(self):
        cfg = {"optimizer": "LBFGS", "fmax_ev_per_angstrom": 1e-9, "max_steps": 2}
        _, _, result = self._run(cfg)
        self.assertFalse(result.converged)
        self.assertGreaterEqual(len(result.energies), 2)   # 途中経過は記録されている

    def test_progress_callback_is_called_for_every_recorded_point(self):
        calls = []
        _, _, result = self._run(progress=lambda step, e, f: calls.append((step, e, f)))
        self.assertEqual([c[0] for c in calls], list(range(len(result.energies))))


if __name__ == "__main__":
    unittest.main()
