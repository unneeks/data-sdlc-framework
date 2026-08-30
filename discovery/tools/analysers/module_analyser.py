"""Module structure analyser — packages, classes, functions, imports.

Uses Python's ``ast`` module for Python files and regex heuristics for
JS/TS, Java, and Go.  Never calls an LLM.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

MAX_AST_SIZE = 200_000  # skip files larger than this for AST parsing
MAX_FILE_SIZE = 500_000


# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------

_EXT_LANG: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".sql": "sql",
    ".tf": "hcl",
    ".sh": "shell",
    ".bash": "shell",
}


def _detect_language(path: Path) -> str | None:
    return _EXT_LANG.get(path.suffix.lower())


# ---------------------------------------------------------------------------
# Python AST helpers
# ---------------------------------------------------------------------------

def _parse_python(path: Path) -> ast.Module | None:
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    if len(source) > MAX_AST_SIZE:
        return None
    try:
        return ast.parse(source, filename=str(path))
    except SyntaxError:
        return None


def _extract_classes(tree: ast.Module) -> list[dict[str, Any]]:
    classes = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            methods = []
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.append(item.name)
            bases = []
            for base in node.bases:
                if isinstance(base, ast.Name):
                    bases.append(base.id)
                elif isinstance(base, ast.Attribute):
                    bases.append(ast.dump(base))
            decorators = []
            for dec in node.decorator_list:
                if isinstance(dec, ast.Name):
                    decorators.append(dec.id)
                elif isinstance(dec, ast.Attribute):
                    decorators.append(ast.dump(dec))
            classes.append({
                "name": node.name,
                "methods": methods,
                "bases": bases,
                "decorators": decorators,
                "line": node.lineno,
            })
    return classes


def _extract_functions(tree: ast.Module) -> list[dict[str, Any]]:
    funcs = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = [a.arg for a in node.args.args if a.arg != "self"]
            decorators = []
            for dec in node.decorator_list:
                if isinstance(dec, ast.Name):
                    decorators.append(dec.id)
                elif isinstance(dec, ast.Attribute):
                    decorators.append(ast.dump(dec))
            funcs.append({
                "name": node.name,
                "args": args,
                "decorators": decorators,
                "is_async": isinstance(node, ast.AsyncFunctionDef),
                "line": node.lineno,
            })
    return funcs


def _extract_imports(tree: ast.Module) -> tuple[list[str], list[str]]:
    """Return (internal_modules, external_packages)."""
    internal: set[str] = set()
    external: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                external.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top = node.module.split(".")[0]
                external.add(top)
    return sorted(internal), sorted(external)


def _extract_docstring(tree: ast.Module) -> str:
    return ast.get_docstring(tree) or ""


def _extract_all(tree: ast.Module) -> list[str] | None:
    """Extract __all__ if defined at module level."""
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        names = []
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                names.append(elt.value)
                        return names
    return None


# ---------------------------------------------------------------------------
# JS/TS heuristic helpers
# ---------------------------------------------------------------------------

_JS_CLASS_RE = re.compile(r"(?:export\s+)?class\s+(\w+)")
_JS_FUNC_RE = re.compile(
    r"(?:export\s+)?(?:async\s+)?function\s+(\w+)|"
    r"(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\("
)
_JS_IMPORT_RE = re.compile(r"""(?:import|require)\s*\(?['"]([^'"]+)['"]""")


def _analyse_js_content(content: str) -> dict[str, Any]:
    classes = [{"name": m.group(1), "methods": [], "bases": []} for m in _JS_CLASS_RE.finditer(content)]
    funcs = []
    for m in _JS_FUNC_RE.finditer(content):
        name = m.group(1) or m.group(2)
        if name:
            funcs.append({"name": name, "args": [], "decorators": []})
    imports_raw = _JS_IMPORT_RE.findall(content)
    external = sorted({i.split("/")[0].lstrip("@") for i in imports_raw if not i.startswith(".")})
    internal = sorted({i for i in imports_raw if i.startswith(".")})
    return {"classes": classes, "functions": funcs, "imports_internal": internal, "imports_external": external}


# ---------------------------------------------------------------------------
# Java heuristic helpers
# ---------------------------------------------------------------------------

_JAVA_CLASS_RE = re.compile(r"(?:public|private|protected)?\s*(?:abstract\s+)?class\s+(\w+)")
_JAVA_METHOD_RE = re.compile(
    r"(?:public|private|protected)\s+(?:static\s+)?(?:[\w<>\[\]]+)\s+(\w+)\s*\("
)
_JAVA_IMPORT_RE = re.compile(r"import\s+([\w.]+);")


def _analyse_java_content(content: str) -> dict[str, Any]:
    classes = [{"name": m.group(1), "methods": [], "bases": []} for m in _JAVA_CLASS_RE.finditer(content)]
    funcs = [{"name": m.group(1), "args": []} for m in _JAVA_METHOD_RE.finditer(content)]
    imports = _JAVA_IMPORT_RE.findall(content)
    external = sorted({i.split(".")[0] for i in imports})
    return {"classes": classes, "functions": funcs, "imports_external": external}


# ---------------------------------------------------------------------------
# Go heuristic helpers
# ---------------------------------------------------------------------------

_GO_FUNC_RE = re.compile(r"func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)\s*\(")
_GO_STRUCT_RE = re.compile(r"type\s+(\w+)\s+struct")
_GO_IMPORT_RE = re.compile(r'"([^"]+)"')


def _analyse_go_content(content: str) -> dict[str, Any]:
    structs = [{"name": m.group(1), "methods": [], "bases": []} for m in _GO_STRUCT_RE.finditer(content)]
    funcs = [{"name": m.group(1), "args": []} for m in _GO_FUNC_RE.finditer(content)]
    imports = _GO_IMPORT_RE.findall(content)
    external = sorted({i.split("/")[0] for i in imports if "." in i.split("/")[0]})
    return {"classes": structs, "functions": funcs, "imports_external": external}


# ---------------------------------------------------------------------------
# Package / module detection
# ---------------------------------------------------------------------------

def _find_python_packages(root: Path, exclude: frozenset[str]) -> list[Path]:
    """Find directories that are Python packages (contain __init__.py)."""
    packages = []
    for init in sorted(root.rglob("__init__.py")):
        rel = init.parent.relative_to(root)
        if any(part in exclude for part in rel.parts):
            continue
        packages.append(init.parent)
    return packages


def _count_lines(path: Path) -> int:
    try:
        return path.read_text(encoding="utf-8", errors="replace").count("\n") + 1
    except OSError:
        return 0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyse_modules(
    repository_root: str,
    exclude_dirs: frozenset[str] | None = None,
) -> list[dict[str, Any]]:
    """Analyse module structure across all supported languages.

    Returns a list of module descriptors — one per Python package, or one
    per standalone file in other languages.
    """
    root = Path(repository_root)
    exclude = exclude_dirs or frozenset(
        {".git", "__pycache__", "node_modules", ".venv", "venv", "dist", "build", ".terraform", "target"}
    )
    modules: list[dict[str, Any]] = []

    # --- Python packages ---
    packages = _find_python_packages(root, exclude)
    analysed_dirs: set[Path] = set()

    for pkg_dir in packages:
        if any(p in analysed_dirs for p in pkg_dir.parents):
            # skip sub-packages — they're included in their parent's analysis
            # actually, let's include them as separate entries for granularity
            pass

        rel = pkg_dir.relative_to(root).as_posix()
        py_files = sorted(f for f in pkg_dir.glob("*.py") if f.is_file())
        if not py_files:
            continue

        total_lines = 0
        all_classes: list[dict] = []
        all_functions: list[dict] = []
        all_internal: set[str] = set()
        all_external: set[str] = set()
        exports: list[str] = []
        docstring = ""
        warnings: list[str] = []

        for py_file in py_files:
            lines = _count_lines(py_file)
            total_lines += lines
            tree = _parse_python(py_file)
            if tree is None:
                warnings.append(f"Could not parse {py_file.name}")
                continue

            if py_file.name == "__init__.py":
                docstring = _extract_docstring(tree)
                all_def = _extract_all(tree)
                if all_def:
                    exports = all_def

            classes = _extract_classes(tree)
            functions = _extract_functions(tree)
            internal, external = _extract_imports(tree)

            for cls in classes:
                cls["source_file"] = py_file.name
            for fn in functions:
                fn["source_file"] = py_file.name

            all_classes.extend(classes)
            all_functions.extend(functions)
            all_internal.update(internal)
            all_external.update(external)

        if not exports:
            exports = sorted(
                {c["name"] for c in all_classes if not c["name"].startswith("_")}
                | {f["name"] for f in all_functions if not f["name"].startswith("_")}
            )

        modules.append({
            "path": rel + "/",
            "type": "package",
            "language": "python",
            "files": len(py_files),
            "lines": total_lines,
            "classes": all_classes,
            "functions": all_functions,
            "imports": {"internal": sorted(all_internal), "external": sorted(all_external)},
            "exports": exports,
            "responsibility_hint": docstring[:200] if docstring else "",
            "warnings": warnings,
        })
        analysed_dirs.add(pkg_dir)

    # --- Standalone Python scripts (not in packages) ---
    for py_file in sorted(root.rglob("*.py")):
        rel_file = py_file.relative_to(root)
        if any(part in exclude for part in rel_file.parts):
            continue
        if py_file.parent in analysed_dirs:
            continue
        if py_file.stat().st_size > MAX_FILE_SIZE:
            continue

        tree = _parse_python(py_file)
        if tree is None:
            continue

        classes = _extract_classes(tree)
        functions = _extract_functions(tree)
        internal, external = _extract_imports(tree)
        docstring = _extract_docstring(tree)

        modules.append({
            "path": rel_file.as_posix(),
            "type": "script",
            "language": "python",
            "files": 1,
            "lines": _count_lines(py_file),
            "classes": classes,
            "functions": functions,
            "imports": {"internal": internal, "external": external},
            "exports": [c["name"] for c in classes if not c["name"].startswith("_")]
                     + [f["name"] for f in functions if not f["name"].startswith("_")],
            "responsibility_hint": docstring[:200] if docstring else "",
            "warnings": [],
        })

    # --- JS/TS files ---
    for ext in (".js", ".jsx", ".ts", ".tsx"):
        for js_file in sorted(root.rglob(f"*{ext}")):
            rel_file = js_file.relative_to(root)
            if any(part in exclude for part in rel_file.parts):
                continue
            if js_file.stat().st_size > MAX_FILE_SIZE:
                continue
            try:
                content = js_file.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            info = _analyse_js_content(content)
            lang = "typescript" if ext in (".ts", ".tsx") else "javascript"
            modules.append({
                "path": rel_file.as_posix(),
                "type": "module",
                "language": lang,
                "files": 1,
                "lines": content.count("\n") + 1,
                "classes": info["classes"],
                "functions": info["functions"],
                "imports": {"internal": info["imports_internal"], "external": info["imports_external"]},
                "exports": [],
                "responsibility_hint": "",
                "warnings": [],
            })

    # --- Java files ---
    for java_file in sorted(root.rglob("*.java")):
        rel_file = java_file.relative_to(root)
        if any(part in exclude for part in rel_file.parts):
            continue
        if java_file.stat().st_size > MAX_FILE_SIZE:
            continue
        try:
            content = java_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        info = _analyse_java_content(content)
        modules.append({
            "path": rel_file.as_posix(),
            "type": "module",
            "language": "java",
            "files": 1,
            "lines": content.count("\n") + 1,
            "classes": info["classes"],
            "functions": info["functions"],
            "imports": {"internal": [], "external": info["imports_external"]},
            "exports": [],
            "responsibility_hint": "",
            "warnings": [],
        })

    # --- Go files ---
    for go_file in sorted(root.rglob("*.go")):
        rel_file = go_file.relative_to(root)
        if any(part in exclude for part in rel_file.parts):
            continue
        if go_file.stat().st_size > MAX_FILE_SIZE:
            continue
        try:
            content = go_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        info = _analyse_go_content(content)
        modules.append({
            "path": rel_file.as_posix(),
            "type": "module",
            "language": "go",
            "files": 1,
            "lines": content.count("\n") + 1,
            "classes": info["classes"],
            "functions": info["functions"],
            "imports": {"internal": [], "external": info["imports_external"]},
            "exports": [],
            "responsibility_hint": "",
            "warnings": [],
        })

    return modules
