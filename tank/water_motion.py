"""Low-cost background light bands; no shader dependency, no per-frame allocation."""
import math
from panda3d.core import TransparencyAttrib
from .art import mesh


class WaterMotion:
    def __init__(self, parent):
        self.root = parent.attachNewNode('moving-water-light')
        self.root.setLightOff(); self.root.setFogOff()
        self.root.setTransparency(TransparencyAttrib.MAlpha)
        self.root.setDepthWrite(False)
        self.bands = []
        self.phase = 0.
        for i in range(18):
            # Transparent edges prevent hard stripes in the water backdrop.
            verts=[]
            for x,alpha in ((-1,0),(0,.09),(1,0)):
                verts += [((x,0,-14),(0,-1,0),(.22,.58,.64,alpha),(0,0)),
                          ((x,0,14),(0,-1,0),(.22,.58,.64,alpha),(0,1))]
            band=mesh('soft-water-band',verts,[(0,2,1),(1,2,3),(2,4,3),(3,4,5)])
            band.reparentTo(self.root)
            self.bands.append(band)

    def update(self, dt, settings):
        if settings.background_motion == 'off' or not settings.background_strength:
            self.root.hide()
            return
        self.root.show()
        self.phase += max(0.,dt)*settings.background_speed
        for i, band in enumerate(self.bands):
            phase=self.phase*.13+i*1.79
            if settings.background_motion == 'rays':
                band.setPos(-33+i*4+math.sin(phase)*1.6,12.4,10)
                band.setScale(1.4,1,1);band.setR(12+math.sin(phase*.7)*4)
            else:
                band.setPos(0,12.4,-2+i*1.6+math.sin(phase)*.8)
                band.setScale(.5,1,3);band.setR(85+math.sin(phase*.7)*3)
            band.setColorScale(1,1,1,settings.background_strength*(.6+.4*math.sin(phase)**2))
