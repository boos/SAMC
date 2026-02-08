"""
Sport plugin registry.

Central registry for all available sport plugins.  Plugins are
registered at import time via :func:`SportRegistry.register`.
The registry provides lookup by ``sport_id`` and enumeration
of all available sports.
"""

from __future__ import annotations

from typing import Optional

from app.sports.base import SportPlugin


class SportRegistry:
    """Singleton registry of available sport plugins."""

    _plugins: dict[str, SportPlugin] = {}

    @classmethod
    def register(cls, plugin: SportPlugin) -> None:
        """Register a sport plugin.

        Raises :class:`ValueError` if ``sport_id`` is already taken.
        """
        if plugin.sport_id in cls._plugins:
            raise ValueError(
                f"Sport '{plugin.sport_id}' already registered"
            )
        cls._plugins[plugin.sport_id] = plugin

    @classmethod
    def get(cls, sport_id: str) -> Optional[SportPlugin]:
        """Get a plugin by *sport_id*.  Returns ``None`` if not found."""
        return cls._plugins.get(sport_id)

    @classmethod
    def get_or_raise(cls, sport_id: str) -> SportPlugin:
        """Get a plugin by *sport_id*.

        Raises :class:`KeyError` if not found.
        """
        plugin = cls._plugins.get(sport_id)
        if not plugin:
            raise KeyError(
                f"Sport '{sport_id}' not registered. "
                f"Available: {list(cls._plugins.keys())}"
            )
        return plugin

    @classmethod
    def all(cls) -> dict[str, SportPlugin]:
        """Return all registered plugins as ``{sport_id: plugin}``."""
        return dict(cls._plugins)

    @classmethod
    def available_sport_ids(cls) -> list[str]:
        """Return sorted list of all registered ``sport_id`` values."""
        return sorted(cls._plugins.keys())

    @classmethod
    def clear(cls) -> None:
        """Remove all plugins.  Useful for testing."""
        cls._plugins.clear()
