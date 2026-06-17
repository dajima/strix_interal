# Phase 1: Build & Release Pipeline - Context

**Gathered:** 2026-06-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 1 交付一键式构建和发布流水线：开发者通过 build_script/ 下的独立脚本构建 strix 二进制（Linux + Windows）和 Docker 沙箱镜像，版本号统一从 pyproject.toml 提取，通过 GitHub Actions workflow_dispatch 或 tag push 触发 Release 发布。

**Docker Compose 部署（BUILD-04）已从本阶段移除** — 用户期望 strix 主容器 + sandbox 容器的编排模式需要重新设计架构，推迟至后续版本。
</domain>

<decisions>
## Implementation Decisions

### 构建脚本 (Build Scripts)
- **D-01:** 构建脚本放在 `build_script/` 目录下，独立可运行的 shell 脚本（非 Makefile target，非 Python CLI）
- **D-02:** 每个脚本独立运行，如 `bash build_script/build-binary.sh`，不设统一入口
- **D-03:** 二进制通过 Docker 容器内构建（复用现有 `Dockerfile.build`），不依赖本地 Python 环境
- **D-04:** CI（GitHub Actions）直接调用 `build_script/` 下的脚本，本地与 CI 使用同一套构建逻辑

### 构建产物目录
- **D-05:** 产物统一输出到 `dist/` 目录，扁平结构，版本号从 `pyproject.toml` 提取并嵌入文件名：
  - `dist/strix-{version}-linux-x86_64` — Linux 二进制
  - `dist/strix-{version}-windows-x86_64.exe` — Windows 二进制
  - `dist/checksums.txt` — SHA256 校验文件

### Docker Compose 部署
- **D-06:** **BUILD-04 已移除** — Docker Compose 部署推迟至后续版本。实现"strix 主容器 + sandbox 容器一键编排"需要对 strix 运行时架构进行重新设计，超出本阶段范围。

### Release 发布
- **D-07:** 发布 Linux + Windows 两个平台二进制（macOS 不在 Phase 1 范围内）
- **D-08:** Docker 沙箱镜像推送到 **Docker Hub**（非 ghcr.io）
- **D-09:** **双触发机制：** `workflow_dispatch`（在 GitHub Actions UI 手动触发）+ `push tags: v*`（推送 Git tag 自动触发）
- **D-10:** GitHub Release 产物包含：平台二进制压缩包（`.tar.gz` for Linux / `.zip` for Windows）+ `checksums.txt`

### Claude's Discretion
以下领域由实现者灵活决定：
- 构建产物 `dist/` 目录结构的具体命名和组织（用户让 Claude 决定）
- GitHub Release 双触发策略的具体 workflow 设计（用户未使用过 GitHub Release，让 Claude 决定）
- `build_script/` 下脚本的具体参数设计和错误处理

### 需求变更记录
| 需求 | 变更 | 原因 |
|------|------|------|
| BUILD-04 (Docker Compose 部署) | **移除** | 用户评估后认为 docker-compose.yml 不适合当前架构，推迟至后续版本 |
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 构建相关文件
- `Dockerfile.build` — 现有 PyInstaller Docker 构建文件，构建脚本需复用此文件
- `strix.spec` — PyInstaller spec 文件，定义二进制打包配置
- `pyproject.toml` — **唯一版本号来源**，[project] version 字段
- `Makefile` — 现有开发工具（format/lint/type-check），不添加构建目标
- `containers/Dockerfile` — Docker 沙箱镜像定义（BUILD-02 的构建目标）

### CI/CD 现有文件
- `.github/workflows/build-release.yml` — 现有 build + release workflow，4 平台矩阵，作为 Phase 1 改造基线

### 规划文件
- `.planning/REQUIREMENTS.md` — 需求定义：BUILD-01/02/03/05/06（BUILD-04 已移除）
- `.planning/ROADMAP.md` — Phase 1 目标与成功标准
- `.planning/PROJECT.md` — 项目技术栈与约束（Python 3.12+、Docker、PyInstaller）
- `.planning/STATE.md` — 关键决策：pyproject.toml 为唯一版本源、Phase 1 先于 Phase 2
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Dockerfile.build** — 已定义 PyInstaller 容器化构建流程（`python:3.12-slim` + binutils + pyinstaller），构建脚本直接 `docker build -f Dockerfile.build` 即可
- **build-release.yml** — 已有完整的 PyInstaller 多渠道构建 + softprops/action-gh-release 发布流程，Phase 1 需在此基础上改造而非重写
- **strix.spec** — Analysis 阶段包含 `strix/` 源码、`containers/` 数据文件，构建脚本无需关心 Python 依赖收集逻辑

### Integration Points
- **版本号链路：** `pyproject.toml` → shell `grep` 提取 → 注入二进制文件名、Docker 镜像 tag、Git tag、Release 标题
- **CI 与本地脚本的统一：** build_script/ 脚本被两种场景调用 —— 本地 `bash build_script/build-binary.sh` 和 GitHub Actions `run: bash build_script/build-binary.sh`

### Established Patterns
- 项目使用 `uv` 作为包管理器 + `ruff`/`mypy`/`bandit` 作为质量工具，构建脚本不改变这些
- Docker 是强依赖（`shutil.which("docker")`），构建脚本假设 Docker 可用
</code_context>

<specifics>
## Specific Ideas

- 构建脚本使用 **bash**（非 Python），与项目现有的 Makefile/shell 风格一致，依赖最小
- Docker 构建方式确保 Linux 二进制在 glibc 兼容环境中编译（`python:3.12-slim`），避免宿主机环境差异
- 版本号提取模式：`grep '^version' pyproject.toml | head -1 | sed 's/.*"\(.*\)"/\1/'`

</specifics>

<deferred>
## Deferred Ideas

| 项目 | 原因 | 目标 |
|------|------|------|
| BUILD-04: Docker Compose 部署 | docker-compose.yml 不适合当前架构；strix 主容器 + sandbox 编排需要重新设计运行时 | 后续版本 |
| macOS 二进制 | Phase 1 聚焦 Linux + Windows | v2.0 |
| Docker Hub vs ghcr.io 切换 | 当前沙箱镜像在 ghcr.io，迁移计划待定 | 后续讨论 |

</deferred>

---

*Phase: 01-build-release-pipeline*
*Context gathered: 2026-06-17 via discuss-phase*
