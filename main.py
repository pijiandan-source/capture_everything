from __future__ import annotations
import argparse, json, os
from PySide6.QtWidgets import QApplication
from models import GameInfo
from steam_resolver import resolve_appid
from shortcut_resolver import parse_input_file
from exe_scanner import scan_exes
from registry_finder import scan_registry
from ui import MainWindow

class Controller:
    def __init__(self, win): self.win=win
    def analyze_path(self,path):
        g=collect(path=path)
        self.win.set_game_info(g)
        self.win.log.appendPlainText(f"[Input] 拖入: {path}")

def collect(appid:str="", path:str="", file:str="") -> GameInfo:
    g=GameInfo()
    if file: path=file
    if path and os.path.isfile(path):
        data=parse_input_file(path)
        appid=appid or data.get("steam_appid","")
        if data.get("exe"): g.main_exe_path=data["exe"]; g.install_dir=os.path.dirname(data["exe"])
    elif path and os.path.isdir(path):
        g.install_dir=path
    if appid:
        g.steam_appid=appid; g.steam_url=f"steam://rungameid/{appid}"
        s=resolve_appid(appid); g.game_name=s.get("name","") or g.game_name; g.install_dir=s.get("install_dir",g.install_dir)
    if g.install_dir and os.path.isdir(g.install_dir):
        exes=scan_exes(g.install_dir,g.game_name)
        if exes:
            main=exes[0]; g.main_exe_path=main.path; g.process_name=os.path.basename(main.path); g.exe_info=main.exe_info
    regs=scan_registry(g.game_name,g.install_dir,g.steam_appid,g.main_exe_path)
    if regs:
        best=regs[0]
        g.registry={"display_name":best.values.get("DisplayName","") ,"install_location":best.values.get("InstallLocation","") ,"publisher":best.values.get("Publisher","") ,"display_icon":best.values.get("DisplayIcon","") ,"uninstall_string":best.values.get("UninstallString","") ,"key":best.key}
    return g

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--appid",default="")
    ap.add_argument("--path",default="")
    ap.add_argument("--file",default="")
    ap.add_argument("--gui",action="store_true")
    args=ap.parse_args()
    if args.gui or (not args.appid and not args.path and not args.file):
        app=QApplication([])
        controller=Controller(None)
        win=MainWindow(controller); controller.win=win
        win.show(); app.exec()
    else:
        g=collect(args.appid,args.path,args.file)
        print(json.dumps(g.to_dict(),ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
