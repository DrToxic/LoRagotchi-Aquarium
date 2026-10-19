from panda3d.core import WindowProperties
from tank.window_mode import WindowModes


class Window:
    def __init__(self, x, y, width, height):
        self.props=WindowProperties()
        self.props.setOrigin(x,y);self.props.setSize(width,height)
        self.props.setUndecorated(False);self.props.setFullscreen(False)
        self.requests=[]
    def getProperties(self):return self.props
    def requestProperties(self, props):
        self.requests.append(WindowProperties(props))
        self.props.addProperties(props)


def test_fullscreen_never_requests_client_size_as_a_display_mode():
    window=Window(2560,180,1920,1009)
    modes=WindowModes(None,lambda window,pipe:(2560,180,1920,1080))
    assert modes.toggle(window)
    props=window.requests[-1]
    assert not props.getFullscreen() and props.getUndecorated()
    assert (props.getXSize(),props.getYSize())==(1920,1080)
    assert (props.getXOrigin(),props.getYOrigin())==(2560,180)
    assert not modes.toggle(window)
    props=window.requests[-1]
    assert (props.getXSize(),props.getYSize())==(1920,1009)
    assert not props.getFullscreen() and not props.getUndecorated()


def test_windows_restore_independently_and_negative_monitor_origins_work():
    a,b=Window(50,50,1200,700),Window(-1900,-150,900,700)
    modes=WindowModes(None,lambda window,pipe:(0,0,2560,1440) if window is a else (-1920,-180,1920,1080))
    modes.toggle(a);modes.toggle(b)
    assert b.getProperties().getXOrigin()==-1920
    modes.toggle(a)
    assert a.getProperties().getXSize()==1200 and b in modes.saved
    modes.discard(b)
    assert not modes.saved
