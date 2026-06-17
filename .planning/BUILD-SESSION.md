# Strix 编译构建与 XBEN 评测 - 会话缓存 v3

## 日期
2026-06-17

## ✅ 已完成

### 编译构建
- Strix Linux 二进制: D:\AI\strix_interal\dist\strix (61.6 MB)
- 编译 Docker 镜像: strix-build:latest

### 评测环境
- XBEN runner 代码: D:\AI\strix_interal\xben-benchmarks\XBEN\
- 104 挑战数据: D:\AI\strix_interal\validation-benchmarks\benchmarks\
- CLI 适配 eval runner: run_infer_cli.py (最终版，语法通过)
- pyyaml 已安装

## ❌ 阻塞项

### Docker 沙箱限制
- Codex 沙箱阻止 Docker 命名管道 (npipe://docker_engine)
- 无法从沙箱内执行 docker build/run/compose
- 用户必须在自己终端执行 Docker 命令

### containerd 兼容性
- Docker Desktop 需取消勾选 "Use containerd"
- run_infer_cli.py 已加 DOCKER_BUILDKIT=0 兜底

## 🔧 下一步（用户在自己终端执行）

`powershell
cd D:\AI\strix_interal\xben-benchmarks\XBEN
python run_infer_cli.py --limit 1     # 测试一个挑战
python run_infer_cli.py               # 全量 104 个
`

前置条件:
- Docker Desktop 运行中
- 设置 STRIX_LLM 和 LLM_API_KEY 环境变量
- 沙箱镜像 strix-sandbox:dev 已构建（可选，strix 内部会自动处理）

## 关键路径
- D:\AI\strix_interal\Dockerfile.build（编译用）
- D:\AI\strix_interal\containers\Dockerfile（沙箱镜像）
- D:\AI\strix_interal\dist\strix（Linux 二进制）
- D:\AI\strix_interal\xben-benchmarks\XBEN\run_infer_cli.py（评测入口）
- D:\AI\strix_interal\validation-benchmarks\benchmarks\（104 挑战）
- D:\AI\strix_interal\run-xben-setup.bat（自动构建脚本）
