#!/usr/bin/env python3
"""Licence gate for Python and npm.

Read ``licenses/policy.toml`` and check both dependency trees against it.
``cargo deny check licenses`` covers the Rust tree.

Runtime and development dependencies are checked separately. Anything shipped
in the bundle must be on the allowlist, while a test tool under MPL-2.0 is not
distributed. This distinction prevents false positives from weakening the
gate.

This deliberately avoids the unmaintained ``license-checker`` package and its
security warnings from outdated ``glob`` versions. Built-in ``npm query``
provides the same metadata.

Usage::

    python scripts/check-licenses.py                 # everything
    python scripts/check-licenses.py --only npm      # one ecosystem
    python scripts/check-licenses.py --report        # summary without checks

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POLICY = ROOT / "licenses" / "policy.toml"

RED = "\033[31m"
YELLOW = "\033[33m"
GREEN = "\033[32m"
GRAY = "\033[90m"
RESET = "\033[0m"


@dataclass
class Package:
    name: str
    version: str
    license: str
    ecosystem: str
    runtime: bool


@dataclass
class Finding:
    package: Package
    kind: str  # "forbidden", "denylist", "unknown", "review"
    reason: str
    replacement: str = ""


@dataclass
class Result:
    checked: int = 0
    findings: list[Finding] = field(default_factory=list)
    notes: list[Finding] = field(default_factory=list)


def load_policy() -> dict:
    if not POLICY.exists():
        sys.exit(f"{RED}Policy is missing: {POLICY}{RESET}")
    with POLICY.open("rb") as f:
        return tomllib.load(f)


# --- Licence expressions ---------------------------------------------------


def split_expression(expression: str) -> list[str]:
    """Split an SPDX expression into individual identifiers.

    For ``OR``, one allowed alternative is sufficient; for ``AND``, every
    identifier must be allowed. :func:`evaluate` applies this distinction.
    """
    without_parentheses = expression.replace("(", " ").replace(")", " ")
    parts = re.split(r"\s+(?:OR|AND|WITH)\s+", without_parentheses, flags=re.IGNORECASE)
    return [part.strip() for part in parts if part.strip()]


def is_allowed(identifier: str, allow: set[str]) -> bool:
    return identifier in allow or identifier.rstrip("+") in allow


def matches_denylist(expression: str, patterns: list[str]) -> str | None:
    upper = expression.upper()
    for pattern in patterns:
        if pattern.upper() in upper:
            # LGPL contains "GPL". Both are forbidden, but report the more
            # precise pattern from the policy.
            return pattern
    return None


def evaluate(package: Package, policy: dict) -> Finding | None:
    """Check one package against the policy; ``None`` means it is allowed."""
    allow = set(policy["allow"]["spdx"])
    review = set(policy.get("review", {}).get("spdx", []))
    exceptions = {entry["package"].lower() for entry in policy.get("exceptions", [])}

    name = package.name.lower()

    # 1. Packages forbidden by name, independently of reported metadata. This
    # also catches permissive metadata paired with problematic bundled files.
    # `applies_to = "runtime"` still permits a development-only tool.
    for entry in policy.get("forbidden", []):
        names = {entry["package"].lower()} | {
            alias.lower() for alias in entry.get("aliases", [])
        }
        if name in names:
            runtime_only = entry.get("applies_to") == "runtime"
            if runtime_only and not package.runtime:
                return Finding(
                    package, "note",
                    "Allowed only as a tool; it must not enter the bundle",
                    entry.get("replacement", ""),
                )
            return Finding(package, "forbidden", entry["reason"].strip(),
                           entry.get("replacement", ""))

    # 2. Documented exception.
    if name in exceptions:
        return None

    # 3. Denylist
    if match := matches_denylist(package.license, policy["deny"]["pattern"]):
        # Copyleft in development tools is reported but does not fail because
        # those tools are not distributed.
        kind = "denylist" if package.runtime else "note"
        return Finding(package, kind, f"Licence contains forbidden pattern {match!r}")

    # 4. Allowlist. One allowed alternative is sufficient for OR.
    identifiers = split_expression(package.license)
    if not identifiers:
        return Finding(package, "unknown", "No licence metadata found")

    has_or = re.search(r"\sOR\s", package.license, re.IGNORECASE) is not None
    allowed = [is_allowed(identifier, allow) for identifier in identifiers]

    if (has_or and any(allowed)) or (not has_or and all(allowed)):
        return None

    # 5. Review list.
    if any(is_allowed(identifier, review) for identifier in identifiers):
        return Finding(
            package,
            "review" if package.runtime else "note",
            "Requires a documented exception in licenses/policy.toml",
        )

    unknown = [identifier for identifier, ok in zip(identifiers, allowed, strict=True) if not ok]
    return Finding(
        package,
        "unknown" if package.runtime else "note",
        f"Not on the allowlist: {', '.join(unknown)}",
    )


# --- Python ----------------------------------------------------------------


def python_packages() -> list[Package]:
    """Return installed Python packages with licence and runtime markers."""
    sidecar = ROOT / "sidecar"
    if not (sidecar / "pyproject.toml").exists():
        return []

    # uv export --no-dev returns exactly the packages shipped in the bundle.
    runtime_names: set[str] = set()
    try:
        export = subprocess.run(
            ["uv", "export", "--no-dev", "--no-emit-project",
             "--format", "requirements-txt", "--no-hashes"],
            cwd=sidecar, capture_output=True, text=True, timeout=120, check=True,
        )
        for line in export.stdout.splitlines():
            line = line.strip()
            if line and not line.startswith(("#", "-")):
                name = re.split(r"[=<>;\[ ]", line)[0]
                if name:
                    runtime_names.add(name.lower().replace("_", "-"))
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as exc:
        print(f"{YELLOW}uv export failed ({exc}); treating every package as runtime{RESET}")

    # Read licences from the installed environment.
    code = (
        "import json\n"
        "from importlib.metadata import distributions\n"
        "result = []\n"
        "for d in distributions():\n"
        "    m = d.metadata\n"
        "    lic = m.get('License-Expression') or m.get('License') or ''\n"
        "    if not lic or len(lic) > 120:\n"
        "        classifiers = [c for c in m.get_all('Classifier') or [] "
        "if c.startswith('License ::')]\n"
        "        if classifiers:\n"
        "            lic = classifiers[-1].split('::')[-1].strip()\n"
        "    result.append({'name': m['Name'] or '', 'version': m['Version'] or '', "
        "'license': (lic or 'UNKNOWN').strip()})\n"
        "print(json.dumps(result))\n"
    )
    try:
        raw = subprocess.run(
            ["uv", "run", "--no-project", "--with-requirements", "/dev/null", "python", "-c", code],
            cwd=sidecar, capture_output=True, text=True, timeout=120,
        )
        if raw.returncode != 0:
            raw = subprocess.run(
                ["uv", "run", "python", "-c", code],
                cwd=sidecar, capture_output=True, text=True, timeout=120, check=True,
            )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as exc:
        print(f"{YELLOW}Could not read Python licences: {exc}{RESET}")
        return []

    packages = []
    for entry in json.loads(raw.stdout):
        normalized = entry["name"].lower().replace("_", "-")
        packages.append(
            Package(
                name=entry["name"],
                version=entry["version"],
                license=_clean(entry["license"]),
                ecosystem="python",
                runtime=not runtime_names or normalized in runtime_names,
            )
        )
    return packages


# Map classifier text to SPDX identifiers. Many older packages provide only a
# classifier rather than an SPDX identifier.
_CLASSIFIERS = {
    "mit license": "MIT",
    "mit": "MIT",
    "apache software license": "Apache-2.0",
    "bsd license": "BSD-3-Clause",
    "bsd": "BSD-3-Clause",
    "isc license (iscl)": "ISC",
    "python software foundation license": "PSF-2.0",
    "mozilla public license 2.0 (mpl 2.0)": "MPL-2.0",
    "historical permission notice and disclaimer (hpnd)": "HPND",
    "zlib/libpng license": "Zlib",
    "the unlicense (unlicense)": "Unlicense",
    "gnu general public license v2 (gplv2)": "GPL-2.0",
    "gnu lesser general public license v2 (lgplv2)": "LGPL-2.0",
}


def _clean(license_name: str) -> str:
    key = license_name.strip().lower()
    return _CLASSIFIERS.get(key, license_name.strip())


# --- npm -------------------------------------------------------------------


def npm_packages() -> list[Package]:
    """Return npm packages through built-in ``npm query``."""
    if not (ROOT / "package.json").exists():
        return []

    def query(selector: str) -> list[dict]:
        try:
            raw = subprocess.run(
                ["npm", "query", selector],
                cwd=ROOT, capture_output=True, text=True, timeout=120, check=True,
            )
            return json.loads(raw.stdout)
        except (subprocess.CalledProcessError, FileNotFoundError,
                subprocess.TimeoutExpired, json.JSONDecodeError):
            return []

    # `.prod` marks everything reachable through dependencies, which is the
    # set that may enter the shipped bundle.
    runtime = {package.get("name") for package in query(".prod")}
    all_packages = query("*")

    seen: set[tuple[str, str]] = set()
    packages = []
    for entry in all_packages:
        name = entry.get("name") or ""
        version = entry.get("version") or ""
        if not name or (name, version) in seen:
            continue
        seen.add((name, version))
        packages.append(
            Package(
                name=name,
                version=version,
                license=(entry.get("license") or "UNKNOWN"),
                ecosystem="npm",
                runtime=name in runtime,
            )
        )
    return packages


# --- Reporting -------------------------------------------------------------


def check(packages: list[Package], policy: dict) -> Result:
    result = Result(checked=len(packages))
    for package in packages:
        finding = evaluate(package, policy)
        if finding is None:
            continue
        if finding.kind == "note":
            result.notes.append(finding)
        else:
            result.findings.append(finding)
    return result


def show(title: str, result: Result) -> None:
    print(f"\n{title}: {result.checked} packages checked")

    for finding in result.findings:
        package = finding.package
        print(f"  {RED}✗{RESET} {package.name} {package.version} — {package.license}")
        print(f"      {finding.reason}")
        if finding.replacement:
            print(f"      {GREEN}Replacement:{RESET} {finding.replacement}")

    for finding in result.notes:
        package = finding.package
        print(f"  {GRAY}·{RESET} {package.name} {package.version} — {package.license} "
              f"{GRAY}(development only){RESET}")

    if not result.findings:
        print(f"  {GREEN}✓{RESET} no violations")


def report(packages: list[Package]) -> None:
    from collections import Counter

    for section, runtime in (("Runtime (in bundle)", True), ("Development", False)):
        filtered = [package for package in packages if package.runtime == runtime]
        if not filtered:
            continue
        print(f"\n{section}: {len(filtered)} packages")
        for license_name, count in Counter(package.license for package in filtered).most_common():
            print(f"  {count:>4}  {license_name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", choices=["python", "npm"], help="check one ecosystem")
    parser.add_argument("--report", action="store_true", help="show a summary without checks")
    args = parser.parse_args()

    policy = load_policy()
    all_packages: list[Package] = []
    errors = 0

    if args.only != "npm":
        packages = python_packages()
        all_packages += packages
        if not args.report:
            result = check(packages, policy)
            show("Python", result)
            errors += len(result.findings)

    if args.only != "python":
        packages = npm_packages()
        all_packages += packages
        if not args.report:
            result = check(packages, policy)
            show("npm", result)
            errors += len(result.findings)

    if args.report:
        report(all_packages)
        return 0

    print()
    if errors:
        print(f"{RED}{errors} licence violation(s); build stopped.{RESET}")
        print("Replace the package or add a documented exception to")
        print("licenses/policy.toml with package, licence, reason and source.")
        return 1

    print(f"{GREEN}All licences are allowed.{RESET}")
    print(f"{GRAY}`cargo deny check licenses` checks the Rust tree.{RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
