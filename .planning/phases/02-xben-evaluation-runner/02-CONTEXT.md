# Phase 2: XBEN Evaluation Runner - Context

**Gathered:** 2026-06-17
**Status:** Ready for planning
**Source:** Smart Discuss (autonomous mode)

<domain>
## Phase Boundary

Phase 2 交付 XBEN 自动化评测 runner：基于现有 `xben-benchmarks/XBEN/run_infer_cli.py` 扩展，支持 CLI 驱动的挑战筛选（`--level`/`--tags`/`--limit`），可靠的 Docker 生命周期管理（每挑战后 `docker compose down -v`），以及结构化的 pass/fail 报告（JSON + Markdown），按难度等级和漏洞类型分类。
</domain>

<decisions>
## Implementation Decisions

### CLI 与 Runner 架构
- **D-01:** XBEN runner 基于现有 `xben-benchmarks/XBEN/run_infer_cli.py` 扩展 — 该文件已有完整的 Docker Compose 编排、flag 检测、JSON 输出逻辑
- **D-02:** CLI 入口保持独立脚本 `run_infer_cli.py`（评测工具，非渗透测试核心功能），不集成到 `strix` CLI 子命令
- **D-03:** 报告输出到 `xben-benchmarks/XBEN/runs/` 目录（已有），每次运行按时间戳建子目录，JSON + Markdown 并存
- **D-04:** 参数风格保持 **argparse**（已有），新增 `--level`（1-5）、`--tags`（逗号分隔）、`--limit`（已有）

### 报告与输出格式
- **D-05:** JSON 结果文件格式：`{run_metadata, summary: {total, solved, unsolved, timeout, errored, solve_rate}, results: [{benchmark_id, name, level, tags, status, duration_seconds, flag_extracted}]}` — 扩展已有单挑战 JSON
- **D-06:** Markdown 报告包含：汇总统计表、按难度等级分解（Easy=1/Medium=2/Hard=3）、按漏洞类型分解（sql_injection/xss/idor 等）、每个挑战的执行状态
- **D-07:** 报告语言：英文（与现有 strix 文档和代码注释一致）

### Docker 清理与错误处理
- **D-08:** **每挑战后强制 `docker compose down -v`**（已有此逻辑在 finally 块中）— 确保无孤儿容器/网络/卷
- **D-09:** 挑战超时保持 **3600s 硬超时**（已有 `TIMEOUT=3600`），超时记为 status `"timeout"`（区别于 unsolved）
- **D-10:** 单个挑战失败**不终止**全量运行 — 已有 try/except 跳过失败挑战继续下一个

### Claude's Discretion
- 报告表格的具体列顺序和样式（实现者灵活决定）
- 终端输出的进度展示格式（是否使用彩色输出、进度条等）
- Markdown 报告中的具体描述性文字
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 现有评测代码
- `xben-benchmarks/XBEN/run_infer_cli.py` — **核心改造目标**：已有 Docker Compose 编排、flag 检测、JSON 输出、`--benchmarks`/`--limit` 参数
- `xben-benchmarks/XBEN/run_infer.py` — run_infer 的原始 Python SDK 版本（可能已过时）

### Strix 核心
- `strix/interface/cli.py` — strix CLI 入口，了解 `--target`/`--instruction`/`--non-interactive` 等参数
- `strix/config/settings.py` — strix 配置（`STRIX_IMAGE`）

### 基准数据
- `validation-benchmarks/benchmarks/` — 104 个 XBEN 挑战，每个含 `benchmark.json`（level/tags/name/description）、`docker-compose.yml`、`.env`（FLAG）
- 难度分布：Easy(1)≈12, Medium(2)≈83, Hard(3)≈4（以 benchmark.json 中 level 字段为准）
- 标签分布于 benchmark.json tags 字段：idor, sql_injection, xss, nosqli, graphql, default_credentials, ssrf, rce 等多种

### 规划文件
- `.planning/REQUIREMENTS.md` — XBEN-01~05 需求定义
- `.planning/ROADMAP.md` — Phase 2 目标与 6 个成功标准
- `.planning/PROJECT.md` — 项目技术栈与约束

### Phase 1 产出（依赖）
- `build_script/build-binary.sh` — strix 二进制构建
- `build_script/build-sandbox.sh` — Docker 沙箱镜像构建
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`run_infer_cli.py`** — 170 行的完整评测脚本，函数包括 `read_flag()`/`rewrite_compose()`/`docker_compose()`/`run_strix_cli()`/`check_flag()`/`wait_for_target()`/`run_one()`/`collect_benchmarks()`
- **Docker Compose 编排逻辑** — 已验证的端口映射重写、`docker compose up/down`、`--remove-orphans -v` 清理
- **Flag 检测** — `check_flag()` 在 strix 输出目录中搜索预期 flag，已在 XBEN-001-24 验证有效

### Integration Points
- **strix 二进制调用**：`STRIX_BIN` 环境变量（默认 `strix`），参数 `--target`/`--instruction`/`--non-interactive`/`--scan-mode deep`
- **Docker 沙箱**：`STRIX_IMAGE` 环境变量（默认 `strix-sandbox:dev`）
- **端口映射**：`host.docker.internal` + 动态端口分配 + `.docker-compose.xben.yml` 重写

### Established Patterns
- **Python 3.12+** 项目，使用标准库 argparse + subprocess + json
- **Docker 依赖**：`shutil.which("docker")` 检查（strix 核心约定）
- **输出目录**：`xben-benchmarks/XBEN/runs/` 已创建
</code_context>

<specifics>
## Specific Ideas

- 报告应反映评测运行的整体质量：solve rate 是核心指标，但 timeouts 和 errors 也应单独列出
- 难度分类映射：benchmark.json 中 level 值为 1/2/3 → Easy/Medium/Hard
- `--level` 参数接受单个数字（1-5），`--tags` 接受逗号分隔的标签列表
- 报告生成在最后统计汇总结果时进行 — runner 收集所有单挑战 JSON 后，在后处理步骤中生成更多报告格式
</specifics>

<deferred>
## Deferred Ideas

| 项目 | 原因 | 目标 |
|------|------|------|
| CI 全量评测 (v2.0) | LLM 成本 ($300-2000/次) + GitHub Actions 6h 限制 | v2.0 |
| 并行挑战执行 | 当前 `run_infer_cli.py` 串行执行，并行需处理端口冲突和 Docker 资源竞争 | v2.0 |
| Token 用量追踪 | 需 strix 核心支持输出 token 统计 | v2.0 |
| 评测历史对比 | 需多轮评测数据积累后才有意义 | v2.0 |
| Agent 详细执行轨迹 | 需要更深的 strix 日志集成 | v2.0 |
| `--timeout` 可配置参数 | 当前 3600s 硬编码已足够评测用途 | v3.0 |

</deferred>

---

*Phase: 02-xben-evaluation-runner*
*Context gathered: 2026-06-17 via smart discuss (autonomous mode)*
