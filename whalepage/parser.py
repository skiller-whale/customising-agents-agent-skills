import re
import shlex
from pathlib import Path
from typing import Any

import yaml

from whalepage.errors import SourceError
from whalepage.models import PageBlock, PageDocument, PageMetadata


OPEN_BLOCK = re.compile(r"^:::\s*([a-z][a-z0-9-]*)(?:\s+(.*?))?\s*$")
CLOSE_BLOCK = re.compile(r"^:::\s*$")
OPTION_NAME = re.compile(r"^[a-z][a-z0-9_-]*$")


def parse_document(text: str, source_path: Path) -> PageDocument:
    metadata, body, body_start_line = _parse_frontmatter(text)
    blocks = _parse_blocks(body, body_start_line)
    if not blocks:
        raise SourceError("The page has no content blocks")
    return PageDocument(metadata, tuple(blocks), source_path)


def _parse_frontmatter(text: str) -> tuple[PageMetadata, str, int]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise SourceError("Page Markdown must start with YAML frontmatter")

    try:
        end = next(index for index, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration as exc:
        raise SourceError("Unclosed YAML frontmatter") from exc

    try:
        raw: Any = yaml.safe_load("\n".join(lines[1:end])) or {}
    except yaml.YAMLError as exc:
        raise SourceError(f"Invalid YAML frontmatter: {exc}") from exc

    if not isinstance(raw, dict):
        raise SourceError("YAML frontmatter must be a mapping")

    title = raw.get("title")
    if not isinstance(title, str) or not title.strip():
        raise SourceError("YAML frontmatter requires a non-empty 'title'")

    description = raw.get("description", "")
    language = raw.get("language", "en")
    if not isinstance(description, str):
        raise SourceError("Frontmatter 'description' must be a string")
    if not isinstance(language, str) or not language.strip():
        raise SourceError("Frontmatter 'language' must be a non-empty string")

    body = "\n".join(lines[end + 1 :])
    return PageMetadata(title.strip(), description.strip(), language.strip()), body, end + 2


def _parse_blocks(body: str, first_line: int) -> list[PageBlock]:
    lines = body.splitlines()
    blocks: list[PageBlock] = []
    prose: list[str] = []
    prose_line = first_line
    index = 0

    def flush_prose() -> None:
        nonlocal prose
        markdown = "\n".join(prose).strip()
        if markdown:
            blocks.append(PageBlock("prose", None, {}, markdown, prose_line))
        prose = []

    while index < len(lines):
        line = lines[index]
        line_number = first_line + index

        if CLOSE_BLOCK.match(line):
            raise SourceError(f"Unexpected closing block marker on line {line_number}")

        opening = OPEN_BLOCK.match(line)
        if not opening:
            if not prose:
                prose_line = line_number
            prose.append(line)
            index += 1
            continue

        flush_prose()
        kind = opening.group(1)
        variant, options = _parse_options(opening.group(2) or "", line_number)
        content: list[str] = []
        index += 1

        while index < len(lines) and not CLOSE_BLOCK.match(lines[index]):
            if OPEN_BLOCK.match(lines[index]):
                nested_line = first_line + index
                raise SourceError(
                    f"Nested blocks are not supported (line {nested_line})"
                )
            content.append(lines[index])
            index += 1

        if index == len(lines):
            raise SourceError(
                f"Block '{kind}' opened on line {line_number} is not closed"
            )

        blocks.append(
            PageBlock(kind, variant, options, "\n".join(content).strip(), line_number)
        )
        index += 1

    flush_prose()
    return blocks


def _parse_options(raw: str, line: int) -> tuple[str | None, dict[str, str]]:
    try:
        parts = shlex.split(raw)
    except ValueError as exc:
        raise SourceError(f"Invalid block options on line {line}: {exc}") from exc

    options: dict[str, str] = {}
    for part in parts:
        if "=" not in part:
            raise SourceError(
                f"Invalid block option '{part}' on line {line}; expected name=value"
            )
        name, value = part.split("=", 1)
        if not OPTION_NAME.match(name):
            raise SourceError(f"Invalid block option name '{name}' on line {line}")
        if name in options:
            raise SourceError(f"Duplicate block option '{name}' on line {line}")
        options[name] = value

    return options.pop("variant", None), options
