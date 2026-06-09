import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32

class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long)
    ]

MonitorEnumProc = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong, ctypes.POINTER(RECT), ctypes.c_double)

class WindowManager:
    def __init__(self):
        self.minimized_windows = set()

    def get_displays(self):
        displays = []
        def callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
            rect = lprcMonitor.contents
            displays.append({
                'hMonitor': hMonitor,
                'x': rect.left,
                'y': rect.top,
                'width': rect.right - rect.left,
                'height': rect.bottom - rect.top
            })
            return 1
        
        user32.EnumDisplayMonitors(0, 0, MonitorEnumProc(callback), 0)
        return displays

    def get_window_monitor(self, hwnd):
        MONITOR_DEFAULTTONEAREST = 2
        return user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)

    def _is_minimizable_window(self, hwnd):
        if not user32.IsWindowVisible(hwnd):
            return False
        
        GWL_EXSTYLE = -20
        WS_EX_TOOLWINDOW = 0x00000080
        ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        if ex_style & WS_EX_TOOLWINDOW:
            return False

        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return False

        return True

    def toggle_minimize_on_monitor(self, monitor_handle, mascot_hwnds):
        SW_MINIMIZE = 6
        SW_RESTORE = 9
        
        hwnds = []
        def enum_windows_proc(hwnd, lParam):
            hwnds.append(hwnd)
            return True
            
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        user32.EnumWindows(EnumWindowsProc(enum_windows_proc), 0)

        # Check if we should restore (if we have previously minimized windows for this monitor)
        to_restore = []
        for hwnd in self.minimized_windows:
            if user32.IsWindow(hwnd):
                win_monitor = self._get_window_monitor(hwnd)
                if win_monitor == monitor_handle:
                    to_restore.append(hwnd)
        
        if to_restore:
            # Restore
            for hwnd in to_restore:
                user32.ShowWindow(hwnd, SW_RESTORE)
                self.minimized_windows.discard(hwnd)
        else:
            # Minimize
            for hwnd in hwnds:
                if hwnd in mascot_hwnds:
                    continue
                
                if self._is_minimizable_window(hwnd):
                    win_monitor = self._get_window_monitor(hwnd)
                    if win_monitor == monitor_handle:
                        if not user32.IsIconic(hwnd):
                            user32.ShowWindow(hwnd, SW_MINIMIZE)
                            self.minimized_windows.add(hwnd)

    def get_windows_on_monitor(self, monitor_handle, mascot_hwnds):
        windows = []
        GWL_EXSTYLE = -20
        WS_EX_TOPMOST = 0x00000008
        WS_EX_LAYERED = 0x00080000

        def enum_windows_proc(hwnd, lParam):
            if hwnd in mascot_hwnds:
                return True
            if not self._is_minimizable_window(hwnd):
                return True
            
            win_monitor = self.get_window_monitor(hwnd)
            if win_monitor == monitor_handle:
                length = user32.GetWindowTextLengthW(hwnd)
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value
                
                ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                topmost = bool(ex_style & WS_EX_TOPMOST)
                layered = bool(ex_style & WS_EX_LAYERED)
                
                windows.append({
                    'hwnd': hwnd,
                    'title': title,
                    'topmost': topmost,
                    'layered': layered
                })
            return True

        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        user32.EnumWindows(EnumWindowsProc(enum_windows_proc), 0)
        return windows

    def toggle_topmost(self, hwnd):
        GWL_EXSTYLE = -20
        WS_EX_TOPMOST = 0x00000008
        HWND_TOPMOST = ctypes.c_void_p(-1)
        HWND_NOTOPMOST = ctypes.c_void_p(-2)
        SWP_NOSIZE = 0x0001
        SWP_NOMOVE = 0x0002

        ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        is_topmost = bool(ex_style & WS_EX_TOPMOST)
        
        insert_after = HWND_NOTOPMOST if is_topmost else HWND_TOPMOST
        user32.SetWindowPos(hwnd, insert_after, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
        return not is_topmost

    def toggle_transparency(self, hwnd):
        GWL_EXSTYLE = -20
        WS_EX_LAYERED = 0x00080000
        LWA_ALPHA = 2
        
        ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        is_layered = bool(ex_style & WS_EX_LAYERED)
        
        if not is_layered:
            # Enable layered style and set alpha to 180 (approx 70% opaque)
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style | WS_EX_LAYERED)
            user32.SetLayeredWindowAttributes(hwnd, 0, 180, LWA_ALPHA)
            return True
        else:
            # Revert to opaque (alpha 255) and remove layered style
            user32.SetLayeredWindowAttributes(hwnd, 0, 255, LWA_ALPHA)
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style & ~WS_EX_LAYERED)
            return False
