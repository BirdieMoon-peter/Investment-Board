# 参与开发

本项目使用 Python 3.12+、Node.js 22.12+ 和 npm。启动脚本适用于 macOS/Linux；Windows 可在 WSL 中运行。首次安装和启动步骤见 [README](README.md)。

## 本地验证

在项目根目录安装开发依赖：

```bash
python3.12 -m venv backend/.venv
backend/.venv/bin/python -m pip install -e 'backend[dev]'
npm ci --prefix frontend
```

运行与 CI 对应的检查：

```bash
DATABASE_URL=sqlite:// INVESTMENT_BOARD_ENV_FILE=/dev/null PYTHONPATH=backend \
  backend/.venv/bin/python -m pytest backend/tests -q
INVESTMENT_BOARD_ENV_FILE=/dev/null PYTHONPATH=backend \
  backend/.venv/bin/python -m pytest scripts/tests -q
npm test --prefix frontend
npm run build --prefix frontend
bash -n scripts/run_all.sh scripts/run_backend.sh scripts/run_frontend.sh scripts/smoke_watchlist.sh
```

后端测试使用内存或临时数据库，并以测试响应替代外部行情和 AI 服务。启动脚本测试会使用临时数据库、子进程和本机回环端口，因此需要允许本地端口绑定。请在没有导出个人 AI 配置的终端运行测试；配置测试会自行设置测试值。

需要验证真实启动入口时，运行 `INVESTMENT_BOARD_ENV_FILE=/dev/null ./scripts/smoke_watchlist.sh`。它会创建独立的临时数据库、申请空闲端口，并在退出时清理自己的进程和文件。它验证本地自选股流程，不验证实时行情或真实 AI 服务的可用性。

## 提交规范

- 开始前阅读 `docs/00-workflow.md`、`docs/01-roadmap.md`、`docs/02-module-registry.md`、`memory/MEMORY.md`、`memory/progress.md` 和当前模块文档。
- 保持改动聚焦于当前模块；需求、接口或验证方式变化时，同步相应文档。
- 在提交说明中写清问题、行为变化和实际运行的验证。模块进入 `done` 前完成独立审查和验证。
- 行情、新闻与 AI 接口使用可复现的测试响应。共享演示和截图使用独立的演示数据。
- 不提交 `.env.local`、密钥、个人自选股/持仓数据库、依赖目录、构建产物或原始验证记录。共享文档也应去除个人账户、持仓及本机路径信息。

CI 会运行后端、启动脚本、前端测试和生产构建。CI 通过只说明这些检查通过；涉及外部数据或 AI 的行为需另行记录验证条件和结果。
