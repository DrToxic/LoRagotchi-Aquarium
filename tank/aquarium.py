import math
from pathlib import Path
import time
from panda3d.core import (AmbientLight,DirectionalLight,Fog,WindowProperties,
                         TransparencyAttrib,ClockObject,TextureStage,loadPrcFileData)
from direct.showbase.ShowBase import ShowBase
from direct.gui.OnscreenText import OnscreenText
from .art import fish_model,scenery,mesh
from .settings import Settings,PRESETS
from .simulation import Simulation
from .views import AquariumView, desktop_lenses
from .window_mode import WindowModes
from .window_drag import WindowDrag
from .service import Service
from .options import OptionsPanel
from .deadzones import DisplayProfile, MAX_WINDOWS
from .projection import blackout_geometry
from .text import configure_text, display_text
from .framing import bounds, regions, aim_at_sand
from .chat import ChatBubbles
from .bubbles import AirBubbles
from .decorations import DecorationLibrary
from .shelves import SandShelves
from .transitions import FishTransitions
from .appearance_scene import AppearanceScene
from .bubble_columns import BubbleColumns

class Aquarium(ShowBase):
    def __init__(self,args):
        self.args=args;self.settings=Settings.load(args.settings)
        for warning in self.settings.load_warnings:print('Settings: '+warning,flush=True)
        self.display_path=Path(args.settings).with_name('display-layout.json')
        self.display=DisplayProfile.load(self.display_path)
        self.restore_rectangles=self.display.windows if args.wall_columns is None else []
        if self.restore_rectangles:args.width,args.height=self.restore_rectangles[0][2:]
        self.start_windows=args.wall_columns or len(self.restore_rectangles) or 1
        if args.preset:self.settings.apply(args.preset)
        if args.render_scale is not None:self.settings.scale=args.render_scale
        for field in ("detail","plants","bubbles","fps"):
            value=getattr(args,field)
            if value is not None:setattr(self.settings,field,value);self.settings.preset="custom"
        if args.no_lighting:self.settings.lighting=False
        if args.no_caustics:self.settings.caustics=False
        if args.no_vsync:self.settings.vsync=False
        loadPrcFileData("tank",f"window-title LoRagotchi Aquarium — Controls\nwin-size 456 748\nwin-origin 32 32\nundecorated false\nfullscreen false\nsync-video {str(self.settings.vsync).lower()}\naudio-library-name null\nframebuffer-multisample 0\ntextures-power-2 none\nnotify-level warning\n")
        configure_text()
        super().__init__();self.disableMouse();self.setBackgroundColor(.012,.075,.115,1)
        self.sim=Simulation();self.models={};self.roster=[];self.inbox=[];self.status="Starting aquarium…"
        self.selected=0;self.show_names=self.settings.show_names;self.panel_visible=True;self.start=time.monotonic();self.screenshot_done=False
        self.scene=self.render.attachNewNode("aquarium");self.scene.setTwoSided(True)
        self.transitions=FishTransitions(self);self._model_snapshots={}
        ambient=AmbientLight("blue-water-ambient");ambient.setColor((.63,.71,.73,1));self.ambient=self.render.attachNewNode(ambient)
        sun=DirectionalLight("surface-light");sun.setColor((.95,.95,.82,1));self.sun=self.render.attachNewNode(sun);self.sun.setHpr(-35,-65,0)
        fill=DirectionalLight("soft-fill");fill.setColor((.15,.30,.34,1));self.fill=self.render.attachNewNode(fill);self.fill.setHpr(130,-20,0)
        fog=self.water_fog=Fog("water-depth");fog.setColor(.028,.15,.19);fog.setExpDensity(.012);self.render.setFog(fog)
        self.camera.setPos(0,-32,12);self.camera.lookAt(0,0,5.5)
        self.chat=ChatBubbles(self.scene,self.camera,self.render,self.settings.chat_bubbles)
        self.cam.node().setActive(False)
        self.views=[];self.second_window=None;self.second_input=None;self._configuring_output=False
        self._next_view_id=0;self._destroying=False
        self._layout=None;self._ui_text={};self._next_ui_update=0.
        self.window_modes=WindowModes(self.pipe)
        self.window_drag=WindowDrag(self)
        self.buffer=None;self.screen=None;self.view_cameras=[]
        self.internal_size=(0,0)
        self.shelves=SandShelves(self)
        self.decorations=DecorationLibrary(self)
        self.appearance=AppearanceScene(self)
        self.columns=BubbleColumns(self)
        self.rebuild_scene()
        for i in range(self.start_windows):
            self.add_window(self.restore_rectangles[i] if self.restore_rectangles else None)
        self.build_panel()
        self.show_controls()
        self.accept("tab",self.tab);self.accept("escape",self.escape);self.accept("f",self.shortcut,[self.fullscreen])
        self.accept("n",self.shortcut,[self.toggle_names]);self.accept("v",self.shortcut,[self.add_window]);self.accept("arrow_right",self.shortcut,[self.select_next])
        self.accept("delete",self.shortcut,[self.remove_selected])
        for i,name in enumerate(PRESETS,1):self.accept(str(i),self.shortcut,[self.set_preset,name])
        self.accept("window-event",self.on_window)
        self._sync_secondary()
        if args.fullscreen:self.fullscreen()
        self.service=Service(args)
        self.taskMgr.add(self.update,"aquarium-update")
        gsg=(self.aquarium_window or self.win).getGsg()
        print(f"Renderer: {gsg.getDriverVendor()} / {gsg.getDriverRenderer()} / {gsg.getDriverVersion()}",flush=True)
        print(f"Controls window + {len(self.views)} aquarium view(s); internal {self.internal_size}",flush=True)
        print("Aquarium: drag anywhere to move; drag edges to resize; Tab controls; F fullscreen; N names; V add view; Esc close view",flush=True)

    @property
    def aquarium_window(self):
        return self.views[0].window if self.views else None

    def rebuild_scene(self):
        if hasattr(self,"decor"):self.decor.removeNode()
        self.decor=self.scene.attachNewNode("scenery")
        self.plants,self.caustic=scenery(self.decor,self.settings)
        # Background gradient plane in world space.
        verts=[((-35,13,-1),(0,-1,0),(.015,.065,.10,1),(0,0)),((35,13,-1),(0,-1,0),(.015,.065,.10,1),(1,0)),
               ((35,13,23),(0,-1,0),(.06,.28,.33,1),(1,1)),((-35,13,23),(0,-1,0),(.06,.28,.33,1),(0,1))]
        bg=self.background=mesh("deep-water",verts,[(0,1,2),(0,2,3)]);bg.reparentTo(self.decor);bg.setLightOff();bg.setFogOff()
        self.light_shafts=[]
        for x in (-14,-2,12):
            ray=mesh("light-shaft",[((x,10,18),(0,-1,0),(.25,.53,.51,.025),(0,1)),((x-5,10,0),(0,-1,0),(.25,.53,.51,0),(0,0)),((x+4,10,0),(0,-1,0),(.25,.53,.51,0),(1,0)),((x+1,10,18),(0,-1,0),(.25,.53,.51,.055),(1,1))],[(0,1,2),(0,2,3)])
            self.light_shafts.append(ray)
            ray.reparentTo(self.decor);ray.setTransparency(TransparencyAttrib.MAlpha);ray.setLightOff();ray.setDepthWrite(False)
        self.bubbles=AirBubbles(self.decor,self.settings.bubbles,self.camera,self.render)
        if hasattr(self,"water_lens"):self.bubbles.set_view(self.water_lens)
        self.render.clearLight()
        if self.settings.lighting:
            self.render.setLight(self.ambient);self.render.setLight(self.sun);self.render.setLight(self.fill)
        for model,_,_ in self.models.values():model.removeNode()
        # Rebuild the currently shown snapshots, including queued old versions.
        # Reconciliation needs those nodes to capture a departure's old pose.
        self.models={};self._model_snapshots={};self._sync_fish_nodes()
        ClockObject.getGlobalClock().setMode(ClockObject.MLimited);ClockObject.getGlobalClock().setFrameRate(self.settings.fps)
        self.setup_output()
        self.appearance.bind()

    def setup_output(self):
        if self._configuring_output or self.win is None or not self.win.getProperties().getOpen():return
        self._configuring_output=True
        try:
            if not self.views:
                self.buffer=self.screen=None;self.internal_size=(0,0);self.view_cameras=[]
                self.sim.set_view(self.sim.volume.origin,self.sim.volume.right,self.sim.volume.forward,
                                  self.sim.volume.up,self.sim.volume.tan_x,self.sim.volume.tan_y,())
                self._layout=None
                self.shelves.layout([],None,self.camera,self.render)
                return
            for view in self.views:view.resize(self.settings.scale)
            rectangles=[view.rectangle() for view in self.views]
            if all(w>0 and h>0 for x,y,w,h in rectangles):
                active=tuple(not v.window.getProperties().getMinimized() for v in self.views)
                layout=(tuple(rectangles),active,tuple(self.display.zones),self.display.constrain)
                if layout!=self._layout:
                    full=self.water_lens=desktop_lenses([bounds(rectangles)])[0]
                    aim_at_sand(self.camera,self.render,full)
                    for view,lens in zip(self.views,desktop_lenses(rectangles)):view.set_lens(lens)
                    self.chat.set_view(full);self.bubbles.set_view(full)
                    self.shelves.layout(rectangles,full,self.camera,self.render)
                    screen_regions=regions(rectangles)
                    left,top,width,height=bounds(rectangles)
                    rotation=self.camera.getQuat(self.render)
                    self.sim.set_view(tuple(self.camera.getPos(self.render)),tuple(rotation.getRight()),
                                      tuple(rotation.getForward()),tuple(rotation.getUp()),
                                      math.tan(math.radians(full.getHfov()/2)),math.tan(math.radians(full.getVfov()/2)),
                                      tuple(r for r,visible in zip(screen_regions,active) if visible),
                                      self.display.zones,self.display.constrain)
                    masks=blackout_geometry(self.display.zones,width/height,max(width,height))
                    for view,region in zip(self.views,screen_regions):
                        view.set_blackout(masks,region)
                    self._layout=layout
                    if hasattr(self,"controls"):self.controls.deadzones.redraw()
            # Kept for diagnostics and the primary-window controls.
            first=self.views[0]
            self.buffer,self.screen,self.internal_size=first.buffer,first.screen,first.internal_size
            self.view_cameras=[view.camera for view in self.views]
        finally:
            self._configuring_output=False
            if hasattr(self,"appearance") and hasattr(self,"background"):
                self.appearance.applied=None
                self.appearance.update(0)

    def add_window(self, rectangle=None):
        if len(self.views)>=MAX_WINDOWS:
            self.status=f"Maximum {MAX_WINDOWS} aquarium windows";return
        view_id=self._next_view_id;self._next_view_id+=1
        props=WindowProperties();props.setTitle(f"LoRagotchi Aquarium — view {view_id+1}")
        if rectangle is None:
            width=(self.args.second_width or self.args.width) if self.views else self.args.width
            height=(self.args.second_height or self.args.height) if self.views else self.args.height
            if not self.views:
                control=self.win.getProperties()
                x,y=control.getXOrigin()+self.win.getXSize()+24,control.getYOrigin()
            elif len(self.views)==1 and self.args.second_origin:
                x,y=self.args.second_origin
            else:
                # A visible cascade is safer than opening off the desktop. Move
                # the native window to its monitor before saving the layout.
                last=self.views[-1].rectangle();x,y=last[0]+48,last[1]+48
            rectangle=(x,y,width,height)
        x,y,width,height=rectangle
        props.setSize(width,height);props.setOrigin(x,y);props.setFullscreen(False);props.setUndecorated(True)
        window=self.openWindow(props=props,fbprops=self.win.getFbProperties(),makeCamera=False,type='onscreen')
        if window is None or not window.isValid():
            if window is not None:self.closeWindow(window)
            self.status="Additional window could not open";return
        view=AquariumView(self,window);view.view_id=view_id
        self.views.append(view);view.names.sync(self.transitions.shown.values())
        view.input=self.setupMouse(window,fMultiWin=True)
        prefix=f'view-{view_id}-';view.input.node().setPrefix(prefix)
        for key,callback,args in (
            ('v',self.add_window,[]),('n',self.toggle_names,[]),('f',self.fullscreen,[window]),
            ('escape',self.close_view,[view]),('arrow_right',self.select_next,[]),
            ('tab',self.show_controls,[]),('mouse1',self.window_drag.begin,[view]),
            ('mouse1-up',self.window_drag.finish,[view])):
            self.accept(prefix+key,callback,args)
        self._sync_secondary();self.setup_output()
        if hasattr(self,'controls'):self.controls.deadzones.refresh_windows(view_id)
        return view

    def _sync_secondary(self):
        self.second_window=self.views[1].window if len(self.views)>1 else None
        self.second_input=self.views[1].input if len(self.views)>1 else None
        self.args.wall_columns=len(self.views)

    def close_view(self,view):
        if view not in self.views:return
        self.window_drag.finish(view,select=False)
        self.views.remove(view);self.window_modes.discard(view.window)
        for event in ('v','n','f','escape','arrow_right','tab','mouse1','mouse1-up'):self.ignore(f'view-{view.view_id}-'+event)
        if view.input:view.input.getParent().getParent().removeNode()
        if view.window.getProperties().getOpen():
            # GLX FBO names are context-local. Retire this output immediately
            # after drawing its own native context, not whichever sibling was
            # most recently captured/rendered.
            view.window.setSort(max(w.getSort() for w in self.winList)+1)
            self.graphicsEngine.renderFrame()
        view.destroy()
        self.closeWindow(view.window);self._sync_secondary()
        if not self._destroying:
            self.setup_output()
            if hasattr(self,'controls'):
                self.controls.deadzones.refresh_windows()
                if not self.views:self.show_controls()

    def open_second_window(self):
        if not self.second_window:return self.add_window()

    def close_second_window(self):
        if self.second_window:self.close_view(self.views[1])

    def save_display(self,windows=False):
        if windows:self.display.windows=[v.rectangle() for v in self.views]
        self.setup_output()
        try:self.display.save(self.display_path)
        except OSError as error:
            self.status=f"Display settings could not save: {error}";return False
        return True

    def sync_models(self):
        self.transitions.reconcile(self.roster)
        self._sync_fish_nodes()

    def _sync_fish_nodes(self):
        visible=list(self.transitions.shown.values())
        owners={f.owner for f in visible}
        for key in list(self.models):
            if key not in owners:
                self.models.pop(key)[0].removeNode();self._model_snapshots.pop(key,None)
        for fish in visible:
            if fish.owner in self.models and self._model_snapshots.get(fish.owner)!=fish:
                self.models.pop(fish.owner)[0].removeNode()
            if fish.owner not in self.models:
                model,tail,fins=fish_model(fish,self.settings.detail);model.reparentTo(self.scene);self.models[fish.owner]=(model,tail,fins)
                self._model_snapshots[fish.owner]=fish
                if fish.owner in self.transitions.arrivals:model.hide()
        self.sim.roster(self.transitions.swimming())
        for view in self.views:view.names.sync(visible)

    def build_panel(self):
        self.controls=OptionsPanel(self)
        self.panel=self.controls.root

    def shortcut(self,callback,*args):
        if not self.controls.editing():callback(*args)

    def tab(self):
        if self.panel_visible and self.controls.editing():self.controls.next_field()
        else:self.toggle_panel()

    def scale_label_update(self):
        if hasattr(self,"scale_label") and hasattr(self,"scale_slider"):
            self.scale_label["text"]=f"{self.scale_slider['value']:.2f}× · UI remains output resolution"
    def apply_scale(self):
        self.settings.scale=float(self.scale_slider["value"]);self.settings.preset="custom";self.setup_output();self.settings.save(self.args.settings)
    def set_preset(self,name):
        if name not in PRESETS:return
        self.settings.apply(name);self.rebuild_scene();self.settings.save(self.args.settings)
        if hasattr(self,"scale_slider"):self.scale_slider["value"]=self.settings.scale
    def toggle_panel(self):
        self.controls.blur()
        if not self.panel_visible:self.show_controls()
        else:
            props=WindowProperties();props.setMinimized(True)
            self.win.requestProperties(props);self.panel_visible=False
    def show_controls(self):
        props=WindowProperties();props.setMinimized(False);props.setForeground(True)
        self.win.requestProperties(props)
        self.panel_visible=True
    def escape(self):
        self.toggle_panel()
    def fullscreen(self,window=None):
        window=window or (self.controls.deadzones.view().window if hasattr(self,'controls') and self.views else self.aquarium_window)
        if window is None:return
        try:self.window_modes.toggle(window)
        except (OSError,ValueError) as error:
            self.status=f"Fullscreen unavailable: {error}"
            print(self.status,flush=True)
    def toggle_names(self):
        self.show_names=not self.show_names
        self.settings.show_names=self.show_names
        self.settings.save(self.args.settings)
    def toggle_chat(self):
        self.settings.chat_bubbles=not self.settings.chat_bubbles
        self.chat.set_enabled(self.settings.chat_bubbles)
        self.settings.save(self.args.settings)
        self.controls.chat_button['text']='Channel chat: '+('on' if self.settings.chat_bubbles else 'off')
    def toggle_wall(self):
        if self.second_window:self.close_second_window()
        else:self.open_second_window()
    def select_next(self):
        if self.roster:self.selected=(self.selected+1)%len(self.roster);self.show_names=True
    def end_session(self):
        if time.monotonic()<self.clear_confirm:
            self.service.commands.put(("clear",));self.clear_confirm=0;self.end_button["text"]="End display session"
        else:self.clear_confirm=time.monotonic()+5;self.end_button["text"]="Click again to clear copies"
    def remove_selected(self):
        if self.roster:self.service.commands.put(("remove",self.roster[self.selected%len(self.roster)].owner))
    def select_fish(self,view=None,watcher=None):
        if not self.views:return
        view=view or self.views[0]
        watcher=watcher or view.input.getParent().node()
        if not watcher.hasMouse():return
        mouse=watcher.getMouse();nearest=None
        from panda3d.core import Point2
        point=Point2()
        for i,fish in enumerate(self.roster):
            if fish.owner not in self.models:continue
            node=self.models[fish.owner][0]
            if node.isHidden():continue
            if view.lens.project(self.camera.getRelativePoint(self.render,node.getPos(self.render)),point):
                distance=(point.x-mouse.x)**2+(point.y-mouse.y)**2
                if nearest is None or distance<nearest[0]:nearest=(distance,i)
        if nearest and nearest[0]<.04:self.selected=nearest[1];self.show_names=True

    def on_window(self,window):
        super().windowEvent(window)
        if not hasattr(self,'views'):return
        view=next((v for v in self.views if v.window==window),None)
        if window==self.win:
            self.panel_visible=not window.getProperties().getMinimized()
            if hasattr(self,"controls"):self.controls.resize()
            # ShowBase otherwise throttles the entire app when its primary
            # window is minimized, even while aquarium outputs are on display.
        elif view and not window.getProperties().getOpen():
            self.close_view(view)
        elif view:
            if window.getProperties().getOpen():
                self.setup_output()
        self.mainWinMinimized=not self.panel_visible and not any(
            v.window.getProperties().getOpen() and not v.window.getProperties().getMinimized()
            for v in self.views)

    def set_ui_text(self,widget,text):
        key=id(widget)
        if self._ui_text.get(key)!=text:
            rendered=display_text(text)
            if isinstance(widget,OnscreenText):widget.setText(rendered)
            else:widget['text']=rendered
            self._ui_text[key]=text

    def update_fish(self,dt):
        poses=self.sim.step(dt)
        for key,pose in poses.items():
            model,tail,fins=self.models[key]
            if self.sim.swimmers[key].parked != model.isHidden():
                model.hide() if self.sim.swimmers[key].parked else model.show()
            model.setPos(pose.x,pose.y,pose.z);model.setHpr(pose.heading,pose.bank,pose.pitch)
            tail.setH(math.sin(pose.phase)*22*pose.speed)
            for i,fin in enumerate(fins):fin.setH(math.sin(pose.phase*.65+i)*12)
        self.transitions.update(dt)

    def update(self,task):
        dt=min(ClockObject.getGlobalClock().getDt(),.1)
        self.window_drag.update()
        self.controls.clipboard.pump()
        while not self.service.events.empty():
            event=self.service.events.get_nowait()
            if isinstance(event,dict):
                kind=event.get("kind")
                if kind=="roster":
                    new=event["fish"]
                    if event.get("mode",self.controls.mode)!=self.controls.mode:
                        # Switching demo/replay to live never leaves synthetic
                        # fish performing departures over the live collection.
                        self.transitions.destroy();self.transitions=FishTransitions(self)
                    self.roster=new;self.sync_models()
                    self.controls.mode=event.get("mode",self.controls.mode)
                elif kind=="connection":
                    self.status=event["text"];self.controls.on_connection(event)
                elif kind=="devices":self.controls.on_devices(event)
                elif kind=="notice":self.status=event["text"]
                elif kind and kind.startswith('radio_'):self.controls.radio.on_event(event)
                elif kind=="mesh":
                    self.inbox=(self.inbox+[event])[-100:]
                    self.chat.accept(event)
            else:
                if event.kind=="return_status":self.status=f"RX return {event.status} · snapshot kept"
        self.update_fish(dt);t=self.sim.time
        self.appearance.update(dt)
        self.columns.update(dt)
        self.bubbles.update(dt)
        self.chat.update(dt)
        # Static text changes on data changes, not on every rendered frame.
        waiting=sum(s.parked for s in self.sim.swimmers.values())
        space_note=f" · {waiting} waiting for swim space" if waiting else ""
        moving=len(self.transitions.arrivals)+len(self.transitions.departures)
        if moving:space_note+=f" · {moving} in transition"
        self.set_ui_text(self.footer,f"{len(self.roster)} shared fish{space_note}\n{self.status}")
        now=time.monotonic()
        if self.panel_visible and now>=self._next_ui_update:
            self._next_ui_update=now+.15
            self.controls.refresh()
            view=self.controls.deadzones.view()
            self.set_ui_text(self.output_label,(f"View {view.view_id+1}: {view.window.getXSize()}×{view.window.getYSize()} · scene {view.internal_size[0]}×{view.internal_size[1]}\n"
                                               if view else "No aquarium views — use Add window\n")+
                               f"{len(self.views)} aquarium window(s) · {self.settings.preset} · cap {self.settings.fps} fps")
            fish=self.roster[self.selected%len(self.roster)] if self.roster else None
            self.set_ui_text(self.fish_label,f"{fish.name} · {['fry','young','adult','elder'][fish.stage]}\n{fish.owner[:16]}…" if fish else "No shared fish yet")
            self.set_ui_text(self.message_label,"Inbox: "+("\n".join(str(m.get('text',''))[:56] for m in self.inbox[-2:]) if self.inbox else "no messages"))
        for view in self.views:
            view.names.update(self.show_names,view.lens,self.camera,self.render,self.models,view.aspect)
        elapsed=time.monotonic()-self.start
        if self.args.screenshot and not self.screenshot_done and elapsed>=self.args.capture_after and self.roster and self.views:
            path=Path(self.args.screenshot);path.parent.mkdir(parents=True,exist_ok=True)
            self.graphicsEngine.renderFrame();self.aquarium_window.saveScreenshot(str(path));self.screenshot_done=True
            print(f"Screenshot: {path.resolve()}",flush=True)
        if self.args.run_seconds and elapsed>=self.args.run_seconds:self.userExit()
        return task.cont

    def destroy(self):
        if hasattr(self,"service"):self.service.close()
        if hasattr(self,"controls"):self.controls.clipboard.close()
        if hasattr(self,"window_drag"):self.window_drag.close()
        if hasattr(self,"chat"):self.chat.destroy()
        if hasattr(self,"transitions"):self.transitions.destroy()
        self._destroying=True
        for view in list(getattr(self,"views",[])):self.close_view(view)
        self.views=[]
        super().destroy()
