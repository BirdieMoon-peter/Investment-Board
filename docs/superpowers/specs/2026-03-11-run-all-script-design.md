# 一键启动脚本设计文档

日期：2026-03-11
状态：approved-for-planning
来源：用户直接需求：为当前本地可运行项目提供一个一键启动脚本

说明：本文档定义一个最小开发态启动器，用于把当前已经完成的 frontend / backend / 本地数据库联调流程收敛成一个命令。它不改变现有模块边界，不替代部署方案。

## 1. 背景

当前项目已经具备本地运行条件：

- backend 可通过 `scripts/run_backend.sh` 启动
- frontend 可通过 `scripts/run_frontend.sh` 启动
- demo 数据可通过 `backend/scripts/seed_watchlist_demo.py` 或已安装命令初始化

但用户仍需要手动开多个终端、分步骤启动，操作成本较高。

## 2. 本轮目标

新增一个**根目录一键启动脚本**，让用户通过一条命令完成本地开发态启动。

该脚本目标为：

1. 可选 seed demo 数据
2. 启动 backend
3. 启动 frontend
4. 在终端输出可访问地址
5. 在用户按 `Ctrl+C` 时统一清理子进程

## 3. 非目标

本轮明确不做：

- 依赖安装
- Python 虚拟环境初始化
- Node 依赖安装
- Docker / Compose / 部署方案
- 生产环境进程守护
- 日志收集系统
- 复杂健康检查编排

## 4. 推荐方案

采用 **单脚本前台托管两个开发进程** 的方式。

### 4.1 核心行为

新增：

- `scripts/run_all.sh`

行为：

- 检查 backend Python 可执行文件存在
- 检查 frontend 依赖目录存在
- 若传入 `--seed`，先执行 demo seed
- 后台拉起 backend
- 后台拉起 frontend
- 当前脚本保持前台运行
- 捕获 `SIGINT` / `SIGTERM`，统一停止子进程

### 4.2 采用原因

- 对当前项目最小改动
- 最大化复用现有 `run_backend.sh` / `run_frontend.sh`
- 使用成本最低：一个命令即可运行
- 退出行为清楚，不会轻易留下孤儿进程

## 5. 输入与输出设计

### 5.1 输入

支持：

- 无参数：直接启动
- `--seed`：启动前先 seed demo 数据

### 5.2 输出

启动成功后输出：

- backend 地址：`http://127.0.0.1:8000`
- frontend 地址：`http://127.0.0.1:5173`
- 提示用户使用 `Ctrl+C` 停止全部服务

## 6. 失败处理

以下情况应直接失败退出：

- `backend/.venv/bin/python` 不存在
- `frontend/node_modules` 不存在
- seed 失败
- backend 进程提前退出
- frontend 进程提前退出

错误信息应尽量直白，指出缺什么、该检查什么。

## 7. 与现有脚本的关系

`run_all.sh` 不直接替代：

- `scripts/run_backend.sh`
- `scripts/run_frontend.sh`

而是作为更高一层的组合脚本，复用它们的已有行为。

## 8. 验证方式

至少验证：

1. `./scripts/run_all.sh` 可启动 frontend + backend
2. `./scripts/run_all.sh --seed` 可先 seed 再启动
3. 启动后终端输出访问地址
4. `Ctrl+C` 后两个子进程都会被清理

## 9. 下一步

下一步进入 implementation planning，并以最小脚本改动完成该一键启动能力。
