from dataclasses import replace
import pytest
from tank.protocol import Snapshot, decode_event, encode_event, ProtocolError
from tank.store import Store


def sample(**kw):
    return replace(Snapshot('01'*32,1,'02'*32,3,4,2,'C',1,2,3,65535,True,'fish'), **kw)


def rich(s, flags=7, species=65535, genes=(8, 247, 6), panel=2):
    return b'\x03'+encode_event(s)[1:]+bytes([flags])+species.to_bytes(2,'little')+bytes(genes)+bytes([panel])


def test_rich_strict():
    s=sample(); e=decode_event(s.rx,rich(s))
    assert (e.species_id,e.body_gene,e.scales_gene,e.eyes_gene,e.panel)==(65535,8,247,6,2)
    for data in (rich(s, flags=8),rich(s,genes=(7,8,9)),rich(s,panel=3),rich(s,flags=0),rich(s)[:-1]):
        with pytest.raises(ProtocolError): decode_event(s.rx,data)
    assert len(encode_event(s))==77
    assert encode_event(e)==rich(s)
    with pytest.raises(ProtocolError): encode_event(replace(e, body_gene=7))


def test_identity_and_replay(tmp_path):
    st=Store(tmp_path/'db'); s=sample(); e=decode_event(s.rx,rich(s))
    assert st.save(s); assert st.save(e); assert not st.save(s)
    assert st.roster()[0].species_id==65535
    with pytest.raises(ProtocolError): st.save(replace(e,species_id=7))
    st.save(replace(s,event_id=2,appearance=False))
    assert st.roster()[0].species_id==65535
    st.save(replace(s,event_id=3,fish_id=9,appearance=False))
    assert st.roster()[0].species_present is False
    assert st.roster()[0].body==s.body
    st.close()


def test_species_registry_is_permanent_and_unknown_safe():
    from tank.species import LABELS, render_id, label
    assert len(LABELS)==14 and LABELS[12]=='Shell-dweller'
    assert [render_id(i) for i in range(14)]==list(range(14))
    assert render_id(65535)==0 and label(65535)=='Unknown (fish)'
