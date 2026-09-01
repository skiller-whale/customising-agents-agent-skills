from pathlib import Path

import pytest

from whalepage.errors import SourceError
from whalepage.parser import parse_document


def test_parses_frontmatter_directives_and_plain_markdown() -> None:
    document = parse_document(
        """---
title: Test page
---

Introductory copy.

::: hero variant=split id=home
# Hello
:::
""",
        Path("page.md"),
    )

    assert document.metadata.title == "Test page"
    assert [block.kind for block in document.blocks] == ["prose", "hero"]
    assert document.blocks[1].variant == "split"
    assert document.blocks[1].options == {"id": "home"}


def test_rejects_nested_blocks() -> None:
    with pytest.raises(SourceError, match="Nested blocks"):
        parse_document(
            """---
title: Test
---
::: hero
::: collection
:::
:::
""",
            Path("page.md"),
        )


def test_rejects_an_unclosed_block() -> None:
    with pytest.raises(SourceError, match="not closed"):
        parse_document(
            """---
title: Test
---
::: hero
# Hello
""",
            Path("page.md"),
        )
