from dataclasses import replace
import pytest
from panda3d.core import NodePath, Point2, Point3
from tank.demo import visitors
from tank.views import NameLabels, desktop_lenses


@pytest.mark.parametrize('rectangles', [
    [(0, 0, 2560, 1440), (2560, 200, 1920, 1080)],
    [(0, 0, 2560, 1440), (-1920, -180, 1920, 1080)],
    [(0, 1080, 1920, 1080), (300, 0, 2560, 1080)],
])
def test_desktop_frusta_agree_on_world_pixel_coordinates(rectangles):
    lenses = desktop_lenses(rectangles)
    for world in [Point3(0, 30, 0), Point3(-7, 30, 3), Point3(9, 25, -2)]:
        desktop = []
        for lens, (x, y, w, h) in zip(lenses, rectangles):
            point = Point2()
            lens.project(world, point)
            desktop.append((x+(point.x+1)*w/2, y+(1-point.y)*h/2))
        assert desktop[0] == pytest.approx(desktop[1], abs=.001)


def test_name_geometry_is_reused_and_renamed_removed_identities_clean_up():
    labels = NameLabels(NodePath('root'))
    fish = list(visitors(256))
    labels.sync(fish)
    assert len(labels.labels) == 256
    assert labels.root.getNumChildren() == 256
    assert len({node for node, name in labels.labels.values()}) == 256
    assert labels.builds == 12  # duplicates share immutable geometry
    originals = {key: node for key, (node, name) in labels.labels.items()}
    labels.sync(fish)
    assert labels.builds == 12
    assert all(labels.labels[key][0] == node for key, node in originals.items())
    renamed = replace(fish[0], name='A new name')
    labels.sync([renamed, fish[1]])
    assert labels.builds == 13
    assert len(labels.labels) == len(labels.geometry) == 2
    assert labels.root.getNumChildren() == 2
    assert labels.labels[renamed.owner][1] == 'A new name'
    labels.sync([])
    assert not labels.labels and not labels.geometry
    labels.destroy()
