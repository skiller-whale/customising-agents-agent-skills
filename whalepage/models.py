from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from markupsafe import Markup


@dataclass(frozen=True)
class PageMetadata:
    title: str
    description: str = ""
    language: str = "en"


@dataclass(frozen=True)
class PageBlock:
    kind: str
    variant: str | None
    options: dict[str, str]
    markdown: str
    line: int


@dataclass(frozen=True)
class PageDocument:
    metadata: PageMetadata
    blocks: tuple[PageBlock, ...]
    source_path: Path


@dataclass(frozen=True)
class Image:
    src: str
    alt: str
    title: str | None = None


@dataclass(frozen=True)
class Action:
    label: str
    href: str
    title: str | None = None


@dataclass(frozen=True)
class ContentItem:
    title: str
    title_html: Markup
    body_html: Markup
    image: Image | None = None
    actions: tuple[Action, ...] = ()


@dataclass(frozen=True)
class BlockContent:
    heading: str | None
    heading_html: Markup
    body_html: Markup
    image: Image | None
    actions: tuple[Action, ...]
    items: tuple[ContentItem, ...]


@dataclass(frozen=True)
class BlockDefinition:
    name: str
    path: Path
    renderable: bool
    default_variant: str | None
    variants: tuple[str, ...]
    requires: tuple[str, ...]
    options: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass(frozen=True)
class BuildResult:
    html: str
    blocks: tuple[str, ...]
    assets: tuple[str, ...]

