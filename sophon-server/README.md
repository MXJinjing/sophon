# Sophon Server

独立 FastAPI 服务端，保留原 uv + protoc 31.1 + Nuitka 构建方式和旧接口。

- `src/`：入口 server.py、下载器、任务和生成的 protobuf Python 模块。
- `proto/`：protobuf schemas。
- `tests/`：原有和历史扩展测试。
- `pyproject.toml` / `uv.lock`：原依赖和锁文件；`.python-version` 使用平台无关 Python 3.13。
- 构建脚本、API 文档、源代码启动器位于仓库根目录；原生 helper 位于根目录 third_party/hpatchz/。

本目录内启动：`uv run --locked python src/server.py`。
仓库根目录内启动：`uv run --project sophon-server --locked python run-server.py`。
默认监听 127.0.0.1:8000，支持 SOPHON_HOST、SOPHON_PORT、TERMINATE_WITH_PID。

仓库根目录内构建：

```sh
./build-sophon.sh --hpatchz /absolute/path/to/hpatchz
python build.py --platform linux --arch x64 --plan
python build.py --platform win32 --arch x64 --plan
python build.py --generate-only
```

Windows PowerShell：`.\build-sophon.ps1 --hpatchz C:\tools\hpatchz.exe`。
SOPHON_ARCH、SOPHON_PYTHON、SOPHON_HPATCHZ 或对应参数仍支持。
实际构建要求本机系统/架构与选定 Python 相符；--plan 只生成配置。
产物为根目录 build/<platform>-<arch>/server.dist/，需要分发整个目录。
protoc 下载到根目录 .cache/protoc/，生成代码写回 src/。
Linux/Windows 原生编译尚未实际运行；目标系统需原生 hpatchz 和 C 编译器。
源码运行的历史 chunk 操作不依赖 hpatchz，旧增量接口需要它。

完整 API 说明见根目录 SOPHON_SERVER_API.zh-CN.md。
按需测试：根目录 `uv run --project sophon-server --locked python test.py --component server`。
