from dataclasses import asdict,replace
from types import SimpleNamespace
import math
import pytest
from panda3d.core import NodePath
from tank.appearance import Appearance
from tank.bubble_physics import BubbleObstacles,object_origins
from tank.collision import CollisionWorld
from tank.demo import visitors
from tank.nursery import NurseryStore,NurserySettings,preview_colour
from tank.settings import Settings
from tank.simulation import Simulation


def adults():return [replace(f,stage=2) for f in list(visitors(3))]


def test_swept_bubble_hits_thin_plate_and_rebuilds_only_on_change():
    physics=CollisionWorld(False)
    physics.replace_boxes('plate',[((0,0,3),(4,4,.04),(0,0,0))])
    bubbles=BubbleObstacles(physics)
    point=bubbles.move((0,0,2),(0,0,4))
    assert point[2]<3 and point[0]>0
    assert bubbles.contacts==1 and bubbles.builds==1
    for _ in range(10):bubbles.move((5,0,2),(5,0,4))
    assert bubbles.builds==1 and len(bubbles.nodes)==1
    physics.replace_boxes('plate',[])
    assert bubbles.move((0,0,2),(0,0,4))==(0,0,4)
    assert bubbles.builds==2 and not bubbles.nodes
    physics.add('fish',2,(0,0,3),0)
    assert bubbles.move((0,0,2),(0,0,4))==(0,0,4)


def test_object_emitters_follow_visibility_and_relocation():
    r=SimpleNamespace(enabled=True,visible=True,position=(4,2,1),bubble_origins=(('hole',(0,0,2)),))
    app=SimpleNamespace(placement=SimpleNamespace(records={'object':r}))
    assert object_origins(app)==[('object:hole',4,2,3)]
    r.position=(8,2,4)
    assert object_origins(app)==[('object:hole',8,2,6)]
    r.visible=False;assert not object_origins(app)
    r.visible=True;r.enabled=False;assert not object_origins(app)


def test_activity_independence_refresh_and_off():
    sim=Simulation(False);fish=list(visitors(24));sim.roster(fish)
    sim.set_activity('lively',[('bubble',(0,0,4)),('object',(4,1,5))])
    observed=set();states=list(sim.swimmers.values())
    for s in states:s.activity_wait=0
    for _ in range(150):
        poses=sim.step(1/30)
        observed.update(s.activity for s in sim.swimmers.values())
        assert all(math.isfinite(p.x+p.y+p.z+p.speed) for p in poses.values())
    assert len(observed)>=4
    sim.roster([replace(fish[0],name='new'),*fish[1:]])
    assert all(a is b for a,b in zip(states,sim.swimmers.values()))
    sim.set_activity('off');sim.step(0)
    assert all(s.activity=='cruise' and s.pace_factor==1 for s in states)


def test_nursery_transaction_capacity_restart_and_immutable_portraits(tmp_path):
    a,b,c=adults();settings=NurserySettings(True,False,2,30)
    path=tmp_path/'nursery.db';store=NurseryStore(path,'live')
    ident=store.create(a,b,settings,now=100,egg_id='a'*32)
    egg=store.eggs()[0]
    assert egg['preview']['firmware_genome'] is None
    assert len(egg['parents'])==2
    store.close();store=NurseryStore(path,'live')
    assert store.eggs()==[egg]
    assert store.create(a,b,settings,now=101,egg_id=ident)==ident
    with pytest.raises(ValueError,match='resting'):store.create(a,c,settings,now=110)
    with pytest.raises(ValueError,match='different parents'):store.create(a,c,settings,now=110,egg_id=ident)
    store.create(a,c,settings,now=2000)
    with pytest.raises(ValueError,match='full'):store.create(b,c,settings,now=5000)
    assert store.eggs()[0]==egg
    store.close()
    other=NurseryStore(path,'demo');assert not other.eggs();other.close()


def test_nursery_parallel_capacity_and_colour_rule(tmp_path):
    a,b,c=adults();p=tmp_path/'eggs.db';s=NurseryStore(p,'x');other=NurseryStore(p,'x')
    settings=NurserySettings(True,False,1,1)
    s.create(a,b,settings)
    with pytest.raises(ValueError,match='full'):other.create(b,c,settings)
    assert len(s.eggs())==1
    p1=asdict(replace(a,body=6,tint=0xf800));p2=asdict(replace(b,body=6,tint=0x001f))
    previews=[preview_colour(p1,p2,str(i)) for i in range(20)]
    assert len({p['fraction'] for p in previews})==20
    assert all(0<p['body_rgb'][0]<1 and p['body_rgb'][1]==0 and 0<p['body_rgb'][2]<1 for p in previews)
    s.close();other.close()


@pytest.mark.parametrize('raw',[{'capacity':0},{'capacity':True},{'automatic':1},{'cooldown_minutes':0}])
def test_invalid_nursery_settings(raw):
    with pytest.raises(ValueError):NurserySettings.from_dict(raw)


def test_living_settings_roundtrip_and_bad_values(tmp_path):
    s=Settings();s.nursery=NurserySettings(True,True,8,10)
    s.appearance=Appearance(column_placement='objects',bubble_collisions=False,background_motion='ripple',fish_activity='lively')
    p=tmp_path/'settings.json';s.save(p);assert Settings.load(p)==s
    for raw in ({'background_speed':float('nan')},{'bubble_collisions':1},{'fish_activity':'wild'}):
        with pytest.raises(ValueError):Appearance.from_dict(raw)


def test_bubble_radius_and_origin_clearance_are_not_point_only():
    physics=CollisionWorld(False)
    physics.replace_boxes('wall',[((0,0,3),(.1,4,4),(0,0,0))])
    bubbles=BubbleObstacles(physics)
    assert not bubbles.clear((.1,0,3),.1)
    assert bubbles.clear((1,0,3),.1)
    small=bubbles.move((1,0,3),(-1,0,3),.05)
    large=bubbles.move((1,0,3),(-1,0,3),.25)
    assert large[0]>small[0]+.1


def test_nursery_worker_restart_and_demo_live_separation(tmp_path):
    from tank.nursery import NurseryWorker
    args=SimpleNamespace(settings=tmp_path/'settings.json',database=tmp_path/'demo.sqlite',session='community')
    a,b,_=adults();config=asdict(NurserySettings(True,False,2,1))
    worker=NurseryWorker(args)
    try:
        assert worker.submit('open',mode='demo')
        assert worker.events.get(timeout=3)['eggs']==[]
        assert worker.submit('create',a=asdict(a),b=asdict(b),settings=config,id='b'*32)
        saved=worker.events.get(timeout=3)['eggs'];assert len(saved)==1
        assert worker.submit('open',mode='live')
        assert worker.events.get(timeout=3)['eggs']==[]
    finally:worker.close()
    worker=NurseryWorker(args)
    try:
        worker.submit('open',mode='demo')
        assert worker.events.get(timeout=3)['eggs']==saved
    finally:worker.close()


def nursery_controller():
    import queue
    from tank.nursery_scene import NurseryScene
    a,b,_=adults();parents=[a,b]
    swimmers={f.owner:SimpleNamespace(x=-5.9+i*2.2,y=-4.4,z=2.65,parked=False,arriving=False,travelling=False,outline=1.75) for i,f in enumerate(parents)}
    commands=[]
    worker=SimpleNamespace(events=queue.Queue(),submit=lambda action,**values:commands.append((action,values)) or True)
    record=SimpleNamespace(enabled=True,visible=True)
    app=SimpleNamespace(settings=Settings(nursery=NurserySettings(True,False,6,30)),roster=parents,scene=None,
        sim=SimpleNamespace(swimmers=swimmers,volume=SimpleNamespace(path_clear=lambda *args:True),time=0),
        placement=SimpleNamespace(records={'nursery:cave':record}))
    scene=NurseryScene.__new__(NurseryScene)
    scene.app=app;scene.worker=worker;scene.pending_request=False;scene.eggs=[];scene.next_attempt=20
    scene.root=SimpleNamespace(getPos=lambda scene:(-4.8,-1.8,.15))
    scene.request_pair(a,b);scene.routes={f.owner:2 for f in parents}
    return scene,parents,commands,record


def test_each_parent_completes_visit_without_needing_synchronised_arrival():
    scene,(a,b),commands,_=nursery_controller()
    sb=scene.app.sim.swimmers[b.owner];sb.y=3.
    for _ in range(7):scene.update(1.)
    assert a.owner in scene.visited and not commands
    scene.app.sim.swimmers[a.owner].y=3.;sb.y=-4.4
    for _ in range(7):scene.update(1.)
    assert len(commands)==1 and commands[0][0]=='create'
    assert scene.pending is None and scene.pending_request
    for _ in range(10):scene.update(1.)
    assert len(commands)==1


@pytest.mark.parametrize('reason',['hidden','disabled','rename','removed'])
def test_unavailable_cave_or_changed_parent_cancels_without_egg(reason):
    scene,(a,b),commands,record=nursery_controller()
    if reason=='hidden':record.visible=False
    if reason=='disabled':scene.app.settings.nursery.enabled=False
    if reason=='rename':scene.app.roster=[replace(a,name='changed'),b]
    if reason=='removed':scene.app.roster=[b]
    scene.update(1.)
    assert scene.pending is None and not commands
