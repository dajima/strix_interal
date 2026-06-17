# 支持文档 — Strix v1.0

- [Windows 安装脚本开发确认.xlsx](/d%3A/AI/strix_interal/Windows%20安装脚本开发确认.xlsx)
- [GitHub](https://github.com/usestrix/strix)
- `.planning/milestones/v1.0-ROADMAP.md` — 里程碑归档

## 快速安装

### 环境要求
- **Python 3.12+**（本地开发/Windows 构建）
- **Docker**（Linux 构建 + 沙箱运行）
- **Git Bash**（Windows 上运行 shell 脚本）

### 安装依赖
```bash
pip install pyinstaller pytest
pip install "openai-agents[litellm]==0.14.6" pydantic rich docker textual requests cvss
```

---

## 构建

### 一键构建所有平台
```bash
# 构建 Linux + Windows 两个平台
bash build_script/build-binary.sh --target all
```

### 按平台构建
```bash
# 仅 Linux（通过 Docker 构建，需要 Docker）
bash build_script/build-binary.sh --target linux

# 仅 Windows（本地 PyInstaller，需要 Python 3.12+）
bash build_script/build-binary.sh --target windows

# 自动检测当前平台
bash build_script/build-binary.sh
```

### 构建沙箱 Docker 镜像
```bash
# 仅构建（本地）
bash build_script/build-sandbox.sh

# 构建并推送到 Docker Hub
bash build_script/build-sandbox.sh --push
```

### 构建产物
| 文件 | 平台 | 说明 |
|------|------|------|
| `dist/release/strix-{VERSION}-linux-x86_64` | Linux | ELF 64-bit 可执行文件 |
| `dist/release/strix-{VERSION}-linux-x86_64.tar.gz` | Linux | 压缩包 |
| `dist/release/strix-{VERSION}-windows-x86_64.exe` | Windows | PE32+ 可执行文件 |
| `dist/release/strix-{VERSION}-windows-x86_64.zip` | Windows | 压缩包 |

---

## 验证

### 验证构建产物
```bash
# 检查 Linux 二进制格式
file dist/release/strix-{VERSION}-linux-x86_64
# 应输出: ELF 64-bit LSB executable, x86-64, for GNU/Linux

# 检查 Windows 二进制格式
file dist/release/strix-{VERSION}-windows-x86_64.exe
# 应输出: PE32+ executable for MS Windows, x86-64

# 测试 Windows 二进制（Windows 上）
./dist/release/strix-{VERSION}-windows-x86_64.exe --version
# 应输出: strix {VERSION}

# 测试 Linux 二进制（Linux 上）
./dist/release/strix-{VERSION}-linux-x86_64 --version
# 应输出: strix {VERSION}
```

### 运行测试
```bash
# XBEN runner 单元测试
pytest xben-benchmarks/XBEN/tests/ -v

# 当前状态: 65 passed, 0 failed
```

---

## XBEN 评测

### 前置条件
1. 已安装 Docker 并运行
2. 已构建 strix 二进制（或设置 `STRIX_BIN` 指向已有二进制）
3. 已构建沙箱镜像（或设置 `STRIX_IMAGE` 指向已有镜像）

### 运行评测
```bash
# 查看所有选项
python xben-benchmarks/XBEN/run_infer_cli.py --help

# 运行全部 104 个挑战
python xben-benchmarks/XBEN/run_infer_cli.py

# 仅运行 Easy 难度的前 5 个挑战
python xben-benchmarks/XBEN/run_infer_cli.py --level 1 --limit 5

# 仅运行 XSS 或 SQLi 相关挑战
python xben-benchmarks/XBEN/run_infer_cli.py --tags "xss,sql_injection"

# 指定超时时间（每个挑战 10 分钟）
python xben-benchmarks/XBEN/run_infer_cli.py --timeout 600

# 指定输出目录
python xben-benchmarks/XBEN/run_infer_cli.py --output-dir my_results/

# 组合使用
python xben-benchmarks/XBEN/run_infer_cli.py --level 2 --tags "idor,ssrf" --limit 10 --timeout 900
```

### 评测输出
| 文件 | 说明 |
|------|------|
| `runs/{timestamp}/summary.json` | 完整 JSON 结果（元数据、汇总统计、按难度/标签分类、每挑战详情） |
| `runs/{timestamp}/report.md` | Markdown 报告（汇总表、按难度分解、按漏洞类型分解、每挑战结果） |
| `runs/{timestamp}/run_XBEN-xxx/result.json` | 单个挑战的详细结果 |

### 可用标签
常用漏洞标签：`idor`, `xss`, `sql_injection`, `nosqli`, `ssrf`, `rce`, `graphql`, `default_credentials`, `command_injection`, `lfi`, `xxe` 等。
（运行 `python xben-benchmarks/XBEN/run_infer_cli.py --help` 获取完整列表）

### 难度等级
| 数值 | 标签 | 说明 |
|------|------|------|
| 1 | Easy | 基础漏洞，单步利用 |
| 2 | Medium | 需要组合利用或绕过的漏洞 |
| 3 | Hard | 复杂漏洞，需要多步利用链 |
| 4-5 | Expert | 高级挑战 |

---

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `STRIX_BIN` | 自动发现（`dist/` 下最新二进制）或 `strix` | strix 二进制路径 |
| `STRIX_IMAGE` | `usestrix/strix-sandbox:latest` | 沙箱 Docker 镜像 |
| `DOCKERHUB_USERNAME` | （无） | Docker Hub 用户名（推送沙箱镜像需要） |
| `DOCKERHUB_TOKEN` | （无） | Docker Hub 访问令牌（推送沙箱镜像需要） |
| `LLM_API_KEY` | （无） | LLM API 密钥 |

---

## GitHub Release（CI）

### 手动触发
1. 打开 [GitHub Actions → Build & Release](https://github.com/usestrix/strix/actions/workflows/build-release.yml)
2. 点击 "Run workflow"
3. 选择分支后触发

### 自动触发
推送以 `v` 开头的 tag 自动触发：
```bash
git tag -a v1.0.5 -m "Release v1.0.5"
git push origin v1.0.5
```

### CI 构建矩阵
| Runner | 构建命令 | 产物 |
|--------|---------|------|
| ubuntu-latest | `build-binary.sh --target linux` | `strix-{v}-linux-x86_64.tar.gz` |
| windows-latest | `build-binary.sh --target windows` | `strix-{v}-windows-x86_64.zip` |
| sandbox (ubuntu) | `build-sandbox.sh --push` | `usestrix/strix-sandbox:{v}` |

---

## 常用命令速查

```bash
# 构建
bash build_script/build-binary.sh --target all    # 构建全部平台
bash build_script/build-sandbox.sh                # 构建沙箱镜像
bash build_script/build-all.sh                    # 构建 + 校验

# 测试
pytest xben-benchmarks/XBEN/tests/ -v             # 全部测试 (65)

# 评测
python xben-benchmarks/XBEN/run_infer_cli.py --limit 1      # 快速验证
python xben-benchmarks/XBEN/run_infer_cli.py --level 2      # Medium 难度
python xben-benchmarks/XBEN/run_infer_cli.py --tags "xss"   # 按标签过滤

# 验证
./dist/release/strix-*-windows-x86_64.exe --version         # 检查版本
file dist/release/*                                          # 检查二进制格式
sha256sum -c dist/checksums.txt                             # 校验完整性
```
