# Sophon Client

无状态的 hk4e Python CLI。版本写在地区包名之后，例如 `hk4e_cn@4.5.0`；客户端不登记安装、不保存任务和文件状态，也不启动或关闭服务端。源码要求 Python >=3.11，推荐统一使用 uv 管理的 Python 3.13；Rich 负责列表颜色与下载进度。

完整分步教程及常见问题见 [根目录 README](../README.md)。以下命令均在仓库根目录执行，Windows、Linux、macOS 的 uv 命令一致。

## 准备和启动顺序

```sh
uv python install 3.13
uv sync --project sophon-server --locked --python 3.13
uv sync --project sophon-client --locked --python 3.13
```

终端一保持服务端运行：

```sh
uv run --project sophon-server --locked python run-server.py
```

终端二执行客户端：

```sh
uv run --project sophon-client --locked python run-client.py --help
```

无需激活 .venv 或安装 pip。若终端已激活根目录环境并提示 VIRTUAL_ENV 不匹配，执行 deactivate，再使用上述命令；不要用 --active 将客户端指向错误环境。

## 命令速查

| 命令 | 用途                    |
| --- |-----------------------|
| `list [包名[@版本]]` | 全部已索引且经官方清单确认的版本      |
| `files 包名[@版本] [路径]` | 类似 ls 浏览清单目录和文件       |
| `install 包名[@版本] --dir 目录` | 安装指定版本，省略版本则最新        |
| `update 包名[@版本] --dir 目录` | 同步指定版本，省略版本则最新        |
| `status --dir 目录` | 只读服务端目录安装版本状态，不检查完整性  |
| `check 包名[@版本] --dir 目录` | 检查大小和 MD5，省略版本读取服务端安装版本 |
| `repair 包名[@版本] --dir 目录` | 修复异常文件，省略版本时可确认先更新    |
| `download 包名[@版本] 文件路径 [更多文件路径] --output 目录` | 指定文件下载，省略版本则最新        |
| `tasks status/pause/resume/cancel/watch TASK_ID` | 管理或观察服务端任务            |

包名：hk4e_cn 国服、hk4e_os 国际服、hk4e_bb 渠道服。

## 安装、维护和下载参数

| 参数 | 默认/规则 | 适用命令 |
| --- | --- | --- |
| `--dir` | 必须明确指定，不能是盘符根目录或用户主目录 | install/update/check/repair/status |
| `--output` | 必须指定专用输出目录 | download |
| `--voice` | 默认 game 主程序，可重复添加 en-us/zh-cn/ja-jp/ko-kr | install/update/check/repair |
| `--category` | 默认 game，或选择四种语音分类之一 | files/download |
| `--threads` | 默认 8，范围 1..64，并行文件数；文件内 chunk 顺序下载 | install/update/repair/download |
| `--limit` | bytes/s，默认 0 不限速；服务端共享限速 | install/update/check/repair/download |
| `--tempdir` | 专用缓存目录，不能包含游戏目录；默认游戏目录内 .tmp | install/update/check/repair/download |
| `--file` | 相对游戏根目录的精确路径，可重复；不能是通配符 | check/repair 可选 |
| `--quick` | 只比较大小，默认比较大小和 MD5 | check/repair |
| `--allow-downgrade` | 显式允许降低已安装版本 | update |
| `--detach` | 提交 task_id 后退出；服务端仍需持续运行 | install/update/check/repair/download |

```sh
uv run --project sophon-client --locked python run-client.py install hk4e_cn@4.5.0 --dir ./games/cn --voice zh-cn --threads 8
uv run --project sophon-client --locked python run-client.py status --dir ./games/cn
uv run --project sophon-client --locked python run-client.py check hk4e_cn@4.5.0 --dir ./games/cn --voice zh-cn
uv run --project sophon-client --locked python run-client.py repair hk4e_cn@4.5.0 --dir ./games/cn --threads 4
uv run --project sophon-client --locked python run-client.py update hk4e_cn --dir ./games/cn
```

install 使用空目录或同版本中断安装目录；已有完整安装使用 update。check/repair 必须提供精确版本，不从客户端记录推断。默认校验分类是 game；语音需明确 --voice，update 还会保留服务端已有受管语音分类。操作不是整个目录的原子事务，取消前部分文件可能已改变，最终版本号在完整操作成功后提交。

## 远程版本目录 

```sh
uv run --project sophon-client --locked python run-client.py list
uv run --project sophon-client --locked python run-client.py list hk4e_cn --refresh
```

list 枚举 [公开历史索引](https://github.com/orilights/pkg_version) 候选并确认官方清单，服务端缓存十分钟，--refresh 强制重查。历史索引可能遗漏版本；清单存在不保证全部资源块仍在线。可用 list hk4e_os@4.5.0 筛选已索引的精确版本；未被索引收录的版本仍可直接通过 files 或 download 查询。

## files：目录、文件与分页

```sh
uv run --project sophon-client --locked python run-client.py files hk4e_os@4.5.0
uv run --project sophon-client --locked python run-client.py files hk4e_os@4.5.0 GenshinImpact_Data
uv run --project sophon-client --locked python run-client.py files hk4e_os@4.5.0 GenshinImpact_Data --page 2 --count 20
uv run --project sophon-client --locked python run-client.py files hk4e_os@4.5.0 GenshinImpact_Data --match '*data_revision'
```

默认根目录，列直接子项；精确文件路径返回该文件。--page 从 1 开始，默认 1；--count 默认 100，范围 1..1000。仅有下一页时才提示下一页，越界页明确提示。--recursive 递归列文件，--match 搜索路径下的文件（通配符须加引号），--refresh 重新下载校验清单。

```text
pwd: hk4e_os@4.5.0 [game] /GenshinImpact_Data
TYPE          SIZE  PATH
directory        -  StreamingAssets
file          21 B  app.info
共 26 项；第 1/1 页。
```

第一列是 file/directory；目录蓝色，文件绿色，目录大小为 -。PATH 相对 pwd，不补末尾 /；递归显示仍保留必要的子目录。pwd 是清单位置，不是终端工作目录。颜色只用于终端；--json 不包含表格或 pwd 文字，保留 API 完整 filename。可设置 NO_COLOR=1 禁用 Rich 颜色。

**download 的位置文件参数，以及 check/repair 的 --file，都必须相对游戏根目录，不能直接使用去掉 pwd 前缀后的短名称。** 例如 pwd 为 /GenshinImpact_Data 时，显示的 app.info 对应完整参数 GenshinImpact_Data/app.info。也可用 --json files 得到完整 filename。所有清单路径使用 /，Windows 也一样。

服务端首次下载完整压缩清单并验证长度、Zstd 完整帧和 protobuf，截断时最多三次重试；随后查询目录索引，不逐页重新下载。内存最多四份索引，保留十五分钟；磁盘缓存可跨重启使用。新搜索模式首次筛选候选，重复搜索复用缓存。目录浏览可与下载并行。

```sh
uv run --project sophon-client --locked python run-client.py download hk4e_os@4.5.0 GenshinImpact_Data/StreamingAssets/AssetBundles/data_revision --output ./picked/os-45
```

下载不再提供 --file；多个路径直接连续填写：download hk4e_os@4.5.0 path/one path/two --output ./picked。必须至少一个精确路径，不支持通配符。单文件下载不更新完整安装版本，建议独立目录避免混合版本。

## status 与 tasks

status --dir 只读 config.ini 和服务端 .sophon/state.json，区分目录不存在、无完整安装、已安装、安装/更新未完成、版本记录不一致。它连接服务端并只读服务端目录，不验证资源完整性；无服务端记录时尝试从 config.ini 识别地区。

```sh
uv run --project sophon-client --locked python run-client.py install hk4e_cn@4.5.0 --dir ./games/cn --detach
uv run --project sophon-client --locked python run-client.py tasks status TASK_ID
uv run --project sophon-client --locked python run-client.py tasks pause TASK_ID
uv run --project sophon-client --locked python run-client.py tasks resume TASK_ID
uv run --project sophon-client --locked python run-client.py tasks cancel TASK_ID
uv run --project sophon-client --locked python run-client.py tasks watch TASK_ID
```

自行保留服务端返回的 task_id，客户端不保存。状态/控制命令原样调用接口，无预检；控制响应不证明任务存在或已完成。服务端没有任务列表接口。任务只保存在服务端内存，重启会中断任务并使 ID 失效。tasks watch 的 Ctrl+C 只退出观察；普通前台下载的 Ctrl+C 请求取消。

## 全局选项、环境与退出码

--server 和 --json 放在子命令之前。默认服务 http://127.0.0.1:8000，可由 SOPHON_SERVER_URL 覆盖；只接受本机地址，因为路径由服务端本机解释。--server 可覆盖环境变量。没有 --no-start-server；全部请求只连接已有服务端。

Rich 显示总下载量、速度、剩余时间和最多四个活跃文件；未知速度或总量不伪造 ETA。非交互终端退回文本。成功 0，失败 1，完整性异常 2，取消 130，参数错误 2；tasks status 等请求成功不代表任务成功，应查看返回数据。

```sh
uv run --project sophon-client --locked python run-client.py --json status --dir ./games/cn
uv run --project sophon-client --locked python run-client.py --server http://127.0.0.1:9000 tasks status TASK_ID
```

旧 registry.json 不再读取或更新，无需为新客户端创建登记。服务端可在游戏目录保存状态、清单和 chunk 缓存，这与客户端无状态不矛盾。错误处理、跨平台依赖和构建详见根目录 README。

status --dir 会显示地区 cn/os/bb 和对应包名。优先读取服务端 .sophon/state.json；无该记录时，从 config.ini 的 channel=14 识别 bb，channel=1 且 sub_channel=1/0 分别识别 cn/os。缺少或无法识别的字段显示地区未知，不默认猜测；JSON 输出包含 region（未知为 null）。

list 的 TOTAL (game) 显示游戏本体文件总大小，DOWNLOAD (game) 显示官方压缩资源下载大小，均不含额外语音。大小来自验证版本时已获取的官方 manifest stats，无需下载清单；不代表更新增量、实际剩余下载量或安装所需临时空间。缺少统计时显示未知。GET /api/history/versions 新增 version_sizes（版本号 → 分类 → total_size/download_size，单位 bytes，缺失为 null）和 size_source=official_manifest_stats；保留 versions 字符串数组。JSON 包含各语音分类大小。重启旧服务端后运行 list --refresh 可获取新字段。

所有目录参数（--dir、--output、--tempdir）原样发送并由服务端展开 ~、解析相对路径及检查磁盘；相对路径基于服务端工作目录，推荐绝对路径。status --dir 调用 GET /api/history/status?gamedir=目录，服务端只读 config.ini 和 .sophon/state.json，客户端不访问本地目录。当前仍只允许本机服务地址，不启用跨机器连接；需要重启服务端加载新接口。

list 按版本号从新到旧排列，最新版本在最前面（按数字比较，例如 4.10.0 排在 4.9.0 前）。

check/repair 支持 --output REPORT_FILE，任务结束后将完整状态及所有 result.issues/error 写入客户端本地 JSON 文件（覆盖同名文件）。tasks watch TASK_ID --output REPORT_FILE 可保存已完成任务报告；--detach 需使用该方式随后导出。--json tasks status TASK_ID 查看完整原始结果。download 的 --output OUTPUT_DIR 仍指服务端下载目录。
