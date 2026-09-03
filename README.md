# MaaAgentCoreAndroid

在 Android 上跑 MaaFramework Python agent 所需的预构建内核

内核跟具体项目无关，只跟 `(CPython 版本, ABI, MaaFramework 版本)` 绑定

## 下载

见 [Releases](../../releases)：

| 资产 | ABI |
|---|---|
| `agent-core-3.13.15-arm64-v8a.tar.gz` | arm64-v8a |
| `agent-core-3.13.15-x86_64.tar.gz` | x86_64 |

Release 包的组成和生产流程见 [RELEASE_PROCESS.md](RELEASE_PROCESS.md)。

## 手动构建

在 GitHub Actions 中运行 `Release agent core` 工作流，手动输入稳定的
CPython `3.x.y` 版本和 MaaFramework 版本。MaaFramework 使用 PyPI 的规范
版本号；为方便输入，`-beta.x` 会被规范化为 `bx`，例如
`5.13.0-beta.1` 会按 `5.13.0b1` 下载、写入 manifest 并生成
`3.13.15-maafw5.13.0b1` tag。

CI 会编译两个 Android ABI、执行静态验收、生成确定性归档并上传 draft
release。静态验收不包含 Android 真机冒烟；发布前必须提供匹配版本的
MaaFramework 原生库并完成真机测试。


## 许可

包内保留 CPython 标准库自带许可，以及 numpy/StrEnum dist-info 中的许可：

| 组件 | 许可 |
|---|---|
| CPython 3.13.15 | PSF License |
| MaaFramework | LGPL-3.0 |
| numpy | BSD-3-Clause |
| StrEnum | MIT |

`maa` 只收录 Python 源码（仅打一处 Android 平台名补丁，见
[PEP 738](https://peps.python.org/pep-0738/)），不复制 wheel 的 dist-info、
原生库和许可文件；MaaFramework 原生库由宿主分发，需同时提供对应许可。
