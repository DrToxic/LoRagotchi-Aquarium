"""Native nursery controls; HA uses its Configuration, never viewer input."""
from copy import deepcopy
from .nursery import NurserySettings
from .text import display_text


class NurseryPanel:
    def __init__(self,controls,parent):
        self.controls=controls;self.app=controls.app
        controls.button(parent,'Back to Aquarium',18,105,190,lambda:controls.page('Aquarium'))
        controls.label(parent,'BREEDING CAVE & LOCAL EGGS',18,150,14)
        self.enabled=controls.menu(parent,['off','on'],224,191,170,lambda _:None,int(self.app.settings.nursery.enabled))
        controls.label(parent,'Cave and nursery',18,191,13)
        controls.label(parent,'Automatic pairing',18,233,13)
        self.automatic=controls.menu(parent,['off','on'],224,233,170,lambda _:None,int(self.app.settings.nursery.automatic))
        controls.label(parent,'Capacity (1–12)',18,275,13)
        self.capacity=controls.entry(parent,str(self.app.settings.nursery.capacity),224,275,170)
        controls.label(parent,'Parent rest (minutes)',18,317,13)
        self.cooldown=controls.entry(parent,str(self.app.settings.nursery.cooldown_minutes),224,317,170)
        controls.button(parent,'Save nursery settings',18,360,396,self.save)
        controls.label(parent,'Choose two adults / elders',18,406,13)
        self.first=controls.menu(parent,['No adults'],18,443,396,lambda _:None)
        self.second=controls.menu(parent,['No adults'],18,483,396,lambda _:None)
        self.create=controls.button(parent,'Invite pair to cave',18,530,396,self.breed)
        self.note=controls.label(parent,'',18,572,12,396)
        controls.label(parent,'Eggs stay here across restarts. Parent portraits are\nfrozen at breeding. DX transfer is not connected.',18,624,11,396)
        self.parents=[];self.signature=None

    def refresh(self):
        adults=[f for f in self.app.roster if f.stage>=2]
        signature=tuple((f.owner,f.fish_id,f.name) for f in adults)
        if signature!=self.signature:
            self.signature=signature;self.parents=adults
            items=[f'{i+1}. {display_text(f.name)} · {f.owner[:8]}' for i,f in enumerate(adults)] or ['No adults']
            for j,menu in enumerate((self.first,self.second)):
                menu['items']=items;menu.set(min(j,len(items)-1),fCommand=0)
        self.controls.enabled(self.create,len(adults)>=2 and self.app.settings.nursery.enabled and not self.app.nursery.pending_request)
        self.note['text']=f'{len(self.app.nursery.eggs)} stored eggs · '+self.app.nursery.status
        self.note.resetFrameSize()

    def save(self):
        try:
            settings=deepcopy(self.app.settings)
            settings.nursery=NurserySettings.from_dict(dict(enabled=self.enabled.get()=='on',automatic=self.automatic.get()=='on',capacity=int(self.capacity.get()),cooldown_minutes=int(self.cooldown.get())))
            settings.save(self.app.args.settings);self.app.settings=settings
            self.app.rebuild_scene();self.app.nursery.status='Nursery settings saved; eggs retained'
        except (ValueError,OSError) as exc:self.app.nursery.status=str(exc)

    def breed(self):
        try:
            self.app.nursery.request_pair(self.parents[self.first['selectedIndex']],self.parents[self.second['selectedIndex']])
        except (ValueError,IndexError) as exc:self.app.nursery.status=str(exc)
