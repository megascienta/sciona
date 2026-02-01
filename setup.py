"""Setup entrypoint for dynamic package selection."""
from __future__ import annotations

import os
from pathlib import Path
from setuptools import find_packages, setup


def _env_flag(name: str, default: str) -> bool:
    value = os.getenv(name, default)
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _include_addons() -> bool:
    env_value = os.getenv("SCIONA_INCLUDE_ADDONS")
    if env_value is not None:
        return _env_flag("SCIONA_INCLUDE_ADDONS", "1")
    core_only_flag = Path(__file__).with_name(".sciona_core_only")
    return not core_only_flag.exists()




def _packages() -> list[str]:
    include_addons = _include_addons()
    base_packages = find_packages(where="core")
    packages = ["sciona"]
    packages.extend(f"sciona.{name}" for name in base_packages)
    if include_addons:
        addon_packages = find_packages(where="addons")
        packages.extend(f"sciona.addons.{name}" for name in addon_packages)
    return packages


def _package_dir() -> dict[str, str]:
    include_addons = _include_addons()
    package_dir = {"sciona": "core"}
    if not include_addons:
        return package_dir
    addon_packages = find_packages(where="addons")
    for name in addon_packages:
        package_dir[f"sciona.addons.{name}"] = str(Path("addons") / name.replace(".", "/"))
    return package_dir


def _package_data() -> dict[str, list[str]]:
    include_addons = _include_addons()
    data: dict[str, list[str]] = {}
    if not include_addons:
        return data
    data.update({
        "sciona.addons.documentation": ["prompts/**/*.md", "prompts/registry.yaml"],
    })
    return data


if os.getenv("SCIONA_PACKAGING_DEBUG"):
    print(f"[sciona] include_addons={_include_addons()}")
    print(f"[sciona] packages={_packages()}")
    print(f"[sciona] package_dir={_package_dir()}")
    print(f"[sciona] package_data={_package_data()}")


def _entry_points() -> dict[str, list[str]]:
    if not _include_addons():
        return {}
    return {
        "sciona.addons": [
            "documentation=sciona.addons.documentation:register",
        ],
    }


setup(
    packages=_packages(),
    package_dir=_package_dir(),
    package_data=_package_data(),
    entry_points=_entry_points(),
)
