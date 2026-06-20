import threading
import tkinter as tk
from tkinter import ttk
from config import C, FONT, FONT_SM
from widgets import W_lbl, W_btn, W_entry, W_accent
from api import YM_PLAYLIST_URL_RE

class PlaylistsPanel(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=C["card"], padx=20, pady=16)
        self.app = app
        self._vars = {}
        self._rows = {}
        self._build()

    def _build(self):
        W_accent(self, C["blue"])

        hdr = tk.Frame(self, bg=C["card"])
        hdr.pack(fill="x", pady=(0, 10))

        W_lbl(hdr, "  Плейлисты для переноса", bold=True, size=FONT[1] + 1).pack(side="left")

        btns = tk.Frame(hdr, bg=C["card"])
        btns.pack(side="right")
        W_btn(btns, "Выбрать все", lambda: self._set_all(True), C["surface"]).pack(side="left", padx=(0, 6))
        W_btn(btns, "Снять все", lambda: self._set_all(False), C["surface"]).pack(side="left")

        link_row = tk.Frame(self, bg=C["card"])
        link_row.pack(fill="x", pady=(0, 4))

        W_lbl(link_row, "  Ссылка на плейлист Яндекс.Музыки:", color=C["dim"], size=FONT[1] - 1).pack(anchor="w")

        link_input_row = tk.Frame(self, bg=C["card"])
        link_input_row.pack(fill="x", pady=(2, 4))

        self.link_var = tk.StringVar()
        self.link_entry = W_entry(link_input_row, var=self.link_var)
        self.link_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.link_entry.bind("<Return>", lambda e: self._add_by_link())

        self.link_btn = W_btn(link_input_row, "Добавить", self._add_by_link, C["surface"])
        self.link_btn.pack(side="left")

        self.link_status_var = tk.StringVar(value="Например: music.yandex.ru/users/login/playlists/1000 (подходит и для плейлиста «Мне нравится»)")
        self.link_status_lbl = tk.Label(self, textvariable=self.link_status_var, bg=C["card"], fg=C["dim"], font=FONT_SM, wraplength=520, justify="left", anchor="w")
        self.link_status_lbl.pack(fill="x", pady=(0, 10))

        cont = tk.Frame(self, bg=C["surface"])
        cont.pack(fill="x")

        self._canvas = tk.Canvas(cont, bg=C["surface"], height=190, highlightthickness=0)
        vsb = ttk.Scrollbar(cont, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        self._inner = tk.Frame(self._canvas, bg=C["surface"])
        self._win = self._canvas.create_window((0, 0), window=self._inner, anchor="nw")

        self._inner.bind("<Configure>", lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>", lambda e: self._canvas.itemconfig(self._win, width=e.width))

        W_lbl(self._inner, "Войдите в Яндекс.Музыку, чтобы увидеть плейлисты", color=C["dim"]).pack(pady=30)

    def load(self, playlists):
        for w in self._inner.winfo_children():
            w.destroy()
        self._vars.clear()
        self._rows.clear()

        if not playlists:
            W_lbl(self._inner, "Нет плейлистов", color=C["dim"]).pack(pady=30)
            return

        for pl in playlists:
            kind = getattr(pl, "kind", None)
            if kind is None:
                continue
            self._add_row((None, kind), pl, checked=True)

    def _add_by_link(self):
        raw = self.link_var.get().strip()
        if not raw:
            return

        if not self.app.ym_client:
            self._set_link_status("Сначала войдите в Яндекс.Музыку", C["red"])
            return

        m = YM_PLAYLIST_URL_RE.search(raw)
        if not m:
            self._set_link_status("Не удалось распознать ссылку. Нужен формат вида music.yandex.ru/users/<логин>/playlists/<номер>", C["red"])
            return

        uid_raw, kind_raw = m.group(1), int(m.group(2))
        user_id = int(uid_raw) if uid_raw.isdigit() else uid_raw

        if (user_id, kind_raw) in self._vars:
            self._set_link_status("Этот плейлист уже в списке", C["dim"])
            return

        self.link_btn.configure(state="disabled", text="Загружаю...")
        self._set_link_status("Загружаю плейлист...", C["blue"])

        threading.Thread(target=self._fetch_link_playlist, args=(user_id, kind_raw), daemon=True).start()

    def _fetch_link_playlist(self, user_id, kind):
        ym = self.app.ym_client
        try:
            pl = ym.users_playlists(kind, user_id=user_id)
            if isinstance(pl, list):
                pl = pl[0] if pl else None
            if pl is None:
                raise ValueError("Плейлист не найден или недоступен")
        except Exception as e:
            msg = str(e)[:150]
            self.app.after(0, lambda: self._on_link_fail(msg))
            return

        self.app.after(0, lambda: self._on_link_ok(user_id, kind, pl))

    def _on_link_ok(self, user_id, kind, pl):
        ref = (user_id, kind)
        title = getattr(pl, "title", None) or f"Плейлист #{kind}"
        if ref in self._vars:
            self._set_link_status("Этот плейлист уже в списке", C["dim"])
        else:
            self._add_row(ref, pl, checked=True, removable=True)
            self._set_link_status(f"Добавлен: {title}", C["green"])
            self.link_var.set("")
        self.link_btn.configure(state="normal", text="Добавить")

    def _on_link_fail(self, msg):
        self._set_link_status(f"Ошибка: {msg}", C["red"])
        self.link_btn.configure(state="normal", text="Добавить")

    def _set_link_status(self, text, color):
        self.link_status_var.set(text)
        self.link_status_lbl.configure(fg=color)

    def _add_row(self, ref, pl, checked=True, removable=False):
        if ref in self._vars:
            return
        if not self._vars:
            for w in self._inner.winfo_children():
                w.destroy()

        title = getattr(pl, "title", None) or f"Плейлист #{ref[1]}"
        cnt = getattr(pl, "track_count", 0) or 0

        var = tk.BooleanVar(value=checked)
        self._vars[ref] = (var, pl)

        row = tk.Frame(self._inner, bg=C["surface"])
        row.pack(fill="x", padx=10, pady=2)
        self._rows[ref] = row

        tk.Checkbutton(row, variable=var, bg=C["surface"], fg=C["text"], activebackground=C["surface"], selectcolor=C["card"], cursor="hand2").pack(side="left")

        label = f"  {title}"
        W_lbl(row, label, color=C["text"]).pack(side="left")

        if cnt:
            W_lbl(row, f"  ({cnt} тр.)", color=C["dim"], size=FONT[1] - 1).pack(side="left")

        if removable:
            W_btn(row, "X", lambda: self._remove_row(ref), C["surface"], size=FONT[1] - 2).pack(side="right", padx=(4, 4))

    def _remove_row(self, ref):
        self._vars.pop(ref, None)
        row = self._rows.pop(ref, None)
        if row is not None:
            row.destroy()
        if not self._vars:
            W_lbl(self._inner, "Нет плейлистов", color=C["dim"]).pack(pady=30)

    def get_selected(self):
        return [(ref, pl) for ref, (var, pl) in self._vars.items() if var.get()]

    def _set_all(self, v):
        for var, _ in self._vars.values():
            var.set(v)