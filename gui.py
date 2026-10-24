# -*- coding: utf-8 -*-
"""
LookForPassword — графический интерфейс (tkinter).

Положите этот файл рядом с main.py (в корень проекта, где лежит папка backend/)
и запускайте:  python gui.py

Окно одно: главная страница (вход) заменяется страницей аккаунта в том же окне.
Вся работа с данными идёт через функции backend/orm_function.py. Обходные пути
(собственный код вместо готовой функции) остались только для поиска и удаления
поста — причины в комментариях «ПОЧЕМУ» в коде.

Дизайн: ASCII-арт, резкие двойные рамки, потускневшее золото + тёмное серебро.

Текст поста хранится в БД как обычный Markdown. При просмотре он отображается с оформлением,
при вводе нового поста доступны панель форматирования, подсветка синтаксиса и предпросмотр.
Горячие клавиши Ctrl+C/V/X/A/Z/Y и Ctrl+B/I/D/E/K работают в любой раскладке (в т. ч. русской).
"""

import contextlib
import io
import os
import re
import sys
import tkinter as tk
import tkinter.font as tkfont
import webbrowser
from datetime import date

# backend/database.py создаёт 'database.db' относительно ТЕКУЩЕЙ папки.
# Чтобы GUI и main.py всегда работали с одной и той же базой, переходим в папку проекта.
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.getcwd())

from sqlalchemy.exc import IntegrityError
import backend.model as m
import backend.orm_function as orm

# ----------------------------------------------------------------------------
# Палитра: потускневшее золото и тёмное серебро на почти чёрном фоне
# ----------------------------------------------------------------------------
BG = "#0b0b0c"          # фон окна
PANEL = "#121213"       # фон внутри рамок
ENTRY_BG = "#060606"    # фон полей ввода
SILVER_DK = "#565a5f"   # тёмное серебро: рамки, неактивное
SILVER = "#8b9096"      # серебро: обычный текст
SILVER_LT = "#aeb2b7"   # светлое серебро: текст поста
GOLD_DK = "#6e5319"     # глубокая тень золота
GOLD = "#a8802c"        # потускневшее золото: акценты, заголовки рамок
GOLD_HI = "#cc9a35"     # золото поярче: ввод, наведение
ERR = "#b5502f"         # ржавчина: сообщения об ошибках
CODE_BG = "#1b1a17"     # фон кода
BOLD_FG = "#d4d7db"     # жирный текст чуть светлее обычного

# ----------------------------------------------------------------------------
# Параметры из спецификации и модели данных
# ----------------------------------------------------------------------------
FONT_CANDIDATES = ("Cascadia Code", "Cascadia Mono", "Consolas", "DejaVu Sans Mono", "Courier New")
TEXT_FONT_PX = 12            # размер шрифта текста поста: 12 px (отрицательное значение в Tk = пиксели)
# Отступ абзаца по спецификации — 1.25 px. Tk округляет пиксели до целых (получится 1 px).
# Если имелось в виду 1.25 см (как в Word), замените на "1.25c".
PARAGRAPH_INDENT = "1.25"
MAX_LOGIN = 15               # User.login = String(15)
MAX_PASSWORD = 30            # User.password = String(30) (пароль, не хэш)
MAX_TITLE = 50               # Post.title = String(50)

LEFT_COLUMN_COLS = 38        # ширина левой колонки (список постов + CRUD) в символах

# ----------------------------------------------------------------------------
# ASCII-арт
# ----------------------------------------------------------------------------
LOGO_LOCK = "\n".join([
    "   .------.   ",
    "  /  ____  \\  ",
    " |  |    |  | ",
    " |  |    |  | ",
    ".------------.",
    "|▓▓▓▓▓▓▓▓▓▓▓▓|",
    "|▓▓▓▓▓▓▓▓▓▓▓▓|",
    "|▓▓▓▓▓██▓▓▓▓▓|",
    "|▓▓▓▓▓██▓▓▓▓▓|",
    "'------------'",
])
_TITLE_TEXT = "[ L o o k F o r P a s s w o r d ]"
_ROW = ("▄▀" * len(_TITLE_TEXT))[: len(_TITLE_TEXT)]       # декоративная линия той же длины
LOGO_TITLE = "\n".join([_ROW, _TITLE_TEXT, _ROW[::-1]])
NO_SIGNAL = (
    "   ╳ ╳ ╳  NO SIGNAL  ╳ ╳ ╳\n\n"
    "   Выберите пост в списке слева\n"
    "   или создайте новый кнопкой Insert.\n\n"
    "   Текст постов поддерживает Markdown."
)
TOOL_HINT = "Markdown · Ctrl+B/I/D/E/K — оформление · Ctrl+C/V/X/A/Z/Y — буфер"
# теги подсветки синтаксиса в режиме ввода
MD_TAGS = ("md_head", "md_b", "md_i", "md_bi", "md_s", "md_code", "md_link", "md_quote", "md_mark")


# ============================================================================
# Чистые функции (не зависят от Tk — их удобно проверять отдельно)
# ============================================================================
def box_top(cols, title):
    """Верхняя граница рамки: (левая часть, подпись, правая часть).
    Подпись выводится золотом, остальное — серебром, поэтому линия делится на три куска."""
    if not title:
        return "╔" + "═" * (cols - 2) + "╗", "", ""
    label = f"[ {title} ]"[: max(0, cols - 3)]
    left = "╔═"
    right = "═" * max(0, cols - len(left) - len(label) - 1) + "╗"
    return left, label, right


def box_bottom(cols):
    """Нижняя граница рамки."""
    return "╚" + "═" * (cols - 2) + "╝"


def thumb_cells(first, last, track):
    """Какие ячейки дорожки (0..track-1) закрашивает ползунок: полуинтервал [start, end).
    first/last — доли видимой части содержимого, как их отдаёт yscrollcommand."""
    start = int(round(first * track))
    end = int(round(last * track))
    end = min(max(end, start + 1), track)
    start = min(start, end - 1)
    return start, end


def format_date(value):
    """Дата создания поста для вывода: ДД.ММ.ГГГГ."""
    try:
        return value.strftime("%d.%m.%Y")
    except AttributeError:
        return "—"


# ============================================================================
# Markdown: разбор и разметка (чистые функции, не зависят от Tk)
# ============================================================================
# Поддерживается: # заголовки (1–3 уровня), **жирный**, *курсив*, ***жирный курсив***,
# ~~зачёркнутый~~, `код`, ```блоки кода```, > цитаты, - / * / + и 1. списки (с вложенностью),
# - [ ] / - [x] задачи, --- линия, [текст](https://ссылка), экранирование \*.
# Переводы строк сохраняются как есть (удобно для заметок).
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)(?:\s+#+)?\s*$")
QUOTE_RE = re.compile(r"^\s*>\s?(.*)$")
BULLET_RE = re.compile(r"^(\s*)([-*+])\s+(.*)$")
ORDERED_RE = re.compile(r"^(\s*)(\d+)[.)]\s+(.*)$")
TASK_RE = re.compile(r"^\[([ xX])\]\s+(.*)$")
HR_RE = re.compile(r"^\s*([-*_])(?:\s*\1){2,}\s*$")
INLINE_RE = re.compile(
    r"(?P<esc>\\[\\`*_~\[\]()#>+\-.!])"
    r"|(?P<code>`[^`\n]+`)"
    r"|(?P<link>\[(?P<ltext>[^\]\n]+)\]\((?P<lurl>https?://[^)\s]+)\))"
    r"|(?P<bi>\*\*\*(?=\S)(.+?)(?<=\S)\*\*\*)"
    r"|(?P<b>\*\*(?=\S)(.+?)(?<=\S)\*\*|(?<!\w)__(?=\S)(.+?)(?<=\S)__(?!\w))"
    r"|(?P<i>\*(?=[^\s*])(.+?)(?<=[^\s*])\*|(?<!\w)_(?=\S)(.+?)(?<=\S)_(?!\w))"
    r"|(?P<s>~~(?=\S)(.+?)(?<=\S)~~)"
)
_INLINE_KINDS = ("esc", "code", "link", "bi", "b", "i", "s")
_PLAIN_TAGS = ("h1", "h2", "h3", "para", "list0", "list1", "list2", "list3", "bullet",
               "quote", "codeblock", "hr", "code", "strike", "link")
_HIGHLIGHT = {"code": "md_code", "link": "md_link", "bi": "md_bi", "b": "md_b",
              "i": "md_i", "s": "md_s"}


def parse_inline(text, styles=frozenset()):
    """Разбирает оформление внутри строки. Возвращает [(кусок текста, множество стилей)].
    Стили вложенные: в **жирном *курсиве*** у куска будут оба."""
    out = []
    pos = 0
    for mt in INLINE_RE.finditer(text):
        if mt.start() > pos:
            out.append((text[pos:mt.start()], styles))
        raw = mt.group(0)
        kind = next(k for k in _INLINE_KINDS if mt.group(k) is not None)
        if kind == "esc":
            out.append((raw[1:], styles))
        elif kind == "code":
            out.append((raw[1:-1], styles | {"code"}))
        elif kind == "link":
            out.extend(parse_inline(mt.group("ltext"),
                                    styles | {"link", "url:" + mt.group("lurl")}))
        elif kind == "bi":
            out.extend(parse_inline(raw[3:-3], styles | {"bold", "italic"}))
        elif kind == "b":
            out.extend(parse_inline(raw[2:-2], styles | {"bold"}))
        elif kind == "i":
            out.extend(parse_inline(raw[1:-1], styles | {"italic"}))
        else:
            out.extend(parse_inline(raw[2:-2], styles | {"strike"}))
        pos = mt.end()
    if pos < len(text):
        out.append((text[pos:], styles))
    return out


def style_tags(styles):
    """Множество стилей → кортеж имён тегов Text.
    Жирный+курсив — отдельный тег (в Tk у перекрывающихся тегов шрифт не складывается),
    а внутри заголовка жирный/курсив не нужны: заголовок и так жирный."""
    names = sorted(x for x in styles if x.startswith("url:"))
    names += [x for x in _PLAIN_TAGS if x in styles]
    if not any(h in styles for h in ("h1", "h2", "h3")):
        if "bold" in styles and "italic" in styles:
            names.append("bolditalic")
        elif "bold" in styles:
            names.append("bold")
        elif "italic" in styles:
            names.append("italic")
    return tuple(names)


def markdown_to_runs(source):
    """Markdown → список (текст, теги) для вставки в Text подряд.
    Теги вида 'url:https://…' означают ссылку: виджет заменит их на свой кликабельный тег."""
    runs = []

    def inline(text, styles):
        for seg, st in parse_inline(text, frozenset(styles)):
            runs.append((seg, style_tags(st)))

    lines = source.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    in_code = False
    for idx, line in enumerate(lines):
        nl = "\n" if idx < len(lines) - 1 else ""
        if line.strip().startswith("```"):          # строка-ограда блока кода не выводится
            in_code = not in_code
            continue
        if in_code:
            runs.append((line + nl, ("codeblock",)))
            continue
        if HR_RE.match(line):
            runs.append(("─" * 40 + nl, ("hr",)))
            continue
        m = HEADING_RE.match(line)
        if m:
            tag = f"h{min(len(m.group(1)), 3)}"
            inline(m.group(2), {tag})
            if nl:
                runs.append((nl, (tag,)))
            continue
        m = QUOTE_RE.match(line)
        if m:
            runs.append(("│ ", ("quote",)))
            inline(m.group(1), {"quote"})
            if nl:
                runs.append((nl, ("quote",)))
            continue
        m = BULLET_RE.match(line)
        ordered = None if m else ORDERED_RE.match(line)
        if m or ordered:
            found = m or ordered
            level = min(len(found.group(1).expandtabs(4)) // 2, 3)
            body = found.group(3)
            if m:
                marker = "• "
                task = TASK_RE.match(body)
                if task:
                    marker = "[x] " if task.group(1) in "xX" else "[ ] "
                    body = task.group(2)
            else:
                marker = f"{ordered.group(2)}. "
            runs.append((marker, ("bullet", f"list{level}")))
            inline(body, {f"list{level}"})
            if nl:
                runs.append((nl, (f"list{level}",)))
            continue
        inline(line, {"para"})
        if nl:
            runs.append((nl, ("para",)))
    return runs


def highlight_spans(source):
    """Подсветка синтаксиса при вводе: [(тег, строка (с 1), колонка от, колонка до)]."""
    spans = []
    in_code = False
    for n, line in enumerate(source.split("\n"), 1):
        if line.strip().startswith("```"):
            in_code = not in_code
            spans.append(("md_code", n, 0, len(line)))
            continue
        if in_code:
            spans.append(("md_code", n, 0, len(line)))
            continue
        if HEADING_RE.match(line):
            spans.append(("md_head", n, 0, len(line)))
            continue
        if QUOTE_RE.match(line):
            spans.append(("md_quote", n, 0, len(line)))
            continue
        m = BULLET_RE.match(line)
        if m:
            spans.append(("md_mark", n, m.start(2), m.end(2)))
        else:
            m = ORDERED_RE.match(line)
            if m:
                spans.append(("md_mark", n, m.start(2), m.end(2) + 1))
        for mt in INLINE_RE.finditer(line):
            kind = next(k for k in _INLINE_KINDS if mt.group(k) is not None)
            if kind in _HIGHLIGHT:
                spans.append((_HIGHLIGHT[kind], n, mt.start(), mt.end()))
    return spans


# --- преобразования текста для кнопок панели форматирования ---
def toggle_wrap(selected, marker):
    """Обернуть выделенное в marker или снять обёртку, если она уже есть."""
    n = len(marker)
    wrapped = (len(selected) >= 2 * n and selected.startswith(marker)
               and selected.endswith(marker))
    # '*' внутри '**…**' — это жирный, а не курсив: тогда оборачиваем ещё раз (получится ***…***)
    if wrapped and marker == "*" and selected.startswith("**") and not selected.startswith("***"):
        wrapped = False
    return selected[n:-n] if wrapped else marker + selected + marker


def toggle_prefix(lines, prefix):
    """Добавить prefix (например '- ' или '> ') ко всем строкам или снять, если он уже везде."""
    filled = [ln for ln in lines if ln.strip()]
    if not filled:
        return [prefix + ln for ln in lines]
    if all(ln.startswith(prefix) for ln in filled):
        return [ln[len(prefix):] if ln.startswith(prefix) else ln for ln in lines]
    return [prefix + ln if ln.strip() else ln for ln in lines]


def toggle_numbered(lines):
    """Нумерованный список: пронумеровать строки или снять нумерацию."""
    num = re.compile(r"^\d+[.)]\s")
    filled = [ln for ln in lines if ln.strip()]
    if filled and all(num.match(ln) for ln in filled):
        return [num.sub("", ln, count=1) for ln in lines]
    out, counter = [], 1
    for ln in lines:
        if ln.strip() or not filled:
            out.append(f"{counter}. {ln}")
            counter += 1
        else:
            out.append(ln)
    return out


def cycle_heading(line):
    """Заголовок по кругу: обычная строка → # → ## → ### → обычная строка."""
    m = re.match(r"^(#{1,3})\s+(.*)$", line)
    if not m:
        return "# " + line
    level = len(m.group(1))
    return m.group(2) if level >= 3 else "#" * (level + 1) + " " + m.group(2)


# --- горячие клавиши, не зависящие от раскладки ---
# Tk сопоставляет Ctrl+буква с латинской буквой, поэтому при русской раскладке стандартные
# Ctrl+C/V не срабатывают. Определяем клавишу по коду (Windows) или по имени keysym.
HOTKEYS = {"c": "copy", "v": "paste", "x": "cut", "a": "select_all", "z": "undo", "y": "redo",
           "b": "bold", "i": "italic", "d": "strike", "e": "code", "k": "link"}
CYRILLIC_KEYS = {  # клавиша в русской раскладке (ЙЦУКЕН) → латинская буква на той же клавише
    "cyrillic_es": "c", "cyrillic_em": "v", "cyrillic_che": "x", "cyrillic_ef": "a",
    "cyrillic_ya": "z", "cyrillic_en": "y", "cyrillic_i": "b", "cyrillic_sha": "i",
    "cyrillic_ve": "d", "cyrillic_u": "e", "cyrillic_el": "k",
    "с": "c", "м": "v", "ч": "x", "ф": "a", "я": "z", "н": "y", "и": "b", "ш": "i",
    "в": "d", "у": "e", "л": "k",
}


def hotkey_action(keysym, keycode, platform, shift=False):
    """Какое действие вызывает Ctrl+клавиша: 'copy', 'paste', 'bold'… или None."""
    key = None
    if platform == "win32" and 65 <= keycode <= 90:
        key = chr(keycode).lower()                 # код виртуальной клавиши не зависит от раскладки
    else:
        name = str(keysym).lower()
        key = name if len(name) == 1 and name.isascii() and name.isalpha() \
            else CYRILLIC_KEYS.get(name)
    action = HOTKEYS.get(key)
    if action == "undo" and shift:                 # Ctrl+Shift+Z = повтор
        return "redo"
    return action


# ============================================================================
# ASCII-виджеты
# ============================================================================
class AsciiBox(tk.Canvas):
    """Рамка из символов ╔═╗║╚╝ с подписью. Содержимое кладётся в self.inner.
    Рамка пересчитывается под размер холста, поэтому растягивается вместе с окном."""

    def __init__(self, master, font, title="", cols=None, rows=None, **kw):
        self.font = font
        self.cw = font.measure("M")              # ширина символа (шрифт моноширинный)
        self.lh = font.metrics("linespace")      # высота строки
        self.title = title
        # width/height — только «желаемый» минимум; реальный размер задаёт grid
        width = cols * self.cw if cols else 1
        height = rows * self.lh if rows else 1
        super().__init__(master, width=width, height=height, bg=BG,
                         highlightthickness=0, bd=0, **kw)
        self.inner = tk.Frame(self, bg=PANEL)
        self._win = self.create_window(self.cw, self.lh, window=self.inner, anchor="nw")
        self.bind("<Configure>", self._redraw)

    def _redraw(self, event):
        """Перерисовываем рамку при любом изменении размера."""
        self.delete("frame")
        cols = max(4, event.width // self.cw)
        rows = max(3, event.height // self.lh)
        cw, lh, font = self.cw, self.lh, self.font

        left, label, right = box_top(cols, self.title)
        self.create_text(0, 0, text=left, anchor="nw", font=font, fill=SILVER_DK, tags="frame")
        if label:
            self.create_text(len(left) * cw, 0, text=label, anchor="nw", font=font,
                             fill=GOLD, tags="frame")
        self.create_text((len(left) + len(label)) * cw, 0, text=right, anchor="nw",
                         font=font, fill=SILVER_DK, tags="frame")
        self.create_text(0, (rows - 1) * lh, text=box_bottom(cols), anchor="nw",
                         font=font, fill=SILVER_DK, tags="frame")
        side = "\n".join("║" * (rows - 2))
        self.create_text(0, lh, text=side, anchor="nw", font=font, fill=SILVER_DK, tags="frame")
        self.create_text((cols - 1) * cw, lh, text=side, anchor="nw", font=font,
                         fill=SILVER_DK, tags="frame")

        # внутренняя область — ровно между границами
        self.itemconfigure(self._win, width=(cols - 2) * cw, height=(rows - 2) * lh)


class AsciiScrollbar(tk.Canvas):
    """Ползунок из символов: ▲ ░░░███░░ ▼. Подключается как обычный scrollbar:
    widget.config(yscrollcommand=sb.set), command=widget.yview.
    Если вся информация помещается — ползунок не рисуется (место под него остаётся,
    чтобы текст не «прыгал» при появлении/исчезновении)."""

    def __init__(self, master, font, command):
        self.font = font
        self.cw = font.measure("M")
        self.lh = font.metrics("linespace")
        super().__init__(master, width=self.cw + 2, height=1, bg=PANEL,
                         highlightthickness=0, bd=0)
        self.command = command
        self.first, self.last = 0.0, 1.0
        self.bind("<Configure>", lambda e: self._redraw())
        self.bind("<Button-1>", self._click)
        self.bind("<B1-Motion>", self._drag)

    def set(self, first, last):
        """Вызывается виджетом-владельцем при прокрутке/изменении содержимого."""
        self.first, self.last = float(first), float(last)
        self._redraw()

    def _visible(self):
        """Нужен ли ползунок: часть содержимого скрыта."""
        return self.first > 0.0 or self.last < 1.0

    def _track_cells(self):
        """Число ячеек дорожки (без стрелок ▲ и ▼)."""
        return max(1, self.winfo_height() // self.lh - 2)

    def _redraw(self):
        self.delete("all")
        if not self._visible():
            return
        track = self._track_cells()
        start, end = thumb_cells(self.first, self.last, track)
        x = self.winfo_width() // 2
        self.create_text(x, 0, text="▲", anchor="n", font=self.font, fill=GOLD)
        for i in range(track):
            if start <= i < end:
                ch, color = "█", GOLD
            else:
                ch, color = "░", SILVER_DK
            self.create_text(x, (i + 1) * self.lh, text=ch, anchor="n", font=self.font, fill=color)
        self.create_text(x, (track + 1) * self.lh, text="▼", anchor="n", font=self.font, fill=GOLD)

    def _click(self, event):
        """Клик по стрелкам прокручивает на строку, по дорожке — переносит ползунок."""
        if not self._visible():
            return
        if event.y < self.lh:
            self.command("scroll", -1, "units")
        elif event.y >= (self._track_cells() + 1) * self.lh:
            self.command("scroll", 1, "units")
        else:
            self._drag(event)

    def _drag(self, event):
        """Перетаскивание: центр ползунка следует за курсором."""
        if not self._visible():
            return
        track_px = self._track_cells() * self.lh
        size = self.last - self.first
        pos = (event.y - self.lh) / track_px - size / 2
        self.command("moveto", min(max(pos, 0.0), 1.0 - size))


class AsciiButton(tk.Label):
    """Кнопка-надпись, например «[ Insert ]». При наведении цвета инвертируются."""

    def __init__(self, master, text, command, font, fg=GOLD, bg=PANEL, **kw):
        super().__init__(master, text=text, font=font, fg=fg, bg=bg, cursor="hand2", bd=0, **kw)
        self._fg, self._bg = fg, bg
        self.command = command
        self.bind("<Enter>", lambda e: self.config(fg=self._bg, bg=self._fg))
        self.bind("<Leave>", lambda e: self.config(fg=self._fg, bg=self._bg))
        self.bind("<Button-1>", lambda e: self.command())

    def set_text(self, text):
        self.config(text=text)


def make_entry(parent, font, var, max_len, bg, show="", width=20):
    """Поле ввода в ASCII-скобках: [ ______ ]. Возвращает (рамка, Entry).
    Длина ввода ограничена max_len — столько позволяет поле в базе данных."""
    frame = tk.Frame(parent, bg=bg)
    tk.Label(frame, text="[", font=font, fg=GOLD, bg=bg).pack(side="left")
    tk.Label(frame, text="]", font=font, fg=GOLD, bg=bg).pack(side="right")
    limit = frame.register(lambda proposed, n=max_len: len(proposed) <= n)
    entry = tk.Entry(frame, textvariable=var, font=font, fg=GOLD_HI, bg=ENTRY_BG,
                     insertbackground=GOLD_HI, selectbackground=GOLD_DK, selectforeground=GOLD_HI,
                     relief="flat", bd=0, highlightthickness=0, show=show, width=width,
                     validate="key", validatecommand=(limit, "%P"))
    entry.pack(side="left", fill="x", expand=True, padx=3, ipady=2)
    entry.max_len = max_len      # нужен вставке из буфера, чтобы не превысить длину поля
    return frame, entry


# ----------------------------------------------------------------------------
# Буфер обмена и горячие клавиши (работают в любой раскладке)
# ----------------------------------------------------------------------------
def _is_secret(widget):
    """Поле пароля (show="*"): копировать и вырезать из него нельзя."""
    return isinstance(widget, tk.Entry) and str(widget.cget("show")) != ""


def _is_editable(widget):
    return str(widget.cget("state")) == "normal"


def _selected_text(widget):
    """Выделенный текст в Entry или Text ('' если ничего не выделено)."""
    try:
        if isinstance(widget, tk.Entry):
            if not widget.selection_present():
                return ""
            return widget.get()[widget.index("sel.first"):widget.index("sel.last")]
        return widget.get("sel.first", "sel.last")
    except tk.TclError:
        return ""


def clip_copy(widget):
    text = _selected_text(widget)
    if text and not _is_secret(widget):
        widget.clipboard_clear()
        widget.clipboard_append(text)


def clip_cut(widget):
    if _is_secret(widget) or not _is_editable(widget) or not _selected_text(widget):
        clip_copy(widget)       # в режиме чтения «вырезать» = «копировать»
        return
    clip_copy(widget)
    widget.delete("sel.first", "sel.last")
    widget.event_generate("<<TextEdited>>")


def clip_paste(widget):
    if not _is_editable(widget):
        return
    try:
        data = widget.clipboard_get()
    except tk.TclError:         # буфер пуст или там не текст
        return
    data = data.replace("\r\n", "\n").replace("\r", "\n")
    if isinstance(widget, tk.Entry):
        data = data.replace("\n", " ")        # в однострочное поле — одной строкой
        if widget.selection_present():
            widget.delete("sel.first", "sel.last")
        limit = getattr(widget, "max_len", None)
        if limit is not None:
            data = data[:max(0, limit - len(widget.get()))]
        widget.insert("insert", data)
    else:
        try:
            widget.delete("sel.first", "sel.last")
        except tk.TclError:     # выделения нет
            pass
        widget.insert("insert", data)
        widget.see("insert")
    widget.event_generate("<<TextEdited>>")


def clip_select_all(widget):
    if isinstance(widget, tk.Entry):
        widget.selection_range(0, "end")
        widget.icursor("end")
    else:
        widget.tag_add("sel", "1.0", "end-1c")


def clip_undo(widget):
    try:
        widget.edit_undo()
        widget.event_generate("<<TextEdited>>")
    except (tk.TclError, AttributeError):       # нечего отменять / у Entry нет истории
        pass


def clip_redo(widget):
    try:
        widget.edit_redo()
        widget.event_generate("<<TextEdited>>")
    except (tk.TclError, AttributeError):
        pass


_CLIPBOARD_ACTIONS = {"copy": clip_copy, "cut": clip_cut, "paste": clip_paste,
                      "select_all": clip_select_all, "undo": clip_undo, "redo": clip_redo}


def bind_hotkeys(widget, extra=None):
    """Подключает горячие клавиши к Entry/Text. extra — {действие: функция} для оформления
    Markdown (Ctrl+B и т. д.). Обработанное сочетание прерывается ("break"), чтобы стандартные
    привязки Tk не выполнили то же действие второй раз (при латинской раскладке)."""
    def on_key(event):
        action = hotkey_action(event.keysym, event.keycode, sys.platform, bool(event.state & 1))
        if action is None:
            return None
        if extra and action in extra:
            extra[action]()
            return "break"
        if action in _CLIPBOARD_ACTIONS:
            _CLIPBOARD_ACTIONS[action](widget)
            return "break"
        return None

    widget.bind("<Control-KeyPress>", on_key)
    if sys.platform == "darwin":
        widget.bind("<Command-KeyPress>", on_key)
    # без фокуса сочетания не придут: Text в режиме чтения сам фокус по клику не берёт
    widget.bind("<Button-1>", lambda e: widget.focus_set(), add="+")


# ============================================================================
# Главная страница: вход и создание аккаунта
# ============================================================================
class LoginPage(tk.Frame):
    SIZE = (400, 560)    # окно входа: фиксированный размер

    def __init__(self, app):
        super().__init__(app.root, bg=BG)
        self.app = app
        font, small = app.font, app.font_small
        self.login_var = tk.StringVar()
        self.pass_var = tk.StringVar()

        # --- логотип ---
        tk.Label(self, text=LOGO_LOCK, font=font, fg=GOLD, bg=BG, justify="center").pack(pady=(22, 6))
        tk.Label(self, text=LOGO_TITLE, font=font, fg=SILVER, bg=BG, justify="center").pack(pady=(0, 18))

        # --- поля Login и Password ---
        for caption, var, show, attr in (("> Login", self.login_var, "", "login_entry"),
                                         ("> Password", self.pass_var, "*", "pass_entry")):
            tk.Label(self, text=caption, font=font, fg=SILVER, bg=BG, anchor="w").pack(fill="x", padx=42)
            limit = MAX_LOGIN if attr == "login_entry" else MAX_PASSWORD
            frame, entry = make_entry(self, font, var, limit, BG, show=show, width=26)
            frame.pack(fill="x", padx=42, pady=(2, 10))
            entry.bind("<Return>", lambda e: self._submit())
            bind_hotkeys(entry)
            setattr(self, attr, entry)

        # --- маленькая кнопка «Create account» (под Password, как в схеме) ---
        AsciiButton(self, "[ Create account ]", self._create, small, fg=SILVER, bg=BG).pack(pady=(0, 14))

        # --- большая кнопка «Подтвердить» ---
        big = "╔════════════════╗\n║  Подтвердить   ║\n╚════════════════╝"
        AsciiButton(self, big, self._submit, font, fg=GOLD, bg=BG, justify="center").pack()

        # --- строка сообщений (место зарезервировано, чтобы окно не менялось) ---
        self.msg = tk.Label(self, text="", font=small, bg=BG, fg=SILVER, wraplength=340, height=2)
        self.msg.pack(pady=(14, 0))

        self.login_entry.focus_set()

    def _message(self, text, kind="info"):
        """Показать сообщение: err — ржавчина, ok — золото, info — серебро."""
        color = {"err": ERR, "ok": GOLD_HI}.get(kind, SILVER)
        self.msg.config(text=text, fg=color)

    def _submit(self):
        """«Подтвердить»: проверяем логин/пароль через orm.comparison."""
        login = self.login_var.get().strip()
        password = self.pass_var.get()
        if not login or not password:
            self._message("[!] Введите логин и пароль", "err")
            return
        session = orm.session_orm()
        try:
            # orm.comparison печатает результат в консоль — глушим вывод
            with contextlib.redirect_stdout(io.StringIO()):
                ok = orm.comparison(session, login, password)
        except Exception as exc:    # ошибка БД не должна ронять окно
            session.close()
            self._message(f"[!] Ошибка базы данных: {exc.__class__.__name__}", "err")
            return
        if ok is not True:
            session.close()
            self._message("[!] Данные не корректные", "err")
            return
        self.app.show_account(session, login)

    def _create(self):
        """«Create account»: создаём аккаунт из введённых Login и Password."""
        login = self.login_var.get().strip()
        password = self.pass_var.get()
        if not login or not password:
            self._message("[!] Введите логин и пароль для нового аккаунта", "err")
            return
        try:
            with orm.session_orm() as session:
                # no_duplicate сама проверяет логин: если он занят — печатает сообщение и закрывает
                # сессию, если свободен — добавляет пользователя в сессию. Возвращаемого значения
                # у неё нет, поэтому факт создания определяем по сессии: появился ли в ней новый User.
                with contextlib.redirect_stdout(io.StringIO()):
                    orm.no_duplicate(session, login, password)
                if not any(isinstance(o, m.User) for o in session.new):
                    self._message("[!] Такой логин уже существует", "err")
                    return
                session.commit()   # no_duplicate только добавляет запись, фиксируем сами
        except IntegrityError:     # запасная защита: UNIQUE(login) в БД (например, гонка двух окон)
            self._message("[!] Такой логин уже существует", "err")
            return
        except Exception as exc:
            self._message(f"[!] Ошибка базы данных: {exc.__class__.__name__}", "err")
            return
        self.pass_var.set("")
        self._message("[+] Аккаунт создан. Нажмите «Подтвердить» для входа", "ok")


# ============================================================================
# Вторая страница: аккаунт пользователя
# ============================================================================
class AccountPage(tk.Frame):
    SIZE = (1000, 660)

    def __init__(self, app, session, login):
        super().__init__(app.root, bg=BG)
        self.app = app
        self.session = session       # одна сессия на всё время работы в аккаунте (как в main.py)
        self.login = login

        self.posts = []              # все посты пользователя: dict(id, title, text, date)
        self.visible = []            # посты, показанные в списке (после поиска)
        self.current_id = None       # id открытого поста
        self.mode = "view"           # "view" — просмотр, "new" — ввод нового поста
        self._armed_id = None        # пост, для которого нажали Delete (ждём подтверждения)
        self._armed_job = None       # таймер сброса подтверждения

        self.previewing = False      # в режиме ввода показан предпросмотр Markdown
        self._draft = ""             # исходный текст, пока открыт предпросмотр
        self._links = {}             # url → имя тега ссылки в Text
        self._hl_job = None          # отложенная подсветка синтаксиса

        self.search_var = tk.StringVar()
        self.title_var = tk.StringVar()
        self._build()
        self.reload()

    # ------------------------------------------------------------------ сборка
    def _build(self):
        font, small = self.app.font, self.app.font_small
        cw = font.measure("M")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- верхний фрейм: login пользователя (+ место под будущие настройки аккаунта) ---
        top = AsciiBox(self, font, title="Account", rows=4)
        top.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=(8, 4))
        top.inner.grid_columnconfigure(1, weight=1)
        tk.Label(top.inner, text=f" Operator ▸ {self.login}", font=self.app.font_bold,
                 fg=GOLD_HI, bg=PANEL).grid(row=0, column=0, sticky="w")
        tk.Label(top.inner, text="░▒▓█ sys.online █▓▒░", font=small, fg=SILVER_DK,
                 bg=PANEL).grid(row=0, column=1)
        AsciiButton(top.inner, "[ Logout ]", self.app.logout, font, fg=SILVER, bg=PANEL
                    ).grid(row=0, column=2, sticky="e", padx=(0, 4))

        # --- левая колонка: список постов + CRUD ---
        left = tk.Frame(self, bg=BG, width=LEFT_COLUMN_COLS * cw)
        left.grid(row=1, column=0, sticky="ns", padx=(8, 4), pady=4)
        left.grid_propagate(False)       # ширина колонки задана жёстко
        left.grid_rowconfigure(0, weight=1)
        left.grid_columnconfigure(0, weight=1)

        posts_box = AsciiBox(left, font, title="Posts")
        posts_box.grid(row=0, column=0, sticky="nsew")
        posts_box.inner.grid_rowconfigure(0, weight=1)
        posts_box.inner.grid_columnconfigure(0, weight=1)
        self.listbox = tk.Listbox(
            posts_box.inner, font=font, bg=PANEL, fg=SILVER, bd=0, highlightthickness=0,
            selectbackground=GOLD, selectforeground=BG, activestyle="none",
            exportselection=False, selectmode="browse")
        self.listbox.grid(row=0, column=0, sticky="nsew", padx=(4, 0))
        list_sb = AsciiScrollbar(posts_box.inner, font, self.listbox.yview)
        list_sb.grid(row=0, column=1, sticky="ns")         # внутри фрейма, справа
        self.listbox.config(yscrollcommand=list_sb.set)    # сам скрывается, когда не нужен
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        crud = AsciiBox(left, font, title="CRUD", rows=9)
        crud.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        ci = crud.inner
        ci.grid_columnconfigure(0, weight=1)
        tk.Label(ci, text=" Search", font=small, fg=SILVER, bg=PANEL, anchor="w"
                 ).grid(row=0, column=0, sticky="ew", pady=(2, 0))
        frame, search_entry = make_entry(ci, font, self.search_var, MAX_TITLE, PANEL)
        frame.grid(row=1, column=0, sticky="ew", padx=4)
        search_entry.bind("<Return>", lambda e: self._on_search())
        bind_hotkeys(search_entry)
        buttons = tk.Frame(ci, bg=PANEL)
        buttons.grid(row=2, column=0, pady=(8, 0))
        self.search_btn = AsciiButton(buttons, "[ Search ]", self._on_search, font)
        self.insert_btn = AsciiButton(buttons, "[ Insert ]", self._on_insert, font)
        self.delete_btn = AsciiButton(buttons, "[ Delete ]", self._on_delete, font)
        for btn in (self.search_btn, self.insert_btn, self.delete_btn):
            btn.pack(side="left", padx=2)
        self.crud_msg = tk.Label(ci, text="", font=small, fg=SILVER, bg=PANEL, anchor="nw",
                                 justify="left", wraplength=(LEFT_COLUMN_COLS - 6) * cw)
        self.crud_msg.grid(row=3, column=0, sticky="nsew", padx=6, pady=(6, 0))

        # --- правая колонка: Title / Text / Date ---
        right = tk.Frame(self, bg=BG)
        right.grid(row=1, column=1, sticky="nsew", padx=(4, 8), pady=4)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        # Title — отдельный фрейм фиксированной высоты, от других компонентов не зависит
        title_box = AsciiBox(right, font, title="Title", rows=4)
        title_box.grid(row=0, column=0, sticky="ew")
        self.title_entry = tk.Entry(
            title_box.inner, textvariable=self.title_var, font=self.app.font_bold, fg=GOLD_HI,
            bg=ENTRY_BG, readonlybackground=PANEL, insertbackground=GOLD_HI,
            selectbackground=GOLD_DK, selectforeground=GOLD_HI, relief="flat", bd=0,
            highlightthickness=0, state="readonly", validate="key",
            validatecommand=(self.register(lambda p: len(p) <= MAX_TITLE), "%P"))
        self.title_entry.pack(fill="x", padx=6, pady=(2, 0))
        self.title_entry.max_len = MAX_TITLE
        bind_hotkeys(self.title_entry)

        # Text — содержимое поста (Markdown), панель форматирования и ползунок внутри фрейма
        text_box = AsciiBox(right, font, title="Text")
        text_box.grid(row=1, column=0, sticky="nsew", pady=6)
        text_box.inner.grid_rowconfigure(1, weight=1)
        text_box.inner.grid_columnconfigure(0, weight=1)

        # панель форматирования видна только при вводе нового поста
        self.toolbar = tk.Frame(text_box.inner, bg=PANEL)
        self.toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=4, pady=(2, 0))
        self._build_toolbar(small)
        self.toolbar.grid_remove()

        self.text = tk.Text(
            text_box.inner, font=self.app.text_font, wrap="word", bg=PANEL, fg=SILVER_LT,
            insertbackground=GOLD_HI, selectbackground=GOLD_DK, selectforeground=GOLD_HI,
            bd=0, highlightthickness=0, padx=8, pady=6, cursor="arrow", state="disabled",
            undo=True, maxundo=-1, autoseparators=True)
        self.text.grid(row=1, column=0, sticky="nsew")
        text_sb = AsciiScrollbar(text_box.inner, font, self.text.yview)
        text_sb.grid(row=1, column=1, sticky="ns")
        self.text.config(yscrollcommand=text_sb.set)
        self._configure_text_tags()
        # Ctrl+C/V/X/A/Z/Y и Ctrl+B/I/D/E/K (оформление действует только при вводе)
        bind_hotkeys(self.text, extra={
            "bold": lambda: self._fmt("bold"), "italic": lambda: self._fmt("italic"),
            "strike": lambda: self._fmt("strike"), "code": lambda: self._fmt("code"),
            "link": lambda: self._fmt("link")})
        self.text.bind("<KeyRelease>", self._schedule_highlight, add="+")
        self.text.bind("<<TextEdited>>", self._schedule_highlight, add="+")

        # Date — всегда под Text, дата создания поста
        date_box = AsciiBox(right, font, title="Date", cols=30, rows=3)
        date_box.grid(row=2, column=0, sticky="e")
        self.date_label = tk.Label(date_box.inner, text="", font=font, fg=SILVER, bg=PANEL)
        self.date_label.pack(expand=True)

    def _build_toolbar(self, small):
        """Панель форматирования Markdown: кнопки + подсказка под ними."""
        bar = tk.Frame(self.toolbar, bg=PANEL)
        bar.pack(fill="x")
        self.tool_hint = tk.Label(self.toolbar, text=TOOL_HINT, font=small, fg=SILVER_DK,
                                  bg=PANEL, anchor="w")
        self.tool_hint.pack(fill="x")
        tools = (("[B]", "bold", "Жирный — Ctrl+B"),
                 ("[I]", "italic", "Курсив — Ctrl+I"),
                 ("[S]", "strike", "Зачёркнутый — Ctrl+D"),
                 ("[`]", "code", "Код в строке — Ctrl+E"),
                 ("[H]", "heading", "Заголовок: # → ## → ### → обычный"),
                 ("[-]", "bullet", "Маркированный список"),
                 ("[1.]", "numbered", "Нумерованный список"),
                 ("[>]", "quote", "Цитата"),
                 ("[```]", "codeblock", "Блок кода"),
                 ("[--]", "hr", "Горизонтальная линия"),
                 ("[URL]", "link", "Ссылка — Ctrl+K"))
        for label, action, hint in tools:
            btn = AsciiButton(bar, label, lambda a=action: self._fmt(a), small)
            btn.pack(side="left", padx=2)
            btn.bind("<Enter>", lambda e, h=hint: self.tool_hint.config(text=h), add="+")
            btn.bind("<Leave>", lambda e: self.tool_hint.config(text=TOOL_HINT), add="+")
        self.preview_btn = AsciiButton(bar, "[ Preview ]", self._toggle_preview, small, fg=SILVER)
        self.preview_btn.pack(side="right", padx=2)

    def _configure_text_tags(self):
        """Теги оформления Text: и для показа Markdown, и для подсветки при вводе."""
        t, fonts = self.text, self.app.md_fonts
        # абзацный отступ: lmargin1 действует на первую строку каждого абзаца
        try:
            t.tag_configure("para", lmargin1=PARAGRAPH_INDENT, lmargin2=0, spacing3=4)
        except tk.TclError:   # на случай, если Tk не принял дробное значение
            t.tag_configure("para", lmargin1=int(round(float(PARAGRAPH_INDENT))),
                            lmargin2=0, spacing3=4)
        t.tag_configure("dim", foreground=SILVER_DK)
        # --- показ Markdown ---
        t.tag_configure("h1", font=fonts["h1"], foreground=GOLD_HI, spacing1=8, spacing3=4)
        t.tag_configure("h2", font=fonts["h2"], foreground=GOLD, spacing1=6, spacing3=3)
        t.tag_configure("h3", font=fonts["h3"], foreground=GOLD, spacing1=4, spacing3=2)
        for level in range(4):    # вложенность списка = отступ, перенос строки = «висячий» отступ
            t.tag_configure(f"list{level}", lmargin1=10 + 18 * level,
                            lmargin2=26 + 18 * level, spacing3=2)
        t.tag_configure("bullet", foreground=GOLD)
        t.tag_configure("quote", foreground=SILVER, lmargin1=8, lmargin2=20)
        t.tag_configure("hr", foreground=SILVER_DK)
        t.tag_configure("codeblock", background=CODE_BG, foreground=GOLD, lmargin1=10, lmargin2=10)
        t.tag_configure("code", background=CODE_BG, foreground=GOLD)
        t.tag_configure("strike", overstrike=True, foreground=SILVER)
        t.tag_configure("bold", font=fonts["bold"], foreground=BOLD_FG)
        t.tag_configure("italic", font=fonts["italic"])
        t.tag_configure("bolditalic", font=fonts["bolditalic"], foreground=BOLD_FG)
        # --- подсветка синтаксиса при вводе ---
        t.tag_configure("md_head", font=fonts["bold"], foreground=GOLD_HI)
        t.tag_configure("md_b", font=fonts["bold"], foreground=BOLD_FG)
        t.tag_configure("md_i", font=fonts["italic"])
        t.tag_configure("md_bi", font=fonts["bolditalic"], foreground=BOLD_FG)
        t.tag_configure("md_s", overstrike=True, foreground=SILVER)
        t.tag_configure("md_code", background=CODE_BG, foreground=GOLD)
        t.tag_configure("md_link", foreground=GOLD_HI, underline=True)
        t.tag_configure("md_quote", foreground=SILVER)
        t.tag_configure("md_mark", foreground=GOLD)
        t.tag_raise("sel")        # выделение должно быть видно поверх фона кода

    # ------------------------------------------------------------------ данные
    def reload(self, select_id=None):
        """Перечитать посты пользователя из БД (orm.get_post) и обновить список."""
        # get_post порядок не гарантирует — сортируем сами: новые (больший id) сверху
        rows = sorted(orm.get_post(self.session, self.login), key=lambda p: p.id, reverse=True)
        # переносим в обычные dict: к ним можно обращаться, не трогая сессию
        self.posts = [dict(id=p.id, title=p.title or "", text=p.text or "", date=p.data)
                      for p in rows]
        self._apply_filter(select_id)

    def _apply_filter(self, select_id=None):
        """Показать в списке посты, чьё название содержит строку поиска."""
        query = self.search_var.get().strip().lower()
        self.visible = [p for p in self.posts if query in p["title"].lower()]
        self.listbox.config(state="normal")
        self.listbox.delete(0, "end")
        for p in self.visible:
            self.listbox.insert("end", p["title"] or "(без названия)")

        wanted = select_id if select_id is not None else self.current_id
        for i, p in enumerate(self.visible):
            if p["id"] == wanted:
                self.listbox.selection_set(i)
                self.listbox.see(i)
                self._show(p)
                return
        self._show(None)

    # ------------------------------------------------------------------ вывод поста
    def _show(self, post):
        """Вывести пост в правую часть (или заглушку, если поста нет)."""
        self._disarm()
        self.current_id = post["id"] if post else None
        self.title_var.set(post["title"] if post else "")
        self.date_label.config(text=f"Date ▸ {format_date(post['date'])}" if post else "Date ▸ —")
        if post:
            self._set_markdown(post["text"])
        else:
            self._set_text(NO_SIGNAL, tag="dim")

    def _reset_text(self, editable):
        """Очистить Text. editable=True — разрешить ввод, иначе поле только для чтения."""
        self._clear_links()
        self.text.config(state="normal", cursor="xterm" if editable else "arrow")
        self.text.delete("1.0", "end")

    def _finish_text(self, editable):
        self.text.edit_reset()      # история отмены не должна переходить от поста к посту
        if not editable:
            self.text.config(state="disabled")

    def _set_text(self, content, tag="para"):
        """Показать обычный текст (заглушка)."""
        self._reset_text(False)
        self.text.insert("1.0", content, tag)
        self._finish_text(False)

    def _set_markdown(self, source):
        """Показать пост с оформлением Markdown (только чтение)."""
        self._reset_text(False)
        for chunk, tags in markdown_to_runs(source):
            names = tuple(self._link_tag(x[4:]) if x.startswith("url:") else x for x in tags)
            self.text.insert("end", chunk, names)
        self.text.tag_raise("sel")
        self._finish_text(False)

    def _set_source(self, source):
        """Показать исходный Markdown для редактирования (с подсветкой синтаксиса)."""
        self._reset_text(True)
        self.text.insert("1.0", source)
        self.text.edit_reset()
        self._highlight()

    def _clear_links(self):
        for tag in self._links.values():
            self.text.tag_delete(tag)
        self._links = {}

    def _link_tag(self, url):
        """Тег ссылки: подчёркнутый, по клику открывает адрес в браузере.
        Ссылками становятся только http(s) — так разбирает их сам Markdown-парсер."""
        tag = self._links.get(url)
        if tag is None:
            tag = f"lnk{len(self._links)}"
            self._links[url] = tag
            t = self.text
            t.tag_configure(tag, foreground=GOLD_HI, underline=True)
            t.tag_bind(tag, "<Button-1>", lambda e, u=url: webbrowser.open(u))
            t.tag_bind(tag, "<Enter>", lambda e: t.config(cursor="hand2"))
            t.tag_bind(tag, "<Leave>", lambda e: t.config(cursor="arrow"))
        return tag

    # ------------------------------------------------------------------ Markdown: ввод
    def _schedule_highlight(self, _event=None):
        """Подсветка с небольшой задержкой, чтобы не пересчитывать на каждую клавишу."""
        if self.mode != "new" or self.previewing:
            return
        if self._hl_job is not None:
            self.after_cancel(self._hl_job)
        self._hl_job = self.after(60, self._highlight)

    def _highlight(self):
        self._hl_job = None
        if self.mode != "new" or self.previewing:
            return
        t = self.text
        for tag in MD_TAGS:
            t.tag_remove(tag, "1.0", "end")
        for tag, line, c0, c1 in highlight_spans(t.get("1.0", "end-1c")):
            t.tag_add(tag, f"{line}.{c0}", f"{line}.{c1}")

    def _current_source(self):
        """Исходный Markdown поста, который сейчас вводят."""
        return self._draft if self.previewing else self.text.get("1.0", "end-1c")

    def _toggle_preview(self):
        """Preview ⇄ Edit: показать, как текст будет выглядеть после сохранения."""
        if self.mode != "new":
            return
        if not self.previewing:
            self._draft = self.text.get("1.0", "end-1c")
            self.previewing = True
            self._set_markdown(self._draft)
            self.preview_btn.set_text("[ Edit ]")
        else:
            self.previewing = False
            self._set_source(self._draft)
            self.preview_btn.set_text("[ Preview ]")
            self.text.mark_set("insert", "end-1c")
            self.text.focus_set()

    def _selection_range(self):
        """Границы выделения в Text; если выделения нет — (курсор, курсор)."""
        try:
            return self.text.index("sel.first"), self.text.index("sel.last")
        except tk.TclError:
            pos = self.text.index("insert")
            return pos, pos

    def _fmt(self, action):
        """Применить оформление Markdown (кнопка панели или горячая клавиша)."""
        if self.mode != "new" or self.previewing:
            return
        t = self.text
        t.edit_separator()          # одно действие оформления = один шаг отмены
        marks = {"bold": "**", "italic": "*", "strike": "~~", "code": "`"}
        if action in marks:
            self._wrap(marks[action])
        elif action == "heading":
            self._lines_op(lambda ls: [cycle_heading(ls[0])] + ls[1:])
        elif action == "bullet":
            self._lines_op(lambda ls: toggle_prefix(ls, "- "))
        elif action == "numbered":
            self._lines_op(toggle_numbered)
        elif action == "quote":
            self._lines_op(lambda ls: toggle_prefix(ls, "> "))
        elif action == "codeblock":
            self._code_block()
        elif action == "hr":
            t.insert("insert", "\n---\n")
        elif action == "link":
            self._link()
        t.edit_separator()
        t.focus_set()
        self._schedule_highlight()

    def _wrap(self, marker):
        """Обернуть выделение в marker (или снять); без выделения — пара маркеров с курсором внутри."""
        t = self.text
        a, b = self._selection_range()
        selected = t.get(a, b) if a != b else ""
        new = toggle_wrap(selected, marker)
        if a != b:
            t.delete(a, b)
        t.insert(a, new)
        if selected:
            t.tag_remove("sel", "1.0", "end")
            t.tag_add("sel", a, f"{a}+{len(new)}c")
        else:
            t.mark_set("insert", f"{a}+{len(marker)}c")

    def _lines_op(self, transform):
        """Преобразовать строки, затронутые выделением (или текущую строку)."""
        t = self.text
        a, b = self._selection_range()
        first, last = int(a.split(".")[0]), int(b.split(".")[0])
        if last > first and b.endswith(".0"):     # выделение закончилось в начале строки
            last -= 1
        start, end = f"{first}.0", f"{last}.end"
        new = "\n".join(transform(t.get(start, end).split("\n")))
        t.delete(start, end)
        t.insert(start, new)
        t.tag_remove("sel", "1.0", "end")
        if a != b:
            t.tag_add("sel", start, f"{start}+{len(new)}c")
        else:
            t.mark_set("insert", f"{first}.end")

    def _code_block(self):
        t = self.text
        a, b = self._selection_range()
        selected = t.get(a, b) if a != b else ""
        if a != b:
            t.delete(a, b)
        t.insert(a, "```\n" + selected + "\n```")
        if not selected:
            t.mark_set("insert", f"{a}+4c")

    def _link(self):
        """[текст](https://…): выделенный текст становится названием ссылки."""
        t = self.text
        a, b = self._selection_range()
        selected = t.get(a, b) if a != b else ""
        if a != b:
            t.delete(a, b)
        new = f"[{selected}](https://)" if selected else "[текст](https://)"
        t.insert(a, new)
        t.tag_remove("sel", "1.0", "end")
        if selected:
            t.mark_set("insert", f"{a}+{len(new) - 1}c")     # курсор перед закрывающей скобкой
        else:
            t.tag_add("sel", f"{a}+1c", f"{a}+6c")           # выделяем «текст» — сразу вводить своё
            t.mark_set("insert", f"{a}+6c")

    def _say(self, text, kind="info"):
        """Сообщение в нижней части CRUD-фрейма."""
        color = {"err": ERR, "ok": GOLD_HI}.get(kind, SILVER)
        self.crud_msg.config(text=text, fg=color)

    # ------------------------------------------------------------------ обработчики
    def _on_select(self, _event=None):
        """Клик по названию в списке открывает пост."""
        if self.mode != "view":
            return
        sel = self.listbox.curselection()
        if sel:
            self._show(self.visible[sel[0]])
            self._say("")

    def _on_search(self):
        """Search: фильтр списка по части названия (без учёта регистра).
        ПОЧЕМУ не orm.select_model: она ищет только точное совпадение, а условие владельца в ней
        сейчас отбрасывается (в SQLAlchemy `A and B` возвращает A, а не «A и B»), так что поиск
        нашёл бы и чужие посты. Фильтруем уже загруженные свои посты."""
        if self.mode != "view":
            return
        self._apply_filter()
        n = len(self.visible)
        self._say(f"Найдено постов: {n}" if n else "Ничего не найдено", "ok" if n else "err")

    def _on_insert(self):
        """Insert: первый клик открывает форму нового поста, второй (Save) сохраняет."""
        if self.mode == "view":
            self._enter_new()
        else:
            self._save_new()

    def _enter_new(self):
        """Режим ввода: Title и Text становятся редактируемыми."""
        self._disarm()
        self.mode = "new"
        self.previewing = False
        self._draft = ""
        self.current_id = None
        self.listbox.selection_clear(0, "end")
        self.listbox.config(state="disabled")
        self.title_var.set("")
        self.title_entry.config(state="normal")
        self.preview_btn.set_text("[ Preview ]")
        self.toolbar.grid()
        self._set_source("")
        self.date_label.config(text=f"Date ▸ {format_date(date.today())}")
        self.insert_btn.set_text("[ Save ]")
        self.delete_btn.set_text("[ Cancel ]")
        self._say("Введите название и текст поста (Markdown), затем нажмите Save.")
        self.title_entry.focus_set()

    def _leave_new(self):
        """Выход из режима ввода: возвращаем поля в режим «только чтение»."""
        self.mode = "view"
        self.previewing = False
        self.toolbar.grid_remove()
        self.title_entry.config(state="readonly")
        self.insert_btn.set_text("[ Insert ]")
        self.delete_btn.set_text("[ Delete ]")
        self.listbox.config(state="normal")

    def _save_new(self):
        """Save: создаём пост готовой orm.create_post."""
        title = self.title_var.get().strip()
        body = self._current_source()      # сохраняется исходный Markdown, не оформленный вид
        if not title:
            self._say("[!] Название поста не может быть пустым", "err")
            return
        try:
            orm.create_post(self.session, self.login, title, body)
            self.session.commit()      # create_post только добавляет пост в сессию
        except Exception as exc:
            self.session.rollback()
            self._say(f"[!] Не удалось сохранить: {exc.__class__.__name__}", "err")
            return
        self._leave_new()
        self.search_var.set("")        # сбрасываем поиск, чтобы новый пост был виден
        self.reload()
        # новый пост получил наибольший id, а список отсортирован по убыванию id — он первый
        self._apply_filter(self.posts[0]["id"] if self.posts else None)
        self._say("[+] Пост добавлен", "ok")

    def _on_delete(self):
        """Delete: удаляет открытый пост после повторного нажатия (подтверждение).
        В режиме ввода эта кнопка работает как Cancel."""
        if self.mode == "new":
            self._leave_new()
            self._show(None)
            self._say("Ввод отменён")
            return
        if self.current_id is None:
            self._say("[!] Сначала выберите пост", "err")
            return
        if self._armed_id != self.current_id:
            # первое нажатие: просим подтвердить, через 3 секунды подтверждение сгорает
            self._armed_id = self.current_id
            self.delete_btn.set_text("[ Sure? ]")
            self._say("Нажмите Delete ещё раз, чтобы удалить пост.")
            self._armed_job = self.after(3000, self._disarm)
            return
        post_id = self.current_id
        try:
            # ПОЧЕМУ не orm.delete_model: сейчас она получает от select_model строки Row, а не
            # объекты Post, и session.delete() на них падает; к тому же поиск по названию
            # не ограничен владельцем. Берём пост из orm.get_post — это только посты текущего
            # пользователя, поэтому чужой пост удалить невозможно. Когда delete_model будет
            # исправлена, три строки ниже заменяются одним её вызовом.
            own = {p.id: p for p in orm.get_post(self.session, self.login)}
            post = own.get(post_id)
            if post is None:
                raise LookupError("post not found")
            self.session.delete(post)
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            self._disarm()
            self._say(f"[!] Не удалось удалить: {exc.__class__.__name__}", "err")
            return
        self._disarm()
        self.current_id = None
        self.reload()
        self._say("[+] Пост удалён", "ok")

    def _disarm(self):
        """Сбросить ожидание подтверждения удаления."""
        if self._armed_job is not None:
            self.after_cancel(self._armed_job)
            self._armed_job = None
        self._armed_id = None
        if self.mode == "view":
            self.delete_btn.set_text("[ Delete ]")


# ============================================================================
# Приложение: одно окно, две страницы
# ============================================================================
class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("LookForPassword")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)       # размер окна не меняется пользователем

        # Cascadia Code, если установлен; иначе ближайший моноширинный шрифт
        available = set(tkfont.families(self.root))
        family = next((name for name in FONT_CANDIDATES if name in available), "Courier")
        self.font = tkfont.Font(root=self.root, family=family, size=-13)
        self.font_bold = tkfont.Font(root=self.root, family=family, size=-13, weight="bold")
        self.font_small = tkfont.Font(root=self.root, family=family, size=-11)
        # шрифт текста поста по спецификации: Cascadia Code, 12 px
        self.text_font = tkfont.Font(root=self.root, family=family, size=-TEXT_FONT_PX)
        # шрифты оформления Markdown (тот же размер, что и текст поста; заголовки крупнее)
        def md_font(size, **kw):
            return tkfont.Font(root=self.root, family=family, size=-size, **kw)
        self.md_fonts = {
            "bold": md_font(TEXT_FONT_PX, weight="bold"),
            "italic": md_font(TEXT_FONT_PX, slant="italic"),
            "bolditalic": md_font(TEXT_FONT_PX, weight="bold", slant="italic"),
            "h1": md_font(20, weight="bold"),
            "h2": md_font(16, weight="bold"),
            "h3": md_font(14, weight="bold"),
        }

        self.page = None
        self.session = None
        self.root.protocol("WM_DELETE_WINDOW", self.quit)
        self.show_login()

    def _swap(self, page, size):
        """Заменить текущую страницу в том же окне и выставить размер по центру экрана."""
        if self.page is not None:
            self.page.destroy()
        self.page = page
        self.page.pack(fill="both", expand=True)
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        w, h = min(size[0], sw - 40), min(size[1], sh - 80)
        self.root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 3}")

    def show_login(self):
        """Главная страница (вход)."""
        self._swap(LoginPage(self), LoginPage.SIZE)

    def show_account(self, session, login):
        """Страница аккаунта (после успешного входа)."""
        self.session = session
        self._swap(AccountPage(self, session, login), AccountPage.SIZE)

    def logout(self):
        """Выход из аккаунта: закрываем сессию и возвращаемся ко входу."""
        self._close_session()
        self.show_login()

    def _close_session(self):
        if self.session is not None:
            self.session.rollback()     # несохранённых изменений быть не должно
            self.session.close()
            self.session = None

    def quit(self):
        """Закрытие окна."""
        self._close_session()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    App().run()
