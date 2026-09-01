from collections.abc import Callable, Sequence

from markdown_it import MarkdownIt
from markdown_it.token import Token
from markupsafe import Markup

from whalepage.models import Action, BlockContent, ContentItem, Image


ImageResolver = Callable[[str], str]


class ContentParser:
    """Turn Markdown tokens into the small set of slots used by page blocks."""

    def __init__(self) -> None:
        self.markdown = MarkdownIt("commonmark", {"html": False, "linkify": False})

    def parse(self, source: str, resolve_image: ImageResolver) -> BlockContent:
        groups = self._top_level_groups(self.markdown.parse(source))
        root_groups: list[list[Token]] = []
        item_groups: list[tuple[list[Token], list[list[Token]]]] = []
        current_item: tuple[list[Token], list[list[Token]]] | None = None

        for group in groups:
            heading = self._heading(group)
            if heading and heading[0] == 3:
                current_item = (group, [])
                item_groups.append(current_item)
            elif current_item is None:
                root_groups.append(group)
            else:
                current_item[1].append(group)

        heading, heading_html, body_html, image, actions = self._slots(
            root_groups, resolve_image
        )
        items: list[ContentItem] = []
        for item_heading, body_groups in item_groups:
            heading_info = self._heading(item_heading)
            assert heading_info is not None
            _, title = heading_info
            _, _, item_body, item_image, item_actions = self._slots(
                body_groups, resolve_image, extract_heading=False
            )
            items.append(
                ContentItem(
                    title=title,
                    title_html=Markup(self._render(item_heading)),
                    body_html=item_body,
                    image=item_image,
                    actions=item_actions,
                )
            )

        return BlockContent(
            heading=heading,
            heading_html=heading_html,
            body_html=body_html,
            image=image,
            actions=actions,
            items=tuple(items),
        )

    def _slots(
        self,
        groups: list[list[Token]],
        resolve_image: ImageResolver,
        *,
        extract_heading: bool = True,
    ) -> tuple[str | None, Markup, Markup, Image | None, tuple[Action, ...]]:
        remaining = list(groups)
        heading: str | None = None
        heading_html = Markup("")
        image: Image | None = None
        actions: tuple[Action, ...] = ()

        if extract_heading:
            for index, group in enumerate(remaining):
                info = self._heading(group)
                if info and info[0] in (1, 2):
                    heading = info[1]
                    heading_html = Markup(self._render(group))
                    remaining.pop(index)
                    break

        for index, group in enumerate(remaining):
            candidate = self._standalone_image(group)
            if candidate:
                image = Image(
                    src=resolve_image(candidate.src),
                    alt=candidate.alt,
                    title=candidate.title,
                )
                remaining.pop(index)
                break

        for index in range(len(remaining) - 1, -1, -1):
            candidate = self._action_list(remaining[index])
            if candidate:
                actions = candidate
                remaining.pop(index)
                break

        return (
            heading,
            heading_html,
            Markup(self._render_many(remaining)),
            image,
            actions,
        )

    @staticmethod
    def _top_level_groups(tokens: Sequence[Token]) -> list[list[Token]]:
        groups: list[list[Token]] = []
        current: list[Token] = []
        depth = 0
        for token in tokens:
            current.append(token)
            depth += token.nesting
            if depth == 0:
                groups.append(current)
                current = []
        if current:
            groups.append(current)
        return groups

    @staticmethod
    def _heading(group: Sequence[Token]) -> tuple[int, str] | None:
        if not group or group[0].type != "heading_open":
            return None
        level = int(group[0].tag[1:])
        inline = next((token for token in group if token.type == "inline"), None)
        return level, inline.content.strip() if inline else ""

    @staticmethod
    def _standalone_image(group: Sequence[Token]) -> Image | None:
        if len(group) != 3 or group[0].type != "paragraph_open":
            return None
        inline = group[1]
        if inline.type != "inline" or not inline.children:
            return None
        children = [
            token
            for token in inline.children
            if not (token.type == "text" and not token.content.strip())
        ]
        if len(children) != 1 or children[0].type != "image":
            return None
        token = children[0]
        return Image(
            src=token.attrGet("src") or "",
            alt=token.content,
            title=token.attrGet("title"),
        )

    @staticmethod
    def _action_list(group: Sequence[Token]) -> tuple[Action, ...]:
        if not group or group[0].type != "bullet_list_open":
            return ()
        inline_tokens = [token for token in group if token.type == "inline"]
        item_count = sum(token.type == "list_item_open" for token in group)
        if len(inline_tokens) != item_count:
            return ()

        actions: list[Action] = []
        for inline in inline_tokens:
            children = inline.children or []
            if len(children) < 3:
                return ()
            if children[0].type != "link_open" or children[-1].type != "link_close":
                return ()
            label_tokens = children[1:-1]
            if any(token.type not in {"text", "code_inline", "strong_open", "strong_close", "em_open", "em_close"} for token in label_tokens):
                return ()
            label = "".join(
                token.content
                for token in label_tokens
                if token.type in {"text", "code_inline"}
            ).strip()
            href = children[0].attrGet("href") or ""
            if not label or not href:
                return ()
            actions.append(Action(label, href, children[0].attrGet("title")))
        return tuple(actions)

    def _render(self, tokens: Sequence[Token]) -> str:
        return self.markdown.renderer.render(tokens, self.markdown.options, {})

    def _render_many(self, groups: Sequence[Sequence[Token]]) -> str:
        return self._render([token for group in groups for token in group])
