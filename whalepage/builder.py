import base64
import mimetypes
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

from whalepage.blocks import BlockRegistry
from whalepage.content import ContentParser
from whalepage.errors import BuildError
from whalepage.models import BuildResult, PageDocument


def default_blocks_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "blocks"


class PageBuilder:
    def __init__(self, blocks_dir: Path | None = None) -> None:
        self.blocks_dir = blocks_dir or default_blocks_dir()
        self.registry = BlockRegistry(self.blocks_dir)
        self.content_parser = ContentParser()
        self.templates = Environment(
            loader=FileSystemLoader(self.blocks_dir),
            autoescape=select_autoescape(("html", "xml"), default_for_string=True),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def build(self, document: PageDocument) -> BuildResult:
        rendered: list[str] = []
        block_names: list[str] = []
        used_ids: set[str] = set()

        for page_block in document.blocks:
            definition = self.registry.get(page_block.kind)
            variant = self.registry.select_variant(definition, page_block.variant)
            options = self.registry.normalise_options(definition, page_block.options)
            content = self.content_parser.parse(
                page_block.markdown,
                lambda src: self._resolve_image(src, document.source_path.parent),
            )
            if options.get("id") in used_ids:
                raise BuildError(f"Duplicate block id: {options['id']}")
            options.setdefault("id", self._unique_id(content.heading or page_block.kind, used_ids))
            used_ids.add(options["id"])
            template = self.templates.get_template(
                f"{definition.name}/variants/{variant}.html"
            )
            rendered.append(
                template.render(content=content, options=options, page=document.metadata)
            )
            block_names.append(definition.name)

        assets = self.registry.resolve_dependencies(block_names)
        styles = self._asset_text(self.blocks_dir / "_page" / "styles.css")
        scripts = self._asset_text(self.blocks_dir / "_page" / "script.js")
        for block in assets:
            styles += self._labelled_asset(block.name, block.path / "styles.css", "css")
            scripts += self._labelled_asset(block.name, block.path / "script.js", "js")

        page_template = self.templates.get_template("_page/template.html")
        html = page_template.render(
            page=document.metadata,
            body=Markup("\n".join(rendered)),
            styles=Markup(styles),
            scripts=Markup(scripts),
        )
        return BuildResult(
            html=html,
            blocks=tuple(block_names),
            assets=tuple(block.name for block in assets),
        )

    @staticmethod
    def _unique_id(label: str, used: set[str]) -> str:
        base = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-") or "section"
        candidate = base
        number = 2
        while candidate in used:
            candidate = f"{base}-{number}"
            number += 1
        return candidate

    @staticmethod
    def _asset_text(path: Path) -> str:
        return path.read_text(encoding="utf-8") if path.is_file() else ""

    def _labelled_asset(self, name: str, path: Path, kind: str) -> str:
        content = self._asset_text(path)
        if not content:
            return ""
        if kind == "css":
            return f"\n/* block: {name} */\n{content}\n"
        return f"\n// block: {name}\n{content}\n"

    @staticmethod
    def _resolve_image(src: str, source_dir: Path) -> str:
        parts = urlsplit(src)
        if parts.scheme or src.startswith("//"):
            return src
        if parts.query or parts.fragment:
            raise BuildError(f"Local image paths cannot contain a query or fragment: {src}")

        path = (source_dir / unquote(parts.path)).resolve()
        if not path.is_file():
            raise BuildError(f"Image does not exist: {path}")
        mime_type, _ = mimetypes.guess_type(path.name)
        if not mime_type or not mime_type.startswith("image/"):
            raise BuildError(f"Unsupported image type: {path.name}")
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"
