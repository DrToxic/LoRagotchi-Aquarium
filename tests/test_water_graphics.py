from dataclasses import replace
from types import SimpleNamespace
import math
from tank.art import fish_model, expressed_colour
from tank.water_art import animate_water

def snap(species=0,stage=2,**kw):
    return SimpleNamespace(owner='a'*64,stage=stage,body=0,scales=4,eyes=2,tint=65535,kind='snapshot',species_id=species,**kw)

def test_all_models_stages_and_low_detail():
    for stage in range(4):
        for species in range(14):
            model,tail,fins=fish_model(snap(species,stage),8)
            assert not model.isEmpty() and not tail.isEmpty()
            assert model.findAllMatches('**/+GeomNode').getNumPaths()>0
            if species:
                before=[tuple(n.getHpr()) for n in fins]
                animate_water(model,tail,fins,1.2,1.)
                assert any(tuple(n.getHpr())!=p for n,p in zip(fins,before))
                assert all(math.isfinite(v) for n in fins for v in n.getHpr())
            model.removeNode()

def test_fallback_and_genes():
    a=fish_model(snap(0),8)[0];b=fish_model(snap(65000),8)[0]
    assert a.getName()==b.getName() and not b.hasTag('water-species')
    assert expressed_colour(snap(body_gene=8),'body')==(1.,0.,0.)
    assert expressed_colour(snap(body_gene=88),'body')==(0.,1.,0.)
    assert expressed_colour(snap(body_gene=255),'body')==expressed_colour(snap(),'body')
    a.removeNode();b.removeNode()

def test_juvenile_neutral_eyes_and_replacement():
    for species in range(1,14):
        a=fish_model(snap(species,0,eyes_gene=8),8)[0]
        b=fish_model(snap(species,0,eyes_gene=168),8)[0]
        # Flattened geometry must have the same vertex colours for eye changes.
        def colours(node):
            from panda3d.core import GeomVertexReader
            result=[]
            for path in node.findAllMatches('**/+GeomNode'):
                gn=path.node()
                for g in range(gn.getNumGeoms()):
                    rd=GeomVertexReader(gn.getGeom(g).getVertexData(),'color')
                    while not rd.isAtEnd(): result.append(tuple(rd.getData4()))
            return result
        assert colours(a)==colours(b)
        a.removeNode();b.removeNode()

def test_panel_tints_use_received_rgb565_without_replacing_coloured_genes():
    from tank.art import tint565
    # Firmware P1 is descriptive; the COMMIT tint already encodes its lower
    # panel colour. A colour-capable peer must still express inherited H1.
    for panel,tint in ((0,0x03b0),(1,0xffff),(2,0x03b0)):
        s=snap(panel=panel,body_gene=6)
        s.tint=tint
        assert expressed_colour(s,'body')==tint565(tint)
        s.body_gene=88
        assert expressed_colour(s,'body')==(0.,1.,0.)
    # Unknown/absent P1 must not invent a replacement tint.
    s=snap(panel=None,body_gene=6);s.tint=0x1234
    assert expressed_colour(s,'body')==tint565(0x1234)

def test_floor_preferences_and_refresh_keep_state():
    from tank.demo import visitors
    from tank.simulation import Simulation
    source=next(iter(visitors(1)))
    fish=replace(source,species_id=9)
    sim=Simulation(reefs=False);sim.roster([fish]);s=sim.swimmers[fish.owner]
    assert s.species_id==9
    # Explicit sampled options have equal distance/occupancy; lower wins.
    original=sim.volume.candidate
    sim.volume.candidate=lambda rng,radius,cell=None,outline=None: (float(cell[0]),0.,2.+cell[1]*3.)
    sim.volume.path_clear=lambda *args:True
    sim.physics.clear_at=lambda *args,**kwargs:True
    s.x,s.y,s.z=0,0,8
    sim._choose_goal(s);assert s.goal[2]==2.
    sim.volume.candidate=original
    old=s;sim.roster([replace(fish,name='new')]);assert sim.swimmers[fish.owner] is old
    sim.roster([replace(fish,species_id=11)]);assert sim.swimmers[fish.owner] is old and old.species_id==11

def test_cetacean_and_jelly_motion_differ():
    for species in (3,4,5):
        model,tail,fins=fish_model(snap(species),10)
        animate_water(model,tail,fins,1.,1.)
        assert abs(tail.getP())>1 and abs(tail.getH())<.01
        model.removeNode()
    model,tail,fins=fish_model(snap(11),10)
    bell=model.find('**/static-water-geometry')
    animate_water(model,tail,fins,0.,1.);a=tuple(bell.getScale())
    animate_water(model,tail,fins,2.,1.);b=tuple(bell.getScale())
    assert a!=b and tuple(model.getScale())==(1.,1.,1.)
    model.removeNode()

def test_mixed_species_movement_is_bounded_and_population_retained():
    from tank.demo import visitors
    from tank.simulation import Simulation
    fish=[replace(f,species_id=i%14) for i,f in enumerate(visitors(56))]
    sim=Simulation(reefs=False);sim.roster(fish)
    before=sim.step(0)
    for _ in range(90):
        after=sim.step(1/30)
        assert len(after)==56
        for owner,p in after.items():
            old=before[owner]
            assert math.dist((p.x,p.y,p.z),(old.x,old.y,old.z))<.2
            assert all(math.isfinite(v) for v in (p.x,p.y,p.z,p.heading,p.phase,p.speed))
        before=after
    assert len({round(s.phase,2) for s in sim.swimmers.values()})>40
