# SteamGameInfoCollector

Windows Steam 游戏信息采集复制工具（本地 GUI + CLI）。

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行方式

GUI:

```bash
python main.py --gui
```

或直接：

```bash
python main.py
```

## CLI 调试

```bash
python main.py --appid 123456
python main.py --path "D:\\SteamLibrary\\steamapps\\common\\Example Game"
python main.py --file "C:\\Users\\xxx\\Desktop\\Example Game.url"
```

## GUI 使用

- 拖入 `.url/.lnk/.exe/目录` 自动分析。
- 主结果区字段均可编辑并单独复制。
- 支持复制基础信息、exe 信息、注册表信息、完整信息、JSON。

## PyInstaller 打包

目录模式（推荐）:

```bash
pyinstaller --noconsole --name SteamGameInfoCollector main.py
```

目录模式打包后，`dist/SteamGameInfoCollector/_internal` 是 PyInstaller 放置 Python 运行时、第三方依赖和 Qt 依赖文件的内部目录。使用目录模式时不要只复制单个 exe，也不要删除 `_internal`，否则程序可能无法启动。若想只分发一个文件，可以使用下面的 `--onefile` 模式。

单文件:

```bash
pyinstaller --noconsole --onefile --name SteamGameInfoCollector main.py
```

## 常见问题

- 在非 Windows 环境下无法读取注册表/lnk/exe 版本信息。
- 若未安装 Steam，会退回为本地路径和 exe/注册表猜测模式。
- exe 的 `CompanyName`、`ProductName`、`FileDescription` 来自版本信息，不等于数字签名。数字签名会单独显示为“已签名 / 未签名 / 读取失败 / 未知”以及签名主体。


## 使用 GitHub Actions 快速出可执行文件

可以。这个仓库已添加工作流：`.github/workflows/build-windows.yml`。

### 方式 1（最简单）
1. 打开 GitHub 仓库的 **Actions**。
2. 选择 **Build Windows EXE**。
3. 点击 **Run workflow**。
4. 构建完成后，在该次运行页面下载 artifact：`SteamGameInfoCollector-windows`。

### 方式 2（自动发布）
1. 推送一个 `v` 开头的 tag（例如 `v0.1.0`）。
2. 工作流会构建并自动创建 GitHub Release，附带 `SteamGameInfoCollector-windows.zip`。

### 方式 3（main 分支自动更新 rease-latest）

推送到 `main` 后，工作流会构建 Windows 版并更新预发布版本 `rease-latest`，下载文件为 `SteamGameInfoCollector-windows.zip`。

触发记录：2026-05-09 重新触发 rease-latest Windows EXE 构建。

### 本地对应命令
```bash
pyinstaller --noconsole --name SteamGameInfoCollector main.py
```


## 一键推送并触发 Release（可选）

如果你已经有 GitHub 仓库地址，可以使用仓库内脚本：

```bash
./publish_release.sh origin work v0.1.0
```

它会自动执行：
1. 检查 remote 是否存在
2. 推送 `work` 分支
3. 创建并推送 tag（如 `v0.1.0`）
4. 触发 `.github/workflows/build-windows.yml` 的 tag 发布流程
