import os
import re
import threading
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox
from config import C, FONT, FONT_SM, FONT_MONO, YM_TOKEN_FILE, YM_FALLBACK_URL, YTM_AUTH_FILE, YTM_MUSIC_URL, YTM_HELP_URL
from utils import _ym_request, _read_json, _write_json
from api import _load_ym_playlists
from widgets import W_lbl, W_btn, W_entry, W_sep, W_accent

class YMAuthPanel(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=C["card"], padx=20, pady=16)
        self.app = app
        self._build()

    def _build(self):
        W_accent(self, C["ym"])
        W_lbl(self, "  Яндекс.Музыка", bold=True, size=FONT[1] + 2).pack(anchor="w")
        W_lbl(self, "Вход через официальную страницу Яндекса", color=C["dim"], size=FONT[1] - 1).pack(anchor="w", pady=(2, 14))

        self.main_btn = W_btn(self, "  Войти через Яндекс", self._open_wizard, C["ym"], fg="#111111")
        self.main_btn.pack(fill="x")

        status_row = tk.Frame(self, bg=C["card"])
        status_row.pack(fill="x", pady=(10, 0))
        self.st_var = tk.StringVar()
        self.st_lbl = tk.Label(status_row, textvariable=self.st_var, bg=C["card"], fg=C["dim"], font=FONT_SM, wraplength=280, justify="left", anchor="w")
        self.st_lbl.pack(side="left", fill="x", expand=True)
        self.logout_btn = W_btn(status_row, "Выйти", self._logout, C["surface"], size=FONT[1] - 1)
        self.logout_btn.pack(side="right")
        self.logout_btn.pack_forget()

        self._try_saved()

    def _open_wizard(self):
        YMWizard(self.app, on_success=self._on_ok)

    def _try_saved(self):
        data = _read_json(YM_TOKEN_FILE)
        tok = data.get("token", "")
        if not tok:
            return
        self._set_status("Загружаю сохранённую сессию...", C["blue"])
        self._lock(True)

        def run():
            try:
                from yandex_music import Client
                client = Client(tok, request=_ym_request()).init()
                pls = _load_ym_playlists(client)
                self.app.after(0, lambda: self._on_ok(client, pls))
            except Exception:
                self.app.after(0, lambda: self._set_status("", C["dim"]))
                self.app.after(0, lambda: self._lock(False))

        threading.Thread(target=run, daemon=True).start()

    def _on_ok(self, client, playlists):
        self._set_status(f"Подключено • {len(playlists)} плейлистов • сессия сохранена", C["green"])
        self._lock(False)
        self.main_btn.configure(text="Яндекс.Музыка подключена", bg=C["green"], state="disabled")
        self.logout_btn.pack(side="right")
        self.app.on_ym_ready(client, playlists)

    def _logout(self):
        try:
            if YM_TOKEN_FILE.exists():
                YM_TOKEN_FILE.unlink()
        except Exception:
            pass
        self.app.ym_client = None
        self.app.ym_playlists = []
        self.app.pl_panel.load([])
        self.main_btn.configure(text="  Войти через Яндекс", bg=C["ym"], state="normal")
        self.logout_btn.pack_forget()
        self._set_status("Вы вышли из аккаунта", C["dim"])

    def _set_status(self, t, color):
        self.st_var.set(t)
        self.st_lbl.configure(fg=color)

    def _lock(self, locked):
        self.main_btn.configure(state="disabled" if locked else "normal")

class YMWizard(tk.Toplevel):
    def __init__(self, parent, on_success):
        super().__init__(parent)
        self.app = parent
        self.on_success = on_success
        self.title("Вход в Яндекс.Музыку")
        self.geometry("480x420")
        self.minsize(440, 380)
        self.configure(bg=C["bg"])
        self.grab_set()
        self.transient(parent)
        self._cancelled = False

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._hdr = tk.Frame(self, bg=C["surface"], pady=12)
        self._hdr.pack(fill="x")
        W_sep(self)
        self._body = tk.Frame(self, bg=C["card"], padx=24, pady=20)
        self._body.pack(fill="both", expand=True, padx=20, pady=16)

        self._build_loading()
        threading.Thread(target=self._run_device_flow, daemon=True).start()

    def _clear(self):
        for w in self._hdr.winfo_children():
            w.destroy()
        for w in self._body.winfo_children():
            w.destroy()

    def _on_close(self):
        self._cancelled = True
        self.destroy()

    def _build_loading(self):
        self._clear()
        W_lbl(self._hdr, "  Вход в Яндекс.Музыку", bold=True, size=FONT[1] + 2).pack()
        W_lbl(self._hdr, "Получаю код для входа у Яндекса...", color=C["dim"]).pack()
        W_lbl(self._body, "Подождите секунду...", color=C["dim"]).pack(pady=20)

    def _build_code_screen(self, verification_url, user_code):
        self._clear()
        W_lbl(self._hdr, "  Подтвердите вход", bold=True, size=FONT[1] + 2).pack()
        W_lbl(self._hdr, "Открыта официальная страница Яндекса", color=C["dim"]).pack()

        W_lbl(self._body, "1. В открывшемся окне браузера войдите в аккаунт Яндекс\n2. Введите код, показанный ниже\n3. Нажмите «Подтвердить» на странице Яндекса", color=C["text"], size=FONT[1] - 1, wraplength=420, justify="left").pack(anchor="w", pady=(0, 16))

        code_box = tk.Frame(self._body, bg=C["surface"], highlightthickness=1, highlightbackground=C["border"])
        code_box.pack(fill="x", pady=(0, 16))
        W_lbl(code_box, user_code, bold=True, size=FONT[1] + 10, color=C["ym"]).pack(pady=14)

        W_btn(self._body, "Открыть страницу Яндекса снова", lambda: webbrowser.open(verification_url), C["surface"]).pack(fill="x", pady=(0, 14))

        self.status_var = tk.StringVar(value="Ожидаю подтверждения в браузере...")
        self.status_lbl = tk.Label(self._body, textvariable=self.status_var, bg=C["card"], fg=C["blue"], font=FONT_SM, wraplength=420, justify="left")
        self.status_lbl.pack(anchor="w")

        bottom = tk.Frame(self._body, bg=C["card"])
        bottom.pack(fill="x", pady=(20, 0))
        W_btn(bottom, "Отмена", self._on_close, C["surface"]).pack(side="left")
        W_btn(bottom, "Другой способ входа", self._build_fallback, C["surface"]).pack(side="right")

    def _build_fallback(self):
        self._cancelled = True
        self._clear()
        W_lbl(self._hdr, "  Вход через браузер", bold=True, size=FONT[1] + 2).pack()
        W_lbl(self._hdr, "Запасной способ", color=C["dim"]).pack()

        W_lbl(self._body, "1. Откроется страница Яндекса\n2. Войдите и разрешите доступ\n3. Яндекс покажет код подтверждения — скопируйте его\n4. Вставьте код в поле ниже", color=C["text"], size=FONT[1] - 1, wraplength=420, justify="left").pack(anchor="w", pady=(0, 14))

        W_btn(self._body, "  Открыть страницу Яндекса", lambda: webbrowser.open(YM_FALLBACK_URL), C["surface"]).pack(fill="x", pady=(0, 14))

        W_lbl(self._body, "Код подтверждения:", color=C["dim"], size=FONT[1] - 1).pack(anchor="w")
        self.tok_var = tk.StringVar()
        self.entry = W_entry(self._body, var=self.tok_var)
        self.entry.pack(fill="x", pady=(2, 14))
        self.entry.bind("<Return>", lambda e: self._connect_token())
        self.entry.focus_set()

        self.go_btn = W_btn(self._body, "Подключить", self._connect_token, C["ym"], fg="#111111")
        self.go_btn.pack(fill="x")

        self.status_var = tk.StringVar()
        self.status_lbl = tk.Label(self._body, textvariable=self.status_var, bg=C["card"], fg=C["dim"], font=FONT_SM, wraplength=420, justify="left")
        self.status_lbl.pack(anchor="w", pady=(10, 0))

        W_btn(self._body, "Отмена", self._on_close, C["surface"]).pack(anchor="w", pady=(16, 0))

        webbrowser.open(YM_FALLBACK_URL)

    def _connect_token(self):
        raw = self.tok_var.get().strip()
        m = re.search(r"access_token=([^&\s]+)", raw)
        token = m.group(1) if m else raw
        if len(token) < 20:
            self.status_var.set("Вставьте код подтверждения со страницы Яндекса")
            self.status_lbl.configure(fg=C["red"])
            return

        self.go_btn.configure(state="disabled", text="Проверяю...")
        self.status_var.set("Подключение...")
        self.status_lbl.configure(fg=C["blue"])

        def run():
            try:
                from yandex_music import Client
                client = Client(token, request=_ym_request()).init()
                pls = _load_ym_playlists(client)
                _write_json(YM_TOKEN_FILE, {"token": token})
                self.app.after(0, lambda: self._finish(client, pls))
            except Exception as e:
                msg = str(e)[:150]
                self.app.after(0, lambda m=msg: self._on_fail(m))

        threading.Thread(target=run, daemon=True).start()

    def _run_device_flow(self):
        try:
            from yandex_music import Client
        except Exception as e:
            self.after(0, lambda: self._on_fail(f"Не удалось загрузить библиотеку: {e}"))
            return

        client = Client(request=_ym_request())

        if not hasattr(client, "device_auth"):
            self.after(0, self._build_fallback)
            return

        code_holder = {}

        def on_code(code):
            if self._cancelled:
                return
            code_holder["code"] = code
            self.after(0, lambda: self._build_code_screen(code.verification_url, code.user_code))
            webbrowser.open(code.verification_url)

        try:
            token = client.device_auth(on_code=on_code)
        except Exception as e:
            if self._cancelled:
                return
            msg = str(e)[:150]
            self.after(0, lambda m=msg: self._on_fail(m))
            return

        if self._cancelled:
            return

        try:
            client = Client(token.access_token, request=_ym_request()).init()
            pls = _load_ym_playlists(client)
            _write_json(YM_TOKEN_FILE, {"token": token.access_token})
            self.after(0, lambda: self._finish(client, pls))
        except Exception as e:
            msg = str(e)[:150]
            self.after(0, lambda m=msg: self._on_fail(m))

    def _on_fail(self, msg):
        if not self.winfo_exists():
            return
        if hasattr(self, "status_var"):
            self.status_var.set(f"Ошибка: {msg}")
            self.status_lbl.configure(fg=C["red"])
            if hasattr(self, "go_btn"):
                self.go_btn.configure(state="normal", text="Подключить")
        else:
            self._build_fallback()

    def _finish(self, client, playlists):
        if not self.winfo_exists():
            return
        messagebox.showinfo("Яндекс.Музыка подключена!", "Аккаунт успешно подключён.\nСессия сохранена — следующий вход будет автоматическим.", parent=self)
        self.on_success(client, playlists)
        self.destroy()

class YTMAuthPanel(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=C["card"], padx=20, pady=16)
        self.app = app
        self._build()

    def _build(self):
        W_accent(self, C["ytm"])
        W_lbl(self, "  YouTube Music", bold=True, size=FONT[1] + 2).pack(anchor="w")
        W_lbl(self, "Вход через music.youtube.com • без проекта Google", color=C["dim"], size=FONT[1] - 1).pack(anchor="w", pady=(2, 14))

        self.main_btn = W_btn(self, "  Войти в YouTube Music", self._open_wizard, C["ytm"])
        self.main_btn.pack(fill="x")

        status_row = tk.Frame(self, bg=C["card"])
        status_row.pack(fill="x", pady=(10, 0))
        self.st_var = tk.StringVar()
        self.st_lbl = tk.Label(status_row, textvariable=self.st_var, bg=C["card"], fg=C["dim"], font=FONT_SM, wraplength=280, justify="left", anchor="w")
        self.st_lbl.pack(side="left", fill="x", expand=True)
        self.logout_btn = W_btn(status_row, "Выйти", self._logout, C["surface"], size=FONT[1] - 1)
        self.logout_btn.pack(side="right")
        self.logout_btn.pack_forget()

        self._try_saved()

    def _open_wizard(self):
        YTMWizard(self.app, on_success=self._on_ok)

    def _try_saved(self):
        if not os.path.exists(YTM_AUTH_FILE):
            return
        self._set_status("Загружаю сохранённую сессию...", C["blue"])
        self._lock(True)

        def run():
            try:
                from ytmusicapi import YTMusic
                ytm = YTMusic(YTM_AUTH_FILE)
                ytm.get_library_playlists(limit=1)
                self.app.after(0, lambda: self._on_ok(ytm))
            except Exception:
                self.app.after(0, lambda: self._set_status("", C["dim"]))
                self.app.after(0, lambda: self._lock(False))

        threading.Thread(target=run, daemon=True).start()

    def _on_ok(self, ytm):
        self._set_status("Подключено • сессия сохранена", C["green"])
        self._lock(False)
        self.main_btn.configure(text="YouTube Music подключён", bg=C["green"], state="disabled")
        self.logout_btn.pack(side="right")
        self.app.on_ytm_ready(ytm)

    def _logout(self):
        try:
            if os.path.exists(YTM_AUTH_FILE):
                os.remove(YTM_AUTH_FILE)
        except Exception:
            pass
        self.app.ytm_client = None
        self.main_btn.configure(text="  Войти в YouTube Music", bg=C["ytm"], state="normal")
        self.logout_btn.pack_forget()
        self._set_status("Вы вышли из аккаунта", C["dim"])

    def _set_status(self, t, color):
        self.st_var.set(t)
        self.st_lbl.configure(fg=color)

    def _lock(self, locked):
        self.main_btn.configure(state="disabled" if locked else "normal")

class YTMWizard(tk.Toplevel):
    def __init__(self, parent, on_success):
        super().__init__(parent)
        self.app = parent
        self.on_success = on_success
        self.title("Вход в YouTube Music")
        self.geometry("560x680")
        self.minsize(480, 560)
        self.configure(bg=C["bg"])
        self.grab_set()
        self.transient(parent)
        self._cancelled = False

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._hdr = tk.Frame(self, bg=C["surface"], pady=12)
        self._hdr.pack(fill="x")
        W_sep(self)

        canvas = tk.Canvas(self, bg=C["card"], highlightthickness=0)
        vsb = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self._body = tk.Frame(canvas, bg=C["card"], padx=24, pady=20)
        win_id = canvas.create_window((0, 0), window=self._body, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win_id, width=e.width))
        self._body.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        self._build_form()

    def _clear(self):
        for w in self._hdr.winfo_children():
            w.destroy()
        for w in self._body.winfo_children():
            w.destroy()

    def _on_close(self):
        self._cancelled = True
        self.destroy()

    def _build_form(self):
        self._clear()
        W_lbl(self._hdr, "  Вход в YouTube Music", bold=True, size=FONT[1] + 2).pack()
        W_lbl(self._hdr, "Через music.youtube.com • без проекта Google", color=C["dim"]).pack()

        W_lbl(self._body, "Google теперь требует, чтобы у каждого приложения был свой проект в Google Cloud для входа по коду (как в Яндекс.Музыке). Чтобы этого избежать, вход выполняется иначе — через копирование заголовков вашей уже авторизованной сессии браузера. Это официальный способ входа в ytmusicapi («browser auth»), он не требует Client ID/Secret и ничего не создаёт в Google Cloud.", color=C["dim"], size=FONT[1] - 2, wraplength=480, justify="left").pack(anchor="w", pady=(0, 14))

        steps = (
            "1.  Откроется music.youtube.com — войдите в свой аккаунт Google, если ещё не вошли\n"
            "2.  Откройте инструменты разработчика: F12 или Ctrl+Shift+I (на Mac — ⌥⌘I), вкладка «Сеть» / «Network»\n"
            "3.  В поле фильтра введите: browse\n"
            "4.  Откройте раздел «Медиатека» на сайте — в списке запросов появится browse?...\n"
            "5.  Chrome / Edge: щёлкните по запросу -> вкладка «Заголовки» -> в разделе «Заголовки запроса» скопируйте всё, начиная со строки accept: */*\n"
            "     Firefox: правой кнопкой по запросу -> Копировать -> Заголовки запроса\n"
            "6.  Вставьте скопированный текст целиком в поле ниже"
        )
        W_lbl(self._body, steps, color=C["text"], size=FONT[1] - 2, wraplength=480, justify="left").pack(anchor="w", pady=(0, 14))

        W_btn(self._body, "  Открыть music.youtube.com", lambda: webbrowser.open(YTM_MUSIC_URL), C["surface"]).pack(fill="x", pady=(0, 6))
        W_btn(self._body, "  Подробная инструкция со скриншотами", lambda: webbrowser.open(YTM_HELP_URL), C["surface"]).pack(fill="x", pady=(0, 14))

        W_lbl(self._body, "Заголовки запроса (request headers):", color=C["dim"], size=FONT[1] - 1).pack(anchor="w")

        txt_frame = tk.Frame(self._body, bg=C["surface"], highlightthickness=1, highlightbackground=C["border"])
        txt_frame.pack(fill="both", pady=(2, 14))
        self.headers_txt = tk.Text(txt_frame, height=9, bg=C["surface"], fg=C["text"], insertbackground=C["text"], relief="flat", bd=6, font=FONT_MONO, wrap="word")
        self.headers_txt.pack(fill="both", expand=True)

        self.go_btn = W_btn(self._body, "Подключить", self._connect, C["ytm"])
        self.go_btn.pack(fill="x")

        self.status_var = tk.StringVar()
        self.status_lbl = tk.Label(self._body, textvariable=self.status_var, bg=C["card"], fg=C["dim"], font=FONT_SM, wraplength=480, justify="left")
        self.status_lbl.pack(anchor="w", pady=(10, 0))

        W_btn(self._body, "Отмена", self._on_close, C["surface"]).pack(anchor="w", pady=(16, 0))

        webbrowser.open(YTM_MUSIC_URL)

    def _connect(self):
        raw = self.headers_txt.get("1.0", "end").strip()

        if len(raw) < 50 or "cookie" not in raw.lower():
            self.status_var.set("Похоже, скопирован не весь блок заголовков. Убедитесь, что в тексте есть строки Cookie и Authorization, и вставьте его целиком.")
            self.status_lbl.configure(fg=C["red"])
            return

        self.go_btn.configure(state="disabled", text="Проверяю...")
        self.status_var.set("Подключение...")
        self.status_lbl.configure(fg=C["blue"])

        threading.Thread(target=self._do_connect, args=(raw,), daemon=True).start()

    def _do_connect(self, raw):
        try:
            import ytmusicapi
            from ytmusicapi import YTMusic

            ytmusicapi.setup(filepath=YTM_AUTH_FILE, headers_raw=raw)

            if self._cancelled:
                return

            ytm = YTMusic(YTM_AUTH_FILE)
            ytm.get_library_playlists(limit=1)
            self.after(0, lambda: self._finish(ytm))
        except Exception as e:
            if self._cancelled:
                return
            msg = str(e)[:200]
            self.after(0, lambda m=msg: self._on_fail(m))

    def _on_fail(self, msg):
        if not self.winfo_exists():
            return
        self.status_var.set(f"Ошибка: {msg}")
        self.status_lbl.configure(fg=C["red"])
        self.go_btn.configure(state="normal", text="Подключить")

    def _finish(self, ytm):
        if not self.winfo_exists():
            return
        messagebox.showinfo("YouTube Music подключён!", "Аккаунт успешно подключён.\nСессия сохранена — следующий вход будет автоматическим.\n\nЭта сессия действует, пока вы не выйдете из аккаунта в браузере (обычно около 2 лет).", parent=self)
        self.on_success(ytm)
        self.destroy()