"""
Prompt Template Engine - Python Implementation

Expands template syntax in prompts with dynamic values and fragment references.
"""

import re
from datetime import datetime
from typing import Any, Callable

from fragments import FragmentKind, FragmentStore


class TemplateEngine:
    """
    Expands template variables in prompt strings.

    Supported syntax:
    - {fragment:id} - Insert fragment content by ID
    - {kind:type} - Insert all fragments of a kind
    - {user_input} - Insert user's message
    - {date} - Insert current date
    - {var_name} - Insert from context dict
    """

    # Pattern matches {name} or {name:value}
    PATTERN = re.compile(r"\{(\w+)(?::(\w+))?\}")

    def __init__(self, store: FragmentStore):
        self.store = store
        self._custom_handlers: dict[str, Callable[[str | None], str]] = {}

    def register_handler(
        self, name: str, handler: Callable[[str | None], str]
    ) -> None:
        """Register a custom variable handler."""
        self._custom_handlers[name] = handler

    def expand(self, template: str, context: dict[str, Any] | None = None) -> str:
        """
        Expand all template variables in a string.

        Args:
            template: String with {var} placeholders
            context: Dict of variable values

        Returns:
            Expanded string with all placeholders replaced
        """
        context = context or {}

        def replace_match(match: re.Match) -> str:
            name = match.group(1)
            param = match.group(2)

            # Handle built-in variables
            if name == "fragment" and param:
                fragment = self.store.get(param)
                return fragment.content if fragment else f"[missing:{param}]"

            if name == "kind" and param:
                try:
                    kind = FragmentKind(param)
                    fragments = self.store.get_by_kind(kind)
                    return "\n\n".join(f.content for f in fragments)
                except ValueError:
                    return f"[unknown kind:{param}]"

            if name == "date":
                return datetime.now().strftime("%Y-%m-%d")

            if name == "user_input":
                return context.get("user_input", "")

            # Check custom handlers
            if name in self._custom_handlers:
                return self._custom_handlers[name](param)

            # Fall back to context dict
            if name in context:
                return str(context[name])

            # Return original if no match
            return match.group(0)

        return self.PATTERN.sub(replace_match, template)


# Convenience function for simple expansion
def expand_template(
    template: str,
    store: FragmentStore,
    context: dict[str, Any] | None = None,
) -> str:
    """Expand a template string with the given store and context."""
    engine = TemplateEngine(store)
    return engine.expand(template, context)


# Example usage
if __name__ == "__main__":
    from fragments import PromptFragment

    store = FragmentStore()
    store.add(PromptFragment(
        id="greeting",
        kind=FragmentKind.CONTEXT,
        content="Hello! I'm ready to help.",
        order_index=0,
    ))

    engine = TemplateEngine(store)

    # Register custom handler
    engine.register_handler("model", lambda _: "claude-3")

    template = """
{fragment:greeting}

Today is {date}.
Model: {model}

User asked: {user_input}
"""

    result = engine.expand(template, {"user_input": "How do I write tests?"})
    print(result)
