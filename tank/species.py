"""Permanent Water registry v1; unknown wire identities are never rewritten."""
LABELS = ("Tropical fish", "Blowfish", "Shark", "Dolphin", "Whale", "Seal",
          "Shrimp", "Squid", "Lobster", "Crab", "Octopus", "Jellyfish",
          "Shell-dweller", "Sea star")


def known(species_id):
    return type(species_id) is int and 0 <= species_id < len(LABELS)


def render_id(species_id):
    return species_id if known(species_id) else 0


def label(species_id):
    return LABELS[species_id] if known(species_id) else "Unknown (fish)"
