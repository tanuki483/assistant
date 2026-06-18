import threading
import time
import ctypes

# 仮想キーコードのマッピング
VK_MAP = {
    'ctrl': 0x11,   # VK_CONTROL
    'alt': 0x12,    # VK_MENU
    'shift': 0x10,  # VK_SHIFT
    'none': None,
}

# アルファベット・数字キーのマッピング
def _key_to_vk(key_str):
    """キー文字列を仮想キーコードに変換"""
    key_str = key_str.strip().upper()
    if len(key_str) == 1 and key_str.isalpha():
        return ord(key_str)
    if len(key_str) == 1 and key_str.isdigit():
        return ord(key_str)
    # ファンクションキー
    if key_str.startswith('F') and key_str[1:].isdigit():
        fnum = int(key_str[1:])
        if 1 <= fnum <= 24:
            return 0x70 + (fnum - 1)  # VK_F1 = 0x70
    return None


class HotkeyManager:
    """
    ctypes (user32.dll GetAsyncKeyState) を使用したグローバルホットキー監視。
    バックグラウンドスレッドで修飾キー＋メインキーの同時押しを検出し、
    コールバックを呼び出す。
    """

    def __init__(self, callback, config):
        """
        callback: ホットキーが押されたときに呼ばれる関数（メインスレッドへの転送は呼び出し側で行う）
        config: dict with keys 'hotkey_mod1', 'hotkey_mod2', 'hotkey_key'
                mod1, mod2: 'ctrl', 'alt', 'shift', 'none'
                key: アルファベット1文字 or 'F1'-'F24'
        """
        self._callback = callback
        self._running = False
        self._thread = None
        self._user32 = ctypes.windll.user32
        self.update_config(config)

    def update_config(self, config):
        """設定を更新（スレッド実行中でも呼び出し可能）"""
        mod1 = config.get('hotkey_mod1', 'ctrl').lower()
        mod2 = config.get('hotkey_mod2', 'shift').lower()
        key = config.get('hotkey_key', 's')

        self._mod_vks = []
        for mod in [mod1, mod2]:
            vk = VK_MAP.get(mod)
            if vk is not None:
                self._mod_vks.append(vk)

        self._main_vk = _key_to_vk(key)

    def start(self):
        """監視スレッドを開始"""
        if self._thread and self._thread.is_alive():
            return
        self._running = True
        self._thread = threading.Thread(target=self._poll, daemon=True)
        self._thread.start()

    def stop(self):
        """監視スレッドを停止"""
        self._running = False

    def _is_key_pressed(self, vk):
        """キーが現在押されているかチェック (最上位ビットが1なら押下中)"""
        state = self._user32.GetAsyncKeyState(vk)
        return (state & 0x8000) != 0

    def _poll(self):
        """0.05秒間隔でキー状態を監視"""
        while self._running:
            try:
                if self._main_vk is not None and len(self._mod_vks) > 0:
                    # 全修飾キーが押されているか
                    all_mods_pressed = all(self._is_key_pressed(vk) for vk in self._mod_vks)
                    # メインキーが押されているか
                    main_pressed = self._is_key_pressed(self._main_vk)

                    if all_mods_pressed and main_pressed:
                        self._callback()
                        # 連打防止: キーが離されるまで待つ
                        time.sleep(0.3)
                        while self._running and self._is_key_pressed(self._main_vk):
                            time.sleep(0.05)
            except Exception:
                pass
            time.sleep(0.05)
