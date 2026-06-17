import tkinter as tk
from tkinter import simpledialog
import os
import time
from tts_manager import TTSManager
from window_manager import WindowManager
from clock_widget import ClockWidget, TimerWidget
from shortcut_manager import ShortcutManager

class MascotWindow:
    def __init__(self, root, display_info, win_manager, tts_manager, all_mascots):
        self.root = root
        self.display_info = display_info
        self.win_manager = win_manager
        self.tts_manager = tts_manager
        self.all_mascots = all_mascots
        
        self.clocks = []
        self.timers = []
        
        # ShortcutManager初期化
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.shortcut_manager = ShortcutManager(base_dir, win_manager)
        
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
        gif_path = os.path.join(base_dir, "cat.gif")
        png_path = os.path.join(base_dir, "cat.png")
        self.width, self.height = 100, 100
        self.frames = []
        self.current_frame = 0

        if os.path.exists(gif_path):
            try:
                while True:
                    frame = tk.PhotoImage(file=gif_path, format=f"gif -index {len(self.frames)}")
                    self.frames.append(frame)
            except tk.TclError:
                pass

            if self.frames:
                self.img = self.frames[0]
                self.width = self.img.width()
                self.height = self.img.height()
                self.label = tk.Label(self.root, image=self.img, bg=self.transparent_color, bd=0)
                if len(self.frames) > 1:
                    self.root.after(100, self.animate_gif)
            else:
                self._fallback_ui()

        elif os.path.exists(png_path):
            try:
                self.img = tk.PhotoImage(file=png_path)
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
        self.label.bind("<Double-Button-1>", self.on_double_click)

        # Bubble
        self.bubble = None
        self.bubble_label = None
        
        # ドラッグ距離トラッキング（ダブルクリック誤発火防止用）
        self._drag_distance = 0

        # Menu features are handled by show_menu which creates a custom bubble

    def _fallback_ui(self):
        self.width, self.height = 120, 120
        self.label = tk.Label(self.root, text="cat.png\n(Not Found)", bg="orange", fg="white", font=("Arial", 12, "bold"))
        self.label.place(x=0, y=0, width=self.width, height=self.height)
        self.root.wm_attributes("-transparentcolor", "") # Disable transparency so we can see the fallback bg

    def animate_gif(self):
        if hasattr(self, 'label') and self.frames:
            self.current_frame = (self.current_frame + 1) % len(self.frames)
            self.label.configure(image=self.frames[self.current_frame])
            self.root.after(100, self.animate_gif)

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
        self._drag_distance = 0

    def on_drag(self, event):
        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y
        self.x += dx
        self.y += dy
        self._drag_distance += (dx**2 + dy**2)**0.5
        self.root.geometry(f"+{self.x}+{self.y}")
        
        # Shake detection
        current_time = time.time()
        move_x = self.x - self.last_x
        
        shake_dist = self.tts_manager.config.get('shake_dist', 10.0)
        shake_time = self.tts_manager.config.get('shake_time', 0.5)
        shake_count_thresh = self.tts_manager.config.get('shake_count', 3)
        
        if abs(move_x) > shake_dist:
            current_dir = 1 if move_x > 0 else -1
            if current_dir != self.last_dir and self.last_dir != 0:
                if current_time - self.last_shake_time < shake_time:
                    self.shake_count += 1
                else:
                    self.shake_count = 1
                self.last_shake_time = current_time
                
                if self.shake_count >= shake_count_thresh:
                    self.trigger_shake_action()
                    self.shake_count = 0
            
            self.last_dir = current_dir
            self.last_x = self.x

    def on_release(self, event):
        self.shake_count = 0

    def trigger_shake_action(self):
        current_monitor = self.win_manager.get_window_monitor(self.get_hwnd())
        print(f"Shake triggered on monitor {current_monitor}")
        mascot_hwnds = [m.get_hwnd() for m in self.all_mascots]
        self.win_manager.toggle_minimize_on_monitor(current_monitor, mascot_hwnds)

    def _close_all_non_speech_bubbles(self):
        """読み上げ以外の全ての吹き出しを閉じる"""
        for attr in ('menu_bubble', 'settings_bubble', 'sens_bubble', 'wm_bubble', 'shortcut_bubble', 'sc_create_bubble', 'sc_existing_bubble', 'sc_manage_bubble'):
            w = getattr(self, attr, None)
            if w and w.winfo_exists():
                w.destroy()

    def show_menu(self, event):
        # 既にメニュー以外の吹き出しが開いていたら全て閉じて終了
        non_menu_open = any(
            getattr(self, attr, None) and getattr(self, attr).winfo_exists()
            for attr in ('settings_bubble', 'sens_bubble', 'wm_bubble', 'shortcut_bubble', 'sc_create_bubble', 'sc_existing_bubble', 'sc_manage_bubble')
        )
        if non_menu_open:
            self._close_all_non_speech_bubbles()
            return
        # メニュー自体が開いていたら閉じる
        if hasattr(self, 'menu_bubble') and self.menu_bubble and self.menu_bubble.winfo_exists():
            self.menu_bubble.destroy()
            return
        self.menu_bubble = tk.Toplevel(self.root)
        self.menu_bubble.overrideredirect(True)
        self.menu_bubble.wm_attributes("-topmost", True)
        self.menu_bubble.wm_attributes("-transparentcolor", self.transparent_color)
        self.menu_bubble.config(bg=self.transparent_color)
        
        canvas = tk.Canvas(self.menu_bubble, bg=self.transparent_color, highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        
        width = 160
        height = 320
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
        
        def spawn_clock_and_close():
            self.menu_bubble.destroy()
            self.clocks.append(ClockWidget(self.root, self.tts_manager))
            
        btn_clock = tk.Button(frame, text="時計", command=spawn_clock_and_close, bg='#f0f0f0', relief='solid', bd=1, width=15)
        btn_clock.pack(pady=5)
        
        def spawn_timer_and_close():
            self.menu_bubble.destroy()
            self.timers.append(TimerWidget(self.root, self.tts_manager))
            
        btn_timer = tk.Button(frame, text="タイマー", command=spawn_timer_and_close, bg='#f0f0f0', relief='solid', bd=1, width=15)
        btn_timer.pack(pady=5)
        
        def open_sc_manage_and_close():
            self.menu_bubble.destroy()
            self.open_shortcut_manager()
            
        btn_sc = tk.Button(frame, text="ショートカット管理...", command=open_sc_manage_and_close, bg='#f0f0f0', relief='solid', bd=1, width=15)
        btn_sc.pack(pady=5)
        
        def open_sens_and_close():
            self.menu_bubble.destroy()
            self.open_sensitivity_settings()
            
        btn_sens = tk.Button(frame, text="詳細設定...", command=open_sens_and_close, bg='#f0f0f0', relief='solid', bd=1, width=15)
        btn_sens.pack(pady=5)
        
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
        height = 300
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
        
        tts_enabled_var = tk.BooleanVar(value=self.tts_manager.config.get('tts_enabled', True))
        chk_tts = tk.Checkbutton(frame, text="読み上げを有効にする", variable=tts_enabled_var, bg='white')
        chk_tts.pack(pady=(0,5))
        
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
                self.tts_manager.config['tts_enabled'] = tts_enabled_var.get()
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

    def open_sensitivity_settings(self):
        if hasattr(self, 'sens_bubble') and self.sens_bubble:
            self.sens_bubble.destroy()
            
        self.sens_bubble = tk.Toplevel(self.root)
        self.sens_bubble.overrideredirect(True)
        self.sens_bubble.wm_attributes("-topmost", True)
        self.sens_bubble.wm_attributes("-transparentcolor", self.transparent_color)
        self.sens_bubble.config(bg=self.transparent_color)
        
        canvas = tk.Canvas(self.sens_bubble, bg=self.transparent_color, highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        
        width = 300
        height = 540
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
        
        title_lbl = tk.Label(frame, text='詳細設定', font=('Meiryo', 10, 'bold'), bg='white')
        title_lbl.pack(pady=(0,5))
        
        tk.Label(frame, text='【最小化（感度調整）】', bg='white', font=('Meiryo', 8, 'bold')).pack(anchor='w', pady=(5,0))
        
        dist_var = tk.DoubleVar(value=self.tts_manager.config.get('shake_dist', 10.0))
        time_var = tk.DoubleVar(value=self.tts_manager.config.get('shake_time', 0.5))
        count_var = tk.IntVar(value=self.tts_manager.config.get('shake_count', 3))
        
        f1 = tk.Frame(frame, bg='white')
        f1.pack(fill='x', pady=2)
        tk.Label(f1, text='判定距離 (px):', bg='white').pack(side='left')
        tk.Entry(f1, textvariable=dist_var, width=8).pack(side='right')
        
        f2 = tk.Frame(frame, bg='white')
        f2.pack(fill='x', pady=2)
        tk.Label(f2, text='判定時間 (秒):', bg='white').pack(side='left')
        tk.Entry(f2, textvariable=time_var, width=8).pack(side='right')
        
        f3 = tk.Frame(frame, bg='white')
        f3.pack(fill='x', pady=2)
        tk.Label(f3, text='判定回数 (往復):', bg='white').pack(side='left')
        tk.Entry(f3, textvariable=count_var, width=8).pack(side='right')
        
        from tkinter import colorchooser
        
        tk.Label(frame, text='【時計】', bg='white', font=('Meiryo', 8, 'bold')).pack(anchor='w', pady=(10,0))
        
        c_size_var = tk.IntVar(value=self.tts_manager.config.get('clock_size', 150))
        cs_f = tk.Frame(frame, bg='white')
        cs_f.pack(fill='x', pady=2)
        tk.Label(cs_f, text='サイズ:', bg='white').pack(side='left')
        tk.Scale(cs_f, variable=c_size_var, from_=50, to=300, orient='horizontal', bg='white', highlightthickness=0).pack(side='left', fill='x', expand=True, padx=5)
        
        c_mode_var = tk.StringVar(value=self.tts_manager.config.get('clock_color_mode', 'デフォルト'))
        c_cust_var = tk.StringVar(value=self.tts_manager.config.get('clock_custom_color', '#ffffff'))
        
        cf = tk.Frame(frame, bg='white')
        cf.pack(fill='x', pady=2)
        tk.OptionMenu(cf, c_mode_var, 'デフォルト', 'ユーザー指定').pack(side='left')
        
        def pick_clock_color():
            c = colorchooser.askcolor(initialcolor=c_cust_var.get(), parent=self.sens_bubble)[1]
            if c: c_cust_var.set(c)
        tk.Button(cf, text='色選択...', command=pick_clock_color).pack(side='left', padx=5)
        
        c_outline_var = tk.BooleanVar(value=self.tts_manager.config.get('clock_outline', False))
        tk.Checkbutton(frame, text='補色で縁取りする', variable=c_outline_var, bg='white').pack(anchor='w')
        
        tk.Label(frame, text='【タイマー】', bg='white', font=('Meiryo', 8, 'bold')).pack(anchor='w', pady=(10,0))
        
        t_size_var = tk.IntVar(value=self.tts_manager.config.get('timer_size', 150))
        ts_f = tk.Frame(frame, bg='white')
        ts_f.pack(fill='x', pady=2)
        tk.Label(ts_f, text='サイズ:', bg='white').pack(side='left')
        tk.Scale(ts_f, variable=t_size_var, from_=50, to=300, orient='horizontal', bg='white', highlightthickness=0).pack(side='left', fill='x', expand=True, padx=5)
        
        t_mode_var = tk.StringVar(value=self.tts_manager.config.get('timer_color_mode', 'デフォルト'))
        t_cust_var = tk.StringVar(value=self.tts_manager.config.get('timer_custom_color', '#ffffff'))
        
        tf = tk.Frame(frame, bg='white')
        tf.pack(fill='x', pady=2)
        tk.OptionMenu(tf, t_mode_var, 'デフォルト', 'ユーザー指定').pack(side='left')
        
        def pick_timer_color():
            c = colorchooser.askcolor(initialcolor=t_cust_var.get(), parent=self.sens_bubble)[1]
            if c: t_cust_var.set(c)
        tk.Button(tf, text='色選択...', command=pick_timer_color).pack(side='left', padx=5)
        
        t_outline_var = tk.BooleanVar(value=self.tts_manager.config.get('timer_outline', False))
        tk.Checkbutton(frame, text='補色で縁取りする', variable=t_outline_var, bg='white').pack(anchor='w')
        
        def save():
            try:
                self.tts_manager.config['shake_dist'] = dist_var.get()
                self.tts_manager.config['shake_time'] = time_var.get()
                self.tts_manager.config['shake_count'] = count_var.get()
                self.tts_manager.config['clock_color_mode'] = c_mode_var.get()
                self.tts_manager.config['clock_custom_color'] = c_cust_var.get()
                self.tts_manager.config['clock_size'] = c_size_var.get()
                self.tts_manager.config['clock_outline'] = c_outline_var.get()
                self.tts_manager.config['timer_color_mode'] = t_mode_var.get()
                self.tts_manager.config['timer_custom_color'] = t_cust_var.get()
                self.tts_manager.config['timer_size'] = t_size_var.get()
                self.tts_manager.config['timer_outline'] = t_outline_var.get()
                self.tts_manager.save_config()
                self.sens_bubble.destroy()
            except ValueError:
                pass
                
        save_btn = tk.Button(frame, text='保存して閉じる', command=save, bg='#f0f0f0', relief='solid', bd=1, padx=10, pady=2)
        save_btn.pack(pady=(10,0))
        
        canvas.create_window(rect_x1 + padding, rect_y1 + padding, window=frame, width=width, height=height, anchor='nw')
        
        x_btn = tk.Label(self.sens_bubble, text='✖', bg='white', fg='gray', font=('Arial', 12, 'bold'), cursor='hand2')
        x_btn.place(x=rect_x2 - 25, y=rect_y1 + 5)
        x_btn.bind('<Button-1>', lambda e: self.sens_bubble.destroy())
        
        self._make_draggable(self.sens_bubble, [canvas, frame, title_lbl, f1, f2, f3, cf, tf, cs_f, ts_f])
        
        self.sens_bubble.update_idletasks()
        
        bx = self.x + self.width - cw + 20
        by = self.y - ch - 10
        if bx < self.display_info['x']:
            bx = self.display_info['x']
        self.sens_bubble.geometry(f"{cw}x{ch}+{bx}+{by}")

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
        current_monitor = self.win_manager.get_window_monitor(self.get_hwnd())
        windows_info = self.win_manager.get_windows_on_monitor(current_monitor, mascot_hwnds)
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
        self.root.master.destroy()

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
        x_btn.bind('<Button-1>', lambda e: self.hide_speech(abort=True))

        self._make_draggable(self.bubble, [canvas, frame])

        self.bubble.update_idletasks()
        
        # Position to the left of the mascot
        bx = self.x - cw - 5
        by = self.y + (self.height // 2) - ch + 20
        
        # Prevent going off the left edge of the monitor
        if bx < self.display_info['x']:
            bx = self.display_info['x']
            
        self.bubble.geometry(f"{cw}x{ch}+{bx}+{by}")

    def hide_speech(self, abort=False):
        if abort:
            self.tts_manager.abort_speech()
        if self.bubble:
            self.bubble.destroy()
            self.bubble = None


    def on_double_click(self, event):
        if self._drag_distance < 5:
            self._close_all_non_speech_bubbles()
            self.open_shortcut_input()

    def open_shortcut_input(self):
        if hasattr(self, 'shortcut_bubble') and self.shortcut_bubble and self.shortcut_bubble.winfo_exists():
            self.shortcut_bubble.destroy()
            
        self.shortcut_bubble = tk.Toplevel(self.root)
        self.shortcut_bubble.overrideredirect(True)
        self.shortcut_bubble.wm_attributes("-topmost", True)
        self.shortcut_bubble.wm_attributes("-transparentcolor", self.transparent_color)
        self.shortcut_bubble.config(bg=self.transparent_color)
        
        canvas = tk.Canvas(self.shortcut_bubble, bg=self.transparent_color, highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        
        width, height = 400, 200
        padding = 15
        tail_width, tail_height = 15, 15
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
        
        title_lbl = tk.Label(frame, text='🔍 ショートカット', font=('Meiryo', 10, 'bold'), bg='white')
        title_lbl.pack(anchor='w', pady=(0,5))
        
        entry_var = tk.StringVar()
        entry = tk.Entry(frame, textvariable=entry_var, font=('Meiryo', 14), width=30)
        entry.pack(fill='x', pady=5)
        
        result_frame = tk.Frame(frame, bg='white')
        result_frame.pack(fill='both', expand=True, pady=5)
        
        res_name_lbl = tk.Label(result_frame, text='', font=('Meiryo', 11, 'bold'), bg='white', fg='#333')
        res_name_lbl.pack(anchor='w')
        res_desc_lbl = tk.Label(result_frame, text='', font=('Meiryo', 9), bg='white', fg='#666')
        res_desc_lbl.pack(anchor='w')
        
        btn_frame = tk.Frame(frame, bg='white')
        btn_frame.pack(fill='x', pady=(5,0))
        
        current_shortcut = [None]
        
        def update_result(*args):
            q = entry_var.get().strip()
            if not q:
                res_name_lbl.config(text='')
                res_desc_lbl.config(text='')
                current_shortcut[0] = None
                return
                
            sc, score = self.shortcut_manager.search(q)
            if sc:
                current_shortcut[0] = sc
                res_name_lbl.config(text=f"💬 {sc.get('name', '???')}  (スコア: {score:.2f})")
                actions = sc.get('actions', [])
                if actions:
                    desc = self.shortcut_manager.format_action_summary(actions[0])
                    if len(actions) > 1:
                        desc += f" (+{len(actions)-1}件)"
                    res_desc_lbl.config(text=f"アクション: {desc}")
                else:
                    res_desc_lbl.config(text="アクションなし")
            else:
                current_shortcut[0] = None
                res_name_lbl.config(text="一致するショートカットがありません")
                res_desc_lbl.config(text="")
                
        entry_var.trace_add('write', update_result)
        
        def on_enter(e):
            if current_shortcut[0]:
                self.shortcut_manager.execute(current_shortcut[0])
                self.shortcut_bubble.destroy()
            else:
                entry_var.set('')
                
        entry.bind('<Return>', on_enter)
        
        def show_detail():
            sc = current_shortcut[0]
            if not sc: return
            details = [self.shortcut_manager.format_action_summary(a) for a in sc.get('actions', [])]
            import tkinter.messagebox as mb
            mb.showinfo("詳細", chr(10).join(details), parent=self.shortcut_bubble)
            
        def add_new():
            q = entry_var.get().strip()
            self.shortcut_bubble.destroy()
            self.open_shortcut_create(initial_trigger=q)
            
        def add_existing():
            q = entry_var.get().strip()
            if not q: return
            self.shortcut_bubble.destroy()
            self.open_shortcut_existing(q)
            
        def open_manage():
            self.shortcut_bubble.destroy()
            self.open_shortcut_manager()
            
        tk.Button(btn_frame, text='詳細', command=show_detail, bg='#f0f0f0', relief='solid', bd=1).pack(side='left', padx=2)
        tk.Button(btn_frame, text='追加', command=add_new, bg='#e6f2ff', relief='solid', bd=1).pack(side='left', padx=2)
        tk.Button(btn_frame, text='既存', command=add_existing, bg='#e6f2ff', relief='solid', bd=1).pack(side='left', padx=2)
        tk.Button(btn_frame, text='管理', command=open_manage, bg='#f0f0f0', relief='solid', bd=1).pack(side='right', padx=2)
        
        canvas.create_window(rect_x1 + padding, rect_y1 + padding, window=frame, width=width, height=height, anchor='nw')
        
        x_btn = tk.Label(self.shortcut_bubble, text='✖', bg='white', fg='gray', font=('Arial', 12, 'bold'), cursor='hand2')
        x_btn.place(x=rect_x2 - 25, y=rect_y1 + 5)
        x_btn.bind('<Button-1>', lambda e: self.shortcut_bubble.destroy())
        
        self._make_draggable(self.shortcut_bubble, [canvas, frame, title_lbl])
        self.shortcut_bubble.update_idletasks()
        
        bx, by = self.x + self.width - cw + 20, self.y - ch - 10
        if bx < self.display_info['x']: bx = self.display_info['x']
        self.shortcut_bubble.geometry(f"{cw}x{ch}+{bx}+{by}")
        
        entry.focus_set()

    def open_shortcut_create(self, initial_trigger="", shortcut_id=None):
        if hasattr(self, 'sc_create_bubble') and self.sc_create_bubble and self.sc_create_bubble.winfo_exists():
            self.sc_create_bubble.destroy()
            
        self.sc_create_bubble = tk.Toplevel(self.root)
        self.sc_create_bubble.overrideredirect(True)
        self.sc_create_bubble.wm_attributes("-topmost", True)
        self.sc_create_bubble.wm_attributes("-transparentcolor", self.transparent_color)
        self.sc_create_bubble.config(bg=self.transparent_color)
        
        canvas = tk.Canvas(self.sc_create_bubble, bg=self.transparent_color, highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        
        width, height = 450, 400
        padding = 15
        tail_width, tail_height = 15, 15
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
        
        title_text = 'ショートカット編集' if shortcut_id else '新規ショートカット作成'
        title_lbl = tk.Label(frame, text=title_text, font=('Meiryo', 10, 'bold'), bg='white')
        title_lbl.pack(anchor='w', pady=(0,5))
        
        sc_data = self.shortcut_manager.get_by_id(shortcut_id) if shortcut_id else None
        
        f1 = tk.Frame(frame, bg='white')
        f1.pack(fill='x', pady=2)
        tk.Label(f1, text='作業名(確認文):', bg='white', width=14, anchor='e').pack(side='left')
        name_var = tk.StringVar(value=sc_data['name'] if sc_data else '')
        tk.Entry(f1, textvariable=name_var, width=35).pack(side='left', padx=5)
        
        f2 = tk.Frame(frame, bg='white')
        f2.pack(fill='x', pady=2)
        tk.Label(f2, text='指示文言(カンマ区切):', bg='white', width=14, anchor='e').pack(side='left')
        trig_val = ", ".join(sc_data['triggers']) if sc_data else initial_trigger
        triggers_var = tk.StringVar(value=trig_val)
        tk.Entry(f2, textvariable=triggers_var, width=35).pack(side='left', padx=5)
        
        tk.Label(frame, text='【アクション】', bg='white', font=('Meiryo', 9, 'bold')).pack(anchor='w', pady=(10,0))
        
        actions_container = tk.Frame(frame, bg='white')
        actions_container.pack(fill='both', expand=True)
        
        action_widgets = []
        
        def add_action_row(act_data=None):
            if not act_data: act_data = {"type": "open", "value": ""}
            row = tk.Frame(actions_container, bg='#f9f9f9', bd=1, relief='solid', pady=5, padx=5)
            row.pack(fill='x', pady=2)
            
            tf = tk.Frame(row, bg='#f9f9f9')
            tf.pack(fill='x')
            tk.Label(tf, text='タイプ:', bg='#f9f9f9').pack(side='left')
            type_var = tk.StringVar(value=act_data['type'])
            tk.OptionMenu(tf, type_var, 'open', 'command', 'text_file', 'window').pack(side='left', padx=5)
            
            vf = tk.Frame(row, bg='#f9f9f9')
            vf.pack(fill='x', pady=2)
            tk.Label(vf, text='値:', bg='#f9f9f9').pack(side='left')
            
            is_dict = isinstance(act_data['value'], dict)
            v_val = act_data['value'].get('path', '') if is_dict and act_data['type'] == 'text_file' else act_data['value'].get('name', '') if is_dict and act_data['type'] == 'window' else act_data['value']
            
            val_var = tk.StringVar(value=str(v_val))
            tk.Entry(vf, textvariable=val_var, width=30).pack(side='left', padx=5)
            
            def do_test():
                t = type_var.get()
                v = val_var.get()
                if t == 'text_file': v = {"path": v, "content": "テスト"}
                elif t == 'window': v = {"match": "starts_with", "name": v}
                res = self.shortcut_manager.test_action({"type": t, "value": v})
                import tkinter.messagebox as mb
                mb.showinfo("テスト結果", self.shortcut_manager.format_result_detail(res), parent=self.sc_create_bubble)
                
            tk.Button(vf, text='テスト', command=do_test, bg='#e6f2ff', relief='solid', bd=1).pack(side='right')
            
            def del_row():
                row.destroy()
                action_widgets.remove(get_data)
                
            tk.Button(tf, text='削除', command=del_row, bg='#ffe6e6', relief='solid', bd=1).pack(side='right')
            
            def get_data():
                t = type_var.get()
                v = val_var.get()
                if t == 'text_file': v = {"path": v, "content": "(ショートカットから生成)"}
                elif t == 'window': v = {"match": "starts_with", "name": v}
                return {"type": t, "value": v}
                
            action_widgets.append(get_data)
            
        if sc_data:
            for a in sc_data.get('actions', []): add_action_row(a)
        else:
            add_action_row()
            
        tk.Button(frame, text='＋アクション追加', command=lambda: add_action_row(), bg='#f0f0f0', relief='solid', bd=1).pack(pady=5)
        
        def save():
            name = name_var.get().strip()
            trigs = [t.strip() for t in triggers_var.get().split(',') if t.strip()]
            acts = [gw() for gw in action_widgets]
            if not name or not trigs or not acts:
                import tkinter.messagebox as mb
                mb.showerror("エラー", "作業名、指示文言、アクションは必須です", parent=self.sc_create_bubble)
                return
            if shortcut_id:
                self.shortcut_manager.update_shortcut(shortcut_id, name=name, triggers=trigs, actions=acts)
            else:
                self.shortcut_manager.add_shortcut(name, trigs, acts)
            self.sc_create_bubble.destroy()
            
        btn_f = tk.Frame(frame, bg='white')
        btn_f.pack(pady=10)
        tk.Button(btn_f, text='保存', command=save, bg='#e6f2ff', relief='solid', bd=1, width=10).pack(side='left', padx=5)
        tk.Button(btn_f, text='キャンセル', command=self.sc_create_bubble.destroy, bg='#f0f0f0', relief='solid', bd=1, width=10).pack(side='left', padx=5)
        
        canvas.create_window(rect_x1 + padding, rect_y1 + padding, window=frame, width=width, height=height, anchor='nw')
        
        x_btn = tk.Label(self.sc_create_bubble, text='✖', bg='white', fg='gray', font=('Arial', 12, 'bold'), cursor='hand2')
        x_btn.place(x=rect_x2 - 25, y=rect_y1 + 5)
        x_btn.bind('<Button-1>', lambda e: self.sc_create_bubble.destroy())
        
        self._make_draggable(self.sc_create_bubble, [canvas, frame, title_lbl])
        self.sc_create_bubble.update_idletasks()
        
        bx, by = self.x + self.width - cw + 20, self.y - ch - 10
        if bx < self.display_info['x']: bx = self.display_info['x']
        self.sc_create_bubble.geometry(f"{cw}x{ch}+{bx}+{by}")

    def open_shortcut_existing(self, new_trigger):
        if hasattr(self, 'sc_existing_bubble') and self.sc_existing_bubble and self.sc_existing_bubble.winfo_exists():
            self.sc_existing_bubble.destroy()
            
        self.sc_existing_bubble = tk.Toplevel(self.root)
        self.sc_existing_bubble.overrideredirect(True)
        self.sc_existing_bubble.wm_attributes("-topmost", True)
        self.sc_existing_bubble.wm_attributes("-transparentcolor", self.transparent_color)
        self.sc_existing_bubble.config(bg=self.transparent_color)
        
        canvas = tk.Canvas(self.sc_existing_bubble, bg=self.transparent_color, highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        
        width, height = 300, 300
        padding = 15
        tail_width, tail_height = 15, 15
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
        
        title_lbl = tk.Label(frame, text='既存ショートカットに追加', font=('Meiryo', 10, 'bold'), bg='white')
        title_lbl.pack(anchor='w', pady=(0,5))
        tk.Label(frame, text=f"追加する文言: {new_trigger}", bg='white').pack(anchor='w')
        
        listbox = tk.Listbox(frame, width=40, height=10)
        listbox.pack(fill='both', expand=True, pady=5)
        
        shortcuts = self.shortcut_manager.get_all()
        for sc in shortcuts:
            listbox.insert('end', sc.get('name', '???'))
            
        def do_add():
            sel = listbox.curselection()
            if not sel: return
            sc = shortcuts[sel[0]]
            self.shortcut_manager.add_trigger(sc['id'], new_trigger)
            self.sc_existing_bubble.destroy()
            
        tk.Button(frame, text='追加', command=do_add, bg='#e6f2ff', relief='solid', bd=1, width=10).pack(pady=5)
        
        canvas.create_window(rect_x1 + padding, rect_y1 + padding, window=frame, width=width, height=height, anchor='nw')
        
        x_btn = tk.Label(self.sc_existing_bubble, text='✖', bg='white', fg='gray', font=('Arial', 12, 'bold'), cursor='hand2')
        x_btn.place(x=rect_x2 - 25, y=rect_y1 + 5)
        x_btn.bind('<Button-1>', lambda e: self.sc_existing_bubble.destroy())
        
        self._make_draggable(self.sc_existing_bubble, [canvas, frame, title_lbl])
        self.sc_existing_bubble.update_idletasks()
        
        bx, by = self.x + self.width - cw + 20, self.y - ch - 10
        if bx < self.display_info['x']: bx = self.display_info['x']
        self.sc_existing_bubble.geometry(f"{cw}x{ch}+{bx}+{by}")

    def open_shortcut_manager(self):
        if hasattr(self, 'sc_manage_bubble') and self.sc_manage_bubble and self.sc_manage_bubble.winfo_exists():
            self.sc_manage_bubble.destroy()
            
        self.sc_manage_bubble = tk.Toplevel(self.root)
        self.sc_manage_bubble.overrideredirect(True)
        self.sc_manage_bubble.wm_attributes("-topmost", True)
        self.sc_manage_bubble.wm_attributes("-transparentcolor", self.transparent_color)
        self.sc_manage_bubble.config(bg=self.transparent_color)
        
        canvas = tk.Canvas(self.sc_manage_bubble, bg=self.transparent_color, highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        
        width, height = 350, 400
        padding = 15
        tail_width, tail_height = 15, 15
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
        
        title_lbl = tk.Label(frame, text='ショートカット管理', font=('Meiryo', 10, 'bold'), bg='white')
        title_lbl.pack(anchor='w', pady=(0,5))
        
        listbox = tk.Listbox(frame, width=50, height=15)
        listbox.pack(fill='both', expand=True, pady=5)
        
        def refresh_list():
            listbox.delete(0, 'end')
            for sc in self.shortcut_manager.get_all():
                mark = "☑" if sc.get('enabled', True) else "☐"
                listbox.insert('end', f"{mark} {sc.get('name', '???')}")
                
        refresh_list()
        
        def toggle_enable():
            sel = listbox.curselection()
            if not sel: return
            sc = self.shortcut_manager.get_all()[sel[0]]
            self.shortcut_manager.update_shortcut(sc['id'], enabled=not sc.get('enabled', True))
            refresh_list()
            
        def do_edit():
            sel = listbox.curselection()
            if not sel: return
            sc = self.shortcut_manager.get_all()[sel[0]]
            self.open_shortcut_create(shortcut_id=sc['id'])
            # We don't close manage window so they can return
            
        def do_delete():
            sel = listbox.curselection()
            if not sel: return
            sc = self.shortcut_manager.get_all()[sel[0]]
            self.shortcut_manager.delete_shortcut(sc['id'])
            refresh_list()
            
        btn_f = tk.Frame(frame, bg='white')
        btn_f.pack(fill='x', pady=5)
        
        tk.Button(btn_f, text='ON/OFF', command=toggle_enable, bg='#f0f0f0', relief='solid', bd=1).pack(side='left', padx=2)
        tk.Button(btn_f, text='編集', command=do_edit, bg='#e6f2ff', relief='solid', bd=1).pack(side='left', padx=2)
        tk.Button(btn_f, text='削除', command=do_delete, bg='#ffe6e6', relief='solid', bd=1).pack(side='left', padx=2)
        tk.Button(btn_f, text='更新', command=refresh_list, bg='#f0f0f0', relief='solid', bd=1).pack(side='right', padx=2)
        
        canvas.create_window(rect_x1 + padding, rect_y1 + padding, window=frame, width=width, height=height, anchor='nw')
        
        x_btn = tk.Label(self.sc_manage_bubble, text='✖', bg='white', fg='gray', font=('Arial', 12, 'bold'), cursor='hand2')
        x_btn.place(x=rect_x2 - 25, y=rect_y1 + 5)
        x_btn.bind('<Button-1>', lambda e: self.sc_manage_bubble.destroy())
        
        self._make_draggable(self.sc_manage_bubble, [canvas, frame, title_lbl])
        self.sc_manage_bubble.update_idletasks()
        
        bx, by = self.x + self.width - cw + 20, self.y - ch - 10
        if bx < self.display_info['x']: bx = self.display_info['x']
        self.sc_manage_bubble.geometry(f"{cw}x{ch}+{bx}+{by}")

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
