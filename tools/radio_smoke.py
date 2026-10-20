"""Native Radio controls with synthetic peer; no physical ports/RF/user data."""
from pathlib import Path
import tempfile
import time


def exercise(app):
    from panda3d.core import WindowProperties
    import tank.service as service_module
    from tools.radio_peer import MeshRadio, PEER, direct_message, channel_message, contact_packet
    radio=MeshRadio(count=3,contact_count=27,channel_count=14);radio.ack_early=True
    owners=[]
    def opening(*args,**kw):
        import threading
        owners.append(threading.get_ident());return radio
    service_module.open_transport=opening
    service_module.discover=lambda kind:[('COM7','COM7 · Synthetic MeshCore RX')]
    controls=app.controls;panel=controls.radio
    app.args.live_database=Path(app.args.settings).parent/'radio-live.sqlite'
    shots=Path('.local/radio-ui');shots.mkdir(parents=True,exist_ok=True)
    def wait_for(predicate,timeout=12):
        end=time.monotonic()+timeout
        while not predicate() and time.monotonic()<end:app.taskMgr.step()
        assert predicate(),(panel.status['text'],controls.connection_label['text'])
    def screenshot(name):
        for _ in range(4):app.taskMgr.step()
        assert app.win.saveScreenshot(str(shots/(name+'.png')))
    def click(text):
        button=next(b for b in panel.write_buttons+panel.read_buttons if b['text']==text)
        button['command']()
    props=WindowProperties();props.setSize(456,748);app.win.requestProperties(props)
    wait_for(lambda:len(app.roster)==12)
    controls.page('Radio');panel.page('Connection')
    assert list(controls.tabs)==['Aquarium','Radio','Deadzones','Decorations','Animations']
    assert list(panel.tabs)==['Connection','Chat','Contacts','Channels','Device','Tools']
    screenshot('connection-disconnected')
    controls.endpoint.enterText('COM7');controls.connect_button['command']()
    wait_for(lambda:controls.state=='connected' and len(app.roster)==3)
    panel.page('Chat');wait_for(lambda:panel.state.get('loaded'))
    assert len(panel.state['contacts'])==27 and len(panel.state['channels'])==14
    assert len(owners)==1
    # Real OS clipboard via the hidden Tk owner; no external desktop required.
    panel.composer['focus']=1
    controls.clipboard.copy('Clipboard fish 🐟')
    app.messenger.send('control-shift-v');assert panel.composer.get()=='Clipboard fish 🐟'
    app.messenger.send('control-c');assert controls.clipboard.paste()=='Clipboard fish 🐟'
    app.messenger.send('control-x');assert panel.composer.get()==''
    controls.blur()
    radio.inbox.extend([channel_message(),direct_message()])
    wait_for(lambda:any(m.get('text')=='Nickel: Hello reef 🐟' for m in panel.messages))
    panel.composer.enterText('Hello from the aquarium 🐟');panel.composer['focus']=1
    old_names=app.show_names;outputs=len(app.views);fish=len(app.roster)
    for key in ('f','n','v','1','delete'):app.messenger.send(key)
    assert app.show_names==old_names and len(app.views)==outputs and len(app.roster)==fish
    click('Send');wait_for(lambda:panel.composer.get()=='' and any(m['direction']=='out' for m in panel.messages))
    assert radio.tx_count==1
    panel.composer.enterText('Next message…');screenshot('chat-channel');panel.composer.enterText('')
    panel.route_menu.set('Direct messages')
    panel.chat_picker.selected='dm:'+PEER[:12];panel.chat_picker.render();panel.choose_chat('dm:'+PEER[:12])
    wait_for(lambda:any(m['direction']=='in' for m in panel.messages))
    panel.composer.enterText('Direct message with confirmed delivery');click('Send')
    panel.send()  # A repeated hotkey before completion must not enqueue twice.
    wait_for(lambda:any(m['status']=='delivered' for m in panel.messages))
    assert radio.tx_count==2
    screenshot('chat-direct')
    panel.page('Contacts');panel.contact_search.enterText('Nickel');click('Search')
    assert len(panel.contact_picker.items)==1 and panel.contact_picker.selected==PEER
    panel.contact_name.enterText('Nickel 🐟');click('Save / Add')
    wait_for(lambda:not panel.pending)
    panel.contact_search.enterText('');click('Search')
    panel.contact_picker.offset=0;panel.contact_picker.selected=panel.contact_picker.items[0][0];panel.contact_picker.render()
    panel.contact_picker.move(1);assert panel.contact_picker.offset==10
    panel.contact_picker.move(-1)
    screenshot('contacts')
    panel.page('Channels');panel.channel_picker.move(1);assert panel.channel_picker.offset==10
    panel.channel_picker.move(-1);panel.choose_channel(0)
    panel.channel_name.enterText('#aquarium-test');click('Save channel')
    wait_for(lambda:any(c['index']==0 and c['name']=='#aquarium-test' for c in panel.state['channels']))
    screenshot('channels')
    panel.page('Device');screenshot('device')
    panel.page('Tools');click('Local radio statistics')
    wait_for(lambda:any('received:' in s for s in panel.activity))
    screenshot('tools')
    # Discoveries enter a distinct list, not silently into the contact table.
    key='fc'*32;radio.replies.put(contact_packet(key,'New harbor node',code=0x8a))
    wait_for(lambda:bool(panel.state['discovered']))
    panel.page('Contacts');panel.contact_mode_menu.set('Discovered')
    assert panel.contact_picker.selected==key
    click('Save / Add');wait_for(lambda:any(c['key']==key for c in panel.state['contacts']))
    assert len(owners)==1 and {1,3,5}<=radio.acked and len(app.roster)==3
    panel.page('Connection');screenshot('connection-connected')
    controls.disconnect_button['command']();wait_for(lambda:controls.state=='idle')
    assert panel.send_button['state']=='disabled' and len(app.roster)==3
    panel.page('Chat');screenshot('chat-offline')
    print('PASS native Radio six tabs, shared-port owner, channel/DM input/send/delivery, Unicode, paged contacts/channels, discovery, device controls, stats and disconnected safety',flush=True)
    print('PASS original Connection layout and aquarium shortcut isolation; fish ACKs and roster survived all operations',flush=True)


def main():
    from tank.aquarium import Aquarium
    Aquarium.run=exercise
    import sys
    with tempfile.TemporaryDirectory(prefix='tank-radio-ui-') as directory:
        sys.argv=[sys.argv[0],'--demo','12','--preset','low','--settings',str(Path(directory)/'settings.json')]
        from tank.__main__ import main as run
        run()


if __name__=='__main__':main()
