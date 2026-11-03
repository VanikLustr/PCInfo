#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PC Info — наглядные сведения о компьютере в реальном времени."""

from __future__ import annotations

import datetime as dt
import getpass
import json
import os
import platform
import socket
import subprocess
import sys
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, ttk

try:
    import psutil
except ImportError:  # установка предлагается при запуске
    psutil = None

IS_WIN = sys.platform.startswith("win")
FONT = "Segoe UI" if IS_WIN else "DejaVu Sans"
MONO = "Consolas" if IS_WIN else "DejaVu Sans Mono"

BG = "#0f1115"
BG_ALT = "#12151c"
CARD = "#181c25"
CARD_HOVER = "#202631"
ROW_ALT = "#151922"
BORDER = "#272e3b"
TEXT = "#e8ecf4"
MUTED = "#8b95a7"
ACCENT = "#5b8cff"
ACCENT_HOVER = "#749dff"
GREEN = "#3ddc97"
PURPLE = "#b58cff"
ORANGE = "#ff9f6b"
WARN = "#ffb547"
DANGER = "#ff6b6b"

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


# ---------------------------------------------------------------- форматирование

def fmt_bytes(value, digits: int = 1) -> str:
    if value is None:
        return "—"
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "—"
    units = ("Б", "КБ", "МБ", "ГБ", "ТБ", "ПБ")
    index = 0
    while value >= 1024 and index < len(units) - 1:
        value /= 1024
        index += 1
    if index == 0:
        return f"{int(value)} {units[index]}"
    return f"{value:.{digits}f} {units[index]}".replace(".", ",")


def fmt_rate(value) -> str:
    return fmt_bytes(value) + "/с"


def fmt_uptime(seconds) -> str:
    try:
        seconds = max(0, int(seconds))
    except (TypeError, ValueError):
        return "—"
    days, rest = divmod(seconds, 86400)
    hours, rest = divmod(rest, 3600)
    minutes, secs = divmod(rest, 60)
    if days:
        return f"{days} д {hours} ч"
    if hours:
        return f"{hours} ч {minutes} мин"
    if minutes:
        return f"{minutes} мин"
    return f"{secs} с"


def fmt_freq(mhz) -> str:
    try:
        mhz = float(mhz)
    except (TypeError, ValueError):
        return "—"
    if mhz <= 0:
        return "—"
    if mhz >= 1000:
        return f"{mhz / 1000:.2f} ГГц".replace(".", ",")
    return f"{mhz:.0f} МГц"


def fmt_cache(kb) -> str:
    try:
        kb = float(kb)
    except (TypeError, ValueError):
        return "—"
    if kb <= 0:
        return "—"
    if kb >= 1024:
        return f"{kb / 1024:.1f} МБ".replace(".", ",")
    return f"{kb:.0f} КБ"


def fmt_link(mbps) -> str:
    try:
        mbps = float(mbps)
    except (TypeError, ValueError):
        return "—"
    if mbps <= 0:
        return "—"
    if mbps >= 1000:
        return f"{mbps / 1000:g} Гбит/с".replace(".", ",")
    return f"{mbps:g} Мбит/с".replace(".", ",")


def fmt_ts(timestamp) -> str:
    try:
        return dt.datetime.fromtimestamp(timestamp).strftime("%d.%m.%Y, %H:%M")
    except (TypeError, ValueError, OSError):
        return "—"


def fmt_tz() -> str:
    now = dt.datetime.now().astimezone()
    offset = now.utcoffset() or dt.timedelta()
    total = int(offset.total_seconds())
    sign = "+" if total >= 0 else "-"
    hours, minutes = divmod(abs(total) // 60, 60)
    return f"UTC{sign}{hours:02d}:{minutes:02d}"


def short(text, limit: int = 34) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def clean(value) -> str:
    if value is None:
        return "—"
    text = " ".join(str(value).split())
    return text or "—"


def join_parts(*parts, sep: str = " · ") -> str:
    return sep.join(str(p).strip() for p in parts if p not in (None, "", "—")) or "—"


def as_list(value) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def load_color(percent) -> str:
    if percent is None:
        return ACCENT
    if percent >= 90:
        return DANGER
    if percent >= 75:
        return WARN
    return ACCENT


# ---------------------------------------------------------------- система

def cpu_name() -> str:
    if IS_WIN:
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
            ) as key:
                return clean(winreg.QueryValueEx(key, "ProcessorNameString")[0])
        except OSError:
            pass
    return clean(platform.processor() or platform.machine() or "Неизвестно")


def os_name() -> str:
    if IS_WIN:
        try:
            import winreg

            path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path) as key:
                def value(name):
                    try:
                        return winreg.QueryValueEx(key, name)[0]
                    except OSError:
                        return ""

                product = str(value("ProductName") or "Windows")
                version = str(value("DisplayVersion") or value("ReleaseId") or "")
                build = str(value("CurrentBuildNumber") or value("CurrentBuild") or "")
            if build.isdigit() and int(build) >= 22000:
                product = product.replace("Windows 10", "Windows 11")
            tail = " ".join(x for x in (version, f"(сборка {build})" if build else "") if x)
            return f"{product} {tail}".strip()
        except OSError:
            pass
    return clean(f"{platform.system()} {platform.release()}")


CIM_SCRIPT = r"""
$ErrorActionPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1 Name, NumberOfCores, NumberOfLogicalProcessors, MaxClockSpeed, L2CacheSize, L3CacheSize, SocketDesignation
$gpu = @(Get-CimInstance Win32_VideoController | Select-Object Name, DriverVersion, CurrentHorizontalResolution, CurrentVerticalResolution, CurrentRefreshRate, VideoProcessor)
$board = Get-CimInstance Win32_BaseBoard | Select-Object Manufacturer, Product, Version
$bios = Get-CimInstance Win32_BIOS | Select-Object Manufacturer, SMBIOSBIOSVersion, Version
$memory = @(Get-CimInstance Win32_PhysicalMemory | Select-Object BankLabel, DeviceLocator, Capacity, Speed, Manufacturer, PartNumber)
$disks = @(Get-CimInstance Win32_DiskDrive | Select-Object Model, Size, InterfaceType, MediaType)
[PSCustomObject]@{cpu=$cpu; gpu=$gpu; board=$board; bios=$bios; memory=$memory; disks=$disks} | ConvertTo-Json -Depth 4 -Compress
"""


def collect_cim():
    """Аппаратные данные Windows через WMI/PowerShell. None — если недоступно."""
    if not IS_WIN:
        return None
    try:
        process = subprocess.run(
            [
                "powershell", "-NoProfile", "-NonInteractive",
                "-ExecutionPolicy", "Bypass", "-Command", CIM_SCRIPT,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8-sig",
            errors="replace",
            timeout=25,
            creationflags=CREATE_NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    text = (process.stdout or "").strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None


# ---------------------------------------------------------------- виджеты

class MetricCard(tk.Frame):
    """Карточка с крупным значением и необязательной полосой загрузки."""

    def __init__(self, master, title, accent=ACCENT, show_bar=True, bar_height=5):
        super().__init__(master, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        self.accent = accent
        self._percent = None

        head = tk.Frame(self, bg=CARD)
        head.pack(fill="x", padx=16, pady=(13, 0))
        tk.Label(head, text=title, bg=CARD, fg=MUTED,
                 font=(FONT, 9, "bold")).pack(side="left")
        tk.Label(head, text="●", bg=CARD, fg=accent,
                 font=(FONT, 7)).pack(side="right")

        self.value_label = tk.Label(self, text="—", bg=CARD, fg=TEXT,
                                    font=(FONT, 22, "bold"), anchor="w")
        self.value_label.pack(fill="x", padx=16, pady=(4, 0))

        self.sub_label = tk.Label(self, text="", bg=CARD, fg=MUTED,
                                  font=(FONT, 9), anchor="w", width=26)
        self.sub_label.pack(fill="x", padx=16, pady=(1, 10))

        self.bar = None
        if show_bar:
            self.bar = tk.Canvas(self, height=bar_height, bg=CARD,
                                 highlightthickness=0, bd=0)
            self.bar.pack(fill="x", padx=16, pady=(0, 14))
            self.bar.bind("<Configure>", lambda _event: self._draw_bar())

    def set(self, value, sub="", percent=None):
        self.value_label.config(text=value)
        self.sub_label.config(text=short(sub, 42))
        self._percent = percent
        self._draw_bar()

    def _draw_bar(self):
        if self.bar is None:
            return
        self.bar.delete("all")
        width = self.bar.winfo_width()
        height = self.bar.winfo_height()
        if width <= 2:
            return
        self.bar.create_rectangle(0, 0, width, height, fill="#252b37", outline="")
        if self._percent is None:
            return
        filled = max(0.0, min(100.0, float(self._percent))) / 100 * width
        color = load_color(self._percent) if self._percent >= 75 else self.accent
        if filled >= 2:
            self.bar.create_rectangle(0, 0, filled, height, fill=color, outline="")


class Table(tk.Frame):
    """Тёмная таблица с прокруткой и чередованием строк."""

    def __init__(self, master, columns, height=8, style="Info.Treeview"):
        super().__init__(master, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        self.tree = ttk.Treeview(
            self,
            columns=[column[0] for column in columns],
            show="headings",
            height=height,
            style=style,
        )
        for key, title, width, anchor, stretch in columns:
            self.tree.heading(key, text=title, anchor=anchor)
            self.tree.column(key, width=width, minwidth=50, anchor=anchor, stretch=stretch)

        scrollbar = ttk.Scrollbar(
            self, orient="vertical", command=self.tree.yview,
            style="Vertical.TScrollbar",
        )
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.tag_configure("odd", background=CARD)
        self.tree.tag_configure("even", background=ROW_ALT)
        self.tree.tag_configure("section", background=BG_ALT, foreground=ACCENT,
                                font=(FONT, 9, "bold"))
        self._row_index = 0

    def add(self, iid, values, tags=None):
        if tags is None:
            tags = ("even" if self._row_index % 2 else "odd",)
            self._row_index += 1
        self.tree.insert("", "end", iid=iid, values=values, tags=tags)

    def set(self, iid, values):
        if self.tree.exists(iid):
            self.tree.item(iid, values=values)

    def get(self, iid):
        return self.tree.item(iid, "values") if self.tree.exists(iid) else None

    def clear(self):
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        self._row_index = 0


class KeyValueTable(Table):
    """Таблица «параметр — значение» с поддержкой заголовков разделов."""

    def __init__(self, master, height=8, key_width=220, style="Info.Treeview",
                 key_title="Параметр", value_title="Значение"):
        super().__init__(
            master,
            [
                ("param", key_title, key_width, "w", False),
                ("value", value_title, 460, "w", True),
            ],
            height=height,
            style=style,
        )
        self.labels = {}
        self._key_font = tkfont.Font(font=(FONT, 10))

    def add(self, key, label, value="—"):
        self.labels[key] = label
        needed = min(320, self._key_font.measure(label) + 32)
        if needed > self.tree.column("param", "width"):
            self.tree.column("param", width=needed)
        super().add(key, (label, value))

    def set(self, key, value):
        if key in self.labels:
            super().set(key, (self.labels[key], value))

    def add_section(self, key, title):
        super().add(key, (title, ""), tags=("section",))


class CoreBars(tk.Frame):
    """Нагрузка логических потоков с полосами, нарисованными на Canvas."""

    def __init__(self, master, count):
        super().__init__(master, bg=CARD, highlightbackground=BORDER,
                         highlightthickness=1)
        self.values = [0.0] * max(0, count)

        header = tk.Frame(self, bg=BG_ALT)
        header.pack(fill="x")
        tk.Label(header, text="Поток", bg=BG_ALT, fg=MUTED,
                 font=(FONT, 9, "bold")).pack(side="left", padx=(11, 0), pady=8)
        tk.Label(header, text="Загрузка", bg=BG_ALT, fg=MUTED,
                 font=(FONT, 9, "bold")).pack(side="right", padx=(0, 12), pady=8)

        body = tk.Frame(self, bg=CARD)
        body.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(body, bg=CARD, highlightthickness=0, bd=0,
                                yscrollincrement=30)
        scrollbar = ttk.Scrollbar(
            body, orient="vertical", command=self.canvas.yview,
            style="Vertical.TScrollbar",
        )
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.canvas.bind("<Configure>", lambda _event: self._draw())
        self.canvas.bind("<MouseWheel>", self._on_wheel)
        self.canvas.bind("<Enter>", lambda _event: self.canvas.bind_all(
            "<MouseWheel>", self._on_wheel))
        self.canvas.bind("<Leave>", lambda _event: self.canvas.unbind_all(
            "<MouseWheel>"))

    def _on_wheel(self, event):
        self.canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")

    def set(self, values):
        self.values = list(values)
        self._draw()

    def _draw(self):
        canvas = self.canvas
        canvas.delete("all")
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        if width <= 2:
            return
        row = 30
        total = max(height, row * len(self.values))
        canvas.configure(scrollregion=(0, 0, width, total))
        bar_x = 105
        bar_width = max(30, width - bar_x - 78)
        for index, percent in enumerate(self.values):
            top = index * row
            canvas.create_rectangle(
                0, top, width, top + row,
                fill=ROW_ALT if index % 2 else CARD, outline="",
            )
            canvas.create_text(
                14, top + row / 2, text=f"Поток {index + 1}",
                anchor="w", fill=TEXT, font=(FONT, 9),
            )
            canvas.create_rectangle(
                bar_x, top + 11, bar_x + bar_width, top + 19,
                fill="#252b37", outline="",
            )
            filled = bar_width * max(0.0, min(100.0, percent)) / 100
            if filled >= 1:
                color = load_color(percent) if percent >= 75 else ACCENT
                canvas.create_rectangle(
                    bar_x, top + 11, bar_x + filled, top + 19,
                    fill=color, outline="",
                )
            canvas.create_text(
                width - 14, top + row / 2,
                text=f"{percent:.1f}%".replace(".", ","),
                anchor="e", fill=TEXT, font=(MONO, 9),
            )


# ---------------------------------------------------------------- приложение

class PCInfoApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PC Info — сведения о компьютере")
        self.configure(bg=BG)
        self._fit_window()
        self.minsize(940, 620)
        self._setup_styles()

        self._job = None
        self._hw_loading = False
        self._hw_ready = False
        self._hw_data = None
        self._prev_io = None
        self._prev_net = None
        self._prev_io_ts = None
        self._prev_net_ts = None
        self._partitions = {}
        self._interfaces = {}
        self.metrics = {}

        self._host = socket.gethostname()
        self._user = getpass.getuser()
        self._os = os_name()
        self._cpu = cpu_name()
        self._boot = psutil.boot_time()
        self._physical = psutil.cpu_count(logical=False) or 0
        self._logical = psutil.cpu_count(logical=True) or 0
        self._sys_drive = (
            os.environ.get("SystemDrive", "C:") + "\\" if IS_WIN else "/"
        )
        psutil.cpu_percent(interval=None, percpu=True)  # первый замер бесполезен

        self._build_ui()
        self._fill_static()
        self._build_partitions()
        self._build_interfaces()
        self._load_hardware()
        self._refresh_dynamic()
        self._job = self.after(1000, self._tick)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(30, self._dark_titlebar)

    # ------------------------------------------------------------ каркас

    def _dark_titlebar(self):
        if not IS_WIN:
            return
        try:
            import ctypes

            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            enabled = ctypes.c_int(1)
            for attribute in (20, 19):
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, attribute, ctypes.byref(enabled), ctypes.sizeof(enabled))
        except Exception:
            pass

    def _fit_window(self):
        screen_w, screen_h = self.winfo_screenwidth(), self.winfo_screenheight()
        width = min(1420, max(980, int(screen_w * 0.72)))
        height = min(900, max(640, int(screen_h * 0.80)))
        x = (screen_w - width) // 2
        y = max(16, (screen_h - height) // 2 - 20)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _setup_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(".", font=(FONT, 10))
        style.configure("TNotebook", background=BG, borderwidth=0,
                        tabmargins=(0, 0, 0, 0), bordercolor=BG,
                        lightcolor=BG, darkcolor=BG)
        style.configure("TNotebook.Tab", background=BG, foreground=MUTED,
                        borderwidth=0, padding=(17, 8), font=(FONT, 10),
                        lightcolor=BG, darkcolor=BG, bordercolor=BG,
                        focuscolor=BG)
        style.map(
            "TNotebook.Tab",
            background=[("selected", CARD), ("active", CARD_HOVER)],
            foreground=[("selected", TEXT), ("active", TEXT)],
            lightcolor=[("selected", CARD), ("active", CARD_HOVER)],
            darkcolor=[("selected", CARD), ("active", CARD_HOVER)],
            bordercolor=[("selected", BORDER), ("active", BORDER)],
        )

        for name, font in (("Info.Treeview", (FONT, 10)),
                           ("Mono.Treeview", (MONO, 10))):
            style.configure(
                name,
                background=CARD,
                fieldbackground=CARD,
                foreground=TEXT,
                borderwidth=0,
                relief="flat",
                lightcolor=CARD,
                darkcolor=CARD,
                bordercolor=CARD,
                rowheight=30,
                font=font,
            )
            style.map(
                name,
                background=[("selected", "#263451")],
                foreground=[("selected", TEXT)],
            )
            style.configure(
                name + ".Heading",
                background=BG_ALT,
                foreground=MUTED,
                borderwidth=0,
                relief="flat",
                padding=(10, 8),
                font=(FONT, 9, "bold"),
            )
            style.map(name + ".Heading", background=[("active", BG_ALT)])

        style.configure(
            "Vertical.TScrollbar",
            background=CARD_HOVER,
            troughcolor=CARD,
            bordercolor=CARD,
            arrowcolor=MUTED,
            relief="flat",
            width=12,
        )
        style.map("Vertical.TScrollbar", background=[("active", ACCENT)])

    def _button(self, parent, text, command, accent=False):
        background = ACCENT if accent else CARD
        foreground = "#ffffff" if accent else TEXT
        hover = ACCENT_HOVER if accent else CARD_HOVER
        button = tk.Button(
            parent,
            text=text,
            command=command,
            bg=background,
            fg=foreground,
            activebackground=hover,
            activeforeground=foreground,
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=15,
            pady=8,
            font=(FONT, 9, "bold"),
            highlightthickness=1,
            highlightbackground=ACCENT if accent else BORDER,
        )
        button.bind("<Enter>", lambda _event: button.config(bg=hover))
        button.bind("<Leave>", lambda _event: button.config(bg=background))
        return button

    def _build_ui(self):
        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=28, pady=(20, 14))

        titles = tk.Frame(header, bg=BG)
        titles.pack(side="left")
        tk.Label(titles, text="Сведения о компьютере", bg=BG, fg=TEXT,
                 font=(FONT, 21, "bold")).pack(anchor="w")
        tk.Label(titles, text="Все основные параметры системы в реальном времени",
                 bg=BG, fg=MUTED, font=(FONT, 10)).pack(anchor="w", pady=(2, 0))

        actions = tk.Frame(header, bg=BG)
        actions.pack(side="right", anchor="center")
        self._button(actions, "Обновить", self._manual_refresh).pack(
            side="left", padx=(0, 8))
        self._button(actions, "Сохранить отчёт", self._save_report, accent=True).pack(
            side="left")

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=24)
        self._build_overview()
        self._build_cpu_tab()
        self._build_memory_tab()
        self._build_disks_tab()
        self._build_network_tab()
        self._build_hardware_tab()

        status = tk.Frame(self, bg=BG)
        status.pack(fill="x", padx=28, pady=(8, 14))
        self.status_dot = tk.Label(status, text="●", bg=BG, fg=GREEN,
                                   font=(FONT, 8))
        self.status_dot.pack(side="left")
        self.status_label = tk.Label(status, text="Сбор сведений…", bg=BG, fg=MUTED,
                                     font=(FONT, 9))
        self.status_label.pack(side="left", padx=(5, 0))
        tk.Label(
            status,
            text=f"Python {platform.python_version()} · обновление каждую секунду",
            bg=BG,
            fg=MUTED,
            font=(FONT, 9),
        ).pack(side="right")

    @staticmethod
    def _tab_title(parent, text):
        return tk.Label(parent, text=text, bg=BG, fg=MUTED,
                        font=(FONT, 9, "bold"))

    # ------------------------------------------------------------ обзор

    def _build_overview(self):
        tab = tk.Frame(self.notebook, bg=BG)
        self.notebook.add(tab, text="Обзор")

        cards = tk.Frame(tab, bg=BG)
        cards.pack(fill="x", pady=(16, 16))
        for index in range(4):
            cards.columnconfigure(index, weight=1, uniform="card")

        self.card_cpu = MetricCard(cards, "ПРОЦЕССОР", ACCENT)
        self.card_ram = MetricCard(cards, "ПАМЯТЬ", GREEN)
        self.card_disk = MetricCard(cards, "СИСТЕМНЫЙ ДИСК", PURPLE)
        self.card_uptime = MetricCard(cards, "ВРЕМЯ РАБОТЫ", WARN, show_bar=False)
        for index, card in enumerate(
                (self.card_cpu, self.card_ram, self.card_disk, self.card_uptime)):
            card.grid(row=0, column=index, sticky="nsew",
                      padx=(0 if index == 0 else 6, 0))

        self.overview_table = KeyValueTable(tab, height=10)
        self.overview_table.pack(fill="both", expand=True)

    def _fill_static(self):
        vm = psutil.virtual_memory()
        user = f"{os.environ.get('USERDOMAIN', '')}\\{self._user}".strip("\\")
        bits = "64-разрядная" if sys.maxsize > 2 ** 32 else "32-разрядная"
        self.overview_table.add("host", "Имя компьютера", self._host)
        self.overview_table.add("user", "Пользователь", user or self._user)
        self.overview_table.add("os", "Операционная система", self._os)
        self.overview_table.add("arch", "Архитектура",
                                f"{platform.machine()} · {bits}")
        self.overview_table.add("cpu", "Процессор", self._cpu)
        self.overview_table.add("ram", "Оперативная память", fmt_bytes(vm.total))
        self.overview_table.add("uptime", "Время работы", "—")
        self.overview_table.add("boot", "Последняя загрузка", fmt_ts(self._boot))
        self.overview_table.add("tz", "Часовой пояс", fmt_tz())
        self.overview_table.add("python", "Python", platform.python_version())

    # ------------------------------------------------------------ процессор

    def _build_cpu_tab(self):
        tab = tk.Frame(self.notebook, bg=BG)
        self.notebook.add(tab, text="Процессор")
        tab.columnconfigure(0, weight=5)
        tab.columnconfigure(1, weight=6)
        tab.rowconfigure(1, weight=1)

        self._tab_title(tab, "ПРОЦЕССОР").grid(
            row=0, column=0, sticky="w", padx=(2, 0), pady=(18, 6))
        self._tab_title(tab, "ЛОГИЧЕСКИЕ ПОТОКИ").grid(
            row=0, column=1, sticky="w", padx=(20, 0), pady=(18, 6))

        self.cpu_table = KeyValueTable(tab, height=11, key_width=210)
        self.cpu_table.grid(row=1, column=0, sticky="nsew", padx=(0, 8))

        self.core_bars = CoreBars(tab, self._logical or 0)
        self.core_bars.grid(row=1, column=1, sticky="nsew", padx=(8, 0))

        freq = None
        try:
            freq = psutil.cpu_freq()
        except (AttributeError, NotImplementedError):
            pass

        self.cpu_table.add("model", "Модель", self._cpu)
        self.cpu_table.add("socket", "Сокет", "—")
        self.cpu_table.add("cores", "Физические ядра", str(self._physical or "—"))
        self.cpu_table.add("threads", "Логические потоки", str(self._logical or "—"))
        self.cpu_table.add("freq", "Текущая частота", fmt_freq(freq.current if freq else None))
        self.cpu_table.add("freq_max", "Максимальная частота", fmt_freq(freq.max if freq else None))
        self.cpu_table.add("cache2", "Кэш L2", "—")
        self.cpu_table.add("cache3", "Кэш L3", "—")
        self.cpu_table.add("load", "Загрузка", "—")
        self.cpu_table.add("temp", "Температура", "—")
        self.cpu_table.add("procs", "Процессов", "—")

    # ------------------------------------------------------------ память

    def _build_memory_tab(self):
        tab = tk.Frame(self.notebook, bg=BG)
        self.notebook.add(tab, text="Память")

        wrap = tk.Frame(tab, bg=BG)
        wrap.pack(fill="x", pady=(16, 16))
        self.mem_card = MetricCard(wrap, "ОПЕРАТИВНАЯ ПАМЯТЬ", GREEN,
                                   show_bar=True, bar_height=7)
        self.mem_card.pack(fill="x")

        self.mem_table = KeyValueTable(tab, height=9)
        self.mem_table.pack(fill="both", expand=True)
        for key, label in (
            ("total", "Всего"),
            ("used", "Используется"),
            ("free", "Свободно"),
            ("available", "Доступно"),
            ("percent", "Загрузка"),
        ):
            self.mem_table.add(key, label)
        self.mem_table.add_section("swap_section", "Файл подкачки")
        self.mem_table.add("swap_total", "Всего")
        self.mem_table.add("swap_used", "Используется")
        self.mem_table.add("swap_free", "Свободно")

    # ------------------------------------------------------------ диски

    def _build_disks_tab(self):
        tab = tk.Frame(self.notebook, bg=BG)
        self.notebook.add(tab, text="Диски")

        self.disk_table = Table(
            tab,
            [
                ("mount", "Раздел", 170, "w", True),
                ("fs", "ФС", 100, "w", True),
                ("total", "Всего", 130, "e", True),
                ("used", "Занято", 130, "e", True),
                ("free", "Свободно", 130, "e", True),
                ("percent", "Заполнено", 120, "e", True),
            ],
            height=8,
        )
        self.disk_table.pack(fill="both", expand=True, pady=(16, 12))

        cards = tk.Frame(tab, bg=BG)
        cards.pack(fill="x")
        cards.columnconfigure(0, weight=1, uniform="io")
        cards.columnconfigure(1, weight=1, uniform="io")
        self.card_read = MetricCard(cards, "ЧТЕНИЕ", ACCENT, show_bar=False)
        self.card_write = MetricCard(cards, "ЗАПИСЬ", ORANGE, show_bar=False)
        self.card_read.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.card_write.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

    def _build_partitions(self):
        self.disk_table.clear()
        self._partitions = {}
        try:
            partitions = psutil.disk_partitions(all=False)
        except OSError:
            partitions = []

        index = 0
        for part in partitions:
            if not part.fstype or "cdrom" in part.opts.lower():
                continue
            if part.mountpoint in ("", "/snap"):
                continue
            try:
                usage = psutil.disk_usage(part.mountpoint)
            except OSError:
                continue
            iid = f"part{index}"
            self._partitions[iid] = (part.mountpoint, part.fstype)
            self.disk_table.add(
                iid,
                (
                    part.mountpoint,
                    part.fstype,
                    fmt_bytes(usage.total),
                    fmt_bytes(usage.used),
                    fmt_bytes(usage.free),
                    f"{usage.percent:.0f}%",
                ),
            )
            index += 1

        if not index:
            self.disk_table.add(
                "part_none",
                ("Нет доступных разделов", "", "", "", "", ""),
            )

    # ------------------------------------------------------------ сеть

    def _build_network_tab(self):
        tab = tk.Frame(self.notebook, bg=BG)
        self.notebook.add(tab, text="Сеть")

        cards = tk.Frame(tab, bg=BG)
        cards.pack(fill="x", pady=(16, 12))
        cards.columnconfigure(0, weight=1, uniform="net")
        cards.columnconfigure(1, weight=1, uniform="net")
        self.card_down = MetricCard(cards, "ПОЛУЧЕНО", GREEN, show_bar=False)
        self.card_up = MetricCard(cards, "ОТПРАВЛЕНО", ORANGE, show_bar=False)
        self.card_down.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.card_up.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        self.net_table = Table(
            tab,
            [
                ("name", "Интерфейс", 300, "w", True),
                ("ipv4", "IPv4", 120, "w", True),
                ("mac", "MAC-адрес", 150, "w", True),
                ("state", "Статус", 90, "w", True),
                ("link", "Лимит", 95, "w", True),
                ("recv", "Принято", 100, "e", True),
                ("sent", "Отправлено", 110, "e", True),
            ],
            height=8,
        )
        self.net_table.pack(fill="both", expand=True, pady=(0, 2))

    def _build_interfaces(self):
        self.net_table.clear()
        self._interfaces = {}
        try:
            addresses = psutil.net_if_addrs()
            stats = psutil.net_if_stats()
            per_nic = psutil.net_io_counters(pernic=True)
        except OSError:
            return

        index = 0
        for name, addr_list in addresses.items():
            lowered = name.lower()
            if lowered == "lo" or "loopback" in lowered:
                continue
            ipv4 = next(
                (a.address for a in addr_list if a.family == socket.AF_INET), None)
            mac = next(
                (a.address for a in addr_list if a.family == psutil.AF_LINK), None)
            stat = stats.get(name)
            if not ipv4 and not (stat and stat.isup):
                continue
            counters = per_nic.get(name)
            iid = f"net{index}"
            self._interfaces[iid] = name
            self.net_table.add(
                iid,
                (
                    name,
                    ipv4 or "—",
                    mac or "—",
                    "Активен" if stat and stat.isup else "Отключён",
                    fmt_link(stat.speed if stat else 0),
                    fmt_bytes(counters.bytes_recv) if counters else "—",
                    fmt_bytes(counters.bytes_sent) if counters else "—",
                ),
            )
            index += 1

        if not index:
            self.net_table.add(
                "net_none",
                ("Активные интерфейсы не найдены", "", "", "", "", "", ""),
            )

    # ------------------------------------------------------------ оборудование

    def _build_hardware_tab(self):
        tab = tk.Frame(self.notebook, bg=BG)
        self.notebook.add(tab, text="Оборудование")
        self.hw_table = KeyValueTable(tab, height=13)
        self.hw_table.pack(fill="both", expand=True, pady=(16, 2))

    def _load_hardware(self):
        if self._hw_loading:
            return
        self._hw_loading = True
        self._hw_ready = False
        self._hw_data = None
        self.hw_table.clear()
        self.hw_table.add("hw_loading", "Состояние", "Сбор данных о компонентах…")
        threading.Thread(target=self._hw_worker, daemon=True).start()

    def _hw_worker(self):
        self._hw_data = collect_cim()
        self._hw_ready = True

    def _apply_hardware(self, data):
        self._hw_loading = False
        self.hw_table.clear()
        self._hw_key = 0

        def section(title):
            self._hw_key += 1
            self.hw_table.add_section(f"hs{self._hw_key}", title)

        def row(label, value):
            self._hw_key += 1
            self.hw_table.add(f"hr{self._hw_key}", label, value if value else "—")

        data = data or {}
        cim = data if isinstance(data, dict) else {}
        gpus = as_list(cim.get("gpu"))
        board = cim.get("board") or {}
        bios = cim.get("bios") or {}
        memory = as_list(cim.get("memory"))
        disks = as_list(cim.get("disks"))
        cpu = cim.get("cpu") or {}

        if isinstance(cpu, dict):
            self.cpu_table.set("socket", clean(cpu.get("SocketDesignation")))
            self.cpu_table.set("cache2", fmt_cache(cpu.get("L2CacheSize")))
            self.cpu_table.set("cache3", fmt_cache(cpu.get("L3CacheSize")))

        section("Видеокарта")
        real_gpus = [g for g in gpus if isinstance(g, dict) and g.get("Name")]
        if real_gpus:
            for offset, gpu in enumerate(real_gpus, start=1):
                prefix = f" {offset}" if len(real_gpus) > 1 else ""
                row("Модель" + prefix, clean(gpu.get("Name")))
                row("Драйвер" + prefix, clean(gpu.get("DriverVersion")))
                if len(real_gpus) == 1 and gpu.get("VideoProcessor"):
                    row("Видеопроцессор", clean(gpu.get("VideoProcessor")))
        else:
            row("Модель", "Не удалось определить")

        section("Экран")
        row("Разрешение", f"{self.winfo_screenwidth()} × {self.winfo_screenheight()}")
        try:
            scale = round(self.winfo_fpixels("1i") / 96 * 100)
            row("Масштаб интерфейса", f"{scale}%")
        except tk.TclError:
            pass
        refresh_rate = next(
            (g.get("CurrentRefreshRate") for g in real_gpus
             if isinstance(g, dict) and g.get("CurrentRefreshRate")), None)
        if refresh_rate:
            row("Частота обновления", f"{refresh_rate} Гц")

        section("Материнская плата")
        if isinstance(board, dict) and (board.get("Product") or board.get("Manufacturer")):
            row("Производитель", clean(board.get("Manufacturer")))
            row("Модель", clean(board.get("Product")))
            row("Версия", clean(board.get("Version")))
        else:
            row("Плата", "Нет данных")

        section("BIOS")
        if isinstance(bios, dict) and (bios.get("SMBIOSBIOSVersion") or bios.get("Version")):
            row("Производитель", clean(bios.get("Manufacturer")))
            row("Версия", clean(bios.get("SMBIOSBIOSVersion") or bios.get("Version")))
        else:
            row("BIOS", "Нет данных")

        section("Накопители")
        if disks:
            for offset, disk in enumerate(disks, start=1):
                if not isinstance(disk, dict):
                    continue
                value = join_parts(
                    fmt_bytes(disk.get("Size")),
                    clean(disk.get("InterfaceType")),
                )
                row(f"Диск {offset}", f"{clean(disk.get('Model'))} · {value}")
        else:
            row("Накопители", "Нет данных")

        section("Модули памяти")
        if memory:
            for offset, module in enumerate(memory, start=1):
                if not isinstance(module, dict):
                    continue
                label = clean(module.get("DeviceLocator") or module.get("BankLabel")
                              or f"Слот {offset}")
                value = join_parts(
                    fmt_bytes(module.get("Capacity")),
                    f"{module.get('Speed')} МГц" if module.get("Speed") else None,
                    " ".join(x for x in (
                        clean(module.get("Manufacturer")),
                        clean(module.get("PartNumber")),
                    ) if x != "—") or None,
                )
                row(label, value)
        else:
            row("Модули", "Нет данных")

        section("Питание")
        try:
            battery = psutil.sensors_battery()
        except (AttributeError, NotImplementedError):
            battery = None
        if battery:
            row("Заряд", f"{battery.percent:.0f}%")
            row("Питание", "Сеть" if battery.power_plugged else "Батарея")
            left = battery.secsleft
            if left not in (psutil.POWER_TIME_UNLIMITED, psutil.POWER_TIME_UNKNOWN) and left > 0:
                row("Осталось", fmt_uptime(left))
        else:
            row("Батарея", "Не обнаружена")

    # ------------------------------------------------------------ обновление

    def _refresh_dynamic(self):
        if self._hw_loading and self._hw_ready:
            self._apply_hardware(self._hw_data)

        self._update_overview()
        self._update_cpu()
        self._update_memory()
        self._update_disks()
        self._update_network()

    def _update_overview(self):
        boot = self._boot
        self.overview_table.set("uptime", fmt_uptime(time.time() - boot))
        self.card_uptime.set(fmt_uptime(time.time() - boot), f"с {fmt_ts(boot)}")

        try:
            usage = psutil.disk_usage(self._sys_drive)
        except OSError:
            usage = None
        if usage:
            self.card_disk.set(
                f"{usage.percent:.0f}%",
                f"{fmt_bytes(usage.used)} из {fmt_bytes(usage.total)}",
                usage.percent,
            )
        else:
            self.card_disk.set("—", self._sys_drive)

        vm = psutil.virtual_memory()
        self.card_ram.set(
            f"{vm.percent:.0f}%",
            f"{fmt_bytes(vm.used)} из {fmt_bytes(vm.total)}",
            vm.percent,
        )

    def _update_cpu(self):
        try:
            per_core = psutil.cpu_percent(interval=None, percpu=True) or []
        except (AttributeError, OSError):
            per_core = []
        load = sum(per_core) / len(per_core) if per_core else 0.0

        self.cpu_table.set("load", f"{load:.1f}%".replace(".", ","))
        self.card_cpu.set(
            f"{load:.0f}%",
            f"Ядер: {self._physical or '—'} · потоков: {self._logical or '—'}",
            load,
        )
        self.core_bars.set(per_core)

        try:
            freq = psutil.cpu_freq()
        except (AttributeError, NotImplementedError):
            freq = None
        if freq:
            self.cpu_table.set("freq", fmt_freq(freq.current))
            self.cpu_table.set("freq_max", fmt_freq(freq.max))

        try:
            sensors = psutil.sensors_temperatures()
            values = [entry.current for entries in sensors.values()
                      for entry in entries if entry.current is not None]
            self.cpu_table.set(
                "temp", f"{max(values):.0f} °C" if values else "Нет датчика")
        except (AttributeError, NotImplementedError, OSError):
            self.cpu_table.set("temp", "Недоступно")

        try:
            self.cpu_table.set("procs", str(len(psutil.pids())))
        except (AttributeError, OSError):
            self.cpu_table.set("procs", "—")

        self.metrics["cpu"] = f"{load:.1f}%"

    def _update_memory(self):
        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()
        self.mem_card.set(
            f"{vm.percent:.0f}%",
            f"{fmt_bytes(vm.used)} из {fmt_bytes(vm.total)}",
            vm.percent,
        )
        self.mem_table.set("total", fmt_bytes(vm.total))
        self.mem_table.set("used", fmt_bytes(vm.used))
        self.mem_table.set("free", fmt_bytes(vm.free))
        self.mem_table.set("available", fmt_bytes(vm.available))
        self.mem_table.set("percent", f"{vm.percent:.0f}%")
        self.mem_table.set("swap_total", fmt_bytes(swap.total))
        self.mem_table.set("swap_used", fmt_bytes(swap.used))
        self.mem_table.set("swap_free", fmt_bytes(swap.free))
        self.metrics["ram"] = f"{vm.percent:.0f}%"

    def _update_disks(self):
        for iid, (mountpoint, fstype) in self._partitions.items():
            try:
                usage = psutil.disk_usage(mountpoint)
            except OSError:
                continue
            self.disk_table.set(
                iid,
                (
                    mountpoint,
                    fstype,
                    fmt_bytes(usage.total),
                    fmt_bytes(usage.used),
                    fmt_bytes(usage.free),
                    f"{usage.percent:.0f}%",
                ),
            )

        try:
            io = psutil.disk_io_counters()
        except (AttributeError, OSError):
            io = None
        read_rate = write_rate = 0.0
        now = time.monotonic()
        if io and self._prev_io and self._prev_io_ts:
            interval = now - self._prev_io_ts
            if interval > 0:
                read_rate = max(0.0, (io.read_bytes - self._prev_io.read_bytes) / interval)
                write_rate = max(0.0, (io.write_bytes - self._prev_io.write_bytes) / interval)
            self.card_read.set(
                fmt_rate(read_rate), f"Всего: {fmt_bytes(io.read_bytes)}")
            self.card_write.set(
                fmt_rate(write_rate), f"Всего: {fmt_bytes(io.write_bytes)}")
        else:
            self.card_read.set("—", "Нет данных")
            self.card_write.set("—", "Нет данных")
        self._prev_io = io
        self._prev_io_ts = now
        self.metrics["disk_read"] = fmt_rate(read_rate)
        self.metrics["disk_write"] = fmt_rate(write_rate)

    def _update_network(self):
        try:
            total = psutil.net_io_counters()
            per_nic = psutil.net_io_counters(pernic=True)
        except (AttributeError, OSError):
            total = None
            per_nic = {}

        down_rate = up_rate = 0.0
        now = time.monotonic()
        if total and self._prev_net and self._prev_net_ts:
            interval = now - self._prev_net_ts
            if interval > 0:
                down_rate = max(0.0, (total.bytes_recv - self._prev_net.bytes_recv) / interval)
                up_rate = max(0.0, (total.bytes_sent - self._prev_net.bytes_sent) / interval)
            self.card_down.set(
                fmt_rate(down_rate), f"Всего: {fmt_bytes(total.bytes_recv)}")
            self.card_up.set(
                fmt_rate(up_rate), f"Всего: {fmt_bytes(total.bytes_sent)}")
        else:
            self.card_down.set("—", "Нет данных")
            self.card_up.set("—", "Нет данных")
        self._prev_net = total
        self._prev_net_ts = now
        self.metrics["net_down"] = fmt_rate(down_rate)
        self.metrics["net_up"] = fmt_rate(up_rate)

        for iid, name in self._interfaces.items():
            counters = per_nic.get(name)
            current = self.net_table.get(iid)
            if not counters or not current or len(current) < 7:
                continue
            self.net_table.set(
                iid,
                (*current[:5], fmt_bytes(counters.bytes_recv),
                 fmt_bytes(counters.bytes_sent)),
            )

    def _manual_refresh(self):
        self.status_label.config(text="Обновление…", fg=MUTED)
        self._build_partitions()
        self._build_interfaces()
        self._load_hardware()
        self._refresh_dynamic()

    def _tick(self):
        try:
            self._refresh_dynamic()
        except Exception as error:  # цикл не должен умирать из-за одного сбоя
            self.status_label.config(text=f"Ошибка обновления: {error}", fg=DANGER)
            self.status_dot.config(fg=DANGER)
        else:
            self.status_label.config(
                text=f"Обновлено в {dt.datetime.now():%H:%M:%S}", fg=MUTED)
            self.status_dot.config(fg=GREEN)
        self._job = self.after(1000, self._tick)

    # ------------------------------------------------------------ отчёт

    @staticmethod
    def _table_text(table) -> list[str]:
        lines = []
        headings = [
            table.tree.heading(column)["text"] for column in table.tree["columns"]
        ]
        lines.append("  ".join(headings))
        lines.append("-" * 64)
        for iid in table.tree.get_children():
            values = [str(value) for value in table.tree.item(iid, "values")]
            if not any(value.strip() for value in values):
                continue
            if len(values) == 2:
                if not values[1].strip():
                    lines.append(values[0])
                else:
                    lines.append(f"{values[0]:<30} {values[1]}")
            else:
                lines.append(" | ".join(value for value in values if value.strip()))
        return lines

    def _build_report(self) -> str:
        lines = [
            "СВЕДЕНИЯ О КОМПЬЮТЕРЕ",
            f"Сформировано: {dt.datetime.now():%d.%m.%Y %H:%M:%S}",
            "=" * 64,
            "",
        ]
        for title, table in (
            ("СИСТЕМА", self.overview_table),
            ("ПРОЦЕССОР", self.cpu_table),
            ("ПАМЯТЬ", self.mem_table),
            ("ДИСКИ", self.disk_table),
            ("СЕТЬ", self.net_table),
            ("ОБОРУДОВАНИЕ", self.hw_table),
        ):
            lines.append(title)
            lines.append("=" * 64)
            lines.extend(self._table_text(table))
            lines.append("")

        lines.append("ПРОИЗВОДИТЕЛЬНОСТЬ (на момент отчёта)")
        lines.append("-" * 64)
        lines.append(f"Загрузка ЦП:      {self.metrics.get('cpu', '—')}")
        lines.append(f"Занято ОЗУ:       {self.metrics.get('ram', '—')}")
        lines.append(f"Чтение диска:     {self.metrics.get('disk_read', '—')}")
        lines.append(f"Запись диска:     {self.metrics.get('disk_write', '—')}")
        lines.append(f"Скачивание:       {self.metrics.get('net_down', '—')}")
        lines.append(f"Отдача:           {self.metrics.get('net_up', '—')}")
        return "\n".join(lines) + "\n"

    def _save_report(self):
        name = f"pc-info-{dt.datetime.now():%Y-%m-%d_%H-%M}.txt"
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Сохранить отчёт",
            initialfile=name,
            defaultextension=".txt",
            filetypes=[("Текстовый файл", "*.txt"), ("Все файлы", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8-sig") as file:
                file.write(self._build_report())
        except OSError as error:
            messagebox.showerror(
                "PC Info", f"Не удалось сохранить отчёт:\n{error}", parent=self)
            return
        messagebox.showinfo("PC Info", f"Отчёт сохранён:\n{path}", parent=self)

    def _on_close(self):
        if self._job:
            try:
                self.after_cancel(self._job)
            except tk.TclError:
                pass
        self.destroy()


# ---------------------------------------------------------------- запуск

def enable_dpi_awareness():
    """Чёткий шрифт и реальное разрешение экрана на Windows с масштабированием."""
    if not IS_WIN:
        return
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def ensure_psutil() -> bool:
    global psutil
    if psutil is not None:
        return True

    root = tk.Tk()
    root.withdraw()
    try:
        answer = messagebox.askyesno(
            "PC Info",
            "Для работы программы нужен модуль psutil.\n\n"
            "Установить его автоматически?",
            parent=root,
        )
        if not answer:
            messagebox.showinfo(
                "PC Info",
                "Установите модуль вручную командой:\n\npip install psutil",
                parent=root,
            )
            return False
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "psutil"],
                check=True,
                creationflags=CREATE_NO_WINDOW,
            )
        except (OSError, subprocess.SubprocessError) as error:
            messagebox.showerror(
                "PC Info",
                f"Не удалось установить psutil:\n{error}\n\n"
                "Установите вручную: pip install psutil",
                parent=root,
            )
            return False
        os.execv(sys.executable, [sys.executable, *sys.argv])
        return False
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass


def main():
    enable_dpi_awareness()
    if not ensure_psutil():
        return
    app = PCInfoApp()
    if "--selftest" in sys.argv:
        app.after(1500, app.destroy)
    app.mainloop()
    if "--selftest" in sys.argv:
        print("selftest OK")


if __name__ == "__main__":
    main()

