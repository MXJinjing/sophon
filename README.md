# Sophon

Sophon 包含 Python 服务端和命令行客户端，用于下载、安装、更新和校验 hk4e 游戏资源。客户端不维护本地安装登记或任务记录；游戏目录状态、下载缓存和任务由服务端处理。

本教程采用固定顺序：**准备 uv 和依赖 → 在终端一启动 server → 在终端二运行 client**。所有项目命令都在 `sophon` 根目录执行；不需要激活虚拟环境，也不需要安装 pip。

## 1. 安装 uv

uv 负责下载 Python、创建项目环境并安装锁文件中的依赖。已有 uv 可以跳过安装，执行 `uv --version` 检查。

macOS / Linux：

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

macOS 已有 Homebrew 也可以使用 `brew install uv`。

Windows PowerShell：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

安装后重新打开终端，再检查：

```sh
uv --version
```

其他安装方式见 [uv 官方安装说明](https://docs.astral.sh/uv/getting-started/installation/)。

## 2. 进入项目并准备环境

macOS 上本项目的位置：

```sh
cd ~/Projects/yaagl-build/sophon
```

Linux 请进入你自己的 Sophon 项目目录。Windows 示例（替换成实际项目路径）：

```powershell
cd C:\Projects\sophon
```

以下命令在三个系统上相同：

```sh
uv python install 3.13
uv sync --project sophon-server --locked --python 3.13
uv sync --project sophon-client --locked --python 3.13
```

首次执行需要下载依赖。服务端依赖包括 FastAPI、pycurl、zstandard 等；客户端依赖包括 Rich 进度条。Python 最低要求 3.11，这里统一使用 3.13。

- `--project sophon-server` 选择服务端环境，位于 `sophon-server/.venv`。
- `--project sophon-client` 选择客户端环境，位于 `sophon-client/.venv`。
- `--locked` 使用提交的锁文件，依赖配置与锁文件不一致时直接报错。
- `uv run` 在指定项目环境中运行命令，会检查需要的依赖。

不要只在根目录执行 `uv sync`，根目录环境不能代替两个组件的环境。也不要用根目录 `.venv/bin/python3` 配合 `python -m pip` 安装客户端依赖。始终指定正确的 `--project` 即可。[uv 项目环境说明](https://docs.astral.sh/uv/guides/projects/)

## 3. 终端一：先启动服务端

保持当前终端在项目根目录，执行：

```sh
uv run --project sophon-server --locked python run-server.py
```

出现类似以下信息表示启动成功：

```text
Uvicorn running on http://127.0.0.1:8000
```

**保持这个终端运行，不要关闭。** 浏览器打开 `http://127.0.0.1:8000/health` 可检查健康响应；`http://127.0.0.1:8000/docs` 可查看 API。

服务端默认只监听本机 8000 端口。运行服务端不会自动下载游戏，下载由下一步的客户端命令发起。

## 4. 终端二：运行客户端

另外打开一个终端，同样进入项目根目录：

```sh
cd ~/Projects/yaagl-build/sophon
uv run --project sophon-client --locked python run-client.py --help
```

Windows / Linux 使用实际项目路径。通过 uv 运行时，命令中的 `python` 在所有平台通用，无需改为 python3。

客户端始终连接终端一启动的服务。没有服务时直接报错；客户端不会自动启动或关闭服务端。

```sh
uv run --project sophon-client --locked python run-client.py list hk4e_cn
```

完整命令中的最后一部分才是具体操作，如 `list`、`install`、`check`。客户端不是交互式菜单，每次运行一条命令，完成后退出；服务端继续运行。

包名：

| 包名 | 地区 |
| --- | --- |
| `hk4e_cn` | 国服 |
| `hk4e_os` | 国际服 |
| `hk4e_bb` | 渠道服 |

指定版本使用 `hk4e_cn@4.5.0`，无需 `--region`。下面的 4.5.0 是用法示例，请先查看 list 的当前结果。

## 5. 查询全部可下载版本

```sh
# 国服全部已索引且经官方清单确认的版本
uv run --project sophon-client --locked python run-client.py list hk4e_cn

# 所有地区
uv run --project sophon-client --locked python run-client.py list

# 忽略服务端十分钟内存缓存，重新查询
uv run --project sophon-client --locked python run-client.py list hk4e_os --refresh
```

服务端从 [公开历史索引](https://github.com/orilights/pkg_version) 获取候选版本，再逐个向官方确认 Sophon 清单。首次查询可能较慢，不下载游戏内容。索引可能存在收录遗漏；清单可用不保证所有资源块仍在线。早期没有 Sophon 清单的版本不会列出。

只筛选一个已索引版本：

```sh
uv run --project sophon-client --locked python run-client.py list hk4e_cn@4.5.0
```

list 去重后按版本号从新到旧显示，最新版本在最前面；例如 4.10.0 排在 4.9.0 前。末尾数量为筛选后实际列出的不重复版本数。

| 列 | 含义 |
| --- | --- |
| PACKAGE | 地区包名和精确版本 |
| TOTAL (game) | 游戏本体的文件总大小 |
| DOWNLOAD (game) | 官方压缩资源的下载大小 |

两种大小都不含额外语音，来自官方版本元数据，无需额外下载清单。缺少统计时显示未知；不代表更新增量、剩余下载量或安装所需临时空间。`--json` 输出还包含各语音分类的大小。

省略安装或下载命令中的 @版本时使用最新版。未被索引收录的精确版本仍可直接通过 files 或 download 查询，不必先出现在 list 中。

## 6. 安装到明确指定的目录

选择专用空目录，或尚不存在的目录。路径带空格时加引号：

```sh
uv run --project sophon-client --locked python run-client.py install hk4e_cn@4.5.0 --dir ./games/cn-45
```

`./games/cn-45` 相对服务端的工作目录；按本教程启动时为项目根目录。所有 `--dir`、`--output`、`--tempdir` 都属于服务端，客户端原样发送，不读取或检查客户端磁盘。服务端展开 `~` 并检查目录，推荐使用绝对路径。也可使用绝对路径，例如 macOS/Linux 的 `/path/to/game`，或 Windows 的 `"D:\Games\hk4e_cn"`。

省略版本安装最新版，添加语音：

```sh
uv run --project sophon-client --locked python run-client.py install hk4e_os --dir ./games/os --voice en-us --voice ja-jp
```

默认安装主程序；语音可选 `zh-cn`、`en-us`、`ja-jp`、`ko-kr`，`--voice` 可重复。所有安装、检查、修复和更新操作必须提供 `--dir`；没有默认游戏目录。

Rich 进度条会显示下载量、百分比、速度、剩余时间和活跃文件。速度尚未测得时不会推算剩余时间。客户端默认等待操作完成，并打印服务端 task_id；请保留该 ID，后续可以用 tasks 管理任务。

## 7. 查看目录安装状态

```sh
uv run --project sophon-client --locked python run-client.py status --dir ./games/cn-45
```

status 只读目录中的 `config.ini` 和服务端 `.sophon/state.json`，显示版本、地区、安装或更新是否未完成，以及版本记录是否一致。它通过服务端读取目录，不创建记录。

地区优先读取服务端 `.sophon/state.json`；无记录时从 `config.ini` 的 channel=14 识别 bb，channel=1 且 sub_channel=1/0 分别识别 cn/os。缺少字段时显示地区未知，不默认猜测。JSON 包含 region（未知为 null）。

“已安装”只代表存在版本信息，不代表所有文件完整；完整性需要下一步 check。

## 8. 检查和修复

可以指定检查版本，也可以省略 @版本以使用服务端目录中的当前版本：

```sh
uv run --project sophon-client --locked python run-client.py check hk4e_cn@4.5.0 --dir ./games/cn-45
uv run --project sophon-client --locked python run-client.py repair hk4e_cn@4.5.0 --dir ./games/cn-45
```

省略版本时的常用命令：

```sh
uv run --project sophon-client --locked python run-client.py check hk4e_cn --dir ./games/cn-45
uv run --project sophon-client --locked python run-client.py repair hk4e_cn --dir ./games/cn-45
```

两者先从服务端 status 获取安装版本，并查询最新版提示是否有更新。check 只提示，始终检查当前版本，不更新。repair 在交互终端询问是否先更新，默认否：选择是则等待 update 成功后修复最新版，选择否则修复当前版本。更新失败或取消时不提交 repair；即便使用 --detach，也必须先等待更新成功再提交后台修复。

非交互环境和 --json 模式不询问、不自动更新。查询更新失败时提示并继续当前版本；目录中无法识别版本时会报错，需要显式指定 @版本。显式版本按指定版本处理，不触发更新询问。

check 默认校验大小和 MD5，不下载游戏文件；可能由服务端生成清单缓存。repair 会修复缺失或损坏的文件。`--quick` 只比较大小，可能漏掉内容损坏。默认处理 game 分类；若需校验已安装语音，显式添加对应 `--voice`。

```sh
uv run --project sophon-client --locked python run-client.py check hk4e_cn@4.5.0 --dir ./games/cn-45 --voice zh-cn
```

### 查看全部异常并保存报告

终端默认显示前 20 项异常；保存完整 JSON 报告（包括全部 issues 和任务级 error）：

```sh
uv run --project sophon-client --locked python run-client.py check hk4e_os --dir ./games/os --output ./reports/check.json
uv run --project sophon-client --locked python run-client.py repair hk4e_os --dir ./games/os --output ./reports/repair.json
```

报告写入客户端本地磁盘，覆盖同名文件，不是服务端游戏目录。任务结束（包括失败/取消）后保存；--detach 不等待完成，需随后用 tasks watch 保存。已有任务可直接查看或导出（替换 TASK_ID 为实际 ID）：

```sh
uv run --project sophon-client --locked python run-client.py --json tasks status TASK_ID
uv run --project sophon-client --locked python run-client.py tasks watch TASK_ID --output ./reports/check.json
```

报告的 result.issues 包含每个异常文件的 filename/reason；任务失败原因在 error 字段。任务 ID 必须仍存在于服务端内存。下载命令的 --output OUTPUT_DIR 指服务端下载目录；检查、修复和观察命令的 --output REPORT_FILE 指客户端报告文件。

## 9. 更新、切换版本和降级

已有安装使用 update，不要重新 install：

```sh
# 更新至最新版
uv run --project sophon-client --locked python run-client.py update hk4e_cn --dir ./games/cn-45

# 同步到指定版本
uv run --project sophon-client --locked python run-client.py update hk4e_cn@5.0.0 --dir ./games/cn-45

# 明确允许降级
uv run --project sophon-client --locked python run-client.py update hk4e_cn@4.5.0 --dir ./games/cn-45 --allow-downgrade
```

update 使用完整清单同步，复用正确文件；服务端保留已有受管语音分类。版本号在完整操作成功后提交，但整个目录不是原子事务：失败或取消前部分文件可能已经改变。操作中断后重新提交相同目标可继续复用文件和缓存。

## 10. 浏览目录和下载指定文件

files 类似 ls，默认列根目录的直接子项，第一列区分目录和文件，文件显示大小：

```sh
uv run --project sophon-client --locked python run-client.py files hk4e_os@4.5.0
uv run --project sophon-client --locked python run-client.py files hk4e_os@4.5.0 GenshinImpact_Data
uv run --project sophon-client --locked python run-client.py files hk4e_os@4.5.0 GenshinImpact_Data/StreamingAssets/AssetBundles/data_revision
```

输出最前面显示 pwd，包含包名、版本、分类和清单路径。TYPE 区分 file/directory，SIZE 显示文件大小，PATH 相对当前 pwd，目录名不添加 /。交互终端目录为蓝色、文件为绿色；--json 保留完整 filename 和原始数据。

```text
pwd: hk4e_os@4.5.0 [game] /GenshinImpact_Data
TYPE          SIZE  PATH
directory        -  StreamingAssets
file          18 B  app.info
```

下载参数必须相对游戏根目录：上例的 app.info 应传 GenshinImpact_Data/app.info，不能只传短名称。

首次下载并验证完整清单，服务端持久缓存压缩清单并建立内存目录索引。后续目录切换和分页直接查询索引，不重新下载、解析或遍历全部文件。`--page 2 --count 100` 在当前目录内分页，`--recursive` 递归列文件，`--match` 搜索路径下的文件。`--refresh` 强制重新下载验证清单。服务端可通过 SOPHON_MANIFEST_CACHE 设置缓存目录，默认 ~/.cache/sophon-server/manifests；缓存属于服务端，不是客户端安装登记。

```sh
uv run --project sophon-client --locked python run-client.py files hk4e_os@4.5.0 --match '*data_revision'
uv run --project sophon-client --locked python run-client.py download hk4e_os@4.5.0 GenshinImpact_Data/StreamingAssets/AssetBundles/data_revision --output ./picked/os-45
```

`download --help` 中 `--output OUTPUT_DIR` 指服务端输出目录。多个文件连续填写，路径有空格时加引号：

```sh
uv run --project sophon-client --locked python run-client.py download hk4e_os@4.5.0 UnityPlayer.dll GenshinImpact_Data/app.info --output ./picked/os-45
```

download 后直接连续填写一个或多个精确文件路径，不再使用 --file；路径相对游戏根目录，使用 `/` 分隔符。check/repair 仍可重复 --file 筛选文件。语音文件使用 --category en-us 等分类。单文件下载使用 --output 指定目录，不更新完整安装版本；建议使用独立目录保存历史文件。

## 11. 后台下载和任务管理

终端一的服务端必须持续运行。使用 `--detach` 提交后，客户端打印 task_id 并退出：

```sh
uv run --project sophon-client --locked python run-client.py install hk4e_cn@4.5.0 --dir ./games/cn-45 --detach
```

安装、更新、检查、修复和下载的提交结果默认显示文字提示，随后显示任务进度；--json 保留原始 JSON。

```text
下载任务已提交：hk4e_os@4.5.0
任务 ID：9185f846-dd11-4dc3-8c30-d2a76f0110fe
状态：等待处理
```

把下面的 `TASK_ID` 替换为实际任务 ID：

```sh
uv run --project sophon-client --locked python run-client.py tasks status TASK_ID
uv run --project sophon-client --locked python run-client.py tasks pause TASK_ID
uv run --project sophon-client --locked python run-client.py tasks resume TASK_ID
uv run --project sophon-client --locked python run-client.py tasks cancel TASK_ID
uv run --project sophon-client --locked python run-client.py tasks watch TASK_ID
```

status/pause/resume/cancel 原样调用服务端接口，保留返回数据。控制消息不代表操作已完成，实际状态用 tasks status 查看。服务端没有“列出全部任务”的接口，客户端也不保存任务 ID。

普通前台操作按 Ctrl+C 会请求取消任务；tasks watch 按 Ctrl+C 只退出观察，任务继续。后台下载期间不要关闭服务端。服务端重启会中断运行任务并清空任务 ID。

## 12. 常用参数和帮助

```sh
uv run --project sophon-client --locked python run-client.py install --help
uv run --project sophon-client --locked python run-client.py tasks --help
uv run --project sophon-client --locked python run-client.py tasks pause --help

# JSON 输出
uv run --project sophon-client --locked python run-client.py --json status --dir ./games/cn-45
```

全局参数 `--server`、`--json` 位于子命令之前。操作参数 `--dir`、`--voice`、`--threads`、`--limit`、`--detach` 等位于子命令之后。

`--threads 8` 默认同时下载最多八个文件，可设置 1..64；每个文件内 chunk 顺序下载。安装、更新、修复和指定文件下载支持此参数；check 不下载。版本统一通过 `@版本` 指定，客户端已移除 `--version`。

```sh
uv run --project sophon-client --locked python run-client.py install hk4e_cn@4.5.0 --dir ./games/cn-45 --threads 4
```

`--limit 1048576` 约为 1 MiB/s，0 不限速，由服务端共享。`--tempdir ./cache/cn-45` 指定服务端缓存目录，缓存目录不能包含游戏目录。

退出码：成功 0，任务或请求失败 1，检查发现异常 2，取消 130；命令参数错误也可能为 2。tasks status 等直接转发命令的成功只表示请求成功，应查看返回体中的任务状态。

## 13. 修改端口

macOS / Linux 的终端一：

```sh
SOPHON_PORT=9000 uv run --project sophon-server --locked python run-server.py
```

Windows PowerShell 的终端一：

```powershell
$env:SOPHON_PORT = "9000"
uv run --project sophon-server --locked python run-server.py
```

终端二：

```sh
uv run --project sophon-client --locked python run-client.py --server http://127.0.0.1:9000 list hk4e_cn
```

当前客户端只接受本机服务地址。下载路径由服务端解释；本教程要求服务端与客户端在同一台机器上。

## 14. 常见问题

### VIRTUAL_ENV does not match the project environment

当前终端激活了根目录 .venv，uv 使用的是 --project 指定的组件环境，所以出现提示。先执行 `deactivate`，再照教程使用 uv run；若没有激活环境，不需要执行 deactivate。不要为消除提示使用 --active，那会改用根目录环境而不是客户端环境。该提示与清单下载被截断无关。

### No module named pip

uv 创建的环境可以没有 pip，本教程不需要 pip。回到根目录执行 `uv sync --project sophon-client --locked --python 3.13`，随后使用带 `--project sophon-client` 的 uv run 命令。无需给根目录 `.venv` 安装 pip。

### 提示安装客户端依赖后可显示图形进度条

当前 Python 缺少 Rich，通常是直接用了根目录或系统 Python。执行上一节的客户端 sync，再用 uv run 启动。普通终端显示进度条；`--json` 或输出重定向到文件时退回文本，这是预期行为。

### HTTP 405: Method Not Allowed

可能连接了更新前的服务端，未加载新增的 `/api/history/versions` 接口。等运行任务完成后，在终端一按 Ctrl+C，再重新执行服务端启动命令。更新源码不会自动更新正在运行的进程。重启会清空服务端任务 ID。

### Install requires an empty directory or a matching interrupted Sophon installation

install 只接受空目录，或同版本安装中断后留下的匹配 Sophon 目录。已有完整安装使用 update；已有文件需要校验/修复时用 check/repair。只下载过零散文件的目录不要当作空目录安装，可以选择新目录。不要为消除报错直接删除现有文件。

### 连接失败或端口被占用

确认终端一仍运行，浏览器访问对应端口的 `/health`。服务端端口与客户端 `--server` 必须一致。若启动报 address already in use，先确认端口上是否已有 Sophon 服务，或按第 13 节选择其他端口。

### 安装依赖时 pycurl 构建失败

先保留完整错误信息；有些平台没有适用的预编译包，需要系统 C 编译器、curl 开发库和相应 TLS 库。uv 管理 Python 依赖，不代替这些系统组件。macOS 可准备 Xcode Command Line Tools；Linux 具体包名依发行版而定。Windows 原生依赖安装尚未在本项目中完整验证。

### 查询历史版本较慢、某个版本无法下载

list 首次逐个确认全部候选，之后使用服务端十分钟内存缓存。`--refresh` 可重查。索引存在某版本不代表官方仍提供清单和资源；网络错误也不会当作版本不存在。下载失败通过任务 error 返回，不自动换成其他版本。

## 15. 仓库结构、构建和测试

```text
sophon/
  run-client.py / run-server.py
  build.py / build-client.py / test.py
  sophon-client/
    pyproject.toml / uv.lock / README.md
    src/sophon_client/
    tests/
  sophon-server/
    pyproject.toml / uv.lock / README.md
    src/
      server.py              # 源码运行与 Nuitka 入口
      manifest*_pb2.py       # protobuf 生成文件
      api/                   # 路由与请求模型
      services/              # 业务任务与查询
      engine/                # 清单、下载、差分更新与修复
      infrastructure/        # 线程、连接、限速与平台适配
    proto/ / tests/
  third_party/hpatchz/
  docs/build-sophon.original.sh.txt
```

源码和测试分开，所有构建脚本位于根目录。完整 API 见 [服务端 README 的 API 参考](sophon-server/README.md#api-参考)。客户端不会创建 registry.json；服务端可在游戏目录中创建 `.sophon` 状态和清单/下载缓存，这是服务端管理目录的一部分。

服务端保留 uv + protoc 31.1 + Nuitka standalone 构建流程。macOS、Linux 和 Windows PowerShell 均在仓库根目录执行：

```sh
uv run --project sophon-server --locked python build.py
```

配置检查和客户端包构建：

```sh
uv run --project sophon-server --locked python build.py --platform linux --arch x64 --plan
uv run --project sophon-server --locked python build.py --platform win32 --arch x64 --plan
uv run --project sophon-client --locked python build-client.py
```

Linux x64、Windows x64 和 macOS arm64/x64 的 hpatchz 已内置，来源、许可证和校验值见 [third_party/hpatchz/README.md](third_party/hpatchz/README.md)。其他架构可在构建时用 `--hpatchz` 指定原生工具。源码历史 chunk 操作不依赖 hpatchz；旧 ldiff 接口需要它。原生构建仍需目标系统编译器；Linux/Windows 完整原生构建尚未实际验证。

服务端产物位于 `build/<platform>-<arch>/server.dist/`，应分发整个目录。客户端 wheel/sdist 位于 `dist/`。源码运行不需要先构建。

测试仅按需手工运行，不由构建自动触发。示例：

```sh
uv run --project sophon-server --locked python test.py --component server --pattern test_version_catalog.py
uv run --project sophon-client --locked python test.py --component client --pattern test_package_cli.py
```

这里只选择两个小型测试文件。HTTP 集成测试需要服务端依赖；渲染测试需要 Rich。构建、缓存、虚拟环境和下载文件均不提交。原构建脚本仅作为归档文档保留。
