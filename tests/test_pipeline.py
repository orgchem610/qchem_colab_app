"""
tests/test_pipeline.py
----------------------
qcapp.pipeline(PySCF版の計算の流れ)の単体テスト。
PySCFは使わず、engine・optimize・freq・writer_molden を代用の関数に差し替えて、
各段階の呼び出しの順序・受け渡し・ログの内容・出力ファイルを確認する。
PySCFによる実際の計算は、Colab上での実機確認が必要。
"""

import contextlib
import io
import os
import shutil
import sys
import unittest
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from common import io_reader  # noqa: E402
from qcapp import __version__, pipeline  # noqa: E402

DEFAULTS = {"frequency": {"warn_natoms": 40}}


class FakeMol:
    def __init__(self, symbols=("O", "H", "H")):
        self.symbols = list(symbols)
        self.natm = len(self.symbols)
        self.cart = False

    def atom_symbol(self, i):
        return self.symbols[i]

    def atom_coords(self, unit="Angstrom"):
        return [[0.0, 0.0, 0.1 * i] for i in range(self.natm)]


def _structure(symbols=("O", "H", "H")):
    return SimpleNamespace(symbols=list(symbols), coords=[[0.0, 0.0, 0.0]] * len(symbols))


class _Base(unittest.TestCase):
    """engine・optimize・freq・writer_molden を代用の関数に差し替えて、呼び出しを記録する。"""

    n_atoms = 3
    energies = [-76.0, -76.1, -76.2]
    freq_warning = ""

    def setUp(self):
        self.calls = []
        self.logs = []
        self.mol = FakeMol()
        self.final_mol = FakeMol(("O",) + ("H",) * (self.n_atoms - 1))
        self.opt_result = SimpleNamespace(
            mol_final=self.final_mol, symbols=list(self.final_mol.symbols),
            coords_history=[[[0.0, 0.0, 0.0]] * self.n_atoms] * 3, energies=list(self.energies),
            gpu_message="CPU (通常のPySCF) で計算します。", elapsed_seconds=1.5, dm0_guess="dm0")
        self.mf = SimpleNamespace(name="mf_cpu")
        self.mf_final = SimpleNamespace(name="mf_final")
        self.freq_result = SimpleNamespace(elapsed_seconds=0.5, warning_message=self.freq_warning)
        self.gpu_detected = False

        def build_mole(structure, charge, multiplicity, basis_key):
            self.calls.append(("build_mole", charge, multiplicity, basis_key))
            return self.mol

        def run_geometry_optimization(mol, functional_key, defaults, try_gpu):
            self.calls.append(("optimize", mol is self.mol, functional_key, try_gpu))
            return self.opt_result

        def build_scf(mol, functional_key, try_gpu):
            self.calls.append(("build_scf", mol is self.final_mol, functional_key, try_gpu))
            return self.mf, False, ""

        def run_scf(mf, defaults, dm0=None):
            self.calls.append(("run_scf", mf is self.mf, dm0))
            return self.mf_final

        def run_frequency_analysis(mf, defaults):
            self.calls.append(("frequency", mf is self.mf_final))
            return self.freq_result

        def write_molden(mf, path):
            self.calls.append(("molden", mf is self.mf_final))
            with open(path, "w", encoding="utf-8") as f:
                f.write("[Molden Format]\n")

        patches = [
            mock.patch.object(pipeline.engine, "build_mole", build_mole),
            mock.patch.object(pipeline.engine, "build_scf", build_scf),
            mock.patch.object(pipeline.engine, "run_scf", run_scf),
            mock.patch.object(pipeline.engine, "gpu_runtime_detected", lambda: self.gpu_detected),
            mock.patch.object(pipeline.optimize, "run_geometry_optimization", run_geometry_optimization),
            mock.patch.object(pipeline.freq_module, "run_frequency_analysis", run_frequency_analysis),
            mock.patch.object(pipeline.writer_molden, "write_molden", write_molden),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def run_pipeline(self, structure=None, defaults=None, **settings):
        values = dict(charge=1, multiplicity=2, functional_key="b3lyp", basis_key="6-31g*",
                      do_frequency=True)
        values.update(settings)
        result = pipeline.run_calculation(
            structure or _structure(), pipeline.CalculationSettings(**values),
            defaults or DEFAULTS, log=self.logs.append)
        self.addCleanup(shutil.rmtree, result.out_dir, True)
        return result

    @property
    def log_text(self):
        return "\n".join(self.logs)

    def names(self):
        return [c[0] for c in self.calls]


class TestOrderAndHandOver(_Base):
    def test_stages_run_in_order_with_the_expected_arguments(self):
        self.run_pipeline()
        self.assertEqual(self.names(),
                         ["build_mole", "optimize", "build_scf", "run_scf", "frequency", "molden"])
        self.assertEqual(self.calls[0], ("build_mole", 1, 2, "6-31g*"))
        self.assertEqual(self.calls[1], ("optimize", True, "b3lyp", False))
        self.assertEqual(self.calls[2], ("build_scf", True, "b3lyp", False))   # 再計算は、常にCPU

    def test_density_matrix_of_the_optimization_is_the_initial_guess_of_the_cpu_scf(self):
        self.run_pipeline()
        self.assertIn(("run_scf", True, "dm0"), self.calls)

    def test_frequency_analysis_uses_the_cpu_scf_result(self):
        self.run_pipeline()
        self.assertIn(("frequency", True), self.calls)
        self.assertIn(("molden", True), self.calls)

    def test_cartesian_functions_are_set_explicitly_on_the_final_molecule(self):
        self.run_pipeline()
        self.assertTrue(self.final_mol.cart)

    def test_without_frequency_the_analysis_is_skipped(self):
        result = self.run_pipeline(do_frequency=False)
        self.assertNotIn("frequency", self.names())
        self.assertIsNone(result.freq_result)
        self.assertIn("構造最適化のみ", self.log_text)
        self.assertNotIn("振動数計算を開始します", self.log_text)

    def test_with_frequency_the_total_time_line_names_both_steps(self):
        self.run_pipeline()
        self.assertIn("構造最適化 + 振動数計算", self.log_text)
        self.assertIn("振動数計算を開始します", self.log_text)


class TestResult(_Base):
    def test_result_holds_everything_the_gui_needs(self):
        result = self.run_pipeline()
        self.assertIs(result.opt_result, self.opt_result)
        self.assertIs(result.final_mol, self.final_mol)
        self.assertIs(result.mf_final, self.mf_final)
        self.assertIs(result.freq_result, self.freq_result)
        self.assertEqual(result.final_symbols, ["O", "H", "H"])
        self.assertEqual(result.final_coords[1], [0.0, 0.0, 0.1])
        self.assertGreaterEqual(result.total_seconds, 0.0)

    def test_output_files_are_written_with_the_standard_names(self):
        result = self.run_pipeline()
        self.assertEqual(os.path.basename(result.final_xyz_path), "final_structure_for_ColabReaction.xyz")
        self.assertEqual(os.path.basename(result.traj_xyz_path), "optimization_trajectory.xyz")
        self.assertEqual(os.path.basename(result.molden_path), "final_structure.molden")
        for path in (result.final_xyz_path, result.traj_xyz_path, result.molden_path):
            self.assertTrue(os.path.exists(path), path)
            self.assertEqual(os.path.dirname(path), result.out_dir)
        self.assertTrue(os.path.basename(result.out_dir).startswith("qchem_output_"))

    def test_final_structure_comment_names_the_version_and_the_method(self):
        result = self.run_pipeline()
        with open(result.final_xyz_path, encoding="utf-8") as f:
            comment = f.read().splitlines()[1]
        self.assertEqual(comment, f"Optimized by qchem_colab_app (v{__version__}, b3lyp/6-31g*)")

    def test_trajectory_has_one_frame_per_recorded_step(self):
        result = self.run_pipeline()
        with open(result.traj_xyz_path, encoding="utf-8") as f:
            self.assertEqual(len(f.read().splitlines()), 3 * (2 + 3))


class TestGpuSetting(_Base):
    def test_gpu_is_detected_automatically_when_not_specified(self):
        self.gpu_detected = True
        self.run_pipeline()
        self.assertEqual(self.calls[1], ("optimize", True, "b3lyp", True))
        self.assertIn("検出されました", self.log_text)

    def test_cpu_message_is_logged_when_no_gpu_runtime_is_detected(self):
        self.gpu_detected = False
        self.run_pipeline()
        self.assertEqual(self.calls[1], ("optimize", True, "b3lyp", False))
        self.assertIn("検出されませんでした", self.log_text)

    def test_explicit_setting_overrides_the_detection(self):
        self.gpu_detected = True
        self.run_pipeline(try_gpu=False)
        self.assertEqual(self.calls[1], ("optimize", True, "b3lyp", False))


class TestLogNotes(_Base):
    def test_optimization_summary_is_logged(self):
        self.run_pipeline()
        self.assertIn("CPU (通常のPySCF) で計算します。", self.log_text)
        self.assertIn("記録されたエネルギー点数: 3", self.log_text)
        self.assertNotIn("エネルギー収束グラフが単調にならない", self.log_text)

    def test_few_recorded_energies_are_noted(self):
        self.opt_result.energies = [-76.0]
        self.run_pipeline()
        self.assertIn("エネルギー収束グラフが単調にならない", self.log_text)

    def test_frequency_warning_is_logged(self):
        self.freq_result.warning_message = "虚振動が1個検出されました。"
        self.run_pipeline()
        self.assertIn("[注意] 虚振動が1個検出されました。", self.log_text)

    def test_default_log_function_is_print(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            result = pipeline.run_calculation(
                _structure(), pipeline.CalculationSettings(0, 1, "hf", "3-21g", do_frequency=False),
                DEFAULTS)
        self.addCleanup(shutil.rmtree, result.out_dir, True)
        self.assertIn("構造最適化を開始します", buffer.getvalue())


class TestManyAtoms(_Base):
    n_atoms = 40

    def test_long_calculation_notice_appears_from_the_configured_threshold(self):
        self.run_pipeline()
        self.assertIn("原子数が40と多いため", self.log_text)

    def test_threshold_is_read_from_the_defaults(self):
        self.run_pipeline(defaults={"frequency": {"warn_natoms": 41}})
        self.assertNotIn("原子数が40と多いため", self.log_text)

    def test_notice_is_not_shown_without_frequency_analysis(self):
        self.run_pipeline(do_frequency=False)
        self.assertNotIn("原子数が40と多いため", self.log_text)


class TestErrors(_Base):
    def test_transition_metal_is_rejected_before_any_calculation(self):
        with self.assertRaises(io_reader.StructureError) as ctx:
            self.run_pipeline(structure=_structure(("Fe", "C", "O")))
        self.assertIn("遷移金属", str(ctx.exception))
        self.assertEqual(self.calls, [])

    def test_errors_of_the_stages_are_passed_on_unchanged(self):
        class Boom(RuntimeError):
            pass

        with mock.patch.object(pipeline.engine, "run_scf", side_effect=Boom("収束しません")):
            with self.assertRaises(Boom):
                self.run_pipeline()
        self.assertNotIn("frequency", self.names())

    def test_progress_logged_before_the_error_is_kept(self):
        with mock.patch.object(pipeline.engine, "run_scf", side_effect=RuntimeError("x")):
            with self.assertRaises(RuntimeError):
                self.run_pipeline()
        self.assertIn("構造最適化を開始します", self.log_text)


if __name__ == "__main__":
    unittest.main()
