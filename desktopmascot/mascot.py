import tkinter as tk
from tkinter import simpledialog
import os
import time
from tts_manager import TTSManager
from window_manager import WindowManager

class MascotWindow:
    def __init__(self, root, display_info, win_manager, tts_manager, all_mascots):
        self.root = root
        self.display_info = display_info
        self.win_manager = win_manager
        self.tts_manager = tts_manager
        self.all_mascots = all_mascots
        
        # Window setup
        self.root.overrideredirect(True)
        self.root.wm_attributes("-topmost", True)
        self.root.wm_attributes("-toolwindow", True)
        # 白黒線画のフチに色が出ないよう、限りなく黒に近い色を透過色に設定
        self.transparent_color = "#000001"
        self.root.wm_attributes("-transparentcolor", self.transparent_color)
        self.root.config(bg=self.transparent_color)
        
        # Load image
        base_dir = os.path.dirname(os.path.abspath(__file__))
        img_path = os.path.join(base_dir, "cat.png")
        self.width, self.height = 100, 100
        if os.path.exists(img_path):
            try:
                self.img = tk.PhotoImage(file=img_path)
                self.width = self.img.width()
                self.height = self.img.height()
                self.label = tk.Label(self.root, image=self.img, bg=self.transparent_color, bd=0)
            except Exception as e:
                print(f"Error loading image: {e}")
                self._fallback_ui()
        else:
            self._fallback_ui()
            
        self.label.pack()

        # Initial Position (Bottom Right)
        self.x = display_info['x'] + display_info['width'] - self.width - 20
        self.y = display_info['y'] + display_info['height'] - self.height - 40
        self.root.geometry(f"{self.width}x{self.height}+{self.x}+{self.y}")

        # Drag and Shake variables
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.last_x = self.x
        self.shake_count = 0
        self.last_dir = 0
        self.last_shake_time = time.time()

        # Binds
        self.label.bind("<ButtonPress-1>", self.on_press)
        self.label.bind("<B1-Motion>", self.on_drag)
        self.label.bind("<ButtonRelease-1>", self.on_release)
        self.label.bind("<Button-3>", self.show_menu)

        # Bubble
        self.bubble = None
        self.bubble_label = None

        # Menu features are handled by show_menu which creates a custom bubble

    def _fallback_ui(self):
        self.width, self.height = 120, 120
        self.label = tk.Label(self.root, text="cat.png\n(Not Found)", bg="orange", fg="white", font=("Arial", 12, "bold"))
        self.label.place(x=0, y=0, width=self.width, height=self.height)
        self.root.wm_attributes("-transparentcolor", "") # Disable transparency so we can see the fallback bg

    def _make_draggable(self, window, widgets):
        def on_press(event):
            window._drag_start_x = event.x_root
            window._drag_start_y = event.y_root

        def on_drag(event):
            dx = event.x_root - window._drag_start_x
            dy = event.y_root - window._drag_start_y
            window.geometry(f"+{window.winfo_x() + dx}+{window.winfo_y() + dy}")
            window._drag_start_x = event.x_root
            window._drag_start_y = event.y_root

        for w in widgets:
            w.bind("<ButtonPress-1>", on_press, add="+")
            w.bind("<B1-Motion>", on_drag, add="+")

    def get_hwnd(self):
        return self.root.winfo_id()

    def on_press(self, event):
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        self.shake_count = 0

    def on_drag(self, event):
        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y
        self.x += dx
        self.y += dy
        self.root.geometry(f"+{self.x}+{self.y}")
        
        # Shake detection
        current_time = time.time()
        move_x = self.x - self.last_x
        
        if abs(move_x) > 10:
            current_dir = 1 if move_x > 0 else -1
            if current_dir != self.last_dir and self.last_dir != 0:
                if current_time - self.last_shake_time < 0.5:
                    self.shake_count += 1
                else:
                    self.shake_count = 1
                self.last_shake_time = current_time
                
                if self.shake_count >= 3: # Shaken back and forth 3 times
                    self.trigger_shake_action()
                    self.shake_count = 0
            
            self.last_dir = current_dir
            self.last_x = self.x

    def on_release(self, event):
        self.shake_count = 0

    def trigger_shake_action(self):
        print(f"Shake triggered on monitor {self.display_info['hMonitor']}")
        mascot_hwnds = [m.get_hwnd() for m in self.all_mascots]
        self.win_manager.toggle_minimize_on_monitor(self.display_info['hMonitor'], mascot_hwnds)

    def show_menu(self, event):
        if hasattr(self, 'menu_bubble') and self.menu_bubble:
            self.menu_bubble.destroy()
            
        self.menu_bubble = tk.Toplevel(self.root)
        self.menu_bubble.overrideredirect(True)
        self.menu_bubble.wm_attributes("-topmost", True)
        self.menu_bubble.wm_attributes("-transparentcolor", self.transparent_color)
        self.menu_bubble.config(bg=self.transparent_color)
        
        canvas = tk.Canvas(self.menu_bubble, bg=self.transparent_color, highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        
        width = 150
        height = 140
        padding = 15
        tail_width = 15
        tail_height = 15
        border_width = 6
        border_color = 'gray'
        offset = border_width // 2
        
        rect_w = width + padding * 2
        rect_h = height + padding * 2
        
        cw = rect_w + border_width
        ch = rect_h + tail_height + border_width
        
        rect_x1, rect_y1 = offset, offset
        rect_x2, rect_y2 = rect_w + offset, rect_h + offset
        
        tail_center_x = rect_w - 40 + offset
        tail_tip_x = tail_center_x
        tail_tip_y = rect_y2 + tail_height
        tail_base_x1 = tail_center_x - tail_width // 2
        tail_base_x2 = tail_center_x + tail_width // 2
        
        canvas.config(width=cw, height=ch)
        
        canvas.create_polygon(tail_base_x1, rect_y2, tail_base_x2, rect_y2, tail_tip_x, tail_tip_y, fill='white', outline=border_color, width=border_width)
        canvas.create_rectangle(rect_x1, rect_y1, rect_x2, rect_y2, fill='white', outline=border_color, width=border_width)
        canvas.create_line(tail_base_x1 + offset, rect_y2, tail_base_x2 - offset, rect_y2, fill='white', width=border_width)
        
        frame = tk.Frame(canvas, bg='white')
        
        title_lbl = tk.Label(frame, text='メニュー', font=('Meiryo', 10, 'bold'), bg='white')
        title_lbl.pack(pady=(0,5))
        
        def open_settings_and_close():
            self.menu_bubble.destroy()
            self.open_settings()
            
        btn_settings = tk.Button(frame, text="読み上げ設定...", command=open_settings_and_close, bg='#f0f0f0', relief='solid', bd=1, width=15)
        btn_settings.pack(pady=5)
        
        def open_wm_and_close():
            self.menu_bubble.destroy()
            self.open_window_manager()
            
        btn_wm = tk.Button(frame, text="ウィンドウ管理...", command=open_wm_and_close, bg='#f0f0f0', relief='solid', bd=1, width=15)
        btn_wm.pack(pady=5)
        
        btn_exit = tk.Button(frame, text="終了", command=self.exit_app, bg='#f0f0f0', relief='solid', bd=1, width=15)
        btn_exit.pack(pady=5)
        
        canvas.create_window(rect_x1 + padding, rect_y1 + padding, window=frame, width=width, height=height, anchor='nw')
        
        x_btn = tk.Label(self.menu_bubble, text='✖', bg='white', fg='gray', font=('Arial', 12, 'bold'), cursor='hand2')
        x_btn.place(x=rect_x2 - 25, y=rect_y1 + 5)
        x_btn.bind('<Button-1>', lambda e: self.menu_bubble.destroy())
        
        self._make_draggable(self.menu_bubble, [canvas, frame, title_lbl])
        
        self.menu_bubble.update_idletasks()
        
        bx = self.x + self.width - cw + 20
        by = self.y - ch - 10
        
        if bx < self.display_info['x']:
            bx = self.display_info['x']
            
        self.menu_bubble.geometry(f"{cw}x{ch}+{bx}+{by}")

    def open_settings(self):
        if hasattr(self, 'settings_bubble') and self.settings_bubble:
            self.settings_bubble.destroy()
            
        self.settings_bubble = tk.Toplevel(self.root)
        self.settings_bubble.overrideredirect(True)
        self.settings_bubble.wm_attributes("-topmost", True)
        self.settings_bubble.wm_attributes("-transparentcolor", self.transparent_color)
        self.settings_bubble.config(bg=self.transparent_color)
        
        canvas = tk.Canvas(self.settings_bubble, bg=self.transparent_color, highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        
        width = 280
        height = 190
        padding = 15
        tail_width = 15
        tail_height = 15
        border_width = 6
        border_color = 'gray'
        offset = border_width // 2
        
        rect_w = width + padding * 2
        rect_h = height + padding * 2
        
        cw = rect_w + border_width
        ch = rect_h + tail_height + border_width
        
        rect_x1, rect_y1 = offset, offset
        rect_x2, rect_y2 = rect_w + offset, rect_h + offset
        
        tail_center_x = rect_w - 40 + offset
        tail_tip_x = tail_center_x
        tail_tip_y = rect_y2 + tail_height
        tail_base_x1 = tail_center_x - tail_width // 2
        tail_base_x2 = tail_center_x + tail_width // 2
        
        canvas.config(width=cw, height=ch)
        
        canvas.create_polygon(tail_base_x1, rect_y2, tail_base_x2, rect_y2, tail_tip_x, tail_tip_y, fill='white', outline=border_color, width=border_width)
        canvas.create_rectangle(rect_x1, rect_y1, rect_x2, rect_y2, fill='white', outline=border_color, width=border_width)
        canvas.create_line(tail_base_x1 + offset, rect_y2, tail_base_x2 - offset, rect_y2, fill='white', width=border_width)
        
        frame = tk.Frame(canvas, bg='white')
        
        title_lbl = tk.Label(frame, text='読み上げ設定', font=('Meiryo', 10, 'bold'), bg='white')
        title_lbl.pack(pady=(0,5))
        
        speed_var = tk.IntVar(value=self.tts_manager.config.get('speech_speed', 0))
        len_var = tk.IntVar(value=self.tts_manager.config.get('max_speech_length', 100))
        height_var = tk.IntVar(value=self.tts_manager.config.get('bubble_max_height', 100))
        
        speed_scale = tk.Scale(frame, from_=-10, to=10, orient='horizontal', label='速度 (-10~10)', bg='white', variable=speed_var, length=200)
        speed_scale.pack()
        
        f1 = tk.Frame(frame, bg='white')
        f1.pack(fill='x', pady=2)
        lbl1 = tk.Label(f1, text='最大文字数:', bg='white')
        lbl1.pack(side='left')
        tk.Entry(f1, textvariable=len_var, width=8).pack(side='right')
        
        f2 = tk.Frame(frame, bg='white')
        f2.pack(fill='x', pady=2)
        lbl2 = tk.Label(f2, text='縦幅上限(px):', bg='white')
        lbl2.pack(side='left')
        tk.Entry(f2, textvariable=height_var, width=8).pack(side='right')
        
        from tkinter import filedialog
        
        dir_var = tk.StringVar(value=self.tts_manager.speak_dir)
        
        f3 = tk.Frame(frame, bg='white')
        f3.pack(fill='x', pady=2)
        lbl3 = tk.Label(f3, text='テキスト格納先:', bg='white')
        lbl3.pack(side='left')
        
        def browse_dir():
            d = filedialog.askdirectory(initialdir=dir_var.get())
            if d:
                dir_var.set(d)
                
        btn_browse = tk.Button(f3, text='参照...', command=browse_dir, bg='#f0f0f0', relief='solid', bd=1, padx=5, pady=0)
        btn_browse.pack(side='right')
        
        ent_dir = tk.Entry(frame, textvariable=dir_var, width=35)
        ent_dir.pack(fill='x', pady=(0,5))
        
        def save():
            try:
                self.tts_manager.config['speech_speed'] = speed_var.get()
                self.tts_manager.config['max_speech_length'] = len_var.get()
                self.tts_manager.config['bubble_max_height'] = height_var.get()
                
                new_dir = dir_var.get()
                self.tts_manager.config['speak_dir'] = new_dir
                self.tts_manager.speak_dir = new_dir
                self.tts_manager._ensure_dir()
                
                self.tts_manager.save_config()
                self.settings_bubble.destroy()
            except ValueError:
                pass
                
        save_btn = tk.Button(frame, text='保存して閉じる', command=save, bg='#f0f0f0', relief='solid', bd=1, padx=10, pady=2)
        save_btn.pack(pady=(10,0))
        
        canvas.create_window(rect_x1 + padding, rect_y1 + padding, window=frame, width=width, height=height, anchor='nw')
        
        x_btn = tk.Label(self.settings_bubble, text='✖', bg='white', fg='gray', font=('Arial', 12, 'bold'), cursor='hand2')
        x_btn.place(x=rect_x2 - 25, y=rect_y1 + 5)
        x_btn.bind('<Button-1>', lambda e: self.settings_bubble.destroy())
        
        self._make_draggable(self.settings_bubble, [canvas, frame, title_lbl, f1, f2, f3, lbl1, lbl2, lbl3])
        
        self.settings_bubble.update_idletasks()
        
        bx = self.x + self.width - cw + 20
        by = self.y - ch - 10
        
        if bx < self.display_info['x']:
            bx = self.display_info['x']
            
        self.settings_bubble.geometry(f"{cw}x{ch}+{bx}+{by}")

    def open_window_manager(self):
        if hasattr(self, 'wm_bubble') and self.wm_bubble:
            self.wm_bubble.destroy()
            
        self.wm_bubble = tk.Toplevel(self.root)
        self.wm_bubble.overrideredirect(True)
        self.wm_bubble.wm_attributes("-topmost", True)
        self.wm_bubble.wm_attributes("-transparentcolor", self.transparent_color)
        self.wm_bubble.config(bg=self.transparent_color)
        
        canvas = tk.Canvas(self.wm_bubble, bg=self.transparent_color, highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        
        width = 280
        height = 200
        padding = 15
        tail_width = 15
        tail_height = 15
        border_width = 6
        border_color = 'gray'
        offset = border_width // 2
        
        rect_w = width + padding * 2
        rect_h = height + padding * 2
        
        cw = rect_w + border_width
        ch = rect_h + tail_height + border_width
        
        rect_x1, rect_y1 = offset, offset
        rect_x2, rect_y2 = rect_w + offset, rect_h + offset
        
        tail_center_x = rect_w - 40 + offset
        tail_tip_x = tail_center_x
        tail_tip_y = rect_y2 + tail_height
        tail_base_x1 = tail_center_x - tail_width // 2
        tail_base_x2 = tail_center_x + tail_width // 2
        
        canvas.config(width=cw, height=ch)
        
        canvas.create_polygon(tail_base_x1, rect_y2, tail_base_x2, rect_y2, tail_tip_x, tail_tip_y, fill='white', outline=border_color, width=border_width)
        canvas.create_rectangle(rect_x1, rect_y1, rect_x2, rect_y2, fill='white', outline=border_color, width=border_width)
        canvas.create_line(tail_base_x1 + offset, rect_y2, tail_base_x2 - offset, rect_y2, fill='white', width=border_width)
        
        frame = tk.Frame(canvas, bg='white')
        
        title_lbl = tk.Label(frame, text='ウィンドウ管理', font=('Meiryo', 10, 'bold'), bg='white')
        title_lbl.pack(pady=(0,5))
        
        list_frame = tk.Frame(frame, bg='white')
        list_frame.pack(fill='both', expand=True)
        
        listbox = tk.Listbox(list_frame, width=35, height=6, font=('Meiryo', 9), selectbackground='#e0e0e0', selectforeground='black')
        scrollbar = tk.Scrollbar(list_frame, orient='vertical', command=listbox.yview)
        listbox.config(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side='right', fill='y')
        listbox.pack(side='left', fill='both', expand=True)
        
        mascot_hwnds = [m.get_hwnd() for m in self.all_mascots]
        windows_info = self.win_manager.get_windows_on_monitor(self.display_info['hMonitor'], mascot_hwnds)
        windows_info.sort(key=lambda w: w['title'])
        
        self.wm_hwnds = []
        for i, w in enumerate(windows_info):
            title = w['title']
            if len(title) > 20: title = title[:18] + '...'
            listbox.insert('end', title)
            self.wm_hwnds.append(w['hwnd'])
            
            if w['topmost']:
                listbox.itemconfig(i, {'fg': '#cc0000', 'bg': '#ffeeee'})
                
        def on_double_click(event):
            sel = listbox.curselection()
            if not sel: return
            idx = sel[0]
            hwnd = self.wm_hwnds[idx]
            
            is_now_topmost = self.win_manager.toggle_topmost(hwnd)
            if is_now_topmost:
                listbox.itemconfig(idx, {'fg': '#cc0000', 'bg': '#ffeeee'})
            else:
                listbox.itemconfig(idx, {'fg': 'black', 'bg': 'white'})
                
        listbox.bind('<Double-Button-1>', on_double_click)
        
        def toggle_trans():
            sel = listbox.curselection()
            if not sel: return
            idx = sel[0]
            hwnd = self.wm_hwnds[idx]
            self.win_manager.toggle_transparency(hwnd)
            
        btn_trans = tk.Button(frame, text='半透明切替', command=toggle_trans, bg='#f0f0f0', relief='solid', bd=1, padx=10, pady=2)
        btn_trans.pack(pady=(5,0))
        
        canvas.create_window(rect_x1 + padding, rect_y1 + padding, window=frame, width=width, height=height, anchor='nw')
        
        x_btn = tk.Label(self.wm_bubble, text='✖', bg='white', fg='gray', font=('Arial', 12, 'bold'), cursor='hand2')
        x_btn.place(x=rect_x2 - 25, y=rect_y1 + 5)
        x_btn.bind('<Button-1>', lambda e: self.wm_bubble.destroy())
        
        self._make_draggable(self.wm_bubble, [canvas, frame, title_lbl])
        
        self.wm_bubble.update_idletasks()
        
        bx = self.x + self.width - cw + 20
        by = self.y - ch - 10
        
        if bx < self.display_info['x']:
            bx = self.display_info['x']
            
        self.wm_bubble.geometry(f"{cw}x{ch}+{bx}+{by}")

    def exit_app(self):
        self.tts_manager.stop()
        for mascot in self.all_mascots:
            mascot.root.destroy()

    def show_speech(self, text):
        if self.bubble:
            self.bubble.destroy()

        self.bubble = tk.Toplevel(self.root)
        self.bubble.overrideredirect(True)
        self.bubble.wm_attributes("-topmost", True)
        self.bubble.wm_attributes("-transparentcolor", self.transparent_color)
        self.bubble.config(bg=self.transparent_color)
        
        canvas = tk.Canvas(self.bubble, bg=self.transparent_color, highlightthickness=0)
        canvas.pack(fill="both", expand=True)

        max_height = self.tts_manager.config.get("bubble_max_height", 100)
        width = 200

        # Create a frame for Text and Scrollbar
        frame = tk.Frame(canvas, bg='white')
        text_widget = tk.Text(frame, wrap='word', width=20, font=('Meiryo', 10), bg='white', relief='flat', bd=0)
        scrollbar = tk.Scrollbar(frame, orient='vertical', command=text_widget.yview)
        text_widget.config(yscrollcommand=scrollbar.set)

        scrollbar.pack(side='right', fill='y')
        text_widget.pack(side='left', fill='both', expand=True)

        text_widget.insert('1.0', text)
        text_widget.config(state='disabled')

        padding = 10
        tail_width = 15
        border_width = 6
        border_color = 'gray'
        offset = border_width // 2

        # We fix the rect size since text scrolls
        rect_w = width + padding * 2
        rect_h = max_height + padding * 2

        cw = rect_w + tail_width + border_width
        ch = rect_h + border_width

        rect_x1, rect_y1 = offset, offset
        rect_x2, rect_y2 = rect_w + offset, rect_h + offset

        tail_tip_x = rect_x2 + tail_width
        tail_tip_y = rect_y2 - 15
        tail_base_y1 = rect_y2 - 30
        tail_base_y2 = rect_y2 - 10

        if tail_base_y1 < offset: tail_base_y1 = offset

        canvas.config(width=cw, height=ch)

        # Tail polygon
        canvas.create_polygon(rect_x2, tail_base_y1, rect_x2, tail_base_y2, tail_tip_x, tail_tip_y, fill='white', outline=border_color, width=border_width)
        # Main rectangle
        canvas.create_rectangle(rect_x1, rect_y1, rect_x2, rect_y2, fill='white', outline=border_color, width=border_width)
        # Erase the connecting line
        canvas.create_line(rect_x2, tail_base_y1 + offset, rect_x2, tail_base_y2 - offset, fill='white', width=border_width)

        # Embed frame inside canvas
        canvas.create_window(rect_x1 + padding, rect_y1 + padding, window=frame, width=width, height=max_height, anchor='nw')

        # Close button (top right)
        x_btn = tk.Label(self.bubble, text='✖', bg='white', fg='gray', font=('Arial', 12, 'bold'), cursor='hand2')
        x_btn.place(x=rect_x2 - 25, y=rect_y1 + 5)
        x_btn.bind('<Button-1>', lambda e: self.hide_speech())

        self._make_draggable(self.bubble, [canvas, frame])

        self.bubble.update_idletasks()
        
        # Position to the left of the mascot
        bx = self.x - cw - 5
        by = self.y + (self.height // 2) - ch + 20
        
        # Prevent going off the left edge of the monitor
        if bx < self.display_info['x']:
            bx = self.display_info['x']
            
        self.bubble.geometry(f"{cw}x{ch}+{bx}+{by}")

    def hide_speech(self):
        if self.bubble:
            self.bubble.destroy()
            self.bubble = None

def main():
    root = tk.Tk()
    root.withdraw()

    win_manager = WindowManager()
    displays = win_manager.get_displays()
    
    config_path = "config.json"
    speak_dir = os.path.join(os.environ["USERPROFILE"], "OneDrive", "Speak")
    
    mascots = []
    
    def on_speak(text):
        for m in mascots:
            m.root.after(0, m.show_speech, text)

    def on_speak_done():
        for m in mascots:
            m.root.after(0, m.hide_speech)

    tts_manager = TTSManager(config_path, speak_dir, on_speak, on_speak_done)
    
    for display in displays:
        top = tk.Toplevel(root)
        mascot = MascotWindow(top, display, win_manager, tts_manager, mascots)
        mascots.append(mascot)

    tts_manager.start()
    
    def on_closing():
        tts_manager.stop()
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", on_closing)

    root.mainloop()

if __name__ == "__main__":
    main()
