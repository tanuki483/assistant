import os
import sys
import json
import uuid
import subprocess
import webbrowser
from janome.tokenizer import Tokenizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class ShortcutManager:
    """日本語ショートカットの管理・検索・実行を行うマネージャー"""

    def __init__(self, base_dir, win_manager=None, config=None):
        self.base_dir = base_dir
        self.json_path = os.path.join(base_dir, "shortcuts.json")
        self.win_manager = win_manager
        self.config = config  # tts_manager.config への参照（デフォルト値取得用）
        self.tokenizer = Tokenizer()
        self.vectorizer = TfidfVectorizer()
        self.tfidf_matrix = None
        self.trigger_map = []  # [shortcut_index, ...]
        self.shortcuts = []
        self.load()

    # ========== データ管理 ==========

    def load(self):
        """JSONファイルからショートカットを読み込み、TF-IDFインデックスを再構築"""
        if os.path.exists(self.json_path):
            try:
                with open(self.json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.shortcuts = data.get("shortcuts", [])
            except (json.JSONDecodeError, IOError):
                self.shortcuts = []
        else:
            self.shortcuts = []
        self._rebuild_index()

    def save(self):
        """ショートカットをJSONファイルに保存し、TF-IDFインデックスを再構築"""
        data = {"shortcuts": self.shortcuts}
        with open(self.json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        self._rebuild_index()

    def add_shortcut(self, name, triggers, actions):
        """新規ショートカットを追加して保存。追加されたショートカットを返す"""
        shortcut = {
            "id": uuid.uuid4().hex[:8],
            "name": name,
            "triggers": triggers if isinstance(triggers, list) else [triggers],
            "actions": actions if isinstance(actions, list) else [actions],
            "enabled": True
        }
        self.shortcuts.append(shortcut)
        self.save()
        return shortcut

    def update_shortcut(self, shortcut_id, name=None, triggers=None, actions=None, enabled=None):
        """既存ショートカットを更新"""
        sc = self.get_by_id(shortcut_id)
        if sc is None:
            return None
        if name is not None:
            sc["name"] = name
        if triggers is not None:
            sc["triggers"] = triggers
        if actions is not None:
            sc["actions"] = actions
        if enabled is not None:
            sc["enabled"] = enabled
        self.save()
        return sc

    def delete_shortcut(self, shortcut_id):
        """ショートカットを削除"""
        self.shortcuts = [s for s in self.shortcuts if s["id"] != shortcut_id]
        self.save()

    def add_trigger(self, shortcut_id, trigger_text):
        """既存ショートカットにトリガーを追加"""
        sc = self.get_by_id(shortcut_id)
        if sc and trigger_text not in sc["triggers"]:
            sc["triggers"].append(trigger_text)
            self.save()
        return sc

    def remove_trigger(self, shortcut_id, trigger_text):
        """既存ショートカットからトリガーを削除"""
        sc = self.get_by_id(shortcut_id)
        if sc and trigger_text in sc["triggers"]:
            sc["triggers"].remove(trigger_text)
            self.save()
        return sc

    def get_all(self):
        """全ショートカットのリストを返す"""
        return list(self.shortcuts)

    def get_by_id(self, shortcut_id):
        """IDでショートカットを検索"""
        for sc in self.shortcuts:
            if sc["id"] == shortcut_id:
                return sc
        return None

    # ========== TF-IDF 検索 ==========

    @staticmethod
    def _kata_to_hira(text):
        """カタカナをひらがなに変換（U+30A1-U+30F6 → U+3041-U+3096）"""
        result = []
        for ch in text:
            cp = ord(ch)
            if 0x30A1 <= cp <= 0x30F6:
                result.append(chr(cp - 0x60))
            else:
                result.append(ch)
        return "".join(result)

    def _tokenize(self, text):
        """Janomeで形態素解析し、カタカナ→ひらがな正規化後にスペース区切りの文字列に変換"""
        try:
            text = self._kata_to_hira(text)
            tokens = list(self.tokenizer.tokenize(text, wakati=True))
            return " ".join(tokens)
        except Exception:
            return self._kata_to_hira(text)

    def _rebuild_index(self):
        """全トリガーをTF-IDFベクトル化してインデックスを構築"""
        all_triggers_tokenized = []
        self.trigger_map = []

        for i, sc in enumerate(self.shortcuts):
            if not sc.get("enabled", True):
                continue
            for trigger in sc.get("triggers", []):
                tokenized = self._tokenize(trigger)
                if tokenized.strip():
                    all_triggers_tokenized.append(tokenized)
                    self.trigger_map.append(i)

        if all_triggers_tokenized:
            try:
                self.tfidf_matrix = self.vectorizer.fit_transform(all_triggers_tokenized)
            except Exception:
                self.tfidf_matrix = None
        else:
            self.tfidf_matrix = None

    def search(self, query):
        """
        入力テキストを全トリガーとTF-IDFコサイン類似度で比較。
        戻り値: (best_shortcut or None, score: float)
        """
        if self.tfidf_matrix is None or len(self.trigger_map) == 0:
            return None, 0.0

        query_tokenized = self._tokenize(query)
        if not query_tokenized.strip():
            return None, 0.0

        try:
            query_vec = self.vectorizer.transform([query_tokenized])
            scores = cosine_similarity(query_vec, self.tfidf_matrix)[0]
        except Exception:
            return None, 0.0

        best_idx = scores.argmax()
        best_score = float(scores[best_idx])

        threshold = self.config.get('shortcut_threshold', 0.1) if self.config else 0.1
        if best_score < threshold:
            return None, best_score

        shortcut_idx = self.trigger_map[best_idx]
        return self.shortcuts[shortcut_idx], best_score

    # ========== アクション実行 ==========

    def execute(self, shortcut):
        """
        ショートカットの全アクションを実行し、結果ログのリストを返す。
        各結果: {"type": str, "value": ..., "success": bool, "error": str|None}
        """
        results = []
        for action in shortcut.get("actions", []):
            result = self._execute_action(action)
            results.append(result)
        return results

    def test_action(self, action):
        """単一アクションのテスト実行。結果dictを返す"""
        return self._execute_action(action)

    def _execute_action(self, action):
        """アクションタイプに応じて実行"""
        action_type = action.get("type", "")
        value = action.get("value", "")
        result = {"type": action_type, "value": value, "success": False, "error": None}

        try:
            if action_type == "open":
                # 引数対応: valueがdictの場合 {"path": "...", "args": ["arg1", ...]}
                if isinstance(value, dict):
                    path = value.get("path", "")
                    args = value.get("args", [])
                    # 文字列の場合はカンマ区切りでリスト化
                    if isinstance(args, str):
                        args = [a.strip() for a in args.split(',') if a.strip()]
                else:
                    path = str(value)
                    args = []
                
                if args:
                    # 引数がある場合はsubprocessで起動
                    ext = os.path.splitext(path)[1].lower()
                    if ext == '.py':
                        cmd = [sys.executable, path] + args
                    elif ext == '.pyw':
                        # pythonwを探す
                        pythonw = os.path.join(os.path.dirname(sys.executable), 'pythonw.exe')
                        if not os.path.exists(pythonw):
                            pythonw = sys.executable
                        cmd = [pythonw, path] + args
                    else:
                        cmd = [path] + args
                    subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    os.startfile(path)
                result["success"] = True

            elif action_type == "command":
                subprocess.Popen(
                    value,
                    shell=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                result["success"] = True

            elif action_type == "text_file":
                # 新フォーマット: {"dir": ..., "filename": ..., "ext": ..., "content": ...}
                if isinstance(value, dict):
                    # デフォルト値をconfigから取得
                    default_dir = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")
                    default_ext = ".txt"
                    if self.config:
                        default_dir = self.config.get('text_file_default_dir', default_dir)
                        default_ext = self.config.get('text_file_default_ext', default_ext)
                    
                    save_dir = value.get("dir", "").strip() or default_dir
                    filename = value.get("filename", "output").strip() or "output"
                    ext = value.get("ext", "").strip() or default_ext
                    content = value.get("content", "")
                    
                    # 拡張子にドットがなければ付加
                    if ext and not ext.startswith('.'):
                        ext = '.' + ext
                    
                    file_path = os.path.join(save_dir, filename + ext)
                else:
                    # 旧フォーマット互換: 文字列の場合はそのままパスとして扱う
                    file_path = str(value) if value else os.path.join(
                        os.environ.get("USERPROFILE", ""), "Desktop", "output.txt")
                    content = ""
                
                # 親ディレクトリを作成
                parent = os.path.dirname(file_path)
                if parent and not os.path.exists(parent):
                    os.makedirs(parent, exist_ok=True)
                # 上書き保護モード
                protect = value.get("protect", False) if isinstance(value, dict) else False
                if protect and os.path.exists(file_path):
                    base, fext = os.path.splitext(file_path)
                    counter = 1
                    while os.path.exists(file_path):
                        file_path = f"{base}({counter}){fext}"
                        counter += 1
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                # 作成後にファイルを開く
                if isinstance(value, dict):
                    open_after = value.get("open_after", False)
                    open_with_notepad = value.get("open_with_notepad", False)
                    if open_with_notepad:
                        subprocess.Popen(['notepad.exe', file_path], creationflags=subprocess.CREATE_NO_WINDOW)
                    elif open_after:
                        os.startfile(file_path)
                result["success"] = True

            elif action_type == "window":
                if self.win_manager:
                    name = value.get("name", "")
                    match_type = value.get("match", "starts_with")
                    found = self.win_manager.activate_window_by_name(name, match_type)
                    result["success"] = found is not None
                    if not found:
                        result["error"] = f"ウィンドウ '{name}' が見つかりませんでした"
                else:
                    result["error"] = "WindowManagerが利用できません"

            else:
                result["error"] = f"不明なアクションタイプ: {action_type}"

        except Exception as e:
            result["error"] = str(e)

        return result

    def format_action_summary(self, action):
        """アクションの概要を人間に読める文字列で返す"""
        action_type = action.get("type", "")
        value = action.get("value", "")

        if action_type == "open":
            if isinstance(value, dict):
                path = value.get('path', '')
                args = value.get('args', [])
                if args:
                    args_str = ', '.join(args) if isinstance(args, list) else str(args)
                    return f"開く: {path} (引数: {args_str})"
                return f"開く: {path}"
            return f"開く: {value}"
        elif action_type == "command":
            return f"コマンド: {value}"
        elif action_type == "text_file":
            if isinstance(value, dict):
                fn = value.get('filename', 'output')
                ext = value.get('ext', '.txt')
                d = value.get('dir', 'デスクトップ') or 'デスクトップ'
                return f"テキスト生成: {fn}{ext} → {d}"
            return f"テキスト生成: {value}"
        elif action_type == "window":
            name = value.get("name", "") if isinstance(value, dict) else str(value)
            match = value.get("match", "") if isinstance(value, dict) else ""
            match_label = "で始まる" if match == "starts_with" else "で終わる"
            return f"ウィンドウ: 「{name}」{match_label}"
        else:
            return f"{action_type}: {value}"

    def format_result_detail(self, result):
        """実行結果の詳細を文字列で返す"""
        status = "✅ 成功" if result["success"] else "❌ 失敗"
        detail = f"[{result['type']}] {result['value']}\n  → {status}"
        if result.get("error"):
            detail += f"\n  エラー: {result['error']}"
        return detail
