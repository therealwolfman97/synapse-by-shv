import copy
import json
import os
import uuid
from datetime import datetime
from functools import partial

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import FadeTransition, ScreenManager, Screen
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

try:
    from kivy.core.clipboard import Clipboard
except Exception:
    Clipboard = None


# ----------------------------
# Theme
# ----------------------------
AMOLED = (0, 0, 0, 1)
CARD = (0.05, 0.07, 0.10, 1)
CARD_2 = (0.08, 0.11, 0.15, 1)
ACCENT = (0.00, 0.72, 0.62, 1)
TEXT = (0.93, 0.96, 0.98, 1)
MUTED = (0.68, 0.73, 0.78, 1)
RED = (0.90, 0.28, 0.28, 1)
GOLD = (0.94, 0.78, 0.18, 1)
GREEN = (0.16, 0.74, 0.42, 1)
YELLOW = (0.95, 0.79, 0.20, 1)
LIGHT_RED = (0.94, 0.50, 0.50, 1)
DARK_TEXT = (0.06, 0.08, 0.10, 1)

try:
    Window.clearcolor = AMOLED
except Exception:
    pass


# ----------------------------
# Helpers
# ----------------------------
def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def safe_mkdir(path):
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        pass


def read_text_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_text_file(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def get_root_storage_path():
    candidates = [
        "/storage/emulated/0",
        "/sdcard",
        os.path.expanduser("~/Downloads"),
        os.path.expanduser("~"),
        os.getcwd(),
    ]
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return os.getcwd()


def get_export_root_dir():
    export_dir = os.path.join(get_root_storage_path(), "Synapse by SHV", "Data Exports")
    safe_mkdir(export_dir)
    return export_dir


def get_file_picker_start_path():
    root = get_root_storage_path()
    return root if os.path.exists(root) else os.getcwd()


def make_unique_path(directory, filename):
    safe_mkdir(directory)
    base, ext = os.path.splitext(filename)
    candidate = os.path.join(directory, filename)
    counter = 1
    while os.path.exists(candidate):
        candidate = os.path.join(directory, f"{base}_{counter}{ext}")
        counter += 1
    return candidate


def apply_solid_bg(widget, color=AMOLED, radius=0):
    from kivy.graphics import Color, Rectangle, RoundedRectangle
    with widget.canvas.before:
        widget._solid_bg_color = Color(*color)
        if radius and float(radius) > 0:
            widget._solid_bg_rect = RoundedRectangle(pos=widget.pos, size=widget.size, radius=[radius] * 4)
        else:
            widget._solid_bg_rect = Rectangle(pos=widget.pos, size=widget.size)

    def _update(*_args):
        widget._solid_bg_rect.pos = widget.pos
        widget._solid_bg_rect.size = widget.size
        if hasattr(widget._solid_bg_rect, "radius"):
            widget._solid_bg_rect.radius = [radius] * 4
        widget._solid_bg_color.rgba = color

    widget.bind(pos=_update, size=_update)
    Clock.schedule_once(_update, 0)
    return widget


def month_name_options():
    return ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def future_status_options():
    return ["In Process", "Done", "Discontinuing"]

def project_status_options():
    return ["Planning", "Active", "Waiting", "Completed"]


def priority_options():
    return ["Low", "Medium", "High"]


def lead_stage_options():
    return ["Lead", "Interested", "Meeting Done", "Proposal Sent", "Won", "Lost"]


def build_type_options():
    return ["Debug APK", "Release APK", "AAB", "Other"]


def build_result_options():
    return ["Success", "Failed"]


def project_status_color(status):
    mapping = {
        "Planning": YELLOW,
        "Active": ACCENT,
        "Waiting": LIGHT_RED,
        "Completed": GREEN,
    }
    return mapping.get((status or "").strip(), ACCENT)


def project_status_text_color(status):
    if (status or "").strip() == "Planning":
        return DARK_TEXT
    return TEXT


def priority_color(priority):
    mapping = {
        "Low": GREEN,
        "Medium": YELLOW,
        "High": LIGHT_RED,
    }
    return mapping.get((priority or "").strip(), ACCENT)


def priority_text_color(priority):
    if (priority or "").strip() == "Medium":
        return DARK_TEXT
    return TEXT


def lead_stage_color(stage):
    mapping = {
        "Lead": MUTED,
        "Interested": YELLOW,
        "Meeting Done": ACCENT,
        "Proposal Sent": GOLD,
        "Won": GREEN,
        "Lost": LIGHT_RED,
    }
    return mapping.get((stage or "").strip(), CARD_2)


def lead_stage_text_color(stage):
    if (stage or "").strip() in ("Interested", "Proposal Sent"):
        return DARK_TEXT
    return TEXT


def safe_lower(value):
    return str(value or "").strip().lower()


def parse_datetime_maybe(text):
    raw = str(text or "").strip()
    if not raw:
        return None
    fmts = [
        "%Y-%b-%d %H:%M",
        "%Y-%m-%d %H:%M",
        "%Y-%b-%d %I:%M %p",
        "%Y-%m-%d %I:%M %p",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
    ]
    for fmt in fmts:
        try:
            return datetime.strptime(raw, fmt)
        except Exception:
            pass
    return None


def followup_is_overdue(call):
    followup = parse_datetime_maybe(call.get("followup_date"))
    if not followup:
        return False
    stage = call.get("lead_stage", "")
    if stage in ("Won", "Lost"):
        return False
    return followup < datetime.now()


def latest_stamp(*values):
    best = None
    best_raw = ""
    for value in values:
        parsed = parse_datetime_maybe(value)
        if parsed and (best is None or parsed > best):
            best = parsed
            best_raw = str(value)
    return best_raw



def mix_color(base_rgba, accent_rgba, weight=0.18):
    br, bg, bb, _ = base_rgba
    ar, ag, ab, _ = accent_rgba
    return (
        br * (1 - weight) + ar * weight,
        bg * (1 - weight) + ag * weight,
        bb * (1 - weight) + ab * weight,
        1,
    )


def future_status_color(status):
    mapping = {
        "In Process": YELLOW,
        "Done": GREEN,
        "Discontinuing": LIGHT_RED,
    }
    return mapping.get((status or "").strip(), ACCENT)


def future_status_text_color(status):
    if (status or "").strip() == "In Process":
        return DARK_TEXT
    return TEXT


def future_status_card_color(status):
    return mix_color(CARD, future_status_color(status), 0.22)


def build_call_date_string(year_text, month_text, day_text, mode_text, hour_text, minute_text, am_pm_text):
    month = str(month_text).strip() or "Jan"
    day = str(day_text).strip() or "01"
    year = str(year_text).strip() or str(datetime.now().year)
    minute = str(minute_text).strip() or "00"
    hour = str(hour_text).strip() or "00"
    if mode_text == "24h":
        return f"{year}-{month}-{day.zfill(2)} {hour.zfill(2)}:{minute.zfill(2)}"
    return f"{year}-{month}-{day.zfill(2)} {hour}:{minute.zfill(2)} {am_pm_text}"


CHECKLIST_TEMPLATE_GUIDE = """# Synapse by SHV checklist template
# Give this template to ChatGPT and ask it to create a checklist .py file in this exact format.

CHECKLIST_TEMPLATE = {
    "name": "Your Checklist Name",
    "description": "Optional short description",
    "items": [
        "Simple checklist item",
        {"entry": "Checklist item with notes", "notes": "Optional notes"},
        {"entry": "Another checklist item", "notes": "Keep notes short and useful"},
    ],
}

# Alternative format also supported:
# def get_checklist_template():
#     return CHECKLIST_TEMPLATE
""".strip()


GITHUB_APK_BUILD_GUIDE = """GitHub APK Build Guide

1. Create a new GitHub repository.

2. Upload your Python/Kivy files:
- main.py
- any .kv files
- images/assets/icons

3. Generate these with this app:
- buildozer.spec
- .github/workflows/build.yml
- .gitignore
- requirements.txt

4. Put them in the repo:
- buildozer.spec in root
- build.yml in .github/workflows/

5. Push to main branch.

6. Open GitHub Actions.

7. Wait for the workflow to build the APK.

8. Download the artifact from the successful run.

Tips:
- keep package.name lowercase
- java 17 is a good default
- ubuntu-22.04 is a good default
- arm64-v8a is often the safest architecture""".strip()


def get_file_generator_root_dir():
    fg_dir = os.path.join(get_root_storage_path(), "Synapse by SHV", "File Generator")
    safe_mkdir(fg_dir)
    return fg_dir


def get_github_apk_root_dir():
    fg_dir = os.path.join(get_file_generator_root_dir(), "GitHub APK File Generator")
    safe_mkdir(fg_dir)
    return fg_dir


def get_fg_history_path():
    return os.path.join(get_github_apk_root_dir(), "history.txt")


def add_fg_history(entry):
    history_path = get_fg_history_path()
    with open(history_path, "a", encoding="utf-8") as f:
        f.write(entry + "\n")


def read_fg_history():
    history_path = get_fg_history_path()
    if not os.path.exists(history_path):
        return "No history yet."
    with open(history_path, "r", encoding="utf-8") as f:
        data = f.read().strip()
    return data if data else "No history yet."


def clear_fg_history():
    history_path = get_fg_history_path()
    with open(history_path, "w", encoding="utf-8") as f:
        f.write("")


def build_buildozer_content(title, package_name, package_domain, version, requirements,
                            permissions, orientation, android_api, min_api, ndk_api, archs):
    return f"""[app]

title = {title}
package.name = {package_name}
package.domain = {package_domain}

source.dir = .
source.include_exts = py,png,jpg,kv,atlas

version = {version}
requirements = {requirements}

orientation = {orientation}
fullscreen = 0

android.permissions = {permissions}
android.api = {android_api}
android.minapi = {min_api}
android.ndk_api = {ndk_api}
android.archs = {archs}
android.accept_sdk_license = True
android.enable_androidx = True

[buildozer]

log_level = 2
warn_on_root = 1
"""


def build_workflow_content(workflow_name, branch, python_version, ubuntu_version, java_version, build_cmd):
    return f"""name: {workflow_name}

on:
  push:
    branches:
      - {branch}
  workflow_dispatch:

jobs:
  build:
    runs-on: {ubuntu_version}

    steps:
      - name: Checkout source
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "{python_version}"

      - name: Set up Java {java_version}
        uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: "{java_version}"

      - name: Install Buildozer
        run: |
          python -m pip install --upgrade pip
          pip install buildozer Cython==0.29.33

      - name: Build APK
        run: |
          {build_cmd}

      - name: Upload APK
        uses: actions/upload-artifact@v4
        with:
          name: apk-package
          path: |
            bin/*.apk
            bin/*.aab
"""


# ----------------------------
# Styled widgets
# ----------------------------
class RoundedButton(Button):
    def __init__(self, fill_color=ACCENT, corner_radius=None, **kwargs):
        defaults = dict(
            size_hint_y=None,
            height=dp(52),
            background_normal="",
            background_down="",
            background_color=(0, 0, 0, 0),
            border=(0, 0, 0, 0),
            color=TEXT,
            font_size=sp(15),
            bold=True,
            halign="center",
            valign="middle",
        )
        defaults.update(kwargs)
        super().__init__(**defaults)
        self.fill_color = fill_color
        self.corner_radius = corner_radius if corner_radius is not None else dp(24)
        from kivy.graphics import Color, RoundedRectangle
        with self.canvas.before:
            self._bg_color_instruction = Color(*fill_color)
            self._bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[self.corner_radius] * 4)
        self.bind(pos=self._update_bg, size=self._update_bg, state=self._update_bg, disabled=self._update_bg)
        self.bind(size=self._update_text_size)
        Clock.schedule_once(self._update_text_size, 0)

    def _draw_color(self):
        r, g, b, a = self.fill_color
        if self.disabled:
            return (r * 0.6, g * 0.6, b * 0.6, 0.55)
        if self.state == "down":
            return (r * 0.85, g * 0.85, b * 0.85, a)
        return self.fill_color

    def _update_text_size(self, *_args):
        self.text_size = (max(0, self.width - dp(18)), max(0, self.height - dp(8)))

    def _update_bg(self, *_args):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size
        self._bg_rect.radius = [self.corner_radius] * 4
        self._bg_color_instruction.rgba = self._draw_color()


class StyledButton(RoundedButton):
    def __init__(self, **kwargs):
        defaults = dict(fill_color=ACCENT, corner_radius=dp(26), height=dp(54), font_size=sp(15), bold=True)
        defaults.update(kwargs)
        super().__init__(**defaults)


class SecondaryButton(RoundedButton):
    def __init__(self, **kwargs):
        defaults = dict(fill_color=CARD_2, corner_radius=dp(24), height=dp(50), font_size=sp(14), bold=False)
        defaults.update(kwargs)
        super().__init__(**defaults)


class DangerButton(RoundedButton):
    def __init__(self, **kwargs):
        defaults = dict(fill_color=RED, corner_radius=dp(24), height=dp(50), font_size=sp(14), bold=True)
        defaults.update(kwargs)
        super().__init__(**defaults)


class Card(BoxLayout):
    def __init__(self, bg_color=CARD, radius=None, auto_height=False, **kwargs):
        defaults = dict(
            orientation="vertical",
            size_hint_y=None,
            padding=dp(16),
            spacing=dp(10),
        )
        defaults.update(kwargs)
        super().__init__(**defaults)
        self.bg_color = bg_color
        self.radius = radius if radius is not None else dp(22)
        from kivy.graphics import Color, RoundedRectangle
        with self.canvas.before:
            self._bg_color = Color(*bg_color)
            self._bg_rect = RoundedRectangle(radius=[self.radius] * 4, pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)
        if auto_height:
            self.bind(minimum_height=self.setter("height"))

    def _update_bg(self, *_args):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size
        self._bg_rect.radius = [self.radius] * 4
        self._bg_color.rgba = self.bg_color


class StatusBadge(Label):
    def __init__(self, text="", bg_color=ACCENT, text_color=TEXT, **kwargs):
        defaults = dict(
            size_hint=(None, None),
            width=dp(130),
            height=dp(34),
            color=text_color,
            font_size=sp(12),
            bold=True,
            halign="center",
            valign="middle",
        )
        defaults.update(kwargs)
        super().__init__(text=text, **defaults)
        self.bg_color = bg_color
        from kivy.graphics import Color, RoundedRectangle
        with self.canvas.before:
            self._bg = Color(*bg_color)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(16)] * 4)
        self.bind(pos=self._update_bg, size=self._update_bg)
        self.bind(size=self._update_text_size)
        Clock.schedule_once(self._update_text_size, 0)

    def _update_text_size(self, *_args):
        self.text_size = (self.width - dp(12), self.height)

    def _update_bg(self, *_args):
        self._rect.pos = self.pos
        self._rect.size = self.size
        self._bg.rgba = self.bg_color


class WrapLabel(Label):
    def __init__(self, **kwargs):
        defaults = dict(
            color=TEXT,
            halign="left",
            valign="top",
            text_size=(0, None),
            size_hint_y=None,
        )
        defaults.update(kwargs)
        super().__init__(**defaults)
        self.bind(size=self._sync_text, texture_size=self._sync_height)
        Clock.schedule_once(self._sync_text, 0)

    def _sync_text(self, *_args):
        self.text_size = (self.width, None)

    def _sync_height(self, *_args):
        pad = dp(2)
        self.height = max(dp(20), self.texture_size[1] + pad)


class TitleLabel(WrapLabel):
    def __init__(self, **kwargs):
        defaults = dict(font_size=sp(28), bold=True, valign="middle")
        defaults.update(kwargs)
        super().__init__(**defaults)


class HomeTitleLabel(WrapLabel):
    def __init__(self, **kwargs):
        defaults = dict(font_size=sp(30), bold=True, valign="middle")
        defaults.update(kwargs)
        super().__init__(**defaults)


class HomeSubtitleLabel(WrapLabel):
    def __init__(self, **kwargs):
        defaults = dict(font_size=sp(15), color=MUTED, valign="middle")
        defaults.update(kwargs)
        super().__init__(**defaults)


class SectionTitle(WrapLabel):
    def __init__(self, **kwargs):
        defaults = dict(font_size=sp(18), bold=True, valign="middle")
        defaults.update(kwargs)
        super().__init__(**defaults)


class BodyLabel(WrapLabel):
    def __init__(self, **kwargs):
        defaults = dict(font_size=sp(15), color=TEXT)
        defaults.update(kwargs)
        super().__init__(**defaults)


class SmallLabel(WrapLabel):
    def __init__(self, **kwargs):
        defaults = dict(font_size=sp(13), color=MUTED)
        defaults.update(kwargs)
        super().__init__(**defaults)


class StyledInput(TextInput):
    def __init__(self, **kwargs):
        defaults = dict(
            size_hint_y=None,
            height=dp(50),
            multiline=False,
            background_normal="",
            background_active="",
            background_color=CARD_2,
            foreground_color=TEXT,
            hint_text_color=MUTED,
            cursor_color=TEXT,
            padding=[dp(14), dp(14), dp(14), dp(12)],
            font_size=sp(14),
        )
        defaults.update(kwargs)
        super().__init__(**defaults)


class StyledMultiline(TextInput):
    def __init__(self, **kwargs):
        defaults = dict(
            size_hint_y=None,
            height=dp(110),
            multiline=True,
            background_normal="",
            background_active="",
            background_color=CARD_2,
            foreground_color=TEXT,
            hint_text_color=MUTED,
            cursor_color=TEXT,
            padding=[dp(14), dp(12), dp(14), dp(12)],
            font_size=sp(14),
        )
        defaults.update(kwargs)
        super().__init__(**defaults)


class StyledSpinner(Spinner):
    def __init__(self, **kwargs):
        defaults = dict(
            size_hint_y=None,
            height=dp(48),
            background_normal="",
            background_down="",
            background_color=CARD_2,
            color=TEXT,
            font_size=sp(14),
            sync_height=True,
        )
        defaults.update(kwargs)
        super().__init__(**defaults)


class StatPill(BoxLayout):
    def __init__(self, value="", label="", **kwargs):
        defaults = dict(
            orientation="vertical",
            size_hint_y=None,
            height=dp(82),
            padding=[dp(10), dp(10), dp(10), dp(8)],
            spacing=dp(2),
        )
        defaults.update(kwargs)
        super().__init__(**defaults)
        from kivy.graphics import Color, RoundedRectangle
        with self.canvas.before:
            self._bg_color = Color(*CARD_2)
            self._bg_rect = RoundedRectangle(radius=[dp(18)] * 4, pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)
        self.add_widget(WrapLabel(text=str(value), color=TEXT, font_size=sp(18), bold=True, halign="center", valign="middle"))
        self.add_widget(SmallLabel(text=str(label), color=MUTED, font_size=sp(12), halign="center"))

    def _update_bg(self, *_args):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size


class SectionDivider(Widget):
    def __init__(self, **kwargs):
        defaults = dict(size_hint_y=None, height=dp(1))
        defaults.update(kwargs)
        super().__init__(**defaults)
        from kivy.graphics import Color, Rectangle
        with self.canvas.before:
            self._c = Color(0.18, 0.22, 0.28, 1)
            self._r = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_line, size=self._update_line)

    def _update_line(self, *_args):
        self._r.pos = self.pos
        self._r.size = self.size


# ----------------------------
# Popup helpers
# ----------------------------
def open_popup(title, content, size=(0.94, 0.90)):
    return Popup(
        title=title,
        content=content,
        size_hint=size,
        separator_color=ACCENT,
        background="",
        background_color=(0, 0, 0, 1),
        auto_dismiss=False,
    )


def show_message(title, message):
    box = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
    lbl = SmallLabel(text=message, color=TEXT)
    btn = StyledButton(text="OK", size_hint_y=None, height=dp(48))
    box.add_widget(lbl)
    box.add_widget(btn)
    pop = open_popup(title, box, size=(0.84, 0.34))
    btn.bind(on_release=pop.dismiss)
    pop.open()


# ----------------------------
# Storage
# ----------------------------
class StorageMixin:
    def get_app_dir(self):
        base = os.path.dirname(os.path.abspath(__file__))
        app_dir = os.path.join(base, "synapse_data")
        safe_mkdir(app_dir)
        return app_dir

    def get_data_path(self):
        return os.path.join(self.get_app_dir(), "synapse_projects.json")

    def normalize_project(self, project):
        stamp = now_str()
        if not isinstance(project, dict):
            project = {}

        project.setdefault("id", str(uuid.uuid4()))
        project.setdefault("name", "Project")
        project.setdefault("duration", "")
        project.setdefault("client", "")
        project.setdefault("description", "")
        project.setdefault("status", "Planning")
        project.setdefault("priority", "Medium")
        project.setdefault("pipeline_stage", "Lead")
        project.setdefault("archived", False)
        project.setdefault("pinned", False)
        project.setdefault("created_at", stamp)
        project.setdefault("updated_at", project.get("created_at", stamp))
        project.setdefault("last_edited_at", project.get("updated_at", project.get("created_at", stamp)))
        project.setdefault("last_activity_at", project.get("updated_at", project.get("created_at", stamp)))
        project.setdefault("attachments", {})
        project.setdefault("build_history", [])
        project.setdefault("checklists", [])
        project.setdefault("calls", [])
        project.setdefault("future_developments", [])
        project.setdefault("sales_notes", [])

        attachments = project.get("attachments") if isinstance(project.get("attachments"), dict) else {}
        for key in ("github_repo", "play_store", "apk_path", "screenshots_path", "client_contact"):
            attachments.setdefault(key, "")
        project["attachments"] = attachments

        normalized_checklists = []
        for checklist in project.get("checklists", []):
            if not isinstance(checklist, dict):
                continue
            c_created = checklist.get("created_at", stamp)
            c_updated = checklist.get("updated_at", c_created)
            items = []
            for item in checklist.get("items", []):
                if isinstance(item, str):
                    item = {"entry": item, "done": False, "notes": ""}
                if not isinstance(item, dict):
                    continue
                items.append({
                    "entry": str(item.get("entry", "")).strip() or "Checklist item",
                    "done": bool(item.get("done", False)),
                    "notes": str(item.get("notes", "")).strip(),
                })
            normalized_checklists.append({
                "id": checklist.get("id", str(uuid.uuid4())),
                "name": str(checklist.get("name", "")).strip() or "Checklist",
                "description": str(checklist.get("description", "")).strip(),
                "created_at": c_created,
                "updated_at": c_updated,
                "items": items,
            })
        project["checklists"] = normalized_checklists

        normalized_calls = []
        for call in project.get("calls", []):
            if not isinstance(call, dict):
                continue
            c_created = call.get("created_at", stamp)
            c_updated = call.get("updated_at", c_created)
            normalized_calls.append({
                "id": call.get("id", str(uuid.uuid4())),
                "title": str(call.get("title", "")).strip() or "Call",
                "date": str(call.get("date", "")).strip(),
                "duration": str(call.get("duration", "")).strip(),
                "about": str(call.get("about", "")).strip(),
                "notes": str(call.get("notes", "")).strip(),
                "next_action": str(call.get("next_action", "")).strip(),
                "followup_date": str(call.get("followup_date", "")).strip(),
                "outcome": str(call.get("outcome", "")).strip(),
                "lead_stage": str(call.get("lead_stage", "Lead")).strip() or "Lead",
                "created_at": c_created,
                "updated_at": c_updated,
            })
        project["calls"] = normalized_calls

        normalized_future = []
        for item in project.get("future_developments", []):
            if not isinstance(item, dict):
                continue
            created = item.get("created_at", stamp)
            updated = item.get("updated_at", created)
            normalized_future.append({
                "id": item.get("id", str(uuid.uuid4())),
                "title": str(item.get("title", "")).strip() or "Untitled item",
                "status": str(item.get("status", "In Process")).strip() or "In Process",
                "notes": str(item.get("notes", "")).strip(),
                "urgent": bool(item.get("urgent", False)),
                "pinned": bool(item.get("pinned", False)),
                "created_at": created,
                "updated_at": updated,
            })
        project["future_developments"] = normalized_future

        normalized_notes = []
        for note in project.get("sales_notes", []):
            if not isinstance(note, dict):
                continue
            created = note.get("created_at", stamp)
            updated = note.get("updated_at", created)
            normalized_notes.append({
                "id": note.get("id", str(uuid.uuid4())),
                "heading": str(note.get("heading", "")).strip() or "Untitled note",
                "body": str(note.get("body", "")).strip(),
                "pinned": bool(note.get("pinned", False)),
                "created_at": created,
                "updated_at": updated,
            })
        project["sales_notes"] = normalized_notes

        normalized_builds = []
        for build in project.get("build_history", []):
            if not isinstance(build, dict):
                continue
            created = build.get("date", stamp)
            normalized_builds.append({
                "id": build.get("id", str(uuid.uuid4())),
                "version": str(build.get("version", "")).strip() or "0.1",
                "date": str(build.get("date", created)).strip() or stamp,
                "build_type": str(build.get("build_type", "Debug APK")).strip() or "Debug APK",
                "result": str(build.get("result", "Success")).strip() or "Success",
                "notes": str(build.get("notes", "")).strip(),
            })
        project["build_history"] = normalized_builds

        latest = latest_stamp(project.get("updated_at"), project.get("last_edited_at"), project.get("last_activity_at")) or stamp
        project["updated_at"] = latest
        project["last_edited_at"] = latest
        if not project.get("last_activity_at"):
            project["last_activity_at"] = latest
        return project

    def load_data(self):
        path = self.get_data_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    data.setdefault("projects", [])
                    data.setdefault("settings", {})
                    settings = data["settings"]
                    settings.setdefault("master_password", "8889")
                    settings.setdefault("autosave_enabled", True)
                    settings.setdefault("backup_on_start", False)
                    settings.setdefault("file_generator", {})
                    settings.setdefault("last_backup_at", "")
                    data["projects"] = [self.normalize_project(project) for project in data.get("projects", [])]
                    return data
            except Exception:
                pass
        return {
            "projects": [],
            "settings": {"master_password": "8889", "autosave_enabled": True, "backup_on_start": False, "file_generator": {}, "last_backup_at": ""},
        }

    def save_data(self):
        self.data_store.setdefault("settings", {}).setdefault("autosave_enabled", True)
        self.data_store.setdefault("settings", {}).setdefault("backup_on_start", False)
        self.data_store.setdefault("settings", {}).setdefault("last_backup_at", "")
        self.data_store["projects"] = [self.normalize_project(project) for project in self.data_store.get("projects", [])]
        path = self.get_data_path()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.data_store, f, indent=2, ensure_ascii=False)


class ManagedScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.scroll_ref = None

    def reset_scroll(self):
        if self.scroll_ref is not None:
            Clock.schedule_once(lambda *_: setattr(self.scroll_ref, "scroll_y", 1), 0)

    def on_pre_enter(self, *args):
        self.reset_scroll()
        self.refresh()

    def refresh(self):
        pass


class MainScreen(ManagedScreen):
    stats_label = None

    def refresh(self):
        app = App.get_running_app()
        metrics = app.get_dashboard_metrics()
        if self.stats_label is not None:
            self.stats_label.text = (
                f"Projects: {metrics['project_count']}    Checklists: {metrics['checklists']}    Calls: {metrics['calls']}\n"
                f"Future Dev: {metrics['future']}    Sales Notes: {metrics['sales']}\n"
                f"QA Progress: {metrics['qa_done']}/{metrics['qa_total']}"
            )
        if getattr(self, 'active_projects_label', None) is not None:
            self.active_projects_label.text = str(metrics['projects_in_progress'])
        if getattr(self, 'overdue_label', None) is not None:
            self.overdue_label.text = str(metrics['overdue_followups'])
        if getattr(self, 'future_breakdown_label', None) is not None:
            self.future_breakdown_label.text = (
                f"In Process: {metrics['future_status_counts'].get('In Process', 0)}\n"
                f"Done: {metrics['future_status_counts'].get('Done', 0)}\n"
                f"Discontinuing: {metrics['future_status_counts'].get('Discontinuing', 0)}"
            )
        if getattr(self, 'latest_sales_label', None) is not None:
            self.latest_sales_label.text = metrics['latest_sales_preview']
        if getattr(self, 'next_call_label', None) is not None:
            self.next_call_label.text = metrics['next_call_preview']
        if getattr(self, 'pinned_projects_label', None) is not None:
            self.pinned_projects_label.text = str(metrics['pinned_projects'])


class ProjectsScreen(ManagedScreen):
    project_list = None

    def refresh(self):
        app = App.get_running_app()
        if self.project_list is None:
            return
        self.project_list.clear_widgets()

        search_text = safe_lower(getattr(getattr(self, 'search_input', None), 'text', ''))
        status_filter = getattr(getattr(self, 'status_filter', None), 'text', 'All') or 'All'
        priority_filter = getattr(getattr(self, 'priority_filter', None), 'text', 'All') or 'All'
        archive_filter = getattr(getattr(self, 'archive_filter', None), 'text', 'Active Only') or 'Active Only'

        projects = []
        for project in app.data_store.get('projects', []):
            haystack = ' '.join([
                project.get('name', ''), project.get('client', ''), project.get('description', ''),
                project.get('status', ''), project.get('priority', ''), project.get('pipeline_stage', ''),
            ]).lower()
            if search_text and search_text not in haystack:
                continue
            if status_filter != 'All' and project.get('status') != status_filter:
                continue
            if priority_filter != 'All' and project.get('priority') != priority_filter:
                continue
            if archive_filter == 'Active Only' and project.get('archived'):
                continue
            if archive_filter == 'Archived Only' and not project.get('archived'):
                continue
            if archive_filter == 'Pinned Only' and not project.get('pinned'):
                continue
            projects.append(project)

        if not projects:
            card = Card(auto_height=True, padding=dp(16), spacing=dp(10))
            card.add_widget(SectionTitle(text='No matching projects'))
            card.add_widget(SmallLabel(text='Try changing the search or filters, or create a new project.'))
            self.project_list.add_widget(card)
            return

        for project in reversed(projects):
            summary = app.get_project_summary(project)
            status = project.get('status', 'Planning')
            priority = project.get('priority', 'Medium')
            stage = project.get('pipeline_stage', 'Lead')
            card = Card(auto_height=True, spacing=dp(10), padding=dp(16), bg_color=mix_color(CARD, project_status_color(status), 0.12))

            title_row = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(8))
            title_row.add_widget(SectionTitle(text=project.get('name', 'Project')))
            if project.get('pinned'):
                title_row.add_widget(StatusBadge(text='Pinned', width=dp(84), bg_color=ACCENT, text_color=TEXT))
            card.add_widget(title_row)

            chip_row = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(8))
            chip_row.add_widget(StatusBadge(text=status, width=dp(118), bg_color=project_status_color(status), text_color=project_status_text_color(status)))
            chip_row.add_widget(StatusBadge(text=priority, width=dp(96), bg_color=priority_color(priority), text_color=priority_text_color(priority)))
            chip_row.add_widget(StatusBadge(text=stage, width=dp(128), bg_color=lead_stage_color(stage), text_color=lead_stage_text_color(stage)))
            card.add_widget(chip_row)

            card.add_widget(SmallLabel(text=f"Duration: {project.get('duration', '-') or '-'}    |    Client: {project.get('client', '-') or '-'}"))
            card.add_widget(SmallLabel(text=f"Description: {project.get('description', '-') or '-'}"))

            stat_row = BoxLayout(size_hint_y=None, height=dp(84), spacing=dp(10))
            stat_row.add_widget(StatPill(value=summary['checklists'], label='Checklists'))
            stat_row.add_widget(StatPill(value=summary['calls'], label='Calls'))
            stat_row.add_widget(StatPill(value=f"{summary['qa_done']}/{summary['qa_total']}", label='QA Done'))
            card.add_widget(stat_row)
            card.add_widget(SmallLabel(text=f"Future Dev: {summary['future']}    |    Sales Notes: {summary['sales']}    |    Builds: {summary['builds']}"))
            card.add_widget(SmallLabel(text=f"Created: {project.get('created_at', '-')}    |    Updated: {project.get('last_edited_at', '-') or '-'}"))

            btn_grid = GridLayout(cols=3, size_hint_y=None, height=dp(48), spacing=dp(8))
            open_btn = StyledButton(text='Open', height=dp(46))
            archive_btn = SecondaryButton(text='Unarchive' if project.get('archived') else 'Archive', height=dp(46))
            del_btn = DangerButton(text='Delete', height=dp(46))
            open_btn.bind(on_release=lambda *_args, pid=project['id']: app.open_project(pid))
            archive_btn.bind(on_release=lambda *_args, pid=project['id']: app.toggle_archive_project(pid))
            del_btn.bind(on_release=lambda *_args, pid=project['id']: app.open_delete_project_popup(pid))
            btn_grid.add_widget(open_btn)
            btn_grid.add_widget(archive_btn)
            btn_grid.add_widget(del_btn)
            card.add_widget(btn_grid)
            self.project_list.add_widget(card)


class ProjectScreen(ManagedScreen):
    project_id = StringProperty('')
    title_label = None
    meta_label = None
    desc_label = None
    summary_label = None

    def refresh(self):
        app = App.get_running_app()
        project = app.get_project(self.project_id)
        if not project:
            return
        summary = app.get_project_summary(project)
        status = project.get('status', 'Planning')
        priority = project.get('priority', 'Medium')
        pipeline_stage = project.get('pipeline_stage', 'Lead')
        if self.title_label is not None:
            self.title_label.text = project.get('name', 'Project')
        if self.meta_label is not None:
            self.meta_label.text = (
                f"Duration: {project.get('duration', '-') or '-'}    |    Client: {project.get('client', '-') or '-'}\n"
                f"Created: {project.get('created_at', '-') or '-'}    |    Last Edited: {project.get('last_edited_at', '-') or '-'}"
            )
        if self.desc_label is not None:
            self.desc_label.text = f"Description: {project.get('description', '-') or '-'}"
        if self.summary_label is not None:
            self.summary_label.text = (
                f"Checklists: {summary['checklists']}    |    Calls: {summary['calls']}    |    Future Dev: {summary['future']}\n"
                f"Sales Notes: {summary['sales']}    |    Builds: {summary['builds']}    |    QA Progress: {summary['qa_done']}/{summary['qa_total']}"
            )
        for ref_name, value, bg, fg in [
            ('status_badge', status, project_status_color(status), project_status_text_color(status)),
            ('priority_badge', priority, priority_color(priority), priority_text_color(priority)),
            ('pipeline_badge', pipeline_stage, lead_stage_color(pipeline_stage), lead_stage_text_color(pipeline_stage)),
            ('pin_badge', 'Pinned' if project.get('pinned') else 'Standard', ACCENT if project.get('pinned') else CARD_2, TEXT),
        ]:
            ref = getattr(self, ref_name, None)
            if ref is not None:
                ref.text = value
                ref.bg_color = bg
                ref.color = fg
                ref._update_bg()
        if getattr(self, 'top_card', None) is not None:
            self.top_card.bg_color = mix_color(CARD, project_status_color(status), 0.18)
            self.top_card._update_bg()


class ChecklistListScreen(ManagedScreen):
    project_id = StringProperty("")
    title_label = None
    checklist_box = None

    def refresh(self):
        app = App.get_running_app()
        project = app.get_project(self.project_id)
        if not project or self.checklist_box is None:
            return
        if self.title_label is not None:
            self.title_label.text = f"Checklists • {project.get('name', 'Project')}"
        self.checklist_box.clear_widgets()
        checklists = project.get("checklists", [])
        if not checklists:
            card = Card(height=dp(130))
            card.add_widget(SectionTitle(text="No checklists yet"))
            card.add_widget(SmallLabel(text="Create one manually or import a Python checklist template."))
            self.checklist_box.add_widget(card)
            return

        for checklist in reversed(checklists):
            items = checklist.get("items", [])
            done = sum(1 for item in items if item.get("done"))
            card = Card(height=dp(224), spacing=dp(10))
            card.add_widget(SectionTitle(text=checklist.get("name", "Checklist")))
            card.add_widget(SmallLabel(text=checklist.get("description", "No description") or "No description"))
            card.add_widget(SmallLabel(text=f"Items: {len(items)}    |    Done: {done}/{len(items)}"))
            btn_row = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(8))
            open_btn = StyledButton(text="Open")
            rename_btn = SecondaryButton(text="Rename")
            open_btn.bind(on_release=lambda *_args, cid=checklist["id"]: app.open_checklist(self.project_id, cid))
            rename_btn.bind(on_release=lambda *_args, cid=checklist["id"]: app.open_rename_checklist_popup(self.project_id, cid))
            btn_row.add_widget(open_btn)
            btn_row.add_widget(rename_btn)
            card.add_widget(btn_row)
            self.checklist_box.add_widget(card)


class ChecklistDetailScreen(ManagedScreen):
    project_id = StringProperty("")
    checklist_id = StringProperty("")
    title_label = None
    desc_label = None
    row_box = None

    def refresh(self):
        app = App.get_running_app()
        checklist = app.get_checklist(self.project_id, self.checklist_id)
        if not checklist or self.row_box is None:
            return
        if self.title_label is not None:
            self.title_label.text = checklist.get("name", "Checklist")
        if self.desc_label is not None:
            self.desc_label.text = checklist.get("description", "No description") or "No description"
        self.row_box.clear_widgets()
        for idx, item in enumerate(checklist.get("items", [])):
            self.row_box.add_widget(ChecklistItemCard(item=item, index=idx))

    def save_rows(self):
        app = App.get_running_app()
        checklist = app.get_checklist(self.project_id, self.checklist_id)
        if not checklist:
            return
        new_items = []
        for card in self.row_box.children[::-1]:
            if isinstance(card, ChecklistItemCard):
                new_items.append({
                    "entry": card.entry_text,
                    "done": bool(card.done_box.active),
                    "notes": card.notes_input.text.strip(),
                })
        checklist['items'] = new_items
        checklist['updated_at'] = now_str()
        project = app.get_project(self.project_id)
        if project:
            app.touch_project(project, 'Checklist items updated')
        app.save_data()
        show_message('Saved', 'Checklist changes saved successfully.')

    def add_item_popup(self):
        app = App.get_running_app()
        box = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
        entry = StyledInput(hint_text="Checklist entry")
        notes = StyledMultiline(hint_text="Optional notes")
        btns = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        add_btn = StyledButton(text="Add Item")
        cancel_btn = SecondaryButton(text="Cancel")
        btns.add_widget(add_btn)
        btns.add_widget(cancel_btn)
        box.add_widget(entry)
        box.add_widget(notes)
        box.add_widget(btns)
        pop = open_popup("New Checklist Item", box, size=(0.92, 0.50))

        def do_add(*_):
            checklist = app.get_checklist(self.project_id, self.checklist_id)
            if checklist is None:
                pop.dismiss()
                return
            if not entry.text.strip():
                show_message("Missing Entry", "Please enter a checklist item.")
                return
            checklist.setdefault('items', []).append({
                'entry': entry.text.strip(),
                'done': False,
                'notes': notes.text.strip(),
            })
            checklist['updated_at'] = now_str()
            project = app.get_project(self.project_id)
            if project:
                app.touch_project(project, 'Checklist item added')
            app.save_data()
            pop.dismiss()
            self.refresh()
            app.refresh_all()

        add_btn.bind(on_release=do_add)
        cancel_btn.bind(on_release=pop.dismiss)
        pop.open()


class ChecklistItemCard(Card):
    entry_text = StringProperty("")

    def __init__(self, item=None, index=0, **kwargs):
        super().__init__(height=dp(188), **kwargs)
        item = item or {}
        self.entry_text = item.get("entry", "")

        top_row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(10))
        text_col = BoxLayout(orientation="vertical", spacing=dp(2))
        entry_lbl = BodyLabel(text=f"{index + 1}. {self.entry_text}", font_size=sp(15))
        text_col.add_widget(entry_lbl)
        top_row.add_widget(text_col)

        done_col = BoxLayout(orientation="horizontal", size_hint_x=None, width=dp(88), spacing=dp(4))
        done_col.add_widget(SmallLabel(text="Done", color=TEXT, halign="center"))
        self.done_box = CheckBox(active=bool(item.get("done", False)), size_hint=(None, None), size=(dp(30), dp(30)))
        done_col.add_widget(self.done_box)
        top_row.add_widget(done_col)

        notes_lbl = SmallLabel(text="Notes", color=TEXT)
        self.notes_input = StyledMultiline(text=item.get("notes", ""), height=dp(90))

        self.add_widget(top_row)
        self.add_widget(notes_lbl)
        self.add_widget(self.notes_input)


class CallsScreen(ManagedScreen):
    project_id = StringProperty('')
    title_label = None
    call_box = None

    def refresh(self):
        app = App.get_running_app()
        project = app.get_project(self.project_id)
        if not project or self.call_box is None:
            return
        if self.title_label is not None:
            self.title_label.text = f"Calls • {project.get('name', 'Project')}"
        self.call_box.clear_widgets()
        calls = sorted(project.get('calls', []), key=lambda c: parse_datetime_maybe(c.get('date')) or datetime.min, reverse=True)
        if not calls:
            card = Card(auto_height=True)
            card.add_widget(SectionTitle(text='No calls logged yet'))
            card.add_widget(SmallLabel(text='Add each client or project call with topic, follow-up date, outcome, and lead stage.'))
            self.call_box.add_widget(card)
            return
        for call in calls:
            card = Card(auto_height=True, spacing=dp(8))
            head = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(8))
            head.add_widget(SectionTitle(text=call.get('title', 'Call')))
            stage = call.get('lead_stage', 'Lead')
            head.add_widget(StatusBadge(text=stage, width=dp(128), bg_color=lead_stage_color(stage), text_color=lead_stage_text_color(stage)))
            card.add_widget(head)
            card.add_widget(SmallLabel(text=f"Date: {call.get('date', '-') or '-'}    |    Duration: {call.get('duration', '-') or '-'}"))
            card.add_widget(SmallLabel(text=f"About: {call.get('about', '-') or '-'}"))
            card.add_widget(SmallLabel(text=f"Outcome: {call.get('outcome', '-') or '-'}"))
            card.add_widget(SmallLabel(text=f"Next Action: {call.get('next_action', '-') or '-'}"))
            followup_text = call.get('followup_date', '-') or '-'
            if followup_is_overdue(call):
                followup_text += '    |    OVERDUE'
            card.add_widget(SmallLabel(text=f"Follow-up: {followup_text}"))
            card.add_widget(SmallLabel(text=f"Notes: {call.get('notes', '-') or '-'}"))
            card.add_widget(SmallLabel(text=f"Created: {call.get('created_at', '-')}    |    Updated: {call.get('updated_at', '-') or '-'}"))
            btn_row = GridLayout(cols=2, size_hint_y=None, height=dp(46), spacing=dp(10))
            edit_btn = SecondaryButton(text='Edit', height=dp(46))
            del_btn = DangerButton(text='Delete', height=dp(46))
            edit_btn.bind(on_release=lambda *_args, cid=call['id']: app.open_new_call_popup(cid))
            del_btn.bind(on_release=lambda *_args, cid=call['id']: app.delete_call(self.project_id, cid))
            btn_row.add_widget(edit_btn)
            btn_row.add_widget(del_btn)
            card.add_widget(btn_row)
            self.call_box.add_widget(card)


class FutureDevelopmentsScreen(ManagedScreen):
    project_id = StringProperty('')
    title_label = None
    summary_label = None
    item_box = None

    def refresh(self):
        app = App.get_running_app()
        project = app.get_project(self.project_id)
        if not project or self.item_box is None:
            return
        if self.title_label is not None:
            self.title_label.text = f"Future Developments • {project.get('name', 'Project')}"

        items = project.get('future_developments', [])
        counts = {status: 0 for status in future_status_options()}
        for item in items:
            counts[item.get('status', 'In Process')] = counts.get(item.get('status', 'In Process'), 0) + 1

        if self.summary_label is not None:
            self.summary_label.text = (
                f"In Process: {counts.get('In Process', 0)}    |    Done: {counts.get('Done', 0)}    |    Discontinuing: {counts.get('Discontinuing', 0)}"
            )

        search_text = safe_lower(getattr(getattr(self, 'search_input', None), 'text', ''))
        status_filter = getattr(getattr(self, 'status_filter', None), 'text', 'All') or 'All'

        self.item_box.clear_widgets()
        filtered_items = []
        for item in items:
            haystack = ' '.join([item.get('title', ''), item.get('notes', '')]).lower()
            if search_text and search_text not in haystack:
                continue
            if status_filter != 'All' and item.get('status') != status_filter:
                continue
            filtered_items.append(item)

        if not filtered_items:
            card = Card(auto_height=True)
            card.add_widget(SectionTitle(text='No future developments found'))
            card.add_widget(SmallLabel(text='Track roadmap ideas here and color-code each one by status.'))
            self.item_box.add_widget(card)
            return

        for item in reversed(filtered_items):
            status = item.get('status', 'In Process')
            card = Card(auto_height=True, spacing=dp(10), bg_color=future_status_card_color(status))
            head = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(8))
            head.add_widget(BodyLabel(text=item.get('title', 'Untitled item'), font_size=sp(16), bold=True))
            if item.get('urgent'):
                head.add_widget(StatusBadge(text='Urgent', width=dp(86), bg_color=LIGHT_RED, text_color=TEXT))
            if item.get('pinned'):
                head.add_widget(StatusBadge(text='Pinned', width=dp(86), bg_color=ACCENT, text_color=TEXT))
            head.add_widget(StatusBadge(text=status, bg_color=future_status_color(status), text_color=future_status_text_color(status)))
            card.add_widget(head)
            card.add_widget(SmallLabel(text=f"Created: {item.get('created_at', '-')}    |    Updated: {item.get('updated_at', '-') or '-'}"))
            card.add_widget(SmallLabel(text=item.get('notes', 'No extra notes yet.') or 'No extra notes yet.', color=TEXT))

            btn_row = GridLayout(cols=2, size_hint_y=None, height=dp(46), spacing=dp(10))
            edit_btn = SecondaryButton(text='Edit', height=dp(46))
            del_btn = DangerButton(text='Delete', height=dp(46))
            edit_btn.bind(on_release=lambda *_args, iid=item['id']: app.open_future_development_popup(iid))
            del_btn.bind(on_release=lambda *_args, iid=item['id']: app.delete_future_development(self.project_id, iid))
            btn_row.add_widget(edit_btn)
            btn_row.add_widget(del_btn)
            card.add_widget(btn_row)
            self.item_box.add_widget(card)


class SalesNotesScreen(ManagedScreen):
    project_id = StringProperty('')
    title_label = None
    summary_label = None
    note_box = None

    def refresh(self):
        app = App.get_running_app()
        project = app.get_project(self.project_id)
        if not project or self.note_box is None:
            return
        if self.title_label is not None:
            self.title_label.text = f"Sales Notes • {project.get('name', 'Project')}"
        notes = project.get('sales_notes', [])
        keyword = safe_lower(getattr(getattr(self, 'search_input', None), 'text', ''))
        filtered = []
        for note in notes:
            haystack = ' '.join([note.get('heading', ''), note.get('body', '')]).lower()
            if keyword and keyword not in haystack:
                continue
            filtered.append(note)
        if self.summary_label is not None:
            self.summary_label.text = f"Saved notes: {len(notes)}    |    Showing: {len(filtered)}"
        self.note_box.clear_widgets()
        if not filtered:
            card = Card(auto_height=True)
            card.add_widget(SectionTitle(text='No sales notes found'))
            card.add_widget(SmallLabel(text='Add quick call summaries, pricing ideas, buyer objections, and follow-up notes here.'))
            self.note_box.add_widget(card)
            return

        for note in reversed(filtered):
            card = Card(auto_height=True, spacing=dp(10))
            head = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(8))
            head.add_widget(SectionTitle(text=note.get('heading', 'Untitled note')))
            if note.get('pinned'):
                head.add_widget(StatusBadge(text='High Value', width=dp(108), bg_color=ACCENT, text_color=TEXT))
            card.add_widget(head)
            card.add_widget(SmallLabel(text=f"Created: {note.get('created_at', '-')}    |    Updated: {note.get('updated_at', '-') or '-'}"))
            card.add_widget(SmallLabel(text=note.get('body', '') or 'No details added yet.', color=TEXT))

            btn_row = GridLayout(cols=3, size_hint_y=None, height=dp(46), spacing=dp(10))
            copy_btn = SecondaryButton(text='Copy Body', height=dp(46))
            edit_btn = SecondaryButton(text='Edit', height=dp(46))
            del_btn = DangerButton(text='Delete', height=dp(46))
            copy_btn.bind(on_release=lambda *_args, body=note.get('body', ''): app.copy_text(body, 'Sales note body copied.'))
            edit_btn.bind(on_release=lambda *_args, nid=note['id']: app.open_sales_note_popup(nid))
            del_btn.bind(on_release=lambda *_args, nid=note['id']: app.delete_sales_note(self.project_id, nid))
            btn_row.add_widget(copy_btn)
            btn_row.add_widget(edit_btn)
            btn_row.add_widget(del_btn)
            card.add_widget(btn_row)
            self.note_box.add_widget(card)


class SettingsScreen(ManagedScreen):
    def refresh(self):
        app = App.get_running_app()
        settings = app.data_store.get('settings', {})
        if getattr(self, 'autosave_box', None) is not None:
            self.autosave_box.active = bool(settings.get('autosave_enabled', True))
        if getattr(self, 'backup_start_box', None) is not None:
            self.backup_start_box.active = bool(settings.get('backup_on_start', False))
        if getattr(self, 'last_backup_label', None) is not None:
            stamp = str(settings.get('last_backup_at', '')).strip() or 'Never'
            self.last_backup_label.text = f'Last backup: {stamp}'


class FileGeneratorHubScreen(ManagedScreen):
    def refresh(self):
        pass


class GithubApkMenuScreen(ManagedScreen):
    def refresh(self):
        pass


class FGBuildozerScreen(ManagedScreen):
    def refresh(self):
        pass


class FGWorkflowScreen(ManagedScreen):
    def refresh(self):
        pass


class FGHistoryScreen(ManagedScreen):
    history_label = None

    def refresh(self):
        if self.history_label is not None:
            self.history_label.text = read_fg_history()


class FGGuideScreen(ManagedScreen):
    def refresh(self):
        pass


# ----------------------------
# App
# ----------------------------
class SynapseApp(App, StorageMixin):
    def build(self):
        self.title = "Synapse by SHV"
        self.data_store = self.load_data()
        self.current_project_id = None

        self.sm = ScreenManager(transition=FadeTransition(duration=0.10))

        home = MainScreen(name="main")
        home.add_widget(self.build_main_ui(home))
        self.sm.add_widget(home)

        projects = ProjectsScreen(name="projects")
        projects.add_widget(self.build_projects_ui(projects))
        self.sm.add_widget(projects)

        project = ProjectScreen(name="project")
        project.add_widget(self.build_project_dashboard_ui(project))
        self.sm.add_widget(project)

        checklist_list = ChecklistListScreen(name="checklists")
        checklist_list.add_widget(self.build_checklist_list_ui(checklist_list))
        self.sm.add_widget(checklist_list)

        checklist_detail = ChecklistDetailScreen(name="checklist_detail")
        checklist_detail.add_widget(self.build_checklist_detail_ui(checklist_detail))
        self.sm.add_widget(checklist_detail)

        calls = CallsScreen(name="calls")
        calls.add_widget(self.build_call_list_ui(calls))
        self.sm.add_widget(calls)

        future_dev = FutureDevelopmentsScreen(name="future_dev")
        future_dev.add_widget(self.build_future_dev_ui(future_dev))
        self.sm.add_widget(future_dev)

        sales_notes = SalesNotesScreen(name="sales_notes")
        sales_notes.add_widget(self.build_sales_notes_ui(sales_notes))
        self.sm.add_widget(sales_notes)

        settings = SettingsScreen(name="settings")
        settings.add_widget(self.build_settings_ui(settings))
        self.sm.add_widget(settings)

        fg_hub = FileGeneratorHubScreen(name="file_generator_hub")
        fg_hub.add_widget(self.build_file_generator_hub_ui(fg_hub))
        self.sm.add_widget(fg_hub)

        github_apk = GithubApkMenuScreen(name="github_apk_menu")
        github_apk.add_widget(self.build_github_apk_menu_ui(github_apk))
        self.sm.add_widget(github_apk)

        fg_buildozer = FGBuildozerScreen(name="fg_buildozer")
        fg_buildozer.add_widget(self.build_fg_buildozer_ui(fg_buildozer))
        self.sm.add_widget(fg_buildozer)

        fg_workflow = FGWorkflowScreen(name="fg_workflow")
        fg_workflow.add_widget(self.build_fg_workflow_ui(fg_workflow))
        self.sm.add_widget(fg_workflow)

        fg_history = FGHistoryScreen(name="fg_history")
        fg_history.add_widget(self.build_fg_history_ui(fg_history))
        self.sm.add_widget(fg_history)

        fg_guide = FGGuideScreen(name="fg_guide")
        fg_guide.add_widget(self.build_fg_guide_ui(fg_guide))
        self.sm.add_widget(fg_guide)

        return self.sm

    # ---------- UI base ----------
    def _build_screen_shell(self, screen, title_text, subtitle_text=None, include_scroll=True):
        outer = BoxLayout(orientation="vertical", padding=[dp(16), dp(18), dp(16), dp(12)], spacing=dp(12))

        header = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(2))
        title = TitleLabel(text=title_text)
        header.add_widget(title)
        if subtitle_text:
            sub = SmallLabel(text=subtitle_text, color=MUTED)
            header.add_widget(sub)
        header.bind(minimum_height=header.setter("height"))
        outer.add_widget(header)

        if include_scroll:
            scroll = ScrollView(bar_width=dp(3), scroll_type=["bars", "content"])
            content = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(12))
            content.bind(minimum_height=content.setter("height"))
            scroll.add_widget(content)
            outer.add_widget(scroll)
            screen.scroll_ref = scroll
            return outer, content

        return outer, None

    def build_main_ui(self, screen):
        outer = BoxLayout(orientation='vertical', padding=[dp(16), dp(18), dp(16), dp(12)], spacing=dp(12))

        title_box = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(2))
        title_box.add_widget(HomeTitleLabel(text='Synapse by SHV'))
        title_box.add_widget(HomeSubtitleLabel(text='Business-Grade Project Planner'))
        title_box.bind(minimum_height=title_box.setter('height'))
        outer.add_widget(title_box)

        scroll = ScrollView(bar_width=dp(3), scroll_type=['bars', 'content'])
        screen.scroll_ref = scroll
        content = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(14))
        content.bind(minimum_height=content.setter('height'))
        scroll.add_widget(content)
        outer.add_widget(scroll)

        hero = Card(auto_height=True, spacing=dp(12), padding=[dp(18), dp(16), dp(18), dp(18)])
        hero.add_widget(SectionTitle(text='Main Dashboard'))
        hero.add_widget(SmallLabel(text='Keep projects, sales pipeline, call follow-ups, future developments, and build logs organized in one AMOLED-friendly workspace.'))
        stats = SmallLabel(text='Projects: 0    Checklists: 0    Calls: 0\nFuture Dev: 0    Sales Notes: 0\nQA Progress: 0/0', color=TEXT)
        hero.add_widget(stats)
        open_btn = StyledButton(text='Open Projects', height=dp(58), corner_radius=dp(28))
        open_btn.bind(on_release=lambda *_: self.go_projects())
        hero.add_widget(open_btn)
        content.add_widget(hero)
        screen.stats_label = stats

        content.add_widget(SectionTitle(text='Dashboard Cards'))
        dash_grid = GridLayout(cols=2, size_hint_y=None, spacing=dp(12), row_default_height=dp(126), row_force_default=True)
        dash_grid.bind(minimum_height=dash_grid.setter('height'))

        def _dash_card(title, body_widget):
            card = Card(height=dp(126), spacing=dp(8), padding=[dp(14), dp(12), dp(14), dp(12)])
            card.add_widget(SmallLabel(text=title, color=MUTED))
            card.add_widget(body_widget)
            return card

        screen.active_projects_label = WrapLabel(text='0', font_size=sp(26), bold=True)
        screen.overdue_label = WrapLabel(text='0', font_size=sp(26), bold=True)
        screen.future_breakdown_label = SmallLabel(text='In Process: 0\nDone: 0\nDiscontinuing: 0', color=TEXT)
        screen.latest_sales_label = SmallLabel(text='No sales notes yet.', color=TEXT)
        screen.next_call_label = SmallLabel(text='No planned call yet.', color=TEXT)
        pinned_projects_label = SmallLabel(text='Use pins for favorites.', color=TEXT)
        screen.pinned_projects_label = pinned_projects_label

        dash_grid.add_widget(_dash_card('Projects in progress', screen.active_projects_label))
        dash_grid.add_widget(_dash_card('Overdue follow-ups', screen.overdue_label))
        dash_grid.add_widget(_dash_card('Future developments', screen.future_breakdown_label))
        dash_grid.add_widget(_dash_card('Latest sales note', screen.latest_sales_label))
        dash_grid.add_widget(_dash_card('Next planned call', screen.next_call_label))
        dash_grid.add_widget(_dash_card('Pinned projects', pinned_projects_label))
        content.add_widget(dash_grid)

        content.add_widget(SectionDivider())
        content.add_widget(SectionTitle(text='Quick Actions'))
        actions_card = Card(auto_height=True, spacing=dp(12), padding=[dp(16), dp(16), dp(16), dp(16)])
        row_top = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(12))
        export_btn = SecondaryButton(text='Export All Data', corner_radius=dp(24))
        import_btn = SecondaryButton(text='Import Data', corner_radius=dp(24))
        row_top.add_widget(export_btn)
        row_top.add_widget(import_btn)
        actions_card.add_widget(row_top)
        row_mid = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(12))
        settings_btn = SecondaryButton(text='Settings', corner_radius=dp(24), height=dp(52))
        backup_btn = SecondaryButton(text='Quick Backup', corner_radius=dp(24), height=dp(52))
        row_mid.add_widget(settings_btn)
        row_mid.add_widget(backup_btn)
        actions_card.add_widget(row_mid)
        content.add_widget(actions_card)

        content.add_widget(SectionDivider())
        content.add_widget(SectionTitle(text='Sections'))
        sections_card = Card(auto_height=True, spacing=dp(12), padding=[dp(16), dp(16), dp(16), dp(16)])
        sections_card.add_widget(SmallLabel(text='Projects now include status, priority, pipeline stage, attachments, build history, archive support, and timestamped activity. File Generator gives you quick GitHub APK build files inside Synapse.'))
        section_row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(12))
        projects_btn = SecondaryButton(text='Projects', corner_radius=dp(24), height=dp(52))
        file_gen_btn = SecondaryButton(text='File Generator', corner_radius=dp(24), height=dp(52))
        projects_btn.bind(on_release=lambda *_: self.go_projects())
        file_gen_btn.bind(on_release=lambda *_: self.go_file_generator_hub())
        section_row.add_widget(projects_btn)
        section_row.add_widget(file_gen_btn)
        sections_card.add_widget(section_row)
        content.add_widget(sections_card)

        bottom = BoxLayout(size_hint_y=None, height=dp(58))
        exit_btn = DangerButton(text='Exit App', height=dp(54), corner_radius=dp(28))
        exit_btn.bind(on_release=lambda *_: self.stop())
        bottom.add_widget(exit_btn)
        outer.add_widget(bottom)

        export_btn.bind(on_release=lambda *_: self.export_all_data())
        import_btn.bind(on_release=lambda *_: self.open_import_data_popup())
        settings_btn.bind(on_release=lambda *_: self.go_settings())
        backup_btn.bind(on_release=lambda *_: self.create_quick_backup())
        return outer

    def build_projects_ui(self, screen):
        outer, content = self._build_screen_shell(screen, 'Projects')

        workspace = Card(auto_height=True, spacing=dp(12), padding=dp(18))
        workspace.add_widget(SectionTitle(text='Project Workspace'))
        workspace.add_widget(SmallLabel(text='Create and manage your client or internal app projects. Use search, status filters, priority filters, archive view, and pins as your data grows.'))
        btn_row = BoxLayout(size_hint_y=None, height=dp(54), spacing=dp(12))
        create_btn = StyledButton(text='Create New Project', corner_radius=dp(26))
        back_btn = SecondaryButton(text='Back to Main', corner_radius=dp(26))
        create_btn.bind(on_release=lambda *_: self.open_new_project_popup())
        back_btn.bind(on_release=lambda *_: self.go_main())
        btn_row.add_widget(create_btn)
        btn_row.add_widget(back_btn)
        workspace.add_widget(btn_row)
        content.add_widget(workspace)

        filter_card = Card(auto_height=True, spacing=dp(10), padding=[dp(16), dp(14), dp(16), dp(16)])
        filter_card.add_widget(SectionTitle(text='Search + Filters'))
        screen.search_input = StyledInput(hint_text='Search projects by name, client, or description')
        screen.status_filter = StyledSpinner(text='All', values=['All'] + project_status_options())
        screen.priority_filter = StyledSpinner(text='All', values=['All'] + priority_options())
        screen.archive_filter = StyledSpinner(text='Active Only', values=['Active Only', 'Archived Only', 'All', 'Pinned Only'])
        filter_card.add_widget(screen.search_input)
        row = GridLayout(cols=3, size_hint_y=None, height=dp(48), spacing=dp(8))
        row.add_widget(screen.status_filter)
        row.add_widget(screen.priority_filter)
        row.add_widget(screen.archive_filter)
        filter_card.add_widget(row)
        content.add_widget(filter_card)

        for widget in (screen.search_input, screen.status_filter, screen.priority_filter, screen.archive_filter):
            widget.bind(text=lambda *_: screen.refresh())

        content.add_widget(SectionTitle(text='Your Projects'))
        project_list = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(12))
        project_list.bind(minimum_height=project_list.setter('height'))
        content.add_widget(project_list)
        screen.project_list = project_list
        return outer

    def build_project_dashboard_ui(self, screen):
        outer, content = self._build_screen_shell(screen, 'Project')

        top = Card(auto_height=True, spacing=dp(10))
        title = SectionTitle(text='Project')
        top.add_widget(title)
        chip_row = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(8))
        status_badge = StatusBadge(text='Planning', width=dp(110), bg_color=project_status_color('Planning'), text_color=project_status_text_color('Planning'))
        priority_badge = StatusBadge(text='Medium', width=dp(96), bg_color=priority_color('Medium'), text_color=priority_text_color('Medium'))
        pipeline_badge = StatusBadge(text='Lead', width=dp(126), bg_color=lead_stage_color('Lead'), text_color=lead_stage_text_color('Lead'))
        pin_badge = StatusBadge(text='Standard', width=dp(96), bg_color=CARD_2, text_color=TEXT)
        chip_row.add_widget(status_badge)
        chip_row.add_widget(priority_badge)
        chip_row.add_widget(pipeline_badge)
        chip_row.add_widget(pin_badge)
        top.add_widget(chip_row)
        meta = SmallLabel(text='')
        desc = SmallLabel(text='')
        summary = SmallLabel(text='', color=TEXT)
        top.add_widget(meta)
        top.add_widget(desc)
        top.add_widget(summary)
        content.add_widget(top)

        actions = Card(auto_height=True, spacing=dp(12))
        actions.add_widget(SectionTitle(text='Project Sections'))
        section_grid = GridLayout(cols=2, size_hint_y=None, height=dp(176), spacing=dp(12))
        checklist_btn = StyledButton(text='Checklists', height=dp(52))
        call_btn = StyledButton(text='Call Logs', height=dp(52))
        future_btn = StyledButton(text='Future Dev', height=dp(52))
        sales_btn = StyledButton(text='Sales Notes', height=dp(52))
        links_btn = SecondaryButton(text='Links & Files', height=dp(52))
        builds_btn = SecondaryButton(text='Build History', height=dp(52))
        for btn in (checklist_btn, call_btn, future_btn, sales_btn, links_btn, builds_btn):
            section_grid.add_widget(btn)
        actions.add_widget(section_grid)
        row2 = GridLayout(cols=3, size_hint_y=None, height=dp(48), spacing=dp(10))
        edit_btn = SecondaryButton(text='Edit Project', height=dp(48))
        pin_btn = SecondaryButton(text='Pin / Unpin', height=dp(48))
        archive_btn = SecondaryButton(text='Archive', height=dp(48))
        row2.add_widget(edit_btn)
        row2.add_widget(pin_btn)
        row2.add_widget(archive_btn)
        actions.add_widget(row2)
        content.add_widget(actions)

        bottom = BoxLayout(size_hint_y=None, height=dp(54), spacing=dp(12))
        back_btn = SecondaryButton(text='Back')
        del_btn = DangerButton(text='Delete Project')
        bottom.add_widget(back_btn)
        bottom.add_widget(del_btn)
        content.add_widget(bottom)

        checklist_btn.bind(on_release=lambda *_: self.open_checklists())
        call_btn.bind(on_release=lambda *_: self.open_calls())
        future_btn.bind(on_release=lambda *_: self.open_future_developments())
        sales_btn.bind(on_release=lambda *_: self.open_sales_notes())
        links_btn.bind(on_release=lambda *_: self.open_project_links_popup(screen.project_id))
        builds_btn.bind(on_release=lambda *_: self.open_build_history_popup(screen.project_id))
        edit_btn.bind(on_release=lambda *_: self.open_edit_project_popup(screen.project_id))
        pin_btn.bind(on_release=lambda *_: self.toggle_project_pin(screen.project_id))
        archive_btn.bind(on_release=lambda *_: self.toggle_archive_project(screen.project_id))
        back_btn.bind(on_release=lambda *_: self.go_projects())
        del_btn.bind(on_release=lambda *_: self.open_delete_project_popup(screen.project_id))

        screen.top_card = top
        screen.title_label = title
        screen.meta_label = meta
        screen.desc_label = desc
        screen.summary_label = summary
        screen.status_badge = status_badge
        screen.priority_badge = priority_badge
        screen.pipeline_badge = pipeline_badge
        screen.pin_badge = pin_badge
        return outer

    def build_checklist_list_ui(self, screen):
        outer, content = self._build_screen_shell(screen, "Checklists")

        top = Card(height=dp(214), spacing=dp(12))
        title = SectionTitle(text="Checklists")
        top.add_widget(title)
        top.add_widget(SmallLabel(text="Create and manage testing checklists. Import from Python templates when the list is huge."))
        row = BoxLayout(size_hint_y=None, height=dp(54), spacing=dp(12))
        new_btn = StyledButton(text="New Checklist")
        import_btn = SecondaryButton(text="Import Checklist .py")
        row.add_widget(new_btn)
        row.add_widget(import_btn)
        top.add_widget(row)
        content.add_widget(top)

        checklist_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(12))
        checklist_box.bind(minimum_height=checklist_box.setter("height"))
        content.add_widget(checklist_box)

        back_btn = SecondaryButton(text="Back", corner_radius=dp(24), height=dp(50))
        back_btn.bind(on_release=lambda *_: self.back_to_project_dashboard())
        content.add_widget(back_btn)

        new_btn.bind(on_release=lambda *_: self.open_new_checklist_popup())
        import_btn.bind(on_release=lambda *_: self.open_import_checklist_popup())

        screen.title_label = title
        screen.checklist_box = checklist_box
        return outer

    def build_checklist_detail_ui(self, screen):
        outer, content = self._build_screen_shell(screen, "Checklist Detail")

        top = Card(height=dp(186), spacing=dp(10))
        title_lbl = SectionTitle(text="Checklist")
        desc_lbl = SmallLabel(text="")
        top.add_widget(title_lbl)
        top.add_widget(desc_lbl)
        rename_row = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(12))
        rename_btn = SecondaryButton(text="Edit Name")
        add_btn_top = SecondaryButton(text="Add Item")
        rename_row.add_widget(rename_btn)
        rename_row.add_widget(add_btn_top)
        top.add_widget(rename_row)
        content.add_widget(top)

        row_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(12))
        row_box.bind(minimum_height=row_box.setter("height"))
        content.add_widget(row_box)

        buttons = BoxLayout(size_hint_y=None, height=dp(54), spacing=dp(12))
        save_btn = StyledButton(text="Save")
        back_btn = SecondaryButton(text="Back")
        buttons.add_widget(save_btn)
        buttons.add_widget(back_btn)
        content.add_widget(buttons)

        add_btn_top.bind(on_release=lambda *_: screen.add_item_popup())
        rename_btn.bind(on_release=lambda *_: self.open_rename_checklist_popup(screen.project_id, screen.checklist_id))
        save_btn.bind(on_release=lambda *_: screen.save_rows())
        back_btn.bind(on_release=lambda *_: self.back_to_checklist_list())

        screen.title_label = title_lbl
        screen.desc_label = desc_lbl
        screen.row_box = row_box
        return outer

    def build_call_list_ui(self, screen):
        outer, content = self._build_screen_shell(screen, 'Calls')

        top = Card(auto_height=True, spacing=dp(12))
        title = SectionTitle(text='Calls')
        top.add_widget(title)
        top.add_widget(SmallLabel(text='Store topic, client context, next action, follow-up date, outcome, and the sales pipeline stage for each call.'))
        new_btn = StyledButton(text='Add New Call')
        new_btn.bind(on_release=lambda *_: self.open_new_call_popup())
        top.add_widget(new_btn)
        content.add_widget(top)

        call_box = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(12))
        call_box.bind(minimum_height=call_box.setter('height'))
        content.add_widget(call_box)

        back_btn = SecondaryButton(text='Back', height=dp(50))
        back_btn.bind(on_release=lambda *_: self.back_to_project_dashboard())
        content.add_widget(back_btn)

        screen.title_label = title
        screen.call_box = call_box
        return outer

    def build_future_dev_ui(self, screen):
        outer, content = self._build_screen_shell(screen, 'Future Developments')

        top = Card(auto_height=True, spacing=dp(12))
        title = SectionTitle(text='Future Developments')
        summary = SmallLabel(text='In Process: 0    |    Done: 0    |    Discontinuing: 0', color=TEXT)
        top.add_widget(title)
        top.add_widget(SmallLabel(text='Track roadmap ideas here. Each item is color-coded by status, and you can mark urgent or pinned items for faster access.'))
        top.add_widget(summary)
        add_btn = StyledButton(text='Add Future Item')
        add_btn.bind(on_release=lambda *_: self.open_future_development_popup())
        top.add_widget(add_btn)
        content.add_widget(top)

        filter_card = Card(auto_height=True, spacing=dp(10))
        filter_card.add_widget(SectionTitle(text='Search + Filter'))
        screen.search_input = StyledInput(hint_text='Search future developments')
        screen.status_filter = StyledSpinner(text='All', values=['All'] + future_status_options())
        filter_card.add_widget(screen.search_input)
        filter_card.add_widget(screen.status_filter)
        content.add_widget(filter_card)
        screen.search_input.bind(text=lambda *_: screen.refresh())
        screen.status_filter.bind(text=lambda *_: screen.refresh())

        item_box = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(12))
        item_box.bind(minimum_height=item_box.setter('height'))
        content.add_widget(item_box)

        back_btn = SecondaryButton(text='Back', height=dp(50))
        back_btn.bind(on_release=lambda *_: self.back_to_project_dashboard())
        content.add_widget(back_btn)

        screen.title_label = title
        screen.summary_label = summary
        screen.item_box = item_box
        return outer

    def build_sales_notes_ui(self, screen):
        outer, content = self._build_screen_shell(screen, 'Sales Notes')

        top = Card(auto_height=True, spacing=dp(12))
        title = SectionTitle(text='Sales Notes')
        summary = SmallLabel(text='Saved notes: 0', color=TEXT)
        top.add_widget(title)
        top.add_widget(SmallLabel(text='Save buyer notes, pricing thoughts, proposal ideas, objections, and high-value follow-up notes.'))
        top.add_widget(summary)
        add_btn = StyledButton(text='Add Sales Note')
        add_btn.bind(on_release=lambda *_: self.open_sales_note_popup())
        top.add_widget(add_btn)
        content.add_widget(top)

        filter_card = Card(auto_height=True, spacing=dp(10))
        filter_card.add_widget(SectionTitle(text='Keyword Filter'))
        screen.search_input = StyledInput(hint_text='Filter sales notes by keyword')
        filter_card.add_widget(screen.search_input)
        screen.search_input.bind(text=lambda *_: screen.refresh())
        content.add_widget(filter_card)

        note_box = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(12))
        note_box.bind(minimum_height=note_box.setter('height'))
        content.add_widget(note_box)

        back_btn = SecondaryButton(text='Back', height=dp(50))
        back_btn.bind(on_release=lambda *_: self.back_to_project_dashboard())
        content.add_widget(back_btn)

        screen.title_label = title
        screen.summary_label = summary
        screen.note_box = note_box
        return outer

    def build_settings_ui(self, screen):
        outer, content = self._build_screen_shell(screen, 'Settings')
        security_card = Card(auto_height=True, spacing=dp(12))
        security_card.add_widget(SectionTitle(text='Security'))
        security_card.add_widget(SmallLabel(text='Use the master password to protect permanent project deletion. Default password is 8889 until you change it.'))
        pw_btn = StyledButton(text='Change Master Password')
        pw_btn.bind(on_release=lambda *_: self.open_change_password_popup())
        security_card.add_widget(pw_btn)
        content.add_widget(security_card)

        backup_card = Card(auto_height=True, spacing=dp(12))
        backup_card.add_widget(SectionTitle(text='Autosave + Backup Safety'))
        screen.autosave_box = CheckBox(active=bool(self.data_store.get('settings', {}).get('autosave_enabled', True)), size_hint=(None, None), size=(dp(30), dp(30)))
        screen.backup_start_box = CheckBox(active=bool(self.data_store.get('settings', {}).get('backup_on_start', False)), size_hint=(None, None), size=(dp(30), dp(30)))
        row1 = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(8))
        row1.add_widget(SmallLabel(text='Autosave after edits', color=TEXT))
        row1.add_widget(screen.autosave_box)
        row2 = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(8))
        row2.add_widget(SmallLabel(text='Create backup on app start', color=TEXT))
        row2.add_widget(screen.backup_start_box)
        backup_card.add_widget(row1)
        backup_card.add_widget(row2)
        screen.last_backup_label = SmallLabel(text='Last backup: Never', color=TEXT)
        backup_card.add_widget(screen.last_backup_label)
        save_settings_btn = SecondaryButton(text='Save Backup Settings', height=dp(48))
        quick_backup_btn = SecondaryButton(text='Create Backup Now', height=dp(48))
        save_settings_btn.bind(on_release=lambda *_: self.save_backup_settings(screen))
        quick_backup_btn.bind(on_release=lambda *_: self.create_quick_backup())
        backup_card.add_widget(save_settings_btn)
        backup_card.add_widget(quick_backup_btn)
        content.add_widget(backup_card)

        back_btn = SecondaryButton(text='Back to Main', height=dp(50))
        back_btn.bind(on_release=lambda *_: self.go_main())
        content.add_widget(back_btn)
        return outer

    def build_file_generator_hub_ui(self, screen):
        outer, content = self._build_screen_shell(screen, "File Generator", "Create helper files for your Android build workflows.")
        intro = Card(height=dp(172), spacing=dp(12))
        intro.add_widget(SectionTitle(text="Generators"))
        intro.add_widget(SmallLabel(text="Start with a generator module, then open the exact tool you need. Generated files are saved under Synapse by SHV/File Generator."))
        open_btn = StyledButton(text="GitHub APK File Generator", height=dp(54))
        open_btn.bind(on_release=lambda *_: self.go_github_apk_menu())
        intro.add_widget(open_btn)
        content.add_widget(intro)

        back_btn = SecondaryButton(text="Back to Main", height=dp(50))
        back_btn.bind(on_release=lambda *_: self.go_main())
        content.add_widget(back_btn)
        return outer

    def build_github_apk_menu_ui(self, screen):
        outer, content = self._build_screen_shell(screen, "GitHub APK File Generator", "Generate the core files for your GitHub APK build flow.")
        menu_card = Card(height=dp(320), spacing=dp(12))
        menu_card.add_widget(SectionTitle(text="Tools"))
        buildozer_btn = SecondaryButton(text="Generate buildozer.spec", height=dp(50))
        workflow_btn = SecondaryButton(text="Generate build.yml", height=dp(50))
        history_btn = SecondaryButton(text="Load History", height=dp(50))
        guide_btn = SecondaryButton(text="GitHub Build Guide", height=dp(50))
        buildozer_btn.bind(on_release=lambda *_: self.go_fg_buildozer())
        workflow_btn.bind(on_release=lambda *_: self.go_fg_workflow())
        history_btn.bind(on_release=lambda *_: self.go_fg_history())
        guide_btn.bind(on_release=lambda *_: self.go_fg_guide())
        menu_card.add_widget(buildozer_btn)
        menu_card.add_widget(workflow_btn)
        menu_card.add_widget(history_btn)
        menu_card.add_widget(guide_btn)
        content.add_widget(menu_card)

        back_btn = SecondaryButton(text="Back", height=dp(50))
        back_btn.bind(on_release=lambda *_: self.go_file_generator_hub())
        content.add_widget(back_btn)
        return outer

    def build_fg_buildozer_ui(self, screen):
        outer, content = self._build_screen_shell(screen, "buildozer.spec", "Generate a ready-to-edit buildozer.spec file.")
        card = Card(auto_height=True, spacing=dp(10), padding=[dp(16), dp(14), dp(16), dp(16)])
        card.add_widget(SectionTitle(text="App Settings"))

        screen.bd_title_input = StyledInput(hint_text="App title (e.g. My Kivy App)")
        screen.bd_package_input = StyledInput(hint_text="Package name (e.g. myapp)")
        screen.bd_domain_input = StyledInput(hint_text="Package domain (e.g. org.test)")
        screen.bd_version_input = StyledInput(hint_text="Version (e.g. 0.1)")
        screen.bd_requirements_input = StyledInput(hint_text="Requirements (e.g. python3,kivy)")

        card.add_widget(SmallLabel(text="App Title"))
        card.add_widget(screen.bd_title_input)
        card.add_widget(SmallLabel(text="Package Name"))
        card.add_widget(screen.bd_package_input)
        card.add_widget(SmallLabel(text="Package Domain"))
        card.add_widget(screen.bd_domain_input)
        card.add_widget(SmallLabel(text="Version"))
        card.add_widget(screen.bd_version_input)
        card.add_widget(SmallLabel(text="Requirements"))
        card.add_widget(screen.bd_requirements_input)

        card.add_widget(SectionTitle(text="Android Settings"))
        screen.bd_permissions_input = StyledInput(hint_text="Permissions (manual)")
        screen.bd_permissions_spinner = StyledSpinner(text="INTERNET", values=["INTERNET", "INTERNET, CAMERA", "INTERNET, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE", "INTERNET, VIBRATE"])
        screen.bd_orientation_input = StyledInput(hint_text="Orientation (manual)")
        screen.bd_orientation_spinner = StyledSpinner(text="portrait", values=["portrait", "landscape", "all"])
        screen.bd_api_input = StyledInput(hint_text="Android API (manual)")
        screen.bd_api_spinner = StyledSpinner(text="33", values=["35", "34", "33", "32", "31", "30"])
        screen.bd_min_input = StyledInput(hint_text="Min API (manual)")
        screen.bd_min_spinner = StyledSpinner(text="21", values=["21", "22", "23", "24", "26"])
        screen.bd_ndk_input = StyledInput(hint_text="NDK API (manual)")
        screen.bd_ndk_spinner = StyledSpinner(text="21", values=["21", "22", "23", "24"])
        screen.bd_arch_input = StyledInput(hint_text="Architectures (manual)")
        screen.bd_arch_spinner = StyledSpinner(text="arm64-v8a, armeabi-v7a", values=["arm64-v8a", "armeabi-v7a", "arm64-v8a, armeabi-v7a"])

        for label_text, widget in [
            ("Permissions", screen.bd_permissions_input),
            ("Permissions Preset", screen.bd_permissions_spinner),
            ("Orientation", screen.bd_orientation_input),
            ("Orientation Preset", screen.bd_orientation_spinner),
            ("Android API", screen.bd_api_input),
            ("Android API Preset", screen.bd_api_spinner),
            ("Min API", screen.bd_min_input),
            ("Min API Preset", screen.bd_min_spinner),
            ("NDK API", screen.bd_ndk_input),
            ("NDK API Preset", screen.bd_ndk_spinner),
            ("Architectures", screen.bd_arch_input),
            ("Architecture Preset", screen.bd_arch_spinner),
        ]:
            card.add_widget(SmallLabel(text=label_text))
            card.add_widget(widget)

        content.add_widget(card)

        btn_stack = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(114), spacing=dp(10))
        save_btn = StyledButton(text="Save buildozer.spec", height=dp(52))
        back_btn = SecondaryButton(text="Back", height=dp(52))
        save_btn.bind(on_release=lambda *_: self.save_fg_buildozer())
        back_btn.bind(on_release=lambda *_: self.go_github_apk_menu())
        btn_stack.add_widget(save_btn)
        btn_stack.add_widget(back_btn)
        content.add_widget(btn_stack)
        return outer

    def build_fg_workflow_ui(self, screen):
        outer, content = self._build_screen_shell(screen, "build.yml", "Generate a GitHub Actions workflow file for APK builds.")
        card = Card(auto_height=True, spacing=dp(10), padding=[dp(16), dp(14), dp(16), dp(16)])
        screen.wf_name_input = StyledInput(hint_text="Workflow name (e.g. Build APK)")
        screen.wf_branch_input = StyledInput(hint_text="Branch (e.g. main)")
        screen.wf_python_input = StyledInput(hint_text="Python version (e.g. 3.11)")
        screen.wf_ubuntu_input = StyledInput(hint_text="Ubuntu version (manual)")
        screen.wf_ubuntu_spinner = StyledSpinner(text="ubuntu-22.04", values=["ubuntu-latest", "ubuntu-24.04", "ubuntu-22.04", "ubuntu-20.04"])
        screen.wf_java_input = StyledInput(hint_text="Java version (manual)")
        screen.wf_java_spinner = StyledSpinner(text="17", values=["17", "21", "11", "8"])
        screen.wf_cmd_input = StyledInput(hint_text="Build command (e.g. buildozer android debug)")

        for label_text, widget in [
            ("Workflow Name", screen.wf_name_input),
            ("Branch", screen.wf_branch_input),
            ("Python Version", screen.wf_python_input),
            ("Ubuntu Version", screen.wf_ubuntu_input),
            ("Ubuntu Preset", screen.wf_ubuntu_spinner),
            ("Java Version", screen.wf_java_input),
            ("Java Preset", screen.wf_java_spinner),
            ("Build Command", screen.wf_cmd_input),
        ]:
            card.add_widget(SmallLabel(text=label_text))
            card.add_widget(widget)

        content.add_widget(card)

        btn_stack = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(114), spacing=dp(10))
        save_btn = StyledButton(text="Save build.yml", height=dp(52))
        back_btn = SecondaryButton(text="Back", height=dp(52))
        save_btn.bind(on_release=lambda *_: self.save_fg_workflow())
        back_btn.bind(on_release=lambda *_: self.go_github_apk_menu())
        btn_stack.add_widget(save_btn)
        btn_stack.add_widget(back_btn)
        content.add_widget(btn_stack)
        return outer

    def build_fg_history_ui(self, screen):
        outer, content = self._build_screen_shell(screen, "Generation History", "Review the files generated by the GitHub APK File Generator.")
        history_card = Card(auto_height=True, spacing=dp(10))
        screen.history_label = StyledMultiline(text="No history yet.", readonly=True, height=dp(340))
        history_card.add_widget(screen.history_label)
        content.add_widget(history_card)

        btn_row = BoxLayout(size_hint_y=None, height=dp(54), spacing=dp(12))
        clear_btn = DangerButton(text="Clear History")
        back_btn = SecondaryButton(text="Back")
        clear_btn.bind(on_release=lambda *_: self.clear_fg_history_and_refresh())
        back_btn.bind(on_release=lambda *_: self.go_github_apk_menu())
        btn_row.add_widget(clear_btn)
        btn_row.add_widget(back_btn)
        content.add_widget(btn_row)
        return outer

    def build_fg_guide_ui(self, screen):
        outer, content = self._build_screen_shell(screen, "GitHub Build Guide", "Quick steps for using the generated APK build files.")
        guide_card = Card(auto_height=True, spacing=dp(10))
        guide_card.add_widget(SmallLabel(text='Use Copy Guide to grab the full text exactly as shown below.', color=TEXT))
        guide_card.add_widget(StyledMultiline(text=GITHUB_APK_BUILD_GUIDE, readonly=True, height=dp(520)))
        content.add_widget(guide_card)

        btn_row = BoxLayout(size_hint_y=None, height=dp(54), spacing=dp(12))
        copy_btn = SecondaryButton(text="Copy Guide")
        back_btn = SecondaryButton(text="Back")
        copy_btn.bind(on_release=lambda *_: self.copy_fg_guide())
        back_btn.bind(on_release=lambda *_: self.go_github_apk_menu())
        btn_row.add_widget(copy_btn)
        btn_row.add_widget(back_btn)
        content.add_widget(btn_row)
        return outer

    # ---------- data access ----------
    def get_project(self, project_id):
        for project in self.data_store.get("projects", []):
            if project.get("id") == project_id:
                return project
        return None

    def get_checklist(self, project_id, checklist_id):
        project = self.get_project(project_id)
        if not project:
            return None
        for checklist in project.get("checklists", []):
            if checklist.get("id") == checklist_id:
                return checklist
        return None

    def get_future_development(self, project_id, item_id):
        project = self.get_project(project_id)
        if not project:
            return None
        for item in project.get("future_developments", []):
            if item.get("id") == item_id:
                return item
        return None

    def get_sales_note(self, project_id, note_id):
        project = self.get_project(project_id)
        if not project:
            return None
        for note in project.get("sales_notes", []):
            if note.get("id") == note_id:
                return note
        return None

    def get_project_summary(self, project):
        project = self.normalize_project(project or {})
        qa_total = sum(len(checklist.get('items', [])) for checklist in project.get('checklists', []))
        qa_done = sum(sum(1 for item in checklist.get('items', []) if item.get('done')) for checklist in project.get('checklists', []))
        return {
            'checklists': len(project.get('checklists', [])),
            'calls': len(project.get('calls', [])),
            'future': len(project.get('future_developments', [])),
            'sales': len(project.get('sales_notes', [])),
            'builds': len(project.get('build_history', [])),
            'qa_total': qa_total,
            'qa_done': qa_done,
        }

    def touch_project(self, project, activity_label='Updated'):
        stamp = now_str()
        project['updated_at'] = stamp
        project['last_edited_at'] = stamp
        project['last_activity_at'] = stamp
        if activity_label:
            project['last_activity_note'] = activity_label

    def copy_text(self, text, success_message='Copied to clipboard.'):
        if Clipboard is None:
            show_message('Clipboard Unavailable', 'Clipboard is not available on this device right now.')
            return
        try:
            Clipboard.copy(str(text or ''))
            show_message('Copied', success_message)
        except Exception as e:
            show_message('Copy Failed', str(e))

    def get_dashboard_metrics(self):
        projects = [self.normalize_project(p) for p in self.data_store.get('projects', [])]
        checklists = calls = future_count = sales_count = done = total = 0
        active_projects = 0
        overdue = 0
        future_status_counts = {status: 0 for status in future_status_options()}
        latest_sales = None
        latest_sales_date = None
        next_call = None
        next_call_date = None
        pinned_projects = 0
        for project in projects:
            if project.get('pinned') and not project.get('archived'):
                pinned_projects += 1
            summary = self.get_project_summary(project)
            checklists += summary['checklists']
            calls += summary['calls']
            future_count += summary['future']
            sales_count += summary['sales']
            done += summary['qa_done']
            total += summary['qa_total']
            if project.get('status') == 'Active' and not project.get('archived'):
                active_projects += 1
            for item in project.get('future_developments', []):
                future_status_counts[item.get('status', 'In Process')] = future_status_counts.get(item.get('status', 'In Process'), 0) + 1
            for call_item in project.get('calls', []):
                if followup_is_overdue(call_item):
                    overdue += 1
                cdt = parse_datetime_maybe(call_item.get('date'))
                if cdt and cdt >= datetime.now() and (next_call_date is None or cdt < next_call_date):
                    next_call_date = cdt
                    next_call = (project.get('name', 'Project'), call_item)
            for note in project.get('sales_notes', []):
                ndt = parse_datetime_maybe(note.get('updated_at')) or parse_datetime_maybe(note.get('created_at'))
                if ndt and (latest_sales_date is None or ndt > latest_sales_date):
                    latest_sales_date = ndt
                    latest_sales = (project.get('name', 'Project'), note)
        latest_sales_preview = 'No sales notes yet.'
        if latest_sales:
            latest_sales_preview = f"{latest_sales[0]} • {latest_sales[1].get('heading', 'Note')}"
        next_call_preview = 'No planned call yet.'
        if next_call:
            next_call_preview = f"{next_call[0]} • {next_call[1].get('title', 'Call')}\n{next_call[1].get('date', '')}"
        return {
            'project_count': len(projects),
            'checklists': checklists,
            'calls': calls,
            'future': future_count,
            'sales': sales_count,
            'qa_done': done,
            'qa_total': total,
            'projects_in_progress': active_projects,
            'overdue_followups': overdue,
            'future_status_counts': future_status_counts,
            'latest_sales_preview': latest_sales_preview,
            'next_call_preview': next_call_preview,
            'pinned_projects': pinned_projects,
        }

    def build_export_payload(self):
        projects = [self.normalize_project(copy.deepcopy(project)) for project in self.data_store.get('projects', [])]
        settings = copy.deepcopy(self.data_store.get('settings', {}))
        settings.setdefault('master_password', self.get_master_password())
        settings.setdefault('autosave_enabled', True)
        settings.setdefault('backup_on_start', False)
        settings.setdefault('file_generator', {})
        settings.setdefault('last_backup_at', '')
        return {'projects': projects, 'settings': settings}

    def create_backup_file(self, reason='manual'):
        export_dir = get_export_root_dir()
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"synapse_backup_{reason}_{stamp}.json"
        path = make_unique_path(export_dir, filename)
        backup_time = now_str()
        payload = self.build_export_payload()
        payload.setdefault('settings', {})['last_backup_at'] = backup_time
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        self.data_store.setdefault('settings', {})['last_backup_at'] = backup_time
        self.save_data()
        return path

    def create_quick_backup(self):
        try:
            path = self.create_backup_file('manual')
            show_message('Backup Created', f'Backup saved successfully:\n{path}')
        except Exception as e:
            show_message('Backup Failed', str(e))

    def save_backup_settings(self, screen):
        settings = self.data_store.setdefault('settings', {})
        settings['autosave_enabled'] = bool(screen.autosave_box.active)
        settings['backup_on_start'] = bool(screen.backup_start_box.active)
        self.save_data()
        show_message('Saved', 'Backup settings updated.')

    def toggle_archive_project(self, project_id):
        project = self.get_project(project_id)
        if not project:
            return
        project['archived'] = not bool(project.get('archived', False))
        self.touch_project(project, 'Archive toggled')
        self.save_data()
        self.refresh_all()

    def toggle_project_pin(self, project_id):
        project = self.get_project(project_id)
        if not project:
            return
        project['pinned'] = not bool(project.get('pinned', False))
        self.touch_project(project, 'Pin toggled')
        self.save_data()
        self.refresh_all()

    def open_project_links_popup(self, project_id):
        project = self.get_project(project_id)
        if not project:
            return
        attachments = project.setdefault('attachments', {})
        box = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12))
        repo_input = StyledInput(text=attachments.get('github_repo', ''), hint_text='GitHub repo link')
        play_input = StyledInput(text=attachments.get('play_store', ''), hint_text='Play Store link')
        apk_input = StyledInput(text=attachments.get('apk_path', ''), hint_text='APK file path')
        shots_input = StyledInput(text=attachments.get('screenshots_path', ''), hint_text='Screenshots folder path')
        contact_input = StyledMultiline(text=attachments.get('client_contact', ''), hint_text='Client contact details', height=dp(120))
        for lbl, widget in [('GitHub Repo', repo_input), ('Play Store', play_input), ('APK Path', apk_input), ('Screenshots Folder', shots_input), ('Client Contact', contact_input)]:
            box.add_widget(SmallLabel(text=lbl, color=TEXT))
            box.add_widget(widget)
        btn_row = GridLayout(cols=3, size_hint_y=None, height=dp(50), spacing=dp(10))
        save_btn = StyledButton(text='Save', height=dp(48))
        copy_btn = SecondaryButton(text='Copy Contact', height=dp(48))
        cancel_btn = SecondaryButton(text='Close', height=dp(48))
        btn_row.add_widget(save_btn)
        btn_row.add_widget(copy_btn)
        btn_row.add_widget(cancel_btn)
        box.add_widget(btn_row)
        pop = open_popup('Links & Files', box, size=(0.94, 0.92))

        def do_save(*_):
            attachments['github_repo'] = repo_input.text.strip()
            attachments['play_store'] = play_input.text.strip()
            attachments['apk_path'] = apk_input.text.strip()
            attachments['screenshots_path'] = shots_input.text.strip()
            attachments['client_contact'] = contact_input.text.strip()
            self.touch_project(project, 'Attachments updated')
            self.save_data()
            pop.dismiss()
            self.refresh_all()

        save_btn.bind(on_release=do_save)
        copy_btn.bind(on_release=lambda *_: self.copy_text(contact_input.text.strip(), 'Client contact copied.'))
        cancel_btn.bind(on_release=pop.dismiss)
        pop.open()

    def open_build_history_popup(self, project_id):
        project = self.get_project(project_id)
        if not project:
            return
        outer = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12))
        outer.add_widget(SmallLabel(text='Track version, build type, result, date, and notes for each build.', color=TEXT))
        scroll = ScrollView(bar_width=dp(3), scroll_type=['bars', 'content'])
        content = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(10))
        content.bind(minimum_height=content.setter('height'))
        scroll.add_widget(content)
        outer.add_widget(scroll)

        def render_entries():
            content.clear_widgets()
            builds = list(reversed(project.get('build_history', [])))
            if not builds:
                empty = Card(auto_height=True)
                empty.add_widget(SectionTitle(text='No build history yet'))
                empty.add_widget(SmallLabel(text='Add build records to keep version and release notes organized.'))
                content.add_widget(empty)
                return
            for build in builds:
                card = Card(auto_height=True, spacing=dp(8), bg_color=mix_color(CARD, GREEN if build.get('result') == 'Success' else LIGHT_RED, 0.14))
                head = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(8))
                head.add_widget(SectionTitle(text=f"v{build.get('version', '0.1')}"))
                head.add_widget(StatusBadge(text=build.get('result', 'Success'), width=dp(90), bg_color=GREEN if build.get('result') == 'Success' else LIGHT_RED, text_color=TEXT))
                card.add_widget(head)
                card.add_widget(SmallLabel(text=f"Date: {build.get('date', '-')}    |    Type: {build.get('build_type', '-') or '-'}"))
                card.add_widget(SmallLabel(text=build.get('notes', 'No notes') or 'No notes', color=TEXT))
                del_btn = DangerButton(text='Delete Record', height=dp(42))
                del_btn.bind(on_release=lambda *_args, bid=build['id']: self.delete_build_record(project_id, bid, pop))
                card.add_widget(del_btn)
                content.add_widget(card)

        btn_row = GridLayout(cols=2, size_hint_y=None, height=dp(50), spacing=dp(10))
        add_btn = StyledButton(text='Add Build Record', height=dp(48))
        close_btn = SecondaryButton(text='Close', height=dp(48))
        btn_row.add_widget(add_btn)
        btn_row.add_widget(close_btn)
        outer.add_widget(btn_row)
        pop = open_popup('Build History', outer, size=(0.95, 0.95))
        add_btn.bind(on_release=lambda *_: self.open_build_record_popup(project_id, render_entries))
        close_btn.bind(on_release=pop.dismiss)
        render_entries()
        pop.open()

    def open_build_record_popup(self, project_id, refresh_callback=None):
        project = self.get_project(project_id)
        if not project:
            return
        box = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12))
        version_input = StyledInput(hint_text='Version (e.g. 1.0.3)')
        date_input = StyledInput(text=now_str(), hint_text='Date')
        type_spin = StyledSpinner(text='Debug APK', values=build_type_options())
        result_spin = StyledSpinner(text='Success', values=build_result_options())
        notes_input = StyledMultiline(hint_text='Notes', height=dp(140))
        for lbl, widget in [('Version', version_input), ('Date', date_input), ('Build Type', type_spin), ('Result', result_spin), ('Notes', notes_input)]:
            box.add_widget(SmallLabel(text=lbl, color=TEXT))
            box.add_widget(widget)
        btn_row = GridLayout(cols=2, size_hint_y=None, height=dp(50), spacing=dp(10))
        save_btn = StyledButton(text='Save Record', height=dp(48))
        cancel_btn = SecondaryButton(text='Cancel', height=dp(48))
        btn_row.add_widget(save_btn)
        btn_row.add_widget(cancel_btn)
        box.add_widget(btn_row)
        pop = open_popup('Add Build Record', box, size=(0.92, 0.86))

        def do_save(*_):
            version = version_input.text.strip() or '0.1'
            project.setdefault('build_history', []).append({
                'id': str(uuid.uuid4()),
                'version': version,
                'date': date_input.text.strip() or now_str(),
                'build_type': type_spin.text.strip() or 'Debug APK',
                'result': result_spin.text.strip() or 'Success',
                'notes': notes_input.text.strip(),
            })
            self.touch_project(project, 'Build history updated')
            self.save_data()
            pop.dismiss()
            if refresh_callback:
                refresh_callback()
            self.refresh_all()

        save_btn.bind(on_release=do_save)
        cancel_btn.bind(on_release=pop.dismiss)
        pop.open()

    def delete_build_record(self, project_id, build_id, parent_popup=None):
        project = self.get_project(project_id)
        if not project:
            return
        project['build_history'] = [b for b in project.get('build_history', []) if b.get('id') != build_id]
        self.touch_project(project, 'Build record removed')
        self.save_data()
        self.refresh_all()
        if parent_popup:
            parent_popup.dismiss()
            self.open_build_history_popup(project_id)

    def get_master_password(self):
        settings = self.data_store.setdefault('settings', {})
        password = settings.get('master_password') or '8889'
        settings['master_password'] = password
        return password

    def get_fg_settings(self):
        settings = self.data_store.setdefault('settings', {})
        fg_settings = settings.setdefault('file_generator', {})
        return fg_settings

    # ---------- navigation ----------
    def go_main(self):
        self.sm.current = "main"
        self.sm.get_screen("main").refresh()

    def go_projects(self):
        self.sm.current = "projects"
        self.sm.get_screen("projects").refresh()

    def go_settings(self):
        self.sm.current = "settings"
        self.sm.get_screen("settings").refresh()

    def go_file_generator_hub(self):
        self.sm.current = "file_generator_hub"
        self.sm.get_screen("file_generator_hub").refresh()

    def go_github_apk_menu(self):
        self.sm.current = "github_apk_menu"
        self.sm.get_screen("github_apk_menu").refresh()

    def go_fg_buildozer(self):
        self.populate_fg_fields()
        self.sm.current = "fg_buildozer"
        self.sm.get_screen("fg_buildozer").refresh()

    def go_fg_workflow(self):
        self.populate_fg_fields()
        self.sm.current = "fg_workflow"
        self.sm.get_screen("fg_workflow").refresh()

    def go_fg_history(self):
        self.sm.current = "fg_history"
        self.sm.get_screen("fg_history").refresh()

    def go_fg_guide(self):
        self.sm.current = "fg_guide"
        self.sm.get_screen("fg_guide").refresh()

    def open_project(self, project_id):
        self.current_project_id = project_id
        screen = self.sm.get_screen("project")
        screen.project_id = project_id
        self.sm.current = "project"

    def back_to_project_dashboard(self):
        if not self.current_project_id:
            self.go_projects()
            return
        self.open_project(self.current_project_id)

    def open_checklists(self):
        if not self.current_project_id:
            return
        screen = self.sm.get_screen("checklists")
        screen.project_id = self.current_project_id
        self.sm.current = "checklists"

    def open_checklist(self, project_id, checklist_id):
        self.current_project_id = project_id
        screen = self.sm.get_screen("checklist_detail")
        screen.project_id = project_id
        screen.checklist_id = checklist_id
        self.sm.current = "checklist_detail"

    def back_to_checklist_list(self):
        screen = self.sm.get_screen("checklists")
        screen.project_id = self.current_project_id
        self.sm.current = "checklists"

    def open_calls(self):
        if not self.current_project_id:
            return
        screen = self.sm.get_screen("calls")
        screen.project_id = self.current_project_id
        self.sm.current = "calls"

    def open_future_developments(self):
        if not self.current_project_id:
            return
        screen = self.sm.get_screen("future_dev")
        screen.project_id = self.current_project_id
        self.sm.current = "future_dev"

    def open_sales_notes(self):
        if not self.current_project_id:
            return
        screen = self.sm.get_screen("sales_notes")
        screen.project_id = self.current_project_id
        self.sm.current = "sales_notes"

    # ---------- import/export ----------
    def export_all_data(self):
        export_dir = get_export_root_dir()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"synapse_export_{stamp}.json"
        path = make_unique_path(export_dir, filename)
        try:
            export_time = now_str()
            payload = self.build_export_payload()
            payload.setdefault("settings", {})["last_backup_at"] = export_time
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            self.data_store.setdefault("settings", {})["last_backup_at"] = export_time
            self.save_data()
            show_message("Export Complete", f"Full Synapse backup saved successfully:\n{path}")
        except Exception as e:
            show_message("Export Failed", str(e))

    def open_import_data_popup(self):
        selected_path = {"value": ""}
        box = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
        box.add_widget(SmallLabel(text="Import a full Synapse data backup from a .json file or paste the JSON directly. Every project imports with its checklists, calls, future developments, sales notes, build history, links/files, statuses, pins, archive state, and timestamps. Use Merge to add projects, or Replace to overwrite everything.", color=TEXT))

        chooser_card = Card(height=dp(250), padding=dp(12), spacing=dp(8))
        chooser_card.add_widget(SmallLabel(text="Pick a JSON export file", color=TEXT))
        chooser = FileChooserListView(path=get_file_picker_start_path(), filters=["*.json"], multiselect=False)
        chooser_card.add_widget(chooser)
        selected_lbl = SmallLabel(text="Selected file: None")
        chooser_card.add_widget(selected_lbl)
        box.add_widget(chooser_card)

        code_header = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        code_header.add_widget(SectionTitle(text="Or paste JSON backup"))
        paste_btn = SecondaryButton(text="Paste", size_hint_x=None, width=dp(108))
        clear_btn = SecondaryButton(text="Clear", size_hint_x=None, width=dp(108))
        code_header.add_widget(paste_btn)
        code_header.add_widget(clear_btn)
        box.add_widget(code_header)

        code_input = StyledMultiline(hint_text="Paste export JSON here", height=dp(180))
        box.add_widget(code_input)

        btn_row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(10))
        merge_btn = StyledButton(text="Merge Import")
        replace_btn = DangerButton(text="Replace All")
        cancel_btn = SecondaryButton(text="Cancel")
        btn_row.add_widget(merge_btn)
        btn_row.add_widget(replace_btn)
        btn_row.add_widget(cancel_btn)
        box.add_widget(btn_row)

        pop = open_popup("Import Data", box, size=(0.96, 0.96))

        def update_selected(*_):
            selection = chooser.selection or []
            selected_path["value"] = selection[0] if selection else ""
            selected_lbl.text = f"Selected file: {selected_path['value'] or 'None'}"

        def do_paste(*_):
            text = ""
            if Clipboard is not None:
                try:
                    text = Clipboard.paste() or ""
                except Exception:
                    text = ""
            if not text:
                show_message("Clipboard Empty", "There was no text available to paste.")
                return
            code_input.text = text

        def do_clear(*_):
            code_input.text = ""

        def _read_import_payload():
            if code_input.text.strip():
                raw = code_input.text
            elif selected_path["value"]:
                raw = read_text_file(selected_path["value"])
            else:
                raise ValueError("Pick a .json file or paste backup JSON first.")
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError("Imported data must be a JSON object.")
            projects = payload.get("projects", [])
            if not isinstance(projects, list):
                raise ValueError("Imported data must contain a projects list.")
            settings = payload.get("settings", {})
            if not isinstance(settings, dict):
                settings = {}
            settings.setdefault("master_password", self.get_master_password())
            settings.setdefault("autosave_enabled", True)
            settings.setdefault("backup_on_start", False)
            settings.setdefault("file_generator", {})
            settings.setdefault("last_backup_at", "")
            return {
                "projects": [self.normalize_project(copy.deepcopy(project)) for project in projects],
                "settings": settings,
            }

        def do_merge(*_):
            try:
                payload = _read_import_payload()
                existing = self.data_store.setdefault("projects", [])
                existing_ids = {p.get("id") for p in existing}
                for project in payload.get("projects", []):
                    if project.get("id") in existing_ids:
                        project = dict(project)
                        project["id"] = str(uuid.uuid4())
                    existing.append(project)
                self.save_data()
                pop.dismiss()
                self.refresh_all()
                show_message("Imported", "Data merged successfully.")
            except Exception as e:
                show_message("Import Error", str(e))

        def do_replace(*_):
            try:
                payload = _read_import_payload()
                self.data_store = payload
                self.save_data()
                pop.dismiss()
                self.refresh_all()
                show_message("Imported", "All data replaced successfully.")
            except Exception as e:
                show_message("Import Error", str(e))

        chooser.bind(selection=update_selected)
        paste_btn.bind(on_release=do_paste)
        clear_btn.bind(on_release=do_clear)
        merge_btn.bind(on_release=do_merge)
        replace_btn.bind(on_release=do_replace)
        cancel_btn.bind(on_release=pop.dismiss)
        pop.open()

    # ---------- project ops ----------
    def open_new_project_popup(self):
        box = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12))
        name_input = StyledInput(hint_text='Project name')
        duration_input = StyledInput(hint_text='Duration (e.g. 2 weeks / ongoing)')
        client_input = StyledInput(hint_text='Client / company / category')
        description_input = StyledMultiline(hint_text='Basic project description', height=dp(120))
        status_spin = StyledSpinner(text='Planning', values=project_status_options())
        priority_spin = StyledSpinner(text='Medium', values=priority_options())
        stage_spin = StyledSpinner(text='Lead', values=lead_stage_options())
        pin_box = CheckBox(active=False, size_hint=(None, None), size=(dp(30), dp(30)))

        box.add_widget(name_input)
        box.add_widget(duration_input)
        box.add_widget(client_input)
        box.add_widget(description_input)
        box.add_widget(SmallLabel(text='Project Status', color=TEXT))
        box.add_widget(status_spin)
        box.add_widget(SmallLabel(text='Priority', color=TEXT))
        box.add_widget(priority_spin)
        box.add_widget(SmallLabel(text='Sales Pipeline', color=TEXT))
        box.add_widget(stage_spin)
        pin_row = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(8))
        pin_row.add_widget(SmallLabel(text='Pin this project', color=TEXT))
        pin_row.add_widget(pin_box)
        box.add_widget(pin_row)

        btn_row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(10))
        save_btn = StyledButton(text='Create Project')
        cancel_btn = SecondaryButton(text='Cancel')
        btn_row.add_widget(save_btn)
        btn_row.add_widget(cancel_btn)
        box.add_widget(btn_row)

        pop = open_popup('Create New Project', box, size=(0.94, 0.94))

        def do_save(*_):
            project_name = name_input.text.strip()
            if not project_name:
                show_message('Missing Name', 'Please enter a project name.')
                return
            stamp = now_str()
            project = {
                'id': str(uuid.uuid4()),
                'name': project_name,
                'duration': duration_input.text.strip(),
                'client': client_input.text.strip(),
                'description': description_input.text.strip(),
                'status': status_spin.text.strip() or 'Planning',
                'priority': priority_spin.text.strip() or 'Medium',
                'pipeline_stage': stage_spin.text.strip() or 'Lead',
                'archived': False,
                'pinned': bool(pin_box.active),
                'created_at': stamp,
                'updated_at': stamp,
                'last_edited_at': stamp,
                'last_activity_at': stamp,
                'attachments': {
                    'github_repo': '', 'play_store': '', 'apk_path': '', 'screenshots_path': '', 'client_contact': ''
                },
                'build_history': [],
                'checklists': [],
                'calls': [],
                'future_developments': [],
                'sales_notes': [],
            }
            self.data_store.setdefault('projects', []).append(project)
            self.save_data()
            pop.dismiss()
            self.go_projects()
            self.refresh_all()

        save_btn.bind(on_release=do_save)
        cancel_btn.bind(on_release=pop.dismiss)
        pop.open()

    def open_edit_project_popup(self, project_id):
        project = self.get_project(project_id)
        if not project:
            return
        box = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12))
        name_input = StyledInput(text=project.get('name', ''), hint_text='Project name')
        duration_input = StyledInput(text=project.get('duration', ''), hint_text='Duration')
        client_input = StyledInput(text=project.get('client', ''), hint_text='Client / company / category')
        description_input = StyledMultiline(text=project.get('description', ''), hint_text='Project description', height=dp(120))
        status_spin = StyledSpinner(text=project.get('status', 'Planning'), values=project_status_options())
        priority_spin = StyledSpinner(text=project.get('priority', 'Medium'), values=priority_options())
        stage_spin = StyledSpinner(text=project.get('pipeline_stage', 'Lead'), values=lead_stage_options())
        pin_box = CheckBox(active=bool(project.get('pinned', False)), size_hint=(None, None), size=(dp(30), dp(30)))

        for widget in (name_input, duration_input, client_input, description_input):
            box.add_widget(widget)
        for lbl, widget in [('Project Status', status_spin), ('Priority', priority_spin), ('Sales Pipeline', stage_spin)]:
            box.add_widget(SmallLabel(text=lbl, color=TEXT))
            box.add_widget(widget)
        pin_row = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(8))
        pin_row.add_widget(SmallLabel(text='Pin this project', color=TEXT))
        pin_row.add_widget(pin_box)
        box.add_widget(pin_row)

        btn_row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(10))
        save_btn = StyledButton(text='Save Changes')
        cancel_btn = SecondaryButton(text='Cancel')
        btn_row.add_widget(save_btn)
        btn_row.add_widget(cancel_btn)
        box.add_widget(btn_row)

        pop = open_popup('Edit Project', box, size=(0.94, 0.94))

        def do_save(*_):
            if not name_input.text.strip():
                show_message('Missing Name', 'Please enter a project name.')
                return
            project['name'] = name_input.text.strip()
            project['duration'] = duration_input.text.strip()
            project['client'] = client_input.text.strip()
            project['description'] = description_input.text.strip()
            project['status'] = status_spin.text.strip() or 'Planning'
            project['priority'] = priority_spin.text.strip() or 'Medium'
            project['pipeline_stage'] = stage_spin.text.strip() or 'Lead'
            project['pinned'] = bool(pin_box.active)
            self.touch_project(project, 'Project details updated')
            self.save_data()
            pop.dismiss()
            self.refresh_all()

        save_btn.bind(on_release=do_save)
        cancel_btn.bind(on_release=pop.dismiss)
        pop.open()

    def open_delete_project_popup(self, project_id):
        project = self.get_project(project_id)
        if not project:
            return
        box = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12))
        box.add_widget(SmallLabel(text=f"Archive is the safer option. Enter the master password only if you want to permanently delete:\n{project.get('name', 'Project')}", color=TEXT))
        pw_input = StyledInput(hint_text='Master password', password=True)
        box.add_widget(pw_input)
        btn_row = GridLayout(cols=3, size_hint_y=None, height=dp(52), spacing=dp(10))
        archive_btn = SecondaryButton(text='Archive', height=dp(50))
        delete_btn = DangerButton(text='Permanent Delete', height=dp(50))
        cancel_btn = SecondaryButton(text='Cancel', height=dp(50))
        btn_row.add_widget(archive_btn)
        btn_row.add_widget(delete_btn)
        btn_row.add_widget(cancel_btn)
        box.add_widget(btn_row)
        pop = open_popup('Delete Project', box, size=(0.94, 0.46))

        def do_archive(*_):
            project['archived'] = True
            self.touch_project(project, 'Project archived')
            self.save_data()
            pop.dismiss()
            self.go_projects()
            self.refresh_all()

        def do_delete(*_):
            if pw_input.text.strip() != self.get_master_password():
                show_message('Wrong Password', 'The master password is incorrect.')
                return
            self.data_store['projects'] = [p for p in self.data_store.get('projects', []) if p.get('id') != project_id]
            self.save_data()
            if self.current_project_id == project_id:
                self.current_project_id = None
            pop.dismiss()
            self.go_projects()
            self.refresh_all()

        archive_btn.bind(on_release=do_archive)
        delete_btn.bind(on_release=do_delete)
        cancel_btn.bind(on_release=pop.dismiss)
        pop.open()

    def open_new_checklist_popup(self):
        if not self.current_project_id:
            return
        box = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
        name = StyledInput(hint_text="Checklist name (e.g. QA Smoke Test)")
        description = StyledMultiline(hint_text="Optional notes / purpose for this checklist", height=dp(120))
        btn_row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(10))
        create_btn = StyledButton(text="Create")
        cancel_btn = SecondaryButton(text="Cancel")
        btn_row.add_widget(create_btn)
        btn_row.add_widget(cancel_btn)
        box.add_widget(name)
        box.add_widget(description)
        box.add_widget(btn_row)
        pop = open_popup("New Checklist", box, size=(0.92, 0.52))

        def do_create(*_):
            project = self.get_project(self.current_project_id)
            if project is None:
                pop.dismiss()
                return
            checklist_name = name.text.strip()
            if not checklist_name:
                show_message("Missing Name", "Please enter a checklist name.")
                return
            checklist = {
                "id": str(uuid.uuid4()),
                "name": checklist_name,
                "description": description.text.strip(),
                "created_at": now_str(),
                "items": [],
            }
            project.setdefault('checklists', []).append(checklist)
            self.touch_project(project, 'Checklist created')
            self.save_data()
            pop.dismiss()
            self.sm.get_screen('checklists').refresh()
            self.refresh_all()

        create_btn.bind(on_release=do_create)
        cancel_btn.bind(on_release=pop.dismiss)
        pop.open()

    def open_rename_checklist_popup(self, project_id, checklist_id):
        checklist = self.get_checklist(project_id, checklist_id)
        if checklist is None:
            return
        box = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
        name_input = StyledInput(text=checklist.get("name", ""), hint_text="Checklist name")
        desc_input = StyledMultiline(text=checklist.get("description", ""), hint_text="Description", height=dp(120))
        btn_row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(10))
        save_btn = StyledButton(text="Save")
        cancel_btn = SecondaryButton(text="Cancel")
        btn_row.add_widget(save_btn)
        btn_row.add_widget(cancel_btn)
        box.add_widget(name_input)
        box.add_widget(desc_input)
        box.add_widget(btn_row)
        pop = open_popup("Edit Checklist", box, size=(0.92, 0.54))

        def do_save(*_):
            if not name_input.text.strip():
                show_message("Missing Name", "Please enter a checklist name.")
                return
            checklist['name'] = name_input.text.strip()
            checklist['description'] = desc_input.text.strip()
            checklist['updated_at'] = now_str()
            project = self.get_project(project_id)
            if project:
                self.touch_project(project, 'Checklist updated')
            self.save_data()
            pop.dismiss()
            self.refresh_all()

        save_btn.bind(on_release=do_save)
        cancel_btn.bind(on_release=pop.dismiss)
        pop.open()

    def open_import_checklist_popup(self):
        if not self.current_project_id:
            return
        selected_path = {'value': ''}

        outer = BoxLayout(orientation='vertical', padding=dp(18), spacing=dp(14))
        apply_solid_bg(outer, AMOLED)

        intro_card = Card(auto_height=True, spacing=dp(8), padding=[dp(14), dp(14), dp(14), dp(14)])
        intro_card.add_widget(SectionTitle(text='Import Checklist Template'))
        intro_card.add_widget(SmallLabel(text='Import a checklist Python file or paste the Python code directly. Synapse supports CHECKLIST_TEMPLATE or get_checklist_template().', color=TEXT))
        outer.add_widget(intro_card)

        guide_card = Card(height=dp(220), spacing=dp(10), padding=[dp(14), dp(14), dp(14), dp(14)])
        guide_header = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(10))
        guide_header.add_widget(SectionTitle(text='Template Guide'))
        copy_btn = SecondaryButton(text='Copy Guide', size_hint_x=None, width=dp(126), height=dp(40))
        guide_header.add_widget(copy_btn)
        guide_card.add_widget(guide_header)
        guide_input = StyledMultiline(text=CHECKLIST_TEMPLATE_GUIDE, readonly=True, height=dp(150))
        guide_card.add_widget(guide_input)
        outer.add_widget(guide_card)

        chooser_card = Card(height=dp(270), padding=[dp(14), dp(14), dp(14), dp(14)], spacing=dp(10))
        chooser_card.add_widget(SectionTitle(text='Pick a checklist .py file'))
        chooser = FileChooserListView(path=get_file_picker_start_path(), filters=['*.py'], multiselect=False)
        chooser_card.add_widget(chooser)
        selected_label = SmallLabel(text='Selected file: None')
        chooser_card.add_widget(selected_label)
        outer.add_widget(chooser_card)

        paste_card = Card(auto_height=True, spacing=dp(10), padding=[dp(14), dp(14), dp(14), dp(14)])
        paste_header = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        paste_header.add_widget(SectionTitle(text='Or Paste Python Template'))
        paste_btn = SecondaryButton(text='Paste', size_hint_x=None, width=dp(108), height=dp(40))
        clear_btn = SecondaryButton(text='Clear', size_hint_x=None, width=dp(108), height=dp(40))
        paste_header.add_widget(paste_btn)
        paste_header.add_widget(clear_btn)
        paste_card.add_widget(paste_header)

        code_input = StyledMultiline(hint_text='Paste checklist template .py contents here', height=dp(220))
        paste_card.add_widget(code_input)
        outer.add_widget(paste_card)

        btns = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(10))
        import_btn = StyledButton(text='Import')
        cancel_btn = SecondaryButton(text='Cancel')
        btns.add_widget(import_btn)
        btns.add_widget(cancel_btn)
        outer.add_widget(btns)

        pop = open_popup('Import Checklist Template', outer, size=(0.96, 0.98))

        def update_selected(*_):
            selection = chooser.selection or []
            selected_path['value'] = selection[0] if selection else ''
            selected_label.text = f"Selected file: {selected_path['value'] or 'None'}"

        def do_copy(*_):
            self.copy_text(CHECKLIST_TEMPLATE_GUIDE, 'Template guide copied to clipboard.')

        def do_paste(*_):
            text = ''
            if Clipboard is not None:
                try:
                    text = Clipboard.paste() or ''
                except Exception:
                    text = ''
            if not text:
                show_message('Clipboard Empty', 'There was no text available to paste.')
                return
            code_input.text = text

        def do_clear(*_):
            code_input.text = ''

        def do_import(*_):
            try:
                if code_input.text.strip():
                    checklist = self.load_checklist_from_code(code_input.text)
                elif selected_path['value']:
                    checklist = self.load_checklist_from_py(selected_path['value'])
                else:
                    show_message('Nothing Selected', 'Pick a .py file or paste checklist code first.')
                    return
                project = self.get_project(self.current_project_id)
                if project is None:
                    raise ValueError('No project selected.')
                checklist['updated_at'] = now_str()
                project.setdefault('checklists', []).append(checklist)
                self.touch_project(project, 'Checklist imported')
                self.save_data()
                pop.dismiss()
                self.refresh_all()
                show_message('Imported', f"Checklist imported successfully:\n{checklist.get('name', 'Checklist')}")
            except Exception as e:
                show_message('Import Error', str(e))

        chooser.bind(selection=update_selected)
        copy_btn.bind(on_release=do_copy)
        paste_btn.bind(on_release=do_paste)
        clear_btn.bind(on_release=do_clear)
        import_btn.bind(on_release=do_import)
        cancel_btn.bind(on_release=pop.dismiss)
        pop.open()

    def load_checklist_from_py(self, path):
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found:\n{path}")
        if not path.lower().endswith(".py"):
            raise ValueError("Please choose a Python (.py) file.")
        code = read_text_file(path)
        return self.load_checklist_from_code(code)

    def load_checklist_from_code(self, code):
        namespace = {}
        exec(code, namespace)
        if "CHECKLIST_TEMPLATE" in namespace:
            payload = namespace["CHECKLIST_TEMPLATE"]
        elif callable(namespace.get("get_checklist_template")):
            payload = namespace["get_checklist_template"]()
        else:
            raise ValueError("No CHECKLIST_TEMPLATE or get_checklist_template() found in the Python content.")
        return self.normalize_checklist_payload(payload)

    def normalize_checklist_payload(self, payload):
        if not isinstance(payload, dict):
            raise ValueError("Checklist template must be a dictionary.")
        name = str(payload.get("name", "Imported Checklist")).strip() or "Imported Checklist"
        description = str(payload.get("description", "")).strip()
        raw_items = payload.get("items", [])
        if not isinstance(raw_items, list):
            raise ValueError("Checklist items must be a list.")
        items = []
        for item in raw_items:
            if isinstance(item, str):
                entry = item.strip()
                if entry:
                    items.append({"entry": entry, "done": False, "notes": ""})
            elif isinstance(item, dict):
                entry = str(item.get("entry", "")).strip()
                if entry:
                    items.append({
                        "entry": entry,
                        "done": bool(item.get("done", False)),
                        "notes": str(item.get("notes", "")).strip(),
                    })
        return {
            "id": str(uuid.uuid4()),
            "name": name,
            "description": description,
            "created_at": now_str(),
            "items": items,
        }

    # ---------- call ops ----------
    def open_new_call_popup(self, call_id=None):
        if not self.current_project_id:
            return
        project = self.get_project(self.current_project_id)
        if project is None:
            return
        existing = None
        if call_id:
            for item in project.get('calls', []):
                if item.get('id') == call_id:
                    existing = item
                    break
        now = datetime.now()
        month_values = month_name_options()
        day_values = [str(i) for i in range(1, 32)]
        year_values = [str(i) for i in range(2000, 2036)]
        minute_values = [str(i).zfill(2) for i in range(0, 60)]
        values_12h = [str(i).zfill(2) for i in range(1, 13)]
        values_24h = [str(i).zfill(2) for i in range(0, 24)]

        parsed_date = parse_datetime_maybe(existing.get('date')) if existing else None
        dt = parsed_date or now

        box = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12))
        title_input = StyledInput(text=existing.get('title', '') if existing else '', hint_text='Call title')
        duration_input = StyledInput(text=existing.get('duration', '') if existing else '', hint_text='Duration (e.g. 25 min)')
        about_input = StyledInput(text=existing.get('about', '') if existing else '', hint_text='What the call is about')
        next_action_input = StyledInput(text=existing.get('next_action', '') if existing else '', hint_text='Next action')
        followup_input = StyledInput(text=existing.get('followup_date', '') if existing else '', hint_text='Follow-up date (YYYY-MM-DD or full datetime)')
        outcome_input = StyledInput(text=existing.get('outcome', '') if existing else '', hint_text='Outcome')
        stage_spin = StyledSpinner(text=existing.get('lead_stage', 'Lead') if existing else 'Lead', values=lead_stage_options())
        notes_input = StyledMultiline(text=existing.get('notes', '') if existing else '', hint_text='Notes / key details', height=dp(120))

        date_card = Card(height=dp(196), spacing=dp(10), padding=dp(12))
        date_card.add_widget(SmallLabel(text='Date & time', color=TEXT))

        row1 = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        month_spin = StyledSpinner(text=month_values[dt.month - 1], values=month_values)
        day_spin = StyledSpinner(text=str(dt.day), values=day_values)
        year_spin = StyledSpinner(text=str(dt.year), values=year_values)
        row1.add_widget(month_spin)
        row1.add_widget(day_spin)
        row1.add_widget(year_spin)
        date_card.add_widget(row1)

        row2 = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        mode_spin = StyledSpinner(text='24h', values=['12h', '24h'])
        hour_spin = StyledSpinner(text=str(dt.hour).zfill(2), values=values_24h)
        minute_spin = StyledSpinner(text=str(dt.minute).zfill(2), values=minute_values)
        am_pm_default = 'AM' if dt.hour < 12 else 'PM'
        hour12 = dt.hour % 12
        hour12 = 12 if hour12 == 0 else hour12
        am_pm_spin = StyledSpinner(text=am_pm_default, values=['AM', 'PM'])
        row2.add_widget(mode_spin)
        row2.add_widget(hour_spin)
        row2.add_widget(minute_spin)
        row2.add_widget(am_pm_spin)
        date_card.add_widget(row2)

        def on_mode_change(_spinner, text):
            if text == '12h':
                hour_spin.values = values_12h
                try:
                    value = int(hour_spin.text.strip() or str(dt.hour).zfill(2))
                    value = value % 12
                    value = 12 if value == 0 else value
                    hour_spin.text = str(value).zfill(2)
                except Exception:
                    hour_spin.text = str(hour12).zfill(2)
                am_pm_spin.disabled = False
                am_pm_spin.opacity = 1
            else:
                hour_spin.values = values_24h
                try:
                    value = int(hour_spin.text.strip() or str(hour12).zfill(2))
                    if am_pm_spin.text == 'PM' and value < 12:
                        value += 12
                    if am_pm_spin.text == 'AM' and value == 12:
                        value = 0
                    hour_spin.text = str(value).zfill(2)
                except Exception:
                    hour_spin.text = str(dt.hour).zfill(2)
                am_pm_spin.disabled = True
                am_pm_spin.opacity = 0.55

        mode_spin.bind(text=on_mode_change)
        on_mode_change(mode_spin, mode_spin.text)

        for widget in (title_input, date_card, duration_input, about_input):
            box.add_widget(widget)
        for lbl, widget in [('Next Action', next_action_input), ('Follow-up Date', followup_input), ('Outcome', outcome_input), ('Lead Stage', stage_spin)]:
            box.add_widget(SmallLabel(text=lbl, color=TEXT))
            box.add_widget(widget)
        box.add_widget(notes_input)

        btn_row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(10))
        save_btn = StyledButton(text='Save Call')
        cancel_btn = SecondaryButton(text='Cancel')
        btn_row.add_widget(save_btn)
        btn_row.add_widget(cancel_btn)
        box.add_widget(btn_row)

        pop = open_popup('Edit Call' if existing else 'Add New Call', box, size=(0.96, 0.98))

        def do_save(*_):
            title = title_input.text.strip() or 'Call'
            date_text = build_call_date_string(year_spin.text, month_spin.text, day_spin.text, mode_spin.text, hour_spin.text, minute_spin.text, am_pm_spin.text)
            stamp = now_str()
            payload = {
                'title': title,
                'date': date_text,
                'duration': duration_input.text.strip(),
                'about': about_input.text.strip(),
                'notes': notes_input.text.strip(),
                'next_action': next_action_input.text.strip(),
                'followup_date': followup_input.text.strip(),
                'outcome': outcome_input.text.strip(),
                'lead_stage': stage_spin.text.strip() or 'Lead',
                'updated_at': stamp,
            }
            if existing:
                existing.update(payload)
            else:
                payload.update({'id': str(uuid.uuid4()), 'created_at': stamp})
                project.setdefault('calls', []).append(payload)
            project['pipeline_stage'] = stage_spin.text.strip() or project.get('pipeline_stage', 'Lead')
            self.touch_project(project, 'Call updated' if existing else 'Call added')
            self.save_data()
            pop.dismiss()
            self.sm.get_screen('calls').refresh()
            self.refresh_all()

        save_btn.bind(on_release=do_save)
        cancel_btn.bind(on_release=pop.dismiss)
        pop.open()

    def delete_call(self, project_id, call_id):
        project = self.get_project(project_id)
        if not project:
            return
        project['calls'] = [call for call in project.get('calls', []) if call.get('id') != call_id]
        self.touch_project(project, 'Call deleted')
        self.save_data()
        self.sm.get_screen('calls').refresh()
        self.refresh_all()

    def open_future_development_popup(self, item_id=None):
        if not self.current_project_id:
            return
        project = self.get_project(self.current_project_id)
        if not project:
            return
        existing = self.get_future_development(self.current_project_id, item_id) if item_id else None

        box = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12))
        title_input = StyledInput(text=existing.get('title', '') if existing else '', hint_text='Idea / feature title')
        status_spinner = StyledSpinner(text=(existing.get('status') if existing else 'In Process'), values=future_status_options())
        notes_input = StyledMultiline(text=existing.get('notes', '') if existing else '', hint_text='Why this matters / next steps / blockers', height=dp(140))
        urgent_box = CheckBox(active=bool(existing.get('urgent', False)) if existing else False, size_hint=(None, None), size=(dp(30), dp(30)))
        pinned_box = CheckBox(active=bool(existing.get('pinned', False)) if existing else False, size_hint=(None, None), size=(dp(30), dp(30)))

        box.add_widget(title_input)
        box.add_widget(SmallLabel(text='Status', color=TEXT))
        box.add_widget(status_spinner)
        box.add_widget(notes_input)
        urgent_row = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(8))
        urgent_row.add_widget(SmallLabel(text='Mark as urgent', color=TEXT))
        urgent_row.add_widget(urgent_box)
        pinned_row = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(8))
        pinned_row.add_widget(SmallLabel(text='Pin this item', color=TEXT))
        pinned_row.add_widget(pinned_box)
        box.add_widget(urgent_row)
        box.add_widget(pinned_row)

        btn_row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(10))
        save_btn = StyledButton(text='Save')
        cancel_btn = SecondaryButton(text='Cancel')
        btn_row.add_widget(save_btn)
        btn_row.add_widget(cancel_btn)
        box.add_widget(btn_row)

        pop = open_popup('Future Development', box, size=(0.92, 0.84))

        def do_save(*_):
            title = title_input.text.strip()
            if not title:
                show_message('Missing Title', 'Please add a feature or idea title.')
                return
            stamp = now_str()
            if existing:
                existing['title'] = title
                existing['status'] = status_spinner.text.strip() or 'In Process'
                existing['notes'] = notes_input.text.strip()
                existing['urgent'] = bool(urgent_box.active)
                existing['pinned'] = bool(pinned_box.active)
                existing['updated_at'] = stamp
            else:
                project.setdefault('future_developments', []).append({
                    'id': str(uuid.uuid4()),
                    'title': title,
                    'status': status_spinner.text.strip() or 'In Process',
                    'notes': notes_input.text.strip(),
                    'urgent': bool(urgent_box.active),
                    'pinned': bool(pinned_box.active),
                    'created_at': stamp,
                    'updated_at': stamp,
                })
            self.touch_project(project, 'Future development updated' if existing else 'Future development added')
            self.save_data()
            pop.dismiss()
            self.refresh_all()

        save_btn.bind(on_release=do_save)
        cancel_btn.bind(on_release=pop.dismiss)
        pop.open()

    def delete_future_development(self, project_id, item_id):
        project = self.get_project(project_id)
        if not project:
            return
        project['future_developments'] = [item for item in project.get('future_developments', []) if item.get('id') != item_id]
        self.touch_project(project, 'Future development deleted')
        self.save_data()
        self.refresh_all()

    def open_sales_note_popup(self, note_id=None):
        if not self.current_project_id:
            return
        project = self.get_project(self.current_project_id)
        if not project:
            return
        existing = self.get_sales_note(self.current_project_id, note_id) if note_id else None

        box = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12))
        heading_input = StyledInput(text=existing.get('heading', '') if existing else '', hint_text='Note heading')
        body_input = StyledMultiline(text=existing.get('body', '') if existing else '', hint_text='Write the note body here', height=dp(200))
        pinned_box = CheckBox(active=bool(existing.get('pinned', False)) if existing else False, size_hint=(None, None), size=(dp(30), dp(30)))
        pin_row = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(8))
        pin_row.add_widget(SmallLabel(text='Mark as high-value / pinned', color=TEXT))
        pin_row.add_widget(pinned_box)
        box.add_widget(heading_input)
        box.add_widget(body_input)
        box.add_widget(pin_row)

        btn_row = GridLayout(cols=3, size_hint_y=None, height=dp(52), spacing=dp(10))
        save_btn = StyledButton(text='Save', height=dp(50))
        copy_btn = SecondaryButton(text='Copy Body', height=dp(50))
        cancel_btn = SecondaryButton(text='Cancel', height=dp(50))
        btn_row.add_widget(save_btn)
        btn_row.add_widget(copy_btn)
        btn_row.add_widget(cancel_btn)
        box.add_widget(btn_row)

        pop = open_popup('Sales Note', box, size=(0.94, 0.82))

        def do_save(*_):
            heading = heading_input.text.strip()
            if not heading:
                show_message('Missing Heading', 'Please enter a note heading.')
                return
            stamp = now_str()
            if existing:
                existing['heading'] = heading
                existing['body'] = body_input.text.strip()
                existing['pinned'] = bool(pinned_box.active)
                existing['updated_at'] = stamp
            else:
                project.setdefault('sales_notes', []).append({
                    'id': str(uuid.uuid4()),
                    'heading': heading,
                    'body': body_input.text.strip(),
                    'pinned': bool(pinned_box.active),
                    'created_at': stamp,
                    'updated_at': stamp,
                })
            self.touch_project(project, 'Sales note updated' if existing else 'Sales note added')
            self.save_data()
            pop.dismiss()
            self.refresh_all()

        save_btn.bind(on_release=do_save)
        copy_btn.bind(on_release=lambda *_: self.copy_text(body_input.text.strip(), 'Sales note body copied.'))
        cancel_btn.bind(on_release=pop.dismiss)
        pop.open()

    def delete_sales_note(self, project_id, note_id):
        project = self.get_project(project_id)
        if not project:
            return
        project['sales_notes'] = [note for note in project.get('sales_notes', []) if note.get('id') != note_id]
        self.touch_project(project, 'Sales note deleted')
        self.save_data()
        self.refresh_all()

    # ---------- settings ----------
    def open_change_password_popup(self):
        current_pw = self.get_master_password()
        box = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
        old_input = StyledInput(hint_text="Current password", password=True)
        new_input = StyledInput(hint_text="New password", password=True)
        confirm_input = StyledInput(hint_text="Confirm new password", password=True)
        box.add_widget(old_input)
        box.add_widget(new_input)
        box.add_widget(confirm_input)
        btn_row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(10))
        save_btn = StyledButton(text="Save")
        cancel_btn = SecondaryButton(text="Cancel")
        btn_row.add_widget(save_btn)
        btn_row.add_widget(cancel_btn)
        box.add_widget(btn_row)
        pop = open_popup("Change Master Password", box, size=(0.92, 0.50))

        def do_save(*_):
            if old_input.text.strip() != str(current_pw):
                show_message("Wrong Password", "Current master password is incorrect.")
                return
            if not new_input.text.strip():
                show_message("Invalid Password", "New password cannot be empty.")
                return
            if new_input.text != confirm_input.text:
                show_message("Mismatch", "The new passwords do not match.")
                return
            self.data_store.setdefault("settings", {})["master_password"] = new_input.text.strip()
            self.save_data()
            pop.dismiss()
            show_message("Saved", "Master password updated.")

        save_btn.bind(on_release=do_save)
        cancel_btn.bind(on_release=pop.dismiss)
        pop.open()

    # ---------- file generator ----------
    def populate_fg_fields(self):
        fg = self.get_fg_settings()
        try:
            b_screen = self.sm.get_screen("fg_buildozer")
            b_screen.bd_title_input.text = fg.get("bd_title", "")
            b_screen.bd_package_input.text = fg.get("bd_package", "")
            b_screen.bd_domain_input.text = fg.get("bd_domain", "")
            b_screen.bd_version_input.text = fg.get("bd_version", "")
            b_screen.bd_requirements_input.text = fg.get("bd_requirements", "")
            b_screen.bd_permissions_input.text = fg.get("bd_permissions", "")
            b_screen.bd_permissions_spinner.text = fg.get("bd_permissions_spinner", "INTERNET")
            b_screen.bd_orientation_input.text = fg.get("bd_orientation", "")
            b_screen.bd_orientation_spinner.text = fg.get("bd_orientation_spinner", "portrait")
            b_screen.bd_api_input.text = fg.get("bd_api", "")
            b_screen.bd_api_spinner.text = fg.get("bd_api_spinner", "33")
            b_screen.bd_min_input.text = fg.get("bd_min", "")
            b_screen.bd_min_spinner.text = fg.get("bd_min_spinner", "21")
            b_screen.bd_ndk_input.text = fg.get("bd_ndk", "")
            b_screen.bd_ndk_spinner.text = fg.get("bd_ndk_spinner", "21")
            b_screen.bd_arch_input.text = fg.get("bd_arch", "")
            b_screen.bd_arch_spinner.text = fg.get("bd_arch_spinner", "arm64-v8a, armeabi-v7a")
        except Exception:
            pass

        try:
            w_screen = self.sm.get_screen("fg_workflow")
            w_screen.wf_name_input.text = fg.get("wf_name", "")
            w_screen.wf_branch_input.text = fg.get("wf_branch", "")
            w_screen.wf_python_input.text = fg.get("wf_python", "")
            w_screen.wf_ubuntu_input.text = fg.get("wf_ubuntu", "")
            w_screen.wf_ubuntu_spinner.text = fg.get("wf_ubuntu_spinner", "ubuntu-22.04")
            w_screen.wf_java_input.text = fg.get("wf_java", "")
            w_screen.wf_java_spinner.text = fg.get("wf_java_spinner", "17")
            w_screen.wf_cmd_input.text = fg.get("wf_cmd", "")
        except Exception:
            pass

    def save_fg_buildozer(self):
        try:
            screen = self.sm.get_screen("fg_buildozer")
            title = screen.bd_title_input.text.strip() or "My Kivy App"
            package_name = screen.bd_package_input.text.strip().lower() or "myapp"
            package_domain = screen.bd_domain_input.text.strip() or "org.test"
            version = screen.bd_version_input.text.strip() or "0.1"
            requirements = screen.bd_requirements_input.text.strip() or "python3,kivy"
            permissions = screen.bd_permissions_input.text.strip() or screen.bd_permissions_spinner.text.strip()
            orientation = screen.bd_orientation_input.text.strip() or screen.bd_orientation_spinner.text.strip()
            android_api = screen.bd_api_input.text.strip() or screen.bd_api_spinner.text.strip()
            min_api = screen.bd_min_input.text.strip() or screen.bd_min_spinner.text.strip()
            ndk_api = screen.bd_ndk_input.text.strip() or screen.bd_ndk_spinner.text.strip()
            archs = screen.bd_arch_input.text.strip() or screen.bd_arch_spinner.text.strip()

            fg = self.get_fg_settings()
            fg.update({
                "bd_title": title,
                "bd_package": package_name,
                "bd_domain": package_domain,
                "bd_version": version,
                "bd_requirements": requirements,
                "bd_permissions": screen.bd_permissions_input.text.strip(),
                "bd_permissions_spinner": screen.bd_permissions_spinner.text.strip(),
                "bd_orientation": screen.bd_orientation_input.text.strip(),
                "bd_orientation_spinner": screen.bd_orientation_spinner.text.strip(),
                "bd_api": screen.bd_api_input.text.strip(),
                "bd_api_spinner": screen.bd_api_spinner.text.strip(),
                "bd_min": screen.bd_min_input.text.strip(),
                "bd_min_spinner": screen.bd_min_spinner.text.strip(),
                "bd_ndk": screen.bd_ndk_input.text.strip(),
                "bd_ndk_spinner": screen.bd_ndk_spinner.text.strip(),
                "bd_arch": screen.bd_arch_input.text.strip(),
                "bd_arch_spinner": screen.bd_arch_spinner.text.strip(),
            })
            self.save_data()

            content = build_buildozer_content(
                title, package_name, package_domain, version,
                requirements, permissions, orientation,
                android_api, min_api, ndk_api, archs
            )
            output_dir = os.path.join(get_github_apk_root_dir(), "buildozer_specs")
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = make_unique_path(output_dir, f"buildozer_{stamp}.spec")
            write_text_file(file_path, content)
            add_fg_history(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Generated buildozer.spec -> {file_path}")
            show_message("Saved", f"buildozer.spec created successfully:\n{file_path}")
        except Exception as e:
            show_message("Error", str(e))

    def save_fg_workflow(self):
        try:
            screen = self.sm.get_screen("fg_workflow")
            workflow_name = screen.wf_name_input.text.strip() or "Build APK"
            branch = screen.wf_branch_input.text.strip() or "main"
            python_version = screen.wf_python_input.text.strip() or "3.11"
            ubuntu_version = screen.wf_ubuntu_input.text.strip() or screen.wf_ubuntu_spinner.text.strip()
            java_version = screen.wf_java_input.text.strip() or screen.wf_java_spinner.text.strip()
            build_cmd = screen.wf_cmd_input.text.strip() or "buildozer android debug"

            fg = self.get_fg_settings()
            fg.update({
                "wf_name": workflow_name,
                "wf_branch": branch,
                "wf_python": python_version,
                "wf_ubuntu": screen.wf_ubuntu_input.text.strip(),
                "wf_ubuntu_spinner": screen.wf_ubuntu_spinner.text.strip(),
                "wf_java": screen.wf_java_input.text.strip(),
                "wf_java_spinner": screen.wf_java_spinner.text.strip(),
                "wf_cmd": build_cmd,
            })
            self.save_data()

            content = build_workflow_content(
                workflow_name, branch, python_version,
                ubuntu_version, java_version, build_cmd
            )
            output_dir = os.path.join(get_github_apk_root_dir(), "github_workflows")
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = make_unique_path(output_dir, f"build_{stamp}.yml")
            write_text_file(file_path, content)
            add_fg_history(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Generated build.yml -> {file_path}")
            show_message("Saved", f"build.yml created successfully:\n{file_path}")
        except Exception as e:
            show_message("Error", str(e))

    def clear_fg_history_and_refresh(self):
        clear_fg_history()
        try:
            self.sm.get_screen("fg_history").refresh()
        except Exception:
            pass
        show_message("History", "File generator history cleared.")

    def copy_fg_guide(self):
        if Clipboard is None:
            show_message("Clipboard Unavailable", "Clipboard is not available on this device right now.")
            return
        try:
            Clipboard.copy(GITHUB_APK_BUILD_GUIDE)
            show_message("Copied", "GitHub build guide copied to clipboard.")
        except Exception as e:
            show_message("Copy Failed", str(e))

    def on_start(self):
        self.populate_fg_fields()
        if self.data_store.get('settings', {}).get('backup_on_start'):
            try:
                self.create_backup_file('startup')
            except Exception:
                pass
        self.refresh_all()

    # ---------- refresh ----------
    def refresh_all(self):
        for name in ("main", "projects", "settings", "file_generator_hub", "github_apk_menu", "fg_history", "fg_guide", "fg_buildozer", "fg_workflow", "future_dev", "sales_notes"):
            try:
                self.sm.get_screen(name).refresh()
            except Exception:
                pass
        if self.current_project_id:
            for name in ("project", "checklists", "calls", "checklist_detail", "future_dev", "sales_notes"):
                try:
                    self.sm.get_screen(name).refresh()
                except Exception:
                    pass


if __name__ == "__main__":
    SynapseApp().run()
