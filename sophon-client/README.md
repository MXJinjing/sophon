# Sophon Client

只使用 Python 标准库的 hk4e CLI（Python >=3.11），连接同一台机器的独立 Sophon Server。无需安装 HTTP/WebSocket 第三方库。CLI 本身不调用私服、不运行游戏，只管理资源下载和维护。

## 启动

在 `~/Projects/yaagl-build/sophon` 下，终端一：

```sh
python3 run-client.py serve
```

需要 uv；首次运行会按服务端锁文件安装依赖。也可直接：

```sh
cd sophon-server
uv run --locked python src/server.py
```

终端二使用 `python3 run-client.py ...`。Windows 将 python3 换成 python。
如需安装命令入口：`python -m pip install -e ./sophon-client`，然后用 `sophon-client ...`。
安装非 editable wheel 时，可用 `sophon-client serve --server-dir /path/to/sophon-server` 明确指定服务端源码目录。

默认服务 `http://127.0.0.1:8000`；`--server` 或 `SOPHON_SERVER_URL` 可覆盖。只接受本机地址，因为下载路径由服务端本机解释。默认登记文件 `~/.sophon/registry.json`，可用 `--registry` 或 `SOPHON_REGISTRY` 覆盖。全局选项放在子命令前。

## 历史版本和指定文件

以下示例在根目录执行；Windows 可将目录参数换成 `C:\Games\hk4e-4.5`，清单内文件路径仍使用 `/`。

```sh
# 查询指定历史版本是否仍有官方清单；可重复 --version
python3 run-client.py versions --region os --version 4.5.0 --version 5.0.0

# 探测范围内 major.minor.0 候选，不是完整历史目录
python3 run-client.py versions --region os --scan 4.5.0 5.6.0

# 查文件名，支持通配筛选和分页
python3 run-client.py files --region os --version 4.5.0 --pattern '*data_revision' --limit 100 --offset 0

# 登记独立历史目录；登记本身不下载、不改写游戏内容
python3 run-client.py register hk4e-45 ./games/hk4e-45 --region os --version 4.5.0

# 任意指定文件：使用 files 输出中的精确相对路径；可重复 --file
python3 run-client.py download hk4e-45 --version 4.5.0 \
  --file GenshinImpact_Data/StreamingAssets/AssetBundles/data_revision

# 语音文件需选择对应分类
python3 run-client.py files --version 4.5.0 --category en-us --pattern '*.pck'
```

download 只处理精确匹配的文件，不下载整包、不更新完整安装的版本号。历史版本只要官方仍提供清单和 chunk 就可请求；不存在或已下线的版本/文件会报错。不会回退到最新版本。Sophon 没有覆盖已验证的所有早期历史版本，详见API 文档。

## 完整安装、更新、检查和修复

使用另一专用目录保存完整安装（不要把已下载零散文件的目录当作空目录安装）：

```sh
python3 run-client.py register full-45 ./games/full-45 --region os --version 4.5.0
python3 run-client.py install full-45
# 可额外指定语音分类，例如 --category game --category zh-cn

# 更新到当前最新版本，默认使用完整 chunk 清单同步，跳过已匹配文件
python3 run-client.py update full-45

# 指定目标历史版本；低于当前版本时需明确允许降级
python3 run-client.py sync full-45 --version 5.0.0
python3 run-client.py sync full-45 --version 4.5.0 --allow-downgrade

# 默认按 config.ini 已安装版本或登记版本检查，不隐式升级历史安装
python3 run-client.py check full-45
python3 run-client.py check full-45 --mode quick
python3 run-client.py repair full-45

# 只检查/修复指定文件
python3 run-client.py check hk4e-45 --version 4.5.0 \
  --file GenshinImpact_Data/StreamingAssets/AssetBundles/data_revision
```

默认 reliable 校验大小和 MD5；quick 只检查大小。check 不下载游戏内容或改写游戏文件，但会生成清单缓存。repair 会修复异常文件。检查发现异常退出码为 2；任务/网络/业务失败为 1；取消为 130；成功为 0（参数解析错误也可能为 2）。

默认 update 使用完整清单以支持跨度较大的历史安装；`update NAME --version X` 等价于向 X 同步。明确指定 `update NAME --incremental` 可使用原 ldiff 增量接口，只适用于上游支持的起始版本，需要 hpatchz，不支持 bb。`predownload NAME` 使用原预下载接口，需完整安装且符合原接口的版本/渠道限制。

完整安装中断后可重新执行同一版本 install。sync/下载中断后重新提交同一目标可复用正确文件和 chunk 缓存。完整同步不是整个目录的原子事务；失败前部分文件可能已替换，最终版本号只在成功后提交。

## 目录与任务管理

```sh
python3 run-client.py list
python3 run-client.py jobs
python3 run-client.py forget hk4e-45  # 只移除登记，不删除文件

python3 run-client.py download hk4e-45 --version 4.5.0 --file 'path/from/files' --detach
python3 run-client.py status TASK_ID
python3 run-client.py watch TASK_ID
python3 run-client.py pause TASK_ID
python3 run-client.py resume TASK_ID
python3 run-client.py cancel TASK_ID
python3 run-client.py limit 1048576
```

支持 `--limit`（bytes/s，0 不限速）、`--tempdir`（专用缓存目录）。CLI 默认等待完成；等待新任务时 Ctrl+C 请求取消。`watch` 的 Ctrl+C 只退出观察，任务继续。`--detach` 后可退出 CLI，任务由服务端继续；服务端需要保持运行。任务 ID 重启后失效，登记文件中的 jobs 是最后观察到的记录；watch 终态会更新登记快照。

游戏目录登记不允许重叠。登记文件短暂使用锁并原子替换，损坏文件不会自动覆盖。客户端崩溃遗留的 registry.lock 需要确认旧客户端已退出后手工移除。

使用 `--json` 输出 JSON 或 JSON Lines，包含完整检查结果：

```sh
python3 run-client.py --json check full-45
python3 run-client.py --json status TASK_ID
```

## 文档与验证

- 根目录 `SOPHON_SERVER_API.zh-CN.md`：完整现行 API，包含历史接口和状态字段。
- 根目录 README：测试与构建命令。
