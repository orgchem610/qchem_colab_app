"""
tests/test_uma_pipeline.py
--------------------------
uma_backend.uma_pipeline(UMA版の計算の流れ)の単体テスト。
UMA・fairchem・ASE・ネットワークは使わず、uma_hf・uma_engine・uma_optimize・uma_freq を
代用の関数に差し替えて、各段階の呼び出しの順序・受け渡し・ログの内容・出力ファイルを確認する。
UMAによる実際の計算は、Colab上での実機確認が必要。
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

from uma_backend import __version__, uma_hf, uma_pipeline  # noqa: E402


def _defaults(warn_natoms=60):
    return {
        "uma": {"task_name": "omol"},
        "geometry_optimization": {"optimizer": "LBFGS", "fmax_ev_per_angstrom": 0.01, "max_steps": 500},
        "frequency": {"displacement_angstrom": 0.01, "warn_natoms": warn_natoms,
                      "small_imaginary_cm1": 50},
    }


class FakeAtoms:
    def __init__(self):
        self.positions = None

    def copy(self):
        copied = FakeAtoms()
        copied.is_copy = True
        return copied

    def set_positions(self, positions):
        self.positions = positions


def _structure(n=3):
    return SimpleNamespace(symbols=["O"] + ["H"] * (n - 1), coords=[[0.0, 0.0, 0.0]] * n)


class _Base(unittest.TestCase):
    n_atoms = 3
    device = "cuda"
    converged = True

    def setUp(self):
        self.calls = []
        self.logs = []
        self.atoms = FakeAtoms()
        self.predictor = object()
        self.calculator = object()
        n = self.n_atoms
        self.opt_result = SimpleNamespace(
            symbols=["O"] + ["H"] * (n - 1),
            coords_history=[[[0.0, 0.0, 0.0]] * n, [[0.0, 0.0, 0.1]] * n],
            energies=[-76.0, -76.1], energies_ev=[-2068.0, -2070.0], fmax_history=[0.5, 0.005],
            converged=self.converged, elapsed_seconds=2.0, max_steps=500, final_fmax=0.005 if self.converged else 0.2,
            optimizer_name="LBFGS", fmax_target=0.01)
        self.freq_result = SimpleNamespace(
            elapsed_seconds=1.0, n_imaginary=0, warning_message="", frequencies_cm1=[1600.0],
            thermo_summary={})

        def check_model_access():
            self.calls.append(("check_model_access",))

        def get_device():
            self.calls.append(("get_device",))
            return self.device

        def describe_device(device):
            return "GPU(Test)" if device == "cuda" else "CPU(テスト)"

        def load_predictor(model_key, device):
            self.calls.append(("load_predictor", model_key, device))
            return self.predictor

        def make_calculator(predictor, task_name):
            self.calls.append(("make_calculator", predictor is self.predictor, task_name))
            return self.calculator

        def build_atoms(structure, charge, multiplicity):
            self.calls.append(("build_atoms", charge, multiplicity))
            return self.atoms

        def run_geometry_optimization(atoms, calculator, opt_cfg, progress=None):
            self.calls.append(("optimize", atoms is self.atoms, calculator is self.calculator,
                               opt_cfg["optimizer"]))
            if progress:
                progress(0, -76.0, 0.5)
                progress(1, -76.1, 0.005)
            return self.opt_result

        def run_frequency_analysis(atoms, calculator, freq_cfg, progress=None):
            self.calls.append(("frequency", getattr(atoms, "is_copy", False), calculator is self.calculator))
            self.freq_atoms = atoms
            if progress:
                for done in range(1, self.n_atoms + 1):
                    progress(done, self.n_atoms)
            return self.freq_result

        patches = [
            mock.patch.object(uma_pipeline.uma_hf, "check_model_access", check_model_access),
            mock.patch.object(uma_pipeline.uma_engine, "get_device", get_device),
            mock.patch.object(uma_pipeline.uma_engine, "describe_device", describe_device),
            mock.patch.object(uma_pipeline.uma_engine, "load_predictor", load_predictor),
            mock.patch.object(uma_pipeline.uma_engine, "make_calculator", make_calculator),
            mock.patch.object(uma_pipeline.uma_engine, "build_atoms", build_atoms),
            mock.patch.object(uma_pipeline.uma_optimize, "run_geometry_optimization", run_geometry_optimization),
            mock.patch.object(uma_pipeline.uma_freq, "run_frequency_analysis", run_frequency_analysis),
            # ログの本文の組み立ては、呼び出しの引数だけを記録する(本文そのものは別のテストで確認)
            mock.patch.object(uma_pipeline.uma_report, "build_log_text", self._build_log_text),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def _build_log_text(self, **kwargs):
        self.report_kwargs = kwargs
        return "REPORT\n"

    def run_pipeline(self, defaults=None, **settings):
        values = dict(charge=1, multiplicity=2, model_key="uma-s-1p2p1", do_frequency=True,
                      input_filename="ethanol.xyz")
        values.update(settings)
        result = uma_pipeline.run_calculation(
            _structure(self.n_atoms), uma_pipeline.CalculationSettings(**values),
            defaults or _defaults(), log=self.logs.append)
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
        self.assertEqual(self.names(), ["check_model_access", "get_device", "load_predictor",
                                        "make_calculator", "build_atoms", "optimize", "frequency"])
        self.assertIn(("load_predictor", "uma-s-1p2p1", "cuda"), self.calls)
        self.assertIn(("make_calculator", True, "omol"), self.calls)      # タスク名は設定ファイルから
        self.assertIn(("build_atoms", 1, 2), self.calls)
        self.assertIn(("optimize", True, True, "LBFGS"), self.calls)

    def test_frequency_analysis_runs_on_a_copy_placed_at_the_final_structure(self):
        self.run_pipeline()
        self.assertIn(("frequency", True, True), self.calls)
        self.assertEqual(self.freq_atoms.positions, [[0.0, 0.0, 0.1]] * 3)

    def test_without_frequency_the_analysis_is_skipped(self):
        result = self.run_pipeline(do_frequency=False)
        self.assertNotIn("frequency", self.names())
        self.assertIsNone(result.freq_result)
        self.assertIn("構造最適化のみ", self.log_text)
        self.assertNotIn("振動数計算を開始します", self.log_text)

    def test_with_frequency_the_total_time_line_names_both_steps(self):
        self.run_pipeline()
        self.assertIn("構造最適化 + 振動数計算", self.log_text)


class TestResult(_Base):
    def test_result_holds_everything_the_gui_needs(self):
        result = self.run_pipeline()
        self.assertIs(result.opt_result, self.opt_result)
        self.assertIs(result.freq_result, self.freq_result)
        self.assertEqual(result.final_symbols, ["O", "H", "H"])
        self.assertEqual(result.final_coords, [[0.0, 0.0, 0.1]] * 3)
        self.assertEqual(result.device_label, "GPU(Test)")
        self.assertGreaterEqual(result.total_seconds, 0.0)

    def test_output_files_are_written_with_the_standard_names(self):
        result = self.run_pipeline()
        self.assertEqual(os.path.basename(result.final_xyz_path), "final_structure_for_ColabReaction.xyz")
        self.assertEqual(os.path.basename(result.traj_xyz_path), "optimization_trajectory.xyz")
        self.assertEqual(os.path.basename(result.log_path), "calculation_log.txt")
        for path in (result.final_xyz_path, result.traj_xyz_path, result.log_path):
            self.assertTrue(os.path.exists(path), path)
            self.assertEqual(os.path.dirname(path), result.out_dir)
        self.assertTrue(os.path.basename(result.out_dir).startswith("qchem_uma_output_"))

    def test_final_structure_comment_names_the_version_the_model_and_the_task(self):
        result = self.run_pipeline()
        with open(result.final_xyz_path, encoding="utf-8") as f:
            comment = f.read().splitlines()[1]
        self.assertEqual(comment, f"Optimized by qchem_colab_app UMA (v{__version__}, uma-s-1p2p1, omol)")

    def test_trajectory_has_one_frame_per_recorded_step(self):
        result = self.run_pipeline()
        with open(result.traj_xyz_path, encoding="utf-8") as f:
            self.assertEqual(len(f.read().splitlines()), 2 * (2 + 3))

    def test_report_is_built_from_the_conditions_and_results(self):
        result = self.run_pipeline()
        kwargs = self.report_kwargs
        self.assertEqual(kwargs["version"], __version__)
        self.assertEqual((kwargs["model_key"], kwargs["task_name"]), ("uma-s-1p2p1", "omol"))
        self.assertEqual(kwargs["device_label"], "GPU(Test)")
        self.assertEqual(kwargs["input_filename"], "ethanol.xyz")
        self.assertEqual((kwargs["charge"], kwargs["multiplicity"]), (1, 2))
        self.assertIs(kwargs["opt_result"], self.opt_result)
        self.assertIs(kwargs["freq_result"], self.freq_result)
        self.assertEqual(kwargs["total_seconds"], result.total_seconds)
        with open(result.log_path, encoding="utf-8") as f:
            self.assertEqual(f.read(), "REPORT\n")

    def test_report_gets_no_frequency_result_when_it_was_not_calculated(self):
        self.run_pipeline(do_frequency=False)
        self.assertIsNone(self.report_kwargs["freq_result"])


class TestLog(_Base):
    def test_access_model_and_optimization_steps_are_logged(self):
        self.run_pipeline()
        text = self.log_text
        self.assertIn("Hugging Faceのアクセス権を確認しています", text)
        self.assertIn("UMAへのアクセスを確認しました。", text)
        self.assertIn("UMAモデル uma-s-1p2p1 を読み込みます(デバイス: GPU(Test))", text)
        self.assertIn("(LBFGS, 収束条件 fmax <= 0.01 eV/Å, 最大 500 ステップ)", text)

    def test_optimization_progress_is_logged_per_step(self):
        self.run_pipeline()
        self.assertIn("  step   0  E = -76.000000 Ha  fmax = 0.5000 eV/Å", self.logs)
        self.assertIn("  step   1  E = -76.100000 Ha  fmax = 0.0050 eV/Å", self.logs)

    def test_converged_summary_is_logged(self):
        self.run_pipeline()
        self.assertIn("収束しました。構造最適化 所要時間: 2.0 秒  (記録された点数: 2)", self.log_text)

    def test_frequency_summary_and_warning_are_logged(self):
        self.freq_result.n_imaginary = 1
        self.freq_result.warning_message = "虚振動が1個検出されました。"
        self.run_pipeline()
        self.assertIn("振動数計算 所要時間: 1.0 秒  (虚振動: 1個)", self.log_text)
        self.assertIn("[注意] 虚振動が1個検出されました。", self.log_text)

    def test_default_log_function_is_print(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            result = uma_pipeline.run_calculation(
                _structure(), uma_pipeline.CalculationSettings(0, 1, "uma-s-1p2p1", do_frequency=False),
                _defaults())
        self.addCleanup(shutil.rmtree, result.out_dir, True)
        self.assertIn("構造最適化を開始します", buffer.getvalue())


class TestCpuDevice(_Base):
    device = "cpu"

    def test_slowness_notice_appears_on_cpu(self):
        self.run_pipeline()
        self.assertIn("GPUが使えないため、計算に非常に時間がかかります", self.log_text)
        self.assertIn("CPU(テスト)", self.log_text)


class TestGpuDevice(_Base):
    def test_no_slowness_notice_on_gpu(self):
        self.run_pipeline()
        self.assertNotIn("GPUが使えないため", self.log_text)


class TestNotConverged(_Base):
    converged = False

    def test_note_for_the_unconverged_optimization_is_logged(self):
        self.run_pipeline()
        self.assertIn("[注意] 500ステップ以内に収束しませんでした(最終 fmax = 0.2000 eV/Å)", self.log_text)
        self.assertNotIn("収束しました。", self.log_text)

    def test_calculation_continues_to_the_outputs(self):
        result = self.run_pipeline()
        self.assertTrue(os.path.exists(result.final_xyz_path))


class TestManyAtoms(_Base):
    n_atoms = 20

    def test_notice_appears_from_the_configured_threshold(self):
        self.run_pipeline(defaults=_defaults(warn_natoms=20))
        self.assertIn("原子数が20と多いため", self.log_text)

    def test_notice_is_not_shown_below_the_threshold(self):
        self.run_pipeline(defaults=_defaults(warn_natoms=21))
        self.assertNotIn("原子数が20と多いため", self.log_text)

    def test_hessian_progress_is_reported_every_tenth_of_the_atoms(self):
        self.run_pipeline()
        lines = [s for s in self.logs if s.startswith("  Hessian計算:")]
        self.assertEqual(lines, [f"  Hessian計算: {i}/20 原子" for i in range(2, 21, 2)])


class TestSmallMolecule(_Base):
    def test_hessian_progress_is_reported_for_every_atom_of_a_small_molecule(self):
        self.run_pipeline()
        lines = [s for s in self.logs if s.startswith("  Hessian計算:")]
        self.assertEqual(lines, ["  Hessian計算: 1/3 原子", "  Hessian計算: 2/3 原子", "  Hessian計算: 3/3 原子"])


class TestErrors(_Base):
    def test_access_error_is_raised_before_anything_else(self):
        with mock.patch.object(uma_pipeline.uma_hf, "check_model_access",
                               side_effect=uma_hf.UmaSetupError("アクセスできません")):
            with self.assertRaises(uma_hf.UmaSetupError):
                self.run_pipeline()
        self.assertEqual(self.calls, [])

    def test_errors_of_the_stages_are_passed_on_unchanged(self):
        with mock.patch.object(uma_pipeline.uma_engine, "load_predictor", side_effect=ImportError("fairchem")):
            with self.assertRaises(ImportError):
                self.run_pipeline()
        self.assertNotIn("optimize", self.names())

    def test_value_error_of_the_configuration_is_passed_on(self):
        with mock.patch.object(uma_pipeline.uma_optimize, "run_geometry_optimization",
                               side_effect=ValueError("未対応の最適化アルゴリズム")):
            with self.assertRaises(ValueError):
                self.run_pipeline()

    def test_progress_logged_before_the_error_is_kept(self):
        with mock.patch.object(uma_pipeline.uma_engine, "load_predictor", side_effect=RuntimeError("x")):
            with self.assertRaises(RuntimeError):
                self.run_pipeline()
        self.assertIn("UMAへのアクセスを確認しました。", self.log_text)


if __name__ == "__main__":
    unittest.main()
