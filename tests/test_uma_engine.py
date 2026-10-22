"""
tests/test_uma_engine.py
------------------------
uma_backend.uma_engine(デバイスの説明・モデルの読み込み・Calculator・Atoms)のうち、モデルの実際の読み込みと推論を
しない部分の単体テスト。
    - Atoms: 実物のASEの Atoms と、common_backend.ase_bridge の本物の変換で確認する。
    - デバイス名: 実物のtorchを使い、GPU名を返す関数だけを差し替える(GPUがない環境でも確認できる)。
    - モデルの読み込み: 実物のfairchemの pretrained_mlip を使い、モデルを取得する関数 get_predict_unit だけを差し替える
      (Hugging Faceへの接続・モデルのダウンロードはしない)。uma_hf(認証・例外)との受け渡しを確認する。
モデルの実際の読み込みと推論は、Colab上での実機確認が必要。
ASE・torch・fairchemが入っていない環境では、それを使うテストだけをスキップする。
"""

import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import real_molecules as rm  # noqa: E402
from qchem_colab_app.common_backend import ase_bridge, io_reader  # noqa: E402
from qchem_colab_app.uma_backend import uma_engine, uma_hf  # noqa: E402

SKIP_NO_ASE = "ASEがインストールされていないためスキップ"
SKIP_NO_TORCH = "torchがインストールされていないためスキップ"
SKIP_NO_FAIRCHEM = "fairchemがインストールされていないためスキップ"


class TestDevice(unittest.TestCase):
    def test_cpu_description_mentions_the_slowness(self):
        self.assertIn("時間がかかります", uma_engine.describe_device("cpu"))

    @unittest.skipUnless(rm.HAS_TORCH, SKIP_NO_TORCH)
    def test_gpu_description_names_the_device(self):
        import torch
        with mock.patch.object(torch.cuda, "get_device_name", return_value="Tesla T4") as get_name:
            self.assertEqual(uma_engine.describe_device("cuda"), "GPU(Tesla T4)")
        get_name.assert_called_once_with(0)

    def test_gpu_description_without_torch_falls_back_to_a_plain_label(self):
        with mock.patch.dict(sys.modules, {"torch": None}):
            self.assertEqual(uma_engine.describe_device("cuda"), "GPU")

    def test_choosing_the_device_is_not_done_here(self):
        # 使うデバイスの判定は common_backend.runtime.torch_cuda_available()(tests/test_runtime.py が検査)
        self.assertFalse(hasattr(uma_engine, "get_device"))


@unittest.skipUnless(rm.HAS_ASE, SKIP_NO_ASE)
class TestBuildAtoms(unittest.TestCase):
    """Atoms本体の作成は ase_bridge(本物)に任せ、ここでは、電荷・スピン多重度の設定(UMA固有)を確認する。"""

    STRUCTURE = io_reader.Structure(symbols=["O", "H", "H"],
                                    coords=[[0.0, 0.0, 0.1], [0.0, 0.76, -0.47], [0.0, -0.76, -0.47]])

    def _build(self, charge, multiplicity):
        with mock.patch.object(uma_engine.ase_bridge, "structure_to_atoms",
                               wraps=ase_bridge.structure_to_atoms) as convert:
            atoms = uma_engine.build_atoms(self.STRUCTURE, charge, multiplicity)
        convert.assert_called_once_with(self.STRUCTURE)
        return atoms

    def test_the_result_is_a_real_ase_atoms_of_the_structure(self):
        from ase import Atoms
        atoms = self._build(0, 1)
        self.assertIsInstance(atoms, Atoms)
        self.assertEqual(atoms.get_chemical_symbols(), ["O", "H", "H"])
        self.assertAlmostEqual(atoms.get_positions()[1][1], 0.76)

    def test_charge_and_spin_are_stored_in_the_info_for_the_omol_task(self):
        atoms = self._build(-1, 2)
        self.assertEqual(atoms.info, {"charge": -1, "spin": 2})

    def test_values_are_converted_to_plain_integers(self):
        atoms = self._build(1.0, 3.0)
        self.assertIs(type(atoms.info["charge"]), int)
        self.assertIs(type(atoms.info["spin"]), int)


class GatedRepoError(Exception):
    """huggingface_hubの例外と同じ名前のダミー(クラス名で判定する実装のため)。"""


class TestLoadPredictorWithoutFairchem(unittest.TestCase):
    def setUp(self):
        uma_engine.clear_predictor_cache()
        self.addCleanup(uma_engine.clear_predictor_cache)

    def test_missing_fairchem_is_reported_as_a_setup_error(self):
        with mock.patch.dict(sys.modules, {"fairchem": None, "fairchem.core": None}):
            with self.assertRaises(uma_hf.UmaSetupError) as ctx:
                uma_engine.load_predictor("uma-s-1p2p1", "cpu")
        self.assertIn("fairchem-core", str(ctx.exception))


@unittest.skipUnless(rm.HAS_FAIRCHEM, SKIP_NO_FAIRCHEM)
class TestLoadPredictor(unittest.TestCase):
    """実物のfairchemを読み込み、モデルを取得する関数 get_predict_unit だけを差し替える。"""

    def setUp(self):
        uma_engine.clear_predictor_cache()
        self.addCleanup(uma_engine.clear_predictor_cache)

    @staticmethod
    def _patched_get_predict_unit(**kwargs):
        from fairchem.core import pretrained_mlip
        return mock.patch.object(pretrained_mlip, "get_predict_unit", **kwargs)

    def test_gated_repo_error_is_explained_as_a_setup_error(self):
        with self._patched_get_predict_unit(side_effect=GatedRepoError("gated")):
            with self.assertRaises(uma_hf.UmaSetupError) as ctx:
                uma_engine.load_predictor("uma-s-1p2p1", "cpu")
        self.assertIn("利用条件に同意", str(ctx.exception))

    def test_other_errors_are_not_wrapped(self):
        with self._patched_get_predict_unit(side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError) as ctx:
                uma_engine.load_predictor("uma-s-1p2p1", "cpu")
        self.assertNotIsInstance(ctx.exception, uma_hf.UmaSetupError)

    def test_the_model_name_and_device_are_passed_to_fairchem(self):
        predictor = object()
        with self._patched_get_predict_unit(return_value=predictor) as get_predict_unit:
            self.assertIs(uma_engine.load_predictor("uma-s-1p2p1", "cuda"), predictor)
        get_predict_unit.assert_called_once_with("uma-s-1p2p1", device="cuda")

    def test_the_same_model_and_device_are_loaded_only_once(self):
        with self._patched_get_predict_unit(side_effect=lambda name, device: object()) as get_predict_unit:
            first = uma_engine.load_predictor("uma-s-1p2p1", "cpu")
            second = uma_engine.load_predictor("uma-s-1p2p1", "cpu")
            uma_engine.clear_predictor_cache()
            third = uma_engine.load_predictor("uma-s-1p2p1", "cpu")
        self.assertIs(first, second)
        self.assertIsNot(first, third)
        self.assertEqual(get_predict_unit.call_count, 2)


class TestModuleSplit(unittest.TestCase):
    def test_authentication_names_are_not_in_uma_engine_any_more(self):
        for name in ("UmaSetupError", "login_with_token", "login_from_environment", "has_hf_token",
                     "explain_hf_error", "check_model_access", "MODEL_REPO_ID", "HF_TOKEN_ENV",
                     "LICENSE_FILENAME"):
            self.assertTrue(hasattr(uma_hf, name), name)
            self.assertFalse(hasattr(uma_engine, name), name)

    def test_device_model_and_atoms_functions_remain_in_uma_engine(self):
        for name in ("describe_device", "load_predictor", "clear_predictor_cache",
                     "make_calculator", "build_atoms"):
            self.assertTrue(hasattr(uma_engine, name), name)
            self.assertFalse(hasattr(uma_hf, name), name)


if __name__ == "__main__":
    unittest.main()
