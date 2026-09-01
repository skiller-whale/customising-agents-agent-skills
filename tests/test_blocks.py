from pathlib import Path

import pytest

from whalepage.blocks import BlockRegistry
from whalepage.errors import BlockError


def _support_block(root: Path, name: str, requires: list[str]) -> None:
    block = root / name
    block.mkdir()
    dependencies = ", ".join(f'"{item}"' for item in requires)
    (block / "block.toml").write_text(
        f'name = "{name}"\nrenderable = false\nrequires = [{dependencies}]\n',
        encoding="utf-8",
    )


def test_resolves_shared_dependencies_once(tmp_path: Path) -> None:
    _support_block(tmp_path, "base", [])
    _support_block(tmp_path, "first", ["base"])
    _support_block(tmp_path, "second", ["base"])

    registry = BlockRegistry(tmp_path)

    assert [block.name for block in registry.resolve_dependencies(["first", "second"])] == [
        "base",
        "first",
        "second",
    ]


def test_rejects_dependency_cycles(tmp_path: Path) -> None:
    _support_block(tmp_path, "first", ["second"])
    _support_block(tmp_path, "second", ["first"])

    with pytest.raises(BlockError, match="first -> second -> first"):
        BlockRegistry(tmp_path)
