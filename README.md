# SteamGameInfoCollector

Windows Steam 游戏信息采集复制工具（本地 GUI + CLI）。

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行方式

开发调试（会显示控制台，方便看错误）：

```bash
python main.py
```

GUI 无控制台运行：

```bash
pythonw main.py
```

也可以显式启动 GUI：

```bash
python main.py --gui
```

## CLI 调试

```bash
python main.py --appid 123456
python main.py --path "D:\\SteamLibrary\\steamapps\\common\\Example Game"
python main.py --file "C:\\Users\\xxx\\Desktop\\Example Game.url"
```

## GUI 使用

- 拖入 `.url/.lnk/.exe/目录` 自动分析。
- 不建议以管理员身份运行本工具。管理员运行可能导致无法从普通 Explorer 拖拽文件到窗口。
- 如果拖拽不可用，请使用“选择文件”“选择文件夹”“手动 AppID”或粘贴路径分析。
- 如需打开 HKLM 注册表项，工具会在用户点击“以管理员打开 regedit”时单独请求 UAC。
- 主结果区字段均可编辑并单独复制。
- 支持复制基础信息、exe 信息、注册表信息、完整信息、JSON。
- exe 候选和注册表候选表格支持双击复制单元格、右键复制更多内容。

## PyInstaller 打包

目录模式（推荐）：

```bash
pyinstaller --noconsole --windowed --name SteamGameInfoCollector main.py
```

目录模式打包后，`dist/SteamGameInfoCollector/_internal` 是 PyInstaller 放置 Python 运行时、第三方依赖和 Qt 依赖文件的内部目录。使用目录模式时不要只复制单个 exe，也不要删除 `_internal`，否则程序可能无法启动。

单文件模式（可选）：

```bash
pyinstaller --noconsole --windowed --onefile --name SteamGameInfoCollector main.py
```

目录模式更推荐。`--onefile` 启动更慢，也更容易被杀软误报。不要使用 UPX，不要加壳，不要混淆。

隐藏控制台窗口是 GUI 程序的正常行为；降低误报的重点是目录模式打包、不 onefile、不加壳、不后台扫描、不静默写注册表。

## 安全与行为说明

- 工具不会联网自动上传数据。
- 工具不会自启动或常驻后台。
- 工具只扫描用户拖入的目录或当前 AppID 对应的游戏目录。
- `reg add LastKey` 只在用户点击“打开注册表”时执行。
- 主程序默认普通权限运行；需要管理员权限的动作会单独请求 UAC，不要求整个 GUI 以管理员权限启动。
- PowerShell 签名检测只在分析当前游戏目录 exe 时执行，不会启动时批量运行。

## 常见问题

- 在非 Windows 环境下无法读取注册表、lnk、exe 版本信息。
- 若未安装 Steam，会退回为本地路径和 exe/注册表猜测模式。
- exe 的 `CompanyName`、`ProductName`、`FileDescription` 来自版本信息，不等于数字签名。数字签名会单独显示为“已签名 / 未签名 / 签名读取失败 / 未知”等状态，以及签名主体。

## 使用 GitHub Actions 快速出可执行文件

这个仓库已添加工作流：`.github/workflows/build-windows.yml`。

### 方式 1：手动构建

1. 打开 GitHub 仓库的 **Actions**。
2. 选择 **Build Windows EXE**。
3. 点击 **Run workflow**。
4. 构建完成后，在该次运行页面下载 artifact：`SteamGameInfoCollector-windows`。

### 方式 2：正式发布

1. 推送一个 `v` 开头的 tag，例如 `v0.1.0`。
2. 工作流会构建并自动创建 GitHub Release，附带 `SteamGameInfoCollector-windows.zip`。

### 方式 3：main 分支自动更新 rease-latest

推送到 `main` 后，工作流会构建 Windows 版并更新预发布版本 `rease-latest`，下载文件为 `SteamGameInfoCollector-windows.zip`。

## 一键推送并触发 Release（可选）

如果你已经有 GitHub 仓库地址，可以使用仓库内脚本：

```bash
./publish_release.sh origin work v0.1.0
```

它会自动执行：

1. 检查 remote 是否存在。
2. 推送指定分支。
3. 创建并推送 tag。
4. 触发 `.github/workflows/build-windows.yml` 的 tag 发布流程。
