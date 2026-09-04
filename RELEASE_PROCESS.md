# 构建产物生产流程

本文说明 `MaaAgentCoreAndroid` 构建产物的组成、生产步骤和验收标准。当前仓库包含 `scripts/build_agent_core.py` 生产脚本和 `Build agent core` GitHub Actions 工作流；第 1 节介绍 GitHub Actions 自动构建，第 2 节起介绍可选的本地手动构建。本地手动构建用于复现发布产物，不是日常开发或贡献的前置要求。

## 1. 自动构建

自动构建通过 `Build agent core` workflow 完成。可以在 GitHub 网页上启动，
也可以用 GitHub CLI 触发；两种方式只负责提交输入，实际编译、验收和打包
都发生在 GitHub Actions runner 上。

### 1.1 网页触发

触发仓库主线上的 workflow 需要 GitHub 写权限；没有写权限时，先在自己
的 fork 中运行同一 workflow。

1. 打开仓库的 **Actions** 页面。
2. 在左侧选择 **Build agent core**。
3. 点击 **Run workflow**。
4. 分支选择要构建的分支，通常是 `main`。
5. 填写两个输入：

   | 输入 | 值 |
   |---|---|
   | `python-version` | 稳定版 CPython `3.x.y`，例如 `3.13.15` |
   | `maafw-version` | MaaFramework 版本，例如 `5.12.3` 或 `5.13.0-beta.1`；后者会规范化为 `5.13.0b1` |

6. 点击 **Run workflow**，进入新 run 页面等待完成。

workflow 的 concurrency 配置会串行调度构建，且不会取消已开始的 run。

### 1.2 GitHub CLI 触发

工作流文件是 `.github/workflows/release.yml`。以下命令默认在仓库检出目录
执行；不在检出目录时，给每条命令追加 `--repo <owner>/<repository>`：

```bash
gh workflow run release.yml \
  --ref main \
  -f python-version=3.13.15 \
  -f maafw-version=5.13.0-beta.1
```

查询最新 run：

```bash
gh run list --workflow release.yml --limit 5
```

跟踪指定 run：

```bash
gh run watch <run-id>
```

### 1.3 下载和校验

run 成功后，在其页面下方的 **Artifacts** 区域下载
`agent-core-<python>-maafw<maafw>`。也可以用 GitHub CLI 下载：

```bash
gh run download <run-id> \
  --name agent-core-3.13.15-maafw5.13.0b1 \
  --dir agent-core-artifact
```

浏览器下载的 artifact 是外层 ZIP，先解开后确认包含两个 `.tar.gz`、
`SHA256SUMS`、`build-metadata.json` 和 `build-report.md`。`gh run download`
会直接解出这些文件。然后在 artifact 目录执行：

```bash
shasum -a 256 --check SHA256SUMS
```

校验通过后：

1. 从官方 MaaFramework GitHub 仓库 <https://github.com/MaaXYZ/MaaFramework>
   的 Releases 下载匹配版本 Android 产物，完成第 2.7 节真机验收。
2. 用下游打包脚本走一次完整消费，确认 manifest、site-packages 叠加安装都可用。

该工作流不会创建 tag 或 GitHub Release。`build-report.md` 不应声称包含
MaaFramework 原生库。artifact 默认保留 30 天；需要长期保存时必须在过期前
下载并归档。若宿主所需的 MaaFramework Android 包有独立发布地址，应在构建
报告中记录对应版本的下载链接。

## 2. 手动构建

本节描述可选的本地手动构建。如需在本机生成发布形态的归档，建议先准备
Android SDK、JDK、`ANDROID_HOME` 和构建脚本所需的命令行工具，再从仓库检出
目录运行脚本；脚本会下载输入、创建工作目录、完成编译、静态验收和打包。
日常调试或贡献代码不需要先执行这套流程。

发布产物统一使用 Android NDK `28.2.13676358`。当前
<https://github.com/Aliothmoon/MaaFwApp> 的 `MaaFwApp` 主线没有
显式配置 `ndkVersion`，而是使用 Android Gradle Plugin `9.2.1`；该版本
AGP 的默认 NDK 为 `28.2.13676358`。

`scripts/build_agent_core.py` 会在解包 CPython 后，把官方
`Android/android-env.sh` 中的 `ndk_version` 显式改成该值。后续 CPython host
构建、`llvm-strip` 和 launcher 编译都由这份配置解析工具链；构建脚本还会
校验实际安装的 NDK revision，并把结果写入 `build-metadata.json` 与
`build-report.md`。因此发布构建不会隐式选择本机已有的其它 NDK，本地开发者
也不需要为此手动预装或切换 NDK。

### 2.1 工作目录与准备

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

本地手动构建时调用：

```bash
python scripts/build_agent_core.py \
  --python-version 3.13.15 \
  --maafw-version 5.13.0-beta.1 \
  --work-dir "$AGENT_CORE_WORK_DIR"
```

### 2.2 生成 CPython 运行时

#### 2.2.1 完整重建

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

从 `prefix/lib` 按允许清单提取，而不是先完整复制 `prefix/` 再做删除：

- `lib/libpython3.13.so` 和 `lib/libpython3.so`
- Python 扩展模块和标准库数据所在的 `lib/python3.13/`
- 压缩标准库 `lib/python313.zip`
- OpenSSL、SQLite 及其 engine/module 目录
- 运行时动态链接所需的其它 `lib*.so*` 文件

运行时里的兼容符号链接（例如 `libcrypto.so`）复制为实体文件；Android 归档不依赖
解包器对 tar symlink 的处理方式。
复制后使用对应 ABI 的 NDK `llvm-strip --strip-unneeded` 去除运行时 `.so` 的本地
调试符号，保留动态链接所需符号。

以下内容只作为提取后的排除校验，不进入允许清单：

- `include/`
- `lib/pkgconfig/`
- 构建目录、对象文件、下载缓存
- pip/ensurepip 的可引导安装内容
- `config-*`、`idlelib`、`pydoc_data`、`tkinter`、`turtledemo` 等桌面/构建侧标准库内容
- `__pycache__`

`bundle/bin/python3` 是一个 Android PIE 可执行文件，入口实现只调用 `Py_BytesMain`。它必须使用 `/system/bin/linker64` 作为 ELF interpreter，并动态链接 `libpython3.13.so`。新生产的 launcher 源码位于 `scripts/launcher.c`，并由构建脚本使用对应 ABI 的 CPython Android 工具链编译。

当前已发布包没有记录 launcher 的原始源码和确切构建命令。产物元数据显示 launcher 由 Android NDK `r29-beta2` / Clang 20 构建，而 `libpython3.13.so` 中可见 NDK `r27d` 标记；这说明当前包不是一次完整、可追溯的单工具链构建。

#### 2.2.2 运行时不变时的复用

如果只更新 `maa`、numpy、StrEnum 或 manifest，而 CPython 运行时保持不变，可以先下载上一版已验证构建产物，校验 SHA-256 后：

1. 解包到干净目录。
2. 只保留对应 ABI 的 `bundle/bin/` 与 `bundle/prefix/`。
3. 删除并重建 `bundle/site-packages/`。
4. 重新生成 `bundle/agent-core.json`。

这种方式可以避免临时重造运行时，但它不是完整生产方案；Python、NDK、依赖库或 launcher 任一变化时仍必须完整重建并重新做真机验收。

#### 2.2.3 进程与并发语义

Android CPython 运行时不包含 `_multiprocessing` 扩展。`multiprocessing`
顶层模块存在不代表进程创建可用；`multiprocessing.Process`、需要进程启动器的
`concurrent.futures.ProcessPoolExecutor`，以及依赖这些 API 的库，都不能作为
本内核的运行时契约。

Agent 载荷应默认单进程执行，需要并发时优先使用线程、协程或异步 I/O，并遵守
Python GIL 与 Android 线程限制。确实需要跨进程能力时，应放在宿主 App、
Android service/process 边界或 MaaFramework Agent IPC 边界中实现；
`MaaAgentServerStartUp` 与 MaaFramework 的通信是跨进程集成，不会为 Python
载荷重新启用 `multiprocessing` 语义。依赖硬性要求 `multiprocessing` 的包，
必须在下游自行提供兼容方案并验收，不能默认由本内核承担。

### 2.3 安装预置 Python 包

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

site-packages 同样按提取契约生成。允许进入 `<abi>/bundle/site-packages/`
的初始根只有：

- `numpy/`
- `numpy.libs/`
- `numpy-<version>.dist-info/`
- `strenum/`
- `StrEnum-<version>.dist-info/`

其中 `numpy/testing/` 必须保留；`numpy.testing` 是运行时公开 API。`bin/`、
`f2py`、`_pyinstaller`、各级 `tests/`、`__pycache__` 和 `.pyc` 不属于提取
契约。pip 目标安装后可用以下命令做裁剪和兜底校验：

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

### 2.4 收录并补丁 `maa`

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

### 2.5 MaaFramework 原生库供给

本内核只提供 Python binding，不收录 MaaFramework 原生库。真机验收和宿主
App 所需的 Android `.so` 必须从官方 MaaFramework GitHub 仓库
<https://github.com/MaaXYZ/MaaFramework> 的 Releases 下载，版本 tag 与
manifest 的 `maafw` 精确匹配。按 ABI 选择官方 Release 资产：

| ABI | 官方资产 |
|---|---|
| `arm64-v8a` | `MAA-android-aarch64-v<version>.zip` |
| `x86_64` | `MAA-android-x86_64-v<version>.zip` |

不要使用第三方镜像、PyPI wheel 内的平台可执行文件或本地重编产物替代官方
Release 输入。下载后记录资产名、tag 和 SHA-256，再部署到宿主
`nativeLibraryDir` 或等价目录。

### 2.6 生成 manifest

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

- artifact 名称和构建报告
- README 的资产表
- `common`
- 输入 wheel 文件名与哈希
- 构建报告中的版本矩阵

### 2.7 静态验收

打包前对每个 ABI 执行：

1. 从归档 staging 根检查，第一层必须只有 `<abi>`，下一层必须只有 `bundle`。
2. `bundle` 顶层只允许 `agent-core.json`、`bin`、`prefix`、`site-packages`。
3. JSON 可解析，字段值与版本矩阵一致。
4. `bin/python3` 是 Android PIE ELF，interpreter 为 `/system/bin/linker64`。
5. `prefix/lib/libpython3.13.so`、`lib-dynload/*.so`、numpy 扩展和 `numpy.libs/*.so` 的机器架构与 ABI 匹配。
6. 逐项确认不存在 MaaFramework 原生库、`maa/bin`、构建缓存、包管理器临时文件和 `__pycache__`。
7. 双向校验 dist-info `RECORD`：包内每个归属文件都有对应行，`RECORD` 每个非空行都指向存在文件，且 hash、大小一致；license 文件仍存在。`maa` 有意不带 dist-info，不参与该校验。
8. 重新对比 `maa` 与源 wheel，确认只有 `library.py` 的目标补丁差异。

#### 真机验收

自动构建只执行上述静态验收并上传 Actions artifact，不会启动模拟器、
真机或 GitHub Release。选择本地手动构建生成对外产物时，先完成静态验收。
对外使用前至少在两个真实 Android 设备或模拟器上分别覆盖两个 ABI。测试环境
必须提供与 manifest 一致的 MaaFramework Android 原生库。

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

### 2.8 打包

打包输入根目录是 `stage/`，归档内必须从 `<abi>/bundle/...` 开始，不能多出 `stage/`、`work/` 或绝对路径。

打包前先对每个 ABI 执行权限归一：

```bash
find stage/<abi>/bundle -type d -exec chmod 0755 {} +
chmod 0755 stage/<abi>/bundle/bin/python3
find stage/<abi>/bundle -type f \
  ! -path 'stage/<abi>/bundle/bin/python3' \
  -exec chmod 0644 {} +
```

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

再解包到新的空目录，重复第 2.7 节静态验收。

权限归一后的期望是：目录 `0755`、`bin/python3` `0755`、普通文件 `0644`。
如果运行时启动要求其它可执行位，必须在文档和验收清单中显式记录。静态验收
必须直接检查归档条目的 mode，而不是只检查解包后 staging 目录。

当前 `3.13.15-maafw5.12.3` 归档的 owner/group 已是 `0`，大部分 mode 被归一为目录 `0777`、文件 `0666`；两个 `bin/python3` 也不是可执行位，下游直接执行前必须先 `chmod`。此外，不同生成阶段的 mtime 不一致，且未固定 gzip 元数据。因此它不能被描述为 byte-for-byte reproducible。上述固定元数据流程是后续版本的规范；它不会逐字节复现当前资产。

## 3. 下游兼容规则

下游消费这个内核时应遵守：

1. 解包后使用 `<abi>/bundle` 作为 agent runtime 根目录，并在启动前执行
   `chmod 0755 <abi>/bundle/bin/python3`。当前 `3.13.15-maafw5.12.3` 资产必须
   依赖这一步；新构建产物的 tar 条目本身必须已经是 `0755`，这里的 `chmod`
   只是下游消费时的防御性归一。
2. 额外依赖安装到 `bundle/site-packages`，不要另建 Python 环境。
3. 从 `agent-core.json` 读取 Python 版本、ABI、`pyAbiTag`、`wheelApis`、`wheelAbi` 和 `provides`。
4. 生成 pip platform 时按顺序展开 `wheelApis`，格式为 `android_<api>_<wheelAbi>`。
5. 用 PEP 503 规则规范化依赖名，比较依赖名时先把名称转为小写，再把连续的 `-`、`_`、`.` 合并成一个 `-`，然后用结果匹配 `provides`；例如 `NumPy` 按 `numpy` 匹配，`scikit_learn` 和 `scikit-learn` 是同一个依赖名。命中 `provides` 且项目约束与提供版本兼容时不要重复安装；版本不兼容时必须报出显式冲突，不能把不兼容 pin 静默当作已满足。
6. `maaagentbinary` 是桌面端可执行包，Android 上应依赖宿主 `nativeLibraryDir` 或等价路径，不安装该包。
7. MaaFramework 原生库由宿主提供，必须来自官方 MaaFramework GitHub 仓库的
   Releases，版本必须与 manifest 的 `maafw` 匹配。
8. 更新任何二进制输入都必须生成新的 Actions artifact，不能复用或覆盖旧产物。
