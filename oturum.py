#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
import json
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QGridLayout,
    QGraphicsDropShadowEffect, QDialog, QHBoxLayout, QSpinBox, QFileDialog, QFrame, QComboBox
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QSize, QTimer, QPropertyAnimation, QEasingCurve

CONFIG_PATH = os.path.expanduser("~/.config/power-menu.conf")
CUSTOM_ICON_PATH = os.path.expanduser("~/.config/power-menu-icons.json")

DEFAULT_TIMER_COLOR = "#FF00FF"
DEFAULT_ANIM_TYPE = "Glow"
TIMER_COLOR_KEY = "timer_color"
TIMER_ANIM_KEY = "timer_anim"

# Masaüstü ortamını algıla
DESKTOP_ENV = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
IS_WAYLAND = "WAYLAND_DISPLAY" in os.environ  # Wayland oturumu mu?

# Aktif display manager'ı algıla (gdm3 veya sddm)
def get_display_manager():
    try:
        result = subprocess.check_output(["systemctl", "is-active", "gdm3"], stderr=subprocess.DEVNULL).decode().strip()
        if result == "active":
            return "gdm3"
    except:
        pass
    try:
        result = subprocess.check_output(["systemctl", "is-active", "sddm"], stderr=subprocess.DEVNULL).decode().strip()
        if result == "active":
            return "sddm"
    except:
        pass
    return "unknown"

DISPLAY_MANAGER = get_display_manager()

# Komutları belirle – En iyi çalışan kombinasyon
if "gnome" in DESKTOP_ENV:
    if DISPLAY_MANAGER == "gdm3":
        # GDM3 + GNOME → En güzel kilitleme ve hızlı kapatma
        BUTTONS = {
            "Kapat": ("system-shutdown-symbolic", "systemctl poweroff"),
            "Yeniden Başlat": ("system-reboot-symbolic", "systemctl reboot"),
            "Oturumu Kilitle": ("system-lock-screen-symbolic", "dbus-send --session --dest=org.gnome.ScreenSaver --type=method_call /org/gnome/ScreenSaver org.gnome.ScreenSaver.Lock"),
            "Oturumu Kapat": ("system-log-out-symbolic", "gnome-session-quit --logout --no-prompt --force")
        }
    else:
        # SDDM + GNOME → dbus çalışmaz, loginctl ile güvenilir yöntem
        BUTTONS = {
            "Kapat": ("system-shutdown-symbolic", "systemctl poweroff"),
            "Yeniden Başlat": ("system-reboot-symbolic", "systemctl reboot"),
            "Oturumu Kilitle": ("system-lock-screen-symbolic", "systemctl suspend"),
            "Oturumu Kapat": ("system-log-out-symbolic", "gnome-session-quit --logout --no-prompt")
        }
elif "kde" in DESKTOP_ENV or "plasma" in DESKTOP_ENV:
    # KDE → SDDM varsayılır, en iyi komutlar
    BUTTONS = {
        "Kapat": ("system-shutdown-symbolic", "systemctl poweroff"),
        "Yeniden Başlat": ("system-reboot-symbolic", "systemctl reboot"),
        "Oturumu Kilitle": ("system-lock-screen-symbolic", "loginctl lock-session"),
        "Oturumu Kapat": ("system-log-out-symbolic", "qdbus6 org.kde.Shutdown /Shutdown org.kde.Shutdown.logout")
    }
elif "cinnamon" in DESKTOP_ENV:
    if IS_WAYLAND:
        # Cinnamon + Wayland → cinnamon-screensaver-command çalışmaz
        BUTTONS = {
            "Kapat": ("system-shutdown-symbolic", "systemctl poweroff"),
            "Yeniden Başlat": ("system-reboot-symbolic", "systemctl reboot"),
            "Oturumu Kilitle": ("system-lock-screen-symbolic", "systemctl suspend"),
            "Oturumu Kapat": ("system-log-out-symbolic", "cinnamon-session-quit --logout --no-prompt")
        }
    else:
        # Cinnamon + X11 → klasik komut çalışır
        BUTTONS = {
            "Kapat": ("system-shutdown-symbolic", "systemctl poweroff"),
            "Yeniden Başlat": ("system-reboot-symbolic", "systemctl reboot"),
            "Oturumu Kilitle": ("system-lock-screen-symbolic", "cinnamon-screensaver-command -l"),
            "Oturumu Kapat": ("system-log-out-symbolic", "cinnamon-session-quit --logout --no-prompt")
        }
else:
    # Bilinmeyen ortamda güvenli fallback
    BUTTONS = {
        "Kapat": ("system-shutdown-symbolic", "systemctl poweroff"),
        "Yeniden Başlat": ("system-reboot-symbolic", "systemctl reboot"),
        "Oturumu Kilitle": ("system-lock-screen-symbolic", "loginctl lock-session"),
        "Oturumu Kapat": ("system-log-out-symbolic", "loginctl terminate-session $XDG_SESSION_ID")
    }

# ------------------- AYARLAR -------------------
def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {"timer_value": 7, TIMER_COLOR_KEY: DEFAULT_TIMER_COLOR, TIMER_ANIM_KEY: DEFAULT_ANIM_TYPE}
    try:
        with open(CONFIG_PATH, "r") as f:
            data = json.load(f)
            data.setdefault("timer_value", 7)
            data.setdefault(TIMER_COLOR_KEY, DEFAULT_TIMER_COLOR)
            data.setdefault(TIMER_ANIM_KEY, DEFAULT_ANIM_TYPE)
            return data
    except:
        return {"timer_value": 7, TIMER_COLOR_KEY: DEFAULT_TIMER_COLOR, TIMER_ANIM_KEY: DEFAULT_ANIM_TYPE}

def save_config(data):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f)

def load_timer_value(): return load_config()["timer_value"]
def save_timer_value(val): cfg = load_config(); cfg["timer_value"] = val; save_config(cfg)
def load_timer_color(): return load_config()[TIMER_COLOR_KEY]
def save_timer_color(color): cfg = load_config(); cfg[TIMER_COLOR_KEY] = color; save_config(cfg)
def load_timer_anim(): return load_config()[TIMER_ANIM_KEY]
def save_timer_anim(anim_type): cfg = load_config(); cfg[TIMER_ANIM_KEY] = anim_type; save_config(cfg)

# ------------------- ÖZEL İKON -------------------
def save_custom_icon(path, action_name):
    data = {}
    if os.path.exists(CUSTOM_ICON_PATH):
        try:
            with open(CUSTOM_ICON_PATH, "r") as f:
                data = json.load(f)
        except:
            data = {}
    data[action_name] = path
    os.makedirs(os.path.dirname(CUSTOM_ICON_PATH), exist_ok=True)
    with open(CUSTOM_ICON_PATH, "w") as f:
        json.dump(data, f)

def load_custom_icons():
    if not os.path.exists(CUSTOM_ICON_PATH):
        return {}
    try:
        with open(CUSTOM_ICON_PATH, "r") as f:
            return json.load(f)
    except:
        return {}

def remove_custom_icon(action_name):
    if os.path.exists(CUSTOM_ICON_PATH):
        with open(CUSTOM_ICON_PATH, "r") as f:
            try:
                data = json.load(f)
            except:
                data = {}
        if action_name in data:
            del data[action_name]
            with open(CUSTOM_ICON_PATH, "w") as f:
                json.dump(data, f)

# ------------------- AYARLAR PENCERESİ -------------------
class AyarPencere(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ayarlar")
        self.setFixedSize(360, 500)
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        self.setWindowModality(Qt.ApplicationModal)
        self.setStyleSheet("""
            QDialog { background-color: #1e1e2f; border-radius: 15px; }
            QLabel { color: #ffffff; font-size: 14px; }
            QPushButton { background-color: #3b3b5c; color: #ffffff; border-radius: 8px; padding: 6px 12px; font-weight: bold; }
            QPushButton:hover { background-color: #5a5a80; }
            QSpinBox, QComboBox {
                background-color: #2e2e44;
                color: #ffffff;
                border-radius: 6px;
                padding: 2px 6px;
            }
            QComboBox QAbstractItemView {
                background-color: #2e2e44;
                color: #ffffff;
                selection-background-color: #444466;
            }
        """)
        layout = QVBoxLayout()
        layout.setContentsMargins(20,20,20,20)
        layout.setSpacing(15)

        lbl = QLabel("Geri Sayım Süresi (1–15 saniye):")
        layout.addWidget(lbl)

        h = QHBoxLayout()
        self.spin = QSpinBox()
        self.spin.setRange(1,15)
        self.spin.setValue(load_timer_value())
        self.spin.setFixedWidth(80)
        h.addWidget(self.spin)
        h.addStretch()
        layout.addLayout(h)

        lbl_color = QLabel("Geri Sayım Sayacı Rengi:")
        layout.addWidget(lbl_color)
        self.color_combo = QComboBox()
        self.color_combo.addItem("Neon Mor", "#FF00FF")
        self.color_combo.addItem("Neon Mavi", "#00FFFF")
        self.color_combo.addItem("Neon Yeşil", "#00FF00")
        self.color_combo.addItem("Neon Kırmızı", "#FF0000")
        color_val = load_timer_color()
        index = self.color_combo.findData(color_val)
        if index >= 0:
            self.color_combo.setCurrentIndex(index)
        layout.addWidget(self.color_combo)

        lbl_anim = QLabel("Geri Sayım Animasyonu:")
        layout.addWidget(lbl_anim)
        self.anim_combo = QComboBox()
        anim_types = ["Glow", "Pulse", "Zoom", "ColorShift"]
        for a in anim_types:
            self.anim_combo.addItem(a)
        anim_val = load_timer_anim()
        index_anim = self.anim_combo.findText(anim_val)
        if index_anim >= 0:
            self.anim_combo.setCurrentIndex(index_anim)
        layout.addWidget(self.anim_combo)

        btn_save = QPushButton("Kaydet")
        btn_save.clicked.connect(self.kaydet)
        layout.addWidget(btn_save)

        self.icon_buttons = {}
        for action_name in BUTTONS.keys():
            card = QFrame()
            card.setStyleSheet("background-color: #2a2a44; border-radius: 10px;")
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(10,8,10,8)

            lbl_action = QLabel(action_name)
            lbl_action.setFixedWidth(120)
            card_layout.addWidget(lbl_action)

            select_btn = QPushButton("İkon Seç")
            select_btn.clicked.connect(lambda _, a=action_name: self.sec_ikon(a))
            card_layout.addWidget(select_btn)

            reset_btn = QPushButton("Varsayılan")
            reset_btn.clicked.connect(lambda _, a=action_name: self.varsayilan(a))
            card_layout.addWidget(reset_btn)

            layout.addWidget(card)
            self.icon_buttons[action_name] = (select_btn, reset_btn)

        self.setLayout(layout)

    def kaydet(self):
        save_timer_value(self.spin.value())
        save_timer_color(self.color_combo.currentData())
        save_timer_anim(self.anim_combo.currentText())
        self.close()
        if self.parent():
            self.parent().refresh_icons()

    def sec_ikon(self, action_name):
        dosya, _ = QFileDialog.getOpenFileName(self, f"{action_name} için ikon seç", "", "Images (*.png *.svg *.ico)")
        if dosya:
            save_custom_icon(dosya, action_name)
            if self.parent():
                self.parent().refresh_icons()

    def varsayilan(self, action_name):
        remove_custom_icon(action_name)
        if self.parent():
            self.parent().refresh_icons()

# ------------------- ONAY PENCERESİ -------------------
class OnayPencere(QWidget):
    def __init__(self, parent=None, komut=""):
        super().__init__(parent)
        self.setWindowModality(Qt.ApplicationModal)
        self.parent_widget = parent
        self.komut = komut
        self.onaylandi = False
        self.saniye = load_timer_value()
        self.timer_color = load_timer_color()
        self.anim_type = load_timer_anim()

        self.setFixedSize(300,300)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        panel = QWidget(self)
        panel.setGeometry(0,0,300,300)
        panel.setStyleSheet("background: rgba(0,0,0,0); border-radius:25px;")

        main_layout = QVBoxLayout(panel)
        main_layout.setContentsMargins(25,30,25,30)
        main_layout.setSpacing(25)

        self.sayaç_kutu = QWidget()
        self.sayaç_kutu.setFixedHeight(80)
        self.sayaç_kutu.setStyleSheet(f"""
            background: rgba(0,0,0,0.15);
            border: 3px solid {self.timer_color};
            border-radius: 20px;
        """)
        main_layout.addWidget(self.sayaç_kutu)

        sayaç_layout = QVBoxLayout(self.sayaç_kutu)
        self.lbl_timer = QLabel(f"00:{self.saniye:02d}")
        self.lbl_timer.setAlignment(Qt.AlignCenter)
        self.lbl_timer.setStyleSheet(f"color: {self.timer_color}; font-size: 54px; font-weight: bold;")
        sayaç_layout.addWidget(self.lbl_timer)

        self.btn_iptal = QPushButton("İptal Et")
        self.btn_iptal.setFixedHeight(55)
        self.btn_iptal.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255,255,255,0.35);
                color: {self.timer_color};
                border-radius: 15px;
                border: 2px solid {self.timer_color};
                font-size: 18px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: rgba(255,255,255,0.55);
            }}
        """)
        self.btn_iptal.clicked.connect(self.iptal_et)
        main_layout.addWidget(self.btn_iptal)

        self.kalan = self.saniye
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.guncelle)
        self.timer.start(1000)

        self.anim_value = 20
        self.anim_growing = True
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.animasyon)
        self.anim_timer.start(100)

        if parent:
            g = parent.geometry()
            self.move(g.center().x() - self.width()//2,
                      g.center().y() - self.height()//2 - 20)

        self.show()
        self.raise_()

    def animasyon(self):
        if self.anim_type in ["Glow","Pulse"]:
            if self.anim_growing:
                self.anim_value += 2
                if self.anim_value >= 35: self.anim_growing = False
            else:
                self.anim_value -= 2
                if self.anim_value <= 15: self.anim_growing = True

            if self.anim_type == "Pulse":
                self.lbl_timer.setStyleSheet(f"color:{self.timer_color}; font-size:{54 + self.anim_value//2}px; font-weight:bold;")
        elif self.anim_type == "Zoom":
            if self.anim_growing:
                self.anim_value += 2
                if self.anim_value >= 40: self.anim_growing = False
            else:
                self.anim_value -= 2
                if self.anim_value <= 10: self.anim_growing = True
            self.lbl_timer.setStyleSheet(f"color:{self.timer_color}; font-size:{48 + self.anim_value}px; font-weight:bold;")
        elif self.anim_type == "ColorShift":
            r = (self.anim_value*5) % 256
            g = (255 - self.anim_value*3) % 256
            b = (self.anim_value*2) % 256
            self.anim_value = (self.anim_value + 1) % 50
            self.lbl_timer.setStyleSheet(f"color: rgb({r},{g},{b}); font-size:54px; font-weight:bold;")

    def guncelle(self):
        self.kalan -= 1
        if self.kalan >= 0:
            self.lbl_timer.setText(f"00:{self.kalan:02d}")
        else:
            self.timer.stop()
            self.anim_timer.stop()
            self.onaylandi = True
            self.close()

    def iptal_et(self):
        self.onaylandi = False
        self.timer.stop()
        self.anim_timer.stop()
        self.close()

    def closeEvent(self, event):
        if self.parent_widget:
            self.parent_widget.onay_sonuc_geldi(self.onaylandi, self.komut)
        event.accept()

# ------------------- ICON BUTTON -------------------
class IconButton(QPushButton):
    def __init__(self, text, icon_path):
        super().__init__()
        self.text_name = text
        self.setFixedSize(120, 120)
        self.setCursor(Qt.PointingHandCursor)

        if os.path.exists(icon_path):
            self.setIcon(QIcon(icon_path))
        else:
            self.setIcon(QIcon.fromTheme(icon_path))

        self.setIconSize(QSize(78, 78))
        self.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #667eea, stop:1 #764ba2);
                border-radius: 25px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #7b8aff, stop:1 #9b59b6);
            }
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setOffset(0, 0)
        shadow.setColor(Qt.black)
        self.setGraphicsEffect(shadow)

        self.anim = QPropertyAnimation(self, b"iconSize", self)
        self.anim.setDuration(200)
        self.anim.setEasingCurve(QEasingCurve.OutQuart)

    def enterEvent(self, event):
        self.anim.setStartValue(QSize(78, 78))
        self.anim.setEndValue(QSize(100, 100))
        self.anim.start()
        if hasattr(self.parent(), 'show_label'):
            if self.text_name in ["Oturumu Kilitle", "Oturumu Kapat"]:
                y_offset = self.parent().hover_offset_lower
            else:
                y_offset = self.parent().hover_offset_upper
            self.parent().show_label(self.text_name, self.mapToParent(self.rect().center()), y_offset)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.anim.setStartValue(self.iconSize())
        self.anim.setEndValue(QSize(78, 78))
        self.anim.start()
        if hasattr(self.parent(), 'hover_label'):
            self.parent().hover_label.hide()
        super().leaveEvent(event)

# ------------------- POWER MENU -------------------
class PowerMenu(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Güç Menüsü")
        self.setFixedSize(420, 580)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowIcon(QIcon("/usr/share/pixmaps/oturum.png"))

        self.hover_offset_upper = -90
        self.hover_offset_lower = 50

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(50, 40, 50, 30)
        main_layout.setSpacing(30)

        # Ayarlar butonu
        ICON_PATH = "/usr/share/pixmaps/ayar1.png"
        ayar_btn = QPushButton()
        ayar_btn.setIcon(QIcon(ICON_PATH))
        ayar_btn.setIconSize(QSize(32, 32))
        ayar_btn.setFixedSize(42, 42)
        ayar_btn.setStyleSheet("""
            QPushButton { background: rgba(255,255,255,0.25); border-radius:20px; }
            QPushButton:hover { background: rgba(255,255,255,0.45); }
        """)
        ayar_btn.clicked.connect(self.ac_ayarlar)

        hl = QHBoxLayout()
        hl.addStretch()
        hl.addWidget(ayar_btn)
        hl.addStretch()
        main_layout.addLayout(hl)

        # Buton grid
        grid = QGridLayout()
        grid.setSpacing(35)
        positions = [(0,0), (0,1), (1,0), (1,1)]

        custom_icons = load_custom_icons()
        for i, (text, (icon_name, cmd)) in enumerate(BUTTONS.items()):
            icon_path = custom_icons.get(text, icon_name)
            btn = IconButton(text, icon_path)
            btn.clicked.connect(lambda _, c=cmd, t=text: self.islem(c, t))
            grid.addWidget(btn, *positions[i])

        main_layout.addLayout(grid)

        # Kapat butonu
        cancel_btn = QPushButton("X")
        cancel_btn.setFixedSize(60, 60)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,50,50,0.15);
                color: #ff5555;
                border-radius: 30px;
                font: bold 32px;
            }
            QPushButton:hover {
                background: rgba(255,50,50,0.35);
            }
        """)
        cancel_btn.clicked.connect(self.close)

        cg = QGridLayout()
        cg.addWidget(cancel_btn, 0, 0, Qt.AlignCenter)
        main_layout.addLayout(cg)

        self.setLayout(main_layout)

        # Hover label
        self.hover_label = QLabel(self)
        self.hover_label.setStyleSheet("""
            background: rgba(30,35,60,180);
            color: white;
            padding: 6px 12px;
            border-radius: 12px;
            font: 12px bold;
        """)
        self.hover_label.hide()

        self.show()

    def show_label(self, text, pos, y_offset=0):
        self.hover_label.setText(text)
        self.hover_label.adjustSize()
        self.hover_label.move(pos.x() - self.hover_label.width() // 2,
                              pos.y() + y_offset)
        self.hover_label.show()

    def ac_ayarlar(self):
        win = AyarPencere(self)
        win.exec_()

    def refresh_icons(self):
        custom_icons = load_custom_icons()
        for btn in self.findChildren(IconButton):
            icon_path = custom_icons.get(btn.text_name, BUTTONS[btn.text_name][0])
            if os.path.exists(icon_path):
                btn.setIcon(QIcon(icon_path))
            else:
                btn.setIcon(QIcon.fromTheme(icon_path))

    def islem(self, komut, isim):
        self.hide()
        self.onay = OnayPencere(self, komut)

    def onay_sonuc_geldi(self, onaylandi, komut):
        if onaylandi:
            os.system(komut)
        else:
            self.show()

# ------------------- ANA ÇALIŞMA -------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setDesktopFileName("oturum.desktop")
    app.setWindowIcon(QIcon("/usr/share/pixmaps/oturum.png"))
    win = PowerMenu()
    sys.exit(app.exec_())
