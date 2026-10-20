"""Scrollable native decoration toggles in the separate operator window."""
from direct.gui.DirectGui import DirectScrolledFrame, DirectCheckButton
from direct.gui import DirectGuiGlobals as DGG
from .text import display_text


class DecorationPanel:
    def __init__(self,controls,parent):
        self.controls,self.app=controls,controls.app
        controls.label(parent,"SEABED LIBRARY",18,105,12)
        controls.label(parent,"Show objects in the shared panoramic tank.",18,135,13)
        self.scroller=DirectScrolledFrame(parent=parent,frameSize=(0,396,-365,0),
            canvasSize=(0,372,-365,0),pos=(18,0,-155),scrollBarWidth=14,
            frameColor=(.025,.095,.115,1),autoHideScrollBars=True,
            horizontalScroll_scrollSize=0,verticalScroll_scrollSize=.15)
        self.rows=[]
        controls.button(parent,"Refresh library",18,556,154,self.refresh)
        self.note=controls.label(parent,"",18,584,11,396)
        self.rebuild()

    def rebuild(self):
        for row in self.rows:row.destroy()
        self.rows=[]
        library=self.app.decorations
        height=max(365,len(library.items)*74+12)
        self.scroller["canvasSize"]=(0,372,-height,0)
        canvas=self.scroller.getCanvas()
        for i,item in enumerate(library.items.values()):
            available=item.key in library.nodes
            check=DirectCheckButton(parent=canvas,text=display_text(item.name),text_align=0,
                text_scale=14,text_pos=(24,0),text_fg=(.86,.94,.89,1),
                indicatorValue=library.enabled(item) if available else False,
                indicator_scale=12,indicator_pos=(6,0,4),
                frameColor=(0,0,0,0),relief=None,pos=(8,0,-25-i*74),
                command=self.toggle,extraArgs=[item.key],state=DGG.NORMAL if available else DGG.DISABLED)
            self.rows.append(check)
            self.rows.append(self.controls.label(canvas,display_text(item.description),32,49+i*74,11,328))
        self.note["text"]=display_text((library.errors[0][:110] if library.errors else
            f"{len(library.items)} objects · tank/assets/decorations/"))

    def toggle(self,value,key):
        self.app.decorations.set_enabled(key,value)

    def refresh(self):
        self.app.decorations.refresh()
        self.rebuild()
