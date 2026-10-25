"""Presentation-only juvenile expression: genes, masks and neutral alleles."""
from dataclasses import asdict, replace
import pytest
from tank import art
from tank.demo import visitors


@pytest.mark.parametrize('primary',range(6))
@pytest.mark.parametrize('stage,body_weight,fin_weight',[(0,2,5),(1,5,6)])
def test_dx_expression_weights(primary,stage,body_weight,fin_weight):
    fish=replace(next(visitors(1)),stage=stage,body=primary,scales=(primary+3)%6)
    original=asdict(fish)
    body,fins=art.juvenile_colours(fish)
    ivory=art.tint565(0xFFBC)
    for actual,allele,weight in ((body,fish.body,body_weight),(fins,fish.body if stage==0 else fish.scales,fin_weight)):
        genetic=art.colour(allele,fish.tint)
        assert actual==pytest.approx(tuple(ivory[k]+(genetic[k]-ivory[k])*weight/8 for k in range(3)))
    assert asdict(fish)==original


@pytest.mark.parametrize('stage',[0,1])
@pytest.mark.parametrize('tint',[0,0xffff,0x8410,0x47af])
def test_neutral_and_existing_guest_tints_are_not_recoloured(stage,tint):
    fish=replace(next(visitors(1)),stage=stage,mode='M',body=6,scales=6,eyes=6,tint=tint)
    assert art.juvenile_colours(fish)==(art.colour(6,tint),)*2


@pytest.mark.parametrize('style',['classic','rounded','faceted'])
@pytest.mark.parametrize('stage',[0,1])
def test_regions_and_eye_genes_are_stage_limited(monkeypatch,style,stage):
    real_mesh=art.mesh
    captures={}
    def capture(name,vertices,triangles):
        captures.setdefault(name,[]).append(tuple(tuple(v[2]) for v in vertices))
        return real_mesh(name,vertices,triangles)
    monkeypatch.setattr(art,'mesh',capture)
    fish=replace(next(visitors(1)),stage=stage,body=5,scales=0,eyes=2)
    root,tail,fins=art.fish_model(fish,18,style)
    first=captures.copy();captures.clear()
    other,_,_=art.fish_model(replace(fish,scales=4,eyes=3),18,style)
    assert first['body']==captures['body']
    assert first['eye-rim']==captures['eye-rim']
    for region in ('tail','dorsal','ventral','pectoral'):
        assert (first[region]==captures[region])==(stage==0)
    # Colours are mesh-local, children of the same joints that already animate.
    assert tail.getParent()==root
    assert all(fin.getParent()==root for fin in fins)
    assert tail.find('**/tail').getParent()==tail
    root.removeNode();other.removeNode()
