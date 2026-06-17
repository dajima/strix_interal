# Strix

## What This Is

Strix 是一个 AI 驱动的多智能体渗透测试工具，在 Docker 沙箱中自动执行安全评估。它使用 LLM 协调多个 AI agent，支持 web 应用、代码仓库、域名/IP 等多种目标类型，自动发现和报告漏洞。

## Core Value

AI agent 能够自主完成端到端渗透测试，在安全的 Docker 沙箱中运行真实安全工具，输出可操作的安全报告。

## Shipped: v1.0 一键构建发布 + XBEN 自动化评测 ✅

**Completed:** 2026-06-17 | **Phases:** 2 | **Requirements:** 10/10

<details>
<summary>v1.0 milestones shipped — click to expand</summary>

**Delivered:**
- 一键构建发布 — build_script/ 下 4 个 bash 脚本（build-binary.sh, build-sandbox.sh, build-all.sh, version.sh）
- Docker Hub 沙箱镜像 — usestrix/strix-sandbox:{VERSION}
- GitHub Actions CI/CD — workflow_dispatch + tag push 双触发发布
- XBEN 自动化评测 runner — --level/--tags/--limit/--timeout 过滤，run_infer_cli.py
- 结构化报告 — JSON (summary.json) + Markdown (report.md)，按难度和漏洞类型分类
- Docker 清理 — 每挑战后 docker compose down -v 保证无残留

**Deferred to v2.0:** Docker Compose 部署 (BUILD-04), macOS 二进制, CI 全量评测, 并行挑战执行

</details>

## Current State

All v1.0 requirements shipped. Next milestone should address:
- Docker Compose 部署（BUILD-04 — v1.0 中移除）
- CI 全量评测流水线（v2.0 范围）
- 并行挑战执行
- 自动化测试套件（项目当前零自动测试）

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

- ✓ Multi-agent 渗透测试引擎 (root + child agents) — strix v1.0.4
- ✓ Docker 沙箱隔离执行环境 — strix v1.0.4
- ✓ 15 个工具包 (shell, browser, proxy, reporting, web_search 等) — strix v1.0.4
- ✓ 多 LLM 提供商支持 (LiteLLM 路由) — strix v1.0.4
- ✓ XBEN 单挑战验证通过 (XBEN-001-24 SOLVED) — 2026-06-17

### Active

<!-- Current scope. Building toward these. -->

- [ ] 一键构建发布脚本（跨平台 Docker 部署）
- [ ] XBEN 自动化评测流水线

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- 新漏洞检测类型 — 本里程碑专注于构建/评测基础设施，新的漏洞能力属于后续里程碑
- Agent 并行优化 — 后续里程碑
- 非 Docker 部署方式 — 当前架构强依赖 Docker

## Context

**技术环境：**
- Python 3.12+，uv 包管理器，hatchling 构建
- openai-agents SDK 0.14.6（agent 编排）
- Docker Engine API（沙箱生命周期）
- LiteLLM 多提供商路由
- PyInstaller（单文件二进制打包）
- GitHub Actions（CI/CD）

**现有评测基础设施：**
- XBEN runner 代码：`xben-benchmarks/XBEN/run_infer_cli.py`
- 104 挑战数据：`validation-benchmarks/benchmarks/`
- 编译 Dockerfile：`Dockerfile.build`
- 沙箱 Dockerfile：`containers/Dockerfile`

**已知问题：**
- 零自动化测试 — 所有质量依赖静态分析
- CI 仅有 build-release workflow，无 PR 检查
- SDK 版本锁定（openai-agents==0.14.6），升级需手动合并
- containerd 兼容性问题（需 Docker Desktop 取消 "Use containerd"）

## Constraints

- **Runtime:** Docker 强依赖（`shutil.which("docker")` 检查，无 Docker 则退出）
- **Platform:** Python 3.12+ / Windows & Linux / Docker Engine
- **Dependencies:** openai-agents SDK 0.14.6 锁定（升级需合并 `docker_client.py` 中的自定义逻辑）
- **Security:** API key 通过环境变量提供，不硬编码

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Docker 作为唯一 sandbox 后端 | 隔离性、工具生态系统、跨平台一致性 | ✓ Good |
| LiteLLM 多提供商路由 | 避免 vendor lock-in，支持本地模型 | ✓ Good |
| PyInstaller 单文件二进制 | 简化分发，无需 Python 环境 | ✓ Good |
| openai-agents SDK 子类化扩展 | 复用 SDK 的 agent 编排、工具定义能力 | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-17 after v1.0 milestone start*
