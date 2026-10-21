"""Native theme pixels, stable simulation, mesh envelopes and mid-lifecycle restyling."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import sys
import tempfile
import time


def exercise(app):
    from panda3d.core import ClockObject, PNMImage
    from tank.themes import BUILTINS,apply,ThemeLibrary
    from tank.art import fish_model
    from tank.demo import visitors
    from tank.settings import Settings
    out=Path('.local/themes');out.mkdir(parents=True,exist_ok=True)
    end=time.monotonic()+12
    while len(app.roster)!=12 and time.monotonic()<end:app.taskMgr.step()
    assert len(app.roster)==12
    app.taskMgr.remove('aquarium-update');ClockObject.getGlobalClock().setMode(ClockObject.MNormal)
    for _ in range(30):app.update_fish(1/30)
    roster=list(app.roster);swimmers={key:id(v) for key,v in app.sim.swimmers.items()}
    bodies={key:id(v) for key,v in app.sim.collisions.bodies.items()} if hasattr(app.sim,'collisions') else None
    def capture(name,controls=False):
        for _ in range(3):app.graphicsEngine.renderFrame()
        image=PNMImage();assert (app.win if controls else app.aquarium_window).getScreenshot(image)
        image.write(str(out/(name+'.png')));return image
    def pixels(image):return [tuple(image.getXel(x,y)) for y in range(0,image.getYSize(),3) for x in range(0,image.getXSize(),3)]
    baseline=pixels(capture('classic'))
    original=deepcopy(app.settings)
    nodes={key:value[0].node() for key,value in app.models.items()}
    for key,raw in BUILTINS.items():
        app.appearance.apply_settings(apply(original,raw));frame=pixels(capture(key))
        assert nodes=={key:value[0].node() for key,value in app.models.items()}
        assert frame==baseline if key=='classic' else frame!=baseline
    app.appearance.apply_settings(original)
    assert pixels(capture('classic-restored'))==baseline
    print('PASS six native theme frames; Classic restores pixel-identically without mesh rebuilding',flush=True)
    # All colours/stages and styles retain a conservative Classic projected envelope.
    count=0
    for stage in range(4):
        for colour in range(7):
            fish=replace(roster[0],stage=stage,body=colour,scales=(colour+1)%7,eyes=(colour+2)%7,tint=0x47af)
            classic=fish_model(fish,18)[0];low,high=classic.getTightBounds()
            for style in ('rounded','faceted'):
                node=fish_model(fish,18,style)[0];a,b=node.getTightBounds()
                assert all(a[k]>=low[k]-.001 and b[k]<=high[k]+.001 for k in range(3)),(stage,style,low,high,a,b)
                node.removeNode();count+=1
            classic.removeNode()
    frames=[]
    for style in ('classic','rounded','faceted'):
        settings=deepcopy(original);settings.fish_style=style
        poses={key:(tuple(v[0].getPos()),tuple(v[0].getHpr()),tuple(v[0].getScale()),v[0].isHidden()) for key,v in app.models.items()}
        app.appearance.apply_settings(settings)
        assert poses=={key:(tuple(v[0].getPos()),tuple(v[0].getHpr()),tuple(v[0].getScale()),v[0].isHidden()) for key,v in app.models.items()}
        frames.append(pixels(capture('fish-'+style)))
        assert swimmers=={key:id(v) for key,v in app.sim.swimmers.items()}
        assert app.roster==roster
    assert frames[0]!=frames[1] and frames[1]!=frames[2] and frames[0]!=frames[2]
    print(f'PASS {count} stage/colour variant envelopes; styles visibly differ, fish state retained',flush=True)
    # Existing desired/shown sequencing remains authoritative during geometry edits.
    app.settings.fish_animations=True;app.settings.exit_styles=dict.fromkeys(('shark','net','bag','bowl','cage'),False)
    old=roster[0];new=replace(old,body=(old.body+1)%7,event_id=old.event_id+1)
    app.roster=[new,*roster[1:]];app.sync_models();assert old.owner in app.transitions.departures
    for _ in range(30):app.update_fish(1/30)
    settings=deepcopy(app.settings);settings.fish_style='rounded';app.appearance.apply_settings(settings)
    assert app.transitions.shown[old.owner]==old
    capture('restyle-during-exit')
    for _ in range(450):app.update_fish(1/30)
    assert app.transitions.shown[old.owner]==new and old.owner not in app.transitions.departures
    assert len(app.models)==len(app.sim.swimmers)==12
    if hasattr(app,'controls'):
        app.controls.page('Themes');panel=app.controls.themes
        panel.key.enterText('my-lagoon');panel.name.enterText('My lagoon');panel.save()
        assert panel.library.read('my-lagoon')['fish_style']=='rounded'
        panel.load();panel.path.enterText(str(Path(app.args.settings).parent/'export.json'));panel.export_file()
        assert json.loads(Path(panel.path.get()).read_text())['id']=='my-lagoon'
        capture('theme-controls',True)
        app.controls.page('Appearance');capture('appearance-controls',True)
    # Dense roster: no leaks, model/body identity and old/new transitions preserved.
    app.settings.fish_animations=False;app.roster=list(visitors(256));app.sync_models()
    for style in ('faceted','rounded','classic'):
        settings=deepcopy(app.settings);settings.fish_style=style;app.appearance.apply_settings(settings)
        assert len(app.models)==len(app.sim.swimmers)==256
        app.update_fish(1/30)
    assert len(app.scene.findAllMatches('**/static-fish-geometry'))==256
    print('PASS native editor/export, mid-exit update and256-fish style changes without leaks',flush=True)
    (out/'report.json').write_text(json.dumps(dict(themes=6,style_envelopes=count,dense_fish=256,managed=getattr(app,'managed',False))))


def main():
    from tank.aquarium import Aquarium
    from tank.__main__ import main as run
    from tank.settings import Settings
    managed='--managed' in sys.argv;Aquarium.run=exercise
    with tempfile.TemporaryDirectory(prefix='aquarium-themes-') as directory:
        path=Path(directory)/'settings.json';settings=Settings();settings.apply('low');settings.vsync=False;settings.fish_animations=False;settings.save(path)
        sys.argv=['themes-smoke','--demo','12','--width','960','--height','540','--settings',str(path)]
        if managed:sys.argv+=['--managed-settings']
        run()


if __name__=='__main__':main()
