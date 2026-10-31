"""Package-manager backends and the resolver that picks one per package."""
from .base import PackageManager, Source
from .registry import managers_for, resolve

__all__ = ["PackageManager", "Source", "managers_for", "resolve"]
