# Requirements: Strix

**Defined:** 2026-06-17
**Core Value:** AI agent 自主完成端到端渗透测试，在 Docker 沙箱中运行真实安全工具，输出可操作的安全报告

## v1.0 Requirements

Requirements for v1.0 milestone: 一键构建发布 + XBEN 自动化评测

### Build & Release (BUILD)

- [ ] **BUILD-01**: 单命令构建脚本，支持编译 strix Linux 二进制文件（通过 PyInstaller 打包 `strix.spec`）
- [ ] **BUILD-02**: 单命令构建 Docker 沙箱镜像（基于 `containers/Dockerfile`）
- [ ] **BUILD-03**: 版本号从 `pyproject.toml` 统一提取，确保二进制、Docker 镜像和 Git tag 版本一致
- [ ] **BUILD-04**: Docker Compose 部署文件，用户可以通过 `docker compose up` 一条命令部署和运行 strix
- [ ] **BUILD-05**: `workflow_dispatch` 一键发布触发，在 GitHub Actions 中点击即可执行完整构建发布流程
- [ ] **BUILD-06**: GitHub Release 自动发布产物，包括 Linux 二进制文件、Docker 镜像推送、docker-compose.yml 和校验文件 (checksums)

### XBEN Evaluation (XBEN)

- [ ] **XBEN-01**: 挑战子集选择功能，支持按难度等级 (`--level`)、漏洞标签 (`--tags`) 和数量限制 (`--limit`) 过滤要运行的挑战
- [ ] **XBEN-02**: 通过率统计报告，按难度等级（Easy/Medium/Hard）和漏洞类型分类汇总通过/失败结果
- [ ] **XBEN-03**: 评测结果 JSON 汇总文件，记录每个挑战的 pass/fail 状态、耗时和发现的 flag
- [ ] **XBEN-04**: Docker 容器可靠清理，在挑战执行前后确保无残余容器/网络/卷（使用唯一项目名 + `docker compose down --volumes --remove-orphans`）
- [ ] **XBEN-05**: 评测结果 Markdown 报告生成，包含汇总统计、难度分解、漏洞类型分解和时间数据

## v2.0 Requirements

Deferred to future release. Tracked but not in current roadmap.

### CI/CD (CI)

- **CI-01**: GitHub Actions `xben-eval.yml` 工作流 (smoke-test 子集用于 PR 检查)
- **CI-02**: CI 成本上限控制
- **CI-03**: 全量评测 (scheduled/weekly `workflow_dispatch`)
- **CI-04**: 跨平台构建矩阵 (Windows + Linux)

### Build & Release (BUILD)

- **BUILD-07**: Windows 平台二进制构建 (`.exe`) 及跨平台 CI 矩阵
- **BUILD-08**: Docker 沙箱镜像 Registry 缓存 (减少重复构建时间)

### XBEN Evaluation (XBEN)

- **XBEN-06**: 并行挑战执行 (`--max-parallel N`)
- **XBEN-07**: Token 用量与 LLM API 成本追踪
- **XBEN-08**: 超时安全 checkpoint/resume (中断后可续跑)
- **XBEN-09**: Agent 详细执行轨迹日志
- **XBEN-10**: 评测历史对比 (多次评测之间对比得分变化)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| 新漏洞检测类型 | 本里程碑聚焦构建/评测基础设施，新漏洞属于独立里程碑 |
| Agent 并行优化 | 独立里程碑，需评测 baseline 数据后驱动 |
| 非 Docker 部署方式 | 当前架构强依赖 Docker |
| 实时 Dashboard | 过度工程化，JSON/Markdown 报告已覆盖需求 |
| CI 全量自动评测 | LLM 成本 ($300-2000/次) + GitHub Actions 6 小时限制，defer 至 v2.0 |
| Windows 二进制构建 | Linux 优先，Windows 设为 v2.0 |
| 多模型对比评测 | 需稳定 baseline 存在后才有意义 |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| BUILD-01 | Phase 1 | Pending |
| BUILD-02 | Phase 1 | Pending |
| BUILD-03 | Phase 1 | Pending |
| BUILD-04 | Phase 1 | Pending |
| BUILD-05 | Phase 1 | Pending |
| BUILD-06 | Phase 1 | Pending |
| XBEN-01 | Phase 2 | Pending |
| XBEN-02 | Phase 2 | Pending |
| XBEN-03 | Phase 2 | Pending |
| XBEN-04 | Phase 2 | Pending |
| XBEN-05 | Phase 2 | Pending |

**Coverage:**
- v1.0 requirements: 11 total
- Mapped to phases: 11
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-17*
*Last updated: 2026-06-17 after roadmap creation*
