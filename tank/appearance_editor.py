"""Grouped appearance editor with retained drafts and explicit save scopes."""
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import time
from panda3d.core import PNMImage, Texture
from direct.gui.DirectGui import DirectFrame, DirectScrolledFrame
from .appearance import Appearance, CHOICES, RANGES, INTEGERS
from .settings import LIMITS, validate_setting
from .themes import ThemeLibrary, STYLES, apply as apply_theme
GROUPS = {
    'Light': (
        ('brightness','Overall brightness'),('ambient_strength','Ambient fill'),
        ('surface_strength','Surface light'),('fill_strength','Side fill'),
        ('surface_heading','Light heading'),('surface_elevation','Light elevation'),
        ('caustics_strength','Caustic strength'),('caustics_speed','Caustic speed'),
        ('shafts','Light shafts'),('shafts_strength','Shaft strength'),
        ('plant_sway','Plant sway'),('plant_speed','Sway speed')),
    'Cycle': (
        ('mode','Lighting mode'),('timezone','Timezone'),('day_start','Day starts'),
        ('night_start','Night starts'),('transition_minutes','Fade minutes'),
        ('day_brightness','Day brightness'),('night_brightness','Night brightness'),
        ('day_colour','Day tint'),('night_colour','Night tint')),
    'Water': (
        ('background_style','Background'),('background_top','Top / solid colour'),
        ('background_bottom','Bottom colour'),('background_motion','Water motion'),
        ('background_speed','Motion speed'),('background_strength','Motion intensity'),('fog_enabled','Water fog'),
        ('fog_colour','Fog colour'),('fog_density','Fog density'),('sand_tint','Sand tint')),
    'Bubbles': (
        ('column_count','Column count'),('column_placement','Placement'),
        ('column_seed','Position seed'),('column_particles','Total column bubbles'),
        ('column_width','Column spread'),('column_size','Bubble size'),('column_speed','Rise speed'),
        ('bubble_collisions','Deflect around objects'),('bubble_dynamics','Vary bubble movement'),
        ('fish_activity','Fish activity')),
    'Quality': (
        ('scene','Scenery style'),('scale','Render scale'),('detail','Mesh detail'),('plants','Plant count'),
        ('bubbles','Ambient bubbles'),('lighting','Scene lighting'),('caustics','Caustics'),
        ('fps','FPS limit'),('vsync','VSync (restart)')),
}
BOOLS = {'fog_enabled','lighting','caustics','vsync','bubble_collisions','bubble_dynamics'}

QUALITY = set(dict(GROUPS['Quality'])) - {'scene'}

class AppearancePanel:
    def __init__(self,controls,parent):
        self.controls,self.app,self.parent=controls,controls.app,parent
        self.library=ThemeLibrary(Path(self.app.args.settings).parent/'themes')
        self.pages={};self.fields={};self.baseline={};self.buttons={};self.confirming=False
        self.bar=controls.card(parent,0,100,800,44)
        for i,(name,label) in enumerate((('Theme','Theme & fish'),('Light','Lighting & cycle'),('Water','Water & bubbles'))):
            self.buttons[name]=controls.button(self.bar,label,10+i*160,26,154,lambda n=name:self.page(n))
            self.buttons[name]['text_scale']=13
        self.form=controls.card(parent,0,162,490,354)
        theme=DirectFrame(parent=self.form,frameColor=(0,0,0,0));self.pages['Theme']=theme
        controls.label(theme,'Theme & fish',20,34,19)
        controls.label(theme,'Choose a visual style for the display.',20,61,13)
        controls.label(theme,'Aquarium theme',20,105,14)
        items,_=self.library.list();self.theme_names={'Current applied look':'current'}
        self.theme_names.update({item['manifest']['name']+' ['+item['manifest']['id']+']':item['manifest']['id'] for item in items})
        self.theme_menu=controls.menu(theme,list(self.theme_names),24,141,440,self.choose_theme)
        controls.label(theme,'Fish style',20,189,14)
        self.fields['fish_style']=(controls.menu(theme,list(STYLES),24,224,440,lambda _:None),True)
        controls.label(theme,'Scenery style · independent of colour themes',20,271,13)
        self.fields['scene']=(controls.menu(theme,['Tidal Garden','Classic'],24,307,440,lambda _:None),True)
        self.scrollers={}
        for name,groups in (('Light',('Light','Cycle')),('Water',('Water','Bubbles')),('Quality',('Quality',))):
            items=[(key,label) for group in groups for key,label in GROUPS[group] if key!='scene']
            frame=DirectScrolledFrame(parent=self.form,frameSize=(0,490,-354,0),canvasSize=(0,466,-(len(items)*54+56),0),
                scrollBarWidth=14,frameColor=(.08,.185,.21,1),autoHideScrollBars=True,
                horizontalScroll_scrollSize=0,verticalScroll_scrollSize=.12)
            self.pages[name]=frame;self.scrollers[name]=frame
            controls.label(frame.getCanvas(),{'Light':'Lighting & cycle','Water':'Water & bubbles','Quality':'Advanced quality · separate save'}[name],20,32,18)
            for row,(key,label) in enumerate(items):
                y=74+row*54;canvas=frame.getCanvas();controls.label(canvas,label,20,y,14)
                value=self.value(key);choices=('off','on') if key in BOOLS else CHOICES.get(key)
                if key=='mode':choices=('static','clock')
                if choices:
                    shown=('on' if value else 'off') if key in BOOLS else value
                    widget=controls.menu(canvas,list(choices),254,y,195,lambda _:None,list(choices).index(shown) if shown in choices else 0)
                else:widget=controls.entry(canvas,str(value),254,y,195)
                self.fields[key]=(widget,bool(choices))
                if not choices:
                    hint=('–'.join(map(str,RANGES[key])) if key in RANGES else '–'.join(map(str,LIMITS[key][:2])) if key in LIMITS else 'local or Europe/London' if key=='timezone' else 'HH:MM (24h)' if key in ('day_start','night_start') else 'classic or #RRGGBB' if key=='fog_colour' else '#RRGGBB')
                    controls.label(canvas,hint,254,y+19,10)
        self.preview_card=controls.card(parent,512,162,288,354)
        controls.label(self.preview_card,'Preview',20,34,19)
        controls.label(self.preview_card,'Applied scene · refreshes each second',20,63,13)
        self.preview_image=DirectFrame(parent=self.preview_card,frameColor=(.06,.14,.16,1),frameSize=(0,248,-110,0),pos=(20,0,-81))
        self.preview_empty=controls.label(self.preview_image,'Open an aquarium window to preview.',12,48,12,220)
        self._preview_texture=None;self._next_preview=0
        controls.label(self.preview_card,'Preview time',20,214,13)
        for i,(name,value) in enumerate((('Day',1),('Night',0),('Current',None))):
            controls.button(self.preview_card,name,20+i*84,252,78,lambda v=value:self.preview(v))
        self.preview_status=controls.label(self.preview_card,'Current time · Applied settings',20,292,12,246)
        controls.label(self.preview_card,'Preview changes the view immediately,\nwithout saving any edits.',20,325,12,246)
        self.actions=DirectFrame(parent=controls.root,frameColor=(.035,.09,.105,1),frameSize=(0,820,-145,0),pos=(254,0,-625))
        self.dirty_label=controls.label(self.actions,'All changes saved',0,10,15,790)
        self.scope=controls.label(self.actions,'Apply & save affects appearance across all three tabs.',0,38,12,790)
        self.reset_button=controls.button(self.actions,'Reset edits',0,83,145,self.reset)
        self.cancel_button=controls.button(self.actions,'Cancel',155,83,115,self.cancel_reset);self.cancel_button.hide()
        self.apply_button=controls.button(self.actions,'Apply & save',288,83,202,self.apply)
        self.apply_button['frameColor']=(.79,.70,.49,1);self.apply_button['text_fg']=(.05,.12,.13,1)
        self.note=controls.label(self.actions,'Theme library actions and advanced quality save separately.',0,127,12,790)
        self.refresh();self.page('Theme')

    def value(self,key):
        if key=='scene':return {'tidal-garden':'Tidal Garden','classic':'Classic'}[self.app.settings.scene]
        if key=='fish_style' or key in QUALITY:return getattr(self.app.settings,key)
        return getattr(self.app.settings.appearance,key)

    def refresh(self):
        # Explicit discard/rebase only, never called by sidebar navigation.
        for key,(widget,menu) in self.fields.items():
            value=self.value(key)
            if menu:
                value=('on' if value else 'off') if key in BOOLS else value
                if value in widget['items']:widget.set(value,fCommand=0)
            else:widget.enterText(str(value))
        self.theme_menu.set('Current applied look',fCommand=0)
        self.baseline={key:widget.get().strip() for key,(widget,_) in self.fields.items()}
        self.cancel_reset();self.update_dirty()

    def changes(self,quality=False):
        return {key:widget.get().strip() for key,(widget,_) in self.fields.items()
                if (key in QUALITY)==quality and widget.get().strip()!=self.baseline.get(key)}

    def choose_theme(self,label):
        if not hasattr(self,'theme_menu') or not self.baseline:return
        key=self.theme_names[label]
        if key=='current':return  # Not a discard command: use Reset edits deliberately.
        try:
            candidate=apply_theme(self.app.settings,self.library.read(key))
            for field in self.fields:
                if field in QUALITY or field=='scene':continue
                value=candidate.fish_style if field=='fish_style' else getattr(candidate.appearance,field)
                widget,menu=self.fields[field]
                if menu:widget.set(('on' if value else 'off') if field in BOOLS else value,fCommand=0)
                else:widget.enterText(str(value))
            self.note['text']='Theme copied into the draft. Apply & save to use it.';self.note.resetFrameSize()
        except (ValueError,OSError) as exc:self.note['text']=str(exc);self.note.resetFrameSize()
        self.update_dirty()

    def page(self,name):
        name={'Cycle':'Light','Bubbles':'Water'}.get(name,name)
        self.controls.blur()
        for key,page in self.pages.items():page.show() if key==name else page.hide()
        for key,button in self.buttons.items():button['frameColor']=(.17,.32,.33,1) if key==name else (.08,.17,.19,1)
        self.active=name;self.cancel_reset()
        self.scope['text']='Apply quality saves only edited performance fields.' if name=='Quality' else 'Apply & save affects appearance across all three tabs.'
        self.apply_button['text']='Apply quality & save' if name=='Quality' else 'Apply & save'
        self.update_dirty()

    def candidate(self,quality=None):
        if quality is None:quality=self.active=='Quality'
        settings=deepcopy(self.app.settings);appearance=asdict(settings.appearance)
        changed=self.changes(quality)
        for key,raw in changed.items():
            try:
                if key=='scene':value={'Tidal Garden':'tidal-garden','Classic':'classic'}[raw]
                elif key in BOOLS:value=raw=='on'
                elif key in INTEGERS or key in ('detail','plants','bubbles','fps'):value=int(raw)
                elif key in RANGES or key=='scale':value=float(raw)
                else:value=raw
                if key in QUALITY or key=='scene':setattr(settings,key,validate_setting(key,value))
                elif key=='fish_style':
                    if value not in STYLES:raise ValueError('Unknown fish style')
                    settings.fish_style=value
                else:appearance[key]=value
            except ValueError as exc:raise ValueError(f'{key}: {exc}') from None
        extra=getattr(settings.appearance,'_extra',{})
        settings.appearance=Appearance.from_dict(appearance);settings.appearance._extra=extra
        if quality and changed:settings.preset='custom'
        if not quality and changed:settings.theme_id='current'
        return settings

    def apply(self):
        quality=self.active=='Quality'
        try:
            restart=self.app.appearance.apply_settings(self.candidate(quality))
            # Rebase only this save scope: unsaved quality / appearance remains intact.
            for key,(widget,_) in self.fields.items():
                if (key in QUALITY)==quality:self.baseline[key]=widget.get().strip()
            self.note['text']='Saved. VSync changes need restart.' if restart else 'Saved. '+self.app.appearance.status+' · '+self.app.columns.status
            self.note.resetFrameSize();self.cancel_reset();self.update_dirty()
            if hasattr(self.app,'scale_slider'):self.app.scale_slider['value']=self.app.settings.scale
        except (ValueError,OSError) as exc:
            self.note['text']=str(exc)[:130];self.note.resetFrameSize()

    def update_dirty(self):
        if not hasattr(self,'dirty_label'):return
        # Rebase untouched fields after immediate saves in other controllers.
        for key,(widget,menu) in self.fields.items():
            if widget.get().strip()!=self.baseline.get(key):continue
            value=self.value(key);value=('on' if value else 'off') if key in BOOLS else str(value)
            if value!=self.baseline.get(key):
                if menu:widget.set(value,fCommand=0)
                else:widget.enterText(value)
                self.baseline[key]=value
        count=len(self.changes())+len(self.changes(True));self.dirty=bool(count)
        self.dirty_label['text']=f'Unsaved changes · {count} edited '+('field' if count==1 else 'fields') if count else 'All changes saved'
        self.dirty_label['text_fg']=(.88,.77,.52,1) if count else (.59,.76,.72,1)
        self.dirty_label.resetFrameSize()

    def refresh_preview(self):
        # Outputs have independent GL contexts: never sample another context's
        # render texture directly (it can silently appear black). A bounded
        # readback refreshes only while this page is visible, without new targets.
        if getattr(self.controls,'active_page',None)!='Appearance' or not self.app.panel_visible:return
        now=time.monotonic()
        if now<self._next_preview:return
        self._next_preview=now+1
        view=next((v for v in self.app.views if v.buffer),None)
        if not view:
            self.preview_image['image']=None;self.preview_empty.show();return
        image=PNMImage()
        if not view.buffer.getScreenshot(image):return
        ratio=image.getXSize()/max(1,image.getYSize())
        pw=min(248,110*ratio);ph=pw/ratio
        small=PNMImage(max(1,round(pw)),max(1,round(ph)));small.quickFilterFrom(image)
        if self._preview_texture is None:
            self._preview_texture=Texture('applied-scene-preview')
        if self.preview_image['image']!=self._preview_texture:self.preview_image['image']=self._preview_texture
        self.preview_image['image_scale']=(pw/2,1,ph/2)
        self.preview_image['image_pos']=(124,0,-55)
        self._preview_texture.load(small);self.preview_empty.hide()

    def preview(self,value):
        self._next_preview=0
        self.app.appearance.preview=value;self.app.appearance.update(0,force=True)
        self.preview_status['text']=('Current time' if value is None else 'Day' if value else 'Night')+' · Applied settings'
        self.preview_status.resetFrameSize()
        self.note['text']=self.app.appearance.status+' · preview is not saved';self.note.resetFrameSize()

    def reset(self):
        self.update_dirty()
        if not self.dirty:return
        if not self.confirming:
            self.confirming=True;self.reset_button['text']='Discard edits?';self.reset_button['frameColor']=(.49,.25,.22,1)
            self.cancel_button.show();self.note['text']='Discard all appearance and quality edits? Click Discard edits again, or Cancel.';self.note.resetFrameSize()
            return
        self.refresh();self.note['text']='Edits reset to currently applied settings. Nothing saved.';self.note.resetFrameSize()

    def cancel_reset(self):
        self.confirming=False
        if hasattr(self,'reset_button'):
            self.reset_button['text']='Reset edits';self.reset_button['frameColor']=(.10,.22,.25,1);self.cancel_button.hide()

    def resize(self,width,height):
        narrow=width<800
        self.bar['frameSize']=(0,max(490,width-16),-44,0)
        self.preview_card.setPos(0 if narrow else 512,0,-(546 if narrow else 162))
        # At small sizes the page scrolls without reducing text size.
        return 820 if narrow else 440

    def draft_defaults(self):
        # Former Restore Classic action is now a draft, never an immediate write.
        defaults=Appearance()
        for key,(widget,menu) in self.fields.items():
            if key in QUALITY or key in ('scene','fish_style'):continue
            value=getattr(defaults,key)
            if menu:widget.set(('on' if value else 'off') if key in BOOLS else value,fCommand=0)
            else:widget.enterText(str(value))
        self.note['text']='Classic appearance defaults drafted. Apply & save to use; quality, scene and fish style retained.'
        self.note.resetFrameSize();self.update_dirty()

    def refresh_theme_choices(self):
        items,warnings=self.library.list();selected=self.theme_menu.get()
        self.theme_names={'Current applied look':'current'}
        self.theme_names.update({item['manifest']['name']+' ['+item['manifest']['id']+']':item['manifest']['id'] for item in items})
        self.theme_menu['items']=list(self.theme_names)
        self.theme_menu.set(selected if selected in self.theme_names else 'Current applied look',fCommand=0)
        if warnings:self.note['text']='; '.join(warnings)[:130];self.note.resetFrameSize()
