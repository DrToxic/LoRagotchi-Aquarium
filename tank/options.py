"""Compact, pixel-sized native controls. No transport work on the render thread."""
from pathlib import Path
import time
import textwrap
from panda3d.core import TextNode
from direct.gui import DirectGuiGlobals as DGG
from direct.gui.DirectGui import DirectFrame, DirectLabel, DirectButton, DirectOptionMenu, DirectSlider, DirectEntry
from .connection import ConnectionProfile
from .settings import PRESETS
from .deadzone_panel import DeadzonePanel
from .text import display_text, entry_font
from .decoration_panel import DecorationPanel
from .animation_panel import AnimationPanel
from .radio_panel import RadioPanel
from .clipboard import Clipboard
from .appearance_panel import AppearancePanel
from .travel_panel import TravelPanel


class OptionsPanel:
    WIDTH, HEIGHT = 432, 724
    TYPES = {'USB serial': 'serial', 'Bluetooth LE': 'ble', 'Network bridge': 'tcp'}

    def __init__(self, app):
        self.app = app; self.entries = []; self.devices = {}; self.scan_pending = False
        self.clipboard=Clipboard()
        self.state = 'idle'; self.mode = 'demo' if app.args.demo is not None else 'replay' if app.args.replay else 'live'
        self.profile = ConnectionProfile.load(Path(app.args.settings).with_name('rx-connection.json'))
        if app.args.connect:
            try: self.profile = ConnectionProfile.from_uri(app.args.connect, app.args.token_file)
            except ValueError: pass
        self.root = DirectFrame(parent=app.pixel2d, frameSize=(0,self.WIDTH,-self.HEIGHT,0),
                                frameColor=(.018,.065,.085,.97))
        # Keep editing reachable even if a projector mask blacks the main view.
        from .projection import configure_overlay_bins
        configure_overlay_bins()
        self.root.setBin('projector-controls',0,100)
        self.label(self.root,'TANK CONTROLS',18,29,17)
        self.button(self.root,'–',389,25,25,app.toggle_panel)
        self.tabs = {name:self.button(self.root,name,18+i*81,66,78,lambda n=name:self.page(n))
                     for i,name in enumerate(('Aquarium','Radio','Deadzones','Decorations','Animations'))}
        for button in self.tabs.values():button["text_scale"]=11
        self.pages = {name:DirectFrame(parent=self.root,frameColor=(0,0,0,0)) for name in self.tabs}
        self.build_aquarium(self.pages['Aquarium'])
        self.pages['Appearance']=DirectFrame(parent=self.root,frameColor=(0,0,0,0))
        self.appearance=AppearancePanel(self,self.pages['Appearance'])
        self.pages['Transfers']=DirectFrame(parent=self.root,frameColor=(0,0,0,0))
        self.transfers=TravelPanel(self,self.pages['Transfers'])
        self.radio=RadioPanel(self,self.pages['Radio'])
        self.deadzones=DeadzonePanel(self,self.pages['Deadzones'])
        self.decorations=DecorationPanel(self,self.pages['Decorations'])
        self.animations=AnimationPanel(self,self.pages['Animations'])
        app.footer=self.label(self.root,'Starting aquarium…',18,665,12,396)
        self.label(self.root,'Drag any aquarium to move; drag its edges to resize.\nTab brings controls here. Esc closes that aquarium.',18,699,12,396)
        self.page('Aquarium'); self.resize()
        for key,operation in [('control-c','copy'),('control-x','cut'),('control-v','paste'),('control-shift-v','replace')]:
            app.accept(key,self.edit_clipboard,[operation])
        app.accept('control-enter',self.send_chat_shortcut)

    def label(self,parent,text,x,y,size=14,wrap=None):
        kwargs = dict(parent=parent,text=text,text_align=TextNode.ALeft,text_scale=size,
                      text_fg=(.82,.91,.88,1),frameColor=(0,0,0,0),pos=(x,0,-y))
        if wrap: kwargs['text_wordwrap']=wrap/size
        return DirectLabel(**kwargs)

    def button(self,parent,text,x,y,width,command):
        def invoke(): self.blur(); command()
        return DirectButton(parent=parent,text=text,text_scale=14,text_pos=(width/2,0),
                            text_fg=(.88,.97,.95,1),frameSize=(0,width,-9,21),
                            frameColor=(.10,.22,.25,1),relief=DGG.FLAT,pos=(x,0,-y),command=invoke)

    def enabled(self,button,enabled):
        state=DGG.NORMAL if enabled else DGG.DISABLED
        if button['state']!=state:
            button['state']=state
            button['frameColor']=(.10,.22,.25,1) if enabled else (.045,.105,.125,1)
            button['text_fg']=(.88,.97,.95,1) if enabled else (.37,.51,.52,1)

    def menu(self,parent,items,x,y,width,command,initial=0):
        # Menu coordinates are font units, matching the popup's own text layout.
        menu=DirectOptionMenu(parent=parent,items=items,initialitem=initial,scale=14,
                                text_align=TextNode.ALeft,text_fg=(.90,.96,.94,1),
                                frameColor=(.09,.19,.22,1),highlightColor=(.15,.36,.39,1),
                                frameSize=(-.3,width/14,-.55,1.1),pos=(x,0,-y),
                                popupMarker_pos=(width/14-.8,0,0),command=command)
        menu.popupMenu.setBin('gui-popup',0,101)
        return menu

    def entry(self,parent,text,x,y,width):
        field = DirectEntry(parent=parent,initialText=text,scale=14,width=width/14,entryFont=entry_font(),
                            numLines=1,focus=0,text_fg=(.94,.98,.95,1),
                            frameColor=(.07,.15,.18,1),relief=DGG.FLAT,
                            frameSize=(-.3,width/14+.3,-.6,1.2),pos=(x,0,-y),
                            command=lambda _:self.blur())
        self.entries.append(field)
        return field

    def build_aquarium(self,parent):
        a=self.app
        self.label(parent,'DISPLAY',18,105,12)
        self.label(parent,'Graphics preset',18,139)
        a.preset_menu=self.menu(parent,list(PRESETS),213,139,187,a.set_preset,
                               list(PRESETS).index(a.settings.preset) if a.settings.preset in PRESETS else 2)
        self.label(parent,'Render scale',18,179)
        a.scale_slider=DirectSlider(parent=parent,range=(.25,1.5),value=a.settings.scale,pageSize=.05,
                                    scale=85,pos=(300,0,-174),command=a.scale_label_update)
        a.scale_label=self.label(parent,'',18,207,12)
        self.button(parent,'Apply scale',18,240,120,a.apply_scale)
        self.button(parent,'Fullscreen [F]',150,240,126,a.fullscreen)
        self.button(parent,'Add window [V]',288,240,126,a.add_window)
        a.output_label=self.label(parent,'',18,272,12)
        self.chat_button=self.button(parent,'Channel chat: '+('on' if a.settings.chat_bubbles else 'off'),
                                     18,315,396,a.toggle_chat)
        self.label(parent,'DISPLAYED FISH',18,336,12)
        a.fish_label=self.label(parent,'',18,363,14,392)
        self.button(parent,'Next fish',18,416,120,a.select_next)
        self.button(parent,'Remove copy',150,416,126,a.remove_selected)
        self.button(parent,'Names [N]',288,416,126,a.toggle_names)
        a.end_button=self.button(parent,'End display session',18,464,396,a.end_session)
        a.message_label=self.label(parent,'Inbox: no messages',18,505,12,392)
        self.button(parent,'Appearance & advanced graphics',18,548,396,lambda:self.page('Appearance'))
        self.label(parent,'Copies stay after originals return. Closing controls quits.',18,588,12)
        a.clear_confirm=0; a.scale_label_update()

    def build_radio(self,parent):
        self.label(parent,'CONNECT TO LoRagotchi-RX',18,105,12)
        self.transport_menu=self.menu(parent,list(self.TYPES),24,139,376,self.transport_changed,
                                      list(self.TYPES.values()).index(self.profile.transport))
        self.local_group=DirectFrame(parent=parent,frameColor=(0,0,0,0))
        self.endpoint_label=self.label(self.local_group,'Port',18,180)
        self.endpoint=self.entry(self.local_group,'',24,211,376)
        self.scan_button=self.button(self.local_group,'Refresh USB ports',18,252,396,self.scan)
        self.device_menu=self.menu(self.local_group,['No devices listed'],24,293,376,self.choose_device)
        self.scan_note=self.label(self.local_group,'Use Refresh or enter a port above.',18,324,12,392)
        self.network_group=DirectFrame(parent=parent,frameColor=(0,0,0,0))
        self.label(self.network_group,'Bridge host / IP',18,180)
        self.host=self.entry(self.network_group,self.profile.host,24,211,274)
        self.label(self.network_group,'Port',322,180)
        self.port=self.entry(self.network_group,self.profile.port,326,211,74)
        self.label(self.network_group,'Bridge token file path',18,253)
        self.token_file=self.entry(self.network_group,self.profile.token_file,24,285,376)
        self.label(self.network_group,'Use the token file from your PC/SBC bridge.\nThis is not onboard radio Wi-Fi.',18,320,12,392)
        self.help_label=self.label(parent,'',18,367,13,392)
        self.connection_label=self.label(parent,'Not connected',18,423,13,392)
        self.connect_button=self.button(parent,'Connect',18,510,190,self.connect)
        self.disconnect_button=self.button(parent,'Disconnect',224,510,190,self.disconnect)
        self.mode_label=self.label(parent,'',18,548,12,392)
        self.label(parent,'Details remembered; connections are never automatic.',18,577,12)
        self.transport_changed(next(k for k,v in self.TYPES.items() if v==self.profile.transport),initial=True)

    def remember_fields(self):
        if self.profile.transport=='serial':self.profile.serial_port=self.endpoint.get().strip()
        elif self.profile.transport=='ble':self.profile.ble_address=self.endpoint.get().strip()
        self.profile.host=self.host.get().strip();self.profile.port=self.port.get().strip()
        self.profile.token_file=self.token_file.get().strip()

    def transport_changed(self,label,initial=False):
        if not hasattr(self,'network_group'):return
        self.blur()
        if not initial:self.remember_fields()
        self.profile.transport=self.TYPES[label]
        self.local_group.hide();self.network_group.hide()
        self.devices={};self.device_menu['items']=['No devices listed'];self.device_menu.set(0,fCommand=0)
        kind=self.profile.transport
        if kind=='tcp':
            self.network_group.show()
            text='Authenticated network bridge. One aquarium client at a time.'
        else:
            self.local_group.show()
            self.endpoint_label['text']='Serial port (e.g. COM4 or /dev/ttyUSB0)' if kind=='serial' else 'Bluetooth address / device identifier'
            self.endpoint.enterText(self.profile.serial_port if kind=='serial' else self.profile.ble_address)
            self.scan_button['text']='Refresh USB ports' if kind=='serial' else 'Scan nearby Bluetooth devices'
            self.scan_note['text']='Refresh the list or enter a device above.'
            text='USB companion connection at 115200 baud.' if kind=='serial' else 'Pair in your OS using the RX display PIN first.\nScanning alone does not pair or connect.'
        self.help_label['text']=text+'\nRequires LoRagotchi-RX firmware, not stock MeshCore.'

    def choose_device(self,label):
        if label in self.devices:self.endpoint.enterText(self.devices[label])

    def scan(self):
        if self.scan_pending:return
        self.scan_pending=True;self.enabled(self.scan_button,False)
        self.scan_note['text']='Scanning…' if self.profile.transport=='ble' else 'Reading USB ports…'
        self.app.service.commands.put(('scan',self.profile.transport))

    def on_devices(self,event):
        self.scan_pending=False;self.enabled(self.scan_button,True)
        if event['transport']!=self.profile.transport:return
        # Bound the native popup to the panel; manual entry remains available.
        self.devices={display_text(f'{i+1}. {label[:48]}'):address for i,(address,label) in enumerate(event['devices'][:12])}
        items=['Choose a detected device']+list(self.devices) if self.devices else ['No devices found']
        self.device_menu['items']=items;self.device_menu.set(0,fCommand=0)
        self.scan_note['text']=display_text(event.get('error') or (f'{len(self.devices)} found. Select one, then Connect.' if self.devices else 'No devices found. You can still enter the address above.'))
        if len(event['devices'])>12:self.scan_note['text']=f'{len(event["devices"])} found; showing 12. Enter another address above.'

    def connect(self):
        if self.state in ('connecting','connected','retrying','disconnecting','fatal'):return
        self.remember_fields()
        try:
            # Pass a snapshot, not fields that subsequent edits can mutate.
            from dataclasses import replace
            self.app.service.connect(replace(self.profile))
            self.state='connecting';self.connection_label['text']='Connecting…'
        except ValueError as exc:self.connection_label['text']=display_text(str(exc))

    def disconnect(self):
        self.app.service.disconnect();self.state='disconnecting'
        self.connection_label['text']='Disconnecting… waiting for the current request.'

    def on_connection(self,event):
        self.state=event.get('state','idle')
        self.connection_label['text']=display_text(textwrap.fill(event['text'],width=54,max_lines=5,placeholder='…'))
        self.radio.connection(event)
        self.refresh()

    def refresh(self):
        self.radio.refresh_hint()
        if getattr(self,'active_page',None)=='Decorations':self.decorations.refresh_status()
        if getattr(self,'active_page',None)=='Transfers':self.transfers.refresh()
        self.app.set_ui_text(self.mode_label,('Demo/replay will be replaced by the saved live collection.'
                                 if self.mode!='live' else 'LIVE collection · saved copies remain when disconnected.'))
        self.enabled(self.connect_button,self.state not in ('connecting','connected','retrying','disconnecting','fatal'))
        self.enabled(self.disconnect_button,self.state in ('connecting','connected','retrying'))
        self.enabled(self.scan_button,not self.scan_pending and self.state not in ('connecting','connected','retrying','disconnecting','fatal'))
        if self.app.clear_confirm and self.app.clear_confirm<time.monotonic():
            self.app.clear_confirm=0;self.app.end_button['text']='End display session'

    def page(self,name):
        self.blur()
        for key,frame in self.pages.items():
            frame.show() if key==name else frame.hide()
            if key in self.tabs:self.tabs[key]['frameColor']=(.14,.34,.37,1) if key==name else (.07,.16,.19,1)
        self.active_page=name
        if name=='Radio':self.radio.page(self.radio.active)
        if name=='Appearance':self.appearance.refresh()
        if name=='Decorations':self.decorations.rebuild()
        if name=='Transfers':self.transfers.refresh()

    def editing(self):return any(entry['focus'] for entry in self.entries)
    def send_chat_shortcut(self):
        if self.active_page=='Radio' and self.radio.active=='Chat' and self.radio.composer['focus']:
            self.radio.send()

    def edit_clipboard(self,operation):
        entry=next((entry for entry in self.entries if entry['focus'] and not entry.isHidden()),None)
        if entry is None:return
        try:
            if operation in ('copy','cut'):
                if entry['obscured']:raise ValueError('Masked fields are not copied to the clipboard.')
                self.clipboard.copy(entry.get())
                if operation=='cut':entry.enterText('')
            else:
                text=self.clipboard.paste()
                if len(text)>4096:raise ValueError('Clipboard text exceeds 4096 characters.')
                if any(ord(c)<32 and c not in '\n\t\r' for c in text):raise ValueError('Clipboard contains unsupported control characters.')
                if entry['numLines']==1:text=text.replace('\r','').replace('\n',' ').replace('\t',' ')
                if operation=='replace':entry.enterText(text)
                else:
                    old=entry.get();cursor=entry.guiItem.getCursorPosition()
                    entry.enterText(old[:cursor]+text+old[cursor:]);entry.setCursorPosition(cursor+len(text))
        except Exception as exc:
            self.radio.status['text']=display_text(f'Clipboard unavailable: {exc}')
    def blur(self):
        for entry in self.entries:entry['focus']=0
    def next_field(self):
        visible=[entry for entry in self.entries if not entry.isHidden()]
        focused=next((i for i,e in enumerate(visible) if e['focus']),-1)
        self.blur()
        if visible:visible[(focused+1)%len(visible)]['focus']=1
    def resize(self):
        width,height=self.app.win.getXSize(),self.app.win.getYSize()
        scale=min(1.,(width-24)/self.WIDTH,(height-24)/self.HEIGHT)
        self.root.setScale(scale);self.root.setPos(max(12,width-self.WIDTH*scale-12),0,-12)
