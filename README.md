# MaaAgentCoreAndroid

在 Android 上跑 MaaFramework Python agent 所需的预构建内核

内核跟具体项目无关，只跟 `(CPython 版本, ABI, MaaFramework 版本)` 绑定

## 下载

见对应 [Actions](../../actions) run 的 Artifacts：

| 资产 | ABI |
|---|---|
| `agent-core-3.13.15-arm64-v8a.tar.gz` | arm64-v8a |
| `agent-core-3.13.15-x86_64.tar.gz` | x86_64 |

构建包的组成和生产流程见 [RELEASE_PROCESS.md](RELEASE_PROCESS.md)。

## 自动构建

自动构建指在 GitHub Actions 中运行 `Build agent core` 工作流。可以直接在
GitHub 网页的 Actions 页面启动，也可以在本地通过 GitHub CLI 触发；构建
过程仍由 GitHub Actions runner 执行。

手动输入稳定的 CPython `3.x.y` 版本和 MaaFramework 版本。MaaFramework
使用 PyPI 的规范版本号；为方便输入，`-beta.x` 会被规范化为 `bx`，例如
`5.13.0-beta.1` 会按 `5.13.0b1` 下载、写入 manifest 并生成
`agent-core-3.13.15-maafw5.13.0b1` artifact。

也可以从仓库检出目录用 GitHub CLI 触发：

```bash
gh workflow run release.yml \
  --ref main \
  -f python-version=3.13.15 \
  -f maafw-version=5.13.0-beta.1
```

用 `gh run list --workflow release.yml --limit 1` 找到 run ID，再从该 run
的 Artifacts 区域下载产物。artifact 是外层 ZIP，解开后才是两个 `.tar.gz`、
`SHA256SUMS`、`build-metadata.json` 和 `build-report.md`。

CI 会编译两个 Android ABI、执行静态验收、生成确定性归档并上传 Actions
artifact，不会创建 GitHub Release 或 tag；默认保留 30 天。静态验收不包含
Android 真机冒烟；对外使用前必须提供匹配版本的
MaaFramework 原生库并完成真机测试。

## 手动构建（可选）

如需在本机复现发布归档，可在准备 Android SDK、JDK 和 `ANDROID_HOME` 后，
从仓库检出目录运行 `scripts/build_agent_core.py`。脚本会显式固定并校验
Android NDK `28.2.13676358`。这只是建议流程，不是日常开发或贡献的前置
要求；完整步骤见 [RELEASE_PROCESS.md](RELEASE_PROCESS.md) 第 2 节。

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
