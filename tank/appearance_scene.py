"""Apply appearance to existing Panda nodes; clock ticks never rebuild the tank."""
from datetime import datetime, timezone
import math
import time
from panda3d.core import GeomVertexRewriter, TextureStage
from .appearance import EnvironmentReader, colour, evaluate, scene_scale


class AppearanceScene:
    def __init__(self, app):
        self.app = app
        self.environment = EnvironmentReader(getattr(app.args, 'environment_file', None))
        self.preview = None
        self.status = ''
        self.last_log = None
        self.next_environment = 0.
        self.applied = None
        self.background = None
        self.weight = None
        self.caustic_phase = 0.
        self.plant_phase = 0.

    def bind(self):
        """Called only after geometry replacement, not during normal updates."""
        self.applied = self.background = None
        self.update(0, force=True)

    def update(self, dt, *, now=None, force=False):
        a = self.app
        p = a.settings.appearance
        mono = time.monotonic()
        if mono >= self.next_environment or force:
            self.environment.read()
            self.next_environment = mono+1
        target, status = evaluate(p, now or datetime.now(timezone.utc), self.environment.value, self.preview)
        # Realtime clock selects the phase; monotonic frame elapsed time blends
        # clock corrections, DST jumps and a recovered HA sun without flashes.
        if self.weight is None or force or self.preview is not None:
            self.weight = target
        else:
            self.weight += (target-self.weight)*(1-math.exp(-max(0, dt)/2))
        self.status = status
        # Log source/fallback transitions, not every clock-minute change.
        diagnostic = status.split('Clock ')[0] if 'Clock ' in status else status
        if diagnostic != self.last_log:
            print('Appearance: '+status, flush=True)
            self.last_log = diagnostic
        scale = scene_scale(p, self.weight)
        state = (tuple(vars(p).items()), scale, a.settings.lighting, a.settings.caustics)
        if state != self.applied:
            a.scene.setColorScale(*scale, 1)
            a.render.clearLight()
            for node, base, strength in ((a.ambient, (.63,.71,.73), p.ambient_strength),
                                         (a.sun, (.95,.95,.82), p.surface_strength),
                                         (a.fill, (.15,.30,.34), p.fill_strength)):
                node.node().setColor(tuple(v*strength for v in base)+(1,))
                if a.settings.lighting:a.render.setLight(node)
            a.sun.setHpr(p.surface_heading, -p.surface_elevation, 0)
            fog = (.028,.15,.19) if p.fog_colour == 'classic' else colour(p.fog_colour)
            a.water_fog.setColor(*(fog[i]*scale[i] for i in range(3)))
            a.water_fog.setExpDensity(p.fog_density)
            a.render.setFog(a.water_fog) if p.fog_enabled else a.render.clearFog()
            clear = tuple(v*scale[i] for i,v in enumerate((.012,.075,.115)))+(1,)
            a.setBackgroundColor(*clear)
            for view in a.views:
                if view.buffer:view.buffer.setClearColor(clear)
            self.set_background(p)
            sand = a.decor.find('**/rippling-sand')
            if not sand.isEmpty():sand.setColorScale(*colour(p.sand_tint),1)
            for cap in a.shelves.root.findAllMatches('**/shelf-sand'):
                cap.setColorScale(*colour(p.sand_tint),1)
            if a.caustic:a.caustic.setColorScale(1,1,1,p.caustics_strength)
            shafts = a.settings.caustics if p.shafts == 'preset' else p.shafts == 'on'
            for ray in a.light_shafts:
                ray.show() if shafts else ray.hide()
                ray.setColorScale(1,1,1,p.shafts_strength)
            self.applied = state
        self.caustic_phase += dt*p.caustics_speed
        self.plant_phase += dt*p.plant_speed
        if a.caustic:
            a.caustic.setTexOffset(TextureStage.getDefault(), self.caustic_phase*.009, self.caustic_phase*.006)
        for node, phase in a.plants:
            node.setR(math.sin(self.plant_phase*.45+phase)*3*p.plant_sway)

    def set_background(self, p):
        if p.background_style == 'classic':
            bottom, top = (.015,.065,.10), (.06,.28,.33)
        else:
            top = colour(p.background_top)
            bottom = top if p.background_style == 'solid' else colour(p.background_bottom)
        key = (bottom, top)
        if key != self.background:
            data = self.app.background.node().modifyGeom(0).modifyVertexData()
            writer = GeomVertexRewriter(data, 'color')
            for value in (bottom,bottom,top,top):writer.setData4(*value,1)
            self.background = key

    def apply_settings(self, settings):
        a = self.app
        previous = a.settings
        # Persist the validated snapshot first; a failed save leaves the display intact.
        settings.save(a.args.settings)
        a.settings = settings
        geometry = any(getattr(previous,k) != getattr(settings,k) for k in ('detail','plants','bubbles','caustics'))
        if geometry:a.rebuild_scene()
        else:
            if previous.fish_style != settings.fish_style:a.restyle_fish()
            from panda3d.core import ClockObject
            ClockObject.getGlobalClock().setFrameRate(settings.fps)
            if previous.scale != settings.scale:a.setup_output()
            self.update(0,force=True)
        a.columns.configure()
        return previous.vsync != settings.vsync
