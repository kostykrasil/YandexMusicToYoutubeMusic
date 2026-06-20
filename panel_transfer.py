import os
import time
import threading
import re
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog, simpledialog
from pathlib import Path
from config import C, FONT, FONT_SM, FONT_MONO, LIKED_KIND
from widgets import W_lbl, W_btn, W_accent

class TransferPanel(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=C["card"], padx=20, pady=16)
        self.app = app
        self._missing = []
        self._build()

    def _build(self):
        W_accent(self, C["green"])
        W_lbl(self, "  Перенос", bold=True, size=FONT[1] + 1).pack(anchor="w", pady=(0, 10))

        opt = tk.Frame(self, bg=C["card"])
        opt.pack(fill="x", pady=(0, 10))

        W_lbl(opt, "Пауза между запросами:", color=C["dim"], size=FONT[1] - 1).pack(side="left")
        self.delay_var = tk.DoubleVar(value=0.3)
        ttk.Spinbox(opt, from_=0.1, to=3.0, increment=0.1, textvariable=self.delay_var, width=5, font=FONT_SM).pack(side="left", padx=6)
        W_lbl(opt, "сек  (увеличьте если появляются ошибки)", color=C["dim"], size=FONT[1] - 1).pack(side="left")

        self.start_btn = W_btn(self, "Начать перенос", self._start, C["green"], size=FONT[1] + 2)
        self.start_btn.configure(pady=11)
        self.start_btn.pack(fill="x", pady=(0, 8))

        self.export_btn = W_btn(self, "  Сохранить список треков в .txt", self._export_tracks, C["surface"])
        self.export_btn.pack(fill="x", pady=(0, 8))

        self.import_btn = W_btn(self, "  Перенести треки из .txt в YouTube Music", self._import_from_file, C["surface"])
        self.import_btn.pack(fill="x", pady=(0, 14))

        self.prog_var = tk.DoubleVar(value=0)
        self.prog_lbl_var = tk.StringVar()
        tk.Label(self, textvariable=self.prog_lbl_var, bg=C["card"], fg=C["dim"], font=FONT_SM, anchor="w").pack(fill="x")

        ttk.Progressbar(self, variable=self.prog_var, maximum=100, style="Horizontal.TProgressbar").pack(fill="x", pady=6)

        self.stats_var = tk.StringVar()
        tk.Label(self, textvariable=self.stats_var, bg=C["card"], fg=C["text"], font=FONT_SM, anchor="w").pack(fill="x", pady=(0, 8))

        self.copy_btn = W_btn(self, "  Скопировать список не найденных треков", self._copy_missing, C["surface"])
        self.copy_btn.pack(anchor="w", pady=(0, 6))
        self.copy_btn.configure(state="disabled")

        W_lbl(self, "Лог:", color=C["dim"], size=FONT[1] - 1).pack(anchor="w")

        self.log_box = scrolledtext.ScrolledText(self, height=11, bg=C["surface"], fg=C["text"], font=FONT_MONO, relief="flat", state="disabled", bd=1, highlightthickness=1, highlightbackground=C["border"])
        self.log_box.pack(fill="both", expand=True, pady=(4, 0))

        for tag, color in [("ok", C["green"]), ("err", C["red"]), ("hdr", C["ym"]), ("dim", C["dim"]), ("blue", C["blue"])]:
            self.log_box.tag_configure(tag, foreground=color)

    def _log(self, text, tag=""):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text + "\n", tag)
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def _start(self):
        if not self.app.ym_client:
            messagebox.showerror("Ошибка", "Войдите в Яндекс.Музыку")
            return
        if not self.app.ytm_client:
            messagebox.showerror("Ошибка", "Подключите YouTube Music")
            return

        selected = self.app.pl_panel.get_selected()
        if not selected:
            messagebox.showwarning("Предупреждение", "Выберите хотя бы один плейлист")
            return

        self.start_btn.configure(state="disabled", text="Идёт перенос...")
        self.export_btn.configure(state="disabled")
        self.import_btn.configure(state="disabled")
        self._clear_log()
        self.prog_var.set(0)
        self.stats_var.set("")
        self._missing.clear()
        self.copy_btn.configure(state="disabled")

        delay = self.delay_var.get()
        threading.Thread(target=self._run, args=(selected, delay), daemon=True).start()

    def _run(self, selected, delay):
        total_pl = len(selected)
        found_all = 0
        miss_all = 0

        log = lambda t, tg="": self.app.after(0, lambda: self._log(t, tg))
        prog = lambda v: self.app.after(0, lambda: self.prog_var.set(v))
        plbl = lambda t: self.app.after(0, lambda: self.prog_lbl_var.set(t))
        stats = lambda t: self.app.after(0, lambda: self.stats_var.set(t))

        log(f"Начинаю перенос {total_pl} плейлистов...", "hdr")
        log("-" * 60, "dim")

        for pl_idx, (ref, ym_pl) in enumerate(selected):
            title = getattr(ym_pl, "title", None) or f"Плейлист #{ref[1]}"

            log(f"\n  {title}", "hdr")
            plbl(f"Плейлист {pl_idx + 1}/{total_pl}: загружаю треки...")

            try:
                tracks = self._fetch_ym_tracks(ref)
            except Exception as e:
                log(f"  Ошибка загрузки: {e}", "err")
                continue

            if not tracks:
                log("  Плейлист пуст или недоступен", "err")
                continue

            log(f"  Треков: {len(tracks)}", "dim")

            try:
                ytm_id = self.app.ytm_client.create_playlist(title=title, description="Перенесено из Яндекс.Музыки")
                log(f"  Плейлист создан в YouTube Music", "ok")
            except Exception as e:
                log(f"  Не удалось создать плейлист: {e}", "err")
                continue

            found_ids = []
            miss_pl = []

            for i, (tr_title, tr_artist) in enumerate(tracks):
                query = f"{tr_artist} - {tr_title}".strip(" -") if tr_artist else tr_title
                if not query:
                    continue

                overall = (pl_idx + (i + 1) / len(tracks)) / total_pl * 100
                prog(overall)
                plbl(f"Плейлист {pl_idx + 1}/{total_pl} - Трек {i + 1}/{len(tracks)}")

                try:
                    res = self.app.ytm_client.search(query, filter="songs", limit=2)
                    vid = None
                    if res:
                        vid = res[0].get("videoId")
                    if vid:
                        found_ids.append(vid)
                        found_all += 1
                        log(f"  {query}", "ok")
                    else:
                        miss_pl.append(query)
                        miss_all += 1
                        log(f"  {query}", "err")
                except Exception as e:
                    log(f"  {query}: {e}", "err")
                    miss_pl.append(query)
                    miss_all += 1

                stats(f"Найдено: {found_all}  •  Не найдено: {miss_all}")
                time.sleep(delay)

            if found_ids:
                log(f"  Добавляю {len(found_ids)} треков...", "dim")
                for b in range(0, len(found_ids), 20):
                    batch = found_ids[b:b + 20]
                    try:
                        self.app.ytm_client.add_playlist_items(ytm_id, batch)
                        time.sleep(0.5)
                    except Exception as e:
                        log(f"   Ошибка пакетной загрузки: {e}", "err")

                log(f"   {len(found_ids)}/{len(tracks)} треков добавлено", "ok")

            if miss_pl:
                self._missing.extend(miss_pl)
                log(f"  Не найдено: {len(miss_pl)}", "err")

        prog(100)
        plbl("Перенос завершён!")
        log("\n" + "-" * 60, "dim")
        log(f"\n  ГОТОВО", "hdr")
        log(f"   Перенесено: {found_all} треков", "ok")
        if miss_all:
            log(f"   Не найдено: {miss_all} треков", "err")

        def done():
            self.start_btn.configure(state="normal", text="Начать перенос")
            self.export_btn.configure(state="normal")
            self.import_btn.configure(state="normal")
            stats(f" Готово! Найдено: {found_all}  •  Не найдено: {miss_all}")
            if self._missing:
                self.copy_btn.configure(state="normal")

        self.app.after(0, done)

    def _export_tracks(self):
        if not self.app.ym_client:
            messagebox.showerror("Ошибка", "Войдите в Яндекс.Музыку")
            return

        selected = self.app.pl_panel.get_selected()
        if not selected:
            messagebox.showwarning("Предупреждение", "Выберите хотя бы один плейлист")
            return

        folder = filedialog.askdirectory(title="Куда сохранить списки треков", mustexist=True)
        if not folder:
            return

        self.start_btn.configure(state="disabled")
        self.export_btn.configure(state="disabled", text="Сохраняю...")
        self.import_btn.configure(state="disabled")
        self._clear_log()

        threading.Thread(target=self._run_export, args=(selected, folder), daemon=True).start()

    def _run_export(self, selected, folder):
        log = lambda t, tg="": self.app.after(0, lambda: self._log(t, tg))

        log(f"Сохраняю списки треков в: {folder}", "hdr")
        log("-" * 60, "dim")

        saved = []
        for ref, ym_pl in selected:
            title = getattr(ym_pl, "title", None) or f"Плейлист #{ref[1]}"
            log(f"\n  {title}", "hdr")

            try:
                tracks = self._fetch_ym_tracks(ref)
            except Exception as e:
                log(f"   Ошибка загрузки: {e}", "err")
                continue

            if not tracks:
                log("   Плейлист пуст или недоступен", "err")
                continue

            path = self._unique_path(os.path.join(folder, self._safe_filename(title) + ".txt"))

            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(f"# {title} - {len(tracks)} треков\n\n")
                    for i, (tr_title, tr_artist) in enumerate(tracks, 1):
                        line = f"{tr_artist} - {tr_title}".strip(" -") if tr_artist else tr_title
                        f.write(f"{i}. {line}\n")
                log(f"    Сохранено: {os.path.basename(path)} ({len(tracks)} тр.)", "ok")
                saved.append(path)
            except Exception as e:
                log(f"   Не удалось сохранить файл: {e}", "err")

        log("\n" + "-" * 60, "dim")
        if saved:
            log(f"  Готово, сохранено файлов: {len(saved)}", "hdr")
        else:
            log("  Не удалось сохранить ни одного файла", "err")

        def done():
            self.start_btn.configure(state="normal")
            self.export_btn.configure(state="normal", text="  Сохранить список треков в .txt")
            self.import_btn.configure(state="normal")

        self.app.after(0, done)

    @staticmethod
    def _safe_filename(name):
        name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .")
        return name[:120] or "playlist"

    @staticmethod
    def _unique_path(path):
        if not os.path.exists(path):
            return path
        base, ext = os.path.splitext(path)
        i = 2
        while os.path.exists(f"{base} ({i}){ext}"):
            i += 1
        return f"{base} ({i}){ext}"

    def _import_from_file(self):
        if not self.app.ytm_client:
            messagebox.showerror("Ошибка", "Подключите YouTube Music")
            return

        path = filedialog.askopenfilename(title="Выберите текстовый файл со списком треков", filetypes=[("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")])
        if not path:
            return

        try:
            queries = self._parse_track_file(path)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось прочитать файл:\n{e}")
            return

        if not queries:
            messagebox.showwarning("Предупреждение", "В файле не найдено ни одного трека")
            return

        title = simpledialog.askstring("Название плейлиста", f"Название нового плейлиста в YouTube Music\n(треков в файле: {len(queries)}):", initialvalue=Path(path).stem, parent=self.app)
        if title is None:
            return
        title = title.strip()
        if not title:
            messagebox.showwarning("Предупреждение", "Название не может быть пустым")
            return

        self.start_btn.configure(state="disabled")
        self.export_btn.configure(state="disabled")
        self.import_btn.configure(state="disabled", text=" Переношу...")
        self._clear_log()
        self.prog_var.set(0)
        self.stats_var.set("")
        self._missing.clear()
        self.copy_btn.configure(state="disabled")

        delay = self.delay_var.get()
        threading.Thread(target=self._run_import, args=(title, queries, delay), daemon=True).start()

    @staticmethod
    def _parse_track_file(path):
        text = None
        for enc in ("utf-8-sig", "cp1251"):
            try:
                text = Path(path).read_text(encoding=enc)
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
        if text is None:
            text = Path(path).read_text(encoding="utf-8", errors="replace")

        queries = []
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            line = re.sub(r'^\d+[\.\)]\s*', '', line)
            line = line.lstrip("-").strip()
            if line:
                queries.append(line)
        return queries

    def _run_import(self, title, queries, delay):
        log = lambda t, tg="": self.app.after(0, lambda: self._log(t, tg))
        prog = lambda v: self.app.after(0, lambda: self.prog_var.set(v))
        plbl = lambda t: self.app.after(0, lambda: self.prog_lbl_var.set(t))
        stats = lambda t: self.app.after(0, lambda: self.stats_var.set(t))

        log(f"Импортирую {len(queries)} треков из файла в плейлист «{title}»...", "hdr")
        log("-" * 60, "dim")

        try:
            ytm_id = self.app.ytm_client.create_playlist(title=title, description="Импортировано из текстового файла")
            log("  Плейлист создан в YouTube Music", "ok")
        except Exception as e:
            log(f"  Не удалось создать плейлист: {e}", "err")
            self.app.after(0, self._import_unlock)
            return

        found_ids = []
        found_all = 0
        miss_all = 0

        for i, query in enumerate(queries):
            prog((i + 1) / len(queries) * 100)
            plbl(f"Трек {i + 1}/{len(queries)}")

            try:
                res = self.app.ytm_client.search(query, filter="songs", limit=2)
                vid = res[0].get("videoId") if res else None
                if vid:
                    found_ids.append(vid)
                    found_all += 1
                    log(f"  {query}", "ok")
                else:
                    self._missing.append(query)
                    miss_all += 1
                    log(f"  {query}", "err")
            except Exception as e:
                log(f"  {query}: {e}", "err")
                self._missing.append(query)
                miss_all += 1

            stats(f"Найдено: {found_all}  •  Не найдено: {miss_all}")
            time.sleep(delay)

        if found_ids:
            log(f"  Добавляю {len(found_ids)} треков...", "dim")
            for b in range(0, len(found_ids), 20):
                batch = found_ids[b:b + 20]
                try:
                    self.app.ytm_client.add_playlist_items(ytm_id, batch)
                    time.sleep(0.5)
                except Exception as e:
                    log(f"  Ошибка пакетной загрузки: {e}", "err")
            log(f"    {len(found_ids)}/{len(queries)} треков добавлено", "ok")

        prog(100)
        plbl("Импорт завершён!")
        log("\n" + "-" * 60, "dim")
        log(f"\n  ГОТОВО", "hdr")
        log(f"   Перенесено: {found_all} треков", "ok")
        if miss_all:
            log(f"   Не найдено: {miss_all} треков", "err")

        def done():
            self._import_unlock()
            stats(f" Готово! Найдено: {found_all}  •  Не найдено: {miss_all}")
            if self._missing:
                self.copy_btn.configure(state="normal")

        self.app.after(0, done)

    def _import_unlock(self):
        self.start_btn.configure(state="normal")
        self.export_btn.configure(state="normal")
        self.import_btn.configure(state="normal", text="  Перенести треки из .txt в YouTube Music")

    def _fetch_ym_tracks(self, ref):
        ym = self.app.ym_client
        user_id, kind = ref
        tracks = self._fetch_playlist_tracks(ym, kind, user_id)
        if not tracks and kind == LIKED_KIND and user_id is None:
            tracks = self._fetch_liked_via_likes_api(ym)
        return tracks

    def _fetch_playlist_tracks(self, ym, kind, user_id):
        try:
            pl = ym.users_playlists(kind, user_id=user_id) if user_id is not None else ym.users_playlists(kind)
        except Exception:
            return []

        if isinstance(pl, list):
            pl = pl[0] if pl else None
        if pl is None:
            return []
        return self._extract_playlist_tracks(pl)

    def _extract_playlist_tracks(self, pl):
        ym = self.app.ym_client
        raw = getattr(pl, "tracks", []) or []
        results = []
        need_ids = []

        for item in raw:
            t, a = self._extract_info(item)
            if t:
                results.append((t, a))
            else:
                tid = getattr(item, "id", None)
                if tid:
                    need_ids.append(tid)

        if need_ids:
            for batch_start in range(0, len(need_ids), 50):
                batch = need_ids[batch_start:batch_start + 50]
                try:
                    fetched = ym.tracks(batch)
                    for tr in (fetched or []):
                        t, a = self._extract_info(tr)
                        if t:
                            results.append((t, a))
                except Exception:
                    pass

        return results

    def _fetch_liked_via_likes_api(self, ym):
        try:
            likes = ym.users_likes_tracks()
        except Exception:
            return []

        short_list = getattr(likes, "tracks", None) or []
        ids = []
        for t in short_list:
            tid = getattr(t, "id", None)
            if tid is None:
                continue
            aid = getattr(t, "album_id", None)
            ids.append(f"{tid}:{aid}" if aid else str(tid))

        results = []
        for batch_start in range(0, len(ids), 50):
            batch = ids[batch_start:batch_start + 50]
            try:
                fetched = ym.tracks(batch)
                for tr in (fetched or []):
                    t, a = self._extract_info(tr)
                    if t:
                        results.append((t, a))
            except Exception:
                pass

        return results

    def _extract_info(self, item):
        if hasattr(item, "title") and item.title:
            arts = getattr(item, "artists", []) or []
            artist = ", ".join(getattr(a, "name", "") for a in arts if getattr(a, "name", ""))
            return item.title, artist

        if hasattr(item, "track") and item.track:
            return self._extract_info(item.track)

        if isinstance(item, dict):
            title = item.get("title", "")
            arts = item.get("artists", [])
            if isinstance(arts, list):
                artist = ", ".join((a.get("name", "") if isinstance(a, dict) else str(a)) for a in arts)
            else:
                artist = ""
            return title, artist

        return None, None

    def _copy_missing(self):
        if not self._missing:
            return
        text = "\n".join(self._missing)
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Скопировано", f"Список {len(self._missing)} не найденных треков скопирован в буфер обмена.")