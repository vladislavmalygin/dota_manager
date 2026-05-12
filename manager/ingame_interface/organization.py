import sqlite3
from datetime import date as _date

from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout

_BOOTCAMP_COOLDOWN_DAYS = 30



class OrganizationPopup(Popup):
    def __init__(self, db_name, **kwargs):
        super().__init__(**kwargs)
        self.db_name = db_name
        self.title = ""
        self.size_hint = (0.85, 0.85)
        self.background_color = (1, 1, 1, 0)

        layout = BoxLayout(orientation='vertical', padding=5, spacing=5)
        scroll = ScrollView(size_hint=(1, 1))
        grid = GridLayout(cols=1, size_hint_y=None, spacing=4)
        grid.bind(minimum_height=grid.setter('height'))

        self._populate(db_name, grid)

        scroll.add_widget(grid)
        layout.add_widget(scroll)

        close_btn = Button(text='Закрыть', size_hint_y=None, height=50,
                           background_color=(0.8, 0.2, 0.2, 0.8))
        close_btn.bind(on_press=self.dismiss)
        layout.add_widget(close_btn)
        self.add_widget(layout)

    def _row(self, text, height=40):
        lbl = Label(text=text, size_hint_y=None, height=height,
                    halign='left', valign='middle', color=(1, 1, 1, 1))
        lbl.bind(size=lbl.setter('text_size'))
        return lbl

    def _header(self, text):
        lbl = Label(text=f'[b]{text}[/b]', markup=True,
                    size_hint_y=None, height=50,
                    halign='center', valign='middle',
                    color=(0.4, 0.9, 1.0, 1))
        lbl.bind(size=lbl.setter('text_size'))
        return lbl

    def _populate(self, db_name, grid):
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, name, country, budget, manager, rating, "
            "COALESCE(org_reputation,20), COALESCE(investor_name,''), "
            "COALESCE(investor_end_date,''), COALESCE(investor_cut_pct,0) "
            "FROM teams WHERE player = 'yes'"
        )
        team = cursor.fetchone()
        if not team:
            grid.add_widget(self._row("Команда не найдена."))
            conn.close()
            return

        team_id, name, country, budget, manager, rating, \
            org_rep, inv_name, inv_end, inv_cut = team
        budget = budget or 0
        rating = rating or 0

        # Active patch
        try:
            from logic.meta import patch_description
            patch_txt = patch_description(db_name)
        except Exception:
            patch_txt = ''

        grid.add_widget(self._header(f"Организация: {name}"))
        grid.add_widget(self._row(f"  Страна: {country or '—'}"))
        grid.add_widget(self._row(f"  Менеджер: {manager or '—'}"))
        grid.add_widget(self._row(f"  Рейтинг: {int(rating)}"))
        grid.add_widget(self._row(f"  Репутация орг.: {org_rep}/100"))
        if patch_txt:
            grid.add_widget(self._row(f"  {patch_txt}"))
        if inv_name and inv_end:
            grid.add_widget(self._row(
                f"  Инвестор: {inv_name}  ({inv_cut}% доходов до {inv_end})"
            ))
        grid.add_widget(self._row(f"  Бюджет: ${budget:,}", height=50))

        roles_order = ['carry', 'mid', 'offlane', 'partial_support', 'full_support']
        roles_labels = ['Carry (1)', 'Mid (2)', 'Offlane (3)', 'Support (4)', 'Support (5)']

        cursor.execute(
            "SELECT carry, mid, offlane, partial_support, full_support FROM teams WHERE id = ?",
            (team_id,)
        )
        role_ids = cursor.fetchone()

        grid.add_widget(self._header("Состав и зарплаты"))

        total_wage = 0
        for idx, role_label in enumerate(roles_labels):
            player_id = role_ids[idx] if role_ids else None
            if player_id:
                cursor.execute(
                    "SELECT name, surname, nickname, wage, micro_skills, macro_skills FROM players WHERE id = ?",
                    (player_id,)
                )
                p = cursor.fetchone()
                if p:
                    pname, psurname, pnick, wage, micro, macro = p
                    wage = wage or 0
                    total_wage += wage
                    skill_avg = int(((micro or 0) + (macro or 0)) / 2)
                    grid.add_widget(self._row(
                        f"  [{role_label}]  {pname} '{pnick}' {psurname}"
                        f"   Скилл: {skill_avg}   Зарплата: ${wage:,}/мес"
                    ))

        grid.add_widget(self._row(f"  Итого зарплат: ${total_wage:,}/мес", height=50))
        months_left = (budget // total_wage) if total_wage > 0 else 0
        grid.add_widget(self._row(
            f"  Бюджет хватит на: ~{months_left} мес.  "
            f"(после выплаты: ${budget - total_wage:,})"
        ))

        # Loan info
        loan_row = cursor.execute(
            "SELECT COALESCE(loan_amount,0), COALESCE(loan_monthly,0) FROM teams WHERE id=?",
            (team_id,)
        ).fetchone()
        if loan_row and loan_row[0] > 0:
            grid.add_widget(self._row(
                f"  Долг: ${loan_row[0]:,}  (погашение: ${loan_row[1]:,}/мес)",
                height=36,
            ))

        # Check bootcamp cooldown
        bootcamp_days_left = 0
        try:
            conn2 = sqlite3.connect(db_name)
            gd_row = conn2.execute("SELECT date FROM save WHERE id=1").fetchone()
            lbd_row = conn2.execute(
                "SELECT last_bootcamp_date FROM teams WHERE id=?", (team_id,)
            ).fetchone()
            conn2.close()
            if gd_row and lbd_row and lbd_row[0]:
                game_dt = _date.fromisoformat(gd_row[0])
                last_bc = _date.fromisoformat(lbd_row[0])
                days_since = (game_dt - last_bc).days
                bootcamp_days_left = max(0, _BOOTCAMP_COOLDOWN_DAYS - days_since)
        except Exception:
            pass

        # Rival info
        rival_name = None
        rival_wins = 0
        rival_losses = 0
        try:
            rv = conn.execute(
                "SELECT t2.name, t1.rival_wins, t1.rival_losses "
                "FROM teams t1 LEFT JOIN teams t2 ON t1.rival_team_id=t2.id "
                "WHERE t1.id=?", (team_id,)
            ).fetchone()
            if rv and rv[0]:
                rival_name, rival_wins, rival_losses = rv
        except Exception:
            pass

        conn.close()

        # ── Rival section ─────────────────────────────────────────
        grid.add_widget(self._header("Соперник"))
        if rival_name:
            grid.add_widget(self._row(
                f'  Соперник: [b]{rival_name}[/b]  |  '
                f'Победы: {rival_wins}  Поражений: {rival_losses}'
            ))
        else:
            grid.add_widget(self._row('  Соперник не выбран.'))
        rival_btn = Button(
            text='Выбрать соперника', size_hint_y=None, height=44,
            background_color=(0.30, 0.18, 0.48, 1), background_normal='',
        )
        rival_btn.bind(on_press=lambda _: _pick_rival(db_name, team_id, self))
        grid.add_widget(rival_btn)

        # ── Actions ──────────────────────────────────────────────
        grid.add_widget(self._header("Действия"))

        # Bootcamp
        if bootcamp_days_left > 0:
            grid.add_widget(Label(
                text=f'Буткемп недоступен — кулдаун {bootcamp_days_left} дн.',
                color=(0.6, 0.6, 0.6, 1), size_hint_y=None, height=36,
                halign='center', valign='middle',
            ))
        for cost, coh_gain, morale_gain, label in [
            (15_000, 10, 0, 'Буткемп лёгкий  ($15,000 → +10 сыгранности)'),
            (25_000, 15, 1, 'Буткемп серьёзный  ($25,000 → +15 сыгр. +1 мораль)'),
        ]:
            can = budget >= cost and bootcamp_days_left == 0
            btn = Button(
                text=label, size_hint_y=None, height=50,
                background_color=(0.15, 0.45, 0.20, 1) if can else (0.35, 0.35, 0.35, 1),
                background_normal='',
                disabled=not can,
            )
            btn.bind(on_press=lambda _, db=db_name, tid=team_id, c=cost,
                     cg=coh_gain, mg=morale_gain: _do_bootcamp(db, tid, c, cg, mg, self))
            grid.add_widget(btn)

        # Loan button — only if budget < 2 months wages
        if total_wage > 0 and budget < total_wage * 2:
            loan_btn = Button(
                text='Взять кредит  ($50,000 / погашение $10,000×6 мес)',
                size_hint_y=None, height=50,
                background_color=(0.55, 0.35, 0.08, 1), background_normal='',
            )
            loan_btn.bind(on_press=lambda _, db=db_name, tid=team_id: _do_loan(db, tid, self))
            grid.add_widget(loan_btn)


def _do_bootcamp(db_name, team_id, cost, coh_gain, morale_gain, popup):
    from kivy.uix.popup import Popup
    from kivy.uix.label import Label
    conn = sqlite3.connect(db_name)
    budget = conn.execute("SELECT COALESCE(budget,0) FROM teams WHERE id=?", (team_id,)).fetchone()[0]
    if budget < cost:
        conn.close()
        Popup(content=Label(text='Недостаточно средств'), size_hint=(0.4, 0.22)).open()
        return
    gd_row = conn.execute("SELECT date FROM save WHERE id=1").fetchone()
    game_date_str = gd_row[0] if gd_row else None
    conn.execute(
        "UPDATE teams SET budget=budget-?, cohesion=MIN(100,COALESCE(cohesion,0)+?), "
        "last_bootcamp_date=? WHERE id=?",
        (cost, coh_gain, game_date_str, team_id),
    )
    if morale_gain > 0:
        slots = conn.execute(
            "SELECT carry,mid,offlane,partial_support,full_support FROM teams WHERE id=?",
            (team_id,)
        ).fetchone() or ()
        for pid in slots:
            if pid:
                conn.execute(
                    "UPDATE players SET morale=MIN(10,COALESCE(morale,5)+?) WHERE id=?",
                    (morale_gain, pid)
                )
    conn.execute(
        "INSERT INTO messages (text, date, author) VALUES (?,date('now'),?)",
        (f"Буткемп проведён: +{coh_gain} сыгранности"
         + (f", +{morale_gain} мораль" if morale_gain else "") +
         f". Стоимость: −${cost:,}", "Организация"),
    )
    conn.commit(); conn.close()
    popup.dismiss()
    show_organization_popup(db_name)


def _do_loan(db_name, team_id, popup):
    from kivy.uix.popup import Popup
    from kivy.uix.label import Label
    conn = sqlite3.connect(db_name)
    existing = (conn.execute(
        "SELECT COALESCE(loan_amount,0) FROM teams WHERE id=?", (team_id,)
    ).fetchone() or (0,))[0]
    if existing > 0:
        conn.close()
        Popup(content=Label(text='Уже есть непогашенный кредит', halign='center'),
              size_hint=(0.45, 0.22)).open()
        return
    conn.execute(
        "UPDATE teams SET budget=budget+50000, loan_amount=50000, loan_monthly=10000 WHERE id=?",
        (team_id,)
    )
    conn.execute(
        "INSERT INTO messages (text, date, author) VALUES (?,date('now'),?)",
        ("Кредит получен: +$50,000. Погашение: $10,000/мес × 6.", "Финансы"),
    )
    conn.commit(); conn.close()
    popup.dismiss()
    show_organization_popup(db_name)


def _pick_rival(db_name, team_id, parent_popup):
    from kivy.uix.popup import Popup
    from kivy.uix.scrollview import ScrollView
    conn = sqlite3.connect(db_name)
    teams = conn.execute(
        "SELECT id, name FROM teams WHERE id!=? AND player!='yes' "
        "ORDER BY COALESCE(rating,0) DESC LIMIT 12", (team_id,)
    ).fetchall()
    conn.close()

    root = BoxLayout(orientation='vertical', padding=8, spacing=6)
    root.add_widget(Label(text='Выберите соперника:', size_hint_y=None, height=30,
                          color=(0.85, 0.70, 1.0, 1), bold=True))
    sv = ScrollView(size_hint=(1, 1))
    grid = GridLayout(cols=1, size_hint_y=None, spacing=3)
    grid.bind(minimum_height=grid.setter('height'))

    popup = Popup(title='', content=root, size_hint=(0.55, 0.65),
                  background_color=(1, 1, 1, 0))

    def _set(tid, tname):
        c2 = sqlite3.connect(db_name)
        c2.execute(
            "UPDATE teams SET rival_team_id=?, rival_wins=0, rival_losses=0 WHERE id=?",
            (tid, team_id)
        )
        c2.execute(
            "INSERT INTO messages (text, date, author) VALUES (?,date('now'),?)",
            (f'Выбран соперник: {tname}. Победы над ними будут засчитываться в соперничестве.',
             'Организация')
        )
        c2.commit(); c2.close()
        popup.dismiss()
        parent_popup.dismiss()
        show_organization_popup(db_name)

    for tid, tname in teams:
        b = Button(text=tname.strip(), size_hint_y=None, height=40,
                   background_color=(0.20, 0.15, 0.35, 1), background_normal='')
        b.bind(on_press=lambda _, i=tid, n=tname: _set(i, n))
        grid.add_widget(b)

    sv.add_widget(grid)
    root.add_widget(sv)
    popup.open()


def show_organization_popup(db_name):
    popup = OrganizationPopup(db_name=db_name)
    popup.open()
