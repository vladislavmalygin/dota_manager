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

        # Bootcamp planner button
        try:
            planned = conn.execute(
                "SELECT planned_bootcamp_date, planned_bootcamp_cost FROM teams WHERE id=?",
                (team_id,)
            ).fetchone() if False else None  # conn already closed above — re-query
        except Exception:
            planned = None
        conn3 = sqlite3.connect(db_name)
        planned = conn3.execute(
            "SELECT COALESCE(planned_bootcamp_date,''), COALESCE(planned_bootcamp_cost,0) "
            "FROM teams WHERE id=?", (team_id,)
        ).fetchone()
        conn3.close()
        if planned and planned[0]:
            grid.add_widget(self._row(
                f'  Запланирован буткемп на [b]{planned[0]}[/b]  (${planned[1]:,})',
                height=36,
            ))
            cancel_plan_btn = Button(
                text='Отменить запланированный буткемп',
                size_hint_y=None, height=40,
                background_color=(0.55, 0.20, 0.20, 1), background_normal='',
            )
            cancel_plan_btn.bind(on_press=lambda _, db=db_name, tid=team_id:
                                 _cancel_planned_bootcamp(db, tid, self))
            grid.add_widget(cancel_plan_btn)
        else:
            plan_btn = Button(
                text='Запланировать буткемп',
                size_hint_y=None, height=44,
                background_color=(0.18, 0.35, 0.50, 1), background_normal='',
            )
            plan_btn.bind(on_press=lambda _, db=db_name, tid=team_id, bud=budget:
                          _open_bootcamp_planner(db, tid, bud, self))
            grid.add_widget(plan_btn)

        # Loan button — only if budget < 2 months wages
        if total_wage > 0 and budget < total_wage * 2:
            loan_btn = Button(
                text='Взять кредит  ($50,000 / погашение $10,000×6 мес)',
                size_hint_y=None, height=50,
                background_color=(0.55, 0.35, 0.08, 1), background_normal='',
            )
            loan_btn.bind(on_press=lambda _, db=db_name, tid=team_id: _do_loan(db, tid, self))
            grid.add_widget(loan_btn)

        # ── Feature 6: Investor system ────────────────────────────────────────
        grid.add_widget(self._header("Инвестор"))
        conn_inv = sqlite3.connect(db_name)
        inv_info = conn_inv.execute(
            "SELECT COALESCE(investor_name,''), COALESCE(investor_end_date,''), "
            "COALESCE(investor_cut_pct,0), COALESCE(investor_condition,'') "
            "FROM teams WHERE id=?", (team_id,)
        ).fetchone()
        conn_inv.close()
        inv_name_cur, inv_end_cur, inv_cut_cur, inv_cond_cur = inv_info or ('', '', 0, '')

        today_str = str(_date.today())
        has_investor = bool(inv_name_cur and inv_end_cur >= today_str)

        if has_investor:
            try:
                days_left_inv = (_date.fromisoformat(inv_end_cur) - _date.fromisoformat(today_str)).days
            except Exception:
                days_left_inv = 0
            grid.add_widget(self._row(
                f"  Инвестор: {inv_name_cur}  |  Доля: {inv_cut_cur}%  |  До: {inv_end_cur}  "
                f"({days_left_inv} дн.)"
            ))
            if inv_cond_cur:
                _COND_LABELS_ORG = {
                    'top8_any': 'Топ-8 любого турнира',
                    'top4_any': 'Топ-4 любого турнира',
                    'top1_any': 'Победа в турнире',
                }
                grid.add_widget(self._row(
                    f"  Условие: {_COND_LABELS_ORG.get(inv_cond_cur, inv_cond_cur)}"
                ))
            cancel_inv_btn = Button(
                text='Досрочно расторгнуть  (штраф $50,000)',
                size_hint_y=None, height=44,
                background_color=(0.65, 0.20, 0.18, 1), background_normal='',
            )
            cancel_inv_btn.bind(on_press=lambda _, db=db_name, tid=team_id:
                                _cancel_investor(db, tid, self))
            grid.add_widget(cancel_inv_btn)
        else:
            grid.add_widget(self._row("  Нет активного инвестора."))
            grid.add_widget(self._row("  Выберите тип инвестирования:"))
            _INVEST_TIERS = [
                ('Бизнес-ангел', 100_000,  5, 12, 'top8_any', 'Топ-8 любого турнира'),
                ('Венчур',       200_000, 10, 18, 'top4_any', 'Топ-4 любого турнира'),
                ('Корпорация',   400_000, 15, 24, 'top1_any', 'Победа в турнире'),
            ]
            for tier_name, lump_sum, cut_pct, duration, condition, cond_label_str in _INVEST_TIERS:
                btn_text = (f'{tier_name}  +${lump_sum:,}  /  {cut_pct}% cut  /  '
                            f'{duration} мес  /  {cond_label_str}')
                inv_btn = Button(
                    text=btn_text, size_hint_y=None, height=50,
                    background_color=(0.18, 0.40, 0.65, 1), background_normal='',
                    disabled=has_investor,
                )
                inv_btn.bind(on_press=lambda _, db=db_name, tid=team_id,
                             ls=lump_sum, tn=tier_name, d=duration,
                             cp=cut_pct, cond=condition:
                             _accept_investor(db, tid, ls, tn, d, cp, cond, self))
                grid.add_widget(inv_btn)

        # ── Brand investment ──────────────────────────────────────────────────
        grid.add_widget(self._header("Бренд организации"))
        conn_brand = sqlite3.connect(db_name)
        brand_val = conn_brand.execute(
            "SELECT COALESCE(brand_value,0) FROM teams WHERE id=?", (team_id,)
        ).fetchone()
        brand_val = brand_val[0] if brand_val else 0
        conn_brand.close()

        grid.add_widget(self._row(f"  Ценность бренда: {brand_val}/300"))
        # Mini progress bar text
        bar_pct = int(brand_val / 300 * 20)
        bar_txt = '[' + '█' * bar_pct + '░' * (20 - bar_pct) + ']'
        grid.add_widget(self._row(f"  {bar_txt}", height=28))

        for cost, gain, label in [
            (20_000,  10, 'Соцсети  ($20k → +10 бренд)'),
            (50_000,  25, 'Мерч и форма  ($50k → +25 бренд)'),
            (100_000, 60, 'PR-кампания  ($100k → +60 бренд)'),
        ]:
            can = budget >= cost and brand_val < 300
            btn = Button(
                text=label, size_hint_y=None, height=44,
                background_color=(0.20, 0.35, 0.55, 1) if can else (0.3, 0.3, 0.3, 1),
                background_normal='',
                disabled=not can,
            )
            btn.bind(on_press=lambda _, c=cost, g=gain:
                     _do_brand_invest(db_name, team_id, c, g, self))
            grid.add_widget(btn)


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


def _cancel_planned_bootcamp(db_name, team_id, popup):
    conn = sqlite3.connect(db_name)
    conn.execute(
        "UPDATE teams SET planned_bootcamp_date=NULL, planned_bootcamp_cost=0 WHERE id=?",
        (team_id,)
    )
    conn.commit(); conn.close()
    popup.dismiss()


def _open_bootcamp_planner(db_name, team_id, budget, popup):
    from kivy.uix.popup import Popup
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.gridlayout import GridLayout
    from kivy.uix.label import Label
    from kivy.uix.button import Button
    from datetime import date as _d, timedelta
    import sqlite3 as _sq

    gd = _sq.connect(db_name).execute("SELECT date FROM save WHERE id=1").fetchone()
    today = _d.fromisoformat(gd[0]) if gd else _d.today()

    p = Popup(title='Запланировать буткемп', size_hint=(0.55, 0.55))
    root = BoxLayout(orientation='vertical', padding=10, spacing=8)
    root.add_widget(Label(
        text='Выберите тип и срок буткемпа (дней от сегодня):',
        size_hint_y=None, height=36, color=(0.8, 0.8, 1.0, 1),
    ))

    gl = GridLayout(cols=1, size_hint_y=None, spacing=6)
    gl.bind(minimum_height=gl.setter('height'))

    options = [
        (30,  15_000, 10, 0, 'Через 30 дн — лёгкий ($15k → +10 сыгр.)'),
        (60,  15_000, 10, 0, 'Через 60 дн — лёгкий ($15k → +10 сыгр.)'),
        (30,  25_000, 15, 1, 'Через 30 дн — серьёзный ($25k → +15 сыгр. +1 мораль)'),
        (60,  25_000, 15, 1, 'Через 60 дн — серьёзный ($25k → +15 сыгр. +1 мораль)'),
        (90,  25_000, 15, 1, 'Через 90 дн — серьёзный ($25k → +15 сыгр. +1 мораль)'),
    ]
    for days, cost, coh, mor, label in options:
        can = budget >= cost
        target = str(today + timedelta(days=days))
        b = Button(
            text=f'{label}  [{target}]',
            size_hint_y=None, height=44,
            background_color=(0.18, 0.40, 0.20, 1) if can else (0.3, 0.3, 0.3, 1),
            background_normal='',
            disabled=not can,
        )
        def _plan(_, _target=target, _cost=cost):
            c2 = _sq.connect(db_name)
            c2.execute(
                "UPDATE teams SET planned_bootcamp_date=?, planned_bootcamp_cost=? WHERE id=?",
                (_target, _cost, team_id)
            )
            c2.commit(); c2.close()
            p.dismiss()
            popup.dismiss()
        b.bind(on_press=_plan)
        gl.add_widget(b)

    from kivy.uix.scrollview import ScrollView
    sv = ScrollView()
    sv.add_widget(gl)
    root.add_widget(sv)
    cancel = Button(text='Отмена', size_hint_y=None, height=44,
                    background_color=(0.5, 0.15, 0.15, 1), background_normal='')
    cancel.bind(on_press=p.dismiss)
    root.add_widget(cancel)
    p.content = root
    p.open()


def _do_brand_invest(db_name, team_id, cost, gain, popup):
    from kivy.uix.popup import Popup
    from kivy.uix.label import Label
    conn = sqlite3.connect(db_name)
    budget = conn.execute(
        "SELECT COALESCE(budget,0) FROM teams WHERE id=?", (team_id,)
    ).fetchone()[0]
    if budget < cost:
        conn.close()
        Popup(content=Label(text='Недостаточно средств', halign='center'),
              size_hint=(0.4, 0.22)).open()
        return
    conn.execute(
        "UPDATE teams SET "
        "brand_value=MIN(300, COALESCE(brand_value,0)+?), "
        "budget=budget-? "
        "WHERE id=?",
        (gain, cost, team_id)
    )
    conn.execute(
        "INSERT INTO messages (text, date, author) VALUES (?,date('now'),?)",
        (f"Инвестиция в бренд: +{gain} ценности бренда. Стоимость: −${cost:,}",
         "Организация"),
    )
    conn.commit(); conn.close()
    popup.dismiss()
    show_organization_popup(db_name)


def _accept_investor(db_name, team_id, lump_sum, tier_name, duration, cut_pct, condition, popup):
    """Feature 6: Accept an investor deal."""
    conn = sqlite3.connect(db_name)
    conn.execute(
        "UPDATE teams SET budget=budget+?, investor_name=?, "
        "investor_end_date=date('now','+'||?||' months'), "
        "investor_cut_pct=?, investor_condition=? WHERE id=?",
        (lump_sum, tier_name, duration, cut_pct, condition, team_id)
    )
    conn.execute(
        "INSERT INTO messages (text, date, author) VALUES (?,date('now'),?)",
        (f'Привлечён инвестор: {tier_name}. Получено ${lump_sum:,}. '
         f'Доля {cut_pct}% на {duration} мес.',
         'Организация')
    )
    conn.commit(); conn.close()
    popup.dismiss()
    show_organization_popup(db_name)


def _cancel_investor(db_name, team_id, popup):
    """Feature 6: Early termination of investor deal."""
    conn = sqlite3.connect(db_name)
    conn.execute(
        "UPDATE teams SET budget=MAX(0,budget-50000), investor_name='', "
        "investor_end_date='', investor_cut_pct=0, investor_condition='' WHERE id=?",
        (team_id,)
    )
    conn.execute(
        "INSERT INTO messages (text, date, author) VALUES (?,date('now'),?)",
        ('Инвестиционный договор расторгнут досрочно. Штраф: −$50,000.',
         'Организация')
    )
    conn.commit(); conn.close()
    popup.dismiss()
    show_organization_popup(db_name)


def show_organization_popup(db_name):
    popup = OrganizationPopup(db_name=db_name)
    popup.open()
