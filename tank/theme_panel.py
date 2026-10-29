"""Native theme library. Existing Appearance pages remain the visual field editor."""
from copy import deepcopy
from pathlib import Path
from .themes import ThemeLibrary, STYLES, BUILTINS, apply, from_settings, decode, encode, MAX_BYTES


class ThemePanel:
    def __init__(self,controls,parent):
        self.controls,self.app,self.parent=controls,controls.app,parent
        self.library=ThemeLibrary(Path(self.app.args.settings).parent/'themes')
        self.selected='classic';self.revision=None;self.selector=None
        controls.button(parent,'Back to Appearance',18,105,220,lambda:controls.page('Appearance'))
        controls.label(parent,'THEMES & FISH',18,149,13)
        controls.button(parent,'Load theme',18,222,190,self.load)
        controls.button(parent,'Refresh library',224,222,190,self.refresh)
        controls.label(parent,'Fish style',18,269,13)
        self.style=controls.menu(parent,list(STYLES),172,269,242,lambda _:None)
        controls.button(parent,'Apply fish style',18,313,396,self.restyle)
        controls.label(parent,'Custom ID',18,360,13)
        self.key=controls.entry(parent,'my-theme',172,360,242)
        controls.label(parent,'Name',18,402,13)
        self.name=controls.entry(parent,'My theme',172,402,242)
        controls.button(parent,'Save current look as theme',18,446,396,self.save)
        controls.label(parent,'Import / export file path',18,490,13)
        self.path=controls.entry(parent,str(Path(self.app.args.settings).parent/'my-theme.json'),18,522,396)
        controls.button(parent,'Import new theme',18,564,190,self.import_file)
        controls.button(parent,'Export selected',224,564,190,self.export_file)
        self.note=controls.label(parent,'',18,607,11,396)
        controls.button(parent,'Draft Classic appearance defaults',18,644,396,self.defaults)
        self.refresh()

    def status(self,text):self.note['text']=str(text)[:130];self.note.resetFrameSize()

    def refresh(self):
        items,warnings=self.library.list();self.items={item['manifest']['id']:item for item in items}
        if self.selected not in self.items:self.selected='classic'
        if self.selector:self.selector.destroy()
        keys=list(self.items)
        self.selector=self.controls.menu(self.parent,keys,18,183,396,self.select,keys.index(self.selected))
        self.style.set(self.app.settings.fish_style,fCommand=0)
        self.select(self.selected)
        if warnings:self.status('; '.join(warnings))

    def select(self,key):
        self.selected=key;item=self.items[key];raw=item['manifest'];self.revision=item['revision']
        self.key.enterText('my-'+key if item['builtin'] else key)
        self.name.enterText('My '+raw['name'] if item['builtin'] else raw['name'])
        self.status(raw['name']+(' · built-in; save under a new ID to duplicate.' if item['builtin'] else ' · custom theme.'))

    def load(self):
        try:
            raw=self.library.read(self.selected)
            self.app.appearance.apply_settings(apply(self.app.settings,raw));self.refresh()
            self.status('Loaded '+raw['name']+'. Quality and schedule retained.')
        except (ValueError,OSError) as exc:self.status(exc)

    def restyle(self):
        settings=deepcopy(self.app.settings);settings.fish_style=self.style.get();settings.theme_id='current'
        try:self.app.appearance.apply_settings(settings);self.status('Fish style saved. Received colours and fish identity retained.')
        except (ValueError,OSError) as exc:self.status(exc)

    def save(self):
        try:
            settings=deepcopy(self.app.settings);settings.fish_style=self.style.get()
            key=self.key.get().strip();raw=from_settings(settings,key,self.name.get())
            self.library.save(raw,self.revision if key==self.selected else None)
            self.selected=key;self.refresh();self.status('Saved custom theme. Load to apply its fish style.')
        except (ValueError,OSError) as exc:self.status(exc)

    def import_file(self):
        try:
            with Path(self.path.get()).expanduser().open('rb') as stream:raw=decode(stream.read(MAX_BYTES+1))
            self.library.save(raw);self.selected=raw['id'];self.refresh();self.status('Imported. Load theme to apply.')
        except (ValueError,OSError) as exc:self.status(exc)

    def export_file(self):
        try:
            raw=self.library.read(self.selected)
            # Exclusive creation avoids silently overwriting any unrelated user file.
            with Path(self.path.get()).expanduser().open('xb') as stream:stream.write(encode(raw))
            self.status('Exported selected theme only. Use a new path for another export.')
        except (ValueError,OSError) as exc:self.status(exc)

    def defaults(self):
        self.controls.appearance.draft_defaults()
        self.controls.page('Appearance')
