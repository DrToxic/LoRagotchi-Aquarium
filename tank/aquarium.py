import math
from pathlib import Path
import random
import time
from panda3d.core import (AmbientLight,DirectionalLight,Fog,Vec4,WindowProperties,Texture,CardMaker,
                         TransparencyAttrib,PerspectiveLens,ClockObject,TextureStage,TextNode,loadPrcFileData)
from direct.showbase.ShowBase import ShowBase
from direct.gui.OnscreenText import OnscreenText
from direct.gui.DirectGui import DirectFrame,DirectLabel,DirectButton,DirectOptionMenu,DirectSlider
from .art import fish_model,scenery,ellipsoid,mesh
from .settings import Settings,PRESETS
from .simulation import Simulation
from .service import Service

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
        loadPrcFileData("tank",f"window-title LoRagotchi Community Tank\nwin-size {args.width} {args.height}\nfullscreen {str(args.fullscreen).lower()}\nsync-video {str(self.settings.vsync).lower()}\naudio-library-name null\nframebuffer-multisample 0\ntextures-power-2 none\nnotify-level warning\n")
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
        self.buffer=None;self.screen=None;self.view_cameras=[]
        self.rebuild_scene()
        self.title=OnscreenText(text="COMMUNITY REEF",pos=(-1.68,.91),scale=.038,fg=(.72,.88,.87,.85),align=TextNode.ALeft,mayChange=True)
        self.subtitle=OnscreenText(text="LoRagotchi · shared fish, one aquarium",pos=(-1.68,.85),scale=.029,fg=(.49,.71,.72,.8),align=TextNode.ALeft)
        self.footer=OnscreenText(text="",pos=(-1.68,-.94),scale=.028,fg=(.65,.8,.79,.8),align=TextNode.ALeft,mayChange=True)
        self.name_labels={}
        self.build_panel()
        if args.operator:self.toggle_panel()
        self.accept("tab",self.toggle_panel);self.accept("escape",self.escape);self.accept("f",self.fullscreen)
        self.accept("n",self.toggle_names);self.accept("v",self.toggle_wall);self.accept("arrow_right",self.select_next)
        self.accept("delete",self.remove_selected);self.accept("mouse1",self.select_fish)
        for i,name in enumerate(PRESETS,1):self.accept(str(i),self.set_preset,[name])
        self.accept("window-event",self.on_window)
        self.service=Service(args)
        self.taskMgr.add(self.update,"aquarium-update")
        gsg=self.win.getGsg()
        print(f"Renderer: {gsg.getDriverVendor()} / {gsg.getDriverRenderer()} / {gsg.getDriverVersion()}",flush=True)
        print(f"Output {self.win.getXSize()}x{self.win.getYSize()}, internal {self.internal_size}, {args.wall_columns} shared-world viewport(s)",flush=True)
        print("Controls: Tab operator panel; F fullscreen; 1..5 quality; N names; V two-tile wall; click/right-arrow select; Delete remove copy; Esc close",flush=True)

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
        if self.win is None or self.win.getXSize()<1:return
        width,height=self.win.getXSize(),self.win.getYSize()
        internal=(max(160,int(width*self.settings.scale)),max(90,int(height*self.settings.scale)))
        if self.screen:self.screen.removeNode()
        for camera in self.view_cameras:
            if camera in self.camList:self.camList.remove(camera)
            camera.removeNode()
        self.view_cameras=[]
        if self.buffer:self.graphicsEngine.removeWindow(self.buffer)
        self.buffer=self.win.makeTextureBuffer("aquarium-internal",*internal)
        if not self.buffer:raise RuntimeError("GPU could not allocate requested internal render target; lower render scale/output size")
        self.buffer.setSort(-100);self.buffer.setClearColor((.012,.075,.115,1));self.internal_size=internal
        base_lens=PerspectiveLens();base_lens.setFov(60);base_lens.setAspectRatio(width/height);base_lens.setNearFar(.1,120)
        film=base_lens.getFilmSize();focal=base_lens.getFocalLength()
        count=self.args.wall_columns
        for tile in range(count):
            lens=base_lens.makeCopy()
            lens.setFilmSize(film.x/count,film.y)
            lens.setFocalLength(focal)  # film cropping must not retain the full-view FOV
            lens.setFilmOffset(film.x*((tile+.5)/count-.5),0)
            camera=self.makeCamera(self.buffer,lens=lens,displayRegion=(tile/count,(tile+1)/count,0,1))
            camera.node().setScene(self.render);self.view_cameras.append(camera)
        maker=CardMaker("composite");maker.setFrameFullscreenQuad()
        self.screen=self.render2d.attachNewNode(maker.generate());self.screen.setTexture(self.buffer.getTexture());self.screen.setBin("background",0);self.screen.setDepthWrite(False);self.screen.setDepthTest(False)

    def sync_models(self):
        owners={f.owner for f in self.roster}
        for key in list(self.models):
            if key not in owners:self.models.pop(key)[0].removeNode()
        for fish in self.roster:
            if fish.owner not in self.models:
                model,tail,fins=fish_model(fish,self.settings.detail);model.reparentTo(self.scene);self.models[fish.owner]=(model,tail,fins)
        self.sim.roster(self.roster)

    def build_panel(self):
        self.panel=DirectFrame(frameColor=(.018,.065,.085,.95),frameSize=(-.02,.83,-1.83,.08),pos=(.83,0,.83))
        def label(text,y,scale=.035):return DirectLabel(parent=self.panel,text=text,text_align=TextNode.ALeft,text_scale=scale,text_fg=(.82,.91,.88,1),frameColor=(0,0,0,0),pos=(.025,0,y))
        label("TANK CONTROLS",0)
        self.connection_label=label("",-.12,.025)
        label("Graphics preset",-.27,.028)
        self.preset_menu=DirectOptionMenu(parent=self.panel,items=list(PRESETS),initialitem=list(PRESETS).index(self.settings.preset) if self.settings.preset in PRESETS else 2,scale=.045,pos=(.025,0,-.35),command=self.set_preset)
        label("Internal render scale",-.48,.028)
        self.scale_slider=DirectSlider(parent=self.panel,range=(.25,1.5),value=self.settings.scale,pageSize=.05,scale=.32,pos=(.39,0,-.55),command=self.scale_label_update)
        self.scale_label=label("",-.63,.025)
        DirectButton(parent=self.panel,text="Apply scale",scale=.035,pos=(.23,0,-.71),command=self.apply_scale)
        DirectButton(parent=self.panel,text="Fullscreen [F]",scale=.032,pos=(.60,0,-.71),command=self.fullscreen)
        self.output_label=label("",-.82,.025)
        self.fish_label=label("",-.96,.027)
        DirectButton(parent=self.panel,text="Next fish",scale=.032,pos=(.18,0,-1.12),command=self.select_next)
        DirectButton(parent=self.panel,text="Remove copy",scale=.032,pos=(.57,0,-1.12),command=self.remove_selected)
        DirectButton(parent=self.panel,text="Names [N]",scale=.032,pos=(.18,0,-1.24),command=self.toggle_names)
        DirectButton(parent=self.panel,text="1 / 2 tiles [V]",scale=.032,pos=(.57,0,-1.24),command=self.toggle_wall)
        self.message_label=label("Inbox: no messages",-1.39,.023)
        self.end_button=DirectButton(parent=self.panel,text="End display session",scale=.032,pos=(.38,0,-1.60),command=self.end_session)
        self.clear_confirm=0
        label("Copies stay after originals return.\nTab closes controls · Esc exits",-1.72,.023)
        self.panel.hide();self.scale_label_update()

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
        self.panel.show() if self.panel_visible else self.panel.hide()
    def escape(self):
        if self.panel_visible:self.toggle_panel()
        else:self.userExit()
    def fullscreen(self):
        prop=WindowProperties();prop.setFullscreen(not self.win.getProperties().getFullscreen());self.win.requestProperties(prop)
    def toggle_names(self):self.show_names=not self.show_names
    def toggle_wall(self):
        self.args.wall_columns=3-self.args.wall_columns;self.setup_output()
    def select_next(self):
        if self.roster:self.selected=(self.selected+1)%len(self.roster);self.show_names=True
    def end_session(self):
        if time.monotonic()<self.clear_confirm:
            self.service.commands.put(("clear",));self.clear_confirm=0;self.end_button["text"]="End display session"
        else:self.clear_confirm=time.monotonic()+5;self.end_button["text"]="Click again to clear copies"
    def remove_selected(self):
        if self.roster:self.service.commands.put(("remove",self.roster[self.selected%len(self.roster)].owner))
    def select_fish(self):
        if not self.mouseWatcherNode.hasMouse() or self.panel_visible:return
        mouse=self.mouseWatcherNode.getMouse();nearest=None
        from panda3d.core import Point2
        for i,fish in enumerate(self.roster):
            node=self.models[fish.owner][0];point=Point2()
            # Full-output lens, independent of cropped wall cameras.
            lens=PerspectiveLens();lens.setFov(60);lens.setAspectRatio(self.win.getXSize()/self.win.getYSize())
            if lens.project(self.camera.getRelativePoint(self.render,node.getPos(self.render)),point):
                distance=(point.x-mouse.x)**2+(point.y-mouse.y)**2
                if nearest is None or distance<nearest[0]:nearest=(distance,i)
        if nearest and nearest[0]<.04:self.selected=nearest[1];self.show_names=True
    def on_window(self,window):
        super().windowEvent(window)
        if window==self.win and hasattr(self,"buffer"):
            if self.win.getProperties().getOpen():self.setup_output()

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
                elif kind=="connection":self.status=event["text"]
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
        self.footer.setText(f"{len(self.roster)} shared fish   ·   {self.status}   ·   {self.args.wall_columns} viewport(s)   ·   Tab controls")
        aspect=self.getAspectRatio();self.title.setX(-aspect+.07);self.subtitle.setX(-aspect+.07);self.footer.setX(-aspect+.07)
        self.panel.setX(aspect-.9)
        if self.panel_visible:
            self.connection_label["text"]=self.status[:44]+("\n"+self.status[44:88] if len(self.status)>44 else "")
            self.output_label["text"]=f"Output {self.win.getXSize()}×{self.win.getYSize()}\nScene {self.internal_size[0]}×{self.internal_size[1]} · {self.args.wall_columns} tile(s)\n{self.settings.preset} · cap {self.settings.fps} fps"
            fish=self.roster[self.selected%len(self.roster)] if self.roster else None
            self.fish_label["text"]=f"{fish.name} · {['fry','young','adult','elder'][fish.stage]}\n{fish.owner[:16]}…" if fish else "No shared fish yet"
            self.message_label["text"]="Inbox: "+("\n".join(str(m.get('text',''))[:46] for m in self.inbox[-3:]) if self.inbox else "no messages")
        # Names are a quiet temporary selection aid, never permanently attached UI.
        from panda3d.core import Point2
        for label in self.name_labels.values():label.hide()
        if self.show_names:
            lens=PerspectiveLens();lens.setFov(60);lens.setAspectRatio(aspect)
            for fish in self.roster:
                key=fish.owner;node=self.models[key][0];point=Point2()
                if lens.project(self.camera.getRelativePoint(self.render,node.getPos(self.render)),point):
                    if key not in self.name_labels:self.name_labels[key]=OnscreenText(text=fish.name,scale=.027,fg=(.83,.93,.88,.9),mayChange=True)
                    label=self.name_labels[key];label.setText(fish.name);label.setPos(point.x*aspect,point.y+.07);label.show()
        elapsed=time.monotonic()-self.start
        if self.args.screenshot and not self.screenshot_done and elapsed>=self.args.capture_after and self.roster:
            path=Path(self.args.screenshot);path.parent.mkdir(parents=True,exist_ok=True)
            self.graphicsEngine.renderFrame();self.win.saveScreenshot(str(path));self.screenshot_done=True
            print(f"Screenshot: {path.resolve()}",flush=True)
        if self.args.run_seconds and elapsed>=self.args.run_seconds:self.userExit()
        return task.cont

    def destroy(self):
        if hasattr(self,"service"):self.service.close()
        super().destroy()
