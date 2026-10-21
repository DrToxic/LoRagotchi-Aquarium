"""Configurable display-copy lifespan, independent of animation preferences."""
from .expiry import validate_hours, remaining_text


class ExpiryPanel:
    def __init__(self, controls, parent):
        self.controls, self.app = controls, controls.app
        controls.label(parent, 'FISH LIFESPAN', 18, 105, 12)
        controls.button(parent, 'Back to aquarium', 18, 145, 396,
                        lambda: controls.page('Aquarium'))
        hours = self.app.settings.fish_lifespan_hours
        controls.label(parent, 'Copies expire', 18, 200)
        self.mode = controls.menu(parent, ['Off', 'After last share'], 205, 200, 195,
                                  lambda _: None, int(hours > 0))
        days = bool(hours and hours % 24 == 0)
        controls.label(parent, 'Lifespan', 18, 248)
        self.amount = controls.entry(parent, f'{hours / 24 if days else hours or 24:g}',
                                     145, 248, 112)
        self.unit = controls.menu(parent, ['Hours', 'Days'], 280, 248, 120,
                                  lambda _: None, int(days))
        controls.button(parent, 'Apply lifespan', 18, 300, 396, self.apply)
        self.note = controls.label(parent, '', 18, 344, 13, 396)
        controls.label(parent,
            'A new share renews the lifespan, even when the fish\nlooks the same. '
            'Restarts and duplicate messages do not.\n\n'
            'Expired copies leave through the selected exit\nanimation. Their saved history is kept.\n\n'
            'Off or a longer lifespan can restore expired copies.\n'
            'Manually removed copies stay hidden until re-shared.\n\n'
            'Original pets and radio returns are unaffected.\n'
            'Maximum: 365 days. Fractions are allowed.', 18, 390, 12, 396)
        self.summary = controls.label(parent, '', 18, 600, 12, 396)

    def apply(self):
        try:
            hours = 0.0
            if self.mode.get() != 'Off':
                hours = validate_hours(float(self.amount.get()) * (24 if self.unit.get() == 'Days' else 1))
                if not hours:
                    raise ValueError('Enter a lifespan above zero, or choose Off')
            # Persist before applying; a failed save must not silently change policy.
            previous = self.app.settings.fish_lifespan_hours
            self.app.settings.fish_lifespan_hours = hours
            try:
                self.app.settings.save(self.app.args.settings)
            except OSError:
                self.app.settings.fish_lifespan_hours = previous
                raise
            self.app.service.commands.put(('lifespan', hours))
            self.note['text'] = 'Expiry off.' if not hours else f'Applied: {hours:g} hours since last share.'
        except (ValueError, OSError) as exc:
            self.note['text'] = str(exc)

    def refresh(self):
        state = self.app.lifespan
        expired = state.get('expired', 0)
        text = f'{len(self.app.roster)} active · {expired} expired copies retained'
        if state.get('undated'):
            text += f"\n{state['undated']} undated copies retained; re-share to start their timer"
        elif self.app.roster:
            fish = self.app.roster[self.app.selected % len(self.app.roster)]
            text += '\n' + remaining_text(state.get('last_shared', {}).get(fish.owner),
                                           state.get('hours', 0))
        self.app.set_ui_text(self.summary, text)
