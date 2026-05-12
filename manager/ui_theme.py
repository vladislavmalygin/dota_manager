"""Centralized UI theme and utilities for dota_manager."""
import traceback as _tb


def log_err(context: str, exc: Exception) -> None:
    """Log exception with context instead of silent pass."""
    print(f'[ERROR] {context}: {exc}')
    _tb.print_exc()

# ── Backgrounds ───────────────────────────────────────────────────────────────
BG_APP      = (0.06, 0.08, 0.12, 1)
BG_SIDEBAR  = (0.07, 0.09, 0.13, 0.97)
BG_TOPBAR   = (0.06, 0.08, 0.12, 0.96)
BG_CARD     = (0.10, 0.13, 0.18, 1)
BG_CARD_B   = (0.09, 0.12, 0.16, 1)
BG_CARD_TRN = (0.09, 0.08, 0.16, 1)   # tournament card
BG_CARD_RES = (0.07, 0.12, 0.09, 1)   # results card
BG_ROW_A    = (0.11, 0.14, 0.18, 1)
BG_ROW_B    = (0.09, 0.12, 0.16, 1)
BG_HEADER   = (0.07, 0.22, 0.35, 1)
BG_WIN      = (0.06, 0.18, 0.08, 1)
BG_LOSE     = (0.20, 0.06, 0.06, 1)

# ── Navigation ────────────────────────────────────────────────────────────────
NAV_IDLE    = (0.12, 0.17, 0.30, 1)
NAV_ACTIVE  = (0.05, 0.45, 0.65, 1)    # FM23 teal
NAV_ALERT   = (0.58, 0.18, 0.08, 1)
NAV_SEP_BG  = (0.07, 0.10, 0.17, 1)
NAV_SEP_FG  = (0.38, 0.58, 0.80, 1)

# ── Text ──────────────────────────────────────────────────────────────────────
TEXT_MAIN   = (0.93, 0.93, 0.93, 1)
TEXT_DIM    = (0.52, 0.58, 0.64, 1)
TEXT_LABEL  = (0.58, 0.70, 0.84, 1)
ACCENT      = (0.20, 0.82, 1.00, 1)    # FM teal
PLAYER_CLR  = (0.25, 0.95, 0.50, 1)

# ── Semantic status ───────────────────────────────────────────────────────────
POSITIVE    = (0.25, 0.90, 0.42, 1)
NEGATIVE    = (0.95, 0.28, 0.20, 1)
WARNING     = (0.98, 0.78, 0.12, 1)
GOLD        = (1.00, 0.84, 0.25, 1)
SILVER      = (0.80, 0.80, 0.85, 1)
BRONZE      = (0.80, 0.50, 0.25, 1)

# ── Buttons ───────────────────────────────────────────────────────────────────
BTN_PRIMARY = (0.12, 0.45, 0.65, 1)
BTN_DANGER  = (0.65, 0.18, 0.18, 1)
BTN_SUCCESS = (0.15, 0.55, 0.20, 1)
BTN_NEUTRAL = (0.20, 0.26, 0.38, 1)

# ── Font sizes ────────────────────────────────────────────────────────────────
FS_HERO  = '22sp'
FS_TITLE = '16sp'
FS_BODY  = '13sp'
FS_SMALL = '11sp'
FS_TINY  = '10sp'


# ── Color helpers ─────────────────────────────────────────────────────────────

def skill_color(v):
    if v >= 80: return POSITIVE
    if v >= 60: return WARNING
    return NEGATIVE


def morale_color(v):
    if v >= 7: return POSITIVE
    if v >= 4: return WARNING
    return NEGATIVE


def cohesion_color(v):
    if v >= 70: return POSITIVE
    if v >= 40: return WARNING
    return NEGATIVE


def budget_color(v):
    if v > 200_000: return POSITIVE
    if v > 50_000:  return WARNING
    return NEGATIVE


def balance_color(v):
    return POSITIVE if v >= 0 else NEGATIVE


def place_color(place):
    if place == 1: return GOLD
    if place == 2: return SILVER
    if place <= 4: return BRONZE
    return TEXT_DIM


def markup_color(rgba):
    """Convert (r,g,b,a) to kivy markup hex color string."""
    r, g, b = int(rgba[0]*255), int(rgba[1]*255), int(rgba[2]*255)
    return f'#{r:02x}{g:02x}{b:02x}'


# ── Common widget factories ───────────────────────────────────────────────────

def make_label(text, height=32, color=TEXT_MAIN, font_size=FS_BODY,
               bold=False, halign='left', markup=False):
    from kivy.uix.label import Label
    if bold:
        text = f'[b]{text}[/b]'
        markup = True
    lbl = Label(
        text=text, markup=markup,
        size_hint_y=None, height=height,
        color=color, font_size=font_size,
        halign=halign, valign='middle',
    )
    lbl.bind(size=lbl.setter('text_size'))
    return lbl


def make_card(bg=BG_CARD, radius=8, padding=(12, 10), spacing=0):
    """Auto-sizing card with rounded background."""
    from kivy.uix.gridlayout import GridLayout
    from kivy.graphics import Color, RoundedRectangle
    inner = GridLayout(cols=1, size_hint_y=None,
                       spacing=spacing, padding=padding)
    inner.bind(minimum_height=inner.setter('height'))
    with inner.canvas.before:
        Color(*bg)
        _r = RoundedRectangle(radius=[radius])
    inner.bind(
        pos =lambda w, _: setattr(_r, 'pos',  w.pos),
        size=lambda w, _: setattr(_r, 'size', w.size),
    )
    return inner


def make_chip(text, bg=BTN_NEUTRAL, fg=TEXT_MAIN, font_size=FS_TINY):
    """Small rounded colored label chip."""
    from kivy.uix.label import Label
    from kivy.graphics import Color, RoundedRectangle
    lbl = Label(
        text=text, markup=False,
        size_hint=(None, None), width=58, height=18,
        font_size=font_size, color=fg,
        halign='center', valign='middle',
    )
    lbl.bind(size=lbl.setter('text_size'))
    with lbl.canvas.before:
        Color(*bg)
        _r = RoundedRectangle(pos=lbl.pos, size=lbl.size, radius=[4])
    lbl.bind(
        pos =lambda w, _: setattr(_r, 'pos',  w.pos),
        size=lambda w, _: setattr(_r, 'size', w.size),
    )
    return lbl


def skill_bar_text(v, width=6):
    """Compact markup bar + number for skill display: ████░░ 82"""
    filled = max(0, min(width, int(v / 100 * width)))
    empty  = width - filled
    c   = markup_color(skill_color(v))
    dim = markup_color(TEXT_DIM)
    bar = f'[color={c}]{"█" * filled}[/color][color={dim}]{"█" * empty}[/color]'
    return f'{bar} {v}'


def make_stepper(steps, active_idx, height=38):
    """Horizontal step indicator. active_idx is 0-based."""
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.label import Label
    from kivy.graphics import Color, RoundedRectangle

    row = BoxLayout(orientation='horizontal', size_hint_y=None, height=height,
                    padding=(12, 0), spacing=0)
    with row.canvas.before:
        Color(*BG_HEADER)
        _r = RoundedRectangle(radius=[4])
    row.bind(pos =lambda w, _: setattr(_r, 'pos',  w.pos),
             size=lambda w, _: setattr(_r, 'size', w.size))

    for i, step in enumerate(steps):
        if i == active_idx:
            text = f'[b][color={markup_color(ACCENT)}]● {step}[/color][/b]'
        elif i < active_idx:
            text = f'[color={markup_color(POSITIVE)}]✓ {step}[/color]'
        else:
            text = f'[color={markup_color(TEXT_DIM)}]○ {step}[/color]'
        lbl = Label(text=text, markup=True, size_hint_x=1,
                    halign='center', valign='middle', font_size=FS_SMALL)
        lbl.bind(size=lbl.setter('text_size'))
        row.add_widget(lbl)
        if i < len(steps) - 1:
            sep = Label(text=f'[color={markup_color(TEXT_DIM)}]──[/color]',
                        markup=True, size_hint_x=None, width=28,
                        halign='center', valign='middle', font_size=FS_SMALL)
            row.add_widget(sep)
    return row


def make_row_separator(height=1):
    from kivy.uix.widget import Widget
    from kivy.graphics import Color, Rectangle
    sep = Widget(size_hint_y=None, height=height)
    with sep.canvas.before:
        Color(0.18, 0.22, 0.30, 1)
        _r = Rectangle()
    sep.bind(pos=lambda w, _: setattr(_r, 'pos', w.pos),
             size=lambda w, _: setattr(_r, 'size', w.size))
    return sep
