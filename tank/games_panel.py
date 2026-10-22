"""Separate native game page; sending always stays in the owner's mesh chat."""
from dataclasses import asdict
import json
from pathlib import Path
from .games import Game,NAMES


class GamesPanel:
    def __init__(self,controls,parent):
        self.controls=controls;self.app=controls.app;self.game=None
        self.path=Path(self.app.args.settings).with_name('aquarium-game.json')
        controls.button(parent,'Back',18,105,100,lambda:controls.page('Aquarium'))
        self.kind=controls.menu(parent,list(NAMES.values()),18,149,396,lambda _:None)
        controls.button(parent,'New game (player 1)',18,194,190,self.new)
        controls.button(parent,'Join pasted invitation',224,194,190,self.join)
        self.board=controls.label(parent,'Start or join a game.',18,238,18,396)
        controls.label(parent,'Your move: square 1–9 / number / hit or stand',18,365,12)
        self.move=controls.entry(parent,'',18,398,180)
        controls.button(parent,'Play / give clue',224,398,190,self.play)
        controls.label(parent,'Paste received LAG1 message here',18,442,12)
        self.incoming=controls.entry(parent,'',18,474,396)
        controls.button(parent,'Receive turn',18,518,190,self.receive)
        controls.button(parent,'Copy outgoing turn',224,518,190,self.copy)
        self.note=controls.label(parent,'Use a direct chat with the same peer. Nothing is\nsent automatically. Blackjack is open-deck, no stakes.',18,564,12,396)
        controls.label(parent,'Copy the turn into MeshCore Chat / Radio, send it,\nthen paste their reply here. Duplicate turns are safe.',18,625,11,396)
        try:
            if self.path.exists():self.game=Game.restore(json.loads(self.path.read_text()));self.refresh()
        except (ValueError,OSError,TypeError,KeyError):self.note['text']='Saved game could not load; start or join a new game.'

    def refresh(self):
        if self.game:
            self.board['text']=NAMES[self.game.kind]+f' · you are player {self.game.seat+1}\n'+self.game.status()['text']
            self.board.resetFrameSize()
            self.path.parent.mkdir(parents=True,exist_ok=True)
            temp=self.path.with_suffix('.tmp');temp.write_text(json.dumps(asdict(self.game)));temp.replace(self.path)

    def invoke(self,fn):
        try:fn();self.refresh()
        except (ValueError,OSError,KeyError,TypeError) as exc:self.note['text']=str(exc);self.note.resetFrameSize()

    def new(self):
        def create():self.game=Game.new(next(k for k,v in NAMES.items() if v==self.kind.get()))
        self.invoke(create)

    def join(self):
        def create():self.game=Game.parse(self.incoming.get())
        self.invoke(create)

    def play(self):
        if self.game:self.invoke(lambda:self.game.act(self.move.get()))

    def receive(self):
        if self.game:self.invoke(lambda:self.game.receive(self.incoming.get()))

    def copy(self):
        if not self.game:return
        # Use the same platform clipboard helper as the existing theme editor.
        try:
            self.controls.clipboard.copy(self.game.packet())
            self.note['text']='Copied turn. Send it to the same direct-chat peer.'
        except Exception:
            self.incoming.enterText(self.game.packet())
            self.note['text']='Outgoing turn placed in the text field; select and copy it.'
        self.note.resetFrameSize()
