import tkinter as tk
from tkinter import simpledialog, messagebox
import time
import math
import threading
import winsound
from PIL import Image, ImageTk, ImageDraw

def resolve_color(mode, custom):
    if mode == "ユーザー指定":
        return custom
    return "white"

def get_complementary_color(widget, color):
    try:
        r, g, b = widget.winfo_rgb(color)
        r = 65535 - r
        g = 65535 - g
        b = 65535 - b
        return f"#{r>>8:02x}{g>>8:02x}{b>>8:02x}"
    except:
        return "black"

class ClockWidget:
    def __init__(self, root_window, tts_manager):
        self.root = root_window
        self.tts_manager = tts_manager
        self.win = tk.Toplevel(self.root)
        self.win.overrideredirect(True)
        self.win.wm_attributes("-topmost", True)
        
        self.transparent_color = "#000001"
        self.win.wm_attributes("-transparentcolor", self.transparent_color)
        self.win.config(bg=self.transparent_color)
        
        self.size = 150
        self.canvas = tk.Canvas(self.win, width=self.size, height=self.size, bg=self.transparent_color, highlightthickness=0)
        self.canvas.pack()
        
        self.cx = self.size // 2
        self.cy = self.size // 2
        self.radius = self.size // 2 - 10
        
        self.draw_face()
        
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<Button-3>", self.show_menu)
        
        # Get screen width to place it top right
        sw = self.win.winfo_screenwidth()
        self.win.geometry(f"+{sw - 200}+50")
        
        self.running = True
        self.update_clock()
        
    def draw_face(self):
        config = self.tts_manager.config
        mode = config.get("clock_color_mode", "デフォルト")
        custom = config.get("clock_custom_color", "#ffffff")
        color = resolve_color(mode, custom)
        outline = config.get("clock_outline", False)
        comp_color = get_complementary_color(self.canvas, color) if outline else ""
        
        sf = self.size / 150.0
        
        self.canvas.delete("face")
        for i in range(60):
            angle = math.radians(i * 6 - 90)
            is_hour = (i % 5 == 0)
            length_out = self.radius
            length_in = self.radius - int((10 if is_hour else 5) * sf)
            x1 = self.cx + length_in * math.cos(angle)
            y1 = self.cy + length_in * math.sin(angle)
            x2 = self.cx + length_out * math.cos(angle)
            y2 = self.cy + length_out * math.sin(angle)
            
            width = max(1, int((2 if is_hour else 1) * sf))
            if outline:
                self.canvas.create_line(x1, y1, x2, y2, fill=comp_color, width=width+2, tags="face")
            self.canvas.create_line(x1, y1, x2, y2, fill=color, width=width, tags="face")
            
            if is_hour:
                num = i // 5
                if num == 0: num = 12
                nx = self.cx + (self.radius - int(20 * sf)) * math.cos(angle)
                ny = self.cy + (self.radius - int(20 * sf)) * math.sin(angle)
                font_size = max(6, int(10 * sf))
                if outline:
                    for dx, dy in [(-1,-1), (-1,1), (1,-1), (1,1), (0,1), (0,-1), (1,0), (-1,0)]:
                        self.canvas.create_text(nx+dx, ny+dy, text=str(num), fill=comp_color, font=("Arial", font_size, "bold"), tags="face")
                self.canvas.create_text(nx, ny, text=str(num), fill=color, font=("Arial", font_size, "bold"), tags="face")
                
    def on_press(self, event):
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        
    def on_drag(self, event):
        x = self.win.winfo_x() - self.drag_start_x + event.x
        y = self.win.winfo_y() - self.drag_start_y + event.y
        self.win.geometry(f"+{x}+{y}")
        
    def show_menu(self, event):
        menu = tk.Menu(self.win, tearoff=0)
        menu.add_command(label="閉じる", command=self.close)
        menu.tk_popup(event.x_root, event.y_root)
        
    def close(self):
        self.running = False
        self.win.destroy()
        
    def update_clock(self):
        if not self.running: return
        
        config = self.tts_manager.config
        new_size = config.get("clock_size", 150)
        sf = new_size / 150.0
        if new_size != self.size:
            self.size = new_size
            self.cx = self.size // 2
            self.cy = self.size // 2
            self.radius = self.size // 2 - int(10 * sf)
            self.canvas.config(width=self.size, height=self.size)
            
        self.canvas.delete("hands")
        
        mode = config.get("clock_color_mode", "デフォルト")
        custom = config.get("clock_custom_color", "#ffffff")
        color = resolve_color(mode, custom)
        outline = config.get("clock_outline", False)
        comp_color = get_complementary_color(self.canvas, color) if outline else ""
        
        self.draw_face()
        
        t = time.localtime()
        sec = t.tm_sec
        min = t.tm_min
        hour = t.tm_hour % 12
        
        s_angle = math.radians(sec * 6 - 90)
        sx = self.cx + (self.radius - int(5 * sf)) * math.cos(s_angle)
        sy = self.cy + (self.radius - int(5 * sf)) * math.sin(s_angle)
        sw = max(1, int(1 * sf))
        if outline: self.canvas.create_line(self.cx, self.cy, sx, sy, fill=comp_color, width=sw+2, tags="hands")
        self.canvas.create_line(self.cx, self.cy, sx, sy, fill="red", width=sw, tags="hands")
        
        m_angle = math.radians(min * 6 + sec * 0.1 - 90)
        mx = self.cx + (self.radius - int(15 * sf)) * math.cos(m_angle)
        my = self.cy + (self.radius - int(15 * sf)) * math.sin(m_angle)
        mw = max(1, int(3 * sf))
        if outline: self.canvas.create_line(self.cx, self.cy, mx, my, fill=comp_color, width=mw+2, tags="hands")
        self.canvas.create_line(self.cx, self.cy, mx, my, fill=color, width=mw, tags="hands")
        
        h_angle = math.radians(hour * 30 + min * 0.5 - 90)
        hx = self.cx + (self.radius - int(30 * sf)) * math.cos(h_angle)
        hy = self.cy + (self.radius - int(30 * sf)) * math.sin(h_angle)
        hw = max(1, int(4 * sf))
        if outline: self.canvas.create_line(self.cx, self.cy, hx, hy, fill=comp_color, width=hw+2, tags="hands")
        self.canvas.create_line(self.cx, self.cy, hx, hy, fill=color, width=hw, tags="hands")
        
        cr = max(2, int(3 * sf))
        if outline: self.canvas.create_oval(self.cx-cr-1, self.cy-cr-1, self.cx+cr+1, self.cy+cr+1, fill=comp_color, outline=comp_color, tags="hands")
        self.canvas.create_oval(self.cx-cr, self.cy-cr, self.cx+cr, self.cy+cr, fill="red", outline="red", tags="hands")
        
        self.win.wm_attributes("-topmost", True)
        self.win.after(1000, self.update_clock)


class TimerWidget:
    def __init__(self, root_window, tts_manager):
        self.root = root_window
        self.tts_manager = tts_manager
        self.win = tk.Toplevel(self.root)
        self.win.overrideredirect(True)
        self.win.wm_attributes("-topmost", True)
        
        self.transparent_color = "#000001"
        self.win.wm_attributes("-transparentcolor", self.transparent_color)
        self.win.config(bg=self.transparent_color)
        
        self.size = 150
        self.canvas = tk.Canvas(self.win, width=self.size, height=self.size + 40, bg=self.transparent_color, highlightthickness=0)
        self.canvas.pack()
        
        self.arc_win = tk.Toplevel(self.win)
        self.arc_win.overrideredirect(True)
        self.arc_win.wm_attributes("-topmost", True)
        self.arc_win.wm_attributes("-transparentcolor", self.transparent_color)
        self.arc_win.wm_attributes("-alpha", 0.5)
        self.arc_win.config(bg=self.transparent_color)
        
        self.arc_canvas = tk.Canvas(self.arc_win, width=self.size, height=self.size + 40, bg=self.transparent_color, highlightthickness=0)
        self.arc_canvas.pack()
        
        self.cx = self.size // 2
        self.cy = self.size // 2
        self.radius = self.size // 2 - 10
        
        self.draw_face()
        
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<Button-3>", self.show_menu)
        
        self.arc_canvas.bind("<ButtonPress-1>", self.on_press)
        self.arc_canvas.bind("<B1-Motion>", self.on_drag)
        self.arc_canvas.bind("<Button-3>", self.show_menu)
        
        sw = self.win.winfo_screenwidth()
        self.win.geometry(f"+{sw - 200}+250")
        self.arc_win.geometry(f"+{sw - 200}+250")
        
        self.running = True
        
        self.total_seconds = 180
        self.remaining_seconds = self.total_seconds
        self.end_time = None
        self.timer_running = False
        
        self.update_timer()
        
    def draw_face(self):
        config = self.tts_manager.config
        mode = config.get("timer_color_mode", "デフォルト")
        custom = config.get("timer_custom_color", "#ffffff")
        color = resolve_color(mode, custom)
        outline = config.get("timer_outline", False)
        comp_color = get_complementary_color(self.canvas, color) if outline else ""
        
        sf = self.size / 150.0
        
        self.canvas.delete("face")
        for i in range(60):
            angle = math.radians(i * 6 - 90)
            is_hour = (i % 5 == 0)
            length_out = self.radius
            length_in = self.radius - int((8 if is_hour else 4) * sf)
            x1 = self.cx + length_in * math.cos(angle)
            y1 = self.cy + length_in * math.sin(angle)
            x2 = self.cx + length_out * math.cos(angle)
            y2 = self.cy + length_out * math.sin(angle)
            
            width = max(1, int((2 if is_hour else 1) * sf))
            if outline:
                self.canvas.create_line(x1, y1, x2, y2, fill=comp_color, width=width+2, tags="face")
            self.canvas.create_line(x1, y1, x2, y2, fill=color, width=width, tags="face")
            
    def on_press(self, event):
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        
    def on_drag(self, event):
        x = self.win.winfo_x() - self.drag_start_x + event.x
        y = self.win.winfo_y() - self.drag_start_y + event.y
        self.win.geometry(f"+{x}+{y}")
        self.arc_win.geometry(f"+{x}+{y}")
        
    def show_menu(self, event):
        menu = tk.Menu(self.win, tearoff=0)
        menu.add_command(label="時間設定", command=self.set_time)
        menu.add_command(label="閉じる", command=self.close)
        menu.tk_popup(event.x_root, event.y_root)
        
    def set_time(self):
        was_running = self.timer_running
        self.timer_running = False
        
        ans = simpledialog.askstring("時間設定", "分数（または HH:MM:SS）を入力してください:", parent=self.win)
        if ans:
            try:
                if ":" in ans:
                    parts = ans.split(":")
                    if len(parts) == 3:
                        secs = int(parts[0])*3600 + int(parts[1])*60 + int(parts[2])
                    elif len(parts) == 2:
                        secs = int(parts[0])*60 + int(parts[1])
                    else:
                        raise ValueError()
                else:
                    secs = int(float(ans) * 60)
                
                if secs > 0:
                    self.total_seconds = secs
                    self.remaining_seconds = secs
                    self.end_time = time.time() + secs
                    self.timer_running = True
            except:
                messagebox.showerror("エラー", "正しい形式で入力してください。", parent=self.win)
        else:
            self.timer_running = was_running
            if was_running and self.end_time:
                self.end_time = time.time() + self.remaining_seconds
                
    def close(self):
        self.running = False
        self.arc_win.destroy()
        self.win.destroy()
        
    def trigger_alarm(self):
        def sound_thread():
            for _ in range(4):
                winsound.Beep(2000, 100)
                time.sleep(0.05)
                winsound.Beep(2000, 100)
                time.sleep(0.2)
        threading.Thread(target=sound_thread, daemon=True).start()
        
        self.win.wm_attributes("-topmost", True)
        messagebox.showinfo("タイマー", "時間になりました！", parent=self.win)
        
    def update_timer(self):
        if not self.running: return
        
        config = self.tts_manager.config
        new_size = config.get("timer_size", 150)
        sf = new_size / 150.0
        
        if new_size != self.size:
            self.size = new_size
            self.cx = self.size // 2
            self.cy = self.size // 2
            self.radius = self.size // 2 - int(10 * sf)
            self.canvas.config(width=self.size, height=self.size + int(40 * sf))
            self.arc_canvas.config(width=self.size, height=self.size + int(40 * sf))
        
        self.canvas.delete("dynamic")
        self.arc_canvas.delete("dynamic")
        
        self.draw_face()
        
        if self.timer_running:
            rem = self.end_time - time.time()
            if rem <= 0:
                self.remaining_seconds = 0
                self.timer_running = False
                self.trigger_alarm()
            else:
                self.remaining_seconds = rem
                
        if self.total_seconds > 0:
            fraction = self.remaining_seconds / self.total_seconds
        else:
            fraction = 0
            
        mode = config.get("timer_color_mode", "デフォルト")
        custom = config.get("timer_custom_color", "#ffffff")
        base_color = resolve_color(mode, custom)
        outline = config.get("timer_outline", False)
        comp_color = get_complementary_color(self.canvas, base_color) if outline else ""
            
        color = base_color
        if self.remaining_seconds == 0 and not self.timer_running:
            color = "red"
            if outline: comp_color = get_complementary_color(self.canvas, "red")
            
        extent_angle = fraction * 360
        if extent_angle > 0:
            off = int(10 * sf)
            if outline:
                self.arc_canvas.create_arc(
                    self.cx - self.radius + off - 2, self.cy - self.radius + off - 2,
                    self.cx + self.radius - off + 2, self.cy + self.radius - off + 2,
                    start=90 - (1 - fraction) * 360, extent=-extent_angle,
                    fill=comp_color, outline="", tags="dynamic"
                )
            self.arc_canvas.create_arc(
                self.cx - self.radius + off, self.cy - self.radius + off,
                self.cx + self.radius - off, self.cy + self.radius - off,
                start=90 - (1 - fraction) * 360, extent=-extent_angle,
                fill="lightblue", outline="", tags="dynamic"
            )
        
        hand_angle = math.radians(-90 + (1 - fraction) * 360)
        hx = self.cx + (self.radius - int(10 * sf)) * math.cos(hand_angle)
        hy = self.cy + (self.radius - int(10 * sf)) * math.sin(hand_angle)
        hw = max(1, int(3 * sf))
        if outline:
            self.canvas.create_line(self.cx, self.cy, hx, hy, fill=comp_color, width=hw+2, tags="dynamic")
        self.canvas.create_line(self.cx, self.cy, hx, hy, fill=color, width=hw, tags="dynamic")
        
        cr = max(2, int(4 * sf))
        if outline:
            self.canvas.create_oval(self.cx-cr-1, self.cy-cr-1, self.cx+cr+1, self.cy+cr+1, fill=comp_color, outline=comp_color, tags="dynamic")
        self.canvas.create_oval(self.cx-cr, self.cy-cr, self.cx+cr, self.cy+cr, fill=color, outline=color, tags="dynamic")
        
        total_s = int(math.ceil(self.remaining_seconds))
        h = total_s // 3600
        m = (total_s % 3600) // 60
        s = total_s % 60
        text_str = f"{h:02d}:{m:02d}:{s:02d}"
        
        if self.remaining_seconds == 0 and int(time.time() * 2) % 2 == 0:
            text_color = "red"
            if outline: comp_color = get_complementary_color(self.canvas, "red")
        else:
            text_color = base_color
            
        font_size = max(8, int(14 * sf))
        ty = self.size + int(20 * sf)
        if outline:
            for dx, dy in [(-1,-1), (-1,1), (1,-1), (1,1), (0,1), (0,-1), (1,0), (-1,0)]:
                self.canvas.create_text(self.cx+dx, ty+dy, text=text_str, fill=comp_color, font=("Arial", font_size, "bold"), tags="dynamic")
        self.canvas.create_text(self.cx, ty, text=text_str, fill=text_color, font=("Arial", font_size, "bold"), tags="dynamic")
        
        self.arc_win.wm_attributes("-topmost", True)
        self.win.wm_attributes("-topmost", True)
        self.win.after(100, self.update_timer)
