import sqlite3

from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle, RoundedRectangle

_ACCENT = (0.35, 0.85, 1.00, 1)
_GOLD   = (1.00, 0.85, 0.25, 1)
_GREEN  = (0.20, 0.88, 0.35, 1)
_RED    = (0.90, 0.28, 0.20, 1)
_WHITE  = (0.92, 0.92, 0.92, 1)
_DIM    = (0.55, 0.55, 0.55, 1)
_BG     = (0.10, 0.10, 0.12, 1)
_BG_MED = (0.15, 0.15, 0.18, 1)
_BG_HDR = (0.10, 0.22, 0.32, 1)


class _BgBox(BoxLayout):
    def __init__(self, bg=_BG_MED, **kw):
        super().__init__(**kw)
        with self.canvas.before:
            self._c = Color(*bg)
            self._r = Rectangle()
        self.bind(pos=self._upd, size=self._upd)

    def _upd(self, *_):
        self._r.pos  = self.pos
        self._r.size = self.size


def _lbl(text, color=_WHITE, height=30, halign='left', bold=False, font_size='13sp'):
    t = f'[b]{text}[/b]' if bold else text
    l = Label(text=t, markup=True, color=color,
              size_hint_y=None, height=height,
              halign=halign, valign='middle', font_size=font_size)
    l.bind(size=l.setter('text_size'))
    return l


def _hdr(text, color=_ACCENT):
    box = _BgBox(bg=_BG_HDR, orientation='horizontal',
                 size_hint_y=None, height=36, padding=(8, 0))
    box.add_widget(_lbl(text, color=color, height=36, bold=True, font_size='14sp'))
    return box


def _row(left, right, bg=_BG_MED, color_r=_WHITE):
    box = _BgBox(bg=bg, orientation='horizontal',
                 size_hint_y=None, height=30, padding=(10, 0))
    box.add_widget(_lbl(left, color=_WHITE, height=30))
    box.add_widget(_lbl(right, color=color_r, height=30, halign='right'))
    return box


class FinancesPopup(Popup):

    def __init__(self, db_name, **kw):
        super().__init__(**kw)
        self.title      = 'Финансы'
        self.size_hint  = (0.80, 0.90)
        self._db        = db_name
        self._build()

    def _build(self):
        conn = sqlite3.connect(self._db)
        c    = conn.cursor()

        # ── team basics ───────────────────────────────────────
        c.execute(
            "SELECT name, COALESCE(budget,0) FROM teams WHERE player='yes'"
        )
        row = c.fetchone()
        if not row:
            conn.close()
            self.content = Label(text='Команда не найдена')
            return
        team_name, budget = row

        # ── wages ────────────────────────────────────────────
        c.execute(
            "SELECT t.carry,t.mid,t.offlane,t.partial_support,t.full_support "
            "FROM teams t WHERE t.player='yes'"
        )
        ids = c.fetchone() or []
        wages = []
        total_wage = 0
        role_names = ['Carry', 'Mid', 'Offlane', 'Support 4', 'Support 5']
        for i, pid in enumerate(ids):
            if pid:
                c.execute(
                    "SELECT nickname, COALESCE(wage,0), COALESCE(age,22), "
                    "COALESCE(micro_skills,0), COALESCE(macro_skills,0) "
                    "FROM players WHERE id=?", (pid,)
                )
                p = c.fetchone()
                if p:
                    wages.append((role_names[i], p[0], p[1], p[2], (p[3]+p[4])//2))
                    total_wage += p[1]

        # ── sponsor ──────────────────────────────────────────
        c.execute(
            "SELECT name, monthly_income, condition_type, condition_bonus, "
            "condition_penalty, signed_date, term_months "
            "FROM sponsors WHERE is_active=1 LIMIT 1"
        )
        sponsor = c.fetchone()

        # ── past tournament prizes ────────────────────────────
        c.execute(
            "SELECT t.name, t.start_date, t.prizepool, "
            "t.money1,t.money2,t.money3,t.money4,t.money5,t.money6,t.money7,t.money8, "
            "t.place1,t.place2,t.place3,t.place4,t.place5,t.place6,t.place7,t.place8 "
            "FROM tournaments t WHERE t.place1 IS NOT NULL "
            "ORDER BY t.start_date DESC LIMIT 8"
        )
        past = c.fetchall()

        c.execute(
            "SELECT id, COALESCE(rating,0), COALESCE(fans,0), "
            "COALESCE(loan_monthly,0), COALESCE(investor_cut_pct,0), "
            "COALESCE(investor_end_date,''), COALESCE(org_reputation,20) "
            "FROM teams WHERE player='yes'"
        )
        my_team_id_row = c.fetchone()
        my_team_id    = my_team_id_row[0] if my_team_id_row else None
        team_rating   = my_team_id_row[1] if my_team_id_row else 0
        fans          = my_team_id_row[2] if my_team_id_row else 0
        loan_monthly  = my_team_id_row[3] if my_team_id_row else 0
        inv_cut_pct   = my_team_id_row[4] if my_team_id_row else 0
        inv_end       = my_team_id_row[5] if my_team_id_row else ''
        org_rep       = my_team_id_row[6] if my_team_id_row else 20

        gd_row = c.execute("SELECT date FROM save WHERE id=1").fetchone()
        game_date_str = gd_row[0] if gd_row else '2024-01-01'

        rep_row = c.execute(
            "SELECT COALESCE(reputation,0) FROM characters LIMIT 1"
        ).fetchone()
        reputation = rep_row[0] if rep_row else 0

        conn.close()

        # ── UI ────────────────────────────────────────────────
        root = BoxLayout(orientation='vertical', spacing=4, padding=6)

        sv   = ScrollView(size_hint=(1, 1))
        grid = GridLayout(cols=1, size_hint_y=None, spacing=3)
        grid.bind(minimum_height=grid.setter('height'))

        # Budget banner
        budget_box = _BgBox(
            bg=(0.08, 0.22, 0.10, 1) if budget > 0 else (0.22, 0.08, 0.08, 1),
            orientation='horizontal', size_hint_y=None, height=52, padding=(12, 0)
        )
        budget_box.add_widget(_lbl(
            f'[b]{team_name}[/b]  —  бюджет: [b]${budget:,}[/b]',
            color=_GREEN if budget > 0 else _RED,
            height=52, font_size='16sp',
        ))
        grid.add_widget(budget_box)

        # Monthly balance & runway
        sponsor_income = sponsor[1] if sponsor else 0
        fans_income = (fans // 10_000) * 1_000
        streaming = max(1_000, int(team_rating * 50 + org_rep * 180 + fans_income))
        streaming = round(streaming / 500) * 500

        # Investor cut on streaming
        inv_cut = 0
        if inv_cut_pct > 0 and inv_end and inv_end >= game_date_str:
            inv_cut = int(team_rating * 120 * inv_cut_pct / 100)

        monthly_income = sponsor_income + streaming
        total_out = total_wage + loan_monthly + inv_cut
        balance = monthly_income - total_out
        bal_color = _GREEN if balance >= 0 else _RED

        grid.add_widget(_hdr('ДОХОДЫ', color=_GREEN))
        grid.add_widget(_row(
            f'Стриминг/мерч  (рейт. {int(team_rating)}, реп. {org_rep}, фанаты {fans:,})',
            f'+${streaming:,}/мес', color_r=_GREEN,
        ))
        if fans_income:
            grid.add_widget(_row(f'  в т.ч. мерч фанатов ({fans//1000}k)', f'+${fans_income:,}/мес', color_r=_GREEN))
        if sponsor_income:
            grid.add_widget(_row('Спонсор', f'+${sponsor_income:,}/мес', color_r=_GREEN))
        grid.add_widget(_row('Итого доход/мес', f'+${monthly_income:,}/мес', color_r=_GREEN))

        grid.add_widget(_hdr('РАСХОДЫ', color=_RED))
        grid.add_widget(_row('Зарплаты', f'-${total_wage:,}/мес', color_r=_RED))
        if loan_monthly:
            grid.add_widget(_row('Погашение кредита', f'-${loan_monthly:,}/мес', color_r=_RED))
        if inv_cut:
            grid.add_widget(_row(f'Инвестор ({inv_cut_pct}%)', f'-${inv_cut:,}/мес', color_r=_RED))
        grid.add_widget(_row('Итого расходы/мес', f'-${total_out:,}/мес', color_r=_RED))

        grid.add_widget(_row(
            'Чистый баланс/мес',
            f'{"+" if balance >= 0 else ""}{balance:,} $',
            bg=(0.08, 0.18, 0.10, 1) if balance >= 0 else (0.20, 0.08, 0.08, 1),
            color_r=bal_color,
        ))

        if balance < 0 and budget > 0:
            months_left = budget // abs(balance)
            runway_color = _GREEN if months_left > 6 else (_GOLD if months_left > 3 else _RED)
            grid.add_widget(_row(
                '⚠ Бюджет иссякнет через',
                f'~{months_left} мес.',
                bg=(0.20, 0.12, 0.05, 1), color_r=runway_color,
            ))
        elif balance >= 0:
            proj_3  = budget + balance * 3
            proj_6  = budget + balance * 6
            proj_12 = budget + balance * 12
            grid.add_widget(_row('Прогноз +3 мес.', f'${proj_3:,}', color_r=_GREEN))
            grid.add_widget(_row('Прогноз +6 мес.', f'${proj_6:,}', color_r=_GREEN))
            grid.add_widget(_row('Прогноз +12 мес.', f'${proj_12:,}', color_r=_GOLD))

        # Wages
        grid.add_widget(_hdr('ЗАРПЛАТЫ', color=_ACCENT))
        for role_name, nick, wage, age, skill in wages:
            grid.add_widget(_row(
                f'  {role_name}  {nick}  (возр. {age}, скилл {skill})',
                f'${wage:,}/мес',
                color_r=_WHITE,
            ))
        grid.add_widget(_row('  Итого зарплаты', f'${total_wage:,}/мес',
                             bg=(0.12, 0.12, 0.15, 1), color_r=_RED))

        # Sponsor
        grid.add_widget(_hdr('СПОНСОР', color=_GOLD))
        if sponsor:
            sname, sincome, scond, sbonus, spen, sdate, sterm = sponsor
            grid.add_widget(_row(f'  {sname}', f'+${sincome:,}/мес', color_r=_GREEN))
            grid.add_widget(_row(f'  Подписан', f'{sdate or "?"} на {sterm} мес.'))
            cond_map = {
                'top4': 'Топ-4 турнира',
                'top1': 'Победа в турнире',
                'always': 'Без условий',
            }
            cond_txt = cond_map.get(scond, scond)
            if sbonus:
                grid.add_widget(_row(f'  Бонус ({cond_txt})', f'+${sbonus:,}', color_r=_GREEN))
            if spen:
                grid.add_widget(_row(f'  Штраф (не выполнено)', f'-${spen:,}', color_r=_RED))
        else:
            grid.add_widget(_row('  Нет активного спонсора', '', color_r=_DIM))

        # Prize history
        grid.add_widget(_hdr('ПРИЗОВЫЕ  (последние турниры)', color=_ACCENT))
        if my_team_id:
            any_prize = False
            for trow in past:
                tname, tdate, prizepool = trow[0], trow[1], trow[2]
                money_list  = list(trow[3:11])
                places_list = list(trow[11:19])
                place = None
                for i, pid in enumerate(places_list):
                    if pid == my_team_id:
                        place = i + 1
                        break
                if place is None:
                    continue
                prize = money_list[place - 1] if place - 1 < len(money_list) else 0
                any_prize = True
                pc = _GOLD if place == 1 else (_WHITE if place <= 4 else _DIM)
                grid.add_widget(_row(
                    f'  {tdate[:7]}  {tname}',
                    f'{place}-е место  +${prize:,}' if prize else f'{place}-е место',
                    color_r=pc,
                ))
            if not any_prize:
                grid.add_widget(_row('  Нет данных', '', color_r=_DIM))
        else:
            grid.add_widget(_row('  Нет данных', '', color_r=_DIM))

        sv.add_widget(grid)
        root.add_widget(sv)

        close = Button(text='Закрыть', size_hint_y=None, height=46,
                       background_color=(0.55, 0.18, 0.18, 1), background_normal='')
        close.bind(on_press=self.dismiss)
        root.add_widget(close)

        self.content = root


def show_finances_popup(db_name):
    FinancesPopup(db_name=db_name).open()
