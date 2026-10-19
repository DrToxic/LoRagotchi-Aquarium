"""Native third-tab editor: window management and percentage-based keep-outs."""
from dataclasses import replace
from panda3d.core import LineSegs, Point3
from direct.gui.DirectGui import DirectFrame
from direct.gui import DirectGuiGlobals as DGG
from .deadzones import Deadzone, SHAPES, MAX_ZONES, MAX_WINDOWS


class DeadzonePanel:
    def __init__(self, controls, parent):
        self.controls=controls;self.app=controls.app
        self.selected=None;self.selected_view=0;self.outlines=False;self.overlay_nodes=[]
        c=controls
        c.label(parent,'WINDOWS & SWIMMING AREA',18,105,12)
        self.window_menu=c.menu(parent,['View 1 (main)'],24,137,226,self.choose_window)
        self.add_button=c.button(parent,'Add',270,137,66,self.add_window)
        self.close_button=c.button(parent,'Close',346,137,68,self.close_window)
        c.button(parent,'Save layout',18,178,120,self.save_layout)
        c.button(parent,'Fullscreen',150,178,126,self.fullscreen)
        self.bounds_button=c.button(parent,'Edges: on',288,178,126,self.toggle_bounds)
        self.preview=DirectFrame(parent=parent,frameSize=(0,396,-124,0),pos=(18,0,-197),
                                 frameColor=(.008,.025,.035,1),state=DGG.NORMAL)
        self.preview.bind(DGG.B1PRESS,self.place)
        self.preview_nodes=self.preview.attachNewNode('layout-preview')
        c.button(parent,'<',18,350,30,lambda:self.cycle(-1))
        self.zone_label=c.label(parent,'New deadzone',60,350,14)
        c.button(parent,'>',252,350,30,lambda:self.cycle(1))
        c.button(parent,'New zone',294,350,120,self.new)
        self.shape=c.menu(parent,list(SHAPES),24,388,376,lambda _:None)
        self.fields=[]
        for text,x,value in (('Left %',24,35),('Top %',122,35),('Width %',220,30),('Height %',318,30)):
            c.label(parent,text,x,420,12)
            self.fields.append(c.entry(parent,str(value),x,447,80))
        c.button(parent,'Apply',18,487,120,self.apply)
        self.enabled_button=c.button(parent,'Enabled: on',150,487,126,self.toggle_enabled)
        self.delete_button=c.button(parent,'Delete',288,487,126,self.delete)
        self.outlines_button=c.button(parent,'Outlines: off',18,530,126,self.toggle_outlines)
        c.label(parent,'Click preview to place the zone; then Apply.',154,528,11,252)
        self.note=c.label(parent,'Teal = windows. Dark = gaps. Coral = deadzones.\nPercentages cover the whole layout; zones save on Apply.',18,559,12,396)
        self.draft_enabled=True
        self.refresh_windows();self.show_selected()

    def choose_window(self,label):
        if hasattr(self,'window_ids') and label in self.window_ids:
            self.selected_view=self.window_ids[label]
            self.controls.enabled(self.close_button,self.selected_view!=0)
            self.redraw()

    def refresh_windows(self,selected=None):
        if selected is not None:self.selected_view=selected
        self.window_ids={f'View {v.view_id+1}'+(' (main)' if v.primary else ''):v.view_id for v in self.app.views}
        if self.selected_view not in self.window_ids.values():self.selected_view=0
        self.window_menu['items']=list(self.window_ids)
        self.window_menu.set(next(k for k,v in self.window_ids.items() if v==self.selected_view),fCommand=0)
        self.controls.enabled(self.close_button,self.selected_view!=0)
        self.controls.enabled(self.add_button,len(self.app.views)<MAX_WINDOWS)
        self.bounds_button['text']='Edges: '+('on' if self.app.display.constrain else 'off')
        self.redraw()

    def view(self):return next(v for v in self.app.views if v.view_id==self.selected_view)
    def add_window(self):self.app.add_window()
    def close_window(self):self.app.close_view(self.view())
    def fullscreen(self):self.app.fullscreen(self.view().window)
    def save_layout(self):
        if self.app.save_display(windows=True):self.note['text']='Window positions and sizes saved for the next launch.\nUse --wall-columns 1 to ignore a saved window layout.'
        else:self.note['text']=self.app.status
    def persist(self):
        if not self.app.save_display():self.note['text']=self.app.status
        self.redraw()
    def toggle_bounds(self):
        self.app.display.constrain=not self.app.display.constrain
        self.bounds_button['text']='Edges: '+('on' if self.app.display.constrain else 'off')
        self.persist()
        self.note['text']='Fish stay inside visible window areas.' if self.app.display.constrain else 'Edge protection off: fish may cross invisible desktop gaps.\nEnabled deadzones still apply.'
    def toggle_outlines(self):
        self.outlines=not self.outlines
        self.outlines_button['text']='Outlines: '+('on' if self.outlines else 'off')
        self.redraw()
    def new(self):self.selected=None;self.show_selected()
    def cycle(self,direction):
        n=len(self.app.display.zones)
        if n:self.selected=((self.selected if self.selected is not None else (-1 if direction>0 else 0))+direction)%n
        self.show_selected()
    def show_selected(self):
        zones=self.app.display.zones
        zone=zones[self.selected] if self.selected is not None else Deadzone()
        self.zone_label['text']=f'Deadzone {self.selected+1} / {len(zones)}' if self.selected is not None else f'New deadzone ({len(zones)}/{MAX_ZONES})'
        self.shape.set(zone.shape,fCommand=0)
        for field,value in zip(self.fields,(zone.x,zone.y,zone.width,zone.height)):field.enterText(f'{value:g}')
        self.draft_enabled=zone.enabled
        self.enabled_button['text']='Enabled: '+('on' if zone.enabled else 'off')
        self.controls.enabled(self.delete_button,self.selected is not None)
        self.redraw()
    def apply(self):
        try:
            zone=Deadzone(self.shape.get(),*(float(f.get()) for f in self.fields),enabled=self.draft_enabled)
            if self.selected is None:
                if len(self.app.display.zones)>=MAX_ZONES:raise ValueError(f'Maximum {MAX_ZONES} zones. Edit or delete one first.')
                self.app.display.zones.append(zone);self.selected=len(self.app.display.zones)-1
            else:self.app.display.zones[self.selected]=zone
        except (ValueError,TypeError) as error:
            self.note['text']=str(error) if str(error).startswith(('Use ','Choose ','Coordinates','Maximum')) else 'Enter numbers for Left, Top, Width and Height.'
            return
        self.note['text']='Deadzone applied. Move/resize windows normally.\nFish hidden by a layout change return to visible water.'
        self.persist();self.show_selected()
    def toggle_enabled(self):
        self.draft_enabled=not self.draft_enabled
        self.enabled_button['text']='Enabled: '+('on' if self.draft_enabled else 'off')
        if self.selected is not None:
            self.app.display.zones[self.selected]=replace(self.app.display.zones[self.selected],enabled=self.draft_enabled)
            self.persist()
    def delete(self):
        if self.selected is not None:
            self.app.display.zones.pop(self.selected);self.selected=None;self.persist();self.show_selected()
    def place(self,event):
        watcher=self.app.mouseWatcherNode
        if not watcher.hasMouse():return
        mouse=watcher.getMouse()
        local=self.preview.getRelativePoint(self.app.render2d,Point3(mouse.x,0,mouse.y))
        left,top,width,height=self.preview_map
        px=(local.x-left)/width;py=(-local.z-top)/height
        if not (0<=px<=1 and 0<=py<=1):return
        try:w,h=float(self.fields[2].get()),float(self.fields[3].get())
        except ValueError:return
        self.fields[0].enterText(f'{max(0,min(100-w,px*100-w/2)):.1f}')
        self.fields[1].enterText(f'{max(0,min(100-h,py*100-h/2)):.1f}')
        self.note['text']='Draft position changed. Apply to move or create the zone.'

    @staticmethod
    def lines(parent,points,color,width=2):
        pen=LineSegs();pen.setThickness(width);pen.setColor(*color)
        for i,(x,y) in enumerate(points):
            (pen.moveTo if i==0 else pen.drawTo)(x,0,y)
        node=parent.attachNewNode(pen.create());node.setDepthTest(False);node.setDepthWrite(False)
        return node

    def redraw(self):
        for node in self.overlay_nodes:node.removeNode()
        self.overlay_nodes=[]
        self.preview_nodes.removeNode();self.preview_nodes=self.preview.attachNewNode('layout-preview')
        rectangles=[v.rectangle() for v in self.app.views]
        if not rectangles:return
        left=min(r[0] for r in rectangles);top=min(r[1] for r in rectangles)
        width=max(x+w for x,y,w,h in rectangles)-left;height=max(y+h for x,y,w,h in rectangles)-top
        if width<=0 or height<=0:return
        scale=min(380/width,108/height);pw,ph=width*scale,height*scale
        px,py=(396-pw)/2,(124-ph)/2;self.preview_map=(px,py,pw,ph)
        for view,(x,y,w,h) in zip(self.app.views,rectangles):
            x0,x1=px+(x-left)*scale,px+(x+w-left)*scale
            y0,y1=-py-(y-top)*scale,-py-(y+h-top)*scale
            # Geometry-only preview children don't intercept parent clicks.
            from panda3d.core import CardMaker
            maker=CardMaker('view-area');maker.setFrame(x0,x1,y1,y0)
            node=self.preview_nodes.attachNewNode(maker.generate());node.setColor(.07,.22,.25,1)
            self.lines(self.preview_nodes,[(x0,y0),(x1,y0),(x1,y1),(x0,y1),(x0,y0)],
                       (.35,.85,.82,1) if view.view_id==self.selected_view else (.20,.46,.48,1))
        for i,zone in enumerate(self.app.display.zones):
            points=zone.outline(width/height)
            color=(1.,.55,.38,1) if zone.enabled else (.43,.44,.45,1)
            self.lines(self.preview_nodes,[(px+(u+1)*pw/2,-py-(1-v)*ph/2) for u,v in points],color,3 if i==self.selected else 1.5)
            if self.outlines and zone.enabled:
                for view,(x,y,w,h) in zip(self.app.views,rectangles):
                    local=[(2*(left+(u+1)*width/2-x)/w-1,1-2*(top+(1-v)*height/2-y)/h) for u,v in points]
                    self.overlay_nodes.append(self.lines(view.root,local,color))
