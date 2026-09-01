---
name: generate-block-reference
description: Creates or refreshes WhalePage's block reference and visual example page. Use when documenting the available page blocks or after changing a block, variant or option.
---

# Generate Block Reference

Create `examples/block-reference.md`, unless the user requests a different path.

1. Run `python -m whalepage blocks` to list the current renderable blocks and variants.
2. Inspect each block's `block.toml`, templates and styles, consulting existing examples for realistic content. Do not document support blocks as if they can be used directly in page Markdown.
3. Write a self-contained reference page that:
   - explains the page Markdown syntax and each renderable block;
   - documents available variants and options;
   - includes a rendered demonstration of every variant, naming the variant explicitly even when it is the default;
   - uses ordinary Markdown outside directives to demonstrate the `prose` block;
   - gives every explicit block a unique `id`.
4. Run `python .claude/skills/generate-block-reference/scripts/check_block_reference.py <source>`.
5. If the script reports missing variants or invalid page Markdown, fix only the reference page and run it again. Stop when it passes or when the failure requires a change outside the reference page.
6. Build the finished reference with `python -m whalepage build <source> --output dist/block-reference.html`.

The bundled script checks coverage against the current block registry and builds the page in memory. Run it directly; read or modify its source only when asked to change or investigate the validator itself.
