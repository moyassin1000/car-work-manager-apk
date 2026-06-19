# -*- coding: utf-8 -*-
"""
برنامج شغل العربية PRO v6 - Kivy/KivyMD Edition
=================================================

تمت إعادة بناء الواجهة بالكامل باستخدام Kivy/KivyMD بدل CustomTkinter.
تم الحفاظ على نفس منطق الحسابات وقاعدة SQLite المحلية الموجودة في نسخة v5.

تشغيل على الكمبيوتر:
    pip install kivy kivymd arabic-reshaper python-bidi
    python car_work_manager_PRO_v6_KivyMD.py

ملاحظات مهمة:
- قاعدة البيانات يتم إنشاؤها باسم car_work_manager.db بجوار البرنامج على الكمبيوتر.
- على Android/Kivy يتم استخدام مجلد بيانات التطبيق تلقائيًا.
- تم إضافة دعم اختياري لتظبيط عرض النص العربي عبر arabic_reshaper + python-bidi.
"""
from __future__ import annotations

import csv
import os
import shutil
import sqlite3
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ----------------------------
# Optional Arabic shaping
# ----------------------------
try:
    import arabic_reshaper  # type: ignore
    from bidi.algorithm import get_display  # type: ignore

    def ar(text: object) -> str:
        value = str(text if text is not None else "")
        try:
            return get_display(arabic_reshaper.reshape(value))
        except Exception:
            return value
except Exception:
    def ar(text: object) -> str:
        return str(text if text is not None else "")


# ----------------------------
# Kivy / KivyMD imports
# ----------------------------
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.properties import ListProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

from kivymd.app import MDApp
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
try:
    from kivymd.uix.snackbar import Snackbar
except Exception:  # KivyMD API differences
    Snackbar = None  # type: ignore


APP_TITLE = "برنامج شغل العربية PRO"
APP_VERSION = "v6 KivyMD"
DB_NAME = "car_work_manager.db"

AR_DAYS = {
    0: "الاثنين",
    1: "الثلاثاء",
    2: "الأربعاء",
    3: "الخميس",
    4: "الجمعة",
    5: "السبت",
    6: "الأحد",
}

AR_MONTHS = [
    "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
    "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر",
]

NUMERIC_FIELDS = [
    "car_revenue", "fuel", "garage", "maintenance", "other_expenses", "paid_from_pocket",
    "driver_commission", "cycle_amount", "cycle_driver_commission",
]
TEXT_FIELDS = ["driver_name", "cycle_driver", "notes"]

DEFAULT_SETTINGS = {
    "my_share": "0.20",
    "partner1_share": "0.40",
    "partner2_share": "0.40",
    "admin_default_rate": "0.10",
    "admin_after_repair_rate": "0.15",
    "daily_garage": "25",
    "my_driver": "مصطفى",
    "driver_options": "مصطفى,مدحت,شخص آخر,بابا",
}

THEME = {
    "bg": "#070A13",
    "bg2": "#0B1020",
    "sidebar": "#050816",
    "sidebar2": "#0A1022",
    "card": "#111827",
    "card2": "#0F172A",
    "card3": "#172033",
    "border": "#243044",
    "text": "#F8FAFC",
    "muted": "#94A3B8",
    "muted2": "#64748B",
    "primary": "#38BDF8",
    "primary2": "#0EA5E9",
    "primary_dark": "#0369A1",
    "green": "#22C55E",
    "green_soft": "#12301F",
    "red": "#EF4444",
    "red_soft": "#351417",
    "orange": "#F59E0B",
    "orange_soft": "#3A260B",
    "purple": "#A78BFA",
    "purple_soft": "#241C3F",
    "cyan_soft": "#0B2C3F",
    "shadow": "#020617",
}


def rgba(hex_color: str, alpha: float = 1.0) -> List[float]:
    hex_color = hex_color.strip().lstrip("#")
    return [int(hex_color[i:i + 2], 16) / 255.0 for i in (0, 2, 4)] + [alpha]


@dataclass
class DayResult:
    income: float
    expenses: float
    admin_rate: float
    admin_value: float
    net: float
    status: str
    debt: float
    my_net: float
    partner1_net: float
    partner2_net: float
    partner1_debt: float
    partner2_debt: float


def safe_float(value: object, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        text = str(value).strip().replace(",", "")
        if text in {"", "-"}:
            return default
        return float(text)
    except Exception:
        return default


def money(value: float) -> str:
    return f"{value:,.2f}"


def pct(value: float) -> str:
    return f"{value * 100:.0f}%"


def parse_date(text: str) -> date:
    return datetime.strptime(text.strip(), "%Y-%m-%d").date()


def day_name(record_date: str) -> str:
    try:
        return AR_DAYS[parse_date(record_date).weekday()]
    except Exception:
        return ""


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


class Storage:
    def __init__(self, path: str) -> None:
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.create_schema()
        self.ensure_default_settings()

    def create_schema(self) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS records (
                record_date TEXT PRIMARY KEY,
                car_revenue REAL DEFAULT 0,
                fuel REAL DEFAULT 0,
                garage REAL DEFAULT 0,
                maintenance REAL DEFAULT 0,
                other_expenses REAL DEFAULT 0,
                paid_from_pocket REAL DEFAULT 0,
                driver_commission REAL DEFAULT 0,
                driver_name TEXT DEFAULT '',
                cycle_amount REAL DEFAULT 0,
                cycle_driver_commission REAL DEFAULT 0,
                cycle_driver TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.conn.commit()

    def ensure_default_settings(self) -> None:
        cur = self.conn.cursor()
        for key, value in DEFAULT_SETTINGS.items():
            cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?, ?)", (key, value))
        self.conn.commit()

    def get_settings(self) -> Dict[str, str]:
        rows = self.conn.execute("SELECT key, value FROM settings").fetchall()
        data = {r["key"]: r["value"] for r in rows}
        for key, value in DEFAULT_SETTINGS.items():
            data.setdefault(key, value)
        return data

    def save_settings(self, data: Dict[str, str]) -> None:
        cur = self.conn.cursor()
        for key, value in data.items():
            cur.execute(
                """
                INSERT INTO settings(key, value) VALUES(?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
                """,
                (key, value),
            )
        self.conn.commit()

    def init_year(self, year: int) -> None:
        daily_garage = safe_float(self.get_settings().get("daily_garage", "25"))
        current = date(year, 1, 1)
        end = date(year, 12, 31)
        cur = self.conn.cursor()
        while current <= end:
            cur.execute(
                """
                INSERT OR IGNORE INTO records(record_date, garage, updated_at)
                VALUES(?, ?, CURRENT_TIMESTAMP)
                """,
                (current.isoformat(), daily_garage),
            )
            current += timedelta(days=1)
        self.conn.commit()

    def default_record(self, record_date: str) -> Dict[str, object]:
        settings = self.get_settings()
        return {
            "record_date": record_date,
            "car_revenue": 0.0,
            "fuel": 0.0,
            "garage": safe_float(settings.get("daily_garage", "25")),
            "maintenance": 0.0,
            "other_expenses": 0.0,
            "paid_from_pocket": 0.0,
            "driver_commission": 0.0,
            "driver_name": "",
            "cycle_amount": 0.0,
            "cycle_driver_commission": 0.0,
            "cycle_driver": "",
            "notes": "",
        }

    def get_record(self, record_date: str) -> Dict[str, object]:
        row = self.conn.execute("SELECT * FROM records WHERE record_date=?", (record_date,)).fetchone()
        if row:
            return dict(row)
        return self.default_record(record_date)

    def save_record(self, record: Dict[str, object]) -> None:
        values = [safe_float(record.get(field)) for field in NUMERIC_FIELDS]
        text_values = [str(record.get(field, "") or "") for field in TEXT_FIELDS]
        self.conn.execute(
            """
            INSERT INTO records(
                record_date, car_revenue, fuel, garage, maintenance, other_expenses, paid_from_pocket,
                driver_commission, driver_name, cycle_amount, cycle_driver_commission, cycle_driver, notes, updated_at
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(record_date) DO UPDATE SET
                car_revenue=excluded.car_revenue,
                fuel=excluded.fuel,
                garage=excluded.garage,
                maintenance=excluded.maintenance,
                other_expenses=excluded.other_expenses,
                paid_from_pocket=excluded.paid_from_pocket,
                driver_commission=excluded.driver_commission,
                driver_name=excluded.driver_name,
                cycle_amount=excluded.cycle_amount,
                cycle_driver_commission=excluded.cycle_driver_commission,
                cycle_driver=excluded.cycle_driver,
                notes=excluded.notes,
                updated_at=CURRENT_TIMESTAMP
            """,
            [
                record["record_date"],
                values[0], values[1], values[2], values[3], values[4], values[5],
                values[6], text_values[0], values[7], values[8], text_values[1], text_values[2],
            ],
        )
        self.conn.commit()

    def reset_record(self, record_date: str) -> None:
        garage = safe_float(self.get_settings().get("daily_garage", "25"))
        self.conn.execute(
            """
            INSERT INTO records(record_date, garage, updated_at)
            VALUES(?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(record_date) DO UPDATE SET
                car_revenue=0, fuel=0, garage=excluded.garage, maintenance=0, other_expenses=0,
                paid_from_pocket=0, driver_commission=0, driver_name='',
                cycle_amount=0, cycle_driver_commission=0, cycle_driver='', notes='', updated_at=CURRENT_TIMESTAMP
            """,
            (record_date, garage),
        )
        self.conn.commit()

    def year_records(self, year: int) -> List[Dict[str, object]]:
        self.init_year(year)
        rows = self.conn.execute(
            "SELECT * FROM records WHERE record_date>=? AND record_date<=? ORDER BY record_date",
            (f"{year}-01-01", f"{year}-12-31"),
        ).fetchall()
        return [dict(r) for r in rows]

    def backup(self, target_dir: str) -> str:
        os.makedirs(target_dir, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = os.path.join(target_dir, f"backup_car_work_{stamp}.db")
        self.conn.commit()
        shutil.copy2(self.path, target)
        return target

    def close(self) -> None:
        self.conn.close()


def calculate_day(record: Dict[str, object], previous_record: Optional[Dict[str, object]], settings: Dict[str, str]) -> DayResult:
    car_revenue = safe_float(record.get("car_revenue"))
    fuel = safe_float(record.get("fuel"))
    garage = safe_float(record.get("garage"))
    maintenance = safe_float(record.get("maintenance"))
    other_expenses = safe_float(record.get("other_expenses"))
    paid_from_pocket = safe_float(record.get("paid_from_pocket"))
    driver_commission = safe_float(record.get("driver_commission"))
    cycle_amount = safe_float(record.get("cycle_amount"))
    cycle_driver_commission = safe_float(record.get("cycle_driver_commission"))

    my_share = safe_float(settings.get("my_share"), 0.20)
    p1_share = safe_float(settings.get("partner1_share"), 0.40)
    p2_share = safe_float(settings.get("partner2_share"), 0.40)
    admin_default = safe_float(settings.get("admin_default_rate"), 0.10)
    admin_after_repair = safe_float(settings.get("admin_after_repair_rate"), 0.15)
    my_driver = str(settings.get("my_driver", "مصطفى")).strip()

    income = car_revenue + cycle_amount
    expenses = fuel + garage + maintenance + other_expenses + driver_commission + cycle_driver_commission

    prev_income = 0.0
    prev_repair_or_other = 0.0
    if previous_record:
        prev_income = safe_float(previous_record.get("car_revenue")) + safe_float(previous_record.get("cycle_amount"))
        prev_repair_or_other = safe_float(previous_record.get("maintenance")) + safe_float(previous_record.get("other_expenses"))

    if income > 0:
        admin_rate = admin_after_repair if previous_record and prev_income == 0 and prev_repair_or_other > 0 else admin_default
    else:
        admin_rate = 0.0

    admin_value = income * admin_rate
    net = income - expenses - admin_value
    status = "ربح" if net > 0 else "مديونية" if net < 0 else "تعادل"

    driver_name = str(record.get("driver_name", "") or "").strip()
    cycle_driver = str(record.get("cycle_driver", "") or "").strip()
    driver_bonus = driver_commission if driver_name and driver_name == my_driver else 0.0
    cycle_driver_bonus = cycle_driver_commission if cycle_driver and cycle_driver == my_driver else 0.0

    my_net = net * my_share + paid_from_pocket + driver_bonus + cycle_driver_bonus
    partner1_net = net * p1_share
    partner2_net = net * p2_share

    return DayResult(
        income=income,
        expenses=expenses,
        admin_rate=admin_rate,
        admin_value=admin_value,
        net=net,
        status=status,
        debt=max(0.0, -net),
        my_net=my_net,
        partner1_net=partner1_net,
        partner2_net=partner2_net,
        partner1_debt=max(0.0, -partner1_net),
        partner2_debt=max(0.0, -partner2_net),
    )


def calculate_all(records: List[Dict[str, object]], settings: Dict[str, str]) -> Dict[str, DayResult]:
    results: Dict[str, DayResult] = {}
    previous: Optional[Dict[str, object]] = None
    for record in records:
        record_date = str(record["record_date"])
        results[record_date] = calculate_day(record, previous, settings)
        previous = record
    return results


def month_summary(records: List[Dict[str, object]], results: Dict[str, DayResult]) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    by_date = {str(r["record_date"]): r for r in records}
    for month_no, name in enumerate(AR_MONTHS, start=1):
        dates = [d for d in sorted(by_date) if parse_date(d).month == month_no]
        month_records = [by_date[d] for d in dates]
        month_results = [results[d] for d in dates if d in results]
        rows.append(
            {
                "month_no": month_no,
                "month": name,
                "income": sum(x.income for x in month_results),
                "expenses": sum(x.expenses for x in month_results),
                "admin_value": sum(x.admin_value for x in month_results),
                "net": sum(x.net for x in month_results),
                "debt": sum(x.debt for x in month_results),
                "my_net": sum(x.my_net for x in month_results),
                "partner1_net": sum(x.partner1_net for x in month_results),
                "partner2_net": sum(x.partner2_net for x in month_results),
                "maintenance": sum(safe_float(r.get("maintenance")) for r in month_records),
                "driver_commission": sum(safe_float(r.get("driver_commission")) for r in month_records),
                "cycle_amount": sum(safe_float(r.get("cycle_amount")) for r in month_records),
            }
        )
    return rows


class ColorBox(BoxLayout):
    bg_color = ListProperty(rgba(THEME["bg"]))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            from kivy.graphics import Color, Rectangle
            self._canvas_color = Color(*self.bg_color)
            self._canvas_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_canvas, size=self._update_canvas, bg_color=self._update_color)

    def _update_canvas(self, *_args) -> None:
        self._canvas_rect.pos = self.pos
        self._canvas_rect.size = self.size

    def _update_color(self, *_args) -> None:
        self._canvas_color.rgba = self.bg_color


class CarWorkManagerKivyApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = f"{APP_TITLE} - {APP_VERSION}"
        self.current_year = date.today().year
        self.current_month = date.today().month
        self.selected_date = date.today()
        self.active_page = "dashboard"
        self.nav_buttons: Dict[str, MDRaisedButton] = {}
        self.entry_fields: Dict[str, MDTextField] = {}
        self.settings_fields: Dict[str, MDTextField] = {}
        self.preview_labels: Dict[str, MDLabel] = {}
        self.storage: Optional[Storage] = None
        self.content: Optional[ColorBox] = None
        self.body: Optional[GridLayout] = None
        self.year_field: Optional[MDTextField] = None
        self.date_field: Optional[MDTextField] = None
        self.notes_field: Optional[MDTextField] = None
        self.month_field: Optional[MDTextField] = None

    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Blue"
        Window.clearcolor = rgba(THEME["bg"])
        try:
            Window.minimum_width = 1100
            Window.minimum_height = 700
            if sys.platform not in {"android", "ios"}:
                Window.size = (1280, 760)
        except Exception:
            pass

        data_dir = self.get_data_dir()
        self.storage = Storage(os.path.join(data_dir, DB_NAME))

        root = ColorBox(orientation="horizontal", bg_color=rgba(THEME["bg"]), spacing=0)
        self.content = ColorBox(
            orientation="vertical",
            bg_color=rgba(THEME["bg"]),
            padding=[dp(18), dp(16), dp(18), dp(16)],
            spacing=dp(12),
            size_hint=(1, 1),
        )
        sidebar = self.build_sidebar()
        root.add_widget(self.content)
        root.add_widget(sidebar)
        self.show_dashboard()
        return root

    def get_data_dir(self) -> str:
        # Android/Kivy: user_data_dir. Desktop: folder beside script to keep DB easy to find.
        if sys.platform in {"android", "ios"}:
            return self.user_data_dir
        try:
            return os.path.dirname(os.path.abspath(__file__))
        except Exception:
            return os.getcwd()

    def on_stop(self) -> None:
        if self.storage:
            self.storage.close()

    # ----------------------------
    # UI helpers
    # ----------------------------
    def notify(self, message: str) -> None:
        try:
            if Snackbar is not None:
                Snackbar(text=ar(message), duration=2.3).open()
                return
        except Exception:
            pass
        print(message)

    def text_label(
        self,
        text: object,
        font_size: int = 15,
        color: Optional[List[float]] = None,
        bold: bool = False,
        height: Optional[float] = None,
        halign: str = "right",
    ) -> MDLabel:
        lbl = MDLabel(
            text=ar(text),
            halign=halign,
            valign="middle",
            theme_text_color="Custom",
            text_color=color or rgba(THEME["text"]),
            font_style="Body1",
            bold=bold,
            font_size=dp(font_size),
            shorten=True,
        )
        if height is not None:
            lbl.size_hint_y = None
            lbl.height = height
        return lbl

    def card(self, orientation: str = "vertical", bg: str = "card", height: Optional[float] = None, padding: int = 14) -> MDCard:
        c = MDCard(
            orientation=orientation,
            padding=dp(padding),
            spacing=dp(8),
            md_bg_color=rgba(THEME[bg]),
            radius=[dp(20), dp(20), dp(20), dp(20)],
            elevation=1,
        )
        if height is not None:
            c.size_hint_y = None
            c.height = height
        return c

    def button(self, text: str, callback, bg: str = "primary_dark", height: int = 42) -> MDRaisedButton:
        btn = MDRaisedButton(
            text=ar(text),
            size_hint=(1, None),
            height=dp(height),
            md_bg_color=rgba(THEME[bg]),
            theme_text_color="Custom",
            text_color=rgba(THEME["text"]),
            on_release=lambda *_: callback(),
        )
        return btn

    def flat_button(self, text: str, callback, height: int = 38) -> MDFlatButton:
        btn = MDFlatButton(
            text=ar(text),
            size_hint=(1, None),
            height=dp(height),
            theme_text_color="Custom",
            text_color=rgba(THEME["primary"]),
            on_release=lambda *_: callback(),
        )
        return btn

    def input_field(self, label: str, value: object = "", multiline: bool = False) -> MDTextField:
        field = MDTextField(
            text=str(value if value is not None else ""),
            hint_text=ar(label),
            mode="rectangle",
            multiline=multiline,
            halign="right",
            size_hint_y=None,
            height=dp(84 if multiline else 54),
            font_size=dp(15),
        )
        return field

    def add_title(self, parent: BoxLayout, text: str, subtitle: str = "") -> None:
        parent.add_widget(self.text_label(text, font_size=20, bold=True, height=dp(34)))
        if subtitle:
            parent.add_widget(self.text_label(subtitle, font_size=12, color=rgba(THEME["muted"]), height=dp(24)))

    def build_sidebar(self) -> ColorBox:
        sidebar = ColorBox(
            orientation="vertical",
            bg_color=rgba(THEME["sidebar"]),
            size_hint=(None, 1),
            width=dp(260),
            padding=[dp(14), dp(16), dp(14), dp(16)],
            spacing=dp(8),
        )

        logo = self.card(bg="sidebar2", height=dp(128), padding=12)
        logo.add_widget(self.text_label("🚐", font_size=32, height=dp(42), halign="center"))
        logo.add_widget(self.text_label("شغل العربية", font_size=21, bold=True, height=dp(34), halign="center"))
        logo.add_widget(self.text_label(APP_VERSION, font_size=12, color=rgba(THEME["muted"]), height=dp(22), halign="center"))
        sidebar.add_widget(logo)

        items = [
            ("dashboard", "🏠  لوحة التحكم"),
            ("entry", "➕  إدخال يوم"),
            ("records", "📋  السجل اليومي"),
            ("reports", "📊  التقارير"),
            ("settings", "⚙️  الإعدادات"),
            ("backup", "💾  نسخ وتصدير"),
        ]
        for key, label in items:
            btn = MDRaisedButton(
                text=ar(label),
                size_hint=(1, None),
                height=dp(46),
                md_bg_color=rgba(THEME["card2"]),
                theme_text_color="Custom",
                text_color=rgba(THEME["muted"]),
                on_release=lambda _btn, page=key: self.navigate(page),
            )
            self.nav_buttons[key] = btn
            sidebar.add_widget(btn)

        sidebar.add_widget(Widget(size_hint_y=1))
        tip = self.card(bg="cyan_soft", height=dp(116), padding=12)
        tip.add_widget(self.text_label("نصيحة", font_size=17, bold=True, color=rgba(THEME["primary"]), height=dp(30)))
        tip.add_widget(self.text_label("سجل كل يوم أول بأول\nعشان التقارير تطلع دقيقة.", font_size=12, color=rgba(THEME["muted"]), height=dp(50)))
        sidebar.add_widget(tip)
        return sidebar

    def update_nav(self, page: str) -> None:
        self.active_page = page
        for key, btn in self.nav_buttons.items():
            if key == page:
                btn.md_bg_color = rgba(THEME["primary_dark"])
                btn.text_color = rgba(THEME["text"])
            else:
                btn.md_bg_color = rgba(THEME["card2"])
                btn.text_color = rgba(THEME["muted"])

    def navigate(self, page: str) -> None:
        routes = {
            "dashboard": self.show_dashboard,
            "entry": self.show_entry,
            "records": self.show_records,
            "reports": self.show_reports,
            "settings": self.show_settings,
            "backup": self.show_backup,
        }
        routes.get(page, self.show_dashboard)()

    def setup_page(self, page: str, title: str, subtitle: str) -> None:
        if not self.content:
            return
        self.update_nav(page)
        self.content.clear_widgets()

        header = self.card(orientation="horizontal", bg="bg2", height=dp(92), padding=14)
        controls = BoxLayout(orientation="horizontal", size_hint=(0.43, 1), spacing=dp(8))
        self.year_field = self.input_field("السنة", str(self.current_year))
        self.year_field.size_hint_x = None
        self.year_field.width = dp(100)
        controls.add_widget(self.button("تحديث", self.refresh_current, bg="primary_dark", height=42))
        controls.add_widget(self.button("السنة الحالية", self.set_current_year, bg="card3", height=42))
        controls.add_widget(self.year_field)

        title_box = BoxLayout(orientation="vertical", size_hint=(0.57, 1))
        title_box.add_widget(self.text_label(title, font_size=24, bold=True, height=dp(40)))
        title_box.add_widget(self.text_label(subtitle, font_size=13, color=rgba(THEME["muted"]), height=dp(28)))
        header.add_widget(controls)
        header.add_widget(title_box)
        self.content.add_widget(header)

        scroll = ScrollView(size_hint=(1, 1), bar_width=dp(6))
        self.body = GridLayout(cols=1, spacing=dp(12), padding=[0, 0, 0, dp(16)], size_hint_y=None)
        self.body.bind(minimum_height=self.body.setter("height"))
        scroll.add_widget(self.body)
        self.content.add_widget(scroll)

    def refresh_current(self) -> None:
        if self.year_field:
            try:
                self.current_year = int(self.year_field.text.strip())
            except Exception:
                self.year_field.text = str(self.current_year)
                self.notify("اكتب السنة بشكل صحيح")
        self.navigate(self.active_page)

    def set_current_year(self) -> None:
        self.current_year = date.today().year
        if self.year_field:
            self.year_field.text = str(self.current_year)
        self.navigate(self.active_page)

    # ----------------------------
    # Data helpers
    # ----------------------------
    def load_year(self) -> Tuple[List[Dict[str, object]], Dict[str, DayResult], List[Dict[str, object]]]:
        assert self.storage is not None
        records = self.storage.year_records(self.current_year)
        settings = self.storage.get_settings()
        results = calculate_all(records, settings)
        months = month_summary(records, results)
        return records, results, months

    def ensure_body(self) -> GridLayout:
        assert self.body is not None
        return self.body

    # ----------------------------
    # Dashboard
    # ----------------------------
    def metric_card(self, title: str, value: str, hint: str, color_name: str) -> MDCard:
        c = self.card(bg="card", height=dp(132), padding=14)
        c.add_widget(self.text_label(title, font_size=13, color=rgba(THEME["muted"]), height=dp(28)))
        c.add_widget(self.text_label(value, font_size=24, bold=True, color=rgba(THEME[color_name]), height=dp(44)))
        c.add_widget(self.text_label(hint, font_size=11, color=rgba(THEME["muted2"]), height=dp(26)))
        return c

    def show_dashboard(self) -> None:
        self.setup_page("dashboard", "لوحة التحكم", f"ملخص سنة {self.current_year} — نفس الحسابات القديمة بواجهة KivyMD")
        body = self.ensure_body()
        records, results, months = self.load_year()
        total_income = sum(x.income for x in results.values())
        total_expenses = sum(x.expenses for x in results.values())
        total_net = sum(x.net for x in results.values())
        total_debt = sum(x.debt for x in results.values())
        active_days = sum(1 for r in records if safe_float(r.get("car_revenue")) or safe_float(r.get("cycle_amount")) or safe_float(r.get("maintenance")) or safe_float(r.get("other_expenses")))
        best_month = max(months, key=lambda m: m["net"])

        grid = GridLayout(cols=4, spacing=dp(10), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        grid.add_widget(self.metric_card("إجمالي الإيراد", f"{money(total_income)} ج", "إيراد العربية + الدورة", "primary"))
        grid.add_widget(self.metric_card("إجمالي المصاريف", f"{money(total_expenses)} ج", "بنزين + جراج + صيانة", "orange"))
        grid.add_widget(self.metric_card("صافي السنة", f"{money(total_net)} ج", "بعد الإدارة والمصاريف", "green" if total_net >= 0 else "red"))
        grid.add_widget(self.metric_card("أيام عليها شغل", str(active_days), "أيام بها حركة", "purple"))
        body.add_widget(grid)

        lower = GridLayout(cols=2, spacing=dp(12), size_hint_y=None)
        lower.bind(minimum_height=lower.setter("height"))

        month_card = self.card(bg="card", padding=14)
        month_card.size_hint_y = None
        month_card.height = dp(580)
        self.add_title(month_card, "أداء الشهور", "شريط سريع لصافي كل شهر")
        max_abs = max([abs(float(m["net"])) for m in months] + [1.0])
        for m in months:
            row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(34), spacing=dp(8))
            amount_color = "green" if m["net"] >= 0 else "red"
            row.add_widget(self.text_label(f"{money(float(m['net']))}", font_size=12, color=rgba(THEME[amount_color]), height=dp(30), halign="left"))
            bar = ProgressBar(max=1, value=clamp(abs(float(m["net"])) / max_abs), size_hint=(1, None), height=dp(16))
            row.add_widget(bar)
            row.add_widget(self.text_label(str(m["month"]), font_size=12, color=rgba(THEME["muted"]), height=dp(30)))
            month_card.add_widget(row)
        lower.add_widget(month_card)

        quick_card = self.card(bg="card", padding=14)
        quick_card.size_hint_y = None
        quick_card.height = dp(580)
        self.add_title(quick_card, "نظرة سريعة", "أهم المؤشرات الحالية")
        today_iso = date.today().isoformat()
        today_result = results.get(today_iso)
        highlights = [
            ("أفضل شهر", best_month["month"], f"{money(float(best_month['net']))} ج", "green" if best_month["net"] >= 0 else "red"),
            ("إجمالي المديونية", "خسائر أيام منفصلة", f"{money(total_debt)} ج", "red"),
            ("اليوم", day_name(today_iso), today_iso, "primary"),
        ]
        if today_result:
            highlights.append(("صافي اليوم", today_result.status, f"{money(today_result.net)} ج", "green" if today_result.net >= 0 else "red"))
        for title, sub, value, color in highlights:
            mini = self.card(bg="card2", height=dp(94), padding=10)
            mini.add_widget(self.text_label(title, font_size=12, color=rgba(THEME["muted"]), height=dp(24)))
            mini.add_widget(self.text_label(value, font_size=21, bold=True, color=rgba(THEME[color]), height=dp(34)))
            mini.add_widget(self.text_label(sub, font_size=11, color=rgba(THEME["muted2"]), height=dp(22)))
            quick_card.add_widget(mini)
        actions = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(48), spacing=dp(8))
        actions.add_widget(self.button("عرض السجل", lambda: self.navigate("records"), bg="card3"))
        actions.add_widget(self.button("إدخال يوم جديد", lambda: self.navigate("entry"), bg="primary_dark"))
        quick_card.add_widget(actions)
        lower.add_widget(quick_card)
        body.add_widget(lower)

    # ----------------------------
    # Entry page
    # ----------------------------
    def show_entry(self) -> None:
        self.setup_page("entry", "إدخال يوم", "كل بيانات اليوم في شاشة واحدة مع حساب فوري قبل الحفظ")
        body = self.ensure_body()
        root = GridLayout(cols=2, spacing=dp(12), size_hint_y=None)
        root.bind(minimum_height=root.setter("height"))

        preview = self.card(bg="card", padding=14)
        preview.size_hint_y = None
        preview.height = dp(720)
        self.add_title(preview, "النتيجة الفورية", "تتحدث تلقائيًا أثناء الكتابة")
        self.preview_labels = {}
        for key, label, color in [
            ("income", "الإيراد", "primary"),
            ("expenses", "المصاريف", "orange"),
            ("admin", "الإدارة", "purple"),
            ("net", "الصافي", "green"),
            ("my_net", "نصيبي", "primary"),
            ("p1", "الشريك 1", "muted"),
            ("p2", "الشريك 2", "muted"),
        ]:
            chip = self.card(bg="card2", height=dp(76), padding=8)
            chip.add_widget(self.text_label(label, font_size=12, color=rgba(THEME["muted"]), height=dp(24)))
            val = self.text_label("0.00 ج", font_size=18, bold=True, color=rgba(THEME[color]), height=dp(34))
            chip.add_widget(val)
            self.preview_labels[key] = val
            preview.add_widget(chip)
        self.status_label = self.text_label("جاهز للحساب", font_size=17, bold=True, color=rgba(THEME["muted"]), height=dp(44), halign="center")
        preview.add_widget(self.status_label)

        form = self.card(bg="card", padding=14)
        form.size_hint_y = None
        form.height = dp(720)
        self.add_title(form, "بيانات اليوم", "التاريخ بصيغة YYYY-MM-DD")
        date_bar = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(58), spacing=dp(8))
        date_bar.add_widget(self.button("اليوم", self.load_today_entry, bg="primary_dark"))
        date_bar.add_widget(self.button("التالي ◀", lambda: self.shift_selected_day(1), bg="card3"))
        self.date_field = self.input_field("التاريخ", self.selected_date.isoformat())
        self.date_field.bind(text=lambda *_: self.update_entry_preview())
        date_bar.add_widget(self.date_field)
        date_bar.add_widget(self.button("▶ السابق", lambda: self.shift_selected_day(-1), bg="card3"))
        form.add_widget(date_bar)

        fields_grid = GridLayout(cols=2, spacing=dp(10), size_hint_y=None)
        fields_grid.bind(minimum_height=fields_grid.setter("height"))
        specs = [
            ("car_revenue", "إيراد العربية"),
            ("cycle_amount", "مبلغ الدورة"),
            ("fuel", "بنزين"),
            ("garage", "جراج"),
            ("maintenance", "صيانة"),
            ("other_expenses", "مصروفات أخرى"),
            ("driver_commission", "كمسيون السواق"),
            ("driver_name", "اسم السواق"),
            ("cycle_driver_commission", "كمسيون سواق الدورة"),
            ("cycle_driver", "سواق الدورة"),
            ("paid_from_pocket", "مدفوع من جيبي"),
        ]
        self.entry_fields = {}
        for key, label in specs:
            field = self.input_field(label, "")
            field.bind(text=lambda *_: self.update_entry_preview())
            self.entry_fields[key] = field
            fields_grid.add_widget(field)
        form.add_widget(fields_grid)

        self.notes_field = self.input_field("ملاحظات", "", multiline=True)
        form.add_widget(self.notes_field)
        actions = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(50), spacing=dp(8))
        actions.add_widget(self.button("تفريغ اليوم", self.reset_entry, bg="red_soft"))
        actions.add_widget(self.button("حفظ اليوم", self.save_entry, bg="primary_dark"))
        form.add_widget(actions)

        root.add_widget(preview)
        root.add_widget(form)
        body.add_widget(root)
        self.load_entry_date(self.selected_date.isoformat(), rebuild=False)

    def shift_selected_day(self, days: int) -> None:
        try:
            base = parse_date(self.date_field.text if self.date_field else self.selected_date.isoformat())
        except Exception:
            base = self.selected_date
        self.selected_date = base + timedelta(days=days)
        self.load_entry_date(self.selected_date.isoformat(), rebuild=False)

    def load_today_entry(self) -> None:
        self.selected_date = date.today()
        self.load_entry_date(self.selected_date.isoformat(), rebuild=False)

    def load_entry_date(self, date_text: str, rebuild: bool = True) -> None:
        assert self.storage is not None
        try:
            self.selected_date = parse_date(date_text)
        except Exception:
            self.notify("تاريخ غير صحيح. اكتب التاريخ بهذا الشكل: YYYY-MM-DD")
            return
        if rebuild and self.active_page != "entry":
            self.show_entry()
            return
        if self.date_field:
            self.date_field.text = self.selected_date.isoformat()
        record = self.storage.get_record(self.selected_date.isoformat())
        for key, field in self.entry_fields.items():
            value = record.get(key, "")
            if isinstance(value, float):
                value = str(int(value)) if value.is_integer() else str(value)
            field.text = str(value or "")
        if self.notes_field:
            self.notes_field.text = str(record.get("notes", "") or "")
        self.update_entry_preview()

    def current_entry_record(self) -> Dict[str, object]:
        record = {"record_date": self.date_field.text.strip() if self.date_field else self.selected_date.isoformat()}
        for key, field in self.entry_fields.items():
            record[key] = field.text
        record["notes"] = self.notes_field.text.strip() if self.notes_field else ""
        return record

    def update_entry_preview(self) -> None:
        if not self.preview_labels or self.storage is None:
            return
        record = self.current_entry_record()
        try:
            selected = parse_date(str(record.get("record_date", date.today().isoformat())))
        except Exception:
            selected = date.today()
        previous_record = self.storage.get_record((selected - timedelta(days=1)).isoformat())
        result = calculate_day(record, previous_record, self.storage.get_settings())
        values = {
            "income": result.income,
            "expenses": result.expenses,
            "admin": result.admin_value,
            "net": result.net,
            "my_net": result.my_net,
            "p1": result.partner1_net,
            "p2": result.partner2_net,
        }
        for key, val in values.items():
            self.preview_labels[key].text = ar(f"{money(val)} ج")
        net_color = "green" if result.net > 0 else "red" if result.net < 0 else "muted"
        self.preview_labels["net"].text_color = rgba(THEME[net_color])
        if hasattr(self, "status_label"):
            self.status_label.text = ar(f"الحالة: {result.status} • الإدارة {pct(result.admin_rate)}")
            self.status_label.text_color = rgba(THEME[net_color])

    def save_entry(self) -> None:
        assert self.storage is not None
        try:
            record = self.current_entry_record()
            parsed = parse_date(str(record["record_date"]))
            self.storage.save_record(record)
            self.current_year = parsed.year
            self.selected_date = parsed
            self.notify("تم حفظ بيانات اليوم بنجاح")
            self.update_entry_preview()
        except Exception as exc:
            self.notify(f"تعذر الحفظ: {exc}")

    def reset_entry(self) -> None:
        assert self.storage is not None
        try:
            record_date = self.date_field.text.strip() if self.date_field else self.selected_date.isoformat()
            parse_date(record_date)
            self.storage.reset_record(record_date)
            self.load_entry_date(record_date, rebuild=False)
            self.notify("تم تفريغ بيانات اليوم")
        except Exception:
            self.notify("اكتب التاريخ بشكل صحيح أولًا")

    # ----------------------------
    # Records
    # ----------------------------
    def show_records(self) -> None:
        self.setup_page("records", "السجل اليومي", "عرض أيام الشهر وتعديل أي يوم بسرعة")
        body = self.ensure_body()
        controls = self.card(orientation="horizontal", bg="card", height=dp(78), padding=12)
        controls.add_widget(self.button("تصدير CSV", self.export_records_csv, bg="primary_dark"))
        controls.add_widget(self.button("الشهر الحالي", self.set_current_month_filter, bg="card3"))
        controls.add_widget(self.button("الشهر التالي", lambda: self.change_month_filter(1), bg="card3"))
        self.month_field = self.input_field("رقم الشهر", str(self.current_month))
        self.month_field.size_hint_x = None
        self.month_field.width = dp(120)
        controls.add_widget(self.month_field)
        controls.add_widget(self.button("الشهر السابق", lambda: self.change_month_filter(-1), bg="card3"))
        body.add_widget(controls)

        self.populate_records_list(body)

    def selected_month_number(self) -> int:
        try:
            val = int(self.month_field.text.strip()) if self.month_field else self.current_month
            if 1 <= val <= 12:
                return val
        except Exception:
            pass
        return self.current_month

    def set_current_month_filter(self) -> None:
        self.current_month = date.today().month
        self.show_records()

    def change_month_filter(self, delta: int) -> None:
        month_no = self.selected_month_number() + delta
        if month_no < 1:
            month_no = 12
        if month_no > 12:
            month_no = 1
        self.current_month = month_no
        self.show_records()

    def populate_records_list(self, body: GridLayout) -> None:
        records, results, _ = self.load_year()
        month_no = self.selected_month_number()
        title = self.card(bg="card", padding=12)
        title.size_hint_y = None
        title.height = dp(620)
        self.add_title(title, f"سجل شهر {AR_MONTHS[month_no - 1]}", "دبل كليك في النسخة القديمة تحول هنا إلى زر تعديل واضح")

        header = GridLayout(cols=7, spacing=dp(6), size_hint_y=None, height=dp(34))
        for h in ["تعديل", "الصافي", "الإدارة", "المصاريف", "الإيراد", "اليوم", "التاريخ"]:
            header.add_widget(self.text_label(h, font_size=12, bold=True, color=rgba(THEME["primary"]), halign="center"))
        title.add_widget(header)

        rows = GridLayout(cols=1, spacing=dp(6), size_hint_y=None)
        rows.bind(minimum_height=rows.setter("height"))
        for record in records:
            d = str(record["record_date"])
            if parse_date(d).month != month_no:
                continue
            res = results[d]
            row_card = self.card(orientation="horizontal", bg="card2", height=dp(44), padding=6)
            row_card.add_widget(self.flat_button("تعديل", lambda dd=d: self.edit_record(dd), height=32))
            row_card.add_widget(self.text_label(money(res.net), font_size=12, color=rgba(THEME["green"] if res.net >= 0 else THEME["red"]), halign="center"))
            row_card.add_widget(self.text_label(money(res.admin_value), font_size=12, color=rgba(THEME["muted"]), halign="center"))
            row_card.add_widget(self.text_label(money(res.expenses), font_size=12, color=rgba(THEME["muted"]), halign="center"))
            row_card.add_widget(self.text_label(money(res.income), font_size=12, color=rgba(THEME["muted"]), halign="center"))
            row_card.add_widget(self.text_label(day_name(d), font_size=12, color=rgba(THEME["muted"]), halign="center"))
            row_card.add_widget(self.text_label(d, font_size=12, color=rgba(THEME["text"]), halign="center"))
            rows.add_widget(row_card)
        scroll = ScrollView(size_hint=(1, 1), bar_width=dp(5))
        scroll.add_widget(rows)
        title.add_widget(scroll)
        body.add_widget(title)

    def edit_record(self, record_date: str) -> None:
        self.selected_date = parse_date(record_date)
        self.show_entry()

    def export_records_csv(self) -> None:
        month_no = self.selected_month_number()
        records, results, _ = self.load_year()
        export_dir = os.path.join(self.get_data_dir(), "exports")
        os.makedirs(export_dir, exist_ok=True)
        path = os.path.join(export_dir, f"سجل_شغل_العربية_{self.current_year}_{month_no:02d}.csv")
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["التاريخ", "اليوم", "إيراد", "مصاريف", "الإدارة", "الصافي", "الحالة", "نصيبي", "الشريك1", "الشريك2", "ملاحظات"])
                for r in records:
                    d = str(r["record_date"])
                    if parse_date(d).month != month_no:
                        continue
                    res = results[d]
                    writer.writerow([d, day_name(d), res.income, res.expenses, res.admin_value, res.net, res.status, res.my_net, res.partner1_net, res.partner2_net, r.get("notes", "")])
            self.notify(f"تم تصدير الملف: {path}")
        except Exception as exc:
            self.notify(f"تعذر التصدير: {exc}")

    # ----------------------------
    # Reports
    # ----------------------------
    def show_reports(self) -> None:
        self.setup_page("reports", "التقارير", "ملخص شهري وسنوي بنظرة مالية واضحة")
        body = self.ensure_body()
        _records, _results, months = self.load_year()
        total_income = sum(float(m["income"]) for m in months)
        total_expenses = sum(float(m["expenses"]) for m in months)
        total_admin = sum(float(m["admin_value"]) for m in months)
        total_net = sum(float(m["net"]) for m in months)

        grid = GridLayout(cols=4, spacing=dp(10), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        grid.add_widget(self.metric_card("إيراد السنة", f"{money(total_income)} ج", "كل الشهور", "primary"))
        grid.add_widget(self.metric_card("مصروفات السنة", f"{money(total_expenses)} ج", "كل المصاريف", "orange"))
        grid.add_widget(self.metric_card("إدارة السنة", f"{money(total_admin)} ج", "حسب النسبة", "purple"))
        grid.add_widget(self.metric_card("صافي السنة", f"{money(total_net)} ج", "بعد الخصم", "green" if total_net >= 0 else "red"))
        body.add_widget(grid)

        table = self.card(bg="card", padding=12)
        table.size_hint_y = None
        table.height = dp(620)
        self.add_title(table, "جدول الشهور", "الإيراد والمصاريف والإدارة والصافي")
        header = GridLayout(cols=9, spacing=dp(5), size_hint_y=None, height=dp(34))
        for h in ["الشريك2", "الشريك1", "نصيبي", "مديونية", "الصافي", "الإدارة", "المصاريف", "الإيراد", "الشهر"]:
            header.add_widget(self.text_label(h, font_size=11, bold=True, color=rgba(THEME["primary"]), halign="center"))
        table.add_widget(header)
        rows = GridLayout(cols=1, spacing=dp(6), size_hint_y=None)
        rows.bind(minimum_height=rows.setter("height"))
        for m in months:
            row = self.card(orientation="horizontal", bg="card2", height=dp(44), padding=6)
            vals = [
                money(float(m["partner2_net"])), money(float(m["partner1_net"])), money(float(m["my_net"])),
                money(float(m["debt"])), money(float(m["net"])), money(float(m["admin_value"])),
                money(float(m["expenses"])), money(float(m["income"])), str(m["month"]),
            ]
            for val in vals:
                row.add_widget(self.text_label(val, font_size=11, color=rgba(THEME["text"]), halign="center"))
            rows.add_widget(row)
        scroll = ScrollView(size_hint=(1, 1), bar_width=dp(5))
        scroll.add_widget(rows)
        table.add_widget(scroll)
        body.add_widget(table)

    # ----------------------------
    # Settings
    # ----------------------------
    def show_settings(self) -> None:
        self.setup_page("settings", "الإعدادات", "تعديل نسب الشراكة والإدارة والجراج والسواق الأساسي")
        body = self.ensure_body()
        assert self.storage is not None
        settings = self.storage.get_settings()

        panel = self.card(bg="card", padding=14)
        panel.size_hint_y = None
        panel.height = dp(560)
        self.add_title(panel, "إعدادات الحساب", "اكتب النسب كأرقام عشرية مثل 0.20")

        fields_grid = GridLayout(cols=2, spacing=dp(10), size_hint_y=None)
        fields_grid.bind(minimum_height=fields_grid.setter("height"))
        specs = [
            ("my_share", "نصيبي"),
            ("partner1_share", "نصيب الشريك 1"),
            ("partner2_share", "نصيب الشريك 2"),
            ("admin_default_rate", "نسبة الإدارة العادية"),
            ("admin_after_repair_rate", "نسبة الإدارة بعد يوم صيانة"),
            ("daily_garage", "الجراج اليومي"),
            ("my_driver", "السواق الأساسي"),
            ("driver_options", "قائمة السواقين"),
        ]
        self.settings_fields = {}
        for key, label in specs:
            field = self.input_field(label, settings.get(key, ""))
            self.settings_fields[key] = field
            fields_grid.add_widget(field)
        panel.add_widget(fields_grid)

        actions = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(50), spacing=dp(8))
        actions.add_widget(self.button("استرجاع الافتراضي", self.reset_settings_defaults, bg="card3"))
        actions.add_widget(self.button("حفظ الإعدادات", self.save_settings, bg="primary_dark"))
        panel.add_widget(actions)
        body.add_widget(panel)

    def save_settings(self) -> None:
        assert self.storage is not None
        data = {k: v.text.strip() for k, v in self.settings_fields.items()}
        share_total = safe_float(data.get("my_share")) + safe_float(data.get("partner1_share")) + safe_float(data.get("partner2_share"))
        if abs(share_total - 1.0) > 0.01:
            self.notify(f"تنبيه: مجموع نسب الشراكة = {share_total:.2f} وليس 1.00. تم الحفظ رغم ذلك")
        self.storage.save_settings(data)
        self.notify("تم حفظ الإعدادات بنجاح")

    def reset_settings_defaults(self) -> None:
        assert self.storage is not None
        self.storage.save_settings(DEFAULT_SETTINGS.copy())
        self.notify("تم استرجاع الإعدادات الافتراضية")
        self.show_settings()

    # ----------------------------
    # Backup / export
    # ----------------------------
    def show_backup(self) -> None:
        self.setup_page("backup", "نسخ وتصدير", "احتفظ بنسخة من قاعدة البيانات أو صدّر السنة CSV")
        body = self.ensure_body()
        panel = GridLayout(cols=2, spacing=dp(12), size_hint_y=None)
        panel.bind(minimum_height=panel.setter("height"))

        backup_card = self.card(bg="card", height=dp(210), padding=14)
        self.add_title(backup_card, "نسخة احتياطية", "يحفظ نسخة كاملة من قاعدة البيانات")
        backup_card.add_widget(self.button("إنشاء نسخة احتياطية", self.create_backup, bg="primary_dark"))
        panel.add_widget(backup_card)

        export_card = self.card(bg="card", height=dp(210), padding=14)
        self.add_title(export_card, "تصدير السنة", "يصدر السنة الحالية كلها إلى CSV")
        export_card.add_widget(self.button("تصدير السنة CSV", self.export_year_csv, bg="card3"))
        panel.add_widget(export_card)
        body.add_widget(panel)

    def create_backup(self) -> None:
        assert self.storage is not None
        try:
            backup_dir = os.path.join(self.get_data_dir(), "backups")
            target = self.storage.backup(backup_dir)
            self.notify(f"تم إنشاء النسخة الاحتياطية: {target}")
        except Exception as exc:
            self.notify(f"تعذر إنشاء النسخة: {exc}")

    def export_year_csv(self) -> None:
        records, results, _months = self.load_year()
        export_dir = os.path.join(self.get_data_dir(), "exports")
        os.makedirs(export_dir, exist_ok=True)
        path = os.path.join(export_dir, f"سجل_شغل_العربية_{self.current_year}.csv")
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["التاريخ", "اليوم", "إيراد", "بنزين", "جراج", "صيانة", "مصروفات أخرى", "كمسيون", "دورة", "إدارة", "صافي", "نصيبي", "الشريك1", "الشريك2", "ملاحظات"])
                for r in records:
                    d = str(r["record_date"])
                    res = results[d]
                    writer.writerow([
                        d, day_name(d), safe_float(r.get("car_revenue")), safe_float(r.get("fuel")),
                        safe_float(r.get("garage")), safe_float(r.get("maintenance")), safe_float(r.get("other_expenses")),
                        safe_float(r.get("driver_commission")), safe_float(r.get("cycle_amount")), res.admin_value,
                        res.net, res.my_net, res.partner1_net, res.partner2_net, r.get("notes", ""),
                    ])
            self.notify(f"تم تصدير الملف: {path}")
        except Exception as exc:
            self.notify(f"تعذر التصدير: {exc}")


def main() -> None:
    CarWorkManagerKivyApp().run()


if __name__ == "__main__":
    main()
