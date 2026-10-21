"""
tests/spec_analysis.py
----------------------
AGENTS.md の仕様書にある「呼出先」「呼出元」「関連テスト」の行を、ソースとテストの構文解析から求める開発用の道具。
(テストではない。tests/test_agents_spec.py が、これを使って AGENTS.md が最新かを検査する。)

使い方(リポジトリ直下で):
    python3 tests/spec_analysis.py            # AGENTS.md の該当行が最新かを調べる(古ければ、差分を表示して終了コード1)
    python3 tests/spec_analysis.py --fix      # AGENTS.md の該当行を、最新の内容に書き換える

求めるもの(すべてプロジェクト内のものだけ。テストは「呼出元」に含めず、「関連テスト」に書く):
    呼出先  : その項目の中で呼ばれる・参照される、他の項目(関数・クラス・メソッド・プロパティ・公開定数)
    呼出元  : その項目を呼ぶ・参照する項目(ノートブックを含む)
    関連テスト: その項目を参照しているテストファイル(下の規則)

関連テストの規則(ソースの構文解析。名前は、識別子と、識別子の形の文字列[hasattrやpatch.objectの引数]から集める):
    - 関数・クラス・定数: テストに、その名前があり、かつ、(名前がプロジェクト全体で1つだけ、またはテストがそのモジュールをimportしている)
    - メソッド・プロパティ: テストが、そのモジュールをimportし、クラス名とメソッド名の両方を含む
    ※ 結果クラスの代用品(SimpleNamespace など)で属性だけを真似るテストは、検出できない。実物のクラスを使うこと。

構文解析では分からない呼出し(型の分からない変数の属性の参照)は、MANUAL_EDGES に手で書く。
"""

import ast
import json
import os
import re
import sys

PKG = "qchem_colab_app"
PACKAGES = ("common_backend", "gui", "pyscf_backend", "uma_backend")
NOTEBOOKS = ("ColabApp.ipynb", "ColabApp_UMA.ipynb")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EXTRA_DOCUMENTED_CONSTANTS = {"OrbitalChoices"}

# 構文解析では分からない呼出し: (呼び出す側, 呼ばれる側)。型の分からない引数・変数の属性の参照、親クラスの呼出し
MANUAL_EDGES = [
    ("uma_backend.uma_pipeline.run_calculation", "uma_backend.uma_optimize.OptimizationResult.final_fmax"),
    ("uma_backend.uma_report.build_log_text", "uma_backend.uma_optimize.OptimizationResult.final_fmax"),
    ("pyscf_backend.freq.FrequencyResult.__init__", "common_backend.vibration.FrequencyResult"),
    ("pyscf_backend.freq.run_frequency_analysis", "common_backend.vibration.FrequencyResult.n_imaginary"),
    ("uma_backend.uma_pipeline.run_calculation", "common_backend.vibration.FrequencyResult.n_imaginary"),
    ("uma_backend.uma_report.build_log_text", "common_backend.vibration.FrequencyResult.zpe_kcal_per_mol"),
]


# ---------------------------------------------------------------------------
# ソースの解析
# ---------------------------------------------------------------------------

class ModInfo:
    def __init__(self, name, tree):
        self.name = name
        self.tree = tree
        self.funcs = set()
        self.classes = {}      # クラス名 -> {"methods": set, "props": set}
        self.consts = set()
        self.imports = {}      # 別名 -> ("module", モジュール名) | ("member", モジュール名, 名前)


def documented_const(name):
    return (name.isupper() and not name.startswith("_")) or name == "__version__" \
        or name in EXTRA_DOCUMENTED_CONSTANTS


def load_modules(repo):
    mods = {}
    for pkg in PACKAGES:
        directory = os.path.join(repo, PKG, pkg)
        for filename in sorted(os.listdir(directory)):
            if filename.endswith(".py") and filename != "__init__.py":
                with open(os.path.join(directory, filename), encoding="utf-8") as f:
                    mods[f"{pkg}.{filename[:-3]}"] = ModInfo(f"{pkg}.{filename[:-3]}", ast.parse(f.read()))
    for m in mods.values():
        for node in m.tree.body:
            if isinstance(node, ast.FunctionDef):
                m.funcs.add(node.name)
            elif isinstance(node, ast.ClassDef):
                methods, props = set(), set()
                for b in node.body:
                    if isinstance(b, ast.FunctionDef):
                        methods.add(b.name)
                        if any(isinstance(d, ast.Name) and d.id == "property" for d in b.decorator_list):
                            props.add(b.name)
                m.classes[node.name] = {"methods": methods, "props": props}
            elif isinstance(node, ast.Assign):
                m.consts.update(t.id for t in node.targets if isinstance(t, ast.Name))
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                m.consts.add(node.target.id)
        register_imports(m, mods)
    return mods


def register_imports(m, mods):
    for node in ast.walk(m.tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[0] == PKG:
            base = ".".join(node.module.split(".")[1:])
            for a in node.names:
                alias = a.asname or a.name
                if f"{base}.{a.name}" in mods:
                    m.imports[alias] = ("module", f"{base}.{a.name}")
                elif base in mods:
                    m.imports[alias] = ("member", base, a.name)


def node_kind(mods, modname, name):
    m = mods[modname]
    if name in m.classes:
        return "class"
    if name in m.funcs:
        return "func"
    if name in m.consts:
        return "const"
    return None


class Analyzer:
    def __init__(self, mods):
        self.mods = mods
        self.edges = []      # (呼ぶ側, 呼ばれる側, 種類, 順序)

    def callee(self, m, expr, local_types, cls_name):
        """式が指す、プロジェクト内の対象 -> (モジュール名, 名前, 種類) または None"""
        if isinstance(expr, ast.Name):
            if node_kind(self.mods, m.name, expr.id):
                return m.name, expr.id, node_kind(self.mods, m.name, expr.id)
            imp = m.imports.get(expr.id)
            if imp and imp[0] == "member" and node_kind(self.mods, imp[1], imp[2]):
                return imp[1], imp[2], node_kind(self.mods, imp[1], imp[2])
            return None
        if isinstance(expr, ast.Attribute) and isinstance(expr.value, ast.Name):
            base, attr = expr.value.id, expr.attr
            imp = m.imports.get(base)
            if imp and imp[0] == "module" and node_kind(self.mods, imp[1], attr):
                return imp[1], attr, node_kind(self.mods, imp[1], attr)
            if base == "self" and cls_name:
                if attr in m.classes.get(cls_name, {}).get("methods", ()):
                    return m.name, f"{cls_name}.{attr}", "method"
                return None
            lt = local_types.get(base)
            if lt and attr in self.mods[lt[0]].classes.get(lt[1], {}).get("methods", ()):
                return lt[0], f"{lt[1]}.{attr}", "method"
        return None

    def analyze_body(self, m, src, fn_node, cls_name):
        local_types = {}
        for n in ast.walk(fn_node):
            if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call) and len(n.targets) == 1 \
                    and isinstance(n.targets[0], ast.Name):
                t = self.callee(m, n.value.func, local_types, cls_name)
                if t and t[2] == "class":
                    local_types[n.targets[0].id] = (t[0], t[1])
        skip = set()           # 呼出しの関数部分・例外・型ヒントの式(別に扱う)
        for n in ast.walk(fn_node):
            if isinstance(n, ast.arg) and n.annotation is not None:
                skip.update(id(x) for x in ast.walk(n.annotation))
            if isinstance(n, ast.FunctionDef) and n.returns is not None:
                skip.update(id(x) for x in ast.walk(n.returns))
            if isinstance(n, ast.AnnAssign):
                skip.update(id(x) for x in ast.walk(n.annotation))
            if isinstance(n, ast.Call):
                skip.add(id(n.func))
            if isinstance(n, ast.ExceptHandler) and n.type is not None:
                skip.update(id(e) for e in (n.type.elts if isinstance(n.type, ast.Tuple) else [n.type]))
        seen, order = set(), 0

        def add(dst, kind):
            nonlocal order
            if dst != src and (dst, kind) not in seen:
                seen.add((dst, kind))
                self.edges.append((src, dst, kind, order))
                order += 1

        ordered = sorted(ast.walk(fn_node), key=lambda x: (getattr(x, "lineno", 0), getattr(x, "col_offset", 0)))
        for n in ordered:
            if isinstance(n, ast.Call):
                t = self.callee(m, n.func, local_types, cls_name)
                if t:
                    add(f"{t[0]}.{t[1]}", "call")
            elif isinstance(n, (ast.Name, ast.Attribute)) and id(n) not in skip:
                t = self.callee(m, n, local_types, cls_name)
                if t and not (isinstance(n, ast.Name) and t[0] == m.name and t[1] == cls_name):
                    add(f"{t[0]}.{t[1]}", "const" if t[2] == "const" else "ref")
            elif isinstance(n, ast.ExceptHandler) and n.type is not None:
                for e in (n.type.elts if isinstance(n.type, ast.Tuple) else [n.type]):
                    t = self.callee(m, e, local_types, cls_name)
                    if t and t[2] == "class":
                        add(f"{t[0]}.{t[1]}", "exc")


def entry_nodes(mods):
    """文書化の対象となる項目: {ノードID: (種類, モジュール名, クラス名またはNone)} と、モジュールごとの定義順"""
    nodes = {}
    for mname, m in mods.items():
        for node in m.tree.body:
            if isinstance(node, ast.FunctionDef):
                nodes[f"{mname}.{node.name}"] = ("func", mname, None)
            elif isinstance(node, ast.ClassDef):
                nodes[f"{mname}.{node.name}"] = ("class", mname, None)
                for b in node.body:
                    if isinstance(b, ast.FunctionDef) and b.name != "__init__":
                        nodes[f"{mname}.{node.name}.{b.name}"] = ("method", mname, node.name)
            else:
                targets = []
                if isinstance(node, ast.Assign):
                    targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
                elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                    targets = [node.target.id]
                for t in targets:
                    if documented_const(t):
                        nodes[f"{mname}.{t}"] = ("const", mname, None)
    return nodes


class Spec:
    """ソース・ノートブック・テストの解析結果。"""

    def __init__(self, repo=ROOT):
        self.repo = repo
        self.mods = load_modules(repo)
        self.nodes = entry_nodes(self.mods)
        an = Analyzer(self.mods)
        for mname, m in self.mods.items():
            for node in m.tree.body:
                if isinstance(node, ast.FunctionDef):
                    an.analyze_body(m, f"{mname}.{node.name}", node, None)
                elif isinstance(node, ast.ClassDef):
                    for b in node.body:
                        if isinstance(b, ast.FunctionDef):
                            an.analyze_body(m, f"{mname}.{node.name}.{b.name}", b, node.name)
        self.edges = list(an.edges)
        for mname, m in self.mods.items():       # モジュール直下の「定数 = 式」が、同じモジュールの定数を使う場合
            for node in m.tree.body:
                targets = []
                if isinstance(node, ast.Assign):
                    targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
                elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                    targets = [node.target.id]
                for target in targets:
                    if documented_const(target):
                        for sub in ast.walk(node.value):
                            if isinstance(sub, ast.Name) and sub.id != target and sub.id in m.consts:
                                self.edges.append((f"{mname}.{target}", f"{mname}.{sub.id}", "const", 50))
        for nb in NOTEBOOKS:
            self.edges += self._notebook_edges(nb)
        for src, dst in MANUAL_EDGES:
            self.edges.append((src, dst, "call", 99))
        self.props = {f"{mn}.{cn}.{p}" for mn, m in self.mods.items()
                      for cn, info in m.classes.items() for p in info["props"]}
        self.dedges = self._document_edges()
        self.tests = self._load_tests()

    def _notebook_edges(self, filename):
        path = os.path.join(self.repo, filename)
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8") as f:
            notebook = json.load(f)
        code = []
        for cell in notebook["cells"]:
            if cell["cell_type"] == "code":
                code.append("\n".join(l for l in "".join(cell["source"]).splitlines()
                                      if not l.lstrip().startswith(("!", "%"))))
        m = ModInfo(filename, ast.parse("\n".join(code)))
        mods = dict(self.mods)
        mods[filename] = m
        register_imports(m, mods)
        an = Analyzer(mods)
        an.analyze_body(m, filename, m.tree, None)
        return an.edges

    def _document_edges(self):
        priority = {"call": 0, "prop": 1, "exc": 2, "ref": 3, "const": 4}
        result = {}
        for src, dst, kind, order in self.edges:
            if kind == "ref" and dst in self.props:
                kind = "prop"
            if dst not in self.nodes:
                continue                     # 文書化の対象でない(非公開の定数など)
            if (src, dst) not in result or priority[kind] < priority[result[(src, dst)][0]]:
                result[(src, dst)] = (kind, order)
        return result

    # --- 関連テスト ---
    def _load_tests(self):
        tests = {}
        directory = os.path.join(self.repo, "tests")
        for filename in sorted(os.listdir(directory)):
            if not (filename.startswith("test_") and filename.endswith(".py")) or filename == "test_agents_spec.py":
                continue
            with open(os.path.join(directory, filename), encoding="utf-8") as f:
                tree = ast.parse(f.read())
            identifiers, imported = set(), set()
            for n in ast.walk(tree):
                if isinstance(n, ast.Name):
                    identifiers.add(n.id)
                elif isinstance(n, ast.Attribute):
                    identifiers.add(n.attr)
                elif isinstance(n, ast.alias):
                    identifiers.add((n.asname or n.name).split(".")[-1])
                elif isinstance(n, ast.Constant) and isinstance(n.value, str) \
                        and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", n.value):
                    identifiers.add(n.value)
                elif isinstance(n, ast.ImportFrom) and n.module and n.module.split(".")[0] == PKG:
                    base = ".".join(n.module.split(".")[1:])
                    for a in n.names:
                        if f"{base}.{a.name}" in self.mods:
                            imported.add(f"{base}.{a.name}")
                        elif base in self.mods:
                            imported.add(base)
            tests[filename] = (identifiers, imported)
        return tests

    def related_tests(self, node):
        kind, mname, cls = self.nodes[node]
        name = node.split(".")[-1]
        counts = {}
        for other in self.nodes:
            if self.nodes[other][0] != "method":
                counts[other.split(".")[-1]] = counts.get(other.split(".")[-1], 0) + 1
        found = []
        for filename, (identifiers, imported) in self.tests.items():
            if kind == "method":
                ok = mname in imported and cls in identifiers and name in identifiers
            else:
                ok = name in identifiers and (counts.get(name, 0) == 1 or mname in imported)
            if ok:
                found.append(filename)
        return found

    # --- 呼出先・呼出元 ---
    def callees(self, node, cur_mod):
        kind = self.nodes[node][0]
        sources = {node, node + ".__init__"} if kind == "class" else {node}
        items = sorted((order, dst, k) for (src, dst), (k, order) in self.dedges.items()
                       if src in sources and dst != node)
        return [self._display(dst, cur_mod) + SUFFIX[k] for _, dst, k in items]

    def callers(self, node, cur_mod):
        items = sorted((src, k) for (src, dst), (k, _) in self.dedges.items() if dst == node)
        return [self._display(src, cur_mod) + SUFFIX[k] for src, k in items]

    @staticmethod
    def _display(node, cur_mod):
        short = node[len(cur_mod) + 1:] if node.startswith(cur_mod + ".") else node
        return f"`{short}`"


SUFFIX = {"call": "", "prop": "（属性として参照）", "exc": "（例外の捕捉）",
          "ref": "（コールバックとして登録）", "const": "（定数）"}


def join_or_none(items):
    return "、".join(items) if items else "なし"


# ---------------------------------------------------------------------------
# AGENTS.md の更新・検査
# ---------------------------------------------------------------------------

ENTRY_RE = re.compile(r"^( *)- `([^`]+)`")
FIELD_RE = re.compile(r"^( *)- (呼出先|呼出元|関連テスト): ")


def _entry_name(signature):
    m = re.match(r"([A-Za-z_][A-Za-z0-9_]*)", signature)
    return m.group(1) if m else None


def update_agents(spec, text):
    """AGENTS.md の本文を受け取り、(更新後の本文, 項目として見つかったノードID の集合, 問題の一覧) を返す。"""
    lines = text.split("\n")
    start = next((i for i, l in enumerate(lines) if l.startswith("## 仕様(モジュールと関数)")), None)
    end = next((i for i, l in enumerate(lines) if l.startswith("### tests")), None)
    if start is None or end is None:
        return text, set(), ["「## 仕様(モジュールと関数)」または「### tests」の見出しが見つかりません"]
    out = lines[:start]
    found, problems = set(), []
    package, module = None, None
    owners = {}                 # 項目の行のインデント -> ノードID(またはノートブック名)
    i = start
    while i < end:
        line = lines[i]
        if line.startswith("### "):
            package, module, owners = line[4:].strip(), None, {}
        m = ENTRY_RE.match(line)
        if m:
            indent, signature = len(m.group(1)), m.group(2)
            owners = {k: v for k, v in owners.items() if k < indent}
            if indent == 0 and signature.endswith(".py"):
                module = f"{package}.{signature[:-3]}" if package in PACKAGES else None
            elif indent == 0 and signature in NOTEBOOKS:
                owners[0] = signature
            elif module in spec.mods and indent in (2, 4):
                name = _entry_name(signature)
                parent = owners.get(2)
                node = f"{module}.{name}" if indent == 2 else f"{parent}.{name}" if parent else None
                if node in spec.nodes:
                    owners[indent] = node
                    found.add(node)
                else:
                    problems.append(f"{module}: 項目 `{signature}` に対応する定義が、ソースにありません")
        f = FIELD_RE.match(line)
        if f:
            owner = owners.get(len(f.group(1)) - 2)
            label = f.group(2)
            if owner in spec.nodes:
                cur_mod = spec.nodes[owner][1]
                if label == "呼出先":
                    out.append(f"{f.group(1)}- 呼出先: {join_or_none(spec.callees(owner, cur_mod))}")
                elif label == "呼出元":
                    out.append(f"{f.group(1)}- 呼出元: {join_or_none(spec.callers(owner, cur_mod))}")
                    related = ["`tests/" + t + "`" for t in spec.related_tests(owner)]
                    out.append(f"{f.group(1)}- 関連テスト: {join_or_none(related)}")
                # 既存の「関連テスト」の行は、上で作り直すため、捨てる
            elif owner in NOTEBOOKS:
                if label == "呼出先":
                    items = sorted((o, d, k) for (s, d, k, o) in
                                   [(s, d, k, o) for s, d, k, o in spec.edges if s == owner] if d in spec.nodes)
                    names = []
                    for _, d, k in items:
                        names.append(f"`{d}`" + SUFFIX["exc" if k == "exc" else "call" if k == "call" else k])
                    out.append(f"{f.group(1)}- 呼出先: {join_or_none(names)}")
                elif label == "呼出元":
                    out.append(line)
            else:
                out.append(line)
            i += 1
            continue
        out.append(line)
        i += 1
    out += lines[end:]
    return "\n".join(out), found, problems


def check(spec, text):
    """AGENTS.md の問題の一覧を返す(空なら最新)。"""
    new_text, found, problems = update_agents(spec, text)
    result = list(problems)
    missing = sorted(set(spec.nodes) - found)
    if missing:
        result.append("仕様書に項目がない定義: " + "、".join(missing))
    if new_text != text:
        old_lines, new_lines = text.split("\n"), new_text.split("\n")
        changed = [n for o, n in zip(old_lines, new_lines) if o != n]
        result.append(f"「呼出先」「呼出元」「関連テスト」の行が古い(約{len(changed)}行)。"
                      "`python3 tests/spec_analysis.py --fix` で更新できる")
    return result


def main(argv):
    spec = Spec()
    path = os.path.join(ROOT, "AGENTS.md")
    if not os.path.exists(path):
        print("AGENTS.md がありません(main ブランチでは、AGENTS.md は管理対象外です)。")
        return 0
    with open(path, encoding="utf-8") as f:
        text = f.read()
    new_text, found, problems = update_agents(spec, text)
    if "--fix" in argv:
        if new_text != text:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_text)
            print("AGENTS.md の「呼出先」「呼出元」「関連テスト」の行を更新しました。")
        else:
            print("AGENTS.md の該当行は、すでに最新です。")
        problems = check(spec, new_text)
        for p in problems:
            print("要対応:", p)
        return 1 if problems else 0
    problems = check(spec, text)
    for p in problems:
        print("要対応:", p)
    if not problems:
        print("AGENTS.md の該当行は、最新です。")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
