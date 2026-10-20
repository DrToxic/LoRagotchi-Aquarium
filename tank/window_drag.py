"""Borderless client-area move/resize, independent of desktop window chrome."""
import ctypes
import ctypes.util
import sys

from panda3d.core import WindowProperties

EDGE=9
MIN_WIDTH,MIN_HEIGHT=320,180


def hit_edges(x,y,width,height):
    return (x<EDGE, x>=width-EDGE, y<EDGE, y>=height-EDGE)


def drag_rectangle(rectangle, edges, dx, dy):
    x,y,width,height=rectangle
    left,right,top,bottom=edges
    if not any(edges):
        return x+dx,y+dy,width,height
    if left:
        delta=min(dx,width-MIN_WIDTH);x+=delta;width-=delta
    elif right:width=max(MIN_WIDTH,width+dx)
    if top:
        delta=min(dy,height-MIN_HEIGHT);y+=delta;height-=delta
    elif bottom:height=max(MIN_HEIGHT,height+dy)
    return x,y,width,height


class DesktopPointer:
    """Read the global pointer during a grab, including outside client edges."""
    def __init__(self):
        self.display=None;self.api=None
        if sys.platform=="win32":
            from ctypes import wintypes
            self.api=ctypes.WinDLL("user32",use_last_error=True)
            self.point_type=wintypes.POINT
            self.api.GetCursorPos.argtypes=[ctypes.POINTER(wintypes.POINT)]
            self.api.GetCursorPos.restype=wintypes.BOOL
            self.api.GetAsyncKeyState.argtypes=[ctypes.c_int]
            self.api.GetAsyncKeyState.restype=ctypes.c_short
        elif sys.platform.startswith("linux"):
            name=ctypes.util.find_library("X11")
            if not name:return
            self.api=ctypes.CDLL(name)
            self.api.XOpenDisplay.argtypes=[ctypes.c_char_p];self.api.XOpenDisplay.restype=ctypes.c_void_p
            self.api.XDefaultRootWindow.argtypes=[ctypes.c_void_p];self.api.XDefaultRootWindow.restype=ctypes.c_ulong
            self.api.XQueryPointer.argtypes=[ctypes.c_void_p,ctypes.c_ulong,
                ctypes.POINTER(ctypes.c_ulong),ctypes.POINTER(ctypes.c_ulong),
                ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_int),
                ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_uint)]
            self.api.XQueryPointer.restype=ctypes.c_int
            self.api.XCloseDisplay.argtypes=[ctypes.c_void_p];self.api.XCloseDisplay.restype=ctypes.c_int
            self.display=self.api.XOpenDisplay(None)
            if self.display:self.root=self.api.XDefaultRootWindow(self.display)

    def sample(self):
        if sys.platform=="win32" and self.api:
            point=self.point_type()
            if self.api.GetCursorPos(ctypes.byref(point)):
                return point.x,point.y,bool(self.api.GetAsyncKeyState(1)&0x8000)
        elif self.display:
            root,child=ctypes.c_ulong(),ctypes.c_ulong()
            x,y,local_x,local_y=(ctypes.c_int() for _ in range(4))
            mask=ctypes.c_uint()
            if self.api.XQueryPointer(self.display,self.root,ctypes.byref(root),ctypes.byref(child),
                                     ctypes.byref(x),ctypes.byref(y),ctypes.byref(local_x),
                                     ctypes.byref(local_y),ctypes.byref(mask)):
                return x.value,y.value,bool(mask.value&(1<<8))
        return None

    def close(self):
        if self.display:
            self.api.XCloseDisplay(self.display);self.display=None


class WindowDrag:
    def __init__(self, app, pointer=None):
        self.app=app
        self.pointer=pointer or DesktopPointer()
        self.active=None

    def begin(self, view):
        if view.window in self.app.window_modes.saved:return
        pointer=view.window.getPointer(0)
        x,y=pointer.getX(),pointer.getY()
        rect=view.rectangle()
        if not (0<=x<rect[2] and 0<=y<rect[3]):return
        sample=self.pointer.sample()
        origin=sample[:2] if sample else (rect[0]+x,rect[1]+y)
        self.active=dict(view=view,rectangle=rect,origin=origin,
                         edges=hit_edges(x,y,rect[2],rect[3]),moved=False,last=rect)
        if hasattr(self.app,"controls"):self.app.controls.blur()

    def finish(self, view=None, select=True):
        state=self.active
        if state is None or (view is not None and state["view"] is not view):return
        self.active=None
        if select and not state["moved"] and not any(state["edges"]):
            self.app.select_fish(state["view"],state["view"].input.getParent().node())

    def update(self):
        state=self.active
        if state is None:return
        view=state["view"]
        if view not in self.app.views or view.window in self.app.window_modes.saved:
            self.finish(select=False);return
        sample=self.pointer.sample()
        if sample:
            x,y,pressed=sample
            if not pressed:self.finish();return
        else:
            pointer=view.window.getPointer(0);rect=view.rectangle()
            x,y=rect[0]+pointer.getX(),rect[1]+pointer.getY()
        dx,dy=round(x-state["origin"][0]),round(y-state["origin"][1])
        if not state["moved"] and max(abs(dx),abs(dy))<4:return
        state["moved"]=True
        rect=drag_rectangle(state["rectangle"],state["edges"],dx,dy)
        if rect==state["last"]:return
        props=WindowProperties();props.setOrigin(*rect[:2]);props.setSize(*rect[2:])
        view.window.requestProperties(props)
        state["last"]=rect

    def close(self):
        self.active=None;self.pointer.close()
