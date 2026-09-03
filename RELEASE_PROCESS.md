# Release 包生产流程

本文说明 `MaaAgentCoreAndroid` release 资产的组成、生产步骤和验收标准。当前仓库没有 checked-in 的构建脚本或 GitHub Actions，因此本文分为两类内容：

- **已确认**：来自已发布包、wheel 元数据和下游消费脚本的实物事实。
- **生产规范**：后续制作同类 release 时应执行的流程。该流程是从当前包反推并整理出来的，不能表述为当前 release 已经由仓库内自动化生成。

## 1. Release 命名与版本矩阵

当前 release：

| 项目 | 值 |
|---|---|
| Tag | `3.13.15-maafw5.12.3` |
| 标题 | `CPython 3.13.15 / MaaFramework 5.12.3` |
| Python | `3.13.15` |
| Python ABI tag | `cp313` |
| MaaFramework Python binding | `5.12.3` |
| numpy | `2.3.2` |
| StrEnum | `0.4.15` |
| Android ABI | `arm64-v8a`, `x86_64` |
| 接受的 Android wheel API level | `24`, `21`, `16` |

资产命名固定为：

```text
agent-core-<python-version>-<android-abi>.tar.gz
```

当前两个资产为：

| 资产 | 大小 | SHA-256 |
|---|---:|---|
| `agent-core-3.13.15-arm64-v8a.tar.gz` | `19933789` | `ae8dda833f5d5975f2cb667d8c154fde196397734e3152282f5bcf591a468941` |
| `agent-core-3.13.15-x86_64.tar.gz` | `22666262` | `1ee7deca52acb1046f6f7593e5a85f07770bd708353f0fd24d9ad47c599ea8f2` |

各 ABI 的 wheel 信息为：

| `abi` | `wheelAbi` | CPython host triple | pip platform 后缀 |
|---|---|---|---|
| `arm64-v8a` | `arm64_v8a` | `aarch64-linux-android` | `arm64_v8a` |
| `x86_64` | `x86_64` | `x86_64-linux-android` | `x86_64` |

## 2. 包内容契约

归档必须以 ABI 目录开头，且路径精确为：

```text
<abi>/bundle/
  agent-core.json
  bin/
    python3
  prefix/
    lib/
      libpython3.13.so
      libpython3.so
      libcrypto.so
      libcrypto_python.so
      libssl.so
      libssl_python.so
      libsqlite3.so
      libsqlite3.so.0
      libsqlite3_python.so
      engines-3/
      ossl-modules/
      python3.13/
      python313.zip
  site-packages/
    maa/
    numpy/
    numpy.libs/
    strenum/
    numpy-2.3.2.dist-info/
    StrEnum-0.4.15.dist-info/
```

`prefix/` 是 Android CPython 运行时，`site-packages/` 是内核预置的第三方包。下游项目会把额外依赖继续安装到同一个 `site-packages/` 目录，因此这些路径是兼容性契约，不能重排。

`agent-core.json` 的字段固定。两个 ABI 只有 `abi` 和 `wheelAbi` 不同：

```json
{
  "python": "3.13.15",
  "pyAbiTag": "cp313",
  "wheelApis": [24, 21, 16],
  "abi": "arm64-v8a",
  "wheelAbi": "arm64_v8a",
  "provides": {
    "numpy": "2.3.2",
    "strenum": "0.4.15",
    "maafw": "5.12.3"
  }
}
```

字段含义：

| 字段 | 用途 |
|---|---|
| `python` | 运行时 CPython 版本，也用于生成 pip 的 `--python-version` |
| `pyAbiTag` | 运行时 ABI，传给 pip 的 `--abi` |
| `wheelApis` | 依次生成多个精确的 `android_<api>_<wheelAbi>` platform |
| `abi` | 归档内目录名和 Android ABI |
| `wheelAbi` | Android wheel 文件名中的 ABI 后缀 |
| `provides` | 内核已经提供的包及版本；下游应按 PEP 503 规范化包名后跳过这些依赖 |

当前包不含 MaaFramework 的 `libMaa*.so`。`maa/` 只包含 Python binding 源码；原生库必须由 Android 宿主 App 或运行环境提供，并且版本必须与 `provides.maafw` 匹配。

## 3. 输入材料与固定版本

每次生产前先建立材料目录，并记录所有输入的 SHA-256。不要在构建过程中让 pip、CPython Android 脚本或依赖下载步骤自行选择新版本。

### 3.1 CPython 源码

用于完整重建运行时：

```text
https://www.python.org/ftp/python/3.13.15/Python-3.13.15.tgz
```

SHA-256：

```text
c28d9d213c09b5b5ab2c29812950e12f746999e099b82894231be954b26baed9
```

CPython 3.13 起 Android 构建走官方 `Android/android.py` 流程。构建机器需要 Android SDK、NDK、JDK 17/21/25、`curl`、`java`，以及构建本机 Python 所需的编译工具。可在 Linux 或 macOS 上交叉构建。

### 3.2 Python 依赖 wheel

numpy 使用 Chaquopy Android wheel index：

```text
https://chaquo.com/pypi-upstream/
```

固定输入为：

| 文件 | SHA-256 |
|---|---|
| `numpy-2.3.2-1-cp313-cp313-android_24_arm64_v8a.whl` | `f7beb51f8d162c110ee8d4c9e275f490ce39dddba919643d949687bb4286bedd` |
| `numpy-2.3.2-1-cp313-cp313-android_24_x86_64.whl` | `17e5ffa985ad510831654610c9ab1558f031875379d1a18a0439d4cee1126705` |
| `StrEnum-0.4.15-py3-none-any.whl` | `a30cda4af7cc6b5bf52c8055bc4bf4b2b6b14a93b574626da33df53cf7740659` |

### 3.3 Maa Python binding

当前包的 `maa/*.py` 与 PyPI `maafw==5.12.3` wheel 内的 Python 源码一致，只有 `maa/library.py` 带 Android 平台名补丁。生产时选择一个 PyPI wheel 作为源材料并固定哈希。本轮核对使用：

```text
maafw-5.12.3-py3-none-manylinux2014_aarch64.whl
```

SHA-256：

```text
6c2c6af0f99508d0cce13d2c041f10813576158eb567a68225d908fffb34897f
```

这里只使用 wheel 里的纯 Python 文件；wheel 自带的 Linux 原生库不进入本包。

## 4. 工作目录与准备

每个 ABI 单独 staging，最终只把 `<abi>/bundle` 写入归档：

```text
work/
  inputs/
  stage/
    arm64-v8a/
      bundle/
        agent-core.json
        bin/
        prefix/
        site-packages/
    x86_64/
      bundle/
        agent-core.json
        bin/
        prefix/
        site-packages/
  dist/
```

建议每次从空目录开始。复用缓存时必须验证输入哈希，并删除旧 `stage/` 与旧 `dist/`，避免上一个 ABI 的 `.so`、dist-info 或 manifest 混入新包。

## 5. 生成 CPython 运行时

### 5.1 完整重建

当前包的运行时布局、Android wheel 生态和 launcher 形态与 Chaquopy 生态使用的 CPython Android 产物兼容；Chaquopy 的公开 target 脚本也是使用 CPython 3.13 的官方 `Android/android.py` 流程构建 `arm64-v8a` 与 `x86_64`。但这只能说明技术路线一致，不能证明当前二进制来自哪个 Chaquopy Maven 版本或 build 编号。在仓库记录精确来源之前，不应做更强的溯源声明。

相关参考：

- Chaquopy target 构建脚本：<https://github.com/chaquo/chaquopy/tree/master/target>
- Python target 构建：<https://github.com/chaquo/chaquopy/blob/master/target/python/build.sh>
- 批量构建与打包：<https://github.com/chaquo/chaquopy/blob/master/target/python/build-and-package.sh>

以 `arm64-v8a` 为例，CPython 官方流程是：

```bash
cd Python-3.13.15/Android
./android.py build aarch64-linux-android
```

`x86_64` 使用：

```bash
cd Python-3.13.15/Android
./android.py build x86_64-linux-android
```

构建产物位于源码树的 `cross-build/<host>/prefix/`。将该目录复制为：

```text
stage/<abi>/bundle/prefix/
```

需要保留的内容包括：

- `lib/libpython3.13.so` 和 `lib/libpython3.so`
- Python 扩展模块和标准库数据所在的 `lib/python3.13/`
- 压缩标准库 `lib/python313.zip`
- OpenSSL、SQLite 及其 engine/module 目录

不应带入：

- `include/`
- `lib/pkgconfig/`
- 构建目录、对象文件、下载缓存
- pip/ensurepip 的可引导安装内容
- `__pycache__`

`bundle/bin/python3` 是一个 Android PIE 可执行文件，入口实现只调用 `Py_BytesMain`。它必须使用 `/system/bin/linker64` 作为 ELF interpreter，并动态链接 `libpython3.13.so`。后续生产应把这份 launcher 的源码或固定二进制来源放入仓库；没有这个输入就无法完整重建当前包。

当前已发布包没有记录 launcher 的原始源码和确切构建命令。产物元数据显示 launcher 由 Android NDK `r29-beta2` / Clang 20 构建，而 `libpython3.13.so` 中可见 NDK `r27d` 标记；这说明当前包不是一次完整、可追溯的单工具链构建。

### 5.2 运行时不变时的复用

如果只更新 `maa`、numpy、StrEnum 或 manifest，而 CPython 运行时保持不变，可以先下载上一版已验证 release，校验 SHA-256 后：

1. 解包到干净目录。
2. 只保留对应 ABI 的 `bundle/bin/` 与 `bundle/prefix/`。
3. 删除并重建 `bundle/site-packages/`。
4. 重新生成 `bundle/agent-core.json`。

这种方式可以避免临时重造运行时，但它不是完整生产方案；Python、NDK、依赖库或 launcher 任一变化时仍必须完整重建并重新做真机验收。

## 6. 安装预置 Python 包

对每个 ABI 执行 pip 的目标目录安装。pip 只做 wheel 文件名 tag 匹配，不在 Android 上执行 setup/build，因此必须使用 `--only-binary=:all:` 并列出精确 platform。

`arm64-v8a`：

```bash
python3 -m pip install \
  --target stage/arm64-v8a/bundle/site-packages \
  --only-binary=:all: \
  --python-version 3.13 \
  --implementation cp \
  --abi cp313 \
  --platform android_24_arm64_v8a \
  --platform android_21_arm64_v8a \
  --platform android_16_arm64_v8a \
  --extra-index-url https://chaquo.com/pypi-upstream/ \
  numpy==2.3.2 StrEnum==0.4.15
```

`x86_64`：

```bash
python3 -m pip install \
  --target stage/x86_64/bundle/site-packages \
  --only-binary=:all: \
  --python-version 3.13 \
  --implementation cp \
  --abi cp313 \
  --platform android_24_x86_64 \
  --platform android_21_x86_64 \
  --platform android_16_x86_64 \
  --extra-index-url https://chaquo.com/pypi-upstream/ \
  numpy==2.3.2 StrEnum==0.4.15
```

`wheelApis` 顺序保留为 `[24, 21, 16]`。Android platform tag 没有类似 manylinux 的自动兼容阶梯；只给一个 API level 会拒掉其它合法 tag，例如只给 `android_24` 时无法选中 `android_21` wheel。

安装后检查：

- `numpy-2.3.2.dist-info/WHEEL` 中的 tag 是当前 ABI 的 `cp313-cp313-android_24_<wheelAbi>`。
- StrEnum 是 `py3-none-any`。
- `numpy.libs/` 中的 `libc++_shared`、`libgfortran`、`libopenblas` 与 ABI 匹配。
- 清理所有 `__pycache__`，但保留 dist-info、license、RECORD 和类型标注文件。

## 7. 收录并补丁 `maa`

从固定的 `maafw` wheel 解出内容，只复制 `maa/` 目录到：

```text
stage/<abi>/bundle/site-packages/maa/
```

明确不要复制：

- `maafw-*.dist-info/`
- `maa/bin/`
- wheel 内任何 `libMaa*.so` 或其它平台原生库

然后给 `maa/library.py` 打 Android 平台名归一化补丁。逻辑是在：

```python
platform_type = platform.system().lower()
```

之后加入：

```python
if platform_type == "android":
    platform_type = LINUX
```

原因：PEP 738 之后，Android CPython 的 `platform.system()` 会返回 `Android`；上游 `maa` 只维护 `windows`、`darwin`、`linux` 三类库名。Android 使用的正是 Linux 风格的 `libMaa*.so` 名称，因此应归一为 `linux`。

验收标准：

- 除 `maa/library.py` 外，所有 `maa/**/*.py` 必须与源 wheel 中的对应文件逐字节一致。
- `site-packages/maa/bin/` 不存在。
- 包内不存在 `libMaaFramework.so`、`libMaaAgentClient.so`、`libMaaAgentServer.so`、`libMaaToolkit.so`。
- 补丁不改变 `maa` 的其它 API。

当前发布包中的 `maa/library.py` 是 CRLF 行尾；PyPI wheel 是 LF 行尾。后续重建时建议以 LF 源文件为基础，只提交上述最小逻辑差异，避免整文件行尾噪声。

## 8. 生成 manifest

manifest 必须由版本矩阵生成，不能手抄后留下旧值。使用 UTF-8、JSON、两个空格缩进，并在文件末尾保留一个换行。

核心数据：

```python
matrix = {
    "arm64-v8a": {
        "abi": "arm64-v8a",
        "wheelAbi": "arm64_v8a",
    },
    "x86_64": {
        "abi": "x86_64",
        "wheelAbi": "x86_64",
    },
}

common = {
    "python": "3.13.15",
    "pyAbiTag": "cp313",
    "wheelApis": [24, 21, 16],
    "provides": {
        "numpy": "2.3.2",
        "strenum": "0.4.15",
        "maafw": "5.12.3",
    },
}
```

对每个 ABI 合并 `common` 与对应的 `abi`、`wheelAbi`，写入：

```text
stage/<abi>/bundle/agent-core.json
```

版本变化时同步更新：

- release tag 和标题
- README 的资产表
- `common`
- 输入 wheel 文件名与哈希
- release notes 中的版本矩阵

## 9. 静态验收

打包前对每个 ABI 执行：

1. 从归档 staging 根检查，第一层必须只有 `<abi>`，下一层必须只有 `bundle`。
2. `bundle` 顶层只允许 `agent-core.json`、`bin`、`prefix`、`site-packages`。
3. JSON 可解析，字段值与版本矩阵一致。
4. `bin/python3` 是 Android PIE ELF，interpreter 为 `/system/bin/linker64`。
5. `prefix/lib/libpython3.13.so`、`lib-dynload/*.so`、numpy 扩展和 `numpy.libs/*.so` 的机器架构与 ABI 匹配。
6. 逐项确认不存在 MaaFramework 原生库、`maa/bin`、构建缓存、包管理器临时文件和 `__pycache__`。
7. 校验 dist-info `RECORD` 能覆盖已安装文件，license 文件仍存在。
8. 重新对比 `maa` 与源 wheel，确认只有 `library.py` 的目标补丁差异。

至少在两个真实 Android 设备或模拟器上分别覆盖两个 ABI。测试环境必须提供 MaaFramework `5.12.3` 的对应 Android 原生库。

真机冒烟内容：

```python
import json
import pathlib
import platform
import sys

import maa
import numpy as np
from strenum import StrEnum

bundle = pathlib.Path(__file__).resolve().parent
manifest = json.loads((bundle / "agent-core.json").read_text())

assert sys.version_info[:3] == (3, 13, 15)
assert manifest["python"] == "3.13.15"
assert np.arange(3).sum() == 3

class Color(StrEnum):
    RED = "red"

assert Color.RED == "red"
assert platform.system().lower() in {"android", "linux"}

# native_lib_dir 指向宿主 App 提供的 MaaFramework 5.12.3 Android .so 目录。
# maa.Library.open(native_lib_dir) 后，再执行项目侧 Agent 集成冒烟。
print(sys.version)
print(platform.machine(), manifest["abi"], np.__version__)
```

除了 import 和 numpy 计算外，还应执行一次实际 `maa.Library.open()` 和项目侧 agent 通信冒烟，确认平台名补丁和宿主原生库版本可用。

## 10. 打包

打包输入根目录是 `stage/`，归档内必须从 `<abi>/bundle/...` 开始，不能多出 `stage/`、`work/` 或绝对路径。

推荐使用固定元数据生成后续版本，例如固定时间戳、UID/GID 为 `0`、排序文件名，并对目录和可执行文件使用可执行位、普通文件使用读写位。Linux GNU tar 的示意命令如下：

```bash
(
  cd stage
  find arm64-v8a -print0 |
    LC_ALL=C sort -z |
    tar --null --no-recursion --files-from=- \
      --format=gnu \
      --sort=name \
      --mtime='@0' \
      --owner=0 --group=0 --numeric-owner \
      --mode='u+rwX,go+rX,go-w' \
      -cf - |
    gzip -n > ../dist/agent-core-3.13.15-arm64-v8a.tar.gz
)
```

`x86_64` 把命令中的两个 ABI 字符串替换为 `x86_64`。

生成后执行：

```bash
sha256sum dist/agent-core-3.13.15-arm64-v8a.tar.gz
sha256sum dist/agent-core-3.13.15-x86_64.tar.gz
tar -tzf dist/agent-core-3.13.15-arm64-v8a.tar.gz >/dev/null
tar -tzf dist/agent-core-3.13.15-x86_64.tar.gz >/dev/null
```

再解包到新的空目录，重复第 9 节静态验收。

打包前先做权限归一：目录 `0755`、`bin/python3` `0755`、普通文件 `0644`。如果运行时启动要求其它可执行位，必须在文档和验收清单中显式记录。

当前 `3.13.15-maafw5.12.3` 归档的 owner/group 已是 `0`，大部分 mode 被归一为目录 `0777`、文件 `0666`，但不同生成阶段的 mtime 不一致，且未固定 gzip 元数据。因此它不能被描述为 byte-for-byte reproducible。上述固定元数据流程是后续版本的规范；它不会逐字节复现当前资产。

## 11. 发布 GitHub Release

所有静态与真机验收通过后再创建 tag。建议流程：

1. 确认 `main` 上 README 和本文中的版本、hash、链接已经更新。
2. 创建 tag：`3.13.15-maafw5.12.3`。
3. 创建 draft release，标题使用 `CPython 3.13.15 / MaaFramework 5.12.3`。
4. 上传两个 `.tar.gz` 资产。
5. 在 release notes 中记录版本矩阵、输入来源、最终 SHA-256 和已测 Android 环境。
6. 从 GitHub 下载 URL 重新下载资产，校验 SHA-256 与本地产物一致。
7. 发布 release。
8. 发布后用下游打包脚本走一次完整消费，确认新 release URL、manifest、site-packages 叠加安装都可用。

Release notes 不应声称包含 MaaFramework 原生库。若宿主所需的 MaaFramework Android 包有独立发布地址，应链接到对应的 `5.12.3` release。

## 12. 下游兼容规则

下游消费这个内核时应遵守：

1. 解包后直接使用 `<abi>/bundle` 作为 agent runtime 根目录。
2. 额外依赖安装到 `bundle/site-packages`，不要另建 Python 环境。
3. 从 `agent-core.json` 读取 Python 版本、ABI、`pyAbiTag`、`wheelApis`、`wheelAbi` 和 `provides`。
4. 生成 pip platform 时按顺序展开 `wheelApis`，格式为 `android_<api>_<wheelAbi>`。
5. 用 PEP 503 规则规范化依赖名；命中 `provides` 的包不要重复安装，即使项目 pin 了不同版本。
6. `maaagentbinary` 是桌面端可执行包，Android 上应依赖宿主 `nativeLibraryDir` 或等价路径，不安装该包。
7. MaaFramework 原生库由宿主提供，版本必须与 manifest 的 `maafw` 匹配。
8. 更新任何二进制输入都必须发新 release 和新资产，不能覆盖已上传资产。

## 13. 当前限制与待固化事项

已确认的限制：

- 仓库内没有生产脚本、GitHub Actions 或完整输入锁定文件。
- 当前 release 的 CPython launcher 源码和确切构建环境未入库。
- 当前包的二进制元数据显示 launcher 与 `libpython3.13.so` 来自不同 NDK 版本，精确构建来源不可追溯。
- 当前归档元数据不完全确定，不能宣称 byte-for-byte 可复现。
- 包内没有 MaaFramework 原生库，真机测试必须准备宿主侧 native 库。
- Android CPython 运行时未包含 `_multiprocessing`；需要该 API 的下游项目必须自行提供兼容 shim 或避免跨进程语义。

后续固化建议：

1. 把 launcher 源码、Python 构建参数、NDK 版本和所有输入哈希加入仓库。
2. 用脚本实现 staging、wheel 安装、`maa` 补丁、manifest 生成、验收和确定性打包。
3. 为两个 ABI 添加 GitHub Actions 构建，并把构建日志哈希写入 release notes。
4. 保留上一版到下一版的二进制对比报告，区分运行时变更与 site-packages 变更。
