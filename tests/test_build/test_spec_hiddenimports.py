"""Guards StepShot.spec against first-party module drift."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGES = ("ui", "services", "models", "tools")


def _spec_hiddenimports() -> set[str]:
    text = (ROOT / "StepShot.spec").read_text(encoding="utf-8")
    block = text.split("hiddenimports = [", 1)[1].split("]", 1)[0]
    return set(re.findall(r'"([\w.]+)"', block))


def _first_party_modules() -> set[str]:
    modules: set[str] = set()
    for package in PACKAGES:
        modules.add(package)
        for path in (ROOT / package).rglob("*.py"):
            relative = path.parent if path.name == "__init__.py" else path.with_suffix("")
            modules.add(".".join(relative.relative_to(ROOT).parts))
    return modules


def test_spec_lists_every_first_party_module():
    missing = sorted(_first_party_modules() - _spec_hiddenimports())
    assert not missing, f"Add to StepShot.spec hiddenimports: {missing}"
