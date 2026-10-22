"""
tests/test_pipeline.py
----------------------
pyscf_backend.pipeline(PySCF版の計算の流れ)の単体テスト。
次の2通りで確認する。
    1. 各段階の呼び出しの順序・受け渡し・ログの内容・出力ファイル(_Base を継承した各クラス):
       engine・optimize・freq・writer_molden・runtime(GPUの判定)の関数だけを差し替える。分子は実物の
       pyscf.gto.Mole、SCFオブジェクトは計算していない実物のRHF、構造・最適化結果・振動数結果は実物のクラスを使う。
    2. 実際の計算(TestRealCalculation): 水(HF/3-21G)の構造最適化・振動数計算・出力を、PySCFとgeomeTRICで
       実際に走らせる(約3秒)。GPU(GPU4PySCF)を使う計算だけは、Colab上での実機確認が必要。
PySCF・geomeTRICが入っていない環境では、それを使うテストだけをスキップする。
"""

import contextlib
import io
import os
import shutil
import sys
import unittest
from unittest import mock

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import real_molecules as rm  # noqa: E402
from qchem_colab_app.common_backend import config_loader, io_reader, version  # noqa: E402
from qchem_colab_app.pyscf_backend import freq, optimize, pipeline  # noqa: E402

DEFAULTS = {"frequency": {"warn_natoms": 40}}
SKIP_NO_PYSCF = "PySCFがインストールされていないためスキップ"
SKIP_NO_GEOMETRIC = "PySCFまたはgeomeTRICがインストールされていないためスキップ"
WATER_COORDS = [[0.0, 0.0, 0.1173], [0.0, 0.7572, -0.4692], [0.0, -0.7572, -0.4692]]


def _mole(n_atoms):
    """実物の pyscf.gto.Mole。1番目がO、残りがH。最初の3原子は水の構造で、残りは3 Åずつ離して置く。
    電子の数が奇数になるときは、陽イオンにする(閉殻のまま、RHFオブジェクトを作れるように)。"""
    coords = WATER_COORDS + [[3.0 * k, 0.0, 0.0] for k in range(1, n_atoms - 2)]
    atoms = [(symbol, tuple(xyz)) for symbol, xyz in zip(["O"] + ["H"] * (n_atoms - 1), coords)]
    return rm.build_mole(atoms, basis="sto-3g", charge=(8 + n_atoms - 1) % 2)


def _structure(symbols=("O", "H", "H")):
    return io_reader.Structure(symbols=list(symbols), coords=[[0.0, 0.0, 0.0]] * len(symbols))


def _optimization_result(final_mol, n_atoms, energies):
    result = optimize.OptimizationResult()
    result.mol_final = final_mol
    result.symbols = [final_mol.atom_symbol(i) for i in range(final_mol.natm)]
    result.coords_history = [[[0.0, 0.0, 0.0]] * n_atoms] * 3
    result.energies = list(energies)
    result.gpu_message = "CPU (通常のPySCF) で計算します。"
    result.elapsed_seconds = 1.5
    result.dm0_guess = "dm0"
    return result


def _frequency_result(warning_message):
    result = freq.FrequencyResult()
    result.elapsed_seconds = 0.5
    result.warning_message = warning_message
    return result


@unittest.skipUnless(rm.HAS_PYSCF, SKIP_NO_PYSCF)
class _Base(unittest.TestCase):
    """engine・optimize・freq・writer_molden の関数だけを差し替えて、呼び出しを記録する。"""

    n_atoms = 3
    energies = [-76.0, -76.1, -76.2]
    freq_warning = ""

    def setUp(self):
        self.calls = []
        self.logs = []
        from pyscf import scf
        self.mol = _mole(3)
        self.final_mol = _mole(self.n_atoms)
        self.opt_result = _optimization_result(self.final_mol, self.n_atoms, self.energies)
        self.mf = scf.RHF(self.final_mol)              # 計算していない実物のSCFオブジェクト(各段階の受け渡しを見分けるため、2つ作る)
        self.mf_final = scf.RHF(self.final_mol)
        self.freq_result = _frequency_result(self.freq_warning)
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
            mock.patch.object(pipeline.runtime, "nvidia_gpu_detected", lambda: self.gpu_detected),
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
        self.assertTrue(np.allclose(result.final_coords[1], WATER_COORDS[1]))        # Å
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
        self.assertEqual(comment, f"Optimized by qchem_colab_app (v{version.__version__}, b3lyp/6-31g*)")

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


@unittest.skipUnless(rm.HAS_PYSCF and rm.HAS_GEOMETRIC, SKIP_NO_GEOMETRIC)
class TestRealCalculation(unittest.TestCase):
    """水(HF/3-21G)の構造最適化・振動数計算・出力を、PySCFとgeomeTRICで実際に走らせる(約3秒)。

    engine・optimize・freq・writer_molden・設定ファイル(config/*.yaml)を、差し替えずに、実物のまま通す。
    入力は、少し歪めた水。収束した構造は、HF/3-21Gの水の平衡構造(O-H 約0.967 Å、H-O-H 約108°)になる。
    """

    @classmethod
    def setUpClass(cls):
        defaults = config_loader.load_yaml("defaults.yaml")
        structure = io_reader.Structure(
            symbols=["O", "H", "H"], coords=[[0.0, 0.0, 0.12], [0.0, 0.80, -0.47], [0.0, -0.80, -0.47]],
            comment="distorted water")
        settings = pipeline.CalculationSettings(
            charge=0, multiplicity=1, functional_key="hf", basis_key="3-21g", do_frequency=True, try_gpu=False)
        cls.logs = []
        cls.result = pipeline.run_calculation(structure, settings, defaults, log=cls.logs.append)
        cls.addClassCleanup(shutil.rmtree, cls.result.out_dir, True)

    def test_the_optimization_converges_to_the_equilibrium_structure_of_water(self):
        result = self.result
        self.assertTrue(result.opt_result.converged)
        self.assertLess(result.opt_result.energies[-1], result.opt_result.energies[0])      # エネルギーが下がった
        coords = np.array(result.final_coords)
        v1, v2 = coords[1] - coords[0], coords[2] - coords[0]
        for bond in (v1, v2):
            self.assertAlmostEqual(np.linalg.norm(bond), 0.967, delta=0.01)                # O-H [Å]
        angle = np.degrees(np.arccos(v1 @ v2 / (np.linalg.norm(v1) * np.linalg.norm(v2))))
        self.assertAlmostEqual(angle, 107.7, delta=1.5)                                     # H-O-H [度]

    def test_the_final_scf_is_converged_at_the_optimized_structure(self):
        result = self.result
        self.assertTrue(result.mf_final.converged)
        self.assertAlmostEqual(result.mf_final.e_tot, result.opt_result.energies[-1], places=4)
        self.assertEqual(result.final_symbols, ["O", "H", "H"])

    def test_the_frequencies_are_those_of_a_minimum(self):
        freq_result = self.result.freq_result
        self.assertEqual(len(freq_result.frequencies_cm1), 3)
        self.assertEqual(freq_result.n_imaginary, 0)
        self.assertEqual(freq_result.warning_message, "")
        self.assertTrue(all(1500.0 < f < 4500.0 for f in freq_result.frequencies_cm1), freq_result.frequencies_cm1)
        self.assertTrue(0.015 < freq_result.zpe_hartree < 0.03, freq_result.zpe_hartree)

    def test_output_files_are_written_and_have_the_expected_contents(self):
        result = self.result
        with open(result.final_xyz_path, encoding="utf-8") as f:
            lines = f.read().splitlines()
        self.assertEqual(lines[0], "3")
        self.assertEqual(lines[1], f"Optimized by qchem_colab_app (v{version.__version__}, hf/3-21g)")
        with open(result.traj_xyz_path, encoding="utf-8") as f:
            self.assertEqual(len(f.read().splitlines()), len(result.opt_result.coords_history) * 5)
        with open(result.molden_path, encoding="utf-8") as f:
            self.assertTrue(f.readline().startswith("[Molden Format]"))
        self.assertGreater(os.path.getsize(result.molden_path), 1000)                       # 軌道の係数まで書かれている

    def test_the_log_reports_each_stage(self):
        text = "\n".join(self.logs)
        for expected in ("構造最適化を開始します", "最終構造でCPU上のSCFを再計算", "振動数計算を開始します",
                         "構造最適化 + 振動数計算"):
            self.assertIn(expected, text)


if __name__ == "__main__":
    unittest.main()
