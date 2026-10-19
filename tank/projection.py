"""Opaque output-resolution projector masks using Panda's native triangulator.

No image texture or shader dependency. Each enabled blackout contributes its
excluded area; inverted shapes are holes in a larger black quad. The outer quad
extends beyond all views so holes never touch its edges, even for full-size zones.
"""
import math
from panda3d.core import (Geom, GeomNode, GeomTriangles, GeomVertexData,
                         GeomVertexFormat, GeomVertexWriter, Triangulator, CullBinManager,
                         AntialiasAttrib, TransparencyAttrib)


def configure_overlay_bins():
    manager=CullBinManager.getGlobalPtr()
    # render2d defaults to the unsorted bin (50), after the standard fixed bin.
    # Separate later bins cover ALL scene text while preserving native GUI order.
    for name,sort in (('projector-mask',55),('projector-controls',58)):
        if manager.findBin(name)<0:manager.addBin(name,CullBinManager.BTUnsorted,sort)


def blackout_geometry(zones, aspect, pixels=4096):
    enabled=[zone for zone in zones if zone.enabled and zone.blackout]
    if not enabled:return None
    data=GeomVertexData('blackout-vertices',GeomVertexFormat.getV3(),Geom.UHStatic)
    vertices=GeomVertexWriter(data,'vertex');triangles=GeomTriangles(Geom.UHStatic)
    offset=0
    # Sub-pixel curve approximation at output resolution, independent of render
    # scale. At 16K output this stays within about half an output pixel.
    steps=max(64,min(1024,4*math.ceil(math.pi*math.sqrt(max(1,pixels)/2)/4)))
    for zone in enabled:
        outline=zone.outline(aspect,steps)[:-1]
        triangulator=Triangulator()
        outer=[(-3.,-3.),(3.,-3.),(3.,3.),(-3.,3.)] if zone.inverted else outline
        points=outer+(outline if zone.inverted else [])
        for u,v in points:
            triangulator.addVertex(u,v);vertices.addData3(u,0,v)
        for i in range(len(outer)):triangulator.addPolygonVertex(i)
        if zone.inverted:
            triangulator.beginHole()
            for i in range(len(outer),len(points)):triangulator.addHoleVertex(i)
        triangulator.triangulate()
        if triangulator.getNumTriangles()==0:raise RuntimeError('Could not triangulate projector blackout')
        for i in range(triangulator.getNumTriangles()):
            triangles.addVertices(*(offset+getter(i) for getter in
                                    (triangulator.getTriangleV0,triangulator.getTriangleV1,triangulator.getTriangleV2)))
        offset+=len(points)
    triangles.closePrimitive();geometry=Geom(data);geometry.addPrimitive(triangles)
    node=GeomNode('projector-blackouts');node.addGeom(geometry)
    return node


def attach_blackout(parent,geometry,rectangle=(-1.,1.,-1.,1.)):
    """Map common layout coordinates into one native view's local overlay."""
    if geometry is None:return None
    left,right,bottom,top=rectangle
    sx,sy=2/(right-left),2/(top-bottom)
    node=parent.attachNewNode('projector-mask-transform')
    node.attachNewNode(geometry)
    node.setScale(sx,1,sy);node.setPos(-(left+right)*sx/2,0,-(bottom+top)*sy/2)
    node.setColor(0,0,0,1);node.setLightOff(100);node.setTextureOff(100);node.setShaderOff(100);node.setFogOff(100)
    node.setTransparency(TransparencyAttrib.MNone,100);node.setAntialias(AntialiasAttrib.MNone,100)
    node.setDepthTest(False);node.setDepthWrite(False);node.setTwoSided(True)
    configure_overlay_bins()
    node.setBin('projector-mask',0)
    return node
