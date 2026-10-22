"""Native dynamic scenery controls; requested and effective visibility differ."""
from direct.gui.DirectGui import DirectScrolledFrame, DirectCheckButton
from direct.gui import DirectGuiGlobals as DGG
from .text import display_text


def scenery_category(key):
    """Classify both Classic and namespaced scene-study placement identities."""
    if not key.startswith('reef:'):return None
    kind=key.removeprefix('reef:').removeprefix('study:').split(':')[0]
    return 'Plants' if kind in ('plant','grass') else 'Reef'


def scenery_name(key):
    if not key.startswith('reef:study:'):
        return key.removeprefix('reef:').replace(':',' ').title()
    kind,_,index=key.removeprefix('reef:study:').partition(':')
    name={'rock':'Limestone','distant':'Distant reef','plate':'Plate coral',
          'fan':'Sea fan','sponge':'Tube sponge','colony':'Coral colony',
          'grass':'Seagrass','rubble':'Reef pebble'}.get(kind,kind.title())
    return f'{name} {int(index)+1}' if index.isdigit() else name


class DecorationPanel:
    def __init__(self,controls,parent):
        self.controls,self.app=controls,controls.app
        self.category='Library';self.rows=[];self.status_labels={}
        controls.label(parent,'SCENERY PLACEMENT',18,105,12)
        self.protect=controls.button(parent,'',18,140,396,self.toggle_protection)
        for name,x in (('Library',18),('Reef',150),('Plants',288)):
            controls.button(parent,name,x,180,126,lambda n=name:self.choose(n))
        self.scroller=DirectScrolledFrame(parent=parent,frameSize=(0,396,-334,0),
            canvasSize=(0,372,-334,0),pos=(18,0,-204),scrollBarWidth=14,
            frameColor=(.025,.095,.115,1),autoHideScrollBars=True,
            horizontalScroll_scrollSize=0,verticalScroll_scrollSize=.15)
        controls.button(parent,'Refresh library',18,570,190,self.refresh)
        controls.button(parent,'Reset auto positions',224,570,190,self.reset)
        self.note=controls.label(parent,'',18,604,11,396)
        self.rebuild()

    def choose(self,name):
        self.category=name;self.rebuild();self.scroller.verticalScroll['value']=0

    def rebuild(self):
        for row in self.rows:
            self.app._ui_text.pop(id(row),None)
            row.destroy()
        self.rows=[];self.status_labels={}
        library=self.app.decorations;placement=self.app.placement
        if self.category=='Library':keys=['decoration:'+key for key in library.items]
        else:keys=[k for k in placement.records if scenery_category(k)==self.category]
        self.scroller['canvasSize']=(0,372,-max(334,len(keys)*94+12),0)
        canvas=self.scroller.getCanvas()
        for i,key in enumerate(keys):
            record=placement.records.get(key);item=library.items.get(key.removeprefix('decoration:'))
            name=item.name if item else scenery_name(key)
            y=25+i*94
            if item:
                check=DirectCheckButton(parent=canvas,text=display_text(name),text_align=0,
                    text_scale=14,text_pos=(24,0),text_fg=(.86,.94,.89,1),
                    indicatorValue=library.enabled(item) if record else False,
                    indicator_scale=12,indicator_pos=(6,0,4),frameColor=(0,0,0,0),relief=None,
                    pos=(8,0,-y),command=self.toggle,extraArgs=[item.key],
                    state=DGG.NORMAL if record else DGG.DISABLED)
                self.rows.append(check)
            else:self.rows.append(self.controls.label(canvas,name,12,y,14))
            pin=self.controls.button(canvas,'Pinned' if placement.pinned(key) else 'Auto',266,y,90,
                                     lambda k=key:self.pin(k))
            self.controls.enabled(pin,record is not None);self.rows.append(pin)
            label=self.controls.label(canvas,'',12,y+27,11,344)
            label['frameSize']=(0,344,-31,12)
            self.rows.append(label);self.status_labels[key]=label
        if not keys:
            text=('No plants in this scene. Set Plant count in Appearance > Quality.' if self.category=='Plants'
                  else 'No scenery in this category.')
            self.rows.append(self.controls.label(canvas,text,12,25,12,344))
        self.refresh_status()

    def refresh_status(self):
        p=self.app.placement
        self.app.set_ui_text(self.protect,'Keep scenery out of deadzones: '+('on' if self.app.display.protect_scenery else 'off'))
        for key,label in self.status_labels.items():
            record=p.records.get(key)
            if record is None:text='Asset unavailable'
            elif not record.visible:text=record.reason
            else:
                moved=any(abs(a-b)>.02 for a,b in zip(record.position,record.authored))
                text=('Relocated' if moved else 'Preferred position')+' · '+('floor' if record.support=='floor' else 'shelf')
                text+='\n'+', '.join(f'{v:.1f}' for v in record.position)
            self.app.set_ui_text(label,text)
        self.app.set_ui_text(self.note,display_text(self.app.decorations.errors[0][:100] if self.app.decorations.errors else
            p.status+'\nAuto moves only when needed; pinned conflicts wait for space.'))

    def toggle(self,value,key):
        self.app.decorations.set_enabled(key,value);self.app.save_display();self.refresh_status()

    def pin(self,key):
        self.app.placement.pin(key,not self.app.placement.pinned(key));self.rebuild()

    def toggle_protection(self):
        self.app.display.protect_scenery=not self.app.display.protect_scenery
        self.app.save_display();self.refresh_status()

    def reset(self):self.app.placement.reset();self.rebuild()

    def refresh(self):
        self.app.decorations.refresh();self.rebuild()
