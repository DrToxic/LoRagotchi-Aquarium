"""Native proof of persisted expiry, exit/re-entry, controls and no model leaks."""
from dataclasses import replace
from pathlib import Path
import json
import sys
import tempfile
import time


def exercise(app):
    from panda3d.core import PNMImage
    from tank.store import Store
    from tank.settings import Settings
    output = Path('.local/expiry'); output.mkdir(parents=True, exist_ok=True)

    def wait(predicate):
        end = time.monotonic()+8
        while not predicate() and time.monotonic()<end:
            app.taskMgr.step()
        assert predicate()

    def advance(seconds):
        for _ in range(round(seconds*30)): app.update_fish(1/30)

    def capture(name, controls=False):
        for _ in range(3): app.graphicsEngine.renderFrame()
        image = PNMImage()
        window = app.win if controls else app.views[0].window
        assert window.getScreenshot(image)
        assert image.write(str(output/(name+'.png')))

    wait(lambda:len(app.roster)==2)
    app.taskMgr.remove('aquarium-update')
    old, fresh = app.roster
    app.settings.fish_animations=True
    app.settings.exit_styles=dict.fromkeys(('shark','net','bag','bowl','cage'),False)
    advance(1)
    old_model=app.models[old.owner][0]
    capture('before-expiry')

    def pump(predicate):
        end=time.monotonic()+8
        while not predicate() and time.monotonic()<end:
            from types import SimpleNamespace
            app.update(SimpleNamespace(cont=None))
            time.sleep(.02)
        assert predicate()

    if hasattr(app,'controls'):
        app.controls.page('Lifespan');panel=app.controls.expiry
        panel.mode.set('After last share',fCommand=0)
        panel.amount.enterText('0.02');panel.unit.set('Hours',fCommand=0)
        panel.apply()
        assert Settings.load(app.args.settings).fish_lifespan_hours==.02
        panel.refresh()
    else:
        app.service.commands.put(('lifespan',.02))
    pump(lambda:len(app.roster)==1)
    assert app.roster==[fresh] and app.lifespan['expired']==1
    if hasattr(app,'controls'):
        app.controls.expiry.refresh();capture('lifespan-controls',True)
    assert app.models[old.owner][0]==old_model
    assert old.owner in app.transitions.departures
    advance(1);capture('expiry-exit')
    advance(12)
    assert old.owner not in app.models and old.owner not in app.sim.swimmers
    assert not app.transitions.departures
    capture('after-expiry')
    print('PASS actual worker expiry -> old model exits -> node/body removed',flush=True)

    store=Store(app.args.database)
    assert len(store.roster())==2
    renewed=replace(old,event_id=101,tx_id=old.tx_id+1)
    store.save(renewed);store.close()
    app.service.commands.put(('lifespan',.02))
    pump(lambda:len(app.roster)==2)
    advance(12)
    assert len(app.models)==len(app.sim.swimmers)==2
    assert app.transitions.shown[old.owner]==renewed
    print('PASS identical-appearance new share renews and returns once',flush=True)

    # Manual hiding survives a policy change to disabled.
    app.service.commands.put(('remove',old.owner))
    pump(lambda:len(app.roster)==1)
    app.service.commands.put(('lifespan',0))
    pump(lambda:app.lifespan.get('hours')==0)
    advance(12)
    assert set(app.models)=={fresh.owner}
    print('PASS manual hide remains hidden when expiry is disabled',flush=True)

    # Restore only via a new share, then expire during arrival. No late re-entry.
    store=Store(app.args.database)
    store.save(replace(renewed,event_id=102,tx_id=renewed.tx_id+1));store.close()
    app.service.commands.put(('lifespan',0))
    pump(lambda:len(app.roster)==2)
    assert old.owner in app.transitions.arrivals
    store=Store(app.args.database)
    with store.db:
        store.db.execute("UPDATE fish SET updated='2020-01-01 00:00:00' WHERE owner=?",(old.owner,))
    store.close()
    app.service.commands.put(('lifespan',1))
    pump(lambda:len(app.roster)==1)
    advance(16)
    assert set(app.models)=={fresh.owner} and not app.transitions.arrivals and not app.transitions.departures
    # Animation opt-out still obeys lifespan; restoring never edits share time.
    app.settings.fish_animations=False
    app.service.commands.put(('lifespan',0));pump(lambda:len(app.roster)==2)
    app.service.commands.put(('lifespan',1));pump(lambda:len(app.roster)==1)
    assert set(app.models)=={fresh.owner}
    print('PASS expiry during entry and animation opt-out; no stale re-entry/leaks',flush=True)
    (output/'report.json').write_text(json.dumps(dict(checks=5,active=len(app.models),
        expired=app.lifespan['expired'],managed=getattr(app,'managed',False)),indent=2))


def main():
    from tank.aquarium import Aquarium
    from tank.__main__ import main as run
    from tank.demo import visitors
    from tank.settings import Settings
    from tank.store import Store
    managed='--managed' in sys.argv
    Aquarium.run=exercise
    with tempfile.TemporaryDirectory(prefix='aquarium-expiry-') as directory:
        path=Path(directory)/'settings.json';database=Path(directory)/'copies.sqlite'
        settings=Settings();settings.apply('low');settings.fish_animations=False
        settings.vsync=False;settings.save(path)
        fish=list(visitors(2))
        store=Store(database,clock=lambda:time.time()-120);store.save(fish[0]);store.close()
        store=Store(database);store.save(fish[1]);store.close()
        # Demo zero isolates the fixture; no live radio or credentials.
        sys.argv=['expiry-smoke','--demo','0','--database',str(database),'--width','960',
                  '--height','540','--settings',str(path)]
        if managed:sys.argv+=['--managed-settings']
        run()


if __name__=='__main__':main()
