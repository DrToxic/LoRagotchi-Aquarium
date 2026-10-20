import pytest
from tank.window_drag import drag_rectangle, hit_edges


def test_drag_anywhere_preserves_size_and_allows_negative_desktop():
    rect=(20,30,640,360)
    assert drag_rectangle(rect,hit_edges(300,200,640,360),-300,-400)==(-280,-370,640,360)


@pytest.mark.parametrize("point,delta,expected",[
    ((0,100),(80,0),(100,30,560,360)),
    ((639,100),(80,0),(20,30,720,360)),
    ((300,0),(0,80),(20,110,640,280)),
    ((300,359),(0,80),(20,30,640,440)),
    ((0,0),(100,70),(120,100,540,290)),
    ((639,359),(100,70),(20,30,740,430)),
    ((0,0),(500,500),(340,210,320,180)),
    ((639,359),(-500,-500),(20,30,320,180)),
])
def test_edge_corner_and_minimum_resize(point,delta,expected):
    assert drag_rectangle((20,30,640,360),hit_edges(*point,640,360),*delta)==expected
