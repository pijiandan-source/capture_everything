from __future__ import annotations

import os
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
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from copy_formatter import as_json, basic_text, exe_text, full_text, reg_text
from models import ExeCandidate, GameInfo, RegistryCandidate
from path_wildcard_converter import PathConvertContext, convert_multiline
from windows_paths import clean_display_path, normalize_registry_path
from windows_shell import open_properties as shell_open_properties, open_registry_path as shell_open_registry_path


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
        root.addLayout(self._build_copy_bar())

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
        return box

    def _build_basic_tab(self) -> QWidget:
        page = QWidget()
        grid = QGridLayout(page)
        groups = [
            ("Steam", [("game_name", "Game Name"), ("steam_appid", "Steam AppID"), ("steam_url", "Steam URL")]),
            ("Paths", [("install_dir", "Game Install Dir"), ("main_exe_path", "Main EXE Path"), ("process_name", "Process Name")]),
            ("EXE Metadata", [
                ("exe_company", "CompanyName"),
                ("exe_product", "ProductName"),
                ("exe_desc", "FileDescription"),
                ("exe_file_version", "FileVersion"),
                ("exe_product_version", "ProductVersion"),
                ("exe_original", "OriginalFilename"),
                ("exe_sig_status", "Digital Signature Status"),
                ("exe_sig_subject", "Digital Signature Subject"),
                ("exe_sig_issuer", "Digital Signature Issuer"),
                ("exe_sig_raw_status", "Digital Signature Raw Status"),
                ("exe_sig_message", "Digital Signature Status Message"),
            ]),
            ("Registry", [
                ("reg_name", "DisplayName"),
                ("reg_install", "InstallLocation"),
                ("reg_pub", "Publisher"),
                ("reg_icon", "DisplayIcon"),
                ("reg_uninstall", "UninstallString"),
                ("reg_key", "Registry Key"),
            ]),
        ]
        for i, (title, fields) in enumerate(groups):
            grid.addWidget(self._field_group(title, fields), i // 2, i % 2)
        return page

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
            if key in {"install_dir", "main_exe_path", "reg_install", "reg_icon"}:
                open_btn = QPushButton("Open")
                open_btn.clicked.connect(lambda _, k=key: self.open_path(self.fields[k].text()))
                row.addWidget(open_btn)
                folder_btn = QPushButton("Folder")
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
        self.exe_table = QTableWidget(0, 16)
        self.exe_table.setHorizontalHeaderLabels(["Recommended", "Score", "Category", "File", "Path", "Size", "CompanyName", "ProductName", "FileDescription", "Signature Status", "Signature Subject", "Signature Issuer", "Signature Raw Status", "Signature Message", "Reasons", "Actions"])
        self.exe_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.exe_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
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
        self.registry_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.registry_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.registry_table.itemDoubleClicked.connect(self.copy_table_item)
        self.registry_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.registry_table.customContextMenuRequested.connect(self.show_registry_context_menu)
        layout.addWidget(self.registry_table)
        return page

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

    def open_containing_folder(self, path: str):
        path = self._clean_display_path(path)
        self.controller.logger.debug("GUI", f"Button=Folder path={path} empty={not bool(path)} exists={os.path.exists(path) if path else False}")
        if os.path.isfile(path):
            path = os.path.dirname(path)
        self.open_path(path)

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
            QMessageBox.information(self, "Info", "当前没有可打开的注册表路径")
            return
        ok, message = shell_open_registry_path(path, self.controller.logger)
        if ok:
            self.statusBar().showMessage("Registry opened", 2000)
        else:
            QMessageBox.warning(self, "Open registry failed", message or "注册表路径格式无法识别或无法打开")

    def _clean_display_path(self, path: str) -> str:
        return clean_display_path(path)

    def set_game_info(self, g: GameInfo):
        self.game = g
        values = {
            "game_name": g.game_name,
            "steam_appid": g.steam_appid,
            "steam_url": g.steam_url,
            "install_dir": g.install_dir,
            "main_exe_path": g.main_exe_path,
            "process_name": g.process_name,
            "exe_company": g.exe_info.company_name,
            "exe_product": g.exe_info.product_name,
            "exe_desc": g.exe_info.file_description,
            "exe_file_version": g.exe_info.file_version,
            "exe_product_version": g.exe_info.product_version,
            "exe_original": g.exe_info.original_filename,
            "exe_sig_status": g.exe_info.digital_signature_status,
            "exe_sig_subject": g.exe_info.digital_signature_subject,
            "exe_sig_issuer": g.exe_info.digital_signature_issuer,
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
                info.digital_signature_raw_status,
                info.digital_signature_status_message,
                ", ".join(c.reasons),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value or "")
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
            self.exe_table.setCellWidget(row, 15, actions)

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
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.registry_table.setItem(row, col, item)

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
        for k in ["game_name", "steam_appid", "steam_url", "install_dir", "main_exe_path", "process_name"]:
            setattr(g, k, self.fields[k].text())
        g.exe_info.company_name = self.fields["exe_company"].text()
        g.exe_info.product_name = self.fields["exe_product"].text()
        g.exe_info.file_description = self.fields["exe_desc"].text()
        g.exe_info.file_version = self.fields["exe_file_version"].text()
        g.exe_info.product_version = self.fields["exe_product_version"].text()
        g.exe_info.original_filename = self.fields["exe_original"].text()
        g.exe_info.digital_signature_status = self.fields["exe_sig_status"].text()
        g.exe_info.digital_signature_subject = self.fields["exe_sig_subject"].text()
        g.exe_info.digital_signature_issuer = self.fields["exe_sig_issuer"].text()
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
