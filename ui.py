from __future__ import annotations
from PySide6.QtWidgets import *
from PySide6.QtCore import Qt, QThread, Signal, QObject
from models import GameInfo
from copy_formatter import basic_text, exe_text, reg_text, full_text, as_json

class DropLabel(QLabel):
    fileDropped = Signal(str)
    def __init__(self):
        super().__init__("把 Steam 游戏图标、.url、.lnk、游戏目录或 exe 拖到这里")
        self.setAcceptDrops(True)
        self.setFrameShape(QFrame.StyledPanel)
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls(): e.acceptProposedAction()
    def dropEvent(self, e):
        urls=e.mimeData().urls()
        if urls: self.fileDropped.emit(urls[0].toLocalFile())

class MainWindow(QMainWindow):
    def __init__(self, controller):
        super().__init__(); self.controller=controller; self.setWindowTitle("Steam 游戏信息采集复制工具")
        self.fields={}
        w=QWidget(); self.setCentralWidget(w); v=QVBoxLayout(w)
        self.drop=DropLabel(); v.addWidget(self.drop)
        self.drop.fileDropped.connect(controller.analyze_path)
        f=QFormLayout(); v.addLayout(f)
        for key,label in [("game_name","游戏名称"),("steam_appid","Steam AppID"),("steam_url","Steam URL"),("install_dir","游戏安装目录"),("main_exe_path","主 exe 路径"),("process_name","进程名"),("exe_company","exe CompanyName"),("exe_product","exe ProductName"),("exe_desc","exe FileDescription"),("exe_file_version","exe FileVersion"),("exe_product_version","exe ProductVersion"),("exe_original","exe OriginalFilename"),("reg_name","注册表 DisplayName"),("reg_install","注册表 InstallLocation"),("reg_pub","注册表 Publisher"),("reg_icon","注册表 DisplayIcon"),("reg_uninstall","注册表 UninstallString"),("reg_key","注册表路径")]:
            le=QLineEdit(); btn=QPushButton("复制"); btn.clicked.connect(lambda _,k=key:self.copy_field(k))
            row=QHBoxLayout(); row.addWidget(le); row.addWidget(btn)
            f.addRow(label, self._wrap(row)); self.fields[key]=le
        h=QHBoxLayout(); v.addLayout(h)
        for text,fn in [("复制基础信息",lambda:basic_text(self.current_game())),("复制 exe 信息",lambda:exe_text(self.current_game())),("复制注册表信息",lambda:reg_text(self.current_game())),("复制完整信息",lambda:full_text(self.current_game())),("复制 JSON",lambda:as_json(self.current_game()))]:
            b=QPushButton(text); b.clicked.connect(lambda _,f=fn:self.copy_text(f())); h.addWidget(b)
        self.log=QPlainTextEdit(); v.addWidget(self.log)
    def _wrap(self, layout):
        w=QWidget(); w.setLayout(layout); return w
    def copy_text(self, text):
        if not text.strip(): QMessageBox.information(self,"提示","当前字段为空"); return
        QApplication.clipboard().setText(text); self.statusBar().showMessage("已复制", 1500)
    def copy_field(self,key): self.copy_text(self.fields[key].text())
    def set_game_info(self,g: GameInfo):
        self.fields["game_name"].setText(g.game_name); self.fields["steam_appid"].setText(g.steam_appid); self.fields["steam_url"].setText(g.steam_url); self.fields["install_dir"].setText(g.install_dir); self.fields["main_exe_path"].setText(g.main_exe_path); self.fields["process_name"].setText(g.process_name)
        self.fields["exe_company"].setText(g.exe_info.company_name); self.fields["exe_product"].setText(g.exe_info.product_name); self.fields["exe_desc"].setText(g.exe_info.file_description); self.fields["exe_file_version"].setText(g.exe_info.file_version); self.fields["exe_product_version"].setText(g.exe_info.product_version); self.fields["exe_original"].setText(g.exe_info.original_filename)
        self.fields["reg_name"].setText(g.registry["display_name"]); self.fields["reg_install"].setText(g.registry["install_location"]); self.fields["reg_pub"].setText(g.registry["publisher"]); self.fields["reg_icon"].setText(g.registry["display_icon"]); self.fields["reg_uninstall"].setText(g.registry["uninstall_string"]); self.fields["reg_key"].setText(g.registry["key"])
    def current_game(self):
        g=GameInfo();
        for k in ["game_name","steam_appid","steam_url","install_dir","main_exe_path","process_name"]: setattr(g,k,self.fields[k].text())
        g.exe_info.company_name=self.fields["exe_company"].text(); g.exe_info.product_name=self.fields["exe_product"].text(); g.exe_info.file_description=self.fields["exe_desc"].text(); g.exe_info.file_version=self.fields["exe_file_version"].text(); g.exe_info.product_version=self.fields["exe_product_version"].text(); g.exe_info.original_filename=self.fields["exe_original"].text()
        g.registry={"display_name":self.fields["reg_name"].text(),"install_location":self.fields["reg_install"].text(),"publisher":self.fields["reg_pub"].text(),"display_icon":self.fields["reg_icon"].text(),"uninstall_string":self.fields["reg_uninstall"].text(),"key":self.fields["reg_key"].text()}
        return g
