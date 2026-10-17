"""
common.colab_widgets
--------------------
Google Colab 上で「ブラウザ側(JavaScript)」と「Python側」をつなぐ部品群。
計算エンジン(PySCF/UMA等)には依存しないため、common/ に置いている。

提供するもの:
    1. ファイルのドラッグ&ドロップ領域
         build_drop_zone_html() / parse_dropped_payload()
    2. Colabのコールバック登録の薄いラッパー
         register_callback() / is_colab()
    3. JavaScriptに埋め込む識別子の安全確認
         check_safe_id()

クリックできるエネルギーグラフ(SVG)は、役割が違うため common/energy_plot.py にある
(グラフがPython側の関数を呼ぶ仕組みには、ここの register_callback() を使う)。

設計方針(なぜこの方式にしたか):
    - ipywidgets.FileUpload は、環境によってはドロップ操作を受け付けない。
    - そこで、外部ライブラリに一切頼らず、「ブラウザ側のJavaScriptが、Colabの
      google.colab.kernel.invokeFunction でPython側の関数を呼ぶ」という
      Colab 公式の仕組みだけを使う。

注意:
    JavaScriptを含むHTMLは、IPython.display.display(HTML(...)) で表示すること
    (ipywidgets.HTML ウィジェットの value に入れるとscriptが実行されない)。
"""

import base64
import binascii
import html
import os
import re
import uuid

ALLOWED_STRUCTURE_EXTENSIONS = (".xyz", ".com", ".gjf", ".pdb")
MAX_DROPPED_FILE_BYTES = 5 * 1024 * 1024  # 5 MB(構造ファイルとしては十分大きい)

_SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_]+$")


# -----------------------------------------------------------------------------
# Colab連携の共通部品
# -----------------------------------------------------------------------------

def is_colab():
    """Google Colab上で実行されているかどうか。"""
    try:
        import google.colab  # noqa: F401
        return True
    except ImportError:
        return False


def register_callback(func, prefix="qchem_cb"):
    """JavaScriptから呼べるPython関数としてfuncを登録し、その登録名を返す。

    Colab以外の環境では何もせず None を返す(呼び出し側は None のとき
    ドロップ領域などを出さず、通常のウィジェットだけで動くようにする)。
    """
    try:
        from google.colab import output
    except ImportError:
        return None
    name = f"{prefix}_{uuid.uuid4().hex}"
    output.register_callback(name, func)
    return name


def check_safe_id(value, label):
    """JavaScriptに埋め込む識別子(コールバック名・DOMのid)が、英数字とアンダースコアだけか確認する。"""
    if not isinstance(value, str) or not _SAFE_ID_PATTERN.match(value):
        raise ValueError(f"{label}には英数字とアンダースコアのみ使用できます: {value!r}")
    return value


# -----------------------------------------------------------------------------
# 1. ドラッグ&ドロップ領域
# -----------------------------------------------------------------------------

def parse_dropped_payload(payload, allowed_extensions=ALLOWED_STRUCTURE_EXTENSIONS,
                          max_bytes=MAX_DROPPED_FILE_BYTES):
    """JavaScriptから渡された辞書を検証し、(ファイル名, 中身のbytes)を返す。

    payload は {"name": "xxx.xyz", "content_b64": "<base64文字列>"} の形。
    問題があれば、利用者にそのまま表示できる日本語メッセージの ValueError を送出する。
    """
    if not isinstance(payload, dict) or "name" not in payload or "content_b64" not in payload:
        raise ValueError("ファイル情報を正しく受け取れませんでした。もう一度ドロップしてください。")

    # パス区切りが混ざっていても、ファイル名部分だけを使う
    name = os.path.basename(str(payload["name"]).replace("\\", "/"))
    extension = os.path.splitext(name)[1].lower()
    if extension not in allowed_extensions:
        raise ValueError(f"対応形式は {', '.join(allowed_extensions)} です(受け取ったファイル: {name})。")

    try:
        content = base64.b64decode(payload["content_b64"], validate=True)
    except (binascii.Error, ValueError, TypeError):
        raise ValueError("ファイルの中身を読み取れませんでした。もう一度ドロップしてください。")

    if not content:
        raise ValueError("空のファイルはアップロードできません。")
    if len(content) > max_bytes:
        raise ValueError(
            f"ファイルが大きすぎます({len(content) / 1024 / 1024:.1f} MB。"
            f"上限は {max_bytes / 1024 / 1024:.0f} MB です)。")
    return name, content


_DROP_ZONE_TEMPLATE = """
<div id="__UID__" style="border:2px dashed #5b8def;border-radius:8px;padding:16px;
     max-width:520px;text-align:center;color:#315a9e;background:#f7faff;cursor:pointer;
     font-family:sans-serif;font-size:14px">
  <div>ここへ構造ファイルをドラッグ＆ドロップ<br>(または、この枠をクリックしてファイルを選択)</div>
  <div style="font-size:12px;margin-top:4px">__EXTENSIONS__</div>
  <div id="__UID__-msg" style="margin-top:8px;font-size:12px;color:#555;min-height:16px"></div>
  <input id="__UID__-input" type="file" accept="__ACCEPT__" style="display:none">
</div>
<script>
(function () {
  var zone = document.getElementById('__UID__');
  var input = document.getElementById('__UID__-input');
  var msg = document.getElementById('__UID__-msg');
  if (!zone || zone.getAttribute('data-ready')) { return; }
  zone.setAttribute('data-ready', '1');

  function say(text, ok) {
    msg.textContent = text;
    msg.style.color = (ok === true) ? '#167a2e' : (ok === false ? '#b42318' : '#555');
  }

  var allowed = '__ACCEPT__'.split(',');
  function send(file) {
    if (!file) { return; }
    var dot = file.name.lastIndexOf('.');
    var ext = dot >= 0 ? file.name.substring(dot).toLowerCase() : '';
    if (allowed.indexOf(ext) < 0) {
      say('対応形式は __EXTENSIONS__ です(受け取ったファイル: ' + file.name + ')。', false);
      return;
    }
    if (file.size > __MAX_BYTES__) {
      say('ファイルが大きすぎます(上限 __MAX_MB__ MB)。', false);
      return;
    }
    var reader = new FileReader();
    reader.onerror = function () { say('ファイルの読み込みに失敗しました。', false); };
    reader.onload = function () {
      var text = String(reader.result);
      var encoded = text.substring(text.indexOf(',') + 1);
      if (!(window.google && google.colab && google.colab.kernel &&
            google.colab.kernel.invokeFunction)) {
        say('Colabのカーネルと通信できません。下の「ファイルを選択」ボタンをご利用ください。', false);
        return;
      }
      say(file.name + ' を送信中…');
      google.colab.kernel.invokeFunction('__CALLBACK__',
          [{name: file.name, content_b64: encoded}], {})
        .then(function () {
          say('送信しました: ' + file.name + '(受信結果はこの下の表示でご確認ください)', true);
        })
        .catch(function (e) {
          say('送信に失敗しました: ' + e + '。下の「ファイルを選択」ボタンをご利用ください。', false);
        });
    };
    reader.readAsDataURL(file);
  }

  ['dragenter', 'dragover'].forEach(function (ev) {
    zone.addEventListener(ev, function (e) {
      e.preventDefault(); zone.style.background = '#e8f0fe';
    });
  });
  ['dragleave', 'drop'].forEach(function (ev) {
    zone.addEventListener(ev, function (e) {
      e.preventDefault(); zone.style.background = '#f7faff';
    });
  });
  zone.addEventListener('drop', function (e) {
    var files = e.dataTransfer && e.dataTransfer.files;
    send(files && files[0]);
  });
  zone.addEventListener('click', function () { input.click(); });
  input.addEventListener('change', function () { send(input.files && input.files[0]); });
})();
</script>
"""


def build_drop_zone_html(callback_name, uid=None,
                         extensions=ALLOWED_STRUCTURE_EXTENSIONS,
                         max_bytes=MAX_DROPPED_FILE_BYTES):
    """ドロップ領域のHTML(JavaScript込み)を返す。display(HTML(...))で表示すること。

    ドロップされたファイルは、register_callback()で登録した関数
    (callback_name)に {"name":..., "content_b64":...} として渡される。
    """
    check_safe_id(callback_name, "callback_name")
    uid = check_safe_id(uid or f"qchem_drop_{uuid.uuid4().hex}", "uid")
    replacements = {
        "__UID__": uid,
        "__CALLBACK__": callback_name,
        "__EXTENSIONS__": html.escape(" / ".join(extensions)),
        "__ACCEPT__": html.escape(",".join(extensions)),
        "__MAX_BYTES__": str(int(max_bytes)),
        "__MAX_MB__": f"{max_bytes / 1024 / 1024:.0f}",
    }
    out = _DROP_ZONE_TEMPLATE
    for key, value in replacements.items():
        out = out.replace(key, value)
    return out
