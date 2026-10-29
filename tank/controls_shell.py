"""Resizable native operator shell. Controllers retain their own save boundaries."""
from panda3d.core import TextNode
from direct.gui.DirectGui import DirectFrame, DirectScrolledFrame, DirectSlider
from .settings import PRESETS
from .text import display_text

NAVIGATION = {
    'Overview': ('Aquarium',), 'Appearance': ('Appearance', 'Themes'),
    'Scenery & motion': ('Decorations', 'Animations', 'Transfers'),
    'Fish & nursery': ('Nursery', 'Lifespan'), 'Windows & layout': ('Deadzones',),
    'Radio & chat': ('Radio',), 'Games': ('Games',), 'Performance': ('Performance',),
}
TITLES = {'Aquarium':'Overview','Themes':'Theme library','Decorations':'Scenery & motion',
          'Animations':'Scenery & motion','Transfers':'Scenery & motion',
          'Nursery':'Fish & nursery','Lifespan':'Fish & nursery','Deadzones':'Windows & layout',
          'Radio':'Radio & chat','Performance':'Performance','Appearance':'Appearance','Games':'Games'}
SUBTITLES = {
    'Aquarium':'Your display session at a glance', 'Appearance':'Shape the look of your aquarium',
    'Themes':'Import, export and save reusable looks · library actions are separate',
    'Decorations':'Scenery choices save immediately · Auto / Pinned stays per object',
    'Animations':'Arrival and departure choices save immediately',
    'Transfers':'Display-only travel · saves separately from appearance',
    'Nursery':'Local eggs and pairing · Save nursery settings is separate',
    'Lifespan':'Display-copy expiry · Apply lifespan is separate',
    'Deadzones':'Save layout remembers windows · deadzone Apply saves its own edits',
    'Radio':'Connection, chat and advanced device writes · no automatic connection',
    'Games':'Manual direct-chat packets · nothing is sent automatically',
    'Performance':'Graphics budgets and output details · separate save scopes',
}

class ControlsShell:
    def make_page(self):
        frame=DirectFrame(parent=self.viewport.getCanvas(),frameColor=(0,0,0,0))
        frame.setZ(90)  # Established controller y=105 becomes viewport y=15.
        return frame

    def build_shell(self):
        self.root=DirectFrame(parent=self.app.pixel2d,frameColor=(.035,.09,.105,1),frameSize=(0,1100,-800,0))
        from .projection import configure_overlay_bins
        configure_overlay_bins();self.root.setBin('projector-controls',0,100)
        self.top=DirectFrame(parent=self.root,frameColor=(.08,.17,.19,1),frameSize=(0,1100,-48,0))
        self.label(self.top,'LoRagotchi Aquarium',24,30,16)
        self.top_caption=self.label(self.top,'NATIVE CONTROLS',846,30,11)
        self.minimize=None
        if not getattr(self.app,'streaming',False):self.minimize=self.button(self.top,'–',1044,27,32,self.app.toggle_panel)
        self.sidebar=DirectFrame(parent=self.root,frameColor=(.047,.13,.145,1),frameSize=(0,224,-800,-48))
        self.label(self.sidebar,'AQUARIUM',24,83,11)
        self.tabs={}
        for i,(name,targets) in enumerate(NAVIGATION.items()):
            button=self.button(self.sidebar,name,18,124+i*48,190,lambda n=targets[0]:self.page(n))
            button['text_align']=TextNode.ALeft;button['text_pos']=(14,0);button['text_scale']=14
            button['frameSize']=(0,190,-12,25);self.tabs[name]=button
        self.mode_badge=self.label(self.sidebar,'',24,715,12,180)
        self.sidebar_hint=self.label(self.sidebar,'Synthetic fish · No radio',24,741,11,180)
        self.draft_badge=self.label(self.root,'',856,93,12,210)
        self.heading=self.label(self.root,'Overview',254,94,27)
        self.subtitle=self.label(self.root,'',254,123,13,810)
        self.subnav=DirectFrame(parent=self.root,frameColor=(0,0,0,0),pos=(254,0,-151))
        self.viewport=DirectScrolledFrame(parent=self.root,frameSize=(0,820,-554,0),
            canvasSize=(0,800,-560,0),pos=(254,0,-180),scrollBarWidth=14,
            frameColor=(0,0,0,0),autoHideScrollBars=True,horizontalScroll_scrollSize=0,
            verticalScroll_scrollSize=.12)
        self.pages={name:self.make_page() for name in ('Aquarium','Radio','Deadzones','Decorations','Animations','Performance')}
        self._subbuttons=[];self._portrait_signature=None;self.portrait=None
        self.app.footer=self.label(self.root,'Starting aquarium…',254,765,11,815)
        self.app.accept('wheel_up',self.scroll_page,[-1]);self.app.accept('wheel_down',self.scroll_page,[1])

    def finish_shell(self):
        # Sidebar replaces obsolete Back links; all feature controls stay intact.
        for name in ('Themes','Nursery','Lifespan','Games'):
            for child in self.pages[name].getChildren():
                if child.getZ()==-105 and child.getName().startswith('DirectButton'):child.hide()
        self.context=DirectFrame(parent=self.viewport.getCanvas(),frameSize=(0,268,-350,0),
            pos=(532,0,-10),frameColor=(.08,.18,.205,1))
        self.context_title=self.label(self.context,'Separate save scopes',20,32,17,230)
        self.context_text=self.label(self.context,'',20,69,14,228)
        self.label(self.context,'No live device is required to explore.',20,315,12,230)
        self._close_dialog=None
        self.bind_scroll_inputs()
        self.app.win.setCloseRequestEvent('operator-close-request')
        self.app.accept('operator-close-request',self.request_close)

    def card(self,parent,x,y,w,h):
        return DirectFrame(parent=parent,pos=(x,0,-y),frameSize=(0,w,-h,0),frameColor=(.08,.185,.21,1))

    def build_overview(self,parent):
        a=self.app
        session=self.session_card=self.card(parent,0,100,800,88)
        self.label(session,'Display session',20,30,16)
        self.session_text=self.label(session,'Waiting for collection…',20,58,14,460)
        self.connection_summary=self.label(session,'No radio connected',410,32,12,365)
        self.label(parent,'Selected fish',0,220,19)
        self.label(parent,'The fish currently selected in this display',0,245,13)
        fish=self.card(parent,0,266,500,200)
        self.portrait_frame=self.card(fish,16,16,170,180)
        a.fish_label=self.label(fish,'No shared fish yet',205,43,18,275)
        self.fish_source=self.label(fish,'',205,103,12,275)
        self.button(fish,'Next fish',205,155,125,a.select_next)
        self.label(fish,'Click a fish in any aquarium to select it.',205,188,11,275)
        self.display_options=self.card(parent,532,266,268,200)
        self.label(self.display_options,'Display options',20,32,18)
        self.names_button=self.button(self.display_options,'Names',20,83,228,a.toggle_names)
        self.chat_button=self.button(self.display_options,'Channel chat',20,132,228,a.toggle_chat)
        self.label(self.display_options,'Display toggles are separate.\nChat is display-only while offline.',20,180,12,228)
        self.label(parent,'Session actions',0,505,18)
        self.button(parent,'Remove copy',0,547,154,a.remove_selected)
        a.end_button=self.button(parent,'End display session',168,547,332,a.end_session)
        self.label(parent,'Remove copy hides only the selected display copy.\nEnd session clears displayed copies; original pets are unchanged.',0,589,12,500)
        a.message_label=self.label(parent,'Inbox: no messages',0,630,12,500)
        a.clear_confirm=0

    def build_performance(self,parent):
        a=self.app
        self.label(parent,'Graphics budgets',18,115,19)
        self.label(parent,'Graphics preset · saves immediately',18,163,14)
        a.preset_menu=self.menu(parent,list(PRESETS),18,207,396,a.set_preset,
            list(PRESETS).index(a.settings.preset) if a.settings.preset in PRESETS else 2)
        self.label(parent,'Render scale · apply separately',18,259,14)
        a.scale_slider=DirectSlider(parent=parent,range=(.25,1.5),value=a.settings.scale,pageSize=.05,
            scale=140,pos=(218,0,-300),command=a.scale_label_update)
        a.scale_label=self.label(parent,'',18,341,13)
        self.button(parent,'Apply scale',18,391,190,a.apply_scale)
        self.button(parent,'Advanced budgets',224,391,190,self.show_quality)
        a.output_label=self.label(parent,'',18,448,14,460)
        self.label(parent,'Advanced quality has its own Apply & save.\nVSync changes need restart. UI stays at output resolution.',18,535,13,460)
        a.scale_label_update()

    def show_quality(self):
        self.page('Appearance');self.appearance.page('Quality')

    def navigate(self,name):
        aliases={key:targets[0] for key,targets in NAVIGATION.items()};name=aliases.get(name,name)
        if name not in self.pages:raise ValueError('Unknown controls page: '+name)
        self.blur()
        for key,frame in self.pages.items():frame.show() if key==name else frame.hide()
        self.active_page=name
        category=next(key for key,targets in NAVIGATION.items() if name in targets)
        for key,button in self.tabs.items():
            button['frameColor']=(.14,.30,.32,1) if key==category else (.047,.13,.145,1)
            button['text_fg']=(.93,.98,.95,1) if key==category else (.64,.76,.76,1)
        self.heading['text']=TITLES[name];self.heading.resetFrameSize()
        self.subtitle['text']=SUBTITLES[name];self.subtitle.resetFrameSize()
        for button in self._subbuttons:button.destroy()
        targets=[t for t in NAVIGATION[category] if t in self.pages]
        names={'Decorations':'Reef, plants & objects','Animations':'Arrivals & exits','Transfers':'Area travel',
               'Nursery':'Nursery','Lifespan':'Copy lifespan','Themes':'Theme library','Appearance':'Appearance editor'}
        self._subbuttons=[]
        if len(targets)>1:
            for i,target in enumerate(targets):
                button=self.button(self.subnav,names[target],i*183,0,176,lambda n=target:self.page(n))
                button['text_scale']=12;button['frameColor']=(.14,.30,.32,1) if target==name else (.08,.17,.19,1)
                self._subbuttons.append(button)
        if name=='Radio':self.radio.page(self.radio.active)
        if name=='Lifespan':self.expiry.refresh()
        if name=='Appearance':self.appearance.refresh_theme_choices();self.appearance.update_dirty()
        if name=='Themes':self.themes.refresh()
        if name=='Decorations':self.decorations.rebuild()
        if name=='Transfers':self.transfers.refresh()
        self.viewport.verticalScroll['value']=0;self.resize_shell()

    def refresh_shell(self):
        a=self.app
        if not hasattr(self,'active_page'):return
        mode=self.mode.upper();self.mode_badge['text']=mode+' MODE' if mode!='LIVE' else 'LIVE COLLECTION'
        self.sidebar_hint['text']=('Synthetic fish' if self.mode=='demo' else 'Recorded fish' if self.mode=='replay' else 'Saved live copies')+'\n'+('Connected' if self.state=='connected' else 'No radio connected')
        self.session_text['text']=f'{len(a.roster)} '+('synthetic' if self.mode=='demo' else 'recorded' if self.mode=='replay' else 'shared')+' fish displayed'
        self.connection_summary['text']=display_text(a.status)[:90]
        self.names_button['text']='Display names: '+('on' if a.show_names else 'off')
        self.chat_button['text']='Channel chat: '+('on' if a.settings.chat_bubbles else 'off')
        fish=a.roster[a.selected%len(a.roster)] if a.roster else None
        signature=(fish,a.settings.fish_style) if fish else None
        if signature!=self._portrait_signature:
            if self.portrait:self.portrait.removeNode();self.portrait=None
            if fish:
                from .art import fish_model
                self.portrait=fish_model(fish,18,a.settings.fish_style)[0]
                self.portrait.reparentTo(self.portrait_frame);self.portrait.setPos(83,-20,-90)
                self.portrait.setScale(62);self.portrait.setLightOff();self.portrait.setDepthTest(False);self.portrait.setDepthWrite(False)
            self._portrait_signature=signature
        self.fish_source['text']=('Synthetic display fish' if self.mode=='demo' else 'Recorded display fish' if self.mode=='replay' else 'Saved display copy') if fish else 'Select a fish when available.'
        self.appearance.update_dirty()
        self.draft_badge['text']='UNSAVED CHANGES' if self.appearance.dirty else ''
        self.draft_badge['text_fg']=(.88,.77,.52,1)
        self.appearance.refresh_preview()

    def request_close(self):
        self.appearance.update_dirty()
        if not self.appearance.dirty:self.app.userExit();return
        if self._close_dialog:return
        self.blur()
        self._close_dialog=DirectFrame(parent=self.root,frameColor=(.025,.06,.07,.98),frameSize=(0,self.app.win.getXSize(),-self.app.win.getYSize(),0),state='normal')
        self._close_dialog.setBin('gui-popup',0,102)
        card=self.card(self._close_dialog,245,210,510,190)
        self.label(card,'Discard unsaved appearance edits?',24,42,21,460)
        self.label(card,'Your applied settings are already saved. Pending edits\nwill be lost only if you choose Discard & quit.',24,82,14,460)
        self.button(card,'Keep editing',24,148,216,self.cancel_close)
        self.button(card,'Discard & quit',266,148,216,self.app.userExit)

    def cancel_close(self):
        if self._close_dialog:self._close_dialog.destroy();self._close_dialog=None

    def resize_shell(self):
        if not hasattr(self,'viewport'):return
        width=max(320,self.app.win.getXSize());height=max(320,self.app.win.getYSize())
        self.root.setScale(1);self.root.setPos(0,0,0)
        self.root['frameSize']=(0,width,-height,0);self.top['frameSize']=(0,width,-48,0)
        self.top_caption.setX(width-254)
        self.draft_badge.setX(max(254,width-220))
        if self.minimize:self.minimize.setX(width-56)
        self.sidebar['frameSize']=(0,224,-height,-48)
        for i,button in enumerate(self.tabs.values()):button.setZ(-(124+i*min(48,max(25,(height-160)/8))))
        self.mode_badge.hide() if height<570 else self.mode_badge.show()
        self.sidebar_hint.hide() if height<570 else self.sidebar_hint.show()
        self.mode_badge.setZ(-(height-62));self.sidebar_hint.setZ(-(height-38))
        self.app.footer.setPos(254,0,-(height-30))
        w=max(160,width-278);h=max(120,height-242)
        self.subtitle['text_wordwrap']=w/13;self.app.footer['text_wordwrap']=w/11
        self.viewport['frameSize']=(0,w,-h,0)
        for i,button in enumerate(self._subbuttons):
            bw=min(176,(w-20)/len(self._subbuttons));button.setX(i*(bw+4));button['frameSize']=(0,bw,-9,21);button['text_pos']=(bw/2,0);button['text_scale']=min(12,bw/14)
        if self._close_dialog:self._close_dialog['frameSize']=(0,width,-height,0)
        narrow=w<800;page=getattr(self,'active_page','Aquarium');content_height=580
        if page=='Aquarium':
            self.session_card['frameSize']=(0,500 if narrow else 800,-112 if narrow else -88,0)
            self.connection_summary.setPos(20 if narrow else 410,0,-(86 if narrow else 32))
            self.connection_summary['text_wordwrap']=(460 if narrow else 365)/12
            self.display_options.setPos(0 if narrow else 532,0,-(740 if narrow else 266))
            content_height=870 if narrow else 558
        elif page=='Appearance':
            h=max(120,height-368);self.viewport['frameSize']=(0,w,-h,0)
            content_height=self.appearance.resize(w,h)
        self.viewport['canvasSize']=(0,max(506,w-16),-max(h,content_height),0)
        self.appearance.actions.show() if page=='Appearance' else self.appearance.actions.hide()
        self.appearance.actions.setPos(254,0,-(height-175))
        self.appearance.actions['frameSize']=(0,max(506,w-16),-145,0)
        self.appearance.note['text_wordwrap']=max(490,w-16)/12
        self.appearance.scope['text_wordwrap']=max(490,w-16)/12
        if hasattr(self,'context'):
            self.context.hide() if narrow or page in ('Aquarium','Appearance') else self.context.show()
            self.context_text['text']={
                'Themes':'Load theme and Apply fish style save immediately.\n\nAppearance drafts are retained. Apply there changes only edited fields.\n\nSave current look saves the applied look, not pending edits.',
                'Radio':'Advanced writes stay disabled while disconnected.\n\nDevice confirmations and radio writes are separate from visual settings.',
                'Deadzones':'Save layout remembers window geometry.\n\nApply saves deadzone coordinates. Existing-zone switches save immediately.\n\nAppearance Apply never saves this page.',
                'Games':'Start or join, copy a turn, send in your own direct chat, then paste their reply.\n\nNo automatic transmission and no stakes.',
            }.get(page,'These controls keep their explicit-save or immediate-save behavior.\n\nAppearance Apply never saves radio, windows, nursery or game state.')
            self.context_text.resetFrameSize()

    def scroll_page(self,direction):
        if getattr(self,'_close_dialog',None):return
        if not self.app.mouseWatcherNode.hasMouse():return
        m=self.app.mouseWatcherNode.getMouse();x=(m.x+1)*self.app.win.getXSize()/2;y=(1-m.y)*self.app.win.getYSize()/2
        if x<254 or y<180:return
        target=self.viewport
        # Route nested scroll areas before the outer page, using actual screen bounds.
        from direct.gui.DirectGuiBase import DirectGuiWidget
        for scroller in list(DirectGuiWidget.guiDict.values()):
            if not isinstance(scroller,DirectScrolledFrame) or scroller==self.viewport or scroller.isHidden():continue
            point=self.app.pixel2d.getRelativePoint(scroller,(0,0,0));l,r,b,t=scroller['frameSize']
            if point.x+l<=x<=point.x+r and -point.z-t<=y<=-point.z-b:target=scroller;break
        target.verticalScroll['value']=max(0,min(1,target.verticalScroll['value']+direction*.12))

    def reveal_field(self,field):
        # Tab into a clipped field scrolls each containing canvas into view.
        from direct.gui.DirectGuiBase import DirectGuiWidget
        scrollers=[w for w in list(DirectGuiWidget.guiDict.values()) if isinstance(w,DirectScrolledFrame) and not w.isHidden() and w.getCanvas().isAncestorOf(field)]
        scrollers.sort(key=lambda w:len(w.getAncestors()),reverse=True)
        for frame in scrollers:
            p=frame.getCanvas().getRelativePoint(field,(0,0,0));_,_,bottom,top=frame['canvasSize']
            view=frame['frameSize'];height=view[3]-view[2];span=top-bottom-height
            if span>0:
                current=frame.verticalScroll['value']*span;y=-p.z
                if y<current+24:frame.verticalScroll['value']=max(0,(y-30)/span)
                elif y>current+height-24:frame.verticalScroll['value']=min(1,(y-height+35)/span)

    def bind_scroll_inputs(self):
        # PGEntry/PGButton suppress generic mouse events while hovered. Bind the
        # corresponding PGItem press events too, retaining normal wheel routing.
        from direct.gui.DirectGuiBase import DirectGuiWidget
        for widget in list(DirectGuiWidget.guiDict.values()):
            widget.bind('press-wheel_down-',lambda event:self.scroll_page(1))
            widget.bind('press-wheel_up-',lambda event:self.scroll_page(-1))
