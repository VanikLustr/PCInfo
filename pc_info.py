#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PC Info — наглядные сведения о компьютере в реальном времени."""

from __future__ import annotations

import datetime as dt
import getpass
import importlib.util
import io
import json
import math
import os
import platform
import socket
import struct
import subprocess
import sys
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
import wave
from collections import deque
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

try:
    import psutil
except ImportError:  # установка предлагается при запуске
    psutil = None

IS_WIN = sys.platform.startswith("win")
FONT = "Segoe UI"
MONO = "JetBrains Mono"
FONT_TITLE = "Bahnschrift SemiBold"
PIE_NOTE = "тема сделана специально для webpie))"

THEMES = {
    "dark": {
        "title": "Тёмная",
        "bg": "#0f1115", "bg_alt": "#12151c", "card": "#181c25",
        "card_hover": "#202631", "row_alt": "#151922", "border": "#272e3b",
        "text": "#e8ecf4", "muted": "#8b95a7", "accent": "#5b8cff",
        "accent_hover": "#749dff", "green": "#3ddc97", "purple": "#b58cff",
        "orange": "#ff9f6b", "warn": "#ffb547", "danger": "#ff6b6b",
        "on_accent": "#ffffff", "track": "#252b37", "select": "#263451",
        "radius": 14, "dark_title": True,
    },
    "light": {
        "title": "Светлая",
        "bg": "#eef1f6", "bg_alt": "#e3e8f0", "card": "#ffffff",
        "card_hover": "#f2f5fa", "row_alt": "#f7f9fc", "border": "#d8dee9",
        "text": "#1b2430", "muted": "#6a7688", "accent": "#3d6fe0",
        "accent_hover": "#2f5dcc", "green": "#0f9d6a", "purple": "#7651d3",
        "orange": "#de7a3a", "warn": "#c08100", "danger": "#d64a4a",
        "on_accent": "#ffffff", "track": "#e7ecf4", "select": "#dce8ff",
        "radius": 14, "dark_title": False,
    },
    "amoled": {
        "title": "AMOLED",
        "bg": "#000000", "bg_alt": "#050505", "card": "#0a0b0d",
        "card_hover": "#16181c", "row_alt": "#0d0e11", "border": "#24282f",
        "text": "#f4f7fb", "muted": "#8b929d", "accent": "#58d6ff",
        "accent_hover": "#86e4ff", "green": "#4be0a2", "purple": "#c59bff",
        "orange": "#ff9d6b", "warn": "#ffcc4d", "danger": "#ff6b6b",
        "on_accent": "#001319", "track": "#1b1f25", "select": "#123744",
        "radius": 16, "dark_title": True,
    },
    "pie": {
        "title": "Pie",
        "bg": "#120a03", "bg_alt": "#1a0e04", "card": "#1f1205",
        "card_hover": "#2e1a07", "row_alt": "#241405", "border": "#6e3900",
        "text": "#fff3e3", "muted": "#b07a45", "accent": "#dd7100",
        "accent_hover": "#e88925", "green": "#e89743", "purple": "#8e6133",
        "orange": "#e88925", "warn": "#e88925", "danger": "#ff5e3a",
        "on_accent": "#190c02", "track": "#3b2208", "select": "#6e3900",
        "radius": 0, "dark_title": True,
    },
}
THEME_ORDER = ("dark", "light", "amoled", "pie")
CURRENT_THEME = "dark"

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
ON_ACCENT = "#ffffff"
TRACK = "#252b37"
SELECT_BG = "#263451"
RADIUS = 14


def apply_theme_globals(name: str):
    global CURRENT_THEME, BG, BG_ALT, CARD, CARD_HOVER, ROW_ALT, BORDER
    global TEXT, MUTED, ACCENT, ACCENT_HOVER, GREEN, PURPLE, ORANGE
    global WARN, DANGER, ON_ACCENT, TRACK, SELECT_BG, RADIUS

    theme = THEMES[name]
    CURRENT_THEME = name
    BG = theme["bg"]
    BG_ALT = theme["bg_alt"]
    CARD = theme["card"]
    CARD_HOVER = theme["card_hover"]
    ROW_ALT = theme["row_alt"]
    BORDER = theme["border"]
    TEXT = theme["text"]
    MUTED = theme["muted"]
    ACCENT = theme["accent"]
    ACCENT_HOVER = theme["accent_hover"]
    GREEN = theme["green"]
    PURPLE = theme["purple"]
    ORANGE = theme["orange"]
    WARN = theme["warn"]
    DANGER = theme["danger"]
    ON_ACCENT = theme["on_accent"]
    TRACK = theme["track"]
    SELECT_BG = theme["select"]
    RADIUS = theme["radius"]


def configure_fonts(root):
    global FONT, MONO, FONT_TITLE
    families = set(tkfont.families(root))
    FONT = next(
        (name for name in ("Segoe UI", "Inter", "DejaVu Sans") if name in families),
        "TkDefaultFont",
    )
    MONO = next(
        (name for name in ("JetBrains Mono", "Cascadia Mono", "Consolas",
                           "DejaVu Sans Mono") if name in families),
        "TkFixedFont",
    )
    FONT_TITLE = next(
        (name for name in ("Bahnschrift SemiBold", "Bahnschrift",
                           "Segoe UI Semibold", "Segoe UI") if name in families),
        FONT,
    )


def settings_path() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    return Path(base) / "PCInfo" / "settings.json"


def load_settings() -> dict:
    defaults = {"theme": "dark", "sounds": True}
    try:
        data = json.loads(settings_path().read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return defaults
    theme = data.get("theme")
    if theme in THEMES:
        defaults["theme"] = theme
    defaults["sounds"] = bool(data.get("sounds", True))
    return defaults


def save_settings(theme: str, sounds: bool):
    try:
        path = settings_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"theme": theme, "sounds": bool(sounds)}, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError:
        pass


def find_donut() -> Path | None:
    candidates = [Path(__file__).resolve().parent / "donut.py"]
    for base in (
        Path.home() / "Desktop",
        Path(os.environ.get("USERPROFILE", "") or ".") / "Desktop",
        Path(os.environ.get("OneDrive", "") or ".") / "Desktop",
        Path(os.environ.get("OneDriveCommercial", "") or ".") / "Desktop",
    ):
        candidates.append(base / "donut.py")
    seen = set()
    for path in candidates:
        try:
            key = str(path.resolve()).lower()
        except OSError:
            key = str(path).lower()
        if key in seen:
            continue
        seen.add(key)
        try:
            if path.is_file():
                return path
        except OSError:
            continue
    return None


class SoundBank:
    """Короткие синтезированные сигналы. Кнопки намеренно оставлены без звука."""

    RATE = 44100

    def __init__(self):
        self.enabled = True
        self._cache = {}
        self._keepalive = b""
        self._recipes = {
            "startup": (
                (392.00, 0.00, 0.55, 0.20),
                (523.25, 0.12, 0.55, 0.22),
                (659.25, 0.24, 0.65, 0.20),
                (783.99, 0.36, 0.80, 0.16),
            ),
            "tab": (
                (880.00, 0.000, 0.07, 0.09),
                (1174.66, 0.045, 0.09, 0.07),
            ),
            "donut": (
                (523.25, 0.00, 0.12, 0.12),
                (659.25, 0.09, 0.12, 0.14),
                (783.99, 0.18, 0.12, 0.16),
                (1046.50, 0.27, 0.30, 0.15),
            ),
        }

    def _render(self, name: str) -> bytes:
        notes = self._recipes[name]
        duration = max(start + length for _, start, length, _ in notes) + 0.08
        count = int(self.RATE * duration)
        samples = [0.0] * count
        for frequency, start, length, gain in notes:
            first = int(start * self.RATE)
            size = min(count - first, int(length * self.RATE))
            attack = max(1, int(0.008 * self.RATE))
            for index in range(size):
                t = index / self.RATE
                envelope = min(1.0, index / attack) * math.exp(-3.2 * index / size)
                value = (
                    math.sin(2 * math.pi * frequency * t)
                    + 0.35 * math.sin(4 * math.pi * frequency * t)
                    + 0.12 * math.sin(6 * math.pi * frequency * t)
                )
                samples[first + index] += value * envelope * gain

        frames = bytearray()
        for sample in samples:
            frames += struct.pack(
                "<h", int(max(-1.0, min(1.0, sample)) * 32767))
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(self.RATE)
            wav.writeframes(bytes(frames))
        return buffer.getvalue()

    def play(self, name: str):
        if not self.enabled or not IS_WIN or name not in self._recipes:
            return
        try:
            import winsound
        except ImportError:
            return
        data = self._cache.get(name)
        if data is None:
            data = self._render(name)
            self._cache[name] = data
        self._keepalive = data
        flags = winsound.SND_MEMORY | getattr(winsound, "SND_NODEFAULT", 0x0002)

        def worker():
            try:
                # winsound не поддерживает SND_ASYNC вместе с SND_MEMORY,
                # поэтому играем синхронно, но в отдельном потоке.
                winsound.PlaySound(data, flags)
            except (RuntimeError, OSError):
                pass

        threading.Thread(target=worker, daemon=True).start()


apply_theme_globals("dark")
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

def _hex_rgb(color: str):
    color = color.lstrip("#")
    if len(color) == 3:
        color = "".join(char * 2 for char in color)
    return tuple(int(color[index:index + 2], 16) for index in (0, 2, 4))


def mix_color(first: str, second: str, ratio: float) -> str:
    ratio = max(0.0, min(1.0, ratio))
    one, two = _hex_rgb(first), _hex_rgb(second)
    return "#" + "".join(
        f"{round(a + (b - a) * ratio):02x}" for a, b in zip(one, two))


def _parent_bg(widget) -> str:
    try:
        return widget.cget("bg")
    except tk.TclError:
        return BG


def draw_rounded(canvas, x1, y1, x2, y2, radius, fill,
                 outline="", width=1, tags=()):
    """Прямоугольник со скруглением; при radius=0 — обычный, с острыми углами."""
    radius = max(0, int(radius))
    radius = min(radius, int((x2 - x1) / 2), int((y2 - y1) / 2))
    if radius <= 1:
        return canvas.create_rectangle(
            x1, y1, x2, y2, fill=fill, outline=outline, width=width, tags=tags)
    points = (
        x1 + radius, y1, x2 - radius, y1, x2, y1,
        x2, y1 + radius, x2, y2 - radius, x2, y2,
        x2 - radius, y2, x1 + radius, y2, x1, y2,
        x1, y2 - radius, x1, y1 + radius, x1, y1,
    )
    return canvas.create_polygon(
        points, smooth=True, splinesteps=24, fill=fill,
        outline=outline, width=width, tags=tags)


class RoundedPanel(tk.Canvas):
    """Панель с нарисованными скруглёнными углами и обычным Frame внутри."""

    def __init__(self, master, fill=None, outline=None, radius=None,
                 pad=None, **kwargs):
        kwargs.setdefault("bg", _parent_bg(master))
        kwargs.setdefault("highlightthickness", 0)
        kwargs.setdefault("bd", 0)
        kwargs.setdefault("width", 1)
        super().__init__(master, **kwargs)
        self.fill = fill or CARD
        self.outline = outline if outline is not None else BORDER
        self.radius = RADIUS if radius is None else radius
        self.pad = max(1, round(self.radius * 0.32)) if self.radius else 1
        if pad is not None:
            self.pad = pad
        self.body = tk.Frame(self, bg=self.fill)
        self._body_id = self.create_window(
            self.pad, self.pad, anchor="nw", window=self.body)
        self.bind("<Configure>", self._redraw_panel)

    def _redraw_panel(self, event=None):
        width = event.width if event else self.winfo_width()
        height = event.height if event else self.winfo_height()
        if width < 2 or height < 2:
            return
        self.delete("panel_bg")
        draw_rounded(
            self, 0.5, 0.5, width - 0.5, height - 0.5, self.radius,
            fill=self.fill, outline=self.outline, width=1, tags=("panel_bg",))
        self.coords(self._body_id, self.pad, self.pad)
        self.itemconfigure(
            self._body_id,
            width=max(1, width - self.pad * 2),
            height=max(1, height - self.pad * 2),
        )
        self.tag_lower("panel_bg")


class RoundedButton(tk.Canvas):
    """Кнопка со своим состоянием нажатия: вдавливается и меняет цвет."""

    def __init__(self, master, text, command, accent=False, radius=None,
                 font=None, height=36, padx=16):
        self.text = text
        self.command = command
        self.accent = accent
        self.radius = min(RADIUS, 10) if radius is None else radius
        self.font = font or (FONT, 9, "bold")
        self._state = "normal"
        measure = tkfont.Font(root=master, font=self.font).measure(text)
        super().__init__(
            master,
            bg=_parent_bg(master),
            highlightthickness=0,
            bd=0,
            width=measure + padx * 2,
            height=height,
            cursor="hand2",
        )
        self.bind("<Configure>", lambda _event: self._redraw())
        self.bind("<Enter>", lambda _event: self._set_state("hover"))
        self.bind("<Leave>", lambda _event: self._set_state("normal"))
        self.bind("<ButtonPress-1>", lambda _event: self._set_state("pressed"))
        self.bind("<ButtonRelease-1>", self._release)

    def _palette(self):
        if self.accent:
            normal = (ACCENT, ON_ACCENT, ACCENT)
            hover = (ACCENT_HOVER, ON_ACCENT, ACCENT_HOVER)
            pressed = (mix_color(ACCENT, "#000000", 0.24), ON_ACCENT,
                       mix_color(ACCENT, "#000000", 0.38))
        else:
            normal = (CARD, TEXT, BORDER)
            hover = (CARD_HOVER, TEXT, BORDER)
            pressed = (ACCENT, ON_ACCENT, ACCENT_HOVER)
        return {"normal": normal, "hover": hover, "pressed": pressed}

    def _set_state(self, state):
        if self._state != state:
            self._state = state
            self._redraw()

    def _release(self, event):
        was_pressed = self._state == "pressed"
        inside = (0 <= event.x <= self.winfo_width()
                  and 0 <= event.y <= self.winfo_height())
        self._set_state("hover" if inside else "normal")
        if was_pressed and self.command:
            self.command()

    def _redraw(self):
        width = self.winfo_width()
        height = self.winfo_height()
        if width < 2 or height < 2:
            return
        fill, foreground, outline = self._palette()[self._state]
        inset = 2 if self._state == "pressed" else 0
        self.delete("all")
        draw_rounded(
            self, inset + 0.5, inset + 0.5, width - inset - 0.5,
            height - inset - 0.5, self.radius, fill=fill,
            outline=outline, width=1)
        if self._state == "pressed":
            self.create_line(
                self.radius + inset, inset + 2,
                width - self.radius - inset, inset + 2,
                fill=mix_color(fill, "#ffffff", 0.22), width=1)
        self.create_text(
            width / 2, height / 2 + (1 if self._state == "pressed" else 0),
            text=self.text, fill=foreground, font=self.font)


class SoundToggle(tk.Canvas):
    """Кастомная галочка «Звуки» в стиле текущей темы."""

    def __init__(self, master, value=True, command=None):
        self.text = "Звуки"
        self.font = (FONT, 9, "bold")
        self._on = bool(value)
        self.command = command
        measure = tkfont.Font(root=master, font=self.font).measure(self.text)
        super().__init__(
            master,
            bg=_parent_bg(master),
            highlightthickness=0,
            bd=0,
            width=measure + 34,
            height=36,
            cursor="hand2",
        )
        self.bind("<Configure>", lambda _event: self._redraw())
        self.bind("<Button-1>", lambda _event: self.toggle())

    def toggle(self):
        self.set_value(not self._on, notify=True)

    def set_value(self, value, notify=False):
        self._on = bool(value)
        self._redraw()
        if notify and self.command:
            self.command(self._on)

    def _redraw(self):
        width = self.winfo_width()
        height = self.winfo_height()
        if width < 2:
            return
        self.delete("all")
        box = 16
        radius = 0 if RADIUS == 0 else 4
        left = 1
        top = (height - box) / 2
        draw_rounded(
            self, left, top, left + box, top + box, radius,
            fill=ACCENT if self._on else CARD,
            outline=ACCENT if self._on else BORDER, width=1)
        if self._on:
            self.create_line(
                left + 4, top + 8, left + 7, top + 11.5,
                left + 12, top + 4.5,
                fill=ON_ACCENT, width=2, capstyle="round", joinstyle="round")
        self.create_text(
            left + box + 8, height / 2, text=self.text, anchor="w",
            fill=TEXT if self._on else MUTED, font=self.font)


class HistoryChart(RoundedPanel):
    """Живой график загрузки ЦП и памяти за последние 90 секунд."""

    def __init__(self, master, cpu_values, ram_values):
        super().__init__(master, fill=CARD, height=74, radius=min(RADIUS, 12))
        self.cpu_values = cpu_values
        self.ram_values = ram_values
        self.span = max(2, getattr(cpu_values, "maxlen", 90) or 90)
        self.canvas = tk.Canvas(
            self.body, bg=CARD, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _event: self.refresh())

    def refresh(self):
        canvas = self.canvas
        canvas.delete("all")
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        if width < 20 or height < 20:
            return
        left, right = 10, width - 10
        top, bottom = 18, height - 8
        for percent in (0, 50, 100):
            y = bottom - (bottom - top) * percent / 100
            canvas.create_line(left, y, right, y, fill=BORDER, dash=(2, 4))
        canvas.create_text(
            left, 7, text="ПУЛЬС · ЦП", anchor="w",
            fill=ACCENT, font=(MONO, 8, "bold"))
        canvas.create_text(
            left + 92, 7, text="ОЗУ", anchor="w",
            fill=GREEN, font=(MONO, 8, "bold"))
        canvas.create_text(
            right, 7, text=f"{self.span} с", anchor="e",
            fill=MUTED, font=(MONO, 8))

        step = (right - left) / (self.span - 1)
        for values, color, fill_area in (
                (self.cpu_values, ACCENT, True),
                (self.ram_values, GREEN, False)):
            points = []
            for index, value in enumerate(values):
                x = left + index * step
                y = bottom - (bottom - top) * max(0.0, min(100.0, value)) / 100
                points.extend((x, y))
            if len(points) < 4:
                continue
            if fill_area:
                canvas.create_polygon(
                    *points, right, bottom, left, bottom,
                    fill=mix_color(CARD, ACCENT, 0.10), outline="")
            canvas.create_line(
                *points, fill=color, width=2, smooth=True, splinesteps=12)
            canvas.create_oval(
                points[-2] - 2.5, points[-1] - 2.5,
                points[-2] + 2.5, points[-1] + 2.5,
                fill=color, outline=CARD)


class MetricCard(RoundedPanel):
    """Карточка с крупным значением и необязательной полосой загрузки."""

    def __init__(self, master, title, accent=ACCENT, show_bar=True,
                 bar_height=5, height=128):
        super().__init__(master, fill=CARD, height=height)
        self.accent = accent
        self._percent = None

        head = tk.Frame(self.body, bg=CARD)
        head.pack(fill="x", padx=16, pady=(11, 0))
        tk.Label(head, text=title, bg=CARD, fg=MUTED,
                 font=(MONO, 8, "bold")).pack(side="left")
        tk.Label(head, text="●", bg=CARD, fg=accent,
                 font=(FONT, 7)).pack(side="right")

        self.value_label = tk.Label(
            self.body, text="—", bg=CARD, fg=TEXT,
            font=(MONO, 20, "bold"), anchor="w")
        self.value_label.pack(fill="x", padx=16, pady=(3, 0))

        self.sub_label = tk.Label(
            self.body, text="", bg=CARD, fg=MUTED,
            font=(FONT, 9), anchor="w")
        self.sub_label.pack(fill="x", padx=16, pady=(0, 8))

        self.bar = None
        if show_bar:
            self.bar = tk.Canvas(
                self.body, height=bar_height, bg=CARD,
                highlightthickness=0, bd=0)
            self.bar.pack(fill="x", padx=16, pady=(0, 12))
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
        radius = 0 if RADIUS == 0 else min(4, height / 2)
        draw_rounded(self.bar, 0, 0, width, height, radius, TRACK)
        if self._percent is None:
            return
        filled = max(0.0, min(100.0, float(self._percent))) / 100 * width
        color = load_color(self._percent) if self._percent >= 75 else self.accent
        if filled >= 2:
            draw_rounded(
                self.bar, 0, 0, max(filled, radius * 2), height,
                radius, color)


class Table(RoundedPanel):
    """Таблица с прокруткой, чередованием строк и скруглённой рамкой."""

    def __init__(self, master, columns, height=8, style="Info.Treeview"):
        super().__init__(
            master, fill=CARD, height=height * 30 + 46, radius=min(RADIUS, 10))
        self.tree = ttk.Treeview(
            self.body,
            columns=[column[0] for column in columns],
            show="headings",
            height=height,
            style=style,
        )
        for key, title, width, anchor, stretch in columns:
            self.tree.heading(key, text=title, anchor=anchor)
            self.tree.column(key, width=width, minwidth=50, anchor=anchor,
                             stretch=stretch)

        scrollbar = ttk.Scrollbar(
            self.body, orient="vertical", command=self.tree.yview,
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


class CoreBars(RoundedPanel):
    """Нагрузка логических потоков с полосами, нарисованными на Canvas."""

    def __init__(self, master, count):
        super().__init__(
            master, fill=CARD, height=420, radius=min(RADIUS, 10))
        self.values = [0.0] * max(0, count)

        header = tk.Frame(self.body, bg=BG_ALT)
        header.pack(fill="x")
        tk.Label(header, text="Поток", bg=BG_ALT, fg=MUTED,
                 font=(MONO, 8, "bold")).pack(side="left", padx=(11, 0), pady=8)
        tk.Label(header, text="Загрузка", bg=BG_ALT, fg=MUTED,
                 font=(MONO, 8, "bold")).pack(side="right", padx=(0, 12), pady=8)

        body = tk.Frame(self.body, bg=CARD)
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
        radius = 0 if RADIUS == 0 else 4
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
            draw_rounded(
                canvas, bar_x, top + 11, bar_x + bar_width, top + 19,
                radius, TRACK)
            filled = bar_width * max(0.0, min(100.0, percent)) / 100
            if filled >= 1:
                color = load_color(percent) if percent >= 75 else ACCENT
                draw_rounded(
                    canvas, bar_x, top + 11,
                    bar_x + max(filled, radius * 2), top + 19,
                    radius, color)
            canvas.create_text(
                width - 14, top + row / 2,
                text=f"{percent:.1f}%".replace(".", ","),
                anchor="e", fill=TEXT, font=(MONO, 9),
            )


# ---------------------------------------------------------------- приложение

class PCInfoApp(tk.Tk):
    def __init__(self):
        super().__init__()
        settings = load_settings()
        apply_theme_globals(settings["theme"])
        configure_fonts(self)
        self.sound = SoundBank()
        self.sound.enabled = settings["sounds"]

        self.title("PC Info — сведения о компьютере")
        self.configure(bg=BG)
        self._fit_window()
        self.minsize(1010, 700)
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
        self._cpu_history = deque(maxlen=90)
        self._ram_history = deque(maxlen=90)
        self._title_clicks = 0
        self._title_click_job = None
        self._donut_window = None
        self._donut_job = None
        self._theme_popup = None
        self._tab_ready = False
        self._suppress_tab_sound = True

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
        self._seed_history()
        self._job = self.after(1000, self._tick)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(30, self._dark_titlebar)
        self.after(400, self._enable_tab_sound)
        self.after(650, lambda: self.sound.play("startup"))
        self.bind_all("<Control-Shift-KeyPress-D>", lambda _event: self._open_donut())
        self.bind_all("<Control-KeyPress-t>", lambda _event: self._cycle_theme())

    # ------------------------------------------------------------ каркас

    def _enable_tab_sound(self):
        self._tab_ready = True
        self._suppress_tab_sound = False

    def _seed_history(self):
        for values in (self._cpu_history, self._ram_history):
            if values:
                values.extendleft([values[-1]] * (values.maxlen - len(values)))

    def _on_tab_changed(self, _event=None):
        if getattr(self, "_tab_ready", False) and not self._suppress_tab_sound:
            self.sound.play("tab")

    def _dark_titlebar(self):
        if not IS_WIN:
            return
        try:
            import ctypes

            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            enabled = ctypes.c_int(
                1 if THEMES[CURRENT_THEME]["dark_title"] else 0)
            for attribute in (20, 19):
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, attribute, ctypes.byref(enabled), ctypes.sizeof(enabled))
        except Exception:
            pass

    def _fit_window(self):
        screen_w, screen_h = self.winfo_screenwidth(), self.winfo_screenheight()
        width = min(1420, max(1010, int(screen_w * 0.72)))
        height = min(900, max(700, int(screen_h * 0.80)))
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
                background=[("selected", SELECT_BG)],
                foreground=[("selected", TEXT)],
            )
            style.configure(
                name + ".Heading",
                background=BG_ALT,
                foreground=MUTED,
                borderwidth=0,
                relief="flat",
                padding=(10, 8),
                font=(MONO, 8, "bold"),
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
        return RoundedButton(parent, text, command, accent=accent)

    def _show_theme_menu(self):
        if self._theme_popup is not None:
            self._close_theme_popup()
            return

        popup = tk.Toplevel(self)
        popup.withdraw()
        popup.overrideredirect(True)
        popup.transient(self)
        popup.configure(bg=BORDER)
        frame = tk.Frame(popup, bg=CARD, padx=6, pady=5)
        frame.pack(padx=1, pady=1)

        tk.Label(
            frame, text="ТЕМА", bg=CARD, fg=MUTED,
            font=(MONO, 8, "bold"), anchor="w").pack(
                fill="x", padx=7, pady=(1, 4))

        for name in THEME_ORDER:
            theme = THEMES[name]
            selected = name == CURRENT_THEME
            row = tk.Frame(frame, bg=CARD, cursor="hand2")
            row.pack(fill="x")
            dot = tk.Label(
                row, text="●", bg=CARD, fg=theme["accent"],
                font=(FONT, 8), padx=7, pady=7)
            dot.pack(side="left")
            label = tk.Label(
                row, text=theme["title"], bg=CARD,
                fg=TEXT if selected else MUTED, font=(FONT, 10),
                anchor="w", width=12, pady=5)
            label.pack(side="left", fill="x", expand=True)
            check = tk.Label(
                row, text="✓" if selected else "", bg=CARD, fg=ACCENT,
                font=(FONT, 9, "bold"), width=2, padx=5)
            check.pack(side="right")

            widgets = (row, dot, label, check)

            def paint(color, items=widgets):
                for item in items:
                    item.configure(bg=color)

            for widget in widgets:
                widget.bind("<Enter>", lambda _e, p=paint: p(CARD_HOVER))
                widget.bind("<Leave>", lambda _e, p=paint: p(CARD))
                widget.bind(
                    "<Button-1>",
                    lambda _e, choice=name: self._select_theme(choice))

        popup.update_idletasks()
        width = popup.winfo_reqwidth()
        height = popup.winfo_reqheight()
        x = self.theme_button.winfo_rootx()
        y = self.theme_button.winfo_rooty() + self.theme_button.winfo_height() + 5
        x = max(8, min(x, self.winfo_screenwidth() - width - 8))
        if y + height > self.winfo_screenheight() - 48:
            y = self.theme_button.winfo_rooty() - height - 5
        popup.geometry(f"{width}x{height}+{x}+{y}")
        popup.deiconify()
        popup.lift()
        popup.grab_set()
        self._theme_popup = popup
        try:
            popup.focus_force()
        except tk.TclError:
            pass
        popup.bind("<Escape>", lambda _event: self._close_theme_popup())
        popup.bind("<Button-1>", lambda _event: self._close_theme_popup())

    def _select_theme(self, name):
        self._close_theme_popup()
        self.after(20, self._set_theme, name)

    def _close_theme_popup(self):
        popup = self._theme_popup
        self._theme_popup = None
        if popup is None:
            return
        try:
            popup.grab_release()
        except tk.TclError:
            pass
        try:
            popup.destroy()
        except tk.TclError:
            pass
        try:
            self.focus_force()
        except tk.TclError:
            pass

    def _set_theme(self, name):
        if name not in THEMES or name == CURRENT_THEME:
            return
        apply_theme_globals(name)
        save_settings(CURRENT_THEME, self.sound.enabled)
        self._rebuild_ui()

    def _cycle_theme(self):
        index = THEME_ORDER.index(CURRENT_THEME)
        self._set_theme(THEME_ORDER[(index + 1) % len(THEME_ORDER)])

    def _set_sounds(self, enabled):
        self.sound.enabled = bool(enabled)
        save_settings(CURRENT_THEME, self.sound.enabled)

    def _rebuild_ui(self):
        self._close_theme_popup()
        try:
            index = self.notebook.index(self.notebook.select())
        except (tk.TclError, AttributeError):
            index = 0
        if self._job:
            try:
                self.after_cancel(self._job)
            except tk.TclError:
                pass
            self._job = None
        self._suppress_tab_sound = True
        self._tab_ready = False
        try:
            self.unbind_all("<MouseWheel>")
        except tk.TclError:
            pass
        for child in self.winfo_children():
            if isinstance(child, tk.Toplevel):
                continue
            child.destroy()
        self.configure(bg=BG)
        self._setup_styles()
        self._build_ui()
        self._fill_static()
        self._build_partitions()
        self._build_interfaces()
        if self._hw_ready:
            self._apply_hardware(self._hw_data)
        elif self._hw_loading:
            self.hw_table.add(
                "hw_loading", "Состояние", "Сбор данных о компонентах…")
        self._refresh_dynamic()
        self._seed_history()
        if index:
            try:
                self.notebook.select(index)
            except tk.TclError:
                pass
        self.status_label.config(
            text=f"Тема · {THEMES[CURRENT_THEME]['title']}", fg=MUTED)
        self.status_dot.config(fg=GREEN)
        self._job = self.after(1000, self._tick)
        self.after(30, self._dark_titlebar)
        self.after(350, self._enable_tab_sound)

    def _build_ui(self):
        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=28, pady=(20, 14))

        titles = tk.Frame(header, bg=BG)
        titles.pack(side="left")
        self.header_title = tk.Label(
            titles, text="Сведения о компьютере", bg=BG, fg=TEXT,
            font=(FONT_TITLE, 22, "bold"))
        self.header_title.pack(anchor="w")
        self.header_title.bind("<Button-1>", self._title_click)
        self.header_subtitle = tk.Label(
            titles, text="Все основные параметры системы в реальном времени",
            bg=BG, fg=MUTED, font=(FONT, 10))
        self.header_subtitle.pack(anchor="w", pady=(2, 0))
        self.header_subtitle.bind("<Button-1>", self._title_click)

        actions = tk.Frame(header, bg=BG)
        actions.pack(side="right", anchor="center")
        self.theme_button = RoundedButton(
            actions, f"Тема · {THEMES[CURRENT_THEME]['title']}",
            self._show_theme_menu)
        self.theme_button.pack(side="left", padx=(0, 10))
        self.sound_toggle = SoundToggle(
            actions, value=self.sound.enabled, command=self._set_sounds)
        self.sound_toggle.pack(side="left", padx=(0, 12))
        self._button(actions, "Обновить", self._manual_refresh).pack(
            side="left", padx=(0, 8))
        self._button(actions, "Сохранить отчёт", self._save_report, accent=True).pack(
            side="left")

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=24)
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        self._build_overview()
        self._build_cpu_tab()
        self._build_memory_tab()
        self._build_disks_tab()
        self._build_network_tab()
        self._build_hardware_tab()

        status = tk.Frame(self, bg=BG)
        status.pack(fill="x", padx=28, pady=(8, 4 if CURRENT_THEME == "pie" else 14))
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
            font=(MONO, 9),
        ).pack(side="right")

        if CURRENT_THEME == "pie":
            tk.Label(
                self,
                text=PIE_NOTE,
                bg=BG,
                fg=MUTED,
                font=(MONO, 8),
            ).pack(anchor="center", pady=(0, 9))

    @staticmethod
    def _tab_title(parent, text):
        return tk.Label(parent, text=text, bg=BG, fg=MUTED,
                        font=(MONO, 9, "bold"))

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

        self.history_chart = HistoryChart(
            tab, self._cpu_history, self._ram_history)
        self.history_chart.pack(fill="x", pady=(0, 12))

        self.overview_table = KeyValueTable(tab, height=6)
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
            style="Mono.Treeview",
        )
        self.disk_table.pack(fill="both", expand=True, pady=(16, 12))

        cards = tk.Frame(tab, bg=BG)
        cards.pack(fill="x")
        cards.columnconfigure(0, weight=1, uniform="io")
        cards.columnconfigure(1, weight=1, uniform="io")
        self.card_read = MetricCard(
            cards, "ЧТЕНИЕ", ACCENT, show_bar=False, height=112)
        self.card_write = MetricCard(
            cards, "ЗАПИСЬ", ORANGE, show_bar=False, height=112)
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
        self.card_down = MetricCard(
            cards, "ПОЛУЧЕНО", GREEN, show_bar=False, height=112)
        self.card_up = MetricCard(
            cards, "ОТПРАВЛЕНО", ORANGE, show_bar=False, height=112)
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
            style="Mono.Treeview",
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
        if hasattr(self, "history_chart"):
            self.history_chart.refresh()

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
        self._cpu_history.append(load)

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
        self._ram_history.append(vm.percent)

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

    # ------------------------------------------------------------ пасхалка

    def _title_click(self, _event=None):
        self._title_clicks += 1
        if self._title_click_job:
            try:
                self.after_cancel(self._title_click_job)
            except tk.TclError:
                pass
            self._title_click_job = None
        if self._title_clicks >= 5:
            self._title_clicks = 0
            self._open_donut()
        else:
            self._title_click_job = self.after(2800, self._reset_title_clicks)

    def _reset_title_clicks(self):
        self._title_clicks = 0
        self._title_click_job = None

    def _open_donut(self):
        if self._donut_window is not None:
            try:
                if self._donut_window.winfo_exists():
                    self._donut_window.lift()
                    self._donut_window.focus_force()
                    return
            except tk.TclError:
                pass
            self._donut_window = None

        path = find_donut()
        if path is None:
            messagebox.showinfo(
                "PC Info",
                "donut.py не найден.\nПоложи его на рабочий стол — и пасхалка оживёт.",
                parent=self,
            )
            return

        try:
            spec = importlib.util.spec_from_file_location("pc_info_donut", path)
            if spec is None or spec.loader is None:
                raise ImportError("не удалось загрузить модуль")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            render = module.render
            width = int(getattr(module, "WIDTH", 80))
            height = int(getattr(module, "HEIGHT", 24))
        except Exception as error:
            messagebox.showerror(
                "PC Info", f"Не удалось запустить пасхалку:\n{error}", parent=self)
            return

        window = tk.Toplevel(self)
        window.title("donut.py")
        window.configure(bg="#000000")
        window.resizable(False, False)
        window.transient(self)
        font = tkfont.Font(root=window, family=MONO, size=9)
        text_width = font.measure("M") * width
        text_height = font.metrics("linespace") * height
        win_width = min(self.winfo_screenwidth() - 80, text_width + 44)
        win_height = min(self.winfo_screenheight() - 120, text_height + 78)
        x = self.winfo_rootx() + max(0, (self.winfo_width() - win_width) // 2)
        y = self.winfo_rooty() + max(0, (self.winfo_height() - win_height) // 2)
        window.geometry(f"{win_width}x{win_height}+{x}+{y}")

        label = tk.Label(
            window, text="", bg="#000000", fg="#e88925",
            font=(MONO, 9), justify="left")
        label.pack(padx=14, pady=(12, 0))
        hint = tk.Label(
            window, text="donut.py  ·  клик или Esc — закрыть",
            bg="#000000", fg="#8e6133", font=(MONO, 8))
        hint.pack(side="bottom", pady=(0, 10))

        self._donut_window = window
        self.sound.play("donut")
        angle_a = 0.0
        angle_b = 0.0

        def frame():
            nonlocal angle_a, angle_b
            if not window.winfo_exists():
                return
            try:
                label.config(text="\n".join(render(angle_a, angle_b)))
            except tk.TclError:
                return
            angle_a += 0.04
            angle_b += 0.02
            self._donut_job = window.after(50, frame)

        def close(_event=None):
            if self._donut_job is not None:
                try:
                    window.after_cancel(self._donut_job)
                except tk.TclError:
                    pass
                self._donut_job = None
            try:
                window.destroy()
            except tk.TclError:
                pass
            self._donut_window = None

        window.protocol("WM_DELETE_WINDOW", close)
        window.bind("<Escape>", close)
        window.bind("<Button-1>", close)
        label.bind("<Button-1>", close)
        hint.bind("<Button-1>", close)
        frame()

    def _on_close(self):
        if self._job:
            try:
                self.after_cancel(self._job)
            except tk.TclError:
                pass
        if self._title_click_job:
            try:
                self.after_cancel(self._title_click_job)
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

