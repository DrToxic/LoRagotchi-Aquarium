import math
from pathlib import Path
import random
import time
from panda3d.core import (AmbientLight,DirectionalLight,Fog,WindowProperties,
                         TransparencyAttrib,ClockObject,TextureStage,TextNode,loadPrcFileData)
from direct.showbase.ShowBase import ShowBase
from direct.gui.OnscreenText import OnscreenText
from .art import fish_model,scenery,ellipsoid,mesh
from .settings import Settings,PRESETS
from .simulation import Simulation
from .views import AquariumView, desktop_lenses
from .window_mode import WindowModes
from .service import Service
from .options import OptionsPanel

class Aquarium(ShowBase):
    def __init__(self,args):
        self.args=args;self.settings=Settings.load(args.settings)
        if args.preset:self.settings.apply(args.preset)
        if args.render_scale is not None:self.settings.scale=args.render_scale
        for field in ("detail","plants","bubbles","fps"):
            value=getattr(args,field)
            if value is not None:setattr(self.settings,field,value);self.settings.preset="custom"
        if args.no_lighting:self.settings.lighting=False
        if args.no_caustics:self.settings.caustics=False
        if args.no_vsync:self.settings.vsync=False
        loadPrcFileData("tank",f"window-title LoRagotchi Community Tank\nwin-size {args.width} {args.height}\nfullscreen false\nsync-video {str(self.settings.vsync).lower()}\naudio-library-name null\nframebuffer-multisample 0\ntextures-power-2 none\nnotify-level warning\n")
        font=Path(__file__).resolve().parent/"assets"/"LiberationSans-Regular.ttf"
        loadPrcFileData("font",f"text-default-font {font.as_posix()}\n")
        super().__init__();self.disableMouse();self.setBackgroundColor(.012,.075,.115,1)
        self.sim=Simulation();self.models={};self.roster=[];self.inbox=[];self.status="Starting aquarium…"
        self.selected=0;self.show_names=False;self.panel_visible=False;self.start=time.monotonic();self.screenshot_done=False
        self.scene=self.render.attachNewNode("aquarium");self.scene.setTwoSided(True)
        ambient=AmbientLight("blue-water-ambient");ambient.setColor((.63,.71,.73,1));self.ambient=self.render.attachNewNode(ambient)
        sun=DirectionalLight("surface-light");sun.setColor((.95,.95,.82,1));self.sun=self.render.attachNewNode(sun);self.sun.setHpr(-35,-65,0)
        fill=DirectionalLight("soft-fill");fill.setColor((.15,.30,.34,1));self.fill=self.render.attachNewNode(fill);self.fill.setHpr(130,-20,0)
        fog=Fog("water-depth");fog.setColor(.028,.15,.19);fog.setExpDensity(.012);self.render.setFog(fog)
        self.camera.setPos(0,-32,12);self.camera.lookAt(0,0,5.5)
        self.cam.node().setActive(False)
        self.views=[];self.second_window=None;self.second_input=None;self._configuring_output=False
        self._layout=None;self._ui_text={};self._next_ui_update=0.
        self.window_modes=WindowModes(self.pipe)
        self.buffer=None;self.screen=None;self.view_cameras=[]
        self.rebuild_scene()
        self.title=OnscreenText(text="COMMUNITY REEF",pos=(-1.68,.91),scale=.038,fg=(.72,.88,.87,.85),align=TextNode.ALeft,mayChange=True)
        self.subtitle=OnscreenText(text="LoRagotchi · shared fish, one aquarium",pos=(-1.68,.85),scale=.029,fg=(.49,.71,.72,.8),align=TextNode.ALeft)
        self.footer=OnscreenText(text="",pos=(-1.68,-.94),scale=.028,fg=(.65,.8,.79,.8),align=TextNode.ALeft,mayChange=True)
        self.build_panel()
        if args.operator:self.toggle_panel()
        self.accept("tab",self.tab);self.accept("escape",self.escape);self.accept("f",self.shortcut,[self.fullscreen])
        self.accept("n",self.shortcut,[self.toggle_names]);self.accept("v",self.shortcut,[self.toggle_wall]);self.accept("arrow_right",self.shortcut,[self.select_next])
        self.accept("delete",self.shortcut,[self.remove_selected]);self.accept("mouse1",self.select_fish)
        for i,name in enumerate(PRESETS,1):self.accept(str(i),self.shortcut,[self.set_preset,name])
        self.accept("window-event",self.on_window)
        if args.wall_columns==2:self.open_second_window()
        if args.fullscreen:self.fullscreen()
        self.service=Service(args)
        self.taskMgr.add(self.update,"aquarium-update")
        gsg=self.win.getGsg()
        print(f"Renderer: {gsg.getDriverVendor()} / {gsg.getDriverRenderer()} / {gsg.getDriverVersion()}",flush=True)
        print(f"Output {self.win.getXSize()}x{self.win.getYSize()}, internal {self.internal_size}, {args.wall_columns} shared-world viewport(s)",flush=True)
        print("Controls: Tab operator panel; F borderless fullscreen; 1..5 quality; N names; V second window; click/right-arrow select; Delete remove copy; Esc close",flush=True)

    def rebuild_scene(self):
        if hasattr(self,"decor"):self.decor.removeNode()
        self.decor=self.scene.attachNewNode("scenery")
        self.plants,self.caustic=scenery(self.decor,self.settings)
        # Background gradient plane in world space.
        verts=[((-35,13,-1),(0,-1,0),(.015,.065,.10,1),(0,0)),((35,13,-1),(0,-1,0),(.015,.065,.10,1),(1,0)),
               ((35,13,23),(0,-1,0),(.06,.28,.33,1),(1,1)),((-35,13,23),(0,-1,0),(.06,.28,.33,1),(0,1))]
        bg=mesh("deep-water",verts,[(0,1,2),(0,2,3)]);bg.reparentTo(self.decor);bg.setLightOff();bg.setFogOff()
        if self.settings.caustics:
            for x in (-14,-2,12):
                ray=mesh("light-shaft",[((x,10,18),(0,-1,0),(.25,.53,.51,.025),(0,1)),((x-5,10,0),(0,-1,0),(.25,.53,.51,0),(0,0)),((x+4,10,0),(0,-1,0),(.25,.53,.51,0),(1,0)),((x+1,10,18),(0,-1,0),(.25,.53,.51,.055),(1,1))],[(0,1,2),(0,2,3)])
                ray.reparentTo(self.decor);ray.setTransparency(TransparencyAttrib.MAlpha);ray.setLightOff();ray.setDepthWrite(False)
        self.bubbles=[];rng=random.Random(17)
        for _ in range(self.settings.bubbles):
            bubble=ellipsoid("bubble",(.035,.035,.046),(.42,.70,.73,.4),8);bubble.setTransparency(TransparencyAttrib.MAlpha);bubble.reparentTo(self.decor)
            self.bubbles.append((bubble,rng.uniform(-18,18),rng.uniform(-4,6),rng.uniform(0,12),rng.uniform(.2,.5)))
        self.render.clearLight()
        if self.settings.lighting:
            self.render.setLight(self.ambient);self.render.setLight(self.sun);self.render.setLight(self.fill)
        for model,_,_ in self.models.values():model.removeNode()
        self.models={};self.sync_models()
        ClockObject.getGlobalClock().setMode(ClockObject.MLimited);ClockObject.getGlobalClock().setFrameRate(self.settings.fps)
        self.setup_output()

    def setup_output(self):
        if self._configuring_output or self.win is None or not self.win.getProperties().getOpen():return
        self._configuring_output=True
        try:
            if not self.views:self.views.append(AquariumView(self,self.win,primary=True))
            for view in self.views:view.resize(self.settings.scale)
            rectangles=[view.rectangle() for view in self.views]
            if all(w>0 and h>0 for x,y,w,h in rectangles):
                layout=tuple(rectangles)
                if layout!=self._layout:
                    for view,lens in zip(self.views,desktop_lenses(rectangles)):view.set_lens(lens)
                    left=min(x for x,y,w,h in rectangles);top=min(y for x,y,w,h in rectangles)
                    width=max(x+w for x,y,w,h in rectangles)-left
                    height=max(y+h for x,y,w,h in rectangles)-top
                    full=desktop_lenses([(left,top,width,height)])[0]
                    regions=tuple((2*(x-left)/width-1,2*(x+w-left)/width-1,
                                   1-2*(y+h-top)/height,1-2*(y-top)/height) for x,y,w,h in rectangles)
                    rotation=self.camera.getQuat(self.render)
                    self.sim.set_view(tuple(self.camera.getPos(self.render)),tuple(rotation.getRight()),
                                      tuple(rotation.getForward()),tuple(rotation.getUp()),
                                      math.tan(math.radians(full.getHfov()/2)),
                                      math.tan(math.radians(full.getVfov()/2)),regions)
                    self._layout=layout
            # Kept for diagnostics and the primary-window controls.
            first=self.views[0]
            self.buffer,self.screen,self.internal_size=first.buffer,first.screen,first.internal_size
            self.view_cameras=[view.camera for view in self.views]
        finally:self._configuring_output=False

    def open_second_window(self):
        if self.second_window:return
        props=WindowProperties()
        props.setTitle("LoRagotchi Aquarium — second view")
        props.setSize(self.args.second_width or self.win.getXSize(),self.args.second_height or self.win.getYSize())
        props.setFullscreen(False)
        if self.args.second_origin:
            props.setOrigin(*self.args.second_origin)
        else:
            primary=self.win.getProperties()
            props.setOrigin(primary.getXOrigin()+self.win.getXSize(),primary.getYOrigin())
        # Let Panda create the native GL context for this window. Reusing the
        # exact same GSG across GLX drawables can produce BadMatch/black windows.
        window=self.openWindow(props=props,fbprops=self.win.getFbProperties(),
                               makeCamera=False,type='onscreen')
        if window is None or not window.isValid():
            if window is not None:self.closeWindow(window)
            self.args.wall_columns=1
            self.status="Second window could not open"
            return
        self.second_window=window
        view=AquariumView(self,window)
        self.views.append(view)
        view.names.sync(self.roster)
        self.second_input=self.setupMouse(window,fMultiWin=True)
        self.second_input.node().setPrefix('second-')
        self.accept('second-v',self.toggle_wall)
        self.accept('second-n',self.toggle_names)
        self.accept('second-f',self.fullscreen,[window])
        self.accept('second-escape',self.close_second_window)
        self.accept('second-arrow_right',self.select_next)
        self.accept('second-mouse1',self.select_fish,[view,self.second_input.getParent().node()])
        self.args.wall_columns=2
        self.setup_output()

    def close_second_window(self):
        if not self.second_window:return
        window=self.second_window
        self.second_window=None
        self.window_modes.discard(window)
        view=self.views.pop()
        view.destroy()
        for event in ('v','n','f','escape','arrow_right','mouse1'):self.ignore('second-'+event)
        if self.second_input:
            # This is the isolated MouseAndKeyboard subtree, not the main input.
            self.second_input.getParent().getParent().removeNode()
            self.second_input=None
        self.closeWindow(window)
        self.args.wall_columns=1
        self.setup_output()

    def sync_models(self):
        owners={f.owner for f in self.roster}
        for key in list(self.models):
            if key not in owners:self.models.pop(key)[0].removeNode()
        for fish in self.roster:
            if fish.owner not in self.models:
                model,tail,fins=fish_model(fish,self.settings.detail);model.reparentTo(self.scene);self.models[fish.owner]=(model,tail,fins)
        self.sim.roster(self.roster)
        for view in self.views:view.names.sync(self.roster)

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
        self.panel_visible=not self.panel_visible
        self.controls.blur()
        self.panel.show() if self.panel_visible else self.panel.hide()
    def escape(self):
        if self.panel_visible:self.toggle_panel()
        else:self.userExit()
    def fullscreen(self,window=None):
        window=window or self.win
        try:self.window_modes.toggle(window)
        except (OSError,ValueError) as error:
            self.status=f"Fullscreen unavailable: {error}"
            print(self.status,flush=True)
    def toggle_names(self):self.show_names=not self.show_names
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
        view=view or self.views[0]
        watcher=watcher or self.mouseWatcherNode
        if not watcher.hasMouse() or (view.primary and self.panel_visible):return
        mouse=watcher.getMouse();nearest=None
        from panda3d.core import Point2
        point=Point2()
        for i,fish in enumerate(self.roster):
            node=self.models[fish.owner][0]
            if view.lens.project(self.camera.getRelativePoint(self.render,node.getPos(self.render)),point):
                distance=(point.x-mouse.x)**2+(point.y-mouse.y)**2
                if nearest is None or distance<nearest[0]:nearest=(distance,i)
        if nearest and nearest[0]<.04:self.selected=nearest[1];self.show_names=True

    def on_window(self,window):
        super().windowEvent(window)
        if not hasattr(self,'views'):return
        if window==self.second_window and not window.getProperties().getOpen():
            self.close_second_window()
        elif window==self.win or window==self.second_window:
            if window.getProperties().getOpen():
                self.setup_output()
                if hasattr(self,"controls"):self.controls.resize()

    def set_ui_text(self,widget,text):
        key=id(widget)
        if self._ui_text.get(key)!=text:
            if isinstance(widget,OnscreenText):widget.setText(text)
            else:widget['text']=text
            self._ui_text[key]=text

    def update(self,task):
        dt=min(ClockObject.getGlobalClock().getDt(),.1)
        while not self.service.events.empty():
            event=self.service.events.get_nowait()
            if isinstance(event,dict):
                kind=event.get("kind")
                if kind=="roster":
                    new=event["fish"]
                    previous={f.owner:f for f in self.roster}
                    for f in new:
                        if previous.get(f.owner)!=f and f.owner in self.models:self.models.pop(f.owner)[0].removeNode()
                    self.roster=new;self.sync_models()
                    self.controls.mode=event.get("mode",self.controls.mode)
                elif kind=="connection":
                    self.status=event["text"];self.controls.on_connection(event)
                elif kind=="devices":self.controls.on_devices(event)
                elif kind=="notice":self.status=event["text"]
                elif kind=="mesh":self.inbox=(self.inbox+[event])[-100:]
            else:
                if event.kind=="return_status":self.status=f"RX return {event.status} · snapshot kept"
        poses=self.sim.step(dt);t=self.sim.time
        for key,pose in poses.items():
            model,tail,fins=self.models[key];model.setPos(pose.x,pose.y,pose.z);model.setHpr(pose.heading,pose.bank,pose.pitch)
            tail.setH(math.sin(pose.phase)*22*pose.speed)
            for i,fin in enumerate(fins):fin.setH(math.sin(pose.phase*.65+i)*12)
        for node,phase in self.plants:node.setR(math.sin(t*.45+phase)*3)
        for node,x,y,phase,speed in self.bubbles:node.setPos(x+math.sin(t+phase)*.12,y,(phase+t*speed)%12)
        if self.caustic:self.caustic.setTexOffset(TextureStage.getDefault(),t*.009,t*.006)
        # Static text changes on data changes, not on every rendered frame.
        self.set_ui_text(self.footer,f"{len(self.roster)} shared fish   ·   {self.status}   ·   {len(self.views)} window(s)   ·   Tab controls")
        aspect=self.getAspectRatio();self.title.setX(-aspect+.07);self.subtitle.setX(-aspect+.07);self.footer.setX(-aspect+.07)
        now=time.monotonic()
        if self.panel_visible and now>=self._next_ui_update:
            self._next_ui_update=now+.15
            self.controls.refresh()
            self.set_ui_text(self.output_label,f"Output {self.win.getXSize()}×{self.win.getYSize()}\nScene {self.internal_size[0]}×{self.internal_size[1]} · {len(self.views)} window(s)\n{self.settings.preset} · cap {self.settings.fps} fps")
            fish=self.roster[self.selected%len(self.roster)] if self.roster else None
            self.set_ui_text(self.fish_label,f"{fish.name} · {['fry','young','adult','elder'][fish.stage]}\n{fish.owner[:16]}…" if fish else "No shared fish yet")
            self.set_ui_text(self.message_label,"Inbox: "+("\n".join(str(m.get('text',''))[:56] for m in self.inbox[-2:]) if self.inbox else "no messages"))
        for view in self.views:
            view.names.update(self.show_names,view.lens,self.camera,self.render,self.models,view.aspect)
        elapsed=time.monotonic()-self.start
        if self.args.screenshot and not self.screenshot_done and elapsed>=self.args.capture_after and self.roster:
            path=Path(self.args.screenshot);path.parent.mkdir(parents=True,exist_ok=True)
            self.graphicsEngine.renderFrame();self.win.saveScreenshot(str(path));self.screenshot_done=True
            print(f"Screenshot: {path.resolve()}",flush=True)
        if self.args.run_seconds and elapsed>=self.args.run_seconds:self.userExit()
        return task.cont

    def destroy(self):
        if hasattr(self,"service"):self.service.close()
        if hasattr(self,"second_window") and self.second_window:self.close_second_window()
        for view in getattr(self,"views",[]):view.destroy()
        self.views=[]
        super().destroy()
