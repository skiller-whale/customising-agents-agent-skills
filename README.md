# WhalePage

WhalePage is a small Python CLI that turns one Markdown file into one
self-contained static HTML page. The Python engine does not know whether it is
building a portfolio, product page, music release or something else. Markdown
supplies the content, and reusable block bundles supply the HTML, CSS and
JavaScript.

## Set up

```console
python -m pip install -r requirements.txt
```

## Build a page

```console
python -m whalepage build examples/portfolio.md
```

The generated page is written to `dist/index.html`. Local images are embedded as
data URLs, and block styles and scripts are inlined, so the result can be opened
or shared as a single file.

The examples demonstrate different uses of the same engine and blocks:

```console
python -m whalepage build examples/portfolio.md --output dist/portfolio.html
python -m whalepage build examples/shop.md --output dist/shop.html
python -m whalepage build examples/music.md --output dist/music.html
```

Other useful commands:

```console
python -m whalepage check examples/shop.md
python -m whalepage blocks
python -m pytest
```

## Page Markdown

A page starts with YAML frontmatter. Standard Markdown outside a directive is
rendered as a `prose` block. Named blocks use top-level `:::` directives:

```markdown
---
title: Northstar Field Supply
description: Durable equipment for weekends outside
---

::: hero variant=centered id=home
# Take the long way home

Field-tested equipment for walking, camping and making coffee outdoors.

- [Shop the collection](#new-arrivals)
- [Read our field notes](#journal)
:::
```

Blocks cannot be nested. Within a block:

- the first H1 or H2 is the block heading;
- a standalone image supplies the block's main image;
- a bullet list containing only links supplies action buttons;
- H3 headings start repeated items, such as cards, tracks or timeline entries.

Run `python -m whalepage blocks` to list the installed blocks and variants.

## Block bundles

Every directory under `blocks/` with a `block.toml` file is discovered
automatically. Renderable blocks contain one template per variant:

```text
blocks/hero/
├── block.toml
├── styles.css
└── variants/
    ├── centered.html
    └── split.html
```

The built-in renderable blocks are `hero`, `prose`, `collection`, `timeline`,
`cta` and `footer`. Their names describe layout and structure rather than a
particular kind of website.

Support blocks such as `button`, `card` and `container` are not used directly in
Markdown. Other blocks depend on them to reuse Jinja macros, CSS and JavaScript.
The builder resolves dependencies and includes every asset bundle once.
