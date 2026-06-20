#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Перенос плейлистов: Яндекс.Музыка -> YouTube Music
------------------------------------------------
• Вход только через официальные страницы Яндекса и music.youtube.com
• Для YouTube Music НЕ требуется создавать проект/приложение в Google
  Cloud Console и Client ID/Secret — используется официальный режим
  ytmusicapi «browser auth» (копирование заголовков уже залогиненной
  сессии браузера)
• Сессии сохраняются — повторный вход не нужен
• Автоматическая установка зависимостей
• Поиск треков и пакетная загрузка плейлистов
"""

import threading
import tkinter as tk
from tkinter import ttk, scrolledtext
from config import C, FONT, FONT_SM, FONT_MONO, IS_WIN
from utils import check_deps, install_deps
from widgets import W_lbl, W_btn, W_sep
from panels_auth import YMAuthPanel, YTMAuthPanel
from panel_playlists import PlaylistsPanel
from panel_transfer import TransferPanel

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Перенос плейлистов • Яндекс.Музыка -> YouTube Music")
        self.geometry("980x820")
        self.minsize(840, 680)
        self.configure(bg=C["bg"])

        if IS_WIN:
            try:
                from ctypes import windll
                windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                pass

        self.ym_client = None
        self.ytm_client = None
        self.ym_playlists = []

        self._apply_styles()

        missing = check_deps()
        if missing:
            self._screen_deps(missing)
        else:
            self._screen_main()

    def _apply_styles(self):
        st = ttk.Style()
        st.theme_use("clam")
        st.configure(".", background=C["bg"], foreground=C["text"], troughcolor=C["surface"], bordercolor=C["border"])
        st.configure("Horizontal.TProgressbar", troughcolor=C["surface"], background=C["green"], bordercolor=C["border"], lightcolor=C["green"], darkcolor=C["green"])
        st.configure("TNotebook", background=C["bg"], borderwidth=0)
        st.configure("TNotebook.Tab", background=C["card"], foreground=C["dim"], padding=[12, 6], font=FONT_SM)
        st.map("TNotebook.Tab", background=[("selected", C["surface"])], foreground=[("selected", C["text"])])
        st.configure("Vertical.TScrollbar", background=C["surface"], troughcolor=C["bg"], bordercolor=C["border"], arrowcolor=C["dim"])

    def _screen_deps(self, missing):
        for w in self.winfo_children():
            w.destroy()

        f = tk.Frame(self, bg=C["bg"], padx=60, pady=50)
        f.pack(fill="both", expand=True)

        W_lbl(f, "Установка компонентов", size=FONT[1] + 6, bold=True).pack(pady=(0, 8))
        W_lbl(f, f"Нужны пакеты: {', '.join(missing)}", color=C["dim"]).pack(pady=(0, 24))

        log = scrolledtext.ScrolledText(f, height=7, bg=C["surface"], fg=C["dim"], font=FONT_MONO, relief="flat", state="disabled")
        log.pack(fill="x", pady=(0, 20))

        def add_log(msg):
            log.configure(state="normal")
            log.insert("end", msg + "\n")
            log.see("end")
            log.configure(state="disabled")

        install_btn = W_btn(f, "Установить и продолжить", None, C["blue"])
        install_btn.pack(pady=4)

        def do_install():
            install_btn.configure(state="disabled", text="Устанавливаю...")

            def run():
                ok = install_deps(missing, lambda m: self.after(0, lambda: add_log(m)))
                if ok:
                    self.after(700, lambda: [w.destroy() for w in self.winfo_children()])
                    self.after(800, self._screen_main)
                else:
                    self.after(0, lambda: install_btn.configure(state="normal", text="Повторить"))

            threading.Thread(target=run, daemon=True).start()

        install_btn.configure(command=do_install)

    def _screen_main(self):
        for w in self.winfo_children():
            w.destroy()

        hdr = tk.Frame(self, bg=C["surface"], pady=14)
        hdr.pack(fill="x")
        W_lbl(hdr, "Перенос плейлистов", size=FONT[1] + 6, bold=True).pack()
        W_lbl(hdr, "Яндекс.Музыка -> YouTube Music", color=C["dim"], size=FONT[1] + 1).pack()
        W_sep(self)

        canvas = tk.Canvas(self, bg=C["bg"], highlightthickness=0)
        vsb = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        body = tk.Frame(canvas, bg=C["bg"])
        win_id = canvas.create_window((0, 0), window=body, anchor="nw")

        def on_resize(e):
            canvas.itemconfig(win_id, width=e.width)

        canvas.bind("<Configure>", on_resize)
        body.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        def _scroll(e):
            delta = -1 * int(e.delta / 120) if IS_WIN else (-1 if e.num == 4 else 1)
            canvas.yview_scroll(delta, "units")

        canvas.bind_all("<MouseWheel>", _scroll)
        canvas.bind_all("<Button-4>", _scroll)
        canvas.bind_all("<Button-5>", _scroll)

        self._build_body(body)

    def _build_body(self, body):
        pad = dict(padx=24, pady=12)

        auth_row = tk.Frame(body, bg=C["bg"])
        auth_row.pack(fill="x", **pad)
        auth_row.columnconfigure(0, weight=1)
        auth_row.columnconfigure(1, weight=1)

        self.ym_panel = YMAuthPanel(auth_row, app=self)
        self.ym_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        self.ytm_panel = YTMAuthPanel(auth_row, app=self)
        self.ytm_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        W_sep(body, pady=4)

        self.pl_panel = PlaylistsPanel(body, app=self)
        self.pl_panel.pack(fill="x", **pad)

        W_sep(body, pady=4)

        self.tr_panel = TransferPanel(body, app=self)
        self.tr_panel.pack(fill="both", expand=True, **pad)

    def on_ym_ready(self, client, playlists):
        self.ym_client = client
        self.ym_playlists = playlists
        self.pl_panel.load(playlists)

    def on_ytm_ready(self, client):
        self.ytm_client = client

if __name__ == "__main__":
    app = App()
    app.mainloop()