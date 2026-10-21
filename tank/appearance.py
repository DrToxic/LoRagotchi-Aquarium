"""Portable, data-only appearance settings and wall-clock lighting evaluation."""
from dataclasses import dataclass, fields
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def colour(value):
    if not isinstance(value, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', value):
        raise ValueError('Use a colour in #RRGGBB format')
    return tuple(int(value[i:i+2], 16)/255 for i in (1, 3, 5))


def minutes(value):
    if not isinstance(value, str) or not re.fullmatch(r'(?:[01][0-9]|2[0-3]):[0-5][0-9]', value):
        raise ValueError('Use a 24-hour time HH:MM')
    h, m = map(int, value.split(':'))
    return h*60+m


def timezone_valid(value):
    if not isinstance(value, str) or len(value) > 100:
        raise ValueError('Use local, ha, or an IANA timezone such as Europe/London')
    if value not in ('local', 'ha'):
        try: ZoneInfo(value)
        except (ValueError, ZoneInfoNotFoundError):
            raise ValueError('Unknown IANA timezone') from None
    return value


@dataclass
class Appearance:
    mode: str = 'static'
    timezone: str = 'local'
    day_start: str = '07:00'
    night_start: str = '19:00'
    transition_minutes: float = 60.
    brightness: float = 1.
    day_brightness: float = 1.
    night_brightness: float = .2
    day_colour: str = '#ffffff'
    night_colour: str = '#709acb'
    ambient_strength: float = 1.
    surface_strength: float = 1.
    fill_strength: float = 1.
    surface_heading: float = -35.
    surface_elevation: float = 65.
    background_style: str = 'classic'
    background_top: str = '#0f4754'
    background_bottom: str = '#04111a'
    fog_enabled: bool = True
    fog_colour: str = 'classic'
    fog_density: float = .012
    sand_tint: str = '#ffffff'
    caustics_strength: float = 1.
    caustics_speed: float = 1.
    shafts: str = 'preset'
    shafts_strength: float = 1.
    plant_sway: float = 1.
    plant_speed: float = 1.
    column_count: int = 0
    column_placement: str = 'mixed'
    column_seed: int = 17
    column_particles: int = 60
    column_width: float = .2
    column_size: float = 1.
    column_speed: float = 1.

    @classmethod
    def from_dict(cls, raw, *, strict=True, warnings=None):
        if not isinstance(raw, dict):
            if strict: raise ValueError('Appearance must be an object')
            if warnings is not None: warnings.append('Invalid appearance object; using Classic')
            return cls()
        result = cls()
        known = {f.name for f in fields(cls)}
        result._extra = {k: v for k, v in raw.items() if k not in known}
        if strict and result._extra:
            raise ValueError('Unknown appearance setting: '+next(iter(result._extra)))
        for key in known & raw.keys():
            try:
                value = validate(key, raw[key])
                setattr(result, key, value)
            except ValueError as exc:
                if strict: raise ValueError(f'{key}: {exc}') from None
                if warnings is not None: warnings.append(f'{key}: {exc}; default retained')
        if result.day_start == result.night_start:
            if strict: raise ValueError('Day and night must start at different times')
            result.day_start, result.night_start = '07:00', '19:00'
            if warnings is not None: warnings.append('Equal day/night times; restored 07:00 / 19:00')
        return result


CHOICES = {
    'mode': ('static', 'clock', 'ha_sun'),
    'background_style': ('classic', 'solid', 'gradient'),
    'shafts': ('preset', 'on', 'off'),
    'column_placement': ('floor', 'shelves', 'mixed'),
}
RANGES = {
    'transition_minutes': (0, 180), 'brightness': (0, 2),
    'day_brightness': (0, 2), 'night_brightness': (0, 2),
    'ambient_strength': (0, 2), 'surface_strength': (0, 2), 'fill_strength': (0, 2),
    'surface_heading': (-180, 180), 'surface_elevation': (0, 90),
    'fog_density': (0, .1), 'caustics_strength': (0, 2), 'caustics_speed': (0, 3),
    'shafts_strength': (0, 2), 'plant_sway': (0, 3), 'plant_speed': (0, 3),
    'column_count': (0, 16), 'column_seed': (0, 2147483647),
    'column_particles': (1, 300), 'column_width': (.05, .8),
    'column_size': (.25, 3), 'column_speed': (.1, 3),
}
INTEGERS = {'column_count', 'column_seed', 'column_particles'}


def validate(key, value):
    if key in CHOICES:
        if value not in CHOICES[key]: raise ValueError('Choose '+', '.join(CHOICES[key]))
    elif key in RANGES:
        low, high = RANGES[key]
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f'Must be a finite number from {low} to {high}')
        if key in INTEGERS and type(value) is not int: raise ValueError('Must be an integer')
    elif key == 'fog_enabled':
        if not isinstance(value, bool): raise ValueError('Must be true or false')
    elif key == 'timezone': timezone_valid(value)
    elif key in ('day_start', 'night_start'): minutes(value)
    elif key == 'fog_colour' and value == 'classic': pass
    else: colour(value)
    return value


def smooth(value):
    x = max(0., min(1., value))
    return x*x*(3-2*x)


def clock_weight(settings, local_time):
    """Ramps begin at each configured time, including schedules across midnight."""
    day, night = minutes(settings.day_start), minutes(settings.night_start)
    day_length = (night-day) % 1440
    ramp = min(settings.transition_minutes, day_length, 1440-day_length)
    phase = (local_time.hour*60+local_time.minute+local_time.second/60-day) % 1440
    if not ramp: return float(phase < day_length)
    return smooth(phase/ramp) if phase < day_length else 1-smooth((phase-day_length)/ramp)


def evaluate(settings, now=None, environment=None, preview=None):
    """Return daylight fraction and diagnostics; no network, Panda or mutable clocks."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None: raise ValueError('A timezone-aware time is required')
    env = environment or {}
    if preview is not None:
        return float(preview), 'Day preview' if preview else 'Night preview'
    if settings.mode == 'static': return 1., 'Static lighting'
    note = ''
    if settings.mode == 'ha_sun':
        observed, elevation = env.get('observed_at'), env.get('elevation')
        if (env.get('online') is True and type(observed) in (int, float)
                and math.isfinite(observed) and -5 <= now.timestamp()-observed <= 120
                and type(elevation) in (int, float) and math.isfinite(elevation)
                and -90 <= elevation <= 90):
            return smooth((elevation+6)/12), 'Home Assistant sun'
        note = 'HA sun unavailable; clock fallback · '
    zone = settings.timezone
    if zone == 'ha':
        zone = env.get('timezone')
        try:
            if zone in (None, 'local', 'ha'): raise ValueError()
            timezone_valid(zone)
        except ValueError:
            zone = 'UTC'
            note += 'HA timezone unavailable; UTC · '
    local = now.astimezone() if zone == 'local' else now.astimezone(ZoneInfo(zone))
    return clock_weight(settings, local), note+f'Clock {local:%H:%M %Z}'


def scene_scale(settings, weight):
    day, night = colour(settings.day_colour), colour(settings.night_colour)
    brightness = settings.brightness*(settings.night_brightness+(settings.day_brightness-settings.night_brightness)*weight)
    return tuple(brightness*(night[i]+(day[i]-night[i])*weight) for i in range(3))


class EnvironmentReader:
    """Tiny local observer snapshot. Retain timezone, never extend stale sun data."""
    def __init__(self, path=None):
        self.path = Path(path) if path else None
        self.value = {}

    def read(self):
        if self.path:
            try:
                with self.path.open() as stream: raw = stream.read(4097)
                if len(raw) > 4096: raise ValueError('Oversized environment snapshot')
                value = json.loads(raw)
                if not isinstance(value, dict): raise ValueError('Invalid environment snapshot')
                self.value = value
            except (OSError, ValueError):
                self.value = {**self.value, 'online': False}
        return self.value
