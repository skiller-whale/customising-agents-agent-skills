class WhalePageError(Exception):
    """A user-facing error while loading or building a page."""


class SourceError(WhalePageError):
    """Invalid page Markdown."""


class BlockError(WhalePageError):
    """Invalid block definition or block usage."""


class BuildError(WhalePageError):
    """A failure while rendering the output page."""
