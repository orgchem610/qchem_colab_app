"""
uma_app.uma_notice
------------------
UMAのライセンス・利用規定・引用に関する情報(一次情報へのリンクと、モデルカードが求めている引用)。

【方針】
    我々の解釈や要約を加えず、一次情報(ライセンス全文・モデルカード・論文)の所在と、
    モデルカードが求めている引用の形を、そのままエンドユーザーに伝える。
    ライセンスの条文の意味や、どのような場合に何をすべきかは、ここでは説明しない
    (利用者が一次情報を読んで判断する)。

【どこに表示するか】
    - ノートブック(ColabApp_UMA.ipynb)の冒頭にだけ表示する。GUI(gui_uma.py)には表示しない。
      ノートブックの文面は、このモジュールの定数と同じ内容に保つ
      (tests/test_uma_notebook.py が、リンクと引用が一致していることを確認する)。
    - 計算ログのファイルの末尾に、同じ一次情報へのリンクを記載する(notice_text)。

【一次情報】(確認日: 2026-10-10)
    ライセンス : https://huggingface.co/facebook/UMA/blob/main/LICENSE (FAIR Chemistry License v1)
    モデルカード: https://huggingface.co/facebook/UMA (Acceptable Use Policy・引用の依頼を含む)
"""

UMA_LICENSE_NAME = "FAIR Chemistry License v1"
LICENSE_URL = "https://huggingface.co/facebook/UMA/blob/main/LICENSE"
MODEL_CARD_URL = "https://huggingface.co/facebook/UMA"
PAPER_URL = "https://arxiv.org/abs/2506.23971"
FAIRCHEM_URL = "https://github.com/facebookresearch/fairchem"

# モデルカードが引用を求めている論文
CITATION = (
    "Wood, B. M. et al. UMA: A Family of Universal Models for Atoms. "
    "arXiv:2506.23971 (2025)."
)


def notice_text():
    """計算ログの末尾に入れる、一次情報へのリンク(プレーンテキスト)。"""
    return "\n".join([
        "[UMAのライセンスと引用]",
        f"- UMAの学習済みモデル: {UMA_LICENSE_NAME}(Meta FAIR Chemistry)  {LICENSE_URL}",
        f"- Acceptable Use Policy・モデルカード: {MODEL_CARD_URL}",
        f"- UMAを利用した成果を発表する場合は、以下の論文を引用してください: {CITATION}  {PAPER_URL}",
    ])
