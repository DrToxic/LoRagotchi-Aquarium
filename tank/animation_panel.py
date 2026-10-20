"""Native lifecycle preferences; no fake radio events or destructive previews."""
from direct.gui.DirectGui import DirectCheckButton
from .transitions import STYLES, STYLE_NAMES


class AnimationPanel:
    def __init__(self,controls,parent):
        self.app=controls.app
        controls.label(parent,"FISH ARRIVALS & DEPARTURES",18,105,12)
        self.check(parent,"Animate arrivals, updates and exits",18,149,
                   self.app.settings.fish_animations,self.toggle)
        controls.label(parent,"New fish swim in from above. Updates take the old\nfish out first, then bring in its latest appearance.",18,191,13,396)
        controls.label(parent,"RANDOM EXIT STYLES",18,257,12)
        self.checks={}
        for i,(style,name) in enumerate(zip(STYLES,STYLE_NAMES)):
            self.checks[style]=self.check(parent,name,18,295+i*42,
                self.app.settings.exit_styles.get(style,True),self.style,[style])
        controls.label(parent,"All styles off: fish simply swim up and out.\nPickups already in progress finish their sequence.\nUp to four exits at once; other fish keep swimming.",
                       18,530,12,396)
        controls.label(parent,"Visual only. Saved copies and radio returns are unchanged.",18,589,11,396)

    def check(self,parent,text,x,y,value,command,args=None):
        return DirectCheckButton(parent=parent,text=text,text_align=0,text_scale=14,
            text_pos=(26,0),text_fg=(.86,.94,.89,1),indicatorValue=value,
            indicator_scale=12,indicator_pos=(7,0,4),frameColor=(0,0,0,0),relief=None,
            pos=(x,0,-y),command=command,extraArgs=args or [])

    def toggle(self,value):
        self.app.settings.fish_animations=bool(value)
        self.app.sync_models()
        self.app.settings.save(self.app.args.settings)

    def style(self,value,key):
        self.app.settings.exit_styles[key]=bool(value)
        self.app.settings.save(self.app.args.settings)
