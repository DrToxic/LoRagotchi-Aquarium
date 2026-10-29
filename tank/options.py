"""Compact, pixel-sized native controls. No transport work on the render thread."""
from pathlib import Path
import time
import textwrap
from panda3d.core import TextNode
from direct.gui import DirectGuiGlobals as DGG
from direct.gui.DirectGui import DirectFrame, DirectLabel, DirectButton, DirectOptionMenu, DirectSlider, DirectEntry
from .controls_shell import ControlsShell
from .connection import ConnectionProfile
from .settings import PRESETS
from .deadzone_panel import DeadzonePanel
from .text import display_text, entry_font
from .decoration_panel import DecorationPanel
from .animation_panel import AnimationPanel
from .expiry_panel import ExpiryPanel
from .radio_panel import RadioPanel
from .clipboard import Clipboard
from .appearance_panel import AppearancePanel
from .theme_panel import ThemePanel
from .nursery_panel import NurseryPanel
from .games_panel import GamesPanel
from .travel_panel import TravelPanel


class OptionsPanel(ControlsShell):
    WIDTH, HEIGHT = 1100, 800
    TYPES = {'USB serial': 'serial', 'Bluetooth LE': 'ble', 'Network bridge': 'tcp'}

    def __init__(self, app):
        self.app = app; self.entries = []; self.devices = {}; self.scan_pending = False
        self.clipboard=Clipboard()
        self.state = 'idle'; self.mode = 'demo' if app.args.demo is not None else 'replay' if app.args.replay else 'live'
        self.profile = ConnectionProfile.load(Path(app.args.settings).with_name('rx-connection.json'))
        if app.args.connect:
            try: self.profile = ConnectionProfile.from_uri(app.args.connect, app.args.token_file)
            except ValueError: pass
        self.build_shell()
        self.build_aquarium(self.pages['Aquarium'])
        self.pages['Lifespan']=self.make_page()
        self.expiry=ExpiryPanel(self,self.pages['Lifespan'])
        self.pages['Appearance']=self.make_page()
        self.appearance=AppearancePanel(self,self.pages['Appearance'])
        self.pages['Themes']=self.make_page()
        self.themes=ThemePanel(self,self.pages['Themes'])
        self.pages['Transfers']=self.make_page()
        self.transfers=TravelPanel(self,self.pages['Transfers'])
        self.pages['Nursery']=self.make_page()
        self.nursery=NurseryPanel(self,self.pages['Nursery'])
        self.pages['Games']=self.make_page()
        self.games=GamesPanel(self,self.pages['Games'])
        self.radio=RadioPanel(self,self.pages['Radio'])
        self.deadzones=DeadzonePanel(self,self.pages['Deadzones'])
        self.decorations=DecorationPanel(self,self.pages['Decorations'])
        self.animations=AnimationPanel(self,self.pages['Animations'])
        self.finish_shell()
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
        button=DirectButton(parent=parent,text=text,text_scale=14,text_pos=(width/2,0),
                            text_fg=(.88,.97,.95,1),frameSize=(0,width,-9,21),
                            frameColor=(.10,.22,.25,1),relief=DGG.FLAT,pos=(x,0,-y),command=invoke)
        if text=='Back' or text.lower().startswith('back to '):button.hide()
        return button

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
        self.build_overview(parent)
        self.build_performance(self.pages['Performance'])

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
        self.refresh_shell()
        self.nursery.refresh()
        if self.active_page=='Lifespan':self.expiry.refresh()
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
        self.navigate(name)

    def editing(self):return bool(getattr(self,'_close_dialog',None)) or any(entry.guiItem.getFocus() for entry in self.entries)
    def send_chat_shortcut(self):
        if self.active_page=='Radio' and self.radio.active=='Chat' and self.radio.composer.guiItem.getFocus():
            self.radio.send()

    def edit_clipboard(self,operation):
        entry=next((entry for entry in self.entries if entry.guiItem.getFocus() and not entry.isHidden()),None)
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
        if getattr(self,'_close_dialog',None):return
        visible=[entry for entry in self.entries if not entry.isHidden()]
        focused=next((i for i,e in enumerate(visible) if e.guiItem.getFocus()),-1)
        self.blur()
        if visible:
            target=visible[(focused+1)%len(visible)];self.reveal_field(target);target['focus']=1
    def resize(self):
        self.resize_shell()
