"""
Sport plugin system.

Import this module to register all available sport plugins.
New sports are added by:
  1. Creating a plugin class implementing :class:`SportPlugin`
  2. Adding a registration line below
"""

from app.sports.registry import SportRegistry
from app.sports.strength.plugin import WeightLiftingPlugin
from app.sports.cycling.plugin import BicycleCommutingPlugin

# Register all built-in plugins
SportRegistry.register(WeightLiftingPlugin())
SportRegistry.register(BicycleCommutingPlugin())

__all__ = ["SportRegistry"]
