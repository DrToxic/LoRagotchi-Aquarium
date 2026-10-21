"""Desktop layout travel preferences, deliberately excluded from themes."""
from .travel import MODES


class TravelPanel:
    def __init__(self,controls,parent):
        self.controls=controls;self.app=controls.app
        controls.label(parent,'TRAVEL BETWEEN WATER AREAS',18,105,12)
        controls.label(parent,'Fish transfers',18,151)
        self.menu=controls.menu(parent,list(MODES),215,151,185,self.choose,
                                MODES.index(self.app.display.transfers))
        controls.label(parent,'Occasional: an attempt every 1–2 minutes.\nFrequent: an attempt every 20–40 seconds.\nEach fish rests at least five minutes between trips.',18,203,13,396)
        controls.label(parent,'Fish swim fully out of one area, then swim into\nanother. One journey at a time; identity, age and\nsaved visits do not change.',18,287,13,396)
        controls.label(parent,'Routes need a clear window edge or rectangular\nblackout. Narrow or crowded areas may have no\nsafe route. Adjacent windows are one tank area.',18,371,13,396)
        self.status=controls.label(parent,'',18,457,13,396)
        controls.button(parent,'Back to animations',18,568,396,lambda:controls.page('Animations'))
        controls.label(parent,'Turning this off lets the current journey finish.\nTurning animations off stops it immediately.',18,610,12,396)

    def choose(self,value):
        self.app.display.transfers=value
        self.app.save_display()
        self.refresh()

    def refresh(self):
        self.menu.set(MODES.index(self.app.display.transfers),fCommand=0)
        travel=self.app.transitions.travel
        travel.refresh()
        status=travel.status
        if not travel.active:
            status='Transfers off' if self.app.display.transfers=='Off' else travel.reason() or status
        self.app.set_ui_text(self.status,status)
