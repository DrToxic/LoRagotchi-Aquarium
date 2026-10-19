"""Borderless fullscreen on the containing Windows monitor; no mode switch."""
import sys
from panda3d.core import WindowProperties


def monitor_bounds(window, pipe):
    if sys.platform == 'win32':
        import ctypes
        from ctypes import wintypes

        class MonitorInfo(ctypes.Structure):
            _fields_ = [('cbSize', wintypes.DWORD), ('rcMonitor', wintypes.RECT),
                        ('rcWork', wintypes.RECT), ('dwFlags', wintypes.DWORD)]

        user32 = ctypes.WinDLL('user32', use_last_error=True)
        user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
        user32.MonitorFromWindow.restype = wintypes.HANDLE
        user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MonitorInfo)]
        user32.GetMonitorInfoW.restype = wintypes.BOOL
        handle = window.getWindowHandle().getIntHandle()
        monitor = user32.MonitorFromWindow(handle, 2)  # nearest if not wholly on one display
        info = MonitorInfo();info.cbSize = ctypes.sizeof(info)
        if not monitor or not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
            raise OSError(ctypes.get_last_error(), 'Could not read the window monitor bounds')
        rect = info.rcMonitor  # whole monitor, not work area excluding taskbar
        return rect.left, rect.top, rect.right-rect.left, rect.bottom-rect.top
    # Panda's display size is sufficient for the tested single-screen Linux
    # path. Per-monitor Linux/macOS placement is not claimed by this fallback.
    return 0, 0, pipe.getDisplayWidth(), pipe.getDisplayHeight()


class WindowModes:
    def __init__(self, pipe, bounds=monitor_bounds):
        self.pipe, self.bounds = pipe, bounds
        self.saved = {}

    def toggle(self, window):
        if window in self.saved:
            original = self.saved.pop(window)
            window.requestProperties(original)
            return False
        x, y, width, height = self.bounds(window, self.pipe)
        if width < 1 or height < 1:
            raise ValueError('Monitor reported an invalid size')
        current = window.getProperties()
        restore = WindowProperties()
        restore.setOrigin(current.getXOrigin(), current.getYOrigin())
        restore.setSize(current.getXSize(), current.getYSize())
        restore.setUndecorated(current.getUndecorated())
        restore.setFullscreen(False)
        props = WindowProperties()
        props.setFullscreen(False)
        props.setUndecorated(True)
        props.setOrigin(x, y)
        props.setSize(width, height)
        self.saved[window] = restore
        window.requestProperties(props)
        return True

    def discard(self, window):
        self.saved.pop(window, None)
