import ast
from pathlib import Path


FRED_MACRO_ROOT = Path("src/fred_macro")


def _imports_legacy_template(module_path: Path) -> bool:
    tree = ast.parse(module_path.read_text())

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "vibe_coding" or alias.name.startswith(
                    "vibe_coding."
                ):
                    return True
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module == "vibe_coding" or node.module.startswith("vibe_coding."):
                return True

    return False


def test_fred_macro_does_not_depend_on_vibe_coding():
    offenders: list[str] = []
    for module_path in sorted(FRED_MACRO_ROOT.rglob("*.py")):
        if _imports_legacy_template(module_path):
            offenders.append(str(module_path))

    assert not offenders, (
        "Legacy imports detected in active fred_macro modules. "
        f"Offenders: {offenders}"
    )
