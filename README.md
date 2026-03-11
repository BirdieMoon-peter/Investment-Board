# Investment Board

一个面向本地运行的自选股 MVP 项目，目前已经打通了一个小型端到端链路：

- **数据层**：SQLModel + SQLite
- **后端**：FastAPI
- **前端**：React + Vite + TypeScript
- **本地运行方式**：seed 好的 SQLite 数据库 + uvicorn + Vite 开发服务器

## 当前 MVP 范围

当前仓库已经实现的能力：

- 按股票代码或名称搜索证券
- 添加到自选股
- 从自选股中移除
- 渲染自选股列表
- 显示空状态、错误状态、无搜索结果状态、缺失行情状态
- 提供本地开发和验收用的 demo seed 数据

当前 MVP 暂不包含：

- 个股详情页
- 分组自选股
- AI 分析界面
- 持仓 / 组合管理
- 新闻 / 公告真实数据面板
- 部署基础设施

## 项目当前状态

当前模块状态如下：

- `data-layer`: done
- `backend`: done
- `frontend`: done
- `scripts`: done

## 仓库结构

```text
backend/   FastAPI 应用、SQLModel 模型、repository、seed / runtime 辅助代码、API 测试
frontend/  React + Vite 应用、UI 组件、前端测试
docs/      workflow、roadmap、module registry、模块文档、plans / specs
memory/    当前进度与稳定决策记录
scripts/   本地启动 backend / frontend 和 smoke 检查的脚本
```

## 环境要求

- **Python 3.12**：用于 backend
- **Node.js + npm**：用于 frontend

## 本地初始化

### 1. 创建 backend 虚拟环境

在仓库根目录执行：

```bash
cd backend
python3.12 -m venv .venv
./.venv/bin/python -m pip install -e ".[dev]"
cd ..
```

### 2. 安装 frontend 依赖

```bash
npm install --prefix frontend
```

## 初始化 demo 数据

支持两种方式。

### 方式一：使用安装后的 backend 命令入口（推荐）

```bash
cd backend
./.venv/bin/seed-watchlist-demo
cd ..
```

### 方式二：直接按模块方式执行

```bash
cd backend
PYTHONPATH="$(pwd)" ./.venv/bin/python -m app.db.services.seed_demo_data_cli
cd ..
```

默认会向本地 SQLite 数据库写入 demo 数据：

```text
investment_board.db
```

## 本地启动项目

### 启动 backend

在仓库根目录执行：

```bash
./scripts/run_backend.sh
```

默认监听地址：

```text
http://127.0.0.1:8000
```

### 启动 frontend

在另一个终端里、同样在仓库根目录执行：

```bash
./scripts/run_frontend.sh
```

默认监听地址：

```text
http://127.0.0.1:5173
```

前端开发环境已经配置了 `/api` 代理，会把请求转发到本地 backend。

## 本地 smoke 验证

### 一键 smoke 脚本

```bash
./scripts/smoke_watchlist.sh
```

这个脚本会自动完成：

- 创建一个单独的 smoke 数据库
- seed demo 证券、行情和自选股数据
- 临时启动 backend
- 检查关键 watchlist API 是否能正确返回 JSON

### 直接检查接口

如果 backend 已经启动，可以直接执行：

```bash
curl -s http://127.0.0.1:8000/api/watchlist/items
curl -s "http://127.0.0.1:8000/api/watchlist/securities/search?query=Ping"
```

## 自动化验证命令

### Backend API 测试

```bash
PYTHONPATH="/Users/peter/Desktop/Investment Board/backend" \
"/Users/peter/Desktop/Investment Board/backend/.venv/bin/python" \
-m pytest "/Users/peter/Desktop/Investment Board/backend/tests/api" -q
```

### Backend 数据层测试

```bash
PYTHONPATH="/Users/peter/Desktop/Investment Board/backend" \
"/Users/peter/Desktop/Investment Board/backend/.venv/bin/python" \
-m pytest "/Users/peter/Desktop/Investment Board/backend/tests/db" -q
```

### Frontend 测试

```bash
npm test --prefix frontend
```

## 当前 API 列表

### 搜索证券

```text
GET /api/watchlist/securities/search?query=<text>
```

### 获取自选股列表

```text
GET /api/watchlist/items
```

### 添加自选股

```text
POST /api/watchlist/items
Content-Type: application/json
{
  "security_id": 1
}
```

### 删除自选股

```text
DELETE /api/watchlist/items/{security_id}
```

## 手工验收清单

如果要做一轮快速手工验收，可以按这个顺序：

1. seed demo 数据
2. 用 `./scripts/run_backend.sh` 启动 backend
3. 用 `./scripts/run_frontend.sh` 启动 frontend
4. 打开 `http://127.0.0.1:5173`
5. 搜索 `Ping`
6. 把结果添加到自选股
7. 确认列表刷新
8. 再移除该条目，确认列表再次刷新

## 项目事实来源

项目 workflow 和实现状态以仓库内的 `docs/` 与 `memory/` 为准，尤其是：

- `docs/00-workflow.md`
- `docs/01-roadmap.md`
- `docs/02-module-registry.md`
- `docs/modules/*.md`
- `memory/MEMORY.md`
- `memory/progress.md`

## 说明

- 当前项目主要针对**本地开发与本地验收**，并不是部署版本。
- 虽然自动化测试和本地 smoke 都已经通过，但用户回来后做一轮浏览器级手工验收仍然很有价值。
