"""
uma_app.uma_notice
------------------
UMAの利用に関する注意書き(ライセンス・利用規定・結果の性質・引用)の文言を
1か所にまとめたモジュール。GUI・ログファイル・READMEで同じ内容を使い回すため、
文言を変えたいときはこのファイルだけを編集すればよい。

【どこまでが法的な義務で、どこからが推奨か】
Hugging Face上のモデルカードとLICENSE(FAIR Chemistry License v1, 2025-05-14更新)を
確認した範囲では、アプリの画面やソースコードに特定の文言を表示せよという条項はない。
条文上の義務は、おおむね次の3点:
    1. UMAの重み等(Materials)を第三者に配布する場合は、同じ契約条件の下で行い、
       契約書の写しも渡す(このアプリは重みを同梱・再配布しない)。
    2. 研究成果を論文等として公表する場合は、Materialsを使用したことを明記する。
    3. 関連法令とAcceptable Use Policy(AUP)を守る。AUPには「既知の危険性を
       最終利用者に適切に開示しないこと」の禁止も含まれる。
本モジュールの注意書きは、2・3を利用者に伝えるための推奨対応であり、
画面表示そのものが法的に義務づけられているわけではない。
公開前には、LICENSE本文が変更されていないか(第8条で変更されうるとされている)
改めて確認すること。法的な助言ではない。
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

# 画面・ログに必ず入れる「結果の性質」の説明(AUPの「既知の危険性の開示」への対応)
RESULT_NATURE = (
    "このアプリの計算結果は、機械学習ポテンシャルUMAによる高速な予測値であり、"
    "DFT等の量子化学計算そのものの値ではありません。学習データに含まれない種類の"
    "分子や電子状態では、誤差が大きくなる可能性があります。"
    "電荷・スピン多重度は正しく指定してください。"
)

# GUIの確認チェックボックスのラベル(チェックを入れないと計算を実行できない)
CONSENT_LABEL = (
    "UMAの利用条件(Hugging Face上のFAIR Chemistry License v1・Acceptable Use Policy)を"
    "確認し、同意済みです"
)


def notice_html():
    """GUI上部に表示する注意書き(HTML文字列)。"""
    return (
        "<div style='border:1px solid #d9b86c;background:#fff8e6;color:#333;"
        "border-radius:6px;padding:8px 12px;max-width:760px;font-size:13px'>"
        "<b>UMAの利用にあたって</b>"
        "<ul style='margin:4px 0 0 0;padding-left:20px'>"
        f"<li>{RESULT_NATURE}</li>"
        "<li>UMAの学習済みモデルは、Meta FAIR Chemistryが"
        f"<a href='{LICENSE_URL}' target='_blank'>{UMA_LICENSE_NAME}</a>の下で提供しています。"
        "Hugging Faceで利用条件に同意した方のみがアクセスできます。"
        "同意は、法的な同意能力のある方が行ってください"
        "(未成年の方は、保護者や指導者の方と相談してから利用してください)。</li>"
        f"<li>利用にあたっては、<a href='{MODEL_CARD_URL}' target='_blank'>モデルカード</a>に"
        "掲載されているAcceptable Use Policyを守ってください"
        "(軍事・戦争・原子力関連の用途、武器の開発、違法薬物、他者を欺く行為などへの"
        "利用が禁止されています)。</li>"
        "<li>結果を論文・報告書などで公表する場合は、UMAを使用したことを明記してください。"
        f"引用: {CITATION} "
        f"(<a href='{PAPER_URL}' target='_blank'>論文</a>、"
        f"<a href='{FAIRCHEM_URL}' target='_blank'>fairchem(MITライセンス)</a>)</li>"
        "</ul></div>"
    )


def notice_text():
    """ログファイル等に入れる注意書き(プレーンテキスト)。"""
    return "\n".join([
        "[UMAに関する注意]",
        f"- {RESULT_NATURE}",
        f"- UMAの学習済みモデルは {UMA_LICENSE_NAME} の下で提供されています: {LICENSE_URL}",
        f"- Acceptable Use Policy は次のモデルカードに掲載されています: {MODEL_CARD_URL}",
        "- 結果を論文・報告書などで公表する場合は、UMAを使用したことを明記してください。",
        f"- 引用: {CITATION}",
    ])
