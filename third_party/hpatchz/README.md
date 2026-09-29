# hpatchz 原生程序

Windows x64 (`win32/x64/hpatchz.exe`) 和 Linux x64 (`linux/x64/hpatchz`) 来自 [HDiffPatch v5.1.3 官方发布](https://github.com/sisong/HDiffPatch/releases/tag/v5.1.3)，保留原始二进制。Linux 程序为静态链接 ELF，目标系统 Linux 内核 3.2.0 或更新。Windows 程序为 PE32+ x86-64；官方包没有随附 DLL。

`manifest.json` 记录下载地址、已验证的官方压缩包 SHA-256，以及提取后程序的 SHA-256。`LICENSE.txt` 为该版本上游许可证；原有 macOS arm64/x64 程序保留。

根目录构建脚本按当前系统和架构自动选择程序并复制到服务端分发目录。源码运行也使用这些路径。可用 `--hpatchz`（构建）或 `SOPHON_HPATCHZ` 覆盖；其他平台/架构需自行提供。当前 macOS 环境仅验证 Windows/Linux 文件格式与平台路径，未执行这两个程序。
