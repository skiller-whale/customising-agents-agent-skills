import re
import tomllib
from pathlib import Path
from typing import Any

from whalepage.errors import BlockError
from whalepage.models import BlockDefinition


IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")


class BlockRegistry:
    def __init__(self, root: Path) -> None:
        self.root = root
        self._blocks = self._discover()
        self._validate_dependencies()

    def renderable(self) -> tuple[BlockDefinition, ...]:
        return tuple(block for block in self._blocks.values() if block.renderable)

    def get(self, name: str) -> BlockDefinition:
        try:
            return self._blocks[name]
        except KeyError as exc:
            available = ", ".join(sorted(block.name for block in self.renderable()))
            raise BlockError(f"Unknown block '{name}'. Available blocks: {available}") from exc

    def select_variant(self, block: BlockDefinition, requested: str | None) -> str:
        if not block.renderable:
            raise BlockError(f"Block '{block.name}' cannot be used in Markdown")
        variant = requested or block.default_variant
        if not variant or variant not in block.variants:
            choices = ", ".join(block.variants)
            raise BlockError(
                f"Unknown variant '{variant}' for block '{block.name}'. "
                f"Available variants: {choices}"
            )
        return variant

    def normalise_options(
        self, block: BlockDefinition, raw: dict[str, str]
    ) -> dict[str, Any]:
        specs = block.options
        unknown = sorted(set(raw) - set(specs) - {"id"})
        if unknown:
            raise BlockError(
                f"Unknown option(s) for block '{block.name}': {', '.join(unknown)}"
            )

        result: dict[str, Any] = {}
        for name, spec in specs.items():
            if name in raw:
                result[name] = self._convert_option(block.name, name, raw[name], spec)
            elif "default" in spec:
                result[name] = spec["default"]
            elif spec.get("required", False):
                raise BlockError(f"Block '{block.name}' requires option '{name}'")

        if "id" in raw:
            if not IDENTIFIER.match(raw["id"]):
                raise BlockError(
                    f"Invalid id '{raw['id']}' for block '{block.name}'"
                )
            result["id"] = raw["id"]
        return result

    def resolve_dependencies(self, names: list[str]) -> tuple[BlockDefinition, ...]:
        ordered: list[BlockDefinition] = []
        visited: set[str] = set()
        visiting: list[str] = []

        def visit(name: str) -> None:
            if name in visited:
                return
            if name in visiting:
                cycle = " -> ".join([*visiting[visiting.index(name) :], name])
                raise BlockError(f"Block dependency cycle: {cycle}")
            block = self.get(name)
            visiting.append(name)
            for dependency in block.requires:
                visit(dependency)
            visiting.pop()
            visited.add(name)
            ordered.append(block)

        for name in names:
            visit(name)
        return tuple(ordered)

    def _discover(self) -> dict[str, BlockDefinition]:
        if not self.root.is_dir():
            raise BlockError(f"Block directory does not exist: {self.root}")

        blocks: dict[str, BlockDefinition] = {}
        for manifest in sorted(self.root.glob("*/block.toml")):
            try:
                raw = tomllib.loads(manifest.read_text(encoding="utf-8"))
            except (OSError, tomllib.TOMLDecodeError) as exc:
                raise BlockError(f"Cannot read {manifest}: {exc}") from exc

            name = raw.get("name")
            if not isinstance(name, str) or not IDENTIFIER.match(name):
                raise BlockError(f"Invalid or missing block name in {manifest}")
            if name != manifest.parent.name:
                raise BlockError(
                    f"Block '{name}' must live in a directory with the same name"
                )
            if name in blocks:
                raise BlockError(f"Duplicate block name '{name}'")

            renderable = raw.get("renderable", True)
            variants = tuple(raw.get("variants", []))
            default_variant = raw.get("default_variant")
            requires = tuple(raw.get("requires", []))
            options = raw.get("options", {})
            if not isinstance(renderable, bool):
                raise BlockError(f"'renderable' must be a boolean in {manifest}")
            if not all(isinstance(item, str) for item in (*variants, *requires)):
                raise BlockError(f"'variants' and 'requires' must be string lists in {manifest}")
            if not isinstance(options, dict):
                raise BlockError(f"'options' must be a table in {manifest}")

            if renderable:
                if not variants or default_variant not in variants:
                    raise BlockError(
                        f"Renderable block '{name}' needs variants and a valid default_variant"
                    )
                for variant in variants:
                    template = manifest.parent / "variants" / f"{variant}.html"
                    if not template.is_file():
                        raise BlockError(
                            f"Block '{name}' is missing template for variant '{variant}'"
                        )

            blocks[name] = BlockDefinition(
                name=name,
                path=manifest.parent,
                renderable=renderable,
                default_variant=default_variant,
                variants=variants,
                requires=requires,
                options=options,
            )
        return blocks

    def _validate_dependencies(self) -> None:
        for block in self._blocks.values():
            missing = [name for name in block.requires if name not in self._blocks]
            if missing:
                raise BlockError(
                    f"Block '{block.name}' has unknown dependencies: {', '.join(missing)}"
                )
        self.resolve_dependencies(list(self._blocks))

    @staticmethod
    def _convert_option(
        block_name: str, option_name: str, value: str, spec: dict[str, Any]
    ) -> Any:
        option_type = spec.get("type", "string")
        try:
            if option_type == "integer":
                converted: Any = int(value)
            elif option_type == "boolean":
                lowered = value.lower()
                if lowered not in {"true", "false"}:
                    raise ValueError
                converted = lowered == "true"
            elif option_type == "string":
                converted = value
            else:
                raise BlockError(
                    f"Block '{block_name}' has unsupported option type '{option_type}'"
                )
        except ValueError as exc:
            raise BlockError(
                f"Option '{option_name}' for block '{block_name}' must be {option_type}"
            ) from exc

        choices = spec.get("choices")
        if choices is not None and converted not in choices:
            allowed = ", ".join(str(choice) for choice in choices)
            raise BlockError(
                f"Option '{option_name}' for block '{block_name}' must be one of: {allowed}"
            )
        return converted
