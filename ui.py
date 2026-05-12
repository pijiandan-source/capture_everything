from __future__ import annotations

import os
import ctypes
from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QMenu,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app_settings import DEFAULT_SETTINGS, load_settings, reset_settings, save_settings, settings_path
from copy_formatter import as_json, basic_text, exe_text, full_text, reg_text
from models import ExeCandidate, GameInfo, RegistryCandidate
from path_wildcard_converter import PathConvertContext, convert_multiline
from windows_paths import clean_display_path, normalize_registry_path
from windows_shell import open_properties as shell_open_properties, open_registry_path as shell_open_registry_path, open_regedit_as_admin


class DropLabel(QLabel):
    fileDropped = Signal(str)

    def __init__(self):
        super().__init__("Drop .url / .lnk / exe / game folder here")
        self.setAcceptDrops(True)
        self.setFrameShape(QFrame.StyledPanel)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumHeight(54)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        urls = e.mimeData().urls()
        if urls:
            self.fileDropped.emit(urls[0].toLocalFile())


class MainWindow(QMainWindow):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setWindowTitle("SteamGameInfoCollector")
        self.resize(1280, 860)
        self.fields: dict[str, QLineEdit] = {}
        self.basic_groups: dict[str, QGroupBox] = {}
        self.settings = load_settings(controller.logger)
        self.settings_checks: dict[str, QCheckBox] = {}
        self.game = GameInfo()

        w = QWidget()
        self.setCentralWidget(w)
        root = QVBoxLayout(w)
        root.addWidget(self._build_input_area())

        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)
        self.tabs.addTab(self._build_basic_tab(), "Basic")
        self.tabs.addTab(self._build_exe_tab(), "EXE Candidates")
        self.tabs.addTab(self._build_registry_tab(), "Registry Candidates")
        self.tabs.addTab(self._build_path_tab(), "Path Wildcards")
        self.tabs.addTab(self._build_log_tab(), "Log")
        self.tabs.addTab(self._build_settings_tab(), "Settings")
        root.addLayout(self._build_copy_bar())
        self.apply_basic_visibility()
        self._log_admin_status()

    def _build_input_area(self) -> QWidget:
        box = QGroupBox("Input")
        layout = QGridLayout(box)
        self.drop = DropLabel()
        self.drop.fileDropped.connect(self.controller.analyze_path)
        layout.addWidget(self.drop, 0, 0, 2, 1)

        self.appid_input = QLineEdit()
        self.appid_input.setPlaceholderText("Steam AppID")
        appid_btn = QPushButton("Analyze")
        appid_btn.clicked.connect(lambda: self.controller.analyze_appid(self.appid_input.text().strip()))
        layout.addWidget(self.appid_input, 0, 1)
        layout.addWidget(appid_btn, 0, 2)

        self.registry_keyword = QLineEdit()
        self.registry_keyword.setPlaceholderText("Game name keyword")
        reg_btn = QPushButton("Search Registry")
        reg_btn.clicked.connect(lambda: self.controller.search_registry(self.registry_keyword.text().strip()))
        layout.addWidget(self.registry_keyword, 1, 1)
        layout.addWidget(reg_btn, 1, 2)

        self.path_input_line = QLineEdit()
        self.path_input_line.setPlaceholderText("Paste shortcut / exe / folder path")
        analyze_path_btn = QPushButton("Analyze Path")
        analyze_path_btn.clicked.connect(lambda: self.controller.analyze_path(self.path_input_line.text().strip().strip('"')))
        layout.addWidget(self.path_input_line, 2, 1)
        layout.addWidget(analyze_path_btn, 2, 2)

        file_btn = QPushButton("Choose File")
        file_btn.clicked.connect(self.choose_file)
        dir_btn = QPushButton("Choose Folder")
        dir_btn.clicked.connect(self.choose_folder)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_all)
        self.debug_check = QCheckBox("Enable detailed Debug log")
        self.debug_check.toggled.connect(self.controller.set_debug)
        self.log_all_registry_check = QCheckBox("Log all registry candidates")
        layout.addWidget(file_btn, 0, 3)
        layout.addWidget(dir_btn, 1, 3)
        layout.addWidget(clear_btn, 0, 4)
        layout.addWidget(self.debug_check, 1, 4)
        layout.addWidget(self.log_all_registry_check, 0, 5)
        layout.addWidget(QLabel("If drag-and-drop fails under admin, use Choose File / Choose Folder / Paste Path."), 2, 3, 1, 3)
        return box

    def _build_basic_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        page = QWidget()
        layout = QVBoxLayout(page)
        groups = [
            ("steam", "Steam", [
                ("game_name", "Game Name"),
                ("steam_appid", "Steam AppID"),
                ("steam_url", "Steam URL"),
            ]),
            ("shortcut", "Shortcut", [
                ("shortcut_name", "Shortcut Name"),
                ("shortcut_type", "Shortcut Type"),
                ("shortcut_path", "Shortcut Path"),
                ("shortcut_icon_path", "Shortcut Icon Path"),
                ("shortcut_icon_index", "Shortcut Icon Index"),
            ]),
            ("game_paths", "Game Paths", [("install_dir", "Game Install Dir")]),
            ("main_exe", "Main EXE", [("main_exe_path", "Main EXE Path"), ("process_name", "Process Name")]),
            ("exe_metadata", "EXE Metadata", [
                ("exe_company", "CompanyName"),
                ("exe_product", "ProductName"),
                ("exe_desc", "FileDescription"),
                ("exe_file_version", "FileVersion"),
                ("exe_product_version", "ProductVersion"),
                ("exe_original", "OriginalFilename"),
                ("exe_internal", "InternalName"),
                ("exe_copyright", "LegalCopyright"),
            ]),
            ("signature", "Digital Signature", [
                ("exe_sig_status", "Digital Signature Status"),
                ("exe_sig_subject", "Digital Signature Subject"),
                ("exe_sig_issuer", "Digital Signature Issuer"),
                ("exe_sig_subject_simple", "Digital Signature Subject Simple"),
                ("exe_sig_issuer_simple", "Digital Signature Issuer Simple"),
                ("exe_sig_subject_raw", "Digital Signature Subject Raw"),
                ("exe_sig_issuer_raw", "Digital Signature Issuer Raw"),
                ("exe_sig_raw_status", "Digital Signature Raw Status"),
                ("exe_sig_message", "Digital Signature Status Message"),
            ]),
            ("registry", "Registry", [
                ("reg_name", "DisplayName"),
                ("reg_install", "InstallLocation"),
                ("reg_pub", "Publisher"),
                ("reg_icon", "DisplayIcon"),
                ("reg_uninstall", "UninstallString"),
                ("reg_key", "Registry Key"),
            ]),
        ]
        for key, title, fields in groups:
            group = self._field_group(title, fields)
            self.basic_groups[key] = group
            layout.addWidget(group)
        layout.addStretch(1)
        scroll.setWidget(page)
        return scroll

    def _field_group(self, title: str, items: list[tuple[str, str]]) -> QGroupBox:
        box = QGroupBox(title)
        form = QFormLayout(box)
        for key, label in items:
            le = QLineEdit()
            self.fields[key] = le
            row = QHBoxLayout()
            row.addWidget(le, 1)
            copy = QPushButton("Copy")
            copy.clicked.connect(lambda _, k=key: self.copy_field(k))
            row.addWidget(copy)
            if key in {"install_dir", "main_exe_path", "reg_install", "reg_icon", "shortcut_path", "shortcut_icon_path"}:
                open_btn = QPushButton("Open")
                if key == "shortcut_icon_path":
                    open_btn.clicked.connect(lambda _, k=key: self.open_optional_path(self.fields[k].text()))
                else:
                    open_btn.clicked.connect(lambda _, k=key: self.open_path(self.fields[k].text()))
                row.addWidget(open_btn)
                folder_btn = QPushButton("Folder")
                if key == "shortcut_icon_path":
                    folder_btn.clicked.connect(lambda _, k=key: self.open_optional_containing_folder(self.fields[k].text()))
                else:
                    folder_btn.clicked.connect(lambda _, k=key: self.open_containing_folder(self.fields[k].text()))
                row.addWidget(folder_btn)
            if key == "main_exe_path":
                prop_btn = QPushButton("Properties")
                prop_btn.clicked.connect(lambda: self.open_properties(self.fields["main_exe_path"].text()))
                row.addWidget(prop_btn)
            if key == "reg_key":
                reg_btn = QPushButton("Open Registry")
                reg_btn.clicked.connect(lambda: self.open_registry(self.fields["reg_key"].text()))
                row.addWidget(reg_btn)
            wrap = QWidget()
            wrap.setLayout(row)
            form.addRow(label, wrap)
        return box

    def _build_exe_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.exe_table = QTableWidget(0, 18)
        self.exe_table.setHorizontalHeaderLabels(["Recommended", "Score", "Category", "File", "Path", "Size", "CompanyName", "ProductName", "FileDescription", "Signature Status", "Signature Subject", "Signature Issuer", "Subject Raw", "Issuer Raw", "Signature Raw Status", "Signature Message", "Reasons", "Actions"])
        self.exe_column_policy = {
            0: (70, 55, 90),
            1: (60, 45, 80),
            2: (110, 80, 160),
            3: (180, 120, 260),
            4: (420, 260, 650),
            5: (100, 80, 140),
            6: (220, 120, 320),
            7: (200, 120, 300),
            8: (220, 120, 340),
            9: (120, 100, 170),
            10: (260, 140, 480),
            11: (260, 140, 480),
            12: (320, 180, 600),
            13: (320, 180, 600),
            14: (140, 100, 190),
            15: (260, 140, 520),
            16: (320, 180, 600),
            17: (420, 320, 520),
        }
        self._apply_table_column_policy(self.exe_table, self.exe_column_policy)
        self.exe_table.itemDoubleClicked.connect(self.copy_table_item)
        self.exe_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.exe_table.customContextMenuRequested.connect(self.show_exe_context_menu)
        layout.addWidget(self.exe_table)
        return page

    def _build_registry_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.registry_table = QTableWidget(0, 9)
        self.registry_table.setHorizontalHeaderLabels(["Recommended", "Score", "DisplayName", "InstallLocation", "Publisher", "DisplayIcon", "UninstallString", "RegistryKey", "Reasons"])
        self.registry_column_policy = {
            0: (70, 55, 90),
            1: (60, 45, 80),
            2: (220, 120, 340),
            3: (360, 220, 600),
            4: (220, 120, 340),
            5: (360, 220, 600),
            6: (420, 240, 700),
            7: (420, 240, 700),
            8: (300, 160, 500),
        }
        self._apply_table_column_policy(self.registry_table, self.registry_column_policy)
        self.registry_table.itemDoubleClicked.connect(self.copy_table_item)
        self.registry_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.registry_table.customContextMenuRequested.connect(self.show_registry_context_menu)
        layout.addWidget(self.registry_table)
        return page

    def _apply_table_column_policy(self, table: QTableWidget, policy: dict[int, tuple[int, int, int]]):
        """
        policy: col -> (default_width, min_width, max_width)
        """
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(False)
        for col, (default_width, min_width, max_width) in policy.items():
            header.setMinimumSectionSize(min(header.minimumSectionSize(), min_width))
            table.setColumnWidth(col, default_width)

    def _clamp_table_columns(self, table: QTableWidget, policy: dict[int, tuple[int, int, int]]):
        table.resizeColumnsToContents()
        for col, (default_width, min_width, max_width) in policy.items():
            current = table.columnWidth(col)
            if current <= 0:
                current = default_width
            table.setColumnWidth(col, max(min_width, min(current, max_width)))

    def _build_path_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        form = QFormLayout()
        self.steam_install = QLineEdit()
        self.platform_install = QLineEdit()
        self.steam_install.setPlaceholderText("Steam install path")
        self.platform_install.setPlaceholderText("Optional platform install path, defaults to Steam install")
        form.addRow("Steam Install", self.steam_install)
        form.addRow("Platform Install", self.platform_install)
        layout.addLayout(form)
        layout.addWidget(QLabel("Local path input"))
        self.path_input = QPlainTextEdit()
        layout.addWidget(self.path_input, 1)
        btns = QHBoxLayout()
        for text, fn in [("Convert", self.convert_paths), ("Copy Result", self.copy_path_result), ("Copy All", self.copy_path_all), ("Export Result", self.export_path_result), ("Clear", self.clear_path_converter)]:
            b = QPushButton(text)
            b.clicked.connect(fn)
            btns.addWidget(b)
        layout.addLayout(btns)
        layout.addWidget(QLabel("Converted result (editable)"))
        self.path_output = QPlainTextEdit()
        layout.addWidget(self.path_output, 1)
        return page

    def _build_log_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        btns = QHBoxLayout()
        for text, fn in [("Copy Log", self.copy_log), ("Save Log", self.save_log), ("Clear Log", self.clear_log)]:
            b = QPushButton(text)
            b.clicked.connect(fn)
            btns.addWidget(b)
        btns.addStretch(1)
        layout.addLayout(btns)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)
        return page

    def _build_settings_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        info = QLabel("Basic visibility settings only affect what is shown in the Basic tab. Copy Full and JSON still include all collected data.")
        info.setWordWrap(True)
        layout.addWidget(info)
        box = QGroupBox("Basic Sections")
        form = QFormLayout(box)
        labels = {
            "steam": "Show Steam info",
            "shortcut": "Show shortcut info",
            "game_paths": "Show game path info",
            "main_exe": "Show main EXE info",
            "exe_metadata": "Show EXE metadata",
            "signature": "Show digital signature info",
            "registry": "Show registry info",
        }
        visibility = self.settings.setdefault("basic_visibility", DEFAULT_SETTINGS["basic_visibility"].copy())
        for key, label in labels.items():
            cb = QCheckBox(label)
            cb.setChecked(bool(visibility.get(key, True)))
            cb.toggled.connect(lambda checked, k=key: self.on_basic_visibility_changed(k, checked))
            self.settings_checks[key] = cb
            form.addRow(cb)
        layout.addWidget(box)
        btns = QHBoxLayout()
        reset_btn = QPushButton("Restore Defaults")
        reset_btn.clicked.connect(self.restore_default_settings)
        open_dir_btn = QPushButton("Open Settings Folder")
        open_dir_btn.clicked.connect(self.open_settings_folder)
        btns.addWidget(reset_btn)
        btns.addWidget(open_dir_btn)
        btns.addStretch(1)
        layout.addLayout(btns)
        layout.addStretch(1)
        return page

    def on_basic_visibility_changed(self, key: str, checked: bool):
        self.settings.setdefault("basic_visibility", {})[key] = checked
        save_settings(self.settings, self.controller.logger)
        self.apply_basic_visibility()

    def apply_basic_visibility(self):
        visibility = self.settings.get("basic_visibility", {})
        for key, group in self.basic_groups.items():
            group.setVisible(bool(visibility.get(key, True)))

    def restore_default_settings(self):
        self.settings = reset_settings(self.controller.logger)
        for key, cb in self.settings_checks.items():
            cb.blockSignals(True)
            cb.setChecked(bool(self.settings["basic_visibility"].get(key, True)))
            cb.blockSignals(False)
        self.apply_basic_visibility()
        self.statusBar().showMessage("Settings restored", 1500)

    def open_settings_folder(self):
        settings_path().parent.mkdir(parents=True, exist_ok=True)
        self.open_path(str(settings_path().parent))

    def _is_admin(self) -> bool:
        if os.name != "nt":
            return False
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False

    def _log_admin_status(self):
        is_admin = self._is_admin()
        self.controller.logger.info("Privilege", f"Process admin={is_admin}")
        if is_admin:
            message = "This tool is running as administrator. Drag-and-drop from normal Explorer may not work; use Choose File / Choose Folder / Paste Path."
            self.controller.logger.warning("Privilege", message)
            self.statusBar().showMessage(message, 8000)

    def _build_copy_bar(self) -> QHBoxLayout:
        h = QHBoxLayout()
        for text, fn in [
            ("Copy Basic", lambda: basic_text(self.current_game())),
            ("Copy EXE", lambda: exe_text(self.current_game())),
            ("Copy Registry", lambda: reg_text(self.current_game())),
            ("Copy Full", lambda: full_text(self.current_game())),
            ("Copy JSON", lambda: as_json(self.current_game())),
        ]:
            b = QPushButton(text)
            b.clicked.connect(lambda _, f=fn: self.copy_text(f()))
            h.addWidget(b)
        h.addStretch(1)
        return h

    def choose_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose File", "", "Supported (*.url *.lnk *.exe);;All files (*.*)")
        if path:
            self.controller.analyze_path(path)

    def choose_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Choose Folder")
        if path:
            self.controller.analyze_path(path)

    def append_log(self, line: str):
        self.log.appendPlainText(line)

    def copy_text(self, text: str, message: str = "Copied", allow_empty: bool = False):
        text = "" if text is None else str(text)
        if not allow_empty and not text.strip():
            QMessageBox.information(self, "Info", "Nothing to copy")
            return
        QApplication.clipboard().setText(text)
        self.statusBar().showMessage(message, 1500)

    def copy_field(self, key: str):
        text = self.fields[key].text()
        if key == "reg_key":
            text = normalize_registry_path(text, self.controller.logger)
        self.copy_text(text)

    def copy_log(self):
        self.copy_text(self.log.toPlainText())

    def save_log(self):
        name = f"SteamGameInfoCollector_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        path, _ = QFileDialog.getSaveFileName(self, "Save Log", name, "Log files (*.log);;Text files (*.txt);;All files (*.*)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.log.toPlainText())
            self.statusBar().showMessage(f"Log saved: {path}", 3000)

    def clear_log(self):
        self.log.clear()
        self.controller.logger.clear()

    def clear_all(self):
        self.game = GameInfo()
        for field in self.fields.values():
            field.clear()
        self.exe_table.setRowCount(0)
        self.registry_table.setRowCount(0)

    def open_path(self, path: str):
        path = self._clean_display_path(path)
        self.controller.logger.debug("GUI", f"Button=Open path={path} empty={not bool(path)} exists={os.path.exists(path) if path else False}")
        if not path:
            return
        try:
            os.startfile(path)
        except Exception as exc:
            self.controller.logger.exception("Shell", f"Open failed: {path}", exc)
            QMessageBox.warning(self, "Open failed", str(exc))

    def open_optional_path(self, path: str):
        path = self._clean_display_path(path)
        exists = os.path.exists(path) if path else False
        self.controller.logger.debug("GUI", f"Button=Open optional path={path} empty={not bool(path)} exists={exists}")
        if not path or not exists:
            self.statusBar().showMessage("Path does not exist; kept for reference only", 2500)
            return
        self.open_path(path)

    def open_containing_folder(self, path: str):
        path = self._clean_display_path(path)
        self.controller.logger.debug("GUI", f"Button=Folder path={path} empty={not bool(path)} exists={os.path.exists(path) if path else False}")
        if os.path.isfile(path):
            path = os.path.dirname(path)
        self.open_path(path)

    def open_optional_containing_folder(self, path: str):
        path = self._clean_display_path(path)
        exists = os.path.exists(path) if path else False
        self.controller.logger.debug("GUI", f"Button=Folder optional path={path} empty={not bool(path)} exists={exists}")
        if not path or not exists:
            self.statusBar().showMessage("Path does not exist; kept for reference only", 2500)
            return
        self.open_containing_folder(path)

    def open_properties(self, path: str):
        path = self._clean_display_path(path)
        self.controller.logger.debug("GUI", f"Button=Properties path={path} empty={not bool(path)} exists={os.path.exists(path) if path else False}")
        if not path:
            return
        ok = shell_open_properties(path, self.controller.logger)
        if not ok:
            self.statusBar().showMessage("Properties dialog failed; selected file in Explorer", 3000)

    def open_registry(self, path: str):
        if not path.strip():
            QMessageBox.information(self, "Info", "No registry path to open.")
            return
        result = shell_open_registry_path(path, self.controller.logger)
        if result.ok:
            self.statusBar().showMessage("Registry opened", 2000)
        elif result.needs_elevation:
            self.handle_registry_elevation_required(result.normalized_path)
        else:
            QMessageBox.warning(self, "Open registry failed", result.message or "Failed to open registry path.")

    def handle_registry_elevation_required(self, registry_path: str):
        self.controller.logger.info("RegistryShell", "Prompt user to run regedit as admin")
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle("Administrator permission required")
        box.setText("Opening regedit requires administrator privileges.")
        box.setInformativeText("You can run regedit as administrator, copy the registry path, or cancel. Do not run the whole tool as administrator unless necessary; admin mode may block drag-and-drop from normal Explorer.")
        copy_btn = box.addButton("Copy Registry Path", QMessageBox.ActionRole)
        admin_btn = box.addButton("Run regedit as Admin", QMessageBox.AcceptRole)
        box.addButton(QMessageBox.Cancel)
        box.exec()
        clicked = box.clickedButton()
        if clicked == copy_btn:
            self.copy_text(registry_path, "Registry path copied", allow_empty=True)
        elif clicked == admin_btn:
            ok, message = open_regedit_as_admin(self.controller.logger)
            if ok:
                self.statusBar().showMessage("UAC prompt opened for regedit", 2500)
            else:
                QMessageBox.warning(self, "Open regedit as admin failed", message or "Failed to start elevated regedit.")

    def _clean_display_path(self, path: str) -> str:
        return clean_display_path(path)

    def set_game_info(self, g: GameInfo):
        self.game = g
        values = {
            "game_name": g.game_name,
            "steam_appid": g.steam_appid,
            "steam_url": g.steam_url,
            "shortcut_name": g.shortcut_name,
            "shortcut_type": g.shortcut_type,
            "shortcut_path": g.shortcut_path,
            "shortcut_icon_path": g.shortcut_icon_path,
            "shortcut_icon_index": g.shortcut_icon_index,
            "install_dir": g.install_dir,
            "main_exe_path": g.main_exe_path,
            "process_name": g.process_name,
            "exe_company": g.exe_info.company_name,
            "exe_product": g.exe_info.product_name,
            "exe_desc": g.exe_info.file_description,
            "exe_file_version": g.exe_info.file_version,
            "exe_product_version": g.exe_info.product_version,
            "exe_original": g.exe_info.original_filename,
            "exe_internal": g.exe_info.internal_name,
            "exe_copyright": g.exe_info.legal_copyright,
            "exe_sig_status": g.exe_info.digital_signature_status,
            "exe_sig_subject": g.exe_info.digital_signature_subject,
            "exe_sig_issuer": g.exe_info.digital_signature_issuer,
            "exe_sig_subject_simple": g.exe_info.digital_signature_subject_simple,
            "exe_sig_issuer_simple": g.exe_info.digital_signature_issuer_simple,
            "exe_sig_subject_raw": g.exe_info.digital_signature_subject_raw,
            "exe_sig_issuer_raw": g.exe_info.digital_signature_issuer_raw,
            "exe_sig_raw_status": g.exe_info.digital_signature_raw_status,
            "exe_sig_message": g.exe_info.digital_signature_status_message,
            "reg_name": g.registry["display_name"],
            "reg_install": g.registry["install_location"],
            "reg_pub": g.registry["publisher"],
            "reg_icon": g.registry["display_icon"],
            "reg_uninstall": g.registry["uninstall_string"],
            "reg_key": normalize_registry_path(g.registry["key"], self.controller.logger),
        }
        for k, v in values.items():
            self.fields[k].setText(v or "")
        self.registry_keyword.setText(g.game_name or self.registry_keyword.text())
        self.appid_input.setText(g.steam_appid or self.appid_input.text())
        self._fill_exe_table(g.exe_candidates)
        self._fill_registry_table(g.registry_candidates)

    def _fill_exe_table(self, candidates: list[ExeCandidate]):
        self.exe_table.setRowCount(len(candidates))
        for row, c in enumerate(candidates):
            info = c.exe_info
            values = [
                "*" if c.path == self.game.main_exe_path else "",
                str(c.score),
                c.category,
                os.path.basename(c.path),
                c.path,
                self._fmt_size(c.size),
                info.company_name,
                info.product_name,
                info.file_description,
                info.digital_signature_status,
                info.digital_signature_subject,
                info.digital_signature_issuer,
                info.digital_signature_subject_raw,
                info.digital_signature_issuer_raw,
                info.digital_signature_raw_status,
                info.digital_signature_status_message,
                ", ".join(c.reasons),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value or "")
                item.setToolTip(value or "")
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.exe_table.setItem(row, col, item)
            actions = QWidget()
            h = QHBoxLayout(actions)
            h.setContentsMargins(0, 0, 0, 0)
            actions_spec = [
                ("Copy Path", lambda cand=c, r=row: self.copy_exe_path(cand.path)),
                ("Copy Info", lambda cand=c, r=row: self.copy_exe_info(cand, r)),
                ("Details", lambda cand=c, r=row: self.show_exe_details(cand, r)),
                ("Set Main", lambda cand=c, r=row: self.set_main_exe(cand, r)),
                ("Folder", lambda cand=c, r=row: self.open_containing_folder(cand.path)),
                ("Properties", lambda cand=c, r=row: self.open_properties(cand.path)),
            ]
            for text, callback in actions_spec:
                b = QPushButton(text)
                b.clicked.connect(lambda _, cb=callback: cb())
                h.addWidget(b)
            self.exe_table.setCellWidget(row, 17, actions)
        self._clamp_table_columns(self.exe_table, self.exe_column_policy)

    def copy_exe_path(self, path: str):
        self.controller.logger.debug("GUI", f"Button=Copy Path path={path} empty={not bool(path)} exists={os.path.exists(path) if path else False}")
        self.copy_text(path)

    def copy_exe_info(self, candidate: ExeCandidate, row: int = -1):
        self.controller.logger.debug("GUI", f"Button=Copy EXE Info row={row} path={candidate.path} exists={os.path.exists(candidate.path)}")
        e = candidate.exe_info
        text = self.format_full_exe_info(candidate)
        self.copy_text(text)

    def show_exe_details(self, candidate: ExeCandidate, row: int = -1):
        self.controller.logger.debug("GUI", f"Button=Details row={row} path={candidate.path} exists={os.path.exists(candidate.path)}")
        e = candidate.exe_info
        text = (
            f"Path: {candidate.path}\n"
            f"Category: {candidate.category}\n"
            f"Score: {candidate.score}\n"
            f"CompanyName: {e.company_name}\n"
            f"ProductName: {e.product_name}\n"
            f"FileDescription: {e.file_description}\n"
            f"FileVersion: {e.file_version}\n"
            f"ProductVersion: {e.product_version}\n"
            f"OriginalFilename: {e.original_filename}\n"
            f"Digital Signature Status: {e.digital_signature_status}\n"
            f"Digital Signature Subject: {e.digital_signature_subject}\n"
            f"Digital Signature Issuer: {e.digital_signature_issuer}\n"
            f"Digital Signature Subject Simple: {e.digital_signature_subject_simple}\n"
            f"Digital Signature Issuer Simple: {e.digital_signature_issuer_simple}\n"
            f"Digital Signature Subject Raw: {e.digital_signature_subject_raw}\n"
            f"Digital Signature Issuer Raw: {e.digital_signature_issuer_raw}\n"
            f"Digital Signature Raw Status: {e.digital_signature_raw_status}\n"
            f"Digital Signature Status Message: {e.digital_signature_status_message}\n"
            f"Digital Signature Error: {e.digital_signature_error}"
        )
        QMessageBox.information(self, "EXE Details", text)

    def set_main_exe(self, candidate: ExeCandidate, row: int = -1):
        self.controller.logger.debug("GUI", f"Button=Set Main row={row} path={candidate.path} exists={os.path.exists(candidate.path)}")
        self.game.main_exe_path = candidate.path
        self.game.process_name = os.path.basename(candidate.path)
        self.game.exe_info = candidate.exe_info
        self.set_game_info(self.game)

    def _fill_registry_table(self, candidates: list[RegistryCandidate]):
        self.registry_table.setRowCount(len(candidates))
        for row, c in enumerate(candidates):
            vals = c.values
            values = [
                "*" if row == 0 else "",
                str(c.score),
                vals.get("DisplayName", ""),
                vals.get("InstallLocation", ""),
                vals.get("Publisher", ""),
                vals.get("DisplayIcon", ""),
                vals.get("UninstallString", ""),
                normalize_registry_path(c.key, self.controller.logger),
                ", ".join(c.reasons),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value or ""))
                item.setToolTip(str(value or ""))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.registry_table.setItem(row, col, item)
        self._clamp_table_columns(self.registry_table, self.registry_column_policy)

    def _fmt_size(self, size: int) -> str:
        if not size:
            return ""
        return f"{size / 1024 / 1024:.2f} MB"

    def copy_table_item(self, item: QTableWidgetItem | None):
        text = item.text() if item else ""
        self.copy_text(text, "已复制当前单元格", allow_empty=True)

    def _table_cell_text(self, table: QTableWidget, row: int, col: int) -> str:
        item = table.item(row, col)
        return item.text() if item else ""

    def _add_menu_action(self, menu: QMenu, title: str, callback):
        action = menu.addAction(title)
        action.triggered.connect(callback)

    def show_exe_context_menu(self, pos):
        row = self.exe_table.rowAt(pos.y())
        col = self.exe_table.columnAt(pos.x())
        if row < 0 or row >= len(self.game.exe_candidates):
            return
        candidate = self.game.exe_candidates[row]
        menu = QMenu(self)
        self._add_menu_action(menu, "复制当前单元格", lambda: self.copy_text(self._table_cell_text(self.exe_table, row, col), "已复制当前单元格", allow_empty=True))
        self._add_menu_action(menu, "复制当前行", lambda: self.copy_text(self.format_exe_row(candidate), "已复制当前行"))
        self._add_menu_action(menu, "复制 exe 路径", lambda: self.copy_text(candidate.path, "已复制 exe 路径", allow_empty=True))
        self._add_menu_action(menu, "复制 exe 文件名", lambda: self.copy_text(os.path.basename(candidate.path), "已复制 exe 文件名", allow_empty=True))
        self._add_menu_action(menu, "复制签名信息", lambda: self.copy_text(self.format_signature_info(candidate), "已复制签名信息", allow_empty=True))
        self._add_menu_action(menu, "复制完整 exe 信息", lambda: self.copy_text(self.format_full_exe_info(candidate), "已复制完整 exe 信息"))
        menu.addSeparator()
        self._add_menu_action(menu, "打开所在目录", lambda: self.open_containing_folder(candidate.path))
        self._add_menu_action(menu, "打开属性", lambda: self.open_properties(candidate.path))
        self._add_menu_action(menu, "选择为主 exe", lambda: self.set_main_exe(candidate, row))
        menu.exec(self.exe_table.viewport().mapToGlobal(pos))

    def show_registry_context_menu(self, pos):
        row = self.registry_table.rowAt(pos.y())
        col = self.registry_table.columnAt(pos.x())
        if row < 0 or row >= len(self.game.registry_candidates):
            return
        candidate = self.game.registry_candidates[row]
        vals = candidate.values
        menu = QMenu(self)
        self._add_menu_action(menu, "复制当前单元格", lambda: self.copy_text(self._table_cell_text(self.registry_table, row, col), "已复制当前单元格", allow_empty=True))
        self._add_menu_action(menu, "复制当前行", lambda: self.copy_text(self.format_registry_info(candidate), "已复制当前行"))
        self._add_menu_action(menu, "复制 DisplayName", lambda: self.copy_text(vals.get("DisplayName", ""), "已复制 DisplayName", allow_empty=True))
        self._add_menu_action(menu, "复制 InstallLocation", lambda: self.copy_text(vals.get("InstallLocation", ""), "已复制 InstallLocation", allow_empty=True))
        self._add_menu_action(menu, "复制 Publisher", lambda: self.copy_text(vals.get("Publisher", ""), "已复制 Publisher", allow_empty=True))
        self._add_menu_action(menu, "复制 DisplayIcon", lambda: self.copy_text(vals.get("DisplayIcon", ""), "已复制 DisplayIcon", allow_empty=True))
        self._add_menu_action(menu, "复制 UninstallString", lambda: self.copy_text(vals.get("UninstallString", ""), "已复制 UninstallString", allow_empty=True))
        self._add_menu_action(menu, "复制注册表路径", lambda: self.copy_text(normalize_registry_path(candidate.key, self.controller.logger), "已复制注册表路径", allow_empty=True))
        self._add_menu_action(menu, "复制完整注册表信息", lambda: self.copy_text(self.format_registry_info(candidate), "已复制完整注册表信息"))
        menu.addSeparator()
        self._add_menu_action(menu, "打开 InstallLocation", lambda: self.open_path(vals.get("InstallLocation", "")))
        self._add_menu_action(menu, "打开注册表", lambda: self.open_registry(candidate.key))
        self._add_menu_action(menu, "选择为当前注册表项", lambda: self.set_current_registry(candidate))
        menu.exec(self.registry_table.viewport().mapToGlobal(pos))

    def format_signature_info(self, candidate: ExeCandidate) -> str:
        e = candidate.exe_info
        return (
            f"数字签名状态: {e.digital_signature_status}\n"
            f"签名主体: {e.digital_signature_subject}\n"
            f"签名颁发者: {e.digital_signature_issuer}\n"
            f"SubjectSimple: {e.digital_signature_subject_simple}\n"
            f"IssuerSimple: {e.digital_signature_issuer_simple}\n"
            f"SubjectRaw: {e.digital_signature_subject_raw}\n"
            f"IssuerRaw: {e.digital_signature_issuer_raw}\n"
            f"签名原始状态: {e.digital_signature_raw_status}\n"
            f"签名状态说明: {e.digital_signature_status_message}"
        )

    def format_exe_row(self, candidate: ExeCandidate) -> str:
        e = candidate.exe_info
        return (
            f"文件名: {os.path.basename(candidate.path)}\n"
            f"路径: {candidate.path}\n"
            f"分类: {candidate.category}\n"
            f"文件大小: {candidate.size}\n"
            f"CompanyName: {e.company_name}\n"
            f"ProductName: {e.product_name}\n"
            f"FileDescription: {e.file_description}\n"
            f"FileVersion: {e.file_version}\n"
            f"ProductVersion: {e.product_version}\n"
            f"OriginalFilename: {e.original_filename}\n"
            f"{self.format_signature_info(candidate)}"
        )

    def format_full_exe_info(self, candidate: ExeCandidate) -> str:
        e = candidate.exe_info
        return (
            f"文件名: {os.path.basename(candidate.path)}\n"
            f"完整路径: {candidate.path}\n"
            f"相对路径: {candidate.relative_path}\n"
            f"文件大小: {candidate.size}\n"
            f"分类标签: {candidate.category}\n"
            f"CompanyName: {e.company_name}\n"
            f"ProductName: {e.product_name}\n"
            f"FileDescription: {e.file_description}\n"
            f"FileVersion: {e.file_version}\n"
            f"ProductVersion: {e.product_version}\n"
            f"OriginalFilename: {e.original_filename}\n"
            f"InternalName: {e.internal_name}\n"
            f"LegalCopyright: {e.legal_copyright}\n"
            f"{self.format_signature_info(candidate)}\n"
            f"评分: {candidate.score}\n"
            f"评分原因: {', '.join(candidate.reasons)}"
        )

    def format_registry_info(self, candidate: RegistryCandidate) -> str:
        vals = candidate.values
        return (
            f"DisplayName: {vals.get('DisplayName', '')}\n"
            f"InstallLocation: {vals.get('InstallLocation', '')}\n"
            f"Publisher: {vals.get('Publisher', '')}\n"
            f"DisplayIcon: {vals.get('DisplayIcon', '')}\n"
            f"UninstallString: {vals.get('UninstallString', '')}\n"
            f"RegistryKey: {normalize_registry_path(candidate.key, self.controller.logger)}\n"
            f"Score: {candidate.score}\n"
            f"Reasons: {', '.join(candidate.reasons)}"
        )

    def set_current_registry(self, candidate: RegistryCandidate):
        vals = candidate.values
        self.game.registry = {
            "display_name": vals.get("DisplayName", ""),
            "install_location": vals.get("InstallLocation", ""),
            "publisher": vals.get("Publisher", ""),
            "display_icon": vals.get("DisplayIcon", ""),
            "uninstall_string": vals.get("UninstallString", ""),
            "key": normalize_registry_path(candidate.key, self.controller.logger),
        }
        self.set_game_info(self.game)
        self.statusBar().showMessage("Registry candidate selected", 1500)

    def current_game(self) -> GameInfo:
        g = self.game
        for k in ["shortcut_name", "shortcut_type", "shortcut_path", "shortcut_icon_path", "shortcut_icon_index"]:
            setattr(g, k, self.fields[k].text())
        for k in ["game_name", "steam_appid", "steam_url", "install_dir", "main_exe_path", "process_name"]:
            setattr(g, k, self.fields[k].text())
        g.exe_info.company_name = self.fields["exe_company"].text()
        g.exe_info.product_name = self.fields["exe_product"].text()
        g.exe_info.file_description = self.fields["exe_desc"].text()
        g.exe_info.file_version = self.fields["exe_file_version"].text()
        g.exe_info.product_version = self.fields["exe_product_version"].text()
        g.exe_info.original_filename = self.fields["exe_original"].text()
        g.exe_info.internal_name = self.fields["exe_internal"].text()
        g.exe_info.legal_copyright = self.fields["exe_copyright"].text()
        g.exe_info.digital_signature_status = self.fields["exe_sig_status"].text()
        g.exe_info.digital_signature_subject = self.fields["exe_sig_subject"].text()
        g.exe_info.digital_signature_issuer = self.fields["exe_sig_issuer"].text()
        g.exe_info.digital_signature_subject_simple = self.fields["exe_sig_subject_simple"].text()
        g.exe_info.digital_signature_issuer_simple = self.fields["exe_sig_issuer_simple"].text()
        g.exe_info.digital_signature_subject_raw = self.fields["exe_sig_subject_raw"].text()
        g.exe_info.digital_signature_issuer_raw = self.fields["exe_sig_issuer_raw"].text()
        g.exe_info.digital_signature_raw_status = self.fields["exe_sig_raw_status"].text()
        g.exe_info.digital_signature_status_message = self.fields["exe_sig_message"].text()
        g.registry = {
            "display_name": self.fields["reg_name"].text(),
            "install_location": self.fields["reg_install"].text(),
            "publisher": self.fields["reg_pub"].text(),
            "display_icon": self.fields["reg_icon"].text(),
            "uninstall_string": self.fields["reg_uninstall"].text(),
            "key": normalize_registry_path(self.fields["reg_key"].text(), self.controller.logger),
        }
        return g

    def _path_context(self) -> PathConvertContext:
        return PathConvertContext(
            steam_install=self.steam_install.text().strip(),
            game_install=self.fields["install_dir"].text().strip(),
            platform_install=self.platform_install.text().strip(),
            steam_appid=self.fields["steam_appid"].text().strip(),
        )

    def convert_paths(self):
        results = convert_multiline(self.path_input.toPlainText(), self._path_context(), self.controller.logger)
        lines = []
        for r in results:
            if r.error:
                lines.append(f"{r.output or r.source} # {r.error}")
            else:
                lines.append(r.output)
        self.path_output.setPlainText("\n".join(lines))

    def copy_path_result(self):
        self.copy_text(self.path_output.toPlainText())

    def copy_path_all(self):
        self.copy_text(self.path_input.toPlainText() + "\n\n" + self.path_output.toPlainText())

    def export_path_result(self):
        name = f"SteamGameInfoCollector_paths_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        path, _ = QFileDialog.getSaveFileName(self, "Export Result", name, "Text files (*.txt);;All files (*.*)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.path_output.toPlainText())
            self.statusBar().showMessage(f"Result exported: {path}", 3000)

    def clear_path_converter(self):
        self.path_input.clear()
        self.path_output.clear()
