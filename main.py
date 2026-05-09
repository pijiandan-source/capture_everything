from __future__ import annotations

import argparse
import json
import os

from PySide6.QtWidgets import QApplication

from debug_logger import DebugLogger
from exe_scanner import scan_exes
from models import GameInfo
from registry_finder import scan_registry
from shortcut_resolver import parse_input_file
from steam_resolver import resolve_appid
from ui import MainWindow


class Controller:
    def __init__(self, win):
        self.win = win
        self.logger = DebugLogger()

    def set_window(self, win):
        self.win = win
        self.logger.add_handler(win.append_log)

    def set_debug(self, enabled: bool):
        self.logger.set_debug(enabled)
        self.logger.info("Logger", f"Detailed debug log: {'enabled' if enabled else 'disabled'}")

    def analyze_path(self, path: str):
        self.logger.info("Input", f"Dropped input: {path}")
        g = collect(path=path, logger=self.logger)
        self.win.set_game_info(g)

    def analyze_appid(self, appid: str):
        self.logger.info("Input", f"Manual AppID: {appid}")
        g = collect(appid=appid, logger=self.logger)
        self.win.set_game_info(g)

    def search_registry(self, game_name: str):
        current = self.win.current_game()
        current.game_name = game_name or current.game_name
        regs = scan_registry(current.game_name, current.install_dir, current.steam_appid, current.main_exe_path, self.logger)
        current.registry_candidates = regs
        if regs:
            best = regs[0]
            current.registry = {
                "display_name": best.values.get("DisplayName", ""),
                "install_location": best.values.get("InstallLocation", ""),
                "publisher": best.values.get("Publisher", ""),
                "display_icon": best.values.get("DisplayIcon", ""),
                "uninstall_string": best.values.get("UninstallString", ""),
                "key": best.key,
            }
        self.win.set_game_info(current)


def collect(appid: str = "", path: str = "", file: str = "", logger: DebugLogger | None = None) -> GameInfo:
    g = GameInfo()
    if file:
        path = file
    if path and os.path.isfile(path):
        data = parse_input_file(path, logger)
        appid = appid or data.get("steam_appid", "")
        if data.get("steam_appid") and logger:
            logger.info("Steam", f"Resolved AppID: {data.get('steam_appid')}")
        if data.get("exe"):
            g.main_exe_path = data["exe"]
            g.install_dir = os.path.dirname(data["exe"])
            if logger:
                logger.info("Input", f"Input exe: {data['exe']}")
    elif path and os.path.isdir(path):
        g.install_dir = path
        if logger:
            logger.info("Input", f"Input folder: {path}")

    if appid:
        g.steam_appid = appid
        g.steam_url = f"steam://rungameid/{appid}"
        s = resolve_appid(appid, logger)
        g.game_name = s.get("name", "") or g.game_name
        g.install_dir = s.get("install_dir", g.install_dir)

    if g.install_dir and os.path.isdir(g.install_dir):
        exes = scan_exes(g.install_dir, g.game_name, logger=logger)
        g.exe_candidates = exes
        if exes:
            main = exes[0]
            g.main_exe_path = main.path
            g.process_name = os.path.basename(main.path)
            g.exe_info = main.exe_info

    regs = scan_registry(g.game_name, g.install_dir, g.steam_appid, g.main_exe_path, logger)
    g.registry_candidates = regs
    if regs:
        best = regs[0]
        g.registry = {
            "display_name": best.values.get("DisplayName", ""),
            "install_location": best.values.get("InstallLocation", ""),
            "publisher": best.values.get("Publisher", ""),
            "display_icon": best.values.get("DisplayIcon", ""),
            "uninstall_string": best.values.get("UninstallString", ""),
            "key": best.key,
        }
    return g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--appid", default="")
    ap.add_argument("--path", default="")
    ap.add_argument("--file", default="")
    ap.add_argument("--gui", action="store_true")
    args = ap.parse_args()
    if args.gui or (not args.appid and not args.path and not args.file):
        app = QApplication([])
        controller = Controller(None)
        win = MainWindow(controller)
        controller.set_window(win)
        win.show()
        app.exec()
    else:
        g = collect(args.appid, args.path, args.file)
        print(json.dumps(g.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
