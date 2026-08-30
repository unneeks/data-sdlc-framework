"""Software Bill of Materials (SBOM) analyser.

Parses dependency manifests across multiple ecosystems and produces a
CycloneDX-inspired component inventory.  Uses only stdlib — no external
packages required.
"""

from __future__ import annotations

import ast
import configparser
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Framework / well-known library classification
# ---------------------------------------------------------------------------

_FRAMEWORKS: set[str] = {
    "django", "flask", "fastapi", "tornado", "sanic", "starlette",
    "express", "next", "react", "angular", "vue", "svelte",
    "spring", "rails", "laravel", "gin", "echo", "actix",
    "airflow", "prefect", "dagster", "dbt", "spark",
    "tensorflow", "pytorch", "keras", "scikit-learn",
    "celery", "dramatiq", "rq",
    "strands-agents", "langchain", "crewai", "autogen",
}


def _classify_type(name: str) -> str:
    if name.lower().replace("-", "").replace("_", "") in {
        f.replace("-", "").replace("_", "") for f in _FRAMEWORKS
    }:
        return "framework"
    return "library"


def _purl(name: str, language: str) -> str:
    """Generate a Package URL (purl) string."""
    ecosystems = {
        "python": "pypi",
        "javascript": "npm",
        "typescript": "npm",
        "rust": "cargo",
        "go": "golang",
        "java": "maven",
        "ruby": "gem",
    }
    eco = ecosystems.get(language, language)
    return f"pkg:{eco}/{name.lower()}"


# ---------------------------------------------------------------------------
# Individual parsers
# ---------------------------------------------------------------------------

def _parse_requirements_txt(path: Path, scope: str = "required") -> list[dict[str, Any]]:
    """Parse pip requirements files."""
    components = []
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        # Handle -r includes, -e, etc.
        if line.startswith("-"):
            continue
        # Split on version specifiers
        m = re.match(r"([A-Za-z0-9_.-]+)\s*(.*)", line)
        if m:
            name = m.group(1)
            version = m.group(2).strip() or "*"
            # Clean extras like [all]
            if "[" in name:
                name = name.split("[")[0]
            components.append({
                "type": _classify_type(name),
                "name": name,
                "version": version,
                "source_file": str(path),
                "scope": scope,
                "language": "python",
                "purl": _purl(name, "python"),
            })
    return components


def _parse_setup_py(path: Path) -> list[dict[str, Any]]:
    """Parse setup.py using AST to extract install_requires."""
    components = []
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source)
    except (OSError, SyntaxError):
        return []

    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg in ("install_requires", "setup_requires"):
            scope = "required" if node.arg == "install_requires" else "dev"
            if isinstance(node.value, (ast.List, ast.Tuple)):
                for elt in node.value.elts:
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                        m = re.match(r"([A-Za-z0-9_.-]+)(.*)", elt.value)
                        if m:
                            name = m.group(1)
                            version = m.group(2).strip() or "*"
                            components.append({
                                "type": _classify_type(name),
                                "name": name,
                                "version": version,
                                "source_file": str(path),
                                "scope": scope,
                                "language": "python",
                                "purl": _purl(name, "python"),
                            })
        elif isinstance(node, ast.keyword) and node.arg == "extras_require":
            if isinstance(node.value, ast.Dict):
                for key, val in zip(node.value.keys, node.value.values):
                    extra_name = key.value if isinstance(key, ast.Constant) else "optional"
                    scope = "dev" if extra_name in ("dev", "test", "testing") else "optional"
                    if isinstance(val, (ast.List, ast.Tuple)):
                        for elt in val.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                m = re.match(r"([A-Za-z0-9_.-]+)(.*)", elt.value)
                                if m:
                                    components.append({
                                        "type": _classify_type(m.group(1)),
                                        "name": m.group(1),
                                        "version": m.group(2).strip() or "*",
                                        "source_file": str(path),
                                        "scope": scope,
                                        "language": "python",
                                        "purl": _purl(m.group(1), "python"),
                                    })
    return components


def _parse_setup_cfg(path: Path) -> list[dict[str, Any]]:
    """Parse setup.cfg [options] install_requires."""
    components = []
    try:
        cfg = configparser.ConfigParser()
        cfg.read(str(path), encoding="utf-8")
    except (OSError, configparser.Error):
        return []

    for section_key, scope in [("install_requires", "required"), ("setup_requires", "dev")]:
        raw = cfg.get("options", section_key, fallback="")
        for line in raw.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            m = re.match(r"([A-Za-z0-9_.-]+)(.*)", line)
            if m:
                components.append({
                    "type": _classify_type(m.group(1)),
                    "name": m.group(1),
                    "version": m.group(2).strip() or "*",
                    "source_file": str(path),
                    "scope": scope,
                    "language": "python",
                    "purl": _purl(m.group(1), "python"),
                })
    return components


def _parse_pyproject_toml(path: Path) -> list[dict[str, Any]]:
    """Parse pyproject.toml for dependencies."""
    components = []
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    # Try stdlib tomllib (3.11+)
    parsed = None
    if sys.version_info >= (3, 11):
        try:
            import tomllib
            parsed = tomllib.loads(content)
        except Exception:
            pass

    if parsed:
        # [project] dependencies
        deps = parsed.get("project", {}).get("dependencies", [])
        for dep in deps:
            m = re.match(r"([A-Za-z0-9_.-]+)(.*)", dep)
            if m:
                components.append({
                    "type": _classify_type(m.group(1)),
                    "name": m.group(1),
                    "version": m.group(2).strip() or "*",
                    "source_file": str(path),
                    "scope": "required",
                    "language": "python",
                    "purl": _purl(m.group(1), "python"),
                })

        # [project.optional-dependencies]
        optionals = parsed.get("project", {}).get("optional-dependencies", {})
        for group, deps in optionals.items():
            scope = "dev" if group in ("dev", "test", "testing", "lint") else "optional"
            for dep in deps:
                m = re.match(r"([A-Za-z0-9_.-]+)(.*)", dep)
                if m:
                    components.append({
                        "type": _classify_type(m.group(1)),
                        "name": m.group(1),
                        "version": m.group(2).strip() or "*",
                        "source_file": str(path),
                        "scope": scope,
                        "language": "python",
                        "purl": _purl(m.group(1), "python"),
                    })

        # [build-system] requires
        build_deps = parsed.get("build-system", {}).get("requires", [])
        for dep in build_deps:
            m = re.match(r"([A-Za-z0-9_.-]+)(.*)", dep)
            if m:
                components.append({
                    "type": _classify_type(m.group(1)),
                    "name": m.group(1),
                    "version": m.group(2).strip() or "*",
                    "source_file": str(path),
                    "scope": "dev",
                    "language": "python",
                    "purl": _purl(m.group(1), "python"),
                })
    else:
        # Regex fallback for older Python
        dep_re = re.compile(r'"([A-Za-z0-9_.-]+(?:\[.*?\])?(?:[><=!~]+[^"]*)?)"')
        in_deps = False
        in_optional = False
        current_scope = "required"

        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("[project]"):
                in_deps = False
                in_optional = False
            elif stripped == "dependencies = [":
                in_deps = True
                current_scope = "required"
            elif re.match(r"\w+\s*=\s*\[", stripped) and in_optional:
                scope_name = stripped.split("=")[0].strip()
                current_scope = "dev" if scope_name in ("dev", "test") else "optional"
                in_deps = True
            elif stripped == "[project.optional-dependencies]":
                in_optional = True
            elif stripped == "[build-system]":
                in_deps = False
                in_optional = False
            elif stripped.startswith("requires = ["):
                in_deps = True
                current_scope = "dev"

            if in_deps:
                for m in dep_re.finditer(line):
                    dep_str = m.group(1)
                    pkg_m = re.match(r"([A-Za-z0-9_.-]+)(.*)", dep_str)
                    if pkg_m:
                        name = pkg_m.group(1)
                        if "[" in name:
                            name = name.split("[")[0]
                        components.append({
                            "type": _classify_type(name),
                            "name": name,
                            "version": pkg_m.group(2).strip() or "*",
                            "source_file": str(path),
                            "scope": current_scope,
                            "language": "python",
                            "purl": _purl(name, "python"),
                        })

            if stripped == "]":
                in_deps = False

    return components


def _parse_package_json(path: Path) -> list[dict[str, Any]]:
    """Parse package.json for npm dependencies."""
    components = []
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return []

    for section, scope in [
        ("dependencies", "required"),
        ("devDependencies", "dev"),
        ("peerDependencies", "optional"),
        ("optionalDependencies", "optional"),
    ]:
        deps = data.get(section, {})
        for name, version in deps.items():
            components.append({
                "type": _classify_type(name),
                "name": name,
                "version": version,
                "source_file": str(path),
                "scope": scope,
                "language": "javascript",
                "purl": _purl(name, "javascript"),
            })
    return components


def _parse_cargo_toml(path: Path) -> list[dict[str, Any]]:
    """Parse Cargo.toml for Rust dependencies (regex-based)."""
    components = []
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    in_deps = False
    in_dev_deps = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped == "[dependencies]":
            in_deps = True
            in_dev_deps = False
            continue
        elif stripped == "[dev-dependencies]":
            in_deps = False
            in_dev_deps = True
            continue
        elif stripped.startswith("["):
            in_deps = False
            in_dev_deps = False
            continue

        if in_deps or in_dev_deps:
            m = re.match(r'(\w[\w-]*)\s*=\s*"([^"]*)"', stripped)
            if m:
                scope = "dev" if in_dev_deps else "required"
                components.append({
                    "type": _classify_type(m.group(1)),
                    "name": m.group(1),
                    "version": m.group(2),
                    "source_file": str(path),
                    "scope": scope,
                    "language": "rust",
                    "purl": _purl(m.group(1), "rust"),
                })
    return components


def _parse_go_mod(path: Path) -> list[dict[str, Any]]:
    """Parse go.mod for Go dependencies."""
    components = []
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    in_require = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("require ("):
            in_require = True
            continue
        elif stripped == ")" and in_require:
            in_require = False
            continue

        if in_require or stripped.startswith("require "):
            m = re.match(r"(?:require\s+)?([\w./\-]+)\s+(v[\d.]+\S*)", stripped)
            if m:
                name = m.group(1)
                version = m.group(2)
                components.append({
                    "type": "library",
                    "name": name,
                    "version": version,
                    "source_file": str(path),
                    "scope": "required",
                    "language": "go",
                    "purl": f"pkg:golang/{name}",
                })
    return components


def _parse_pom_xml(path: Path) -> list[dict[str, Any]]:
    """Parse pom.xml for Java dependencies (regex-based, no XML parser needed)."""
    components = []
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    dep_re = re.compile(
        r"<dependency>\s*"
        r"<groupId>([^<]+)</groupId>\s*"
        r"<artifactId>([^<]+)</artifactId>\s*"
        r"(?:<version>([^<]+)</version>)?\s*"
        r"(?:<scope>([^<]+)</scope>)?",
        re.DOTALL,
    )
    for m in dep_re.finditer(content):
        group = m.group(1)
        artifact = m.group(2)
        version = m.group(3) or "*"
        scope = m.group(4) or "required"
        if scope == "compile":
            scope = "required"
        components.append({
            "type": _classify_type(artifact),
            "name": f"{group}:{artifact}",
            "version": version,
            "source_file": str(path),
            "scope": scope,
            "language": "java",
            "purl": f"pkg:maven/{group}/{artifact}",
        })
    return components


def _parse_build_gradle(path: Path) -> list[dict[str, Any]]:
    """Parse build.gradle for dependencies (regex-based)."""
    components = []
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    dep_re = re.compile(
        r"(implementation|api|compileOnly|runtimeOnly|testImplementation|testRuntimeOnly)"
        r"""\s+['"]([^'"]+)['"]"""
    )
    for m in dep_re.finditer(content):
        config = m.group(1)
        dep_str = m.group(2)
        scope = "dev" if "test" in config.lower() else "required"
        parts = dep_str.split(":")
        name = ":".join(parts[:2]) if len(parts) >= 2 else dep_str
        version = parts[2] if len(parts) >= 3 else "*"
        components.append({
            "type": _classify_type(name),
            "name": name,
            "version": version,
            "source_file": str(path),
            "scope": scope,
            "language": "java",
            "purl": f"pkg:maven/{'/'.join(parts[:2]) if len(parts) >= 2 else name}",
        })
    return components


def _parse_gemfile(path: Path) -> list[dict[str, Any]]:
    """Parse Gemfile for Ruby dependencies."""
    components = []
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    gem_re = re.compile(r"""gem\s+['"]([^'"]+)['"](?:\s*,\s*['"]([^'"]+)['"])?""")
    in_dev = False
    for line in content.splitlines():
        stripped = line.strip()
        if "group :development" in stripped or "group :test" in stripped:
            in_dev = True
        elif stripped == "end":
            in_dev = False

        m = gem_re.match(stripped)
        if m:
            components.append({
                "type": _classify_type(m.group(1)),
                "name": m.group(1),
                "version": m.group(2) or "*",
                "source_file": str(path),
                "scope": "dev" if in_dev else "required",
                "language": "ruby",
                "purl": _purl(m.group(1), "ruby"),
            })
    return components


def _parse_dockerfile(path: Path) -> list[dict[str, Any]]:
    """Extract base images and system packages from Dockerfile."""
    components = []
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    # Base images
    for m in re.finditer(r"FROM\s+([\w./-]+)(?::(\S+))?", content):
        image = m.group(1)
        tag = m.group(2) or "latest"
        components.append({
            "type": "container",
            "name": image,
            "version": tag,
            "source_file": str(path),
            "scope": "required",
            "language": "docker",
            "purl": f"pkg:docker/{image}",
        })

    # pip install inside Dockerfile
    for m in re.finditer(r"pip\s+install\s+(.*?)(?:\\?\n|$)", content):
        pkgs = m.group(1)
        for pkg_m in re.finditer(r"([A-Za-z0-9_.-]+)(?:[><=!~]+\S*)?", pkgs):
            name = pkg_m.group(0).split("==")[0].split(">=")[0].split("<=")[0]
            name = name.strip()
            if name and name not in ("-r", "--no-cache-dir", "--upgrade", "-U", "--requirement"):
                components.append({
                    "type": _classify_type(name),
                    "name": name,
                    "version": "*",
                    "source_file": str(path),
                    "scope": "required",
                    "language": "python",
                    "purl": _purl(name, "python"),
                })

    # apt-get install
    for m in re.finditer(r"apt-get\s+install\s+(?:-y\s+)?(.*?)(?:\\?\n|&&|$)", content):
        pkgs = m.group(1)
        for pkg in pkgs.split():
            pkg = pkg.strip().rstrip("\\")
            if pkg and not pkg.startswith("-"):
                components.append({
                    "type": "os",
                    "name": pkg,
                    "version": "*",
                    "source_file": str(path),
                    "scope": "required",
                    "language": "system",
                    "purl": f"pkg:deb/debian/{pkg}",
                })

    return components


def _parse_docker_compose(path: Path) -> list[dict[str, Any]]:
    """Extract service images from docker-compose YAML."""
    components = []
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    for m in re.finditer(r"image:\s*['\"]?(\S+?)['\"]?\s*$", content, re.MULTILINE):
        image_full = m.group(1)
        parts = image_full.split(":")
        image = parts[0]
        tag = parts[1] if len(parts) > 1 else "latest"
        components.append({
            "type": "container",
            "name": image,
            "version": tag,
            "source_file": str(path),
            "scope": "required",
            "language": "docker",
            "purl": f"pkg:docker/{image}",
        })
    return components


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

_PARSERS: list[tuple[str, str, Any]] = [
    ("requirements.txt", "pip-requirements", _parse_requirements_txt),
    ("requirements-*.txt", "pip-requirements", _parse_requirements_txt),
    ("requirements_*.txt", "pip-requirements", _parse_requirements_txt),
    ("constraints.txt", "pip-constraints", lambda p: _parse_requirements_txt(p, "required")),
    ("setup.py", "setuptools", _parse_setup_py),
    ("setup.cfg", "setuptools-cfg", _parse_setup_cfg),
    ("pyproject.toml", "pyproject", _parse_pyproject_toml),
    ("package.json", "npm", _parse_package_json),
    ("Cargo.toml", "cargo", _parse_cargo_toml),
    ("go.mod", "go-mod", _parse_go_mod),
    ("pom.xml", "maven", _parse_pom_xml),
    ("build.gradle", "gradle", _parse_build_gradle),
    ("Gemfile", "bundler", _parse_gemfile),
    ("Dockerfile", "docker", _parse_dockerfile),
    ("Dockerfile.*", "docker", _parse_dockerfile),
    ("docker-compose.yml", "docker-compose", _parse_docker_compose),
    ("docker-compose.yaml", "docker-compose", _parse_docker_compose),
    ("compose.yml", "docker-compose", _parse_docker_compose),
    ("compose.yaml", "docker-compose", _parse_docker_compose),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyse_sbom(
    repository_root: str,
    exclude_dirs: frozenset[str] | None = None,
) -> dict[str, Any]:
    """Generate a Software Bill of Materials for the repository.

    Scans for dependency manifests across all supported ecosystems.
    Returns a CycloneDX-inspired component inventory.
    """
    root = Path(repository_root)
    exclude = exclude_dirs or frozenset(
        {".git", "__pycache__", "node_modules", ".venv", "venv", "dist", "build", ".terraform", "target"}
    )

    all_components: list[dict[str, Any]] = []
    dependency_files: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()  # (name, version, source_file) dedup

    for pattern, file_type, parser in _PARSERS:
        if "*" in pattern:
            matches = sorted(root.rglob(pattern))
        else:
            matches = sorted(root.rglob(pattern))

        for dep_file in matches:
            rel = dep_file.relative_to(root)
            if any(part in exclude for part in rel.parts):
                continue

            components = parser(dep_file)
            new_count = 0
            for comp in components:
                key = (comp["name"], comp["version"], comp["source_file"])
                if key not in seen:
                    seen.add(key)
                    # Store relative path
                    comp["source_file"] = rel.as_posix()
                    all_components.append(comp)
                    new_count += 1

            if new_count > 0 or components:
                dependency_files.append({
                    "path": rel.as_posix(),
                    "type": file_type,
                    "components": len(components),
                })

    # Build summary
    by_language: dict[str, int] = {}
    by_scope: dict[str, int] = {}
    by_type: dict[str, int] = {}
    for comp in all_components:
        lang = comp.get("language", "unknown")
        by_language[lang] = by_language.get(lang, 0) + 1
        scope = comp.get("scope", "required")
        by_scope[scope] = by_scope.get(scope, 0) + 1
        ctype = comp.get("type", "library")
        by_type[ctype] = by_type.get(ctype, 0) + 1

    return {
        "format": "data-sdlc-sbom/1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repository": str(root),
        "components": all_components,
        "summary": {
            "total_components": len(all_components),
            "by_language": by_language,
            "by_scope": by_scope,
            "by_type": by_type,
        },
        "dependency_files": dependency_files,
    }
