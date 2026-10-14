"""
tests/test_uma_freq.py
----------------------
uma_app.uma_freq の数値計算部分(中心差分によるHessian・並進回転を除いた調和解析)の
単体テスト。ASEにもUMAにも依存せず、numpyだけで動く。

「原子間をバネでつないだモデル」の解析解や、物理的に成り立つべき性質
(回転しても振動数が変わらない・同位体で質量を変えると 1/√2 になる等)と照らし合わせて、
単位換算と並進・回転の除去が正しいことを確認する。
UMAを使った実際の振動数計算(run_frequency_analysis)は、Colab上での実機確認が必要。
"""

import math
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from uma_app import uma_freq  # noqa: E402

# テストでは、力を厳密に計算できるバネのモデルを使うため、数値微分の刻み幅を小さくして
# (刻み幅の2乗に比例する)差分誤差を無視できるようにしている。
# 実際のUMAでは、ASEの既定と同じ0.01 Åを使う(力に含まれる数値ノイズが微分で
# 増幅されるため、小さくしすぎないほうがよい)。
DELTA = 1e-4


def spring_forces_fn(pairs):
    """pairs = [(i, j, k[eV/Å^2], r0[Å]), ...] の、原子対ごとのバネのモデルの力を返す関数を作る。"""
    def forces_fn(positions):
        positions = np.asarray(positions, dtype=float)
        forces = np.zeros_like(positions)
        for i, j, k, r0 in pairs:
            d = positions[i] - positions[j]
            r = np.linalg.norm(d)
            f = -k * (r - r0) * d / r          # 原子iにはたらく力
            forces[i] += f
            forces[j] -= f
        return forces
    return forces_fn


def equilibrium_pairs(positions, pair_constants):
    """現在の座標での距離を自然長にしたバネのリスト(=その座標がつり合いの位置になる)。"""
    return [(i, j, k, float(np.linalg.norm(positions[i] - positions[j])))
            for i, j, k in pair_constants]


def expected_diatomic_cm1(k_ev_per_a2, m1_amu, m2_amu):
    """二原子分子の調和振動数 [cm^-1] を、SI単位だけで独立に計算した値。"""
    k_si = k_ev_per_a2 * 1.602176634e-19 / 1.0e-20            # N/m
    mu_si = (m1_amu * m2_amu / (m1_amu + m2_amu)) * 1.66053906660e-27   # kg
    omega = math.sqrt(k_si / mu_si)                            # rad/s
    return omega / (2.0 * math.pi * 2.99792458e10)


def rotation_matrix(axis, angle):
    axis = np.asarray(axis, dtype=float)
    axis = axis / np.linalg.norm(axis)
    a, b = math.cos(angle), math.sin(angle)
    x, y, z = axis
    return np.array([
        [a + x * x * (1 - a), x * y * (1 - a) - z * b, x * z * (1 - a) + y * b],
        [y * x * (1 - a) + z * b, a + y * y * (1 - a), y * z * (1 - a) - x * b],
        [z * x * (1 - a) - y * b, z * y * (1 - a) + x * b, a + z * z * (1 - a)],
    ])


def water_like(scale_k=1.0):
    """H-O-H型(角度104.5°)の三原子分子。O-H間とH-H間にバネをつないだモデル。"""
    r_oh, angle = 0.96, math.radians(104.5)
    positions = np.array([
        [0.0, 0.0, 0.0],
        [r_oh, 0.0, 0.0],
        [r_oh * math.cos(angle), r_oh * math.sin(angle), 0.0],
    ])
    constants = [(0, 1, 45.0 * scale_k), (0, 2, 45.0 * scale_k), (1, 2, 5.0 * scale_k)]
    masses = [15.999, 1.008, 1.008]
    return positions, equilibrium_pairs(positions, constants), masses


class TestComputeHessianFd(unittest.TestCase):
    def test_recovers_the_force_constant_matrix_of_a_quadratic_potential(self):
        rng = np.random.default_rng(0)
        a = rng.normal(size=(6, 6))
        k_matrix = a @ a.T + 6 * np.eye(6)               # 対称な正定値行列(2原子分)
        forces_fn = lambda pos: (-k_matrix @ np.asarray(pos).reshape(-1)).reshape(-1, 3)
        hessian = uma_freq.compute_hessian_fd(forces_fn, np.zeros((2, 3)), delta=0.01)
        np.testing.assert_allclose(hessian, k_matrix, atol=1e-9)

    def test_progress_is_reported_per_atom(self):
        calls = []
        uma_freq.compute_hessian_fd(lambda pos: np.zeros((2, 3)), np.zeros((2, 3)),
                                    progress=lambda done, total: calls.append((done, total)))
        self.assertEqual(calls, [(1, 2), (2, 2)])


class TestDiatomic(unittest.TestCase):
    def _frequency(self, k, masses, direction):
        direction = np.asarray(direction, dtype=float)
        direction /= np.linalg.norm(direction)
        positions = np.array([[0.1, -0.2, 0.3], [0.1, -0.2, 0.3] + 1.2 * direction])
        pairs = equilibrium_pairs(positions, [(0, 1, k)])
        hessian = uma_freq.compute_hessian_fd(spring_forces_fn(pairs), positions, DELTA)
        freqs, modes = uma_freq.harmonic_analysis(masses, positions, hessian)
        return freqs, modes

    def test_frequency_matches_the_analytic_value_in_cm1(self):
        freqs, modes = self._frequency(30.0, [1.008, 35.45], [1, 2, 3])
        self.assertEqual(len(freqs), 1)                  # 3N-5 = 1(直線分子)
        self.assertEqual(modes.shape, (1, 2, 3))
        expected = expected_diatomic_cm1(30.0, 1.008, 35.45)
        self.assertAlmostEqual(freqs[0] / expected, 1.0, places=6)

    def test_heavier_isotope_lowers_the_frequency_by_root_two(self):
        light, _ = self._frequency(30.0, [1.008, 1.008], [1, 0, 0])
        heavy, _ = self._frequency(30.0, [2.016, 2.016], [1, 0, 0])
        self.assertAlmostEqual(light[0] / heavy[0], math.sqrt(2.0), places=5)

    def test_negative_curvature_gives_a_negative_frequency(self):
        freqs, _ = self._frequency(-30.0, [1.008, 35.45], [0, 0, 1])
        self.assertEqual(len(freqs), 1)
        self.assertLess(freqs[0], 0)
        expected = expected_diatomic_cm1(30.0, 1.008, 35.45)
        self.assertAlmostEqual(abs(freqs[0]) / expected, 1.0, places=6)

    def test_stretch_mode_moves_the_two_atoms_in_opposite_directions(self):
        _, modes = self._frequency(30.0, [1.008, 35.45], [0, 1, 0])
        # 質量中心が動かない: m1*d1 + m2*d2 = 0
        net = 1.008 * modes[0, 0] + 35.45 * modes[0, 1]
        np.testing.assert_allclose(net, np.zeros(3), atol=1e-9)


class TestPolyatomic(unittest.TestCase):
    def test_nonlinear_triatomic_has_3N_minus_6_modes_all_positive(self):
        positions, pairs, masses = water_like()
        hessian = uma_freq.compute_hessian_fd(spring_forces_fn(pairs), positions, DELTA)
        freqs, modes = uma_freq.harmonic_analysis(masses, positions, hessian)
        self.assertEqual(len(freqs), 3)
        self.assertEqual(modes.shape, (3, 3, 3))
        self.assertTrue(np.all(freqs > 100))
        self.assertTrue(np.all(np.diff(freqs) >= 0))     # 昇順
        # 各モードは長さ1に規格化されている
        np.testing.assert_allclose(np.linalg.norm(modes.reshape(3, -1), axis=1), np.ones(3), atol=1e-9)

    def test_modes_have_no_translation_or_rotation_component(self):
        positions, pairs, masses = water_like()
        masses = np.array(masses)
        hessian = uma_freq.compute_hessian_fd(spring_forces_fn(pairs), positions, DELTA)
        _, modes = uma_freq.harmonic_analysis(masses, positions, hessian)
        com = (masses[:, None] * positions).sum(axis=0) / masses.sum()
        for mode in modes:
            linear_momentum = (masses[:, None] * mode).sum(axis=0)
            angular_momentum = (masses[:, None] * np.cross(positions - com, mode)).sum(axis=0)
            np.testing.assert_allclose(linear_momentum, np.zeros(3), atol=1e-8)
            np.testing.assert_allclose(angular_momentum, np.zeros(3), atol=1e-8)

    def test_frequencies_do_not_change_when_the_molecule_is_rotated(self):
        positions, pairs, masses = water_like()
        base = uma_freq.compute_hessian_fd(spring_forces_fn(pairs), positions, DELTA)
        f0, _ = uma_freq.harmonic_analysis(masses, positions, base)

        rot = rotation_matrix([1.0, 2.0, -1.0], 0.9)
        positions_rot = positions @ rot.T
        pairs_rot = equilibrium_pairs(positions_rot, [(i, j, k) for i, j, k, _ in pairs])
        hess_rot = uma_freq.compute_hessian_fd(spring_forces_fn(pairs_rot), positions_rot, DELTA)
        f1, _ = uma_freq.harmonic_analysis(masses, positions_rot, hess_rot)
        np.testing.assert_allclose(f1, f0, rtol=1e-5)

    def test_stiffer_springs_raise_all_frequencies_by_root_of_the_factor(self):
        positions, pairs, masses = water_like(scale_k=1.0)
        _, pairs4, _ = water_like(scale_k=4.0)
        f1, _ = uma_freq.harmonic_analysis(
            masses, positions, uma_freq.compute_hessian_fd(spring_forces_fn(pairs), positions, DELTA))
        f4, _ = uma_freq.harmonic_analysis(
            masses, positions, uma_freq.compute_hessian_fd(spring_forces_fn(pairs4), positions, DELTA))
        np.testing.assert_allclose(f4 / f1, 2.0 * np.ones(3), rtol=1e-5)

    def test_linear_triatomic_has_3N_minus_5_modes(self):
        # O=C=O型の直線三原子分子。原子間をバネでつないだだけのモデルでは、
        # 直線のつり合いにおける横方向(折れ曲がり)の復元力は0になるため、
        # 折れ曲がり2モードは振動数0付近、伸縮2モードだけが有限の値になる。
        positions = np.array([[-1.16, 0.0, 0.0], [0.0, 0.0, 0.0], [1.16, 0.0, 0.0]])
        pairs = equilibrium_pairs(positions, [(0, 1, 70.0), (1, 2, 70.0), (0, 2, 3.0)])
        hessian = uma_freq.compute_hessian_fd(spring_forces_fn(pairs), positions, DELTA)
        freqs, modes = uma_freq.harmonic_analysis([15.999, 12.011, 15.999], positions, hessian)
        self.assertEqual(len(freqs), 4)                  # 3N-5(回転を6個除いてしまうと3個になる)
        self.assertEqual(modes.shape, (4, 3, 3))
        self.assertEqual(int(np.sum(np.abs(freqs) < 1.0)), 2)
        self.assertEqual(int(np.sum(freqs > 100.0)), 2)


class TestEdgeCases(unittest.TestCase):
    def test_single_atom_returns_no_modes(self):
        freqs, modes = uma_freq.harmonic_analysis([12.0], [[0.0, 0.0, 0.0]], np.zeros((3, 3)))
        self.assertEqual(len(freqs), 0)
        self.assertEqual(modes.shape, (0, 1, 3))


if __name__ == "__main__":
    unittest.main()
