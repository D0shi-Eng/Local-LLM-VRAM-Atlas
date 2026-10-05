"""Runtime knowledge base: compatibility facts from official docs, never executed."""

from atlas.runtimes.knowledge import (
    SUPPORT_STATUSES,
    RuntimeCapability,
    get_capability,
    list_capabilities,
)

__all__ = [
    "RuntimeCapability",
    "SUPPORT_STATUSES",
    "get_capability",
    "list_capabilities",
]
