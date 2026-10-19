"""Shared visual/physical dimensions. Quality settings never move solid scenery."""
import random

FISH_SCALES = (.48, .72, 1., 1.16)
TANK_LIMITS = ((-22., 22.), (-7., 8.), (.25, 16.))


def reef_rocks(rng=None):
    rng = rng or random.Random(101)
    rocks = []
    for side in (-1, 1):
        for i in range(10):
            x = side*(10+rng.random()*7)
            y = 1+rng.random()*5
            sx, sz = 1+rng.random()*2.3, .6+rng.random()*1.8
            colour = (.18+rng.random()*.06, .27, .25)
            heading = rng.randrange(360)
            rocks.append(((x, y, sz*.6), (sx, sx*.6, sz), heading, colour, i))
    return rocks


def coral_branches():
    for side in (-1, 1):
        for i in range(7):
            for j in range(5):
                yield ((side*(7+i*.6)+(j-2)*.23, -1.5+i*.5, .6+j*.08),
                       (.13, .14, .45+j*.10), (j-2)*17)
