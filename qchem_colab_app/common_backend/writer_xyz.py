"""
common_backend.writer_xyz
-----------------
単一フレーム(最終構造用)および多フレーム(最適化トラジェクトリ用)の
.xyzファイル・文字列を書き出すモジュール。外部ライブラリに依存しない。

計算エンジン(pyscf_backend=PySCF, 将来のuma_backend等)に依存しない共通コードのため、
pyscf_backend側のバージョン番号やモジュール固有の文言をここに埋め込まないこと
(comment引数はNoneならごく簡単な既定文言を使い、エンジン側の詳しい情報
[バージョン・手法名など]を含めたい場合は呼び出し側で組み立てて渡す)。

「最終構造をColabReactionにそのまま渡せる形式でダウンロードできるように」
という要望に対応するため、write_final_structure() が書き出すファイルは、
ColabReactionがreactant/productとして受け付ける標準的な.xyz形式
そのものにしている(独自拡張は入れていない)。
"""

import os

# 最適化の出力ファイル名(PySCF版・UMA版で共通)
FINAL_STRUCTURE_FILENAME = "final_structure_for_ColabReaction.xyz"
TRAJECTORY_FILENAME = "optimization_trajectory.xyz"


def _format_xyz_block(symbols, coords, comment=""):
    lines = [str(len(symbols)), comment]
    for sym, xyz in zip(symbols, coords):
        x, y, z = xyz
        lines.append(f"{sym:<2s} {x:20.12f} {y:20.12f} {z:20.12f}")
    return "\n".join(lines)


def write_final_structure(symbols, coords, filepath, comment="Optimized structure"):
    """最終構造を単一フレームの標準.xyzとして書き出す。

    このファイルはColabReactionのreactant/productとしてそのまま
    アップロードできることを想定している。comment(バージョン・手法名等)は
    呼び出し側(pyscf_backend側やuma_backend側)で組み立てて渡すこと。
    """
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(_format_xyz_block(symbols, coords, comment) + "\n")


def write_trajectory(symbols, coords_history, filepath, energies=None):
    """最適化の全ステップを含む多フレーム.xyzを書き出す(Avogadro等の汎用ビューア向け)。"""
    blocks = []
    for i, coords in enumerate(coords_history):
        if energies and i < len(energies):
            comment = f"step {i}  E = {energies[i]:.8f} Hartree"
        else:
            comment = f"step {i}"
        blocks.append(_format_xyz_block(symbols, coords, comment))
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(blocks) + "\n")


def write_optimization_outputs(out_dir, final_symbols, final_coords, final_comment, opt_result):
    """構造最適化の標準の出力(最終構造と最適化トラジェクトリ)を out_dir に書き出す。

    PySCF版・UMA版の両方が、同じファイル名・同じ形式で出力するための関数。
    opt_result は、symbols・coords_history・energies を持つ最適化結果
    (pyscf_backend.optimize・uma_backend.uma_optimize の OptimizationResult)。
    戻り値は (最終構造のパス, トラジェクトリのパス)。
    """
    final_path = os.path.join(out_dir, FINAL_STRUCTURE_FILENAME)
    write_final_structure(final_symbols, final_coords, final_path, comment=final_comment)
    trajectory_path = os.path.join(out_dir, TRAJECTORY_FILENAME)
    write_trajectory(opt_result.symbols, opt_result.coords_history, trajectory_path, opt_result.energies)
    return final_path, trajectory_path


def xyz_string(symbols, coords, comment=""):
    """ファイルに書き出さず、xyz形式の文字列だけを返す(py3Dmol等に直接渡す用)。"""
    return _format_xyz_block(symbols, coords, comment) + "\n"


def multiframe_xyz_string(symbols, coords_list, comments=None):
    """複数フレームをまとめたxyz文字列を返す(py3Dmolのアニメーション表示用)。"""
    blocks = []
    for i, coords in enumerate(coords_list):
        comment = comments[i] if comments and i < len(comments) else f"frame {i}"
        blocks.append(_format_xyz_block(symbols, coords, comment))
    return "\n".join(blocks) + "\n"
