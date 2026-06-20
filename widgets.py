import tkinter as tk
from config import C, FONT

def W_lbl(parent, text="", size=None, bold=False, color=None, **kw):
    f = (FONT[0], size or FONT[1], "bold" if bold else "normal")
    return tk.Label(parent, text=text, font=f, bg=parent.cget("bg"), fg=color or C["text"], **kw)

def W_btn(parent, text, cmd, color=None, fg="white", size=None, **kw):
    f = (FONT[0], size or FONT[1], "bold")
    return tk.Button(parent, text=text, command=cmd, bg=color or C["surface"], fg=fg,
                     activebackground=color or C["border"], activeforeground=fg,
                     font=f, relief="flat", bd=0, padx=14, pady=7, cursor="hand2", **kw)

def W_entry(parent, var=None, show=None, **kw):
    return tk.Entry(parent, textvariable=var, show=show, bg=C["surface"], fg=C["text"],
                    insertbackground=C["text"], selectbackground=C["blue"], selectforeground=C["bg"],
                    relief="flat", bd=1, highlightthickness=1, highlightbackground=C["border"],
                    highlightcolor=C["blue"], font=FONT, **kw)

def W_sep(parent, pady=0, color=None):
    tk.Frame(parent, bg=color or C["border"], height=1).pack(fill="x", pady=pady)

def W_accent(parent, color):
    tk.Frame(parent, bg=color, height=3).pack(fill="x", pady=(0, 12))