"""
WiFi Toolkit GUI  —   guided interface
Wraps: airmon-ng · airodump-ng · aircrack-ng · kismet

Requirements:
    pip install PyQt6

Run:
    sudo python main.py   (sudo needed for airmon/airodump/kismet)
"""

import sys, subprocess, shutil, re
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QLineEdit, QTextEdit, QFileDialog,
    QGroupBox, QFormLayout, QCheckBox, QSplitter, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QStackedWidget,
    QScrollArea, QStatusBar,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette, QTextCursor

# ── Palette ─────────────────────────────────────────────────────────────────
BG      = "#0d1117"
BG2     = "#161b22"
BG3     = "#21262d"
BORDER  = "#30363d"
ACCENT  = "#388bfd"
ACCENT2 = "#1f6feb"
GREEN   = "#3fb950"
RED     = "#f85149"
YELLOW  = "#d29922"
TEXT    = "#e6edf3"
TEXT2   = "#8b949e"

DARK_STYLE = f"""
QMainWindow, QWidget {{ background: {BG}; color: {TEXT}; font-family: "Segoe UI", "Inter", sans-serif; font-size: 13px; }}
QGroupBox {{
    border: 1px solid {BORDER}; border-radius: 8px; margin-top: 10px;
    padding: 8px; color: {TEXT2}; font-size: 11px; font-weight: bold;
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; }}
QLineEdit, QComboBox, QTextEdit {{
    background: {BG3}; border: 1px solid {BORDER}; border-radius: 6px;
    color: {TEXT}; padding: 5px 8px;
}}
QLineEdit:focus, QComboBox:focus {{ border: 1px solid {ACCENT}; }}
QComboBox::drop-down {{ border: none; }}
QComboBox QAbstractItemView {{ background: {BG3}; color: {TEXT}; selection-background-color: {ACCENT2}; }}
QPushButton {{
    background: {BG3}; border: 1px solid {BORDER}; border-radius: 6px;
    color: {TEXT}; padding: 6px 14px;
}}
QPushButton:hover {{ background: {BG2}; border-color: {ACCENT}; }}
QPushButton:pressed {{ background: {ACCENT2}; }}
QPushButton#primary {{ background: {ACCENT2}; border-color: {ACCENT}; color: white; font-weight: bold; }}
QPushButton#primary:hover {{ background: {ACCENT}; }}
QPushButton#danger {{ background: #4a1010; border-color: {RED}; color: {RED}; }}
QPushButton#danger:hover {{ background: #6b1515; }}
QPushButton#success {{ background: #0f2d1a; border-color: {GREEN}; color: {GREEN}; }}
QCheckBox {{ color: {TEXT}; spacing: 6px; }}
QCheckBox::indicator {{ width: 14px; height: 14px; border-radius: 3px; border: 1px solid {BORDER}; background: {BG3}; }}
QCheckBox::indicator:checked {{ background: {ACCENT2}; border-color: {ACCENT}; }}
QTableWidget {{
    background: {BG2}; border: 1px solid {BORDER}; border-radius: 6px;
    gridline-color: {BORDER}; color: {TEXT};
}}
QTableWidget::item:selected {{ background: {ACCENT2}; color: white; }}
QHeaderView::section {{
    background: {BG3}; color: {TEXT2}; border: none;
    border-bottom: 1px solid {BORDER}; padding: 5px 8px; font-weight: bold;
}}
QScrollBar:vertical {{ background: {BG2}; width: 8px; border-radius: 4px; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 4px; min-height: 20px; }}
QScrollBar:horizontal {{ background: {BG2}; height: 8px; border-radius: 4px; }}
QScrollBar::handle:horizontal {{ background: {BORDER}; border-radius: 4px; min-width: 20px; }}
QSplitter::handle {{ background: {BORDER}; }}
QStatusBar {{ background: {BG2}; border-top: 1px solid {BORDER}; color: {TEXT2}; }}
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def tool_ok(name): return shutil.which(name) is not None

def badge(text, color):
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"background:{color}22; color:{color}; border:1px solid {color}55;"
        f"border-radius:4px; padding:1px 8px; font-size:11px; font-weight:bold;"
    )
    lbl.setFixedHeight(22)
    return lbl

def section_label(text):
    lbl = QLabel(text)
    lbl.setStyleSheet(f"color:{TEXT2}; font-size:11px; font-weight:bold; margin-top:4px;")
    return lbl

def hint_label(text):
    lbl = QLabel(text)
    lbl.setStyleSheet(f"color:{TEXT2}; font-size:11px;")
    lbl.setWordWrap(True)
    return lbl

def separator():
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet(f"color:{BORDER};")
    return line

def scrollable(widget):
    """Wrap a widget in a vertical-only QScrollArea so it never gets squashed."""
    sa = QScrollArea()
    sa.setWidget(widget)
    sa.setWidgetResizable(True)
    sa.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    sa.setStyleSheet(f"QScrollArea {{ border: none; background: {BG}; }}")
    return sa


# ── Background subprocess runner ──────────────────────────────────────────────

class CommandRunner(QThread):
    output   = pyqtSignal(str)
    finished = pyqtSignal(int)
    error    = pyqtSignal(str)

    def __init__(self, cmd, use_sudo=False):
        super().__init__()
        self.cmd = cmd
        self.use_sudo = use_sudo
        self._proc = None
        self._abort = False

    def run(self):
        cmd = (["sudo"] + self.cmd) if self.use_sudo else self.cmd
        self.output.emit(f"$ {' '.join(cmd)}\n")
        try:
            self._proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1,
            )
            for line in self._proc.stdout:
                if self._abort: break
                self.output.emit(line)
            self._proc.wait()
            self.finished.emit(self._proc.returncode)
        except FileNotFoundError:
            self.error.emit(f"'{cmd[0]}' not found. Is it installed?")
        except Exception as e:
            self.error.emit(str(e))

    def stop(self):
        self._abort = True
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()


# ── Terminal widget ───────────────────────────────────────────────────────────

class Terminal(QTextEdit):
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setFont(QFont("Monospace", 10))
        self.setStyleSheet(
            f"background:{BG}; color:{TEXT}; border:1px solid {BORDER};"
            f"border-radius:6px; padding:8px;"
        )

    def write(self, text):
        c = self.textCursor()
        c.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(c)
        self.insertPlainText(text)
        self.ensureCursorVisible()

    def write_html(self, html):
        c = self.textCursor()
        c.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(c)
        self.insertHtml(html)
        self.ensureCursorVisible()

    def write_banner(self, text, color=GREEN):
        self.write_html(
            f'<div style="background:{color}22;border-left:3px solid {color};margin:2px 0;">'
            f'<span style="color:{color};font-weight:bold;font-family:monospace;">'
            f'  ★  {text}  ★</span></div><br>'
        )

    def write_error(self, text):
        self.write_html(
            f'<span style="color:{RED};font-family:monospace;">[ERROR] {text}</span><br>'
        )


# ── Sidebar nav button ────────────────────────────────────────────────────────

class NavButton(QPushButton):
    def __init__(self, icon_text, label):
        super().__init__()
        self.setText(f"  {icon_text}  {label}")
        self.setCheckable(True)
        self.setFixedHeight(44)
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: none; border-radius: 0;
                color: {TEXT2}; text-align: left; padding-left: 12px; font-size: 13px;
            }}
            QPushButton:hover {{ background: {BG3}; color: {TEXT}; }}
            QPushButton:checked {{
                background: {BG3}; color: {ACCENT};
                border-left: 3px solid {ACCENT};
            }}
        """)


# ══════════════════════════════════════════════════════════════════════════════
# Dashboard
# ══════════════════════════════════════════════════════════════════════════════

class DashboardPanel(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)

        title = QLabel("WiFi Toolkit")
        title.setStyleSheet(f"color:{TEXT}; font-size:22px; font-weight:bold;")
        sub = QLabel("A guided interface for wireless security tools.")
        sub.setStyleSheet(f"color:{TEXT2}; font-size:13px;")
        layout.addWidget(title)
        layout.addWidget(sub)
        layout.addWidget(separator())

        layout.addWidget(section_label("TOOL STATUS"))
        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)
        for tool, icon in [("airmon-ng","📡"), ("airodump-ng","🔍"), ("aircrack-ng","🔑"), ("kismet","🗺")]:
            card = QGroupBox()
            card.setStyleSheet(
                f"QGroupBox {{ background:{BG2}; border:1px solid {BORDER}; border-radius:8px; padding:12px; }}"
            )
            v = QVBoxLayout(card)
            v.setSpacing(4)
            ico = QLabel(icon)
            ico.setStyleSheet("font-size:22px; border:none;")
            nm = QLabel(tool)
            nm.setStyleSheet(f"color:{TEXT}; font-weight:bold; border:none;")
            ok = tool_ok(tool)
            st = badge("installed" if ok else "not found", GREEN if ok else RED)
            v.addWidget(ico)
            v.addWidget(nm)
            v.addWidget(st)
            cards_row.addWidget(card)
        layout.addLayout(cards_row)

        layout.addWidget(separator())
        layout.addWidget(section_label("TYPICAL WORKFLOW"))

        steps = [
            ("1", "airmon-ng",   "Put your wireless card into monitor mode so it can capture all nearby WiFi frames — not just those addressed to your device."),
            ("2", "airodump-ng", "Scan the air. Discover nearby access points and connected clients. Lock to a target's channel and BSSID to capture its WPA handshake."),
            ("3", "aireplay-ng", "Send controlled deauthentication frames to temporarily disconnect clients and force WPA/WPA2 handshakes for later analysis on authorized networks."),
            ("4", "aircrack-ng", "Crack the captured handshake using a dictionary wordlist (WPA)  to recover the network key."),
            
        ]
        for num, tool, desc in steps:
            row = QHBoxLayout()
            row.setSpacing(12)
            n = QLabel(num)
            n.setFixedSize(28, 28)
            n.setAlignment(Qt.AlignmentFlag.AlignCenter)
            n.setStyleSheet(
                f"background:{ACCENT2}; color:white; border-radius:14px; font-weight:bold; font-size:12px;"
            )
            t = QLabel(tool)
            t.setFixedWidth(100)
            t.setStyleSheet(f"color:{ACCENT}; font-weight:bold;")
            d = QLabel(desc)
            d.setWordWrap(True)
            d.setStyleSheet(f"color:{TEXT2};")
            row.addWidget(n)
            row.addWidget(t)
            row.addWidget(d, stretch=1)
            layout.addLayout(row)

        layout.addStretch()


# ══════════════════════════════════════════════════════════════════════════════
# airmon-ng
# ══════════════════════════════════════════════════════════════════════════════

class AirmonPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._runner = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        sp = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(20, 20, 12, 20)
        lv.setSpacing(12)

        lv.addWidget(QLabel("airmon-ng", styleSheet=f"color:{TEXT}; font-size:18px; font-weight:bold;"))
        lv.addWidget(hint_label(
            "airmon-ng enables or disables monitor mode on a wireless interface. "
            "Monitor mode allows the card to capture every WiFi frame it hears, "
            "regardless of destination — required by airodump-ng and other tools."
        ))
        lv.addWidget(separator())

        lv.addWidget(section_label("WIRELESS INTERFACE"))
        lv.addWidget(hint_label("The card you want to switch to monitor mode. Usually wlan0."))
        irow = QHBoxLayout()
        self.iface_combo = QComboBox()
        rbtn = QPushButton("↺ Refresh")
        rbtn.clicked.connect(self._refresh)
        irow.addWidget(self.iface_combo, stretch=1)
        irow.addWidget(rbtn)
        lv.addLayout(irow)

        lv.addWidget(section_label("CHANNEL  (optional)"))
        lv.addWidget(hint_label(
            "Lock the monitor interface to a specific channel after enabling monitor mode. "
            "airmon-ng's built-in channel argument is unreliable — the kernel overrides it immediately. "
            "This app uses  iw dev wlan0mon set channel N  after airmon-ng finishes, "
            "which is the correct and stable method. "
            "Leave blank to hop freely (airodump-ng will handle hopping on its own)."
        ))
        self.ch_edit = QLineEdit()
        self.ch_edit.setPlaceholderText("e.g.  6   or   36")
        lv.addWidget(self.ch_edit)

        self.kill_check = QCheckBox("Kill interfering processes first  (airmon-ng check kill)")
        lv.addWidget(self.kill_check)
        lv.addWidget(hint_label(
            "⚠  This stops NetworkManager and wpa_supplicant, disconnecting you from WiFi."
        ))

        lv.addWidget(separator())
        lv.addWidget(section_label("ACTIONS"))

        for text, obj, slot in [
            ("▶  Enable monitor mode",  "primary", self._start),
            ("■  Disable monitor mode", "danger",  self._stop),
            ("🔍  Check for conflicts", "",        self._check),
        ]:
            b = QPushButton(text)
            if obj: b.setObjectName(obj)
            b.clicked.connect(slot)
            lv.addWidget(b)

        lv.addStretch()

        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(12, 20, 20, 20)
        h = QHBoxLayout()
        h.addWidget(section_label("OUTPUT"))
        h.addStretch()
        cb = QPushButton("Clear"); cb.clicked.connect(lambda: self.term.clear())
        h.addWidget(cb)
        rv.addLayout(h)
        self.term = Terminal()
        rv.addWidget(self.term)

        sp.addWidget(scrollable(left)); sp.addWidget(right)
        sp.setSizes([300, 580])
        layout.addWidget(sp)
        self._refresh()

    def _refresh(self):
        self.iface_combo.clear()
        try:
            out = subprocess.check_output(["ip", "-o", "link", "show"], text=True)
            for line in out.splitlines():
                p = line.split(":")
                if len(p) >= 2:
                    n = p[1].strip().split("@")[0].strip()
                    if n != "lo": self.iface_combo.addItem(n)
        except Exception:
            self.iface_combo.addItem("wlan0")

    def _run(self, cmd):
        if not tool_ok("airmon-ng"):
            QMessageBox.warning(self, "Not found", "airmon-ng is not installed.\nsudo apt install aircrack-ng"); return
        if self._runner and self._runner.isRunning(): self._runner.stop()
        self._runner = CommandRunner(cmd, use_sudo=True)
        self._runner.output.connect(self.term.write)
        self._runner.error.connect(self.term.write_error)
        self._runner.finished.connect(lambda c: self.term.write_banner(f"Done (exit {c})", GREEN if c == 0 else RED))
        self._runner.start()

    def _start(self):
        iface = self.iface_combo.currentText().strip()
        if not iface: return
        ch = self.ch_edit.text().strip()

        # airmon-ng's channel argument is unreliable — the kernel overrides it.
        # Correct sequence:
        #   1. airmon-ng start wlan0           (no channel arg)
        #   2. iw dev wlan0mon set channel N   (immediately after)
        #   3. iw dev wlan0mon set channel N   (again 1s later — driver sometimes needs two)
        # Note: if you also run airodump-ng without -c it will re-hop channels
        # on its own. Always set the channel field in the airodump-ng panel too.

        def _lock_channel(code):
            if code != 0:
                self.term.write_banner(f"airmon-ng failed (exit {code})", RED)
                return
            mon = iface if iface.endswith("mon") else iface + "mon"
            if ch:
                self.term.write(f"[GUI] Locking {mon} to channel {ch}...\n")
                self._run(["iw", "dev", mon, "set", "channel", ch])
                # Re-lock after 1s — some drivers need two attempts
                QTimer.singleShot(1200, lambda: self._run(
                    ["iw", "dev", mon, "set", "channel", ch]
                ))
                self.term.write_banner(
                    f"Monitor mode up on {mon}, channel {ch}. "
                    f"Set the same channel in the airodump-ng panel to prevent re-hopping.",
                    GREEN
                )
            else:
                self.term.write_banner(
                    f"Monitor mode enabled on {mon} — no channel lock. "
                    f"airodump-ng will hop channels automatically.", GREEN
                )

        if self.kill_check.isChecked():
            self._run(["airmon-ng", "check", "kill"])
            QTimer.singleShot(1500, lambda: self._run_then(
                ["airmon-ng", "start", iface], _lock_channel
            ))
        else:
            self._run_then(["airmon-ng", "start", iface], _lock_channel)

    def _run_then(self, cmd, on_finished):
        """Run a command and call on_finished(exit_code) when it completes."""
        if not tool_ok("airmon-ng"):
            QMessageBox.warning(self, "Not found", "airmon-ng is not installed.\nsudo apt install aircrack-ng"); return
        if self._runner and self._runner.isRunning(): self._runner.stop()
        self._runner = CommandRunner(cmd, use_sudo=True)
        self._runner.output.connect(self.term.write)
        self._runner.error.connect(self.term.write_error)
        self._runner.finished.connect(on_finished)
        self._runner.start()

    def _stop(self):
        iface = self.iface_combo.currentText().strip()
        if iface: self._run(["airmon-ng", "stop", iface])

    def _check(self):
        self._run(["airmon-ng", "check"])


# ══════════════════════════════════════════════════════════════════════════════
# airodump-ng
# ══════════════════════════════════════════════════════════════════════════════

class AirodumpPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._runner = None
        self._ap_rows = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Horizontal split: scrollable left controls | right output area
        main_sp = QSplitter(Qt.Orientation.Horizontal)

        # ── LEFT: scrollable control panel ───────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background: {BG}; }}")

        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(20, 20, 16, 20)
        lv.setSpacing(12)

        lv.addWidget(QLabel("airodump-ng", styleSheet=f"color:{TEXT}; font-size:18px; font-weight:bold;"))
        lv.addWidget(hint_label(
            "airodump-ng passively scans all nearby WiFi traffic. "
            "It lists every access point and client it sees. "
            "When locked to a target's channel and BSSID, it captures the 4-way WPA handshake "
            "that occurs when a client (re)connects — which aircrack-ng can then crack."
        ))
        lv.addWidget(separator())

        # Capture settings
        lv.addWidget(section_label("INTERFACE & CHANNEL"))
        f1 = QFormLayout()
        self.iface_edit = QLineEdit(); self.iface_edit.setPlaceholderText("wlan0mon")
        self.ch_edit    = QLineEdit(); self.ch_edit.setPlaceholderText("blank = hop all channels")
        f1.addRow("Interface:", self.iface_edit)
        f1.addRow("Channel (-c):", self.ch_edit)
        lv.addLayout(f1)

        lv.addWidget(section_label("TARGET FILTER  (optional)"))
        f2 = QFormLayout()
        self.bssid_edit = QLineEdit(); self.bssid_edit.setPlaceholderText("AA:BB:CC:DD:EE:FF")
        self.band_combo = QComboBox(); self.band_combo.addItems(["Both (2.4 + 5 GHz)", "2.4 GHz only", "5 GHz only"])
        f2.addRow("BSSID:", self.bssid_edit)
        f2.addRow("Band:", self.band_combo)
        lv.addLayout(f2)

        lv.addWidget(section_label("SAVE TO FILE"))
        f3 = QFormLayout()
        self.write_edit = QLineEdit(); self.write_edit.setText("handshake")
        f3.addRow("Prefix (-w):", self.write_edit)
        lv.addLayout(f3)

        br = QHBoxLayout()
        self.run_btn  = QPushButton("▶  Start capture"); self.run_btn.setObjectName("primary"); self.run_btn.clicked.connect(self._start)
        self.stop_btn = QPushButton("■  Stop");          self.stop_btn.setObjectName("danger");  self.stop_btn.clicked.connect(self._stop)
        br.addWidget(self.run_btn); br.addWidget(self.stop_btn)
        lv.addLayout(br)

        lv.addStretch()
        scroll.setWidget(left)
        main_sp.addWidget(scroll)

        # ── RIGHT: AP table + terminal stacked vertically ─────────────────────
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(12, 20, 20, 20)
        rv.setSpacing(8)

        rv.addWidget(section_label("DISCOVERED ACCESS POINTS"))
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["BSSID", "PWR", "CH", "Beacons", "#Data", "ESSID"])
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setMinimumHeight(160)
        rv.addWidget(self.table)

        out_hdr = QHBoxLayout()
        out_hdr.addWidget(section_label("RAW OUTPUT"))
        out_hdr.addStretch()
        cb = QPushButton("Clear"); cb.clicked.connect(self._clear)
        out_hdr.addWidget(cb)
        rv.addLayout(out_hdr)
        self.term = Terminal()
        rv.addWidget(self.term, stretch=1)

        main_sp.addWidget(right)
        main_sp.setSizes([320, 660])
        layout.addWidget(main_sp)

    def _csv_path(self):
        """
        airodump-ng writes the CSV next to wherever it was launched from.
        We use an absolute path so we always know where to look regardless
        of the working directory the app was started from.
        """
        import os
        prefix = self.write_edit.text().strip() or "handshake"
        # If the user typed a relative prefix, anchor it to the home directory
        # so sudo doesn't write it to /root unexpectedly.
        if not os.path.isabs(prefix):
            prefix = os.path.join(os.path.expanduser("~"), prefix)
        return f"{prefix}-01.csv"

    def _build_cmd(self):
        import os
        cmd = ["airodump-ng"]
        ch = self.ch_edit.text().strip()
        if ch: cmd += ["-c", ch]
        bssid = self.bssid_edit.text().strip()
        if bssid: cmd += ["--bssid", bssid]
        band = self.band_combo.currentIndex()
        if band == 1: cmd += ["--band", "bg"]
        elif band == 2: cmd += ["--band", "a"]
        # Use absolute prefix so the file lands somewhere we can actually find it.
        prefix = self.write_edit.text().strip() or "handshake"
        if not os.path.isabs(prefix):
            prefix = os.path.join(os.path.expanduser("~"), prefix)
        cmd += ["-w", prefix, "--output-format", "pcap,csv"]
        cmd.append(self.iface_edit.text().strip() or "wlan0mon")
        return cmd

    def _start(self):
        if not tool_ok("airodump-ng"):
            QMessageBox.warning(self, "Not found", "airodump-ng not found.\nsudo apt install aircrack-ng"); return
        if self._runner and self._runner.isRunning(): self._runner.stop()
        self._runner = CommandRunner(self._build_cmd(), use_sudo=True)
        self._runner.output.connect(self._handle_raw)
        self._runner.error.connect(self.term.write_error)
        self._runner.start()
        csv = self._csv_path()
        self.term.write(f"[GUI] CSV will be read from: {csv}\n")
        self.term.write(f"[GUI] AP table refreshes every 2 seconds once that file appears.\n\n")
        self._csv_timer = QTimer(self)
        self._csv_timer.timeout.connect(self._poll_csv)
        self._csv_timer.start(2000)

    def _stop(self):
        if hasattr(self, "_csv_timer"): self._csv_timer.stop()
        if self._runner: self._runner.stop()

    def _clear(self):
        self.term.clear()
        self.table.setRowCount(0)
        self._ap_rows.clear()

    def _handle_raw(self, line):
        clean = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", line)
        if clean.strip():
            self.term.write(clean)
        if "WPA handshake" in line:
            self.term.write_banner("WPA handshake captured! → take the .cap file to aircrack-ng", GREEN)

    def _poll_csv(self):
        """
        Parse the CSV airodump-ng writes alongside the capture file.

        Real airodump-ng CSV column order (0-indexed):
          0  BSSID
          1  First time seen
          2  Last time seen
          3  channel
          4  Speed
          5  Privacy
          6  Cipher
          7  Authentication
          8  Power
          9  # beacons
          10 # IV
          11 LAN IP
          12 ID-length
          13 ESSID
          14 Key
        """
        import os
        csv_file = self._csv_path()
        if not os.path.exists(csv_file):
            return
        try:
            with open(csv_file, "r", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            self.term.write(f"[GUI] Could not read CSV: {e}\n")
            return

        # The file has two sections divided by a blank line:
        # section 1 = APs, section 2 = clients
        sections = re.split(r"\n\s*\n", content)
        ap_section = sections[0] if sections else ""

        for line in ap_section.splitlines():
            line = line.strip()
            # Skip header and empty lines
            if not line or line.upper().startswith("BSSID"):
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 14:
                continue
            bssid = parts[0]
            # Validate it looks like a MAC address
            if not re.match(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$", bssid):
                continue
            ch      = parts[3]
            power   = parts[8]
            beacons = parts[9]
            data    = parts[10]
            essid   = parts[13] if parts[13] else "<hidden>"

            if bssid in self._ap_rows:
                row = self._ap_rows[bssid]
            else:
                row = self.table.rowCount()
                self.table.insertRow(row)
                self._ap_rows[bssid] = row
            for col, val in enumerate([bssid, power, ch, beacons, data, essid]):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, col, item)


# ══════════════════════════════════════════════════════════════════════════════
# aircrack-ng
# ══════════════════════════════════════════════════════════════════════════════

class AircrackPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._runner = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        sp = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(20, 20, 12, 20)
        lv.setSpacing(12)

        lv.addWidget(QLabel("aircrack-ng", styleSheet=f"color:{TEXT}; font-size:18px; font-weight:bold;"))
        lv.addWidget(hint_label(
            "aircrack-ng recovers WiFi keys from captured packets. "
            "For WPA/WPA2 it runs a dictionary attack — it hashes every word in your wordlist "
            "and checks whether it matches the handshake's MIC value. "
            "For WEP it uses statistical attacks (PTW/FMS) and needs ~20 000+ IVs."
        ))
        lv.addWidget(separator())

        lv.addWidget(section_label("CAPTURE FILE  (.cap / .pcap)"))
        lv.addWidget(hint_label("The file saved by airodump-ng. Must contain at least one complete WPA handshake."))
        cr = QHBoxLayout()
        self.cap_edit = QLineEdit(); self.cap_edit.setPlaceholderText("handshake-01.cap")
        cb = QPushButton("Browse…"); cb.clicked.connect(lambda: self._browse(self.cap_edit, "Cap files (*.cap *.pcap)"))
        cr.addWidget(self.cap_edit, stretch=1); cr.addWidget(cb)
        lv.addLayout(cr)

        lv.addWidget(section_label("WORDLIST  (WPA dictionary attack)"))
        lv.addWidget(hint_label(
            "One password per line. Common choices: /usr/share/wordlists/rockyou.txt, "
            "SecLists, or a custom list. Leave blank for WEP mode."
        ))
        wr = QHBoxLayout()
        self.wl_edit = QLineEdit(); self.wl_edit.setPlaceholderText("/usr/share/wordlists/rockyou.txt")
        wb = QPushButton("Browse…"); wb.clicked.connect(lambda: self._browse(self.wl_edit, "Text files (*.txt)"))
        wr.addWidget(self.wl_edit, stretch=1); wr.addWidget(wb)
        lv.addLayout(wr)

        lv.addWidget(section_label("FILTERS  (optional)"))
        lv.addWidget(hint_label("If the capture has multiple networks, filter to the one you want."))
        f = QFormLayout()
        self.bssid_edit = QLineEdit(); self.bssid_edit.setPlaceholderText("AA:BB:CC:DD:EE:FF")
        self.essid_edit = QLineEdit(); self.essid_edit.setPlaceholderText("NetworkName")
        f.addRow("BSSID (-b):", self.bssid_edit)
        f.addRow("ESSID (-e):", self.essid_edit)
        lv.addLayout(f)

        lv.addWidget(separator())
        self.run_btn  = QPushButton("▶  Run aircrack-ng"); self.run_btn.setObjectName("primary"); self.run_btn.clicked.connect(self._run)
        self.stop_btn = QPushButton("■  Stop");            self.stop_btn.setObjectName("danger");  self.stop_btn.clicked.connect(self._stop)
        lv.addWidget(self.run_btn); lv.addWidget(self.stop_btn)
        lv.addStretch()

        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(12, 20, 20, 20)
        h = QHBoxLayout()
        h.addWidget(section_label("OUTPUT"))
        h.addStretch()
        self.key_label = QLabel("")
        self.key_label.setStyleSheet(
            f"background:{GREEN}22; color:{GREEN}; border:1px solid {GREEN}55;"
            f"border-radius:4px; padding:4px 12px; font-weight:bold;"
        )
        self.key_label.setVisible(False)
        h.addWidget(self.key_label)
        cb = QPushButton("Clear"); cb.clicked.connect(lambda: self.term.clear()); h.addWidget(cb)
        rv.addLayout(h)
        self.term = Terminal()
        rv.addWidget(self.term)

        sp.addWidget(scrollable(left)); sp.addWidget(right)
        sp.setSizes([320, 560])
        layout.addWidget(sp)

    def _browse(self, widget, filt):
        p, _ = QFileDialog.getOpenFileName(self, "Select file", "", filt + ";;All files (*)")
        if p: widget.setText(p)

    def _build_cmd(self):
        cap = self.cap_edit.text().strip()
        if not cap:
            QMessageBox.warning(self, "Missing file", "Please select a capture file."); return None
        cmd = ["aircrack-ng"]
        wl = self.wl_edit.text().strip()
        if wl: cmd += ["-w", wl]
        b = self.bssid_edit.text().strip()
        if b: cmd += ["-b", b]
        e = self.essid_edit.text().strip()
        if e: cmd += ["-e", e]
        cmd += ["-a", "2"]   # always WPA/WPA2
        cmd.append(cap)
        return cmd

    def _run(self):
        if not tool_ok("aircrack-ng"):
            QMessageBox.warning(self, "Not found", "aircrack-ng is not installed.\nsudo apt install aircrack-ng"); return
        cmd = self._build_cmd()
        if not cmd: return
        self.key_label.setVisible(False)
        if self._runner and self._runner.isRunning(): self._runner.stop()
        self._runner = CommandRunner(cmd)
        self._runner.output.connect(self._handle)
        self._runner.error.connect(self.term.write_error)
        self._runner.finished.connect(lambda c: self.term.write_banner(f"Done (exit {c})", GREEN if c == 0 else RED))
        self._runner.start()

    def _stop(self):
        if self._runner: self._runner.stop()

    def _handle(self, line):
        self.term.write(line)
        m = re.search(r"KEY FOUND!\s*\[\s*(.*?)\s*\]", line, re.IGNORECASE)
        if m:
            key = m.group(1)
            self.term.write_banner(f"KEY FOUND:  {key}", GREEN)
            self.key_label.setText(f"  ★  KEY FOUND:  {key}  ★")
            self.key_label.setVisible(True)


# ══════════════════════════════════════════════════════════════════════════════
# Kismet
# ══════════════════════════════════════════════════════════════════════════════

class KismetPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._runner = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        sp = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(20, 20, 12, 20)
        lv.setSpacing(12)

        lv.addWidget(QLabel("kismet", styleSheet=f"color:{TEXT}; font-size:18px; font-weight:bold;"))
        lv.addWidget(hint_label(
            "Kismet is a passive wireless network detector, sniffer, and intrusion detection system. "
            "Unlike airodump-ng it runs as a service with a full web UI at localhost:2501 "
            "where you see a live map of every AP and client, their signal levels, "
            "manufacturer info, and historical data. It logs everything to .kismet and .pcapng files."
        ))
        lv.addWidget(separator())

        lv.addWidget(section_label("CAPTURE SOURCE"))
        lv.addWidget(hint_label(
            "The monitor-mode interface(s) to capture on. Kismet handles channel hopping internally. "
            "You can add multiple sources separated by commas: wlan0mon,wlan1mon"
        ))
        self.src_edit = QLineEdit(); self.src_edit.setPlaceholderText("wlan0mon")
        lv.addWidget(self.src_edit)

        lv.addWidget(section_label("LOGGING"))
        f = QFormLayout()
        self.pfx_edit = QLineEdit(); self.pfx_edit.setText("kismet")
        dr = QHBoxLayout()
        self.dir_edit = QLineEdit(); self.dir_edit.setPlaceholderText("/tmp")
        db = QPushButton("Browse…"); db.clicked.connect(self._browse_dir)
        dr.addWidget(self.dir_edit, stretch=1); dr.addWidget(db)
        f.addRow("Log prefix:", self.pfx_edit)
        f.addRow("Directory:", dr)
        lv.addLayout(f)

        self.no_log_check = QCheckBox("Disable file logging  (--no-logging)")
        lv.addWidget(self.no_log_check)
        lv.addWidget(hint_label("Useful for demos — Kismet still shows everything in the web UI but writes nothing to disk."))

        lv.addWidget(section_label("EXTRA FLAGS"))
        self.extra_edit = QLineEdit(); self.extra_edit.setPlaceholderText("e.g.  --override=site.conf")
        lv.addWidget(self.extra_edit)

        lv.addWidget(separator())
        for text, obj, slot in [
            ("▶  Start kismet",                  "primary", self._start),
            ("■  Stop kismet",                   "danger",  self._stop),
            ("🌐  Open web UI → localhost:2501",  "success", self._open_webui),
        ]:
            b = QPushButton(text)
            if obj: b.setObjectName(obj)
            b.clicked.connect(slot)
            lv.addWidget(b)
        lv.addStretch()

        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(12, 20, 20, 20)
        h = QHBoxLayout()
        h.addWidget(section_label("OUTPUT"))
        h.addStretch()
        cb = QPushButton("Clear"); cb.clicked.connect(lambda: self.term.clear()); h.addWidget(cb)
        rv.addLayout(h)
        self.term = Terminal()
        rv.addWidget(self.term)

        sp.addWidget(scrollable(left)); sp.addWidget(right)
        sp.setSizes([300, 580])
        layout.addWidget(sp)

    def _browse_dir(self):
        p = QFileDialog.getExistingDirectory(self, "Select log directory")
        if p: self.dir_edit.setText(p)

    def _build_cmd(self):
        cmd = ["kismet"]
        src = self.src_edit.text().strip()
        if src: cmd += ["-c", src]
        pfx = self.pfx_edit.text().strip()
        if pfx: cmd += ["--log-prefix", pfx]
        d = self.dir_edit.text().strip()
        if d: cmd += ["--log-path", d]
        if self.no_log_check.isChecked(): cmd.append("--no-logging")
        extra = self.extra_edit.text().strip()
        if extra: cmd += extra.split()
        return cmd

    def _start(self):
        if not tool_ok("kismet"):
            QMessageBox.warning(self, "Not found", "kismet is not installed.\nsudo apt install kismet"); return
        if self._runner and self._runner.isRunning(): self._runner.stop()
        self._runner = CommandRunner(self._build_cmd(), use_sudo=True)
        self._runner.output.connect(self._handle)
        self._runner.error.connect(self.term.write_error)
        self._runner.finished.connect(lambda c: self.term.write_banner(f"Kismet stopped (exit {c})", YELLOW))
        self._runner.start()

    def _stop(self):
        if self._runner: self._runner.stop()

    def _open_webui(self):
        subprocess.Popen(["xdg-open", "http://localhost:2501"])

    def _handle(self, line):
        self.term.write(line)
        if any(kw in line for kw in ("Kismet starting", "Starting Kismet", "Launching kismet")):
            self.term.write_banner("Kismet is running — open the web UI to explore discovered networks", GREEN)


# ══════════════════════════════════════════════════════════════════════════════
# aireplay-ng
# ══════════════════════════════════════════════════════════════════════════════

class AireplayPanel(QWidget):
    """Dedicated aireplay-ng deauth panel — mirrors airmon-ng layout."""

    def __init__(self):
        super().__init__()
        self._runner = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        sp = QSplitter(Qt.Orientation.Horizontal)

        # ── Left: controls ────────────────────────────────────────────────────
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(20, 20, 12, 20)
        lv.setSpacing(12)

        lv.addWidget(QLabel("aireplay-ng", styleSheet=f"color:{TEXT}; font-size:18px; font-weight:bold;"))
        lv.addWidget(hint_label(
            "aireplay-ng injects 802.11 frames into a network. "
            "Its most common use is the deauthentication attack (-0): "
            "it sends forged deauth frames to a client, forcing it to disconnect "
            "and immediately reconnect to its AP — which triggers a WPA handshake "
            "that airodump-ng can capture."
        ))
        lv.addWidget(separator())

        # Interface
        lv.addWidget(section_label("INTERFACE"))
        lv.addWidget(hint_label(
            "Must be in monitor mode and support packet injection. "
            "Use the Hardening panel to verify injection capability before running deauth."
        ))
        irow = QHBoxLayout()
        self.iface_edit = QLineEdit()
        self.iface_edit.setPlaceholderText("wlan0mon")
        rbtn = QPushButton("↺ Refresh")
        rbtn.clicked.connect(self._refresh_ifaces)
        self.iface_combo = QComboBox()
        irow.addWidget(self.iface_combo, stretch=1)
        irow.addWidget(rbtn)
        lv.addLayout(irow)

        lv.addWidget(separator())

        # Deauth options
        lv.addWidget(section_label("DEAUTH ATTACK  (-0)"))
        lv.addWidget(hint_label(
            "Sends deauthentication frames to kick a client off the AP. "
            "Count 0 means continuous — it keeps sending until you press Stop. "
            "A specific client MAC targets one device; leaving it blank broadcasts "
            "deauth to every client on the AP (more disruptive, use carefully)."
        ))

        f = QFormLayout()
        f.setSpacing(8)

        self.ap_edit = QLineEdit()
        self.ap_edit.setPlaceholderText("AA:BB:CC:DD:EE:FF  — target AP  (required)")
        f.addRow("AP BSSID (-a):", self.ap_edit)

        self.client_edit = QLineEdit()
        self.client_edit.setPlaceholderText("11:22:33:44:55:66  — blank = broadcast to all clients")
        f.addRow("Client MAC (-c):", self.client_edit)

        self.count_edit = QLineEdit()
        self.count_edit.setText("0")
        self.count_edit.setPlaceholderText("0 = continuous, 5 = send 5 bursts")
        f.addRow("Count (-0):", self.count_edit)

        lv.addLayout(f)

        lv.addWidget(hint_label(
            "⚠  Count 0 runs forever — use Stop to end it. "
            "Only use on networks you own or have written permission to test. "
            "Devices using 802.11w (Protected Management Frames) will ignore deauth."
        ))

        lv.addWidget(separator())

        self.start_btn = QPushButton("⚡  Send deauth")
        self.start_btn.setObjectName("danger")
        self.start_btn.clicked.connect(self._start)
        self.stop_btn = QPushButton("■  Stop")
        self.stop_btn.clicked.connect(self._stop)
        lv.addWidget(self.start_btn)
        lv.addWidget(self.stop_btn)
        lv.addStretch()

        # ── Right: terminal ───────────────────────────────────────────────────
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(12, 20, 20, 20)
        h = QHBoxLayout()
        h.addWidget(section_label("OUTPUT"))
        h.addStretch()
        cb = QPushButton("Clear")
        cb.clicked.connect(self.term.clear if hasattr(self, "term") else lambda: None)
        h.addWidget(cb)
        rv.addLayout(h)
        self.term = Terminal()
        # Fix clear button now that self.term exists
        cb.clicked.disconnect()
        cb.clicked.connect(self.term.clear)
        rv.addWidget(self.term)

        sp.addWidget(scrollable(left))
        sp.addWidget(right)
        sp.setSizes([320, 580])
        layout.addWidget(sp)

        self._refresh_ifaces()

    def _refresh_ifaces(self):
        self.iface_combo.clear()
        try:
            out = subprocess.check_output(["ip", "-o", "link", "show"], text=True)
            for line in out.splitlines():
                parts = line.split(":")
                if len(parts) >= 2:
                    name = parts[1].strip().split("@")[0].strip()
                    if name != "lo":
                        self.iface_combo.addItem(name)
        except Exception:
            self.iface_combo.addItem("wlan0mon")

    def _selected_iface(self):
        return self.iface_combo.currentText().strip() or "wlan0mon"

    def _run_cmd(self, cmd):
        if not tool_ok("aireplay-ng"):
            QMessageBox.warning(self, "Not found", "aireplay-ng not found.\nsudo apt install aircrack-ng")
            return
        if self._runner and self._runner.isRunning():
            self._runner.stop()
        self._runner = CommandRunner(cmd, use_sudo=True)
        self._runner.output.connect(self.term.write)
        self._runner.error.connect(self.term.write_error)
        self._runner.finished.connect(self._on_finished)
        self._runner.start()

    def _start(self):
        ap = self.ap_edit.text().strip()
        if not ap:
            QMessageBox.warning(self, "Missing BSSID", "Enter the AP BSSID before sending deauth.")
            return
        count  = self.count_edit.text().strip() or "0"
        client = self.client_edit.text().strip()
        cmd = ["aireplay-ng", "-0", count, "-a", ap]
        if client:
            cmd += ["-c", client]
        cmd.append(self._selected_iface())
        if count == "0":
            self.term.write("[GUI] Count is 0 — running continuously. Press Stop to end.\n\n")
        self._run_cmd(cmd)

    def _stop(self):
        if self._runner:
            self._runner.stop()

    def _on_finished(self, code):
        messages = {
            0: ("Done.", GREEN),
            7: (
                "Exit code 7 — injection failed. "
                "Your card may not support injection, or the interface is not in monitor mode. "
                "Run the injection test first.",
                RED
            ),
        }
        text, color = messages.get(code, (f"aireplay-ng exited with code {code}. "
            "If the target was unaffected it likely uses 802.11w Protected Management Frames.", YELLOW))
        self.term.write_banner(text, color)


# ══════════════════════════════════════════════════════════════════════════════
# Hardening panel
# ══════════════════════════════════════════════════════════════════════════════

class HardeningPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._pmf_runner = None
        self._inj_runner = None
        self._ids_runner = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        sp = QSplitter(Qt.Orientation.Horizontal)

        # ── LEFT: controls ────────────────────────────────────────────────────
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(20, 20, 12, 20)
        lv.setSpacing(12)

        lv.addWidget(QLabel("WiFi Hardening", styleSheet=f"color:{TEXT}; font-size:18px; font-weight:bold;"))
        lv.addWidget(hint_label(
            "Use these tools to assess and improve the security of a WiFi network you own or administer. "
            "Each test is read-only and passive — nothing is transmitted to the target network."
        ))
        lv.addWidget(separator())

        # ── PMF test ──────────────────────────────────────────────────────────
        lv.addWidget(section_label("TEST 1 — PMF / DEAUTH PROTECTION"))
        lv.addWidget(hint_label(
            "Protected Management Frames (802.11w) prevent deauthentication attacks by "
            "cryptographically signing management frames. Without PMF, any nearby attacker "
            "can forcibly disconnect clients from your network at will.\n\n"
            "This test scans for the target SSID and reads the RSN Capabilities field "
            "from its beacon frames to determine whether PMF is disabled, optional, or required."
        ))

        f1 = QFormLayout()
        f1.setSpacing(8)
        self.pmf_iface_edit = QLineEdit(); self.pmf_iface_edit.setPlaceholderText("wlan0  or  wlan0mon")
        self.pmf_ssid_edit  = QLineEdit(); self.pmf_ssid_edit.setPlaceholderText("YourNetworkName")
        f1.addRow("Interface:", self.pmf_iface_edit)
        f1.addRow("SSID:", self.pmf_ssid_edit)
        lv.addLayout(f1)

        pmf_btn = QPushButton("🔬  Test PMF status")
        pmf_btn.setObjectName("primary")
        pmf_btn.clicked.connect(self._test_pmf)
        lv.addWidget(pmf_btn)

        lv.addWidget(separator())

        # ── Injection test ────────────────────────────────────────────────────
        lv.addWidget(section_label("TEST 2 — PACKET INJECTION CAPABILITY"))
        lv.addWidget(hint_label(
            "Tests whether your wireless card and driver support packet injection. "
            "Injection is required for active attacks like deauth. "
            "If this fails, your card cannot perform deauth attacks — "
            "which from a defender's perspective means an attacker with the same card also cannot.\n\n"
            "Uses:  aireplay-ng --test"
        ))

        f2 = QFormLayout()
        f2.setSpacing(8)
        self.inj_iface_edit = QLineEdit(); self.inj_iface_edit.setPlaceholderText("wlan0mon  (must be in monitor mode)")
        f2.addRow("Interface:", self.inj_iface_edit)
        lv.addLayout(f2)

        inj_btn = QPushButton("🔬  Test injection capability")
        inj_btn.setObjectName("primary")
        inj_btn.clicked.connect(self._test_injection)
        lv.addWidget(inj_btn)

        lv.addWidget(separator())

        # ── Kismet IDS ────────────────────────────────────────────────────────
        lv.addWidget(section_label("TEST 3 — KISMET AS IDS  (deauth flood detection)"))
        lv.addWidget(hint_label(
            "Kismet can act as a passive intrusion detection system. "
            "When run in IDS mode it alerts on deauth floods — a sudden burst of deauthentication "
            "frames is a clear sign someone nearby is running aireplay-ng against your network. "
            "It also detects evil twin APs (a rogue AP using your SSID to steal credentials).\n\n"
            "This starts Kismet in headless IDS mode with alerts logged to the terminal. "
            "Open the web UI at localhost:2501 for a full visual view of alerts."
        ))

        f3 = QFormLayout()
        f3.setSpacing(8)
        self.ids_iface_edit = QLineEdit(); self.ids_iface_edit.setPlaceholderText("wlan0mon")
        f3.addRow("Monitor interface:", self.ids_iface_edit)
        lv.addLayout(f3)

        lv.addWidget(hint_label(
            "Kismet will alert on:\n"
            "  DEAUTHFLOOD — more than 5 deauth frames per second from one source\n"
            "  DISASSOCFLOOD — same for disassociation frames\n"
            "  APSPOOF — SSID being broadcast from an unexpected BSSID (evil twin)\n"
            "  BCASTDISCON — broadcast deauth targeting all clients simultaneously"
        ))

        ids_row = QHBoxLayout()
        self.ids_start_btn = QPushButton("▶  Start Kismet IDS")
        self.ids_start_btn.setObjectName("primary")
        self.ids_start_btn.clicked.connect(self._start_ids)
        self.ids_stop_btn = QPushButton("■  Stop")
        self.ids_stop_btn.setObjectName("danger")
        self.ids_stop_btn.clicked.connect(self._stop_ids)
        self.ids_webui_btn = QPushButton("🌐  Web UI")
        self.ids_webui_btn.clicked.connect(lambda: subprocess.Popen(["xdg-open", "http://localhost:2501"]))
        ids_row.addWidget(self.ids_start_btn)
        ids_row.addWidget(self.ids_stop_btn)
        ids_row.addWidget(self.ids_webui_btn)
        lv.addLayout(ids_row)

        lv.addWidget(separator())
        lv.addWidget(section_label("HARDENING CHECKLIST"))

        checks = [
            ("Use WPA3 or WPA2/WPA3 mixed mode",
             "WPA3 uses SAE instead of PSK — eliminates offline handshake cracking entirely."),
            ("Enable PMF (Required if possible)",
             "Prevents deauth attacks. Set to Required if all your devices support it, Optional otherwise."),
            ("Use a long random passphrase (20+ chars)",
             "Offline dictionary attacks only work if the password is in a wordlist. Random passphrases are immune."),
            ("Disable WPS",
             "WPS PIN is vulnerable to Pixie Dust and brute force attacks regardless of passphrase strength."),
            ("Isolate IoT devices on a separate VLAN",
             "IP cameras, smart devices etc. often lack PMF and updates. Keep them off your main network."),
            ("Enable AP client isolation on guest networks",
             "Prevents clients from communicating with each other — essential for untrusted networks."),
            ("Monitor for deauth floods with Kismet IDS",
             "A sudden burst of deauth frames is a clear sign someone is running aireplay-ng nearby."),
        ]

        for title, desc in checks:
            row = QHBoxLayout()
            row.setSpacing(8)
            icon = QLabel("✓")
            icon.setFixedWidth(18)
            icon.setStyleSheet(f"color:{GREEN}; font-weight:bold; font-size:14px;")
            col = QVBoxLayout()
            t = QLabel(title)
            t.setStyleSheet(f"color:{TEXT}; font-weight:bold;")
            d = QLabel(desc)
            d.setWordWrap(True)
            d.setStyleSheet(f"color:{TEXT2}; font-size:11px;")
            col.addWidget(t)
            col.addWidget(d)
            col.setSpacing(2)
            row.addWidget(icon)
            row.addLayout(col, stretch=1)
            lv.addLayout(row)

        lv.addStretch()
        sp.addWidget(scrollable(left))

        # ── RIGHT: output ─────────────────────────────────────────────────────
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(12, 20, 20, 20)
        h = QHBoxLayout()
        h.addWidget(section_label("TEST OUTPUT"))
        h.addStretch()
        cb = QPushButton("Clear")
        rv.addLayout(h)
        self.term = Terminal()
        cb.clicked.connect(self.term.clear)
        h.addWidget(cb)
        rv.addWidget(self.term)

        sp.addWidget(right)
        sp.setSizes([380, 500])
        layout.addWidget(sp)

    def _test_pmf(self):
        iface = self.pmf_iface_edit.text().strip() or "wlan0"
        ssid  = self.pmf_ssid_edit.text().strip()
        if not ssid:
            QMessageBox.warning(self, "Missing SSID", "Enter the SSID of the network to test."); return
        if not tool_ok("iw"):
            QMessageBox.warning(self, "Not found", "iw not found.\nsudo apt install iw"); return
        self.term.write(f"[GUI] Scanning on {iface} — this takes a few seconds...\n\n")
        if self._pmf_runner and self._pmf_runner.isRunning():
            self._pmf_runner.stop()
        self._pmf_runner = CommandRunner(["iw", "dev", iface, "scan", "flush"], use_sudo=True)
        self._pmf_scan_buf = []
        self._pmf_ssid = ssid
        self._pmf_runner.output.connect(self._handle_pmf_line)
        self._pmf_runner.error.connect(self.term.write_error)
        self._pmf_runner.finished.connect(self._finish_pmf)
        self._pmf_runner.start()

    def _handle_pmf_line(self, line):
        # Just buffer — don't try to parse mid-stream because the SSID line
        # comes AFTER the RSN Capabilities line in the iw output block.
        self._pmf_scan_buf.append(line)
        self.term.write(line)

    def _finish_pmf(self, code):
        ssid = self._pmf_ssid
        full = "".join(self._pmf_scan_buf)

        # Split into per-BSS blocks. Each block starts with "BSS xx:xx:xx..."
        blocks = re.split(r"(?=^BSS )", full, flags=re.MULTILINE)

        target_block = None
        for block in blocks:
            # iw puts the SSID as "SSID: <name>" — match exactly to avoid
            # partial matches (e.g. "Home" matching "HomeGuest")
            if re.search(rf"^\s*SSID: {re.escape(ssid)}\s*$", block, re.MULTILINE):
                target_block = block
                break

        if target_block is None:
            self.term.write_banner(
                f"'{ssid}' not found in scan. "
                f"Check the SSID spelling, make sure the interface is up, "
                f"and that the network is in range.",
                YELLOW
            )
            return

        self.term.write(f"\n[GUI] Found BSS block for '{ssid}' — checking RSN capabilities...\n")

        # Look for RSN section then its Capabilities line within that block.
        # iw output structure inside a BSS block:
        #   RSN:     * Version: 1
        #            * Group cipher: ...
        #            * Capabilities: 0x0000
        rsn_match = re.search(
            r"RSN:(?:\n\s+\*.*?)*?\n\s+\* Capabilities:.*?\((0x[0-9a-fA-F]+)\)",
            target_block
        )

        if not rsn_match:
            # No RSN section at all — open network or WEP
            self.term.write_banner(
                f"No RSN/WPA2 information found for '{ssid}'. "
                f"The network may be open or using WEP — PMF is not applicable.",
                YELLOW
            )
            return

        cap = int(rsn_match.group(1), 16)
        pmf_required = bool(cap & 0x0080)
        pmf_capable  = bool(cap & 0x0040)

        self.term.write(f"[GUI] RSN Capabilities: 0x{cap:04x}\n")
        self.term.write(f"[GUI] Bit 6 (PMF capable/optional): {int(pmf_capable)}\n")
        self.term.write(f"[GUI] Bit 7 (PMF required):          {int(pmf_required)}\n\n")

        if pmf_required:
            self.term.write_banner(
                f"PMF REQUIRED (0x{cap:04x}) — fully protected against deauth attacks ✓",
                GREEN
            )
        elif pmf_capable:
            self.term.write_banner(
                f"PMF OPTIONAL (0x{cap:04x}) — partially protected. "
                f"Upgrade to PMF Required in your router settings for full protection.",
                YELLOW
            )
        else:
            self.term.write_banner(
                f"PMF DISABLED (0x{cap:04x}) — vulnerable to deauth attacks. "
                f"Enable Protected Management Frames in your router's wireless security settings.",
                RED
            )

    def _test_injection(self):
        iface = self.inj_iface_edit.text().strip() or "wlan0mon"
        if not tool_ok("aireplay-ng"):
            QMessageBox.warning(self, "Not found", "aireplay-ng not found.\nsudo apt install aircrack-ng"); return
        self.term.write(f"[GUI] Testing packet injection on {iface}...\n\n")
        if self._inj_runner and self._inj_runner.isRunning():
            self._inj_runner.stop()
        self._inj_runner = CommandRunner(["aireplay-ng", "--test", iface], use_sudo=True)
        self._inj_runner.output.connect(self._handle_inj_line)
        self._inj_runner.error.connect(self.term.write_error)
        self._inj_runner.finished.connect(self._finish_inj)
        self._inj_runner.start()

    def _handle_inj_line(self, line):
        self.term.write(line)

    def _finish_inj(self, code):
        if code == 0:
            self.term.write_banner("Injection test passed — card supports packet injection.", GREEN)
        else:
            self.term.write_banner(
                f"Injection test failed (exit {code}) — "
                f"card does not support injection or interface is not in monitor mode.", RED
            )

    def _start_ids(self):
        if not tool_ok("kismet"):
            QMessageBox.warning(self, "Not found", "kismet is not installed.\nsudo apt install kismet"); return
        iface = self.ids_iface_edit.text().strip() or "wlan0mon"
        # --no-logging avoids the fatal startup error caused by missing log dirs
        # --no-ncurses outputs plain text to the pipe instead of a TUI
        cmd = ["kismet", "-c", iface, "--no-logging", "--no-ncurses"]
        self.term.write(f"[GUI] Starting Kismet IDS on {iface}...\n")
        self.term.write("[GUI] Logging disabled — alerts will appear here and at localhost:2501\n")
        self.term.write("[GUI] Watch for: DEAUTHFLOOD  APSPOOF  DISASSOCFLOOD  BCASTDISCON\n\n")
        if self._ids_runner and self._ids_runner.isRunning():
            self._ids_runner.stop()
        self._ids_runner = CommandRunner(cmd, use_sudo=True)
        self._ids_runner.output.connect(self._handle_ids_line)
        self._ids_runner.error.connect(self.term.write_error)
        self._ids_runner.finished.connect(
            lambda c: self.term.write_banner(f"Kismet IDS stopped (exit {c})", YELLOW)
        )
        self._ids_runner.start()

    def _stop_ids(self):
        if self._ids_runner and self._ids_runner.isRunning():
            self._ids_runner.stop()

    def _handle_ids_line(self, line):
        self.term.write(line)
        # Highlight known alert keywords
        alerts = ["DEAUTHFLOOD", "DISASSOCFLOOD", "APSPOOF", "BCASTDISCON", "ALERT"]
        for kw in alerts:
            if kw in line.upper():
                self.term.write_banner(f"IDS ALERT DETECTED: {line.strip()}", RED)
                break
        if "Kismet starting" in line or "Starting Kismet" in line:
            self.term.write_banner("Kismet IDS is running — monitoring for attacks", GREEN)


# ══════════════════════════════════════════════════════════════════════════════
# Legal panel
# ══════════════════════════════════════════════════════════════════════════════

class LegalPanel(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background: {BG}; }}")

        content = QWidget()
        cv = QVBoxLayout(content)
        cv.setContentsMargins(32, 28, 32, 32)
        cv.setSpacing(20)

        # Title
        title = QLabel("⚖  Legal Considerations")
        title.setStyleSheet(f"color:{TEXT}; font-size:20px; font-weight:bold;")
        cv.addWidget(title)

        warning_box = QWidget()
        warning_box.setStyleSheet(
            f"background:{RED}18; border:1px solid {RED}55; border-radius:8px; padding:4px;"
        )
        wv = QVBoxLayout(warning_box)
        wv.setContentsMargins(16, 12, 16, 12)
        wl = QLabel(
            "⚠  This tool is provided strictly for educational purposes and authorised security testing. "
            "Using it against any network, device, or system without explicit written permission "
            "from the owner is illegal in most jurisdictions and may result in criminal prosecution, "
            "civil liability, and significant fines or imprisonment."
        )
        wl.setWordWrap(True)
        wl.setStyleSheet(f"color:{RED}; font-weight:bold; font-size:12px;")
        wv.addWidget(wl)
        cv.addWidget(warning_box)

        cv.addWidget(separator())

        sections = [
            (
                "🇪🇺  European Union — NIS2 Directive & Computer Misuse Laws",
                f"""The EU Directive on Network and Information Security (NIS2, 2022/2555) and national implementations 
across member states criminalise unauthorised access to computer systems and networks. 
In Romania specifically, Law 161/2003 (Title III) and the Criminal Code (Art. 360–365) 
cover unauthorised access to computer systems, interception of computer transmissions, 
and disruption of computer systems.

Relevant offences under Romanian law:
  •  Art. 360 — Unauthorised access to a computer system: up to 3 years imprisonment.
  •  Art. 361 — Intercepting a computer transmission without right: up to 2 years.
  •  Art. 362 — Altering computer data without right: up to 7 years.
  •  Art. 364 — Disrupting a computer system (e.g. deauth flooding): up to 7 years.

Capturing WiFi handshakes from networks you do not own constitutes interception of 
a computer transmission under Art. 361 regardless of whether the data is decrypted.""",
                ACCENT
            ),
            (
                "🇺🇸  United States — Computer Fraud and Abuse Act (CFAA)",
                f"""The Computer Fraud and Abuse Act (18 U.S.C. § 1030) prohibits intentionally 
accessing a computer or network without authorisation or in excess of authorised access. 
WiFi interception may also fall under the Electronic Communications Privacy Act (ECPA, 
18 U.S.C. § 2511) which prohibits intentional interception of electronic communications.

Key provisions:
  •  § 1030(a)(2) — Unauthorised access to obtain information: up to 1 year (first offence).
  •  § 1030(a)(5) — Knowingly causing damage to a protected computer: up to 10 years.
  •  § 2511 ECPA  — Intercepting electronic communications: up to 5 years.

Even passive capture (airodump-ng with no deauth) of frames from a network you 
do not own may constitute a violation of the ECPA.""",
                ACCENT
            ),
            (
                "🌍  General Principle — Authorisation is Everything",
                f"""Regardless of jurisdiction, the legal boundary is consistent: 
explicit written authorisation from the network owner before any testing begins.

A proper authorisation should include:
  •  The specific network(s) and IP/MAC ranges in scope
  •  The time window during which testing is permitted
  •  The specific techniques permitted (passive scan, deauth, cracking etc.)
  •  Contact information for the authorising party
  •  A statement that the tester is not liable for authorised findings

Verbal permission is not sufficient. A signed document or email chain 
from the network owner protects both parties.""",
                GREEN
            ),
            (
                "✅  Authorised Use Cases",
                f"""This tool is appropriate for:

  •  Your own home network (you own the router)
  •  A dedicated lab network set up for the purpose of testing
  •  A penetration test engagement with a signed scope-of-work document
  •  A CTF or school contest on the designated contest network only
  •  Academic research under an institutional ethics review board approval

In all cases, document your authorisation before you begin.""",
                GREEN
            ),
        ]

        for heading, body, color in sections:
            box = QWidget()
            box.setStyleSheet(
                f"background:{color}0d; border-left:3px solid {color}; "
                f"border-radius:0px 6px 6px 0px; padding:2px;"
            )
            bv = QVBoxLayout(box)
            bv.setContentsMargins(14, 10, 14, 12)
            bv.setSpacing(8)
            h = QLabel(heading)
            h.setStyleSheet(f"color:{color}; font-weight:bold; font-size:13px;")
            bv.addWidget(h)
            b = QLabel(body)
            b.setWordWrap(True)
            b.setStyleSheet(f"color:{TEXT2}; font-size:12px; line-height:1.5;")
            b.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            bv.addWidget(b)
            cv.addWidget(box)

        # Acknowledgement checkbox
        cv.addWidget(separator())
        ack_row = QHBoxLayout()
        self.ack_check = QCheckBox(
            "I confirm I have explicit written authorisation to test the target network "
            "and I understand the legal consequences of unauthorised use."
        )
        self.ack_check.setStyleSheet(f"color:{TEXT}; font-size:12px;")
        self.ack_check.stateChanged.connect(self._on_ack)
        ack_row.addWidget(self.ack_check)
        cv.addLayout(ack_row)

        self.ack_label = QLabel("")
        self.ack_label.setStyleSheet(f"color:{GREEN}; font-weight:bold; font-size:12px;")
        cv.addWidget(self.ack_label)

        cv.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _on_ack(self, state):
        if state == 2:
            self.ack_label.setText("✓  Acknowledged. Proceed responsibly.")
        else:
            self.ack_label.setText("")


# ══════════════════════════════════════════════════════════════════════════════
# Main window
# ══════════════════════════════════════════════════════════════════════════════

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WiFi Toolkit")
        self.resize(1100, 720)
        self.setMinimumSize(800, 540)

        root = QWidget()
        rl = QHBoxLayout(root)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)

        # Sidebar
        sidebar = QWidget()
        sidebar.setFixedWidth(190)
        sidebar.setStyleSheet(f"background:{BG2}; border-right:1px solid {BORDER};")
        sv = QVBoxLayout(sidebar)
        sv.setContentsMargins(0, 0, 0, 0)
        sv.setSpacing(0)

        logo = QLabel("  📡  WiFi Toolkit")
        logo.setFixedHeight(52)
        logo.setStyleSheet(
            f"color:{TEXT}; font-size:14px; font-weight:bold;"
            f"border-bottom:1px solid {BORDER}; padding-left:8px;"
        )
        sv.addWidget(logo)

        self.stack = QStackedWidget()
        self._btns = []

        for icon, label, panel in [
            ("🏠", "Dashboard",    DashboardPanel()),
            ("📡", "airmon-ng",    AirmonPanel()),
            ("🔍", "airodump-ng",  AirodumpPanel()),
            ("💥", "aireplay-ng",  AireplayPanel()),
            ("🔑", "aircrack-ng",  AircrackPanel()),
            ("🗺", "kismet",       KismetPanel()),
            ("🛡", "Hardening",    HardeningPanel()),
            ("⚖",  "Legal",        LegalPanel()),
        ]:
            idx = self.stack.count()
            btn = NavButton(icon, label)
            btn.clicked.connect(lambda _, i=idx: self._switch(i))
            sv.addWidget(btn)
            self._btns.append(btn)
            self.stack.addWidget(panel)

        sv.addStretch()

        # Tool status at bottom of sidebar
        sv.addWidget(separator())
        for tool in ("airmon-ng", "airodump-ng", "aireplay-ng", "aircrack-ng", "kismet"):
            ok = tool_ok(tool)
            dot = QLabel(f"  {'●' if ok else '○'}  {tool}")
            dot.setStyleSheet(f"color:{'#3fb950' if ok else '#f85149'}; font-size:11px; padding:2px 0;")
            sv.addWidget(dot)
        sv.addSpacing(10)

        rl.addWidget(sidebar)
        rl.addWidget(self.stack, stretch=1)
        self.setCentralWidget(root)

        status = QStatusBar()
        status.showMessage("Select a tool from the sidebar.  Each panel explains what the tool does and why.")
        self.setStatusBar(status)

        self._switch(0)

    def _switch(self, i):
        self.stack.setCurrentIndex(i)
        for j, b in enumerate(self._btns):
            b.setChecked(j == i)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(DARK_STYLE)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
