"""Compact native appearance editor; validation precedes saving or scene changes."""
from copy import deepcopy
from dataclasses import asdict
from direct.gui.DirectGui import DirectFrame, DirectScrolledFrame
from .appearance import Appearance, CHOICES, RANGES, INTEGERS
from .settings import LIMITS, validate_setting


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
        ('background_bottom','Bottom colour'),('fog_enabled','Water fog'),
        ('fog_colour','Fog colour'),('fog_density','Fog density'),('sand_tint','Sand tint')),
    'Bubbles': (
        ('column_count','Column count'),('column_placement','Placement'),
        ('column_seed','Position seed'),('column_particles','Total column bubbles'),
        ('column_width','Column spread'),('column_size','Bubble size'),('column_speed','Rise speed')),
    'Quality': (
        ('scene','Scenery style'),('scale','Render scale'),('detail','Mesh detail'),('plants','Plant count'),
        ('bubbles','Ambient bubbles'),('lighting','Scene lighting'),('caustics','Caustics'),
        ('fps','FPS limit'),('vsync','VSync (restart)')),
}
BOOLS = {'fog_enabled','lighting','caustics','vsync'}


class AppearancePanel:
    def __init__(self, controls, parent):
        self.controls,self.app=controls,controls.app
        controls.button(parent,'Back to Aquarium',18,105,188,lambda:controls.page('Aquarium'))
        controls.button(parent,'Themes & fish',224,105,190,lambda:controls.page('Themes'))
        self.pages={};self.fields={};self.buttons={}
        for i,(name,items) in enumerate(GROUPS.items()):
            self.buttons[name]=controls.button(parent,name,18+i*80,145,77,lambda n=name:self.page(n))
            self.buttons[name]['text_scale']=12
            frame=DirectScrolledFrame(parent=parent,frameSize=(0,396,-360,0),
                canvasSize=(0,372,-max(360,len(items)*43+28),0),pos=(18,0,-164),
                scrollBarWidth=14,frameColor=(.025,.095,.115,1),autoHideScrollBars=True,
                horizontalScroll_scrollSize=0,verticalScroll_scrollSize=.1)
            self.pages[name]=frame
            for row,(key,label) in enumerate(items):
                y=30+row*43;canvas=frame.getCanvas()
                controls.label(canvas,label,10,y,13)
                value=self.value(key)
                choices=('Tidal Garden','Classic') if key=='scene' else ('off','on') if key in BOOLS else CHOICES.get(key)
                if choices:
                    # Desktop has no HA credential/API connection. HA sun is offered
                    # only in HA Configuration, with a real observer behind it.
                    if key=='mode':choices=('static','clock')
                    shown=('on' if value else 'off') if key in BOOLS else value
                    if shown not in choices:shown=choices[0]
                    widget=controls.menu(canvas,list(choices),190,y,156,lambda _:None,list(choices).index(shown))
                else:widget=controls.entry(canvas,str(value),190,y,156)
                self.fields[key]=(widget,bool(choices))
                hint=('–'.join(map(str,RANGES[key])) if key in RANGES else
                      '–'.join(map(str,LIMITS[key][:2])) if key in LIMITS else
                      'local or Europe/London' if key=='timezone' else
                      'HH:MM (24h)' if key in ('day_start','night_start') else
                      'classic or #RRGGBB' if key=='fog_colour' else '#RRGGBB')
                if not choices:controls.label(canvas,hint,190,y+16,9)
        controls.button(parent,'Preview day',18,556,125,lambda:self.preview(1))
        controls.button(parent,'Preview night',153,556,125,lambda:self.preview(0))
        controls.button(parent,'Current time',288,556,126,lambda:self.preview(None))
        controls.button(parent,'Apply & save',18,598,190,self.apply)
        controls.button(parent,'Reset appearance',224,598,190,self.reset)
        self.note=controls.label(parent,'Colours use #RRGGBB. Apply saves all pages.',18,630,11,396)
        self.page('Light')

    def value(self,key):
        if key=='scene':return {'tidal-garden':'Tidal Garden','classic':'Classic'}[self.app.settings.scene]
        return getattr(self.app.settings,key) if key in dict(GROUPS['Quality']) else getattr(self.app.settings.appearance,key)

    def page(self,name):
        self.controls.blur()
        for key,page in self.pages.items():
            page.show() if key==name else page.hide()
        self.active=name

    def refresh(self):
        for key,(widget,menu) in self.fields.items():
            value=self.value(key)
            if menu:
                value=('on' if value else 'off') if key in BOOLS else value
                if value in widget['items']:widget.set(value,fCommand=0)
            else:widget.enterText(str(value))

    def candidate(self):
        settings=deepcopy(self.app.settings)
        appearance=asdict(settings.appearance)
        quality=dict(GROUPS['Quality'])
        for key,(widget,_) in self.fields.items():
            raw=widget.get().strip()
            try:
                if key=='scene':value={'Tidal Garden':'tidal-garden','Classic':'classic'}[raw]
                elif key in BOOLS:value=raw=='on'
                elif key in INTEGERS or key in ('detail','plants','bubbles','fps'):value=int(raw)
                elif key in RANGES or key=='scale':value=float(raw)
                else:value=raw
                if key in quality:setattr(settings,key,validate_setting(key,value))
                else:appearance[key]=value
            except ValueError as exc:raise ValueError(f'{key}: {exc}') from None
        extra=getattr(settings.appearance,'_extra',{})
        settings.appearance=Appearance.from_dict(appearance)
        settings.appearance._extra=extra
        if any(getattr(settings,k)!=getattr(self.app.settings,k) for k in quality if k!='scene'):settings.preset='custom'
        if appearance!=asdict(self.app.settings.appearance):settings.theme_id="current"
        return settings

    def apply(self):
        try:
            restart=self.app.appearance.apply_settings(self.candidate())
            self.note['text']='Saved. VSync changes need restart.' if restart else 'Saved. '+self.app.appearance.status+' · '+self.app.columns.status
            self.note.resetFrameSize()
            if hasattr(self.app,'scale_slider'):self.app.scale_slider['value']=self.app.settings.scale
        except (ValueError,OSError) as exc:
            self.note['text']=str(exc)[:155];self.note.resetFrameSize()

    def preview(self,value):
        # Unsaved edits are deliberately not smuggled into persisted settings.
        self.app.appearance.preview=value
        self.app.appearance.update(0,force=True)
        self.note['text']=self.app.appearance.status+' · preview is not saved'
        self.note.resetFrameSize()

    def reset(self):
        # Reset appearance only, never quality, fish, windows or radio preferences.
        settings=deepcopy(self.app.settings);settings.appearance=Appearance();settings.theme_id="classic"
        try:self.app.appearance.apply_settings(settings)
        except OSError as exc:self.note['text']=str(exc)[:155];return
        self.app.appearance.preview=None
        self.app.appearance.update(0,force=True)
        self.refresh();self.note['text']='Classic appearance restored; quality settings retained.'
        self.note.resetFrameSize()
