import argparse
import sys
from pathlib import Path

from whalepage.blocks import BlockRegistry
from whalepage.builder import PageBuilder, default_blocks_dir
from whalepage.errors import WhalePageError
from whalepage.parser import parse_document


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="whalepage", description="Build a single static HTML page from Markdown"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="build an HTML page")
    build.add_argument("source", type=Path)
    build.add_argument("--output", "-o", type=Path, default=Path("dist/index.html"))
    build.add_argument("--blocks-dir", type=Path, default=default_blocks_dir())

    check = subparsers.add_parser("check", help="validate a page without writing it")
    check.add_argument("source", type=Path)
    check.add_argument("--blocks-dir", type=Path, default=default_blocks_dir())

    blocks = subparsers.add_parser("blocks", help="list installed page blocks")
    blocks.add_argument("--blocks-dir", type=Path, default=default_blocks_dir())
    return parser


def _load(source: Path):
    try:
        text = source.read_text(encoding="utf-8")
    except OSError as exc:
        raise WhalePageError(f"Cannot read {source}: {exc}") from exc
    return parse_document(text, source.resolve())


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "blocks":
            registry = BlockRegistry(args.blocks_dir)
            for block in registry.renderable():
                variants = ", ".join(block.variants)
                print(f"{block.name}: {variants}")
            return 0

        document = _load(args.source)
        result = PageBuilder(args.blocks_dir).build(document)
        if args.command == "check":
            print(
                f"OK: {args.source} ({len(result.blocks)} blocks, "
                f"{len(result.assets)} asset bundles)"
            )
            return 0

        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result.html, encoding="utf-8")
        print(f"Built {args.output} from {len(result.blocks)} blocks")
        return 0
    except WhalePageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
