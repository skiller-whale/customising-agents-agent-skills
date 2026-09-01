from pathlib import Path

import pytest

from whalepage.builder import PageBuilder
from whalepage.errors import BlockError, BuildError
from whalepage.parser import parse_document


ROOT = Path(__file__).parent.parent


def test_builds_example_as_one_self_contained_page() -> None:
    source = ROOT / "examples" / "portfolio.md"
    document = parse_document(source.read_text(encoding="utf-8"), source)

    result = PageBuilder().build(document)

    assert result.blocks == ("hero", "collection", "timeline", "cta", "footer")
    assert "<section class=\"hero hero--split\" id=\"home\">" in result.html
    assert "data:image/svg+xml;base64," in result.html
    assert result.html.count("/* block: button */") == 1
    assert result.html.count("// block: button") == 1
    assert "Jo Rivera" in result.html


def test_rejects_unknown_variants() -> None:
    source = ROOT / "examples" / "portfolio.md"
    document = parse_document(
        """---
title: Bad variant
---
::: hero variant=sideways
# Hello
:::
""",
        source,
    )

    with pytest.raises(BlockError, match="Unknown variant 'sideways'"):
        PageBuilder().build(document)


def test_rejects_invalid_block_options() -> None:
    source = ROOT / "examples" / "portfolio.md"
    document = parse_document(
        """---
title: Bad columns
---
::: collection columns=12
## Work
:::
""",
        source,
    )

    with pytest.raises(BlockError, match="must be one of: 2, 3, 4"):
        PageBuilder().build(document)


def test_builds_the_alternative_variants_and_plain_markdown() -> None:
    source = ROOT / "examples" / "portfolio.md"
    document = parse_document(
        """---
title: Alternative variants
---
Plain Markdown becomes a prose block.

::: hero
# Hello
:::
::: collection variant=list
## Projects
### One
Details.
:::
::: timeline variant=list
## Experience
### One
Details.
:::
::: cta
## Contact
- [Email](mailto:hello@example.com)
:::
""",
        source,
    )

    result = PageBuilder().build(document)

    assert result.blocks == ("prose", "hero", "collection", "timeline", "cta")
    assert "hero--centered" in result.html
    assert "collection__list" in result.html
    assert "timeline-block--list" in result.html
    assert "cta--simple" in result.html


def test_rejects_duplicate_explicit_ids() -> None:
    source = ROOT / "examples" / "portfolio.md"
    document = parse_document(
        """---
title: Duplicate ids
---
::: hero id=top
# Hello
:::
::: cta id=top
## Contact
:::
""",
        source,
    )

    with pytest.raises(BuildError, match="Duplicate block id: top"):
        PageBuilder().build(document)


@pytest.mark.parametrize("example", ["portfolio.md", "shop.md", "music.md"])
def test_builds_each_example(example: str) -> None:
    source = ROOT / "examples" / example
    document = parse_document(source.read_text(encoding="utf-8"), source)

    result = PageBuilder().build(document)

    assert result.html.startswith("<!doctype html>")
    assert len(result.blocks) >= 4
