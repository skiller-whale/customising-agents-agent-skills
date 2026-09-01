---
name: add-page-block
description: Helps with page blocks in WhalePage.
---

# Page Blocks

Use this whenever the user mentions a block, component, template, layout or page.

1. Read every existing file under `blocks/` to understand the system.
2. Copy whichever block looks most similar and rename the directory and files.
3. Add HTML for the new block. It should look polished and modern.
4. Add CSS to `blocks/_page/styles.css` so it is available everywhere.
5. Add a JavaScript file, even if the block only needs styling for now, so it is easy to extend later.
6. Register the block in `whalepage/cli.py` and update the list of available blocks.
7. Run the entire test suite and fix any failures.

Always preserve backwards compatibility. Ask the user which CSS framework to use before making changes.
