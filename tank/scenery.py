"""Normal scene selection, independent of lighting themes and quality presets."""
from .art import scenery as classic
from .reef_art import scenery as tidal_garden


def scenery(parent, settings, placement=None):
    provider = {'tidal-garden': tidal_garden, 'classic': classic}[settings.scene]
    return provider(parent, settings, placement)
