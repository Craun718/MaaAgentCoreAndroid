# Release 包生产流程

本文说明 `MaaAgentCoreAndroid` release 资产的组成、生产步骤和验收标准。当前仓库包含 `scripts/build_agent_core.py` 生产脚本和手动触发的 `Release agent core` GitHub Actions 工作流，因此本文分为两类内容：

- **已确认**：来自已发布包、wheel 元数据和下游消费脚本的实物事实。
- **生产规范**：手动 CI 和 `scripts/build_agent_core.py` 执行的流程。旧 release 在这些脚本入库前发布，不能表述为由当前自动化生成。

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

手动 CI 的 MaaFramework 输入使用 PyPI 规范版本号。为兼容常见的
`-beta.x` 写法，脚本先把它规范化为 `bx`，后续 wheel 查询、manifest、
release tag 和 prerelease 标记都使用规范化结果：

| 手动输入 | 规范化版本 | Release tag 后缀 |
|---|---|---|
| `5.12.3` | `5.12.3` | `maafw5.12.3` |
| `5.13.0-beta.1` | `5.13.0b1` | `maafw5.13.0b1` |
| `5.13.0b6` | `5.13.0b6` | `maafw5.13.0b6` |

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

手动 CI 中 Python 和 MaaFramework 版本来自 workflow 输入；numpy/StrEnum
版本由脚本固定。构建产出的 `build-metadata.json` 会记录实际下载的 Python
源码包、maafw wheel 和 runtime wheel SHA-256。

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

手动 CI 调用：

```bash
python scripts/build_agent_core.py \
  --python-version 3.13.15 \
  --maafw-version 5.13.0-beta.1 \
  --work-dir "$AGENT_CORE_WORK_DIR"
```

## 5. 生成 CPython 运行时

### 5.1 完整重建

当前包的运行时布局、Android wheel 生态和 launcher 形态与 Chaquopy 生态使用的 CPython Android 产物兼容；Chaquopy 的公开 target 脚本也是使用 CPython 3.13 的官方 `Android/android.py` 流程构建 `arm64-v8a` 与 `x86_64`。但这只能说明技术路线一致，不能证明当前二进制来自哪个 Chaquopy Maven 版本或 build 编号。在仓库记录精确来源之前，不应做更强的溯源声明。

相关参考：

- Chaquopy target 构建脚本：<https://github.com/chaquo/chaquopy/tree/master/target>
- Python target 构建：<https://github.com/chaquo/chaquopy/blob/master/target/python/build.sh>
- 批量构建与打包：<https://github.com/chaquo/chaquopy/blob/master/target/python/build-and-package.sh>

以 `arm64-v8a` 为例，CPython 官方流程必须把子命令放在全局选项前：

```bash
cd Python-3.13.15/Android
python android.py configure-build --clean --cross-build-dir "$WORK/cross-build"
python android.py make-build --cross-build-dir "$WORK/cross-build"
python android.py pythoninfo-build --cross-build-dir "$WORK/cross-build"
python android.py configure-host --clean aarch64-linux-android --cross-build-dir "$WORK/cross-build"
python android.py make-host aarch64-linux-android --cross-build-dir "$WORK/cross-build"
```

`x86_64` 把最后两条命令中的 host triplet 替换为 `x86_64-linux-android`。
生产脚本按上述顺序执行，并同时构建两个 ABI。

构建产物位于指定的 `cross-build/<host>/prefix/`。将该目录复制为：

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

`bundle/bin/python3` 是一个 Android PIE 可执行文件，入口实现只调用 `Py_BytesMain`。它必须使用 `/system/bin/linker64` 作为 ELF interpreter，并动态链接 `libpython3.13.so`。新生产的 launcher 源码位于 `scripts/launcher.c`，并由构建脚本使用对应 ABI 的 CPython Android 工具链编译。

当前已发布包没有记录 launcher 的原始源码和确切构建命令。产物元数据显示 launcher 由 Android NDK `r29-beta2` / Clang 20 构建，而 `libpython3.13.so` 中可见 NDK `r27d` 标记；这说明当前包不是一次完整、可追溯的单工具链构建。

### 5.2 运行时不变时的复用

如果只更新 `maa`、numpy、StrEnum 或 manifest，而 CPython 运行时保持不变，可以先下载上一版已验证 release，校验 SHA-256 后：

1. 解包到干净目录。
2. 只保留对应 ABI 的 `bundle/bin/` 与 `bundle/prefix/`。
3. 删除并重建 `bundle/site-packages/`。
4. 重新生成 `bundle/agent-core.json`。

这种方式可以避免临时重造运行时，但它不是完整生产方案；Python、NDK、依赖库或 launcher 任一变化时仍必须完整重建并重新做真机验收。

## 6. 安装预置 Python 包

对每个 ABI 执行 pip 的目标目录安装。pip 只做 wheel 文件名 tag 匹配，不在 Android 上执行 setup/build，因此必须使用 `--only-binary=:all:` 并列出精确 platform。预置包的依赖集合是固定的，安装时应使用 `--no-deps`；发现缺失依赖时更新版本矩阵和输入清单，而不是让 pip 自动选择新包。

还必须使用 `--no-compile`。否则 pip 会用宿主机 Python 生成错误 ABI 的 `.pyc`，并把它们写入 `RECORD`；这些字节码不能在 Android 运行时使用。

`arm64-v8a`：

```bash
python3 -m pip install \
  --target stage/arm64-v8a/bundle/site-packages \
  --only-binary=:all: \
  --no-deps \
  --no-compile \
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
  --no-deps \
  --no-compile \
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

安装后按当前包契约裁剪 site-packages：

```bash
rm -rf \
  stage/<abi>/bundle/site-packages/bin \
  stage/<abi>/bundle/site-packages/numpy/f2py \
  stage/<abi>/bundle/site-packages/numpy/_pyinstaller

find stage/<abi>/bundle/site-packages/numpy \
  -type d -name tests -prune -exec rm -rf {} +

find stage/<abi>/bundle/site-packages \
  -type d -name __pycache__ -prune -exec rm -rf {} +

find stage/<abi>/bundle/site-packages \
  -type f -name '*.pyc' -delete
```

不要把 `numpy/testing/` 当成 `tests/` 删除；`numpy.testing` 是运行时公开 API。`bin/`、`f2py`、`_pyinstaller` 和各级 `tests/` 不属于本内核的运行时契约。

裁剪后必须重新生成 numpy 和 StrEnum 的 `RECORD`。`RECORD` 要覆盖包拥有的每个实际文件，同时不得引用已删除文件。以 `arm64-v8a` 为例：

```python
import base64
import csv
import hashlib
from pathlib import Path

site_packages = Path("stage/arm64-v8a/bundle/site-packages")
packages = {
    "numpy-2.3.2.dist-info": (
        "numpy",
        "numpy.libs",
        "numpy-2.3.2.dist-info",
    ),
    "StrEnum-0.4.15.dist-info": (
        "strenum",
        "StrEnum-0.4.15.dist-info",
    ),
}

for dist_info_name, owned_roots in packages.items():
    record = site_packages / dist_info_name / "RECORD"
    rows = []
    for root_name in owned_roots:
        root = site_packages / root_name
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            if path == record:
                continue
            digest = hashlib.sha256(path.read_bytes()).digest()
            encoded = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
            rows.append((path.relative_to(site_packages).as_posix(), encoded, path.stat().st_size))

    with record.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerows(rows)
```

版本变化时同步更新 dist-info 名称和 owned roots。生产脚本会裁剪后重新生成 numpy 和 StrEnum 的 `RECORD`，不要手改这些清单。

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
7. 双向校验 dist-info `RECORD`：包内每个归属文件都有对应行，`RECORD` 每个非空行都指向存在文件，且 hash、大小一致；license 文件仍存在。`maa` 有意不带 dist-info，不参与该校验。
8. 重新对比 `maa` 与源 wheel，确认只有 `library.py` 的目标补丁差异。

### 真机验收

手动 CI 只执行上述静态验收并创建 draft release，不会启动模拟器或真机。
发布前至少在两个真实 Android 设备或模拟器上分别覆盖两个 ABI。测试环境必须提供与 manifest 一致的 MaaFramework Android 原生库。

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

打包前先做权限归一：目录 `0755`、`bin/python3` `0755`、普通文件 `0644`。如果运行时启动要求其它可执行位，必须在文档和验收清单中显式记录。静态验收必须直接检查归档条目的 mode，而不是只检查解包后 staging 目录。

当前 `3.13.15-maafw5.12.3` 归档的 owner/group 已是 `0`，大部分 mode 被归一为目录 `0777`、文件 `0666`；两个 `bin/python3` 也不是可执行位，下游直接执行前必须先 `chmod`。此外，不同生成阶段的 mtime 不一致，且未固定 gzip 元数据。因此它不能被描述为 byte-for-byte reproducible。上述固定元数据流程是后续版本的规范；它不会逐字节复现当前资产。

## 11. 发布 GitHub Release

手动 CI 的发布流程：

1. 确认要构建的 commit，并在 Actions 页面手动运行 `Release agent core`。
2. CI 编译、打包、静态验收，并创建 draft release。Beta 版本会带 prerelease 标记。
3. CI 上传两个 `.tar.gz` 资产、`SHA256SUMS` 和 `build-metadata.json`；release notes 记录版本矩阵和最终 SHA-256。
4. 从 GitHub 下载 URL 重新下载资产，校验 SHA-256 与 `SHA256SUMS` 一致。
5. 准备匹配版本的 MaaFramework 原生库，完成第 9 节真机验收。
6. 把已测 Android 环境和结果补充到 release notes。
7. 人工发布 release。若已存在同名 release 或 tag，CI 拒绝覆盖。
8. 发布后用下游打包脚本走一次完整消费，确认新 release URL、manifest、site-packages 叠加安装都可用。

Release notes 不应声称包含 MaaFramework 原生库。若宿主所需的 MaaFramework Android 包有独立发布地址，应链接到对应的 `5.12.3` release。

## 12. 下游兼容规则

下游消费这个内核时应遵守：

1. 解包后使用 `<abi>/bundle` 作为 agent runtime 根目录。当前 `3.13.15-maafw5.12.3` 资产的 launcher 没有可执行位，启动前必须显式调整；后续按本文生成的包必须在归档内直接带 `0755`。
2. 额外依赖安装到 `bundle/site-packages`，不要另建 Python 环境。
3. 从 `agent-core.json` 读取 Python 版本、ABI、`pyAbiTag`、`wheelApis`、`wheelAbi` 和 `provides`。
4. 生成 pip platform 时按顺序展开 `wheelApis`，格式为 `android_<api>_<wheelAbi>`。
5. 用 PEP 503 规则规范化依赖名。命中 `provides` 且项目约束与提供版本兼容时不要重复安装；版本不兼容时必须报出显式冲突，不能把不兼容 pin 静默当作已满足。
6. `maaagentbinary` 是桌面端可执行包，Android 上应依赖宿主 `nativeLibraryDir` 或等价路径，不安装该包。
7. MaaFramework 原生库由宿主提供，版本必须与 manifest 的 `maafw` 匹配。
8. 更新任何二进制输入都必须发新 release 和新资产，不能覆盖已上传资产。

## 13. 当前限制与待固化事项

当前限制：

- CI 只执行静态验收和 draft 上传，不包含 Android 真机冒烟；发布必须保留人工门槛。
- 仓库没有离线完整输入锁定文件；CPython Android 依赖仍由官方脚本按源码内版本下载。
- 当前包的二进制元数据显示 launcher 与 `libpython3.13.so` 来自不同 NDK 版本，精确构建来源不可追溯。
- 当前包的 numpy/StrEnum `RECORD` 是裁剪前的旧清单，包含不存在的 `__pycache__`、tests、f2py 和 entry-point 路径；例如 arm64 包中 numpy 有 951 个悬空行、StrEnum 有 4 个悬空行。它不能作为包元数据完整性验收基线，下个 release 必须重新生成。
- 当前包的两个 launcher 归档 mode 都是 `0666`，不是可执行文件。下游必须先调整权限；后续包按第 10 节归一为 `0755`。
- 当前归档元数据不完全确定，不能宣称 byte-for-byte 可复现。
- 包内没有 MaaFramework 原生库，真机测试必须准备宿主侧 native 库。
- Android CPython 运行时未包含 `_multiprocessing`；需要该 API 的下游项目必须自行提供兼容 shim 或避免跨进程语义。

后续固化建议：

1. 为两个 ABI 增加可复用的真机或模拟器冒烟矩阵，并把结果记录到 release notes。
2. 增加离线输入锁存和校验，避免构建过程依赖外部下载地址的可用性。
3. 保留上一版到下一版的二进制对比报告，区分运行时变更与 site-packages 变更。
4. 固化 GitHub Actions runner 与 Android SDK/NDK 的可追溯环境信息。
