# Sophon

目录布局：

```text
sophon/
  build.py / build-sophon.sh / build-sophon.ps1 / build-client.py
  run-client.py / run-server.py / test.py
  SOPHON_SERVER_API.zh-CN.md
  sophon-client/
    pyproject.toml / uv.lock / README.md
    src/sophon_client/
    tests/
  sophon-server/
    pyproject.toml / uv.lock / README.md
    src/
    proto/
    tests/
  third_party/hpatchz/
  docs/build-sophon.original.sh.txt
```

客户端和服务端源码、测试分离；所有构建脚本集中在根目录。旧构建脚本作为非可执行文档归档，uv + protoc + Nuitka 构建方式保持不变。build/、dist/、环境、缓存和下载内容不提交。

原 `~/Projects/yaagl-build/sophon-server` 已移动到 `sophon/sophon-server`。原启动器仓库的 Python 源码未修改；根目录统一 API 文档描述独立服务端当前实现。独立服务端增加 hk4e 历史清单、指定文件、完整同步、只检查和定版本修复接口；CLI 只支持 hk4e，合法旧接口仍保留。

## 使用

根目录内：

```sh
# 终端一：前台启动服务端
python3 run-client.py serve

# 终端二：查看帮助和历史版本
python3 run-client.py --help
python3 run-client.py versions --region os --version 4.5.0
python3 run-client.py files --version 4.5.0 --pattern '*data_revision'

# 专用历史目录、按精确文件路径下载
python3 run-client.py register hk4e-45 ./games/hk4e-45 --region os --version 4.5.0
python3 run-client.py download hk4e-45 \
  --file GenshinImpact_Data/StreamingAssets/AssetBundles/data_revision
```

Windows 使用 `python`，其他参数一致。也可以直接用 `uv run --project sophon-server --locked python run-server.py` 启动服务端。CLI 无第三方运行依赖；服务端需要 uv 和 Python >=3.11，默认 Python 3.13。详情见 `sophon-client/README.md`。

历史资源取决于官方仍提供清单和 chunk，无法保证任意已下线版本可恢复。源码整理前已验证 os/cn 的 4.5.0、5.0.0、5.6.0 元数据；实际下载、校验、只检查和修复过 os 4.5.0 的一个文件。探测的 os 1.0.0、3.0.0、4.0.0 无可用 Sophon 清单。

## 构建

保留 uv + 固定 protoc 31.1 + Nuitka standalone 流程。在仓库根目录内：

```sh
./build-sophon.sh --hpatchz /absolute/path/to/hpatchz
python build.py --platform linux --arch x64 --plan
python build.py --platform win32 --arch x64 --plan
```

Windows PowerShell：`.\build-sophon.ps1 --hpatchz C:\tools\hpatchz.exe`。
Linux/Windows 需目标系统原生 hpatchz 和编译器；现有 macOS arm64/x64 helper 和许可保留在 third_party/hpatchz/。新历史 chunk 操作源码运行无需 hpatchz，但保留旧增量接口的完整打包仍要求提供它。未实际运行 Linux/Windows 原生编译。

客户端可直接源码运行，也可安装：`python -m pip install -e ./sophon-client`。发布 Python 包：`python3 build-client.py`。

## 测试

根目录内：

```sh
uv run --project sophon-server --locked python test.py --component server
uv run --project sophon-server --locked python test.py --component client
```

以上命令仅在需要时手工运行，不会由构建入口自动执行。可附加 `--pattern test_build_platforms.py` 等参数只选择一个测试文件。

测试使用小型本地 HTTP fixture，不下载整款游戏。包括原有任务/限速/完整性测试、版本严格匹配、按文件下载、修复、只检查、更新/降级、失败不提交版本号、中断重试、路径安全、登记文件和 CLI 任务控制。

测试依赖来自服务端已有锁文件，测试本身不额外要求 httpx 或 WebSocket 客户端包。运行前确保选用服务端 uv 环境。

服务端产物位于 `build/<platform>-<arch>/server.dist/`，应分发整个目录；客户端 sdist/wheel 位于 `dist/`。源码目录变化后旧的原生二进制需要重新构建。
