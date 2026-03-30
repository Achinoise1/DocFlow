# GitHub Actions Workflow 逐行解析

> 参考来源：[CPP-Ticket build.yml](https://github.com/Casta-mere/CPP-Ticket/blob/main/.github/workflows/build.yml)

---

## 一、整体结构

该 workflow 共包含四个顶层部分：

```
name           → Workflow 显示名称
on             → 触发条件
jobs
  build-frontend  → 构建前端静态资源（Ubuntu）
  build-windows   → 打包 Windows 可执行文件（依赖 build-frontend）
  build-macos     → 打包 macOS 可执行文件（依赖 build-frontend）
  release         → 创建 GitHub Release（依赖以上两个打包 job）
```

---

## 二、`on`（触发条件）

```yaml
on:
  push:
    tags:
      - "V*"
  workflow_dispatch:
```

| 字段 | 说明 |
|------|------|
| `push.tags: "V*"` | 当推送以 `V` 开头的 tag（如 `V1.0.0`）时自动触发，适合发布版本时使用 |
| `workflow_dispatch` | 允许在 GitHub Actions 页面手动点击按钮触发，方便调试或紧急发布 |

**⚙️ 通用逻辑**：tag 触发发布是 CI/CD 标准实践，可直接复用。

---

## 三、`jobs`（各任务详解）

### 3.1 `build-frontend`（构建前端）

```yaml
build-frontend:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4                   # 拉取代码
    - name: Create docker volume
      run: docker volume create cpp_node_modules  # 创建 Docker 卷缓存 node_modules
    - name: Build frontend image
      run: docker build -t cpp-ticket-frontend:${{ github.ref_name }} -f Frontend/Dockerfile Frontend
      # 构建前端 Docker 镜像，用 tag 名称标记版本
    - name: Run frontend container to build static files
      run: |
        docker run --rm \
          -v cpp_node_modules:/cpp-ticket/node_modules \
          -v ${{ github.workspace }}/Frontend/cpp-ticket:/cpp-ticket \
          -v ${{ github.workspace }}/Frontend/static:/cpp-ticket/out_exported \
          cpp-ticket-frontend:${{ github.ref_name }}
      # 启动容器，将 node_modules 卷挂载为缓存，将宿主机目录挂载用于输出静态文件
    - name: Upload static files
      uses: actions/upload-artifact@v4
      with:
        name: frontend-static
        path: Frontend/static/
      # 将构建产物上传为 artifact，供后续 job 下载使用
```

**逐步解析：**

1. `actions/checkout@v4`：拉取当前仓库代码到 runner（**通用逻辑**）
2. `docker volume create`：创建具名 Docker 卷，用于在容器间缓存 `node_modules`，避免重复安装（**项目特定**）
3. `docker build`：根据 `Frontend/Dockerfile` 构建前端镜像（**项目特定**）
4. `docker run`：在容器内执行前端构建命令，通过卷挂载将静态文件输出到宿主机（**项目特定**）
5. `upload-artifact`：将静态文件打包上传，使后续 job 能够下载（**通用逻辑**）

---

### 3.2 `build-windows`（打包 Windows 版本）

```yaml
build-windows:
  runs-on: windows-latest
  needs: build-frontend       # 必须等 build-frontend 完成后才执行
  steps:
    - uses: actions/checkout@v4

    - name: Download static files
      uses: actions/download-artifact@v4
      with:
        name: frontend-static
        path: Frontend/static
      # 从上一个 job 下载前端构建产物

    - name: Configure pip to use Tsinghua mirror
      run: |
        mkdir %USERPROFILE%\.pip
        echo [global] > %USERPROFILE%\.pip\pip.ini
        echo index-url = https://pypi.tuna.tsinghua.edu.cn/simple >> %USERPROFILE%\.pip\pip.ini
        echo trusted-host = pypi.tuna.tsinghua.edu.cn >> %USERPROFILE%\.pip\pip.ini
      # 配置 pip 使用清华镜像源，加速依赖下载（在国内 runner 上尤为重要）

    - name: Install Python dependencies and PyInstaller
      run: |
        python -m pip install --upgrade pip
        pip install -r ./Backend/requirements.txt
        pip install --upgrade pip setuptools
        pip install --upgrade pyinstaller
      # 安装项目依赖和打包工具 PyInstaller

    - name: Use PyInstaller to build Windows binary
      run: pyinstaller run.spec
      # 根据 run.spec 配置文件，将 Python 项目打包为单个 exe

    - name: Compress CPP-Ticket.exe into zip
      run: powershell Compress-Archive -Path dist/CPP-Ticket.exe -DestinationPath CPP-Ticket_windows_${{ github.ref_name }}.zip
      # 将 exe 压缩为 zip，文件名包含版本号

    - name: Upload zip artifact
      uses: actions/upload-artifact@v4
      with:
        name: cpp-ticket-zip
        path: CPP-Ticket_windows_${{ github.ref_name }}.zip
      # 上传 zip 供 release job 使用
```

**逐步解析：**

1. `needs: build-frontend`：声明依赖，确保前端静态文件先构建完成（**通用逻辑**）
2. `download-artifact`：下载前一 job 上传的静态文件（**通用逻辑**）
3. 配置清华 pip 镜像：降低依赖下载失败率（**项目特定 / 可选通用**）
4. 安装依赖 + PyInstaller：为打包做准备（**半通用**，依赖内容是项目特定的）
5. `pyinstaller run.spec`：根据 spec 文件构建 exe（**项目特定**）
6. `Compress-Archive`：用 PowerShell 压缩为 zip（**项目特定**）
7. `upload-artifact`：上传压缩包（**通用逻辑**）

---

### 3.3 `build-macos`（打包 macOS 版本）

```yaml
build-macos:
  runs-on: macos-latest
  needs: build-frontend
  steps:
    - uses: actions/checkout@v4

    - name: Download static files
      uses: actions/download-artifact@v4
      with:
        name: frontend-static
        path: Frontend/static

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: "3.x"
      # macOS runner 可能没有预装 Python，需显式安装

    - name: Configure pip to use Tsinghua mirror
      run: |
        mkdir -p ~/.pip
        echo "[global]" > ~/.pip/pip.conf
        echo "index-url = https://pypi.tuna.tsinghua.edu.cn/simple" >> ~/.pip/pip.conf
        echo "trusted-host = pypi.tuna.tsinghua.edu.cn" >> ~/.pip/pip.conf

    - name: Install Python dependencies and PyInstaller
      run: |
        python -m pip install --upgrade pip
        pip install -r ./Backend/requirements.txt
        pip install --upgrade pip setuptools
        pip install --upgrade pyinstaller

    - name: Use PyInstaller to build macOS binary
      run: pyinstaller run.spec

    - name: Compress CPP-Ticket into zip
      run: zip -r CPP-Ticket_macos_${{ github.ref_name }}.zip dist/CPP-Ticket
      # macOS 用 zip 命令代替 PowerShell

    - name: Upload zip artifact
      uses: actions/upload-artifact@v4
      with:
        name: cpp-ticket-macos-zip
        path: CPP-Ticket_macos_${{ github.ref_name }}.zip
```

**与 `build-windows` 的差异：**

| 差异点 | Windows | macOS |
|--------|---------|-------|
| runner | `windows-latest` | `macos-latest` |
| Python 安装 | 预装，无需额外步骤 | 需 `actions/setup-python@v4` |
| pip 配置路径 | `%USERPROFILE%\.pip\pip.ini` | `~/.pip/pip.conf` |
| 压缩命令 | `powershell Compress-Archive` | `zip -r` |
| 产物名称 | `*_windows_*.zip` | `*_macos_*.zip` |

---

### 3.4 `release`（发布 GitHub Release）

```yaml
release:
  needs: [build-windows, build-macos]   # 必须等两个平台都打包完成
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4

    - name: Download Windows zip
      uses: actions/download-artifact@v4
      with:
        name: cpp-ticket-zip
        path: artifacts/
      # 下载 Windows 压缩包到 artifacts/ 目录

    - name: Download macOS zip
      uses: actions/download-artifact@v4
      with:
        name: cpp-ticket-macos-zip
        path: artifacts/
      # 下载 macOS 压缩包到同一目录

    - name: Create GitHub Release with zip files
      uses: softprops/action-gh-release@v2
      with:
        tag_name: ${{ github.ref_name }}    # 使用触发 workflow 的 tag 名称
        name: Release ${{ github.ref_name }} # Release 显示名称
        files: |
          artifacts/CPP-Ticket_windows_${{ github.ref_name }}.zip
          artifacts/CPP-Ticket_macos_${{ github.ref_name }}.zip
        # 将两个平台的 zip 文件附加到 Release
      env:
        GITHUB_TOKEN: ${{ secrets.GH_CPP_Ticket }}
        # 使用自定义 PAT（非默认 GITHUB_TOKEN），可能是为了触发其他仓库的 webhook
```

**逐步解析：**

1. `needs: [build-windows, build-macos]`：等待所有平台打包完成（**通用逻辑**）
2. 两次 `download-artifact`：下载各平台产物（**通用逻辑**）
3. `softprops/action-gh-release@v2`：第三方 Action，一行创建 GitHub Release 并附上文件（**通用逻辑**）
4. `secrets.GH_CPP_Ticket`：使用自定义 Personal Access Token（**项目特定**，通常也可用 `secrets.GITHUB_TOKEN`）

---

## 四、通用逻辑 vs 项目特定逻辑

| 逻辑 | 类型 | 说明 |
|------|------|------|
| `actions/checkout@v4` | ✅ 通用 | 所有 workflow 几乎必用 |
| `actions/upload-artifact@v4` | ✅ 通用 | Job 间传递构建产物的标准方式 |
| `actions/download-artifact@v4` | ✅ 通用 | 配合 upload-artifact 使用 |
| `softprops/action-gh-release@v2` | ✅ 通用 | 发布 Release 的常用第三方 Action |
| `needs` 声明依赖 | ✅ 通用 | 控制 job 执行顺序的标准方式 |
| tag 触发 + `workflow_dispatch` | ✅ 通用 | 发布流水线的标准触发方式 |
| Docker 构建前端 | ❌ 项目特定 | 特定于有前端的全栈项目 |
| 清华 pip 镜像配置 | ⚠️ 可选 | 在国内服务器/网络受限时提速 |
| `pyinstaller run.spec` | ❌ 项目特定 | 特定于用 PyInstaller 打包的项目 |
| `powershell Compress-Archive` | ❌ 项目特定 | Windows 平台特有的压缩方式 |
| `secrets.GH_CPP_Ticket` | ❌ 项目特定 | 自定义 PAT，名称需根据项目修改 |

---

## 五、可复用模板结构

以下是提取通用逻辑后的最小可复用模板，适用于「多平台 Python 桌面应用 → PyInstaller 打包 → GitHub Release」场景：

```yaml
name: Build & Release

on:
  push:
    tags:
      - "V*"           # 根据项目 tag 命名规范修改，如 "v*"
  workflow_dispatch:

jobs:
  # ──────────────────────────────────────────────
  # [可选] 若有前端需提前构建，保留此 job；否则删除
  # ──────────────────────────────────────────────
  build-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      # 【项目特定】替换为实际的前端构建命令
      - name: Build frontend
        run: echo "替换为前端构建逻辑"

      - name: Upload static files
        uses: actions/upload-artifact@v4
        with:
          name: frontend-static          # artifact 名称，需与下载步骤对应
          path: path/to/static/output/   # 【项目特定】前端产物路径

  # ──────────────────────────────────────────────
  # Windows 打包
  # ──────────────────────────────────────────────
  build-windows:
    runs-on: windows-latest
    needs: build-frontend    # 若无前端 job，删除此行
    steps:
      - uses: actions/checkout@v4

      # 若无前端 job，删除此步骤
      - name: Download static files
        uses: actions/download-artifact@v4
        with:
          name: frontend-static
          path: path/to/static/          # 【项目特定】

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt    # 【项目特定】requirements 文件路径
          pip install pyinstaller

      - name: Build with PyInstaller
        run: pyinstaller your_app.spec      # 【项目特定】spec 文件名

      - name: Package into zip
        run: powershell Compress-Archive -Path dist/YourApp.exe -DestinationPath YourApp_windows_${{ github.ref_name }}.zip
        # 【项目特定】修改 exe 名称和输出 zip 名称

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: app-windows-zip           # artifact 名称，需与 release job 对应
          path: YourApp_windows_${{ github.ref_name }}.zip

  # ──────────────────────────────────────────────
  # macOS 打包（若不需要 macOS 版本，删除整个 job）
  # ──────────────────────────────────────────────
  build-macos:
    runs-on: macos-latest
    needs: build-frontend    # 若无前端 job，删除此行
    steps:
      - uses: actions/checkout@v4

      - name: Download static files
        uses: actions/download-artifact@v4
        with:
          name: frontend-static
          path: path/to/static/

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.x"           # 【项目特定】Python 版本

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pyinstaller

      - name: Build with PyInstaller
        run: pyinstaller your_app.spec

      - name: Package into zip
        run: zip -r YourApp_macos_${{ github.ref_name }}.zip dist/YourApp

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: app-macos-zip
          path: YourApp_macos_${{ github.ref_name }}.zip

  # ──────────────────────────────────────────────
  # 发布 GitHub Release
  # ──────────────────────────────────────────────
  release:
    needs: [build-windows, build-macos]  # 【项目特定】列出所有需等待的打包 job
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Download Windows artifact
        uses: actions/download-artifact@v4
        with:
          name: app-windows-zip
          path: artifacts/

      - name: Download macOS artifact
        uses: actions/download-artifact@v4
        with:
          name: app-macos-zip
          path: artifacts/

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          tag_name: ${{ github.ref_name }}
          name: Release ${{ github.ref_name }}
          files: |
            artifacts/YourApp_windows_${{ github.ref_name }}.zip
            artifacts/YourApp_macos_${{ github.ref_name }}.zip
            # 【项目特定】列出所有需附加到 Release 的文件
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          # 大多数情况下使用默认 GITHUB_TOKEN 即可
          # 若需要跨仓库操作，替换为自定义 PAT：${{ secrets.YOUR_PAT_SECRET }}
```

---

## 六、DocFlow 适配说明

DocFlow 是纯 Windows 桌面应用（依赖 `win32com`），无前端构建步骤，因此相比 CPP-Ticket 模板可做如下简化：

- ❌ 删除 `build-frontend` job（无前端）
- ❌ 删除 `build-macos` job（`win32com` 仅支持 Windows）
- ✅ 保留 `build-windows` job，spec 文件改为 `main.spec`，产物改为 `DocFlow.exe`
- ✅ 保留 `release` job，`needs` 只需 `[build-windows]`

具体实现见 `.github/workflows/build.yml`。
