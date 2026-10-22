"""Small, casual, two-player games over copy/paste MeshCore direct messages.

No radio ownership, auto-send, stakes or firmware changes. Messages include the
complete bounded turn history, so duplicates/loss can be repaired by resending.
The chat transport/user verifies the sender; LAG1 is not an authentication layer.
"""
from dataclasses import dataclass,field,asdict
import hashlib
import secrets

NAMES={'t':'Noughts & crosses','g':'Guess the number','b':'Open-deck blackjack'}


def token(value,length):
    return isinstance(value,str) and len(value)==length and all(c in '0123456789abcdef' for c in value)


def commitment(number,nonce):return hashlib.sha256(f'{number}:{nonce}'.encode()).hexdigest()[:24]


def deck(ident):
    # Specified hash ordering, identical across Python/OS versions. Deliberately
    # open-deck: either peer can inspect it; no money, concealed cards or wagers.
    return sorted(range(52),key=lambda card:hashlib.sha256(f'{ident}:{card}'.encode()).digest())


def score(cards):
    ranks=[min(c%13+1,10) for c in cards];value=sum(ranks)
    if 1 in ranks and value+10<=21:value+=10
    return value


@dataclass
class Game:
    kind: str
    ident: str
    seat: int
    moves: list=field(default_factory=list)
    commit: str='-'
    reveal: str='-'
    secret: str=''

    @classmethod
    def new(cls,kind):
        if kind not in NAMES:raise ValueError('Unknown game')
        game=cls(kind,secrets.token_hex(8),0)
        if kind=='g':
            number=secrets.randbelow(20)+1;nonce=secrets.token_hex(6)
            game.secret=f'{number},{nonce}';game.commit=commitment(number,nonce)
        return game

    @classmethod
    def parse(cls,text,seat=1):
        if not isinstance(text,str) or len(text.encode())>160:raise ValueError('Game messages must fit 160 bytes')
        parts=text.strip().split('|')
        if len(parts)!=7 or parts[0]!='LAG1':raise ValueError('Paste a complete LAG1 game message')
        _,kind,ident,commit,moves,reveal,version=parts
        if kind not in NAMES or not token(ident,16) or version!='1':raise ValueError('Unsupported game message')
        if seat not in (0,1) or type(seat) is not int:raise ValueError('Choose player 1 or 2')
        if (kind=='g' and not token(commit,24)) or (kind!='g' and (commit!='-' or reveal!='-')):
            raise ValueError('Invalid game commitment')
        game=cls(kind,ident,seat,[] if moves=='-' else moves.split('.'),commit,reveal)
        if len(game.moves)>32:raise ValueError('Too many turns')
        game.status()  # Validate the entire history before accepting anything.
        return game

    @classmethod
    def restore(cls,raw):
        if not isinstance(raw,dict) or raw.keys()-set(cls.__dataclass_fields__):raise ValueError('Invalid saved game')
        game=cls(**raw)
        validated=cls.parse(game.packet(),game.seat)
        if game.secret:
            number,nonce=game.secret.split(',');number=int(number)
            if game.kind!='g' or game.seat!=0 or not 1<=number<=20 or not token(nonce,12) or commitment(number,nonce)!=game.commit:
                raise ValueError('Invalid private guessing-game state')
        validated.secret=game.secret
        return validated

    def packet(self):
        text='|'.join(('LAG1',self.kind,self.ident,self.commit,'.'.join(self.moves) or '-',self.reveal,'1'))
        if len(text.encode())>160:raise ValueError('Game message exceeds radio budget')
        return text

    def status(self):
        if self.kind=='t':
            board=['·']*9;winner=None
            for i,move in enumerate(self.moves):
                if winner is not None or move not in '123456789' or len(move)!=1:raise ValueError('Invalid board history')
                pos=int(move)-1
                if board[pos]!='·':raise ValueError('Square already occupied')
                mark='XO'[i%2];board[pos]=mark
                if any(all(board[j]==mark for j in line) for line in ((0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6))):winner=i%2
            done=winner is not None or len(self.moves)==9
            text='\n'.join('  '.join(board[i:i+3]) for i in (0,3,6))
            result=('Player '+str(winner+1)+' wins') if winner is not None else 'Draw' if done else 'Player '+str(len(self.moves)%2+1)+' to move'
            return dict(turn=None if done else len(self.moves)%2,done=done,text=text+'\n'+result,board=board)
        if self.kind=='g':
            low,high=1,20;guesses=0;last=None;finished=False
            for i,move in enumerate(self.moves):
                if finished:raise ValueError('Moves after game ended')
                if i%2==0:
                    if not move.isdecimal() or str(int(move))!=move or not low<=int(move)<=high:raise ValueError('Guess outside remaining range')
                    last=int(move);guesses+=1
                else:
                    if move not in ('h','l','c'):raise ValueError('Invalid clue')
                    if move=='h':low=last+1
                    elif move=='l':high=last-1
                    finished=move=='c' or guesses==10
                    if low>high:raise ValueError('Contradictory clues')
            if self.reveal!='-':
                try:number,nonce=self.reveal.split(',');number=int(number)
                except (ValueError,TypeError):raise ValueError('Invalid reveal') from None
                if not finished or not 1<=number<=20 or not token(nonce,12) or commitment(number,nonce)!=self.commit:
                    raise ValueError('Reveal does not match the invitation')
                for i in range(1,len(self.moves),2):
                    guess=int(self.moves[i-1]);expected='c' if guess==number else 'h' if guess<number else 'l'
                    if self.moves[i]!=expected:raise ValueError('Host gave an incorrect clue')
            elif finished:raise ValueError('Finished game must reveal its committed number')
            result=('Number verified: '+str(number)) if finished else f'Guess {low}–{high} · {guesses} guesses'
            return dict(turn=None if finished else (1 if len(self.moves)%2==0 else 0),done=finished,text=result,range=[low,high])
        cards=deck(self.ident);hands=[cards[:2],cards[2:4]];cursor=4;stood=[False,False];turn=0
        for move in self.moves:
            if all(stood) or move not in ('h','s'):raise ValueError('Invalid blackjack history')
            if move=='h':
                hands[turn].append(cards[cursor]);cursor+=1
                if score(hands[turn])>=21:stood[turn]=True
            else:stood[turn]=True
            other=1-turn
            if not stood[other]:turn=other
        done=all(stood)
        totals=[score(h) for h in hands]
        valid=[v if v<=21 else 0 for v in totals]
        result=('Draw' if valid[0]==valid[1] else 'Player '+str(1 if valid[0]>valid[1] else 2)+' wins') if done else f'Player {turn+1}: hit or stand'
        return dict(turn=None if done else turn,done=done,text=f'Player 1: {totals[0]}  ·  Player 2: {totals[1]}\n'+result,hands=hands,totals=totals)

    def act(self,move):
        state=self.status()
        if state['done'] or state['turn']!=self.seat:raise ValueError('Wait for the other player')
        move=str(move).strip().lower()
        copy=Game.restore(asdict(self))
        if self.kind=='g' and self.seat==0:
            if not self.secret:raise ValueError('Host recovery needs its private saved game')
            number,_=self.secret.split(',');guess=int(self.moves[-1]);number=int(number)
            move='c' if guess==number else 'h' if guess<number else 'l'
            copy.moves.append(move)
            if move=='c' or len(copy.moves)==20:copy.reveal=self.secret
        else:
            if self.kind=='b':move={'hit':'h','stand':'s'}.get(move,move)
            copy.moves.append(move)
        copy.status();copy.packet()
        self.moves,self.reveal=copy.moves,copy.reveal
        return self.packet()

    def receive(self,text):
        incoming=Game.parse(text,self.seat)
        if (incoming.kind,incoming.ident,incoming.commit)!=(self.kind,self.ident,self.commit):raise ValueError('Message belongs to a different game')
        common=min(len(self.moves),len(incoming.moves))
        if self.moves[:common]!=incoming.moves[:common]:raise ValueError('Conflicting turn history; game unchanged')
        if len(incoming.moves)<=len(self.moves):return 'Duplicate / older message; no change'
        if self.status()['turn']==self.seat:raise ValueError('Remote message attempted to play your turn')
        # A peer can make several consecutive blackjack moves after we stand.
        trial=Game.restore(asdict(self))
        for move in incoming.moves[len(self.moves):]:
            if trial.status()['turn']==self.seat:raise ValueError('Remote message attempted to play your turn')
            trial.moves.append(move)
            trial.reveal=incoming.reveal if len(trial.moves)==len(incoming.moves) else '-'
            trial.status()
        self.moves,self.reveal=incoming.moves,incoming.reveal
        return 'Turn received'


def operation(raw):
    if not isinstance(raw,dict):raise ValueError('Invalid game request')
    action=raw.get('action')
    if action=='new':game=Game.new(raw.get('kind'))
    elif action=='join':game=Game.parse(raw.get('text'))
    else:
        game=Game.restore(raw.get('game'))
        if action=='move':game.act(raw.get('move',''))
        elif action=='receive':game.receive(raw.get('text'))
        elif action!='restore':raise ValueError('Unknown game action')
    return dict(game=asdict(game),status=game.status(),packet=game.packet(),name=NAMES[game.kind])
