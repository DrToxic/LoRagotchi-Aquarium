"""Native MeshCore workspace. Widgets enqueue jobs; they never touch a port."""
from collections import deque
from datetime import datetime
import time
import textwrap
from direct.gui.DirectGui import DirectFrame, DirectScrolledFrame
from .text import display_text


def editable_name(value):
    # Remote names are untrusted; don't inject Panda formatting into PGEntry.
    # This is only a field presentation. Wire/history values remain unchanged.
    return ''.join(c for c in value if ord(c)>=32 and ord(c)!=127)


def set_scrolled_text(frame, label, text, *, latest=True):
    label['text']=text
    # DirectLabel updates glyphs but keeps its original PGItem frame. Inside a
    # PGScrollFrame that stale one-line frame culls the entire history as soon
    # as it leaves the viewport, even while later lines are still on screen.
    label.resetFrameSize()
    # Font metrics/word wrapping, including emoji, determine the canvas height;
    # a line-count estimate leaves blank overscroll or cuts off the final line.
    bottom=label.getZ()+label.getBounds()[2]
    left,right,_,top=frame['canvasSize']
    view=frame['frameSize']
    height=max(view[3]-view[2],top-bottom+12)
    frame['canvasSize']=(left,right,top-height,top)
    frame.verticalScroll['value']=1 if latest else 0


class Picker:
    """A bounded popup with pagination: all contacts stay reachable at 432px."""
    def __init__(self, ui, parent, y, changed, width=376):
        self.ui=ui;self.changed=changed;self.items=[];self.selected=None;self.offset=0;self.labels={}
        self.menu=ui.menu(parent,['No items'],24,y,width,self.choose)
        self.previous=ui.button(parent,'Previous',18,y+34,90,lambda:self.move(-1))
        self.next=ui.button(parent,'Next',324,y+34,90,lambda:self.move(1))
        self.count=ui.label(parent,'0 items',123,y+34,12,190)

    def set_items(self, items):
        if self.items==items:return
        old=self.selected;self.items=items
        keys=[item[0] for item in items]
        if self.selected not in keys:self.selected=keys[0] if keys else None
        self.offset=(keys.index(self.selected)//10)*10 if self.selected in keys else 0
        self.render()
        if old!=self.selected:self.changed(self.selected)

    def render(self):
        page=self.items[self.offset:self.offset+10]
        self.labels={display_text(f'{self.offset+i+1}. {label[:38]}'):key for i,(key,label) in enumerate(page)}
        labels=list(self.labels) or ['No items']
        self.menu['items']=labels
        index=next((i for i,label in enumerate(labels) if self.labels.get(label)==self.selected),0)
        self.menu.set(index,fCommand=0)
        self.count['text']=f'{self.offset+1 if page else 0}–{self.offset+len(page)} of {len(self.items)}'
        self.ui.enabled(self.previous,self.offset>0)
        self.ui.enabled(self.next,self.offset+10<len(self.items))

    def move(self, direction):
        offset=self.offset+direction*10
        if not 0<=offset<len(self.items):return
        self.offset=offset;self.selected=self.items[offset][0];self.render();self.changed(self.selected)

    def choose(self,label):
        if label in self.labels:
            self.selected=self.labels[label];self.changed(self.selected)


class RadioPanel:
    NAMES=('Connection','Chat','Contacts','Channels','Device','Tools')

    def __init__(self, ui, parent):
        self.ui=ui;self.app=ui.app;self.state={};self.connected=False;self.active='Connection'
        self.pending={};self.write_buttons=[];self.read_buttons=[];self.confirmation=None
        self.chat_route='Channels';self.conversation=None;self.messages=[];self.unread={};self.drafts={}
        self.activity=deque(maxlen=60);self.device_info=None;self.contact_filter=''
        self.contact_mode='Saved';self.channel_selected=None;self.chat_selected=None
        self.tabs={name:ui.button(parent,name,18+i*66,105,64,lambda n=name:self.page(n)) for i,name in enumerate(self.NAMES)}
        for tab in self.tabs.values():tab['text_scale']=10.5
        self.pages={name:DirectFrame(parent=parent,frameColor=(0,0,0,0)) for name in self.NAMES}
        self.pages['Connection'].setZ(-36)
        ui.build_radio(self.pages['Connection'])
        self.build_chat(self.pages['Chat']);self.build_contacts(self.pages['Contacts'])
        self.build_channels(self.pages['Channels']);self.build_device(self.pages['Device']);self.build_tools(self.pages['Tools'])
        self.status=ui.label(parent,'Connect a radio to use chat and device tools.',18,641,11,396)
        self.page('Connection');self.refresh_enabled()

    def button(self,parent,text,x,y,width,action,write=True):
        button=self.ui.button(parent,text,x,y,width,action)
        (self.write_buttons if write else self.read_buttons).append(button)
        return button

    def page(self,name):
        self.ui.blur();self.active=name
        for key,frame in self.pages.items():
            frame.show() if key==name else frame.hide()
            self.tabs[key]['frameColor']=(.14,.34,.37,1) if key==name else (.07,.16,.19,1)
        if name!='Connection' and self.connected and not self.state.get('loaded') and not self.state.get('loading'):
            self.request('refresh')
        if name=='Chat' and self.conversation:self.load_history()

    def connection(self,event):
        self.connected=event['state']=='connected'
        if not self.connected:
            self.confirmation=None
            self.status['text']='Radio disconnected. Saved chat remains visible; sending is disabled.'
        elif self.active!='Connection':self.request('refresh')
        self.refresh_enabled()

    def refresh_enabled(self):
        ready=self.connected and self.state.get('supported',False) and self.state.get('loaded',False)
        write=ready and self.state.get('writable',False)
        for button in self.write_buttons:self.ui.enabled(button,write)
        for button in self.read_buttons:self.ui.enabled(button,self.connected and self.state.get('supported',False))
        if hasattr(self,'older_button'):
            self.ui.enabled(self.older_button,bool(self.state.get('rx')))
            self.ui.enabled(self.latest_button,bool(self.state.get('rx')))
        if hasattr(self,'send_button'):self.ui.enabled(self.send_button,write and bool(self.chat_selected) and not any(p['action']=='send' for p in self.pending.values()))

    def request(self,action,**data):
        if not self.connected and not (action=='history' and self.state.get('rx')):
            self.status['text']='Connect a radio first.';return
        if action=='refresh' and any(p['action']=='refresh' for p in self.pending.values()):return
        try:
            request=self.app.service.radio_request(action,**data)
            # Passwords/channel keys are never retained in UI request tracking.
            self.pending[request]=dict(action=action,text=data.get('text') if action=='send' else None,
                                       conversation=self.conversation)
            if action not in ('history',):self.status['text']='Working…'
            self.refresh_enabled()
        except ValueError as exc:self.status['text']=display_text(str(exc))

    def confirm(self,token,description,action):
        now=time.monotonic()
        if self.confirmation and self.confirmation[0]==token and self.confirmation[1]>now:
            self.confirmation=None;action()
        else:
            self.confirmation=(token,now+8)
            self.status['text']=display_text(description+' Click again within 8s to confirm.')

    def build_chat(self,parent):
        u=self.ui
        self.route_menu=u.menu(parent,['Channels','Direct messages'],24,151,236,self.change_route)
        self.button(parent,'Refresh',278,151,136,lambda:self.request('refresh'),False)
        self.chat_picker=Picker(u,parent,191,self.choose_chat)
        self.transcript=DirectScrolledFrame(parent=parent,frameSize=(0,396,-220,0),
            canvasSize=(0,374,-220,0),frameColor=(.025,.095,.115,1),scrollBarWidth=12,
            pos=(18,0,-246),autoHideScrollBars=True)
        self.transcript_label=u.label(self.transcript.getCanvas(),'Choose a channel or contact.',10,20,12,350)
        self.older_button=self.button(parent,'Older messages',18,493,190,self.older,False)
        self.latest_button=self.button(parent,'Latest',224,493,190,self.load_history,False)
        DirectFrame(parent=parent,frameSize=(0,396,-60,0),frameColor=(.07,.15,.18,1),pos=(18,0,-516))
        self.composer=u.entry(parent,'',24,533,376)
        self.composer['numLines']=3;self.composer['frameSize']=(-.3,376/14+.3,-2.65,1.2)
        self.composer['command']=lambda _:None
        self.chat_hint=u.label(parent,'UTF-8 limit: 160 bytes · sends only when clicked',18,587,11,396)
        self.send_button=self.button(parent,'Send',282,615,132,self.send)
        self.chat_summary=u.label(parent,'Local history · no automatic retries',18,615,11,250)

    def change_route(self,label):
        if hasattr(self,'composer') and self.conversation:self.drafts[self.conversation]=self.composer.get()
        self.chat_route=label
        if hasattr(self,'chat_picker'):self.populate_chat()

    def populate_chat(self):
        if self.chat_route=='Channels':
            items=[(f"channel:{c['index']}:{c['identity']}",f"{c['index']}: {c['name'] or '(unnamed)'}")
                   for c in sorted(self.state.get('channels',[]),key=lambda c:c['index']) if c['occupied']]
        else:
            grouped={}
            for c in self.state.get('contacts',[]):grouped.setdefault(c['key'][:12],[]).append(c)
            items=[]
            known=set()
            for prefix,contacts in grouped.items():
                label=(contacts[0]['name'] or prefix) if len(contacts)==1 else 'Ambiguous prefix '+prefix
                items.append(('dm:'+prefix,label));known.add('dm:'+prefix)
            items.extend((c,'Unknown sender '+c[3:]) for c in self.state.get('conversations',[]) if c.startswith('dm:') and c not in known)
            items.sort(key=lambda item:item[1].casefold())
        items=[(key,label+(f' [{self.unread[key]}]' if self.unread.get(key) else '')) for key,label in items]
        self.chat_picker.set_items(items)

    def choose_chat(self,key):
        if not hasattr(self,'composer'):return
        if self.conversation:self.drafts[self.conversation]=self.composer.get()
        self.conversation=key;self.chat_selected=key
        self.composer.enterText(self.drafts.get(key,''));self.messages=[]
        set_scrolled_text(self.transcript,self.transcript_label,'No messages in this conversation yet.')
        if key:self.load_history()
        self.refresh_enabled()

    def load_history(self):
        if self.conversation:
            self.unread.pop(self.conversation,None)
            self.request('history',conversation=self.conversation)
        self.update_badge()

    def older(self):
        if self.conversation and self.messages:
            self.request('history',conversation=self.conversation,before=self.messages[0]['id'])

    def send(self):
        # Keyboard shortcuts must obey the same in-flight guard as the button.
        if any(p['action']=='send' for p in self.pending.values()):return
        key=self.chat_selected
        if not key:return
        text=self.composer.get()
        if key.startswith('channel:'):
            self.request('send',route='channel',target=int(key.split(':')[1]),text=text)
        else:
            peers=[c for c in self.state.get('contacts',[]) if c['key'].startswith(key[3:])]
            if len(peers)!=1:
                self.status['text']='Save/refresh this contact first. Ambiguous prefixes cannot be sent to.';return
            self.request('send',route='direct',target=peers[0]['key'],text=text)

    def draw_history(self,event):
        if event['conversation']!=self.conversation:return
        self.messages=event['messages'];lines=[]
        for item in self.messages:
            stamp=datetime.fromtimestamp(item.get('timestamp') or item.get('received',0)).strftime('%m/%d %H:%M')
            who='You' if item['direction']=='out' else 'Received'
            if self.conversation.startswith('dm:') and item['direction']=='in':
                prefix=item.get('sender_prefix','')
                matches=[c for c in self.state.get('contacts',[]) if c['key'].startswith(prefix)]
                who=matches[0]['name'] if len(matches)==1 else prefix
            lines.append(display_text(f"{stamp} · {who} · {item['status']}"))
            lines.extend(textwrap.wrap(display_text(item['text']),width=45,replace_whitespace=False) or [''])
            lines.append('')
        rendered='\n'.join(lines) or 'No saved messages here.'
        set_scrolled_text(self.transcript,self.transcript_label,rendered,latest=not event.get('before'))
        self.chat_summary['text']=f"{len(self.messages)} messages · {'earlier page' if event.get('before') else 'latest'}"

    def build_contacts(self,parent):
        u=self.ui
        self.contact_mode_menu=u.menu(parent,['Saved','Discovered'],24,151,236,self.change_contact_mode)
        self.button(parent,'Refresh',278,151,136,lambda:self.request('contacts'),False)
        self.contact_search=u.entry(parent,'',24,190,270)
        self.button(parent,'Search',310,190,104,self.search_contacts,False)
        self.contact_picker=Picker(u,parent,232,self.choose_contact)
        self.contact_detail=u.label(parent,'Select a contact. Names are not identities.',18,301,12,396)
        u.label(parent,'Local contact name',18,363,12)
        self.contact_name=u.entry(parent,'',24,391,270)
        self.button(parent,'Save / Add',310,391,104,self.save_contact)
        self.favorite_button=self.button(parent,'Favorite',18,434,124,self.favorite)
        self.button(parent,'Reset route',154,434,124,lambda:self.contact_action('reset_path'))
        self.button(parent,'Remove',290,434,124,self.remove_contact)
        self.button(parent,'Share on air',18,474,124,lambda:self.contact_action('share_contact'))
        self.button(parent,'Export URL',154,474,124,lambda:self.contact_action('export_contact'),False)
        self.button(parent,'Message',290,474,124,self.message_contact,False)
        u.label(parent,'Contact URL / advertisement hex (import or export)',18,510,12)
        self.contact_uri=u.entry(parent,'',24,540,376)
        self.button(parent,'Import contact',18,584,190,lambda:self.request('import_contact',uri=self.contact_uri.get()))
        u.label(parent,'Ctrl+C copies a field; Ctrl+V pastes; Ctrl+Shift+V replaces.\nDiscovered nodes are added only when you choose Save / Add.',18,615,11,396)

    def change_contact_mode(self,label):
        self.contact_mode=label
        if hasattr(self,'contact_picker'):self.populate_contacts()

    def search_contacts(self):
        self.contact_filter=self.contact_search.get().casefold().strip();self.populate_contacts()

    def contact_items(self):return self.state.get('contacts' if self.contact_mode=='Saved' else 'discovered',[])

    def populate_contacts(self):
        items=sorted(self.contact_items(),key=lambda c:(not(c['flags']&1),c['name'].casefold(),c['key']))
        self.contact_picker.set_items([(c['key'],('* ' if c['flags']&1 else '')+(c['name'] or 'Unnamed')+' · '+c['key'][:8])
                                      for c in items if self.contact_filter in (c['name']+' '+c['key']).casefold()])

    def selected_contact(self):return next((c for c in self.contact_items() if c['key']==self.contact_picker.selected),None)

    def choose_contact(self,key,fill=True):
        if not hasattr(self,'contact_name'):return
        item=self.selected_contact()
        if not item:
            self.contact_detail['text']='No matching contacts. Advertisements populate Discovered.';return
        types={1:'Chat node',2:'Repeater',3:'Room server',4:'Sensor'}
        path='flood / unknown' if item['path_length']==255 else item['path'] or 'direct / zero hop'
        self.contact_detail['text']=display_text(f"{types.get(item['type'],'Node')} · {item['key'][:32]}\n{item['key'][32:]}\nRoute: {path[:50]} · {item['lat']:.4f}, {item['lon']:.4f}")
        if fill:self.contact_name.enterText(editable_name(item['name']))
        self.favorite_button['text']='Unfavorite' if item['flags']&1 else 'Favorite'

    def save_contact(self):
        if self.selected_contact():self.request('save_contact',key=self.contact_picker.selected,name=self.contact_name.get())

    def favorite(self):
        item=self.selected_contact()
        if item:self.request('save_contact',key=item['key'],flags=item['flags']^1)

    def contact_action(self,action):
        if self.selected_contact():self.request(action,key=self.contact_picker.selected)

    def remove_contact(self):
        item=self.selected_contact()
        if item:self.confirm(('remove',item['key']),f"Remove {item['name'] or item['key'][:12]} from the radio?",lambda:self.contact_action('remove_contact'))

    def message_contact(self):
        item=self.selected_contact()
        if not item:return
        self.route_menu.set('Direct messages');self.chat_picker.selected='dm:'+item['key'][:12]
        self.populate_chat();self.chat_picker.render();self.choose_chat(self.chat_picker.selected);self.page('Chat')

    def build_channels(self,parent):
        u=self.ui
        u.label(parent,'CHANNEL SLOTS',18,151,12)
        self.button(parent,'Refresh',278,151,136,lambda:self.request('refresh'),False)
        self.channel_picker=Picker(u,parent,191,self.choose_channel)
        self.channel_detail=u.label(parent,'Select an occupied or empty radio slot.',18,270,12,396)
        u.label(parent,'Channel name',18,315,12)
        self.channel_name=u.entry(parent,'',24,345,376)
        u.label(parent,'Private key · 32 hex characters',18,388,12)
        self.channel_secret=u.entry(parent,'',24,418,376);self.channel_secret['obscured']=True
        u.label(parent,'#hashtag names derive the standard shared key.\nPrivate names need a key supplied by the channel owner.\nExisting keys are never displayed or saved on this PC.',18,464,12,396)
        self.button(parent,'Save channel',18,545,190,self.save_channel)
        self.button(parent,'Clear slot',224,545,190,self.clear_channel)
        u.label(parent,'Replacing or clearing a populated slot needs a second click.\nChanging #loragotchi-dx affects aquarium chat reception.',18,596,12,396)

    def choose_channel(self,key):
        if not hasattr(self,'channel_name'):return
        self.channel_selected=key
        item=next((c for c in self.state.get('channels',[]) if c['index']==key),None)
        if item:
            self.channel_name.enterText(editable_name(item['name']));self.channel_secret.enterText('')
            self.channel_detail['text']=display_text(f"Slot {key} · {'configured' if item['occupied'] else 'empty'} · {item['name'] or 'no name'}")

    def save_channel(self):
        index=self.channel_selected
        if index is None:return
        name,secret=self.channel_name.get().strip(),self.channel_secret.get().strip()
        def save():
            self.request('channel',index=index,name=name,secret=secret);self.channel_secret.enterText('')
        item=next(c for c in self.state['channels'] if c['index']==index)
        if item['occupied']:self.confirm(('channel',index,name,secret),'Replace the selected channel?',save)
        else:save()

    def clear_channel(self):
        index=self.channel_selected
        if index is not None:self.confirm(('clear_channel',index),'Clear the selected radio channel?',lambda:self.request('clear_channel',index=index))

    def build_device(self,parent):
        u=self.ui
        self.device_summary=u.label(parent,'Radio information will appear after synchronization.',18,152,12,396)
        self.button(parent,'Refresh',278,207,136,lambda:self.request('refresh'),False)
        u.label(parent,'Node name',18,249,12)
        self.node_name=u.entry(parent,'',24,279,270)
        self.button(parent,'Save name',310,279,104,lambda:self.request('name',name=self.node_name.get()))
        for title,x in [('MHz',18),('kHz BW',123),('SF',228),('CR',320)]:u.label(parent,title,x,320,12)
        self.frequency=u.entry(parent,'',24,350,88);self.bandwidth=u.entry(parent,'',129,350,88)
        self.sf=u.entry(parent,'',234,350,66);self.cr=u.entry(parent,'',326,350,74)
        self.button(parent,'Apply RF settings',18,393,222,self.save_rf)
        self.power=u.entry(parent,'',254,393,54)
        self.button(parent,'Set dBm',322,393,92,lambda:self.request('power',power=self.power.get()))
        u.label(parent,'Latitude / Longitude',18,431,12)
        self.lat=u.entry(parent,'',24,462,126);self.lon=u.entry(parent,'',172,462,126)
        self.button(parent,'Set GPS',322,462,92,lambda:self.request('location',lat=self.lat.get(),lon=self.lon.get()))
        self.autoadd=u.menu(parent,['Manual contacts','Auto-add contacts'],24,508,184,lambda _:None)
        self.location_policy=u.menu(parent,['Hide advert GPS','Share advert GPS','Use radio GPS policy'],226,508,174,lambda _:None)
        self.button(parent,'Save preferences',18,553,190,lambda:self.request('preferences',manual_add=int(self.autoadd.get()=='Manual contacts'),location_policy=self.location_policy['items'].index(self.location_policy.get())))
        self.button(parent,'Sync clock',224,553,190,lambda:self.request('clock'))
        self.button(parent,'Advertise: local',18,602,190,lambda:self.request('advert',flood=False))
        self.button(parent,'Advertise: flood',224,602,190,lambda:self.request('advert',flood=True))

    def save_rf(self):
        data=dict(frequency=self.frequency.get(),bandwidth=self.bandwidth.get(),sf=self.sf.get(),cr=self.cr.get())
        self.confirm(('rf',tuple(data.values())),'Apply RF settings to the radio?',lambda:self.request('radio',**data))

    def fill_device(self,info,device):
        if not info or info==self.device_info:return
        previous=self.device_info or {}
        self.device_info=dict(info)
        self.device_summary['text']=display_text(f"{info.get('name','Radio')} · {device.get('model','')}\n{device.get('version','')} · {info.get('battery_mv','?')} mV · {info.get('storage_used_kb','?')}/{info.get('storage_total_kb','?')} KB\n{info.get('key','')[:48]}")
        for key,field in [('name',self.node_name),('frequency',self.frequency),('bandwidth',self.bandwidth),('sf',self.sf),('cr',self.cr),('power',self.power),('lat',self.lat),('lon',self.lon)]:
            if not field['focus'] and previous.get(key)!=info.get(key):field.enterText(editable_name(str(info.get(key,''))))
        if previous.get('manual_add')!=info.get('manual_add'):self.autoadd.set(0 if info.get('manual_add') else 1,fCommand=0)
        if previous.get('location_policy')!=info.get('location_policy'):self.location_policy.set(min(2,info.get('location_policy',0)),fCommand=0)

    def build_tools(self,parent):
        u=self.ui
        u.label(parent,'REMOTE NODE / REPEATER / ROOM',18,151,12)
        self.tools_picker=Picker(u,parent,191,lambda _:None)
        u.label(parent,'Login password (not saved)',18,267,12)
        self.password=u.entry(parent,'',24,297,230);self.password['obscured']=True
        self.button(parent,'Login',272,297,66,self.login)
        self.button(parent,'Logout',348,297,66,lambda:self.remote('logout'))
        self.button(parent,'Status',18,340,124,lambda:self.remote('status'))
        self.button(parent,'Telemetry',154,340,124,lambda:self.remote('telemetry'))
        self.button(parent,'Find route',290,340,124,lambda:self.remote('discover_path'))
        u.label(parent,'Remote command (requires appropriate login)',18,378,12)
        self.remote_command=u.entry(parent,'',24,408,270)
        self.button(parent,'Send',310,408,104,lambda:self.remote('command',text=self.remote_command.get()))
        u.label(parent,'Manual route · hex hop hashes / bytes per hop',18,449,12)
        self.route_path=u.entry(parent,'',24,479,240)
        self.path_width=u.menu(parent,['1','2','3'],284,479,40,lambda _:None)
        self.button(parent,'Set path',338,479,76,lambda:self.remote('save_contact',path=self.route_path.get(),path_width=int(self.path_width.get())))
        self.button(parent,'Local radio statistics',18,524,396,lambda:self.request('stats'),False)
        self.activity_frame=DirectScrolledFrame(parent=parent,frameSize=(0,396,-80,0),canvasSize=(0,374,-80,0),
            frameColor=(.025,.095,.115,1),scrollBarWidth=12,pos=(18,0,-549),autoHideScrollBars=True)
        self.activity_label=u.label(self.activity_frame.getCanvas(),'Activity: remote replies and diagnostics appear here.',8,16,11,350)

    def remote(self,action,**data):
        if self.tools_picker.selected:self.request(action,key=self.tools_picker.selected,**data)

    def login(self):
        self.remote('login',password=self.password.get());self.password.enterText('')

    def update_badge(self):
        total=sum(self.unread.values());self.tabs['Chat']['text']='Chat'+(f' ({min(total,99)})' if total else '')

    def refresh_hint(self):
        limit=160 if self.chat_route=='Direct messages' else 158-len(self.state.get('info',{}).get('name','').encode('utf-8'))
        count=len(self.composer.get().encode('utf-8'))
        self.app.set_ui_text(self.chat_hint,f'{count}/{limit} UTF-8 bytes · Ctrl+Enter sends')

    def on_event(self,event):
        kind=event['kind']
        if kind=='radio_state':
            if self.state.get('rx')!=event['rx']:
                self.messages=[];self.conversation=None;self.chat_selected=None;self.unread.clear();self.drafts.clear()
                set_scrolled_text(self.transcript,self.transcript_label,'No messages selected.')
                self.composer.enterText('');self.device_info=None
                self.contact_uri.enterText('');self.password.enterText('');self.channel_secret.enterText('')
            self.state=event
            self.populate_chat();self.populate_contacts()
            self.choose_contact(self.contact_picker.selected,fill=False)
            self.channel_picker.set_items([(c['index'],f"Slot {c['index']} · {c['name'] or '(empty)'}") for c in sorted(event['channels'],key=lambda c:c['index'])])
            selected=next((c for c in event['channels'] if c['index']==self.channel_selected),None)
            if selected:self.channel_detail['text']=display_text(f"Slot {selected['index']} · {'configured' if selected['occupied'] else 'empty'} · {selected['name'] or 'no name'}")
            self.tools_picker.set_items([(c['key'],c['name']+' · '+c['key'][:8]) for c in sorted(event['contacts'],key=lambda c:c['name'].casefold())])
            self.fill_device(event['info'],event['device'])
            if not event['supported']:self.status['text']='Bluetooth MTU too small for chat/contacts. Use USB; fish intake still works.'
            elif event['loaded'] and not event['writable']:self.status['text']='LAN bridge is read-only. Enable --radio-control on the bridge for writes.'
            self.refresh_enabled()
        elif kind=='radio_history':self.draw_history(event)
        elif kind=='radio_message':
            key=event['conversation']
            if key not in self.state.get('conversations',[]):self.state.setdefault('conversations',[]).append(key)
            if key!=self.conversation or self.active!='Chat' or self.ui.active_page!='Radio':
                self.unread[key]=self.unread.get(key,0)+1
            self.populate_chat();self.update_badge()
        elif kind=='radio_export':self.contact_uri.enterText(event['text'])
        elif kind in ('radio_notice','radio_result'):
            text=event.get('text','')
            if text:
                self.status['text']=display_text(textwrap.fill(text,70,max_lines=2,placeholder='…'))
                self.activity.append(text)
                lines=[]
                for value in self.activity:
                    lines.extend(textwrap.wrap(display_text(value),54));lines.append('')
                set_scrolled_text(self.activity_frame,self.activity_label,'\n'.join(lines))
            if kind=='radio_result':
                request=self.pending.pop(event['id'],{})
                if event['ok'] and request.get('action')=='send':
                    key=request.get('conversation')
                    if key==self.conversation and self.composer.get()==request.get('text'):self.composer.enterText('')
                    if self.drafts.get(key)==request.get('text'):self.drafts.pop(key,None)
                self.refresh_enabled()
