import argparse
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPOSITORY_ROOT))

from whalepage.blocks import BlockRegistry  # noqa: E402
from whalepage.builder import PageBuilder, default_blocks_dir  # noqa: E402
from whalepage.errors import WhalePageError  # noqa: E402
from whalepage.parser import parse_document  # noqa: E402


def check_reference(source: Path, blocks_dir: Path) -> list[tuple[str, str]]:
    text = source.read_text(encoding="utf-8")
    document = parse_document(text, source.resolve())
    registry = BlockRegistry(blocks_dir)

    expected = {
        (block.name, variant)
        for block in registry.renderable()
        for variant in block.variants
    }
    demonstrated: set[tuple[str, str]] = set()
    for page_block in document.blocks:
        block = registry.get(page_block.kind)
        variant = registry.select_variant(block, page_block.variant)
        demonstrated.add((block.name, variant))

    PageBuilder(blocks_dir).build(document)
    return sorted(expected - demonstrated)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check that a WhalePage reference demonstrates every block variant"
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("--blocks-dir", type=Path, default=default_blocks_dir())
    args = parser.parse_args(argv)

    try:
        missing = check_reference(args.source, args.blocks_dir)
    except (OSError, WhalePageError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if missing:
        print("Missing block variants:", file=sys.stderr)
        for block, variant in missing:
            print(f"  {block}/{variant}", file=sys.stderr)
        return 1

    registry = BlockRegistry(args.blocks_dir)
    variant_count = sum(len(block.variants) for block in registry.renderable())
    print(f"OK: {args.source} demonstrates all {variant_count} block variants")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
