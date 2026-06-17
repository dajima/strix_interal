# Phase 1: Build & Release Pipeline - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-17
**Phase:** 1-build-release-pipeline
**Areas discussed:** 构建脚本方式, 构建产物目录结构, Docker Compose 部署设计, Release 产物与发布目标

---

## 构建脚本方式

| Option | Description | Selected |
|--------|-------------|----------|
| build_script/ 目录 | 所有构建/发布脚本放在独立目录下，每个脚本做一件事 | ✓ |
| 扩展现有 Makefile | 保留现有 Makefile 风格，添加构建目标 | |
| Python CLI 子命令 | 集成到 strix CLI 中 | |
| 纯 Docker 构建 | 仅 Docker 构建，不依赖本地 Python 环境 | |

**User's choice:** 新增一个 `build_script/` 目录

| Option | Description | Selected |
|--------|-------------|----------|
| 独立运行 | 每个脚本可单独运行，如 `bash build_script/build-binary.sh` | ✓ |
| 统一入口 + 子命令 | 单一入口脚本接受子命令 | |
| Makefile 入口 | Makefile 调用 build_script/ 脚本 | |

**User's choice:** 每个脚本独立可运行

| Option | Description | Selected |
|--------|-------------|----------|
| Docker 内构建 | 复用 Dockerfile.build 容器内编译 | ✓ |
| 本地构建 | 需要本地 Python + uv + pyinstaller | |
| 自动检测 | 优先 Docker，回退本地 | |

**User's choice:** Docker 内构建，利用现有 Dockerfile.build

| Option | Description | Selected |
|--------|-------------|----------|
| CI 复用构建脚本 | GitHub Actions 直接调用 build_script/ 脚本 | ✓ |

**User's choice:** CI 复用构建脚本，本地和 CI 一致

**Notes:** 构建脚本使用 bash（非 Python），CI workflow 和本地开发使用同一套脚本

---

## 构建产物目录结构

| Option | Description | Selected |
|--------|-------------|----------|
| Claude 决定 | 我来设计 dist/ 目录结构 | ✓ |

**User's choice:** 用户让 Claude 决定

**Notes:** `dist/` 扁平结构：二进制文件 + docker-compose.yml + checksums.txt。版本号从 pyproject.toml 提取嵌入文件名。Docker 镜像直接推送无需本地 tar 导出。

---

## Docker Compose 部署设计

| Option | Description | Selected |
|--------|-------------|----------|
| 移除 BUILD-04 | 放弃 docker-compose.yml 需求 | ✓ |
| Docker run 单行命令 | 替代 docker compose 的简化方案 | |

**User's choice:** 用户评估后认为 docker-compose.yml 不适合当前架构，放弃该需求

**Notes:** BUILD-04 从 Phase 1 移除。strix 主容器 + sandbox 容器的编排需要重新设计运行时架构，推迟至后续版本。

---

## Release 产物与发布目标

| Option | Description | Selected |
|--------|-------------|----------|
| Linux 优先 | 仅构建 Linux x86_64 二进制 | |
| Linux + Windows | 保留两个平台 | ✓ |
| 多平台矩阵 | 保留现有 4 平台矩阵 | |

**User's choice:** 同时保留 Linux 和 Windows

| Option | Description | Selected |
|--------|-------------|----------|
| Docker Hub | 沙箱镜像推送至 Docker Hub | ✓ |
| ghcr.io | 继续使用 GitHub Container Registry | |
| 仅二进制 | 不推送 Docker 镜像 | |

**User's choice:** Docker Hub

| Option | Description | Selected |
|--------|-------------|----------|
| Claude 决定发布触发 | 用户未使用过 GitHub Release | ✓ |

**User's choice:** 用户让 Claude 决定发布触发方式

**Notes:** Claude 推荐双触发：`workflow_dispatch` + `push tags: v*`。发布流程：提取版本号 → 构建 Linux + Windows 二进制 → 构建 Docker 镜像并推送到 Docker Hub → 创建 GitHub Release（含 `.tar.gz`/`.zip` + `checksums.txt`）

---

## Claude's Discretion

- 构建产物 `dist/` 目录结构设计
- GitHub Release 双触发策略（workflow_dispatch + tag push）
- `build_script/` 下脚本的具体参数设计和错误处理

## Deferred Ideas

- BUILD-04: Docker Compose 部署 — 推迟至后续版本，需重新设计运行时架构
- macOS 平台二进制 — Phase 1 聚焦 Linux + Windows
- Docker Hub vs ghcr.io 切换 — 当前沙箱镜像在 ghcr.io，迁移计划待定
