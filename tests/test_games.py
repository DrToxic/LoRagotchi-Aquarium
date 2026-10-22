from dataclasses import asdict
import pytest
from tank.games import Game,operation


def test_ttt_dupes_out_of_order_conflict_and_win():
    a=Game.new('t');b=Game.parse(a.packet())
    with pytest.raises(ValueError):b.act('1')
    for game,other,move in ((a,b,'1'),(b,a,'4'),(a,b,'2'),(b,a,'5'),(a,b,'3')):
        packet=game.act(move);other.receive(packet);assert other.packet()==packet
        assert 'Duplicate' in other.receive(packet)
    assert a.status()['done'] and 'Player 1 wins' in b.status()['text']
    with pytest.raises(ValueError):b.act('6')
    conflict=Game.new('t')
    with pytest.raises(ValueError):a.receive(conflict.packet())


def test_peer_cannot_forge_our_turn_or_replace_history():
    a=Game.new('t');b=Game.parse(a.packet());a.act('1');b.receive(a.packet());b.act('2');a.receive(b.packet())
    fake=Game.parse(a.packet());fake.moves+=['3','4']
    before=a.packet()
    with pytest.raises(ValueError):a.receive(fake.packet())
    assert a.packet()==before
    fake.moves=['1','3']
    with pytest.raises(ValueError):a.receive(fake.packet())


def test_guess_committed_secret_clues_and_restart():
    a=Game.new('g');b=Game.parse(a.packet());a=Game.restore(asdict(a))
    number=int(a.secret.split(',')[0]);wrong=1 if number!=1 else 20
    b.act(str(wrong));a.receive(b.packet());a.act('clue');b.receive(a.packet())
    b.act(str(number));a.receive(b.packet());a.act('clue');b.receive(a.packet())
    assert a.status()['done'] and b.status()['done']
    assert 'verified' in b.status()['text'] and len(a.packet())<=160
    tampered=a.packet().replace(a.reveal,'1,000000000000')
    with pytest.raises(ValueError):Game.parse(tampered)


def test_blackjack_resend_consecutive_moves_and_bounded_packets():
    for _ in range(12):
        a=Game.new('b');b=Game.parse(a.packet())
        for i in range(30):
            if a.status()['done']:break
            game,other=(a,b) if a.status()['turn']==0 else (b,a)
            game.act('stand' if game.status()['totals'][game.seat]>15 else 'hit')
            other.receive(game.packet());assert a.packet()==b.packet()
            assert len(a.packet().encode())<=160
        assert a.status()['done'] and b.status()['done']


@pytest.mark.parametrize('text',['', 'LAG1|t|bad', 'x'*161,'LAG1|t|0000000000000000|-|1.1|-|1'])
def test_malformed_messages(text):
    with pytest.raises(ValueError):Game.parse(text)


def test_stateless_web_operation_restores_private_host_without_exposing_secret_in_invite():
    result=operation({'action':'new','kind':'g'})
    assert result['game']['secret'] not in result['packet']
    joined=operation({'action':'join','text':result['packet']})
    assert joined['game']['seat']==1 and joined['game']['secret']==''
    assert operation({'action':'restore','game':result['game']})==result
