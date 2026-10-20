"""Physical desktop panorama; sand is anchored in the combined water frustum."""
import math

from panda3d.core import Point2, Point3

SAND_FRACTION = 1/3
SAND_BACK = (0., 13., 0.)


def bounds(rectangles):
    left = min(x for x, y, w, h in rectangles)
    top = min(y for x, y, w, h in rectangles)
    return (left, top, max(x+w for x, y, w, h in rectangles)-left,
            max(y+h for x, y, w, h in rectangles)-top)


def regions(rectangles):
    left, top, width, height = bounds(rectangles)
    return tuple((2*(x-left)/width-1, 2*(x+w-left)/width-1,
                  1-2*(y+h-top)/height, 1-2*(y-top)/height)
                 for x, y, w, h in rectangles)


def aim_at_sand(camera, render, lens):
    """Aim the common camera so nominal rear sand projects to the lower third."""
    pos = camera.getPos(render)
    ground_angle = math.atan2(SAND_BACK[2]-pos.z, SAND_BACK[1]-pos.y)
    target_ray = math.atan((2*SAND_FRACTION-1)*math.tan(math.radians(lens.getVfov()/2)))
    camera.setHpr(0, math.degrees(ground_angle-target_ray), 0)


def at_depth(lens, camera, render, u, v, depth):
    """Intersect a screen ray with a world-Y plane (the bubble's travel plane)."""
    near, far = Point3(), Point3()
    lens.extrude(Point2(u, v), near, far)
    near = render.getRelativePoint(camera, near)
    far = render.getRelativePoint(camera, far)
    delta = far-near
    return near+delta*((depth-near.y)/delta.y)
