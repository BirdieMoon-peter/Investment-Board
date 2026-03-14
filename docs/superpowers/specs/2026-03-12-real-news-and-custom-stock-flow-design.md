# 真实新闻同步与自定义股票添加设计文档

日期：2026-03-12
状态：approved-for-planning

## 1. 背景

当前项目已经具备以下能力：
- watchlist 列表与 stock detail 页面已联通
- 手动单股同步链路可用
- 公告真实源已恢复
- 新闻真实源当前仅做了稳定降级，尚未真正恢复可用同步

当前缺口：
- 用户无法把本地数据集中不存在的股票代码直接加入系统
- 详情页虽然已有基本骨架，但“股票信息呈现”仍需围绕真实同步结果做增强
- 新闻同步需要从“安全降级为空”恢复为“真正可用的真实新闻同步”

## 2. 本轮目标

本轮目标围绕一条主流程完成：**Add and track**。

用户应当能够：
1. 在现有搜索/添加体验中添加股票
2. 当股票不在本地搜索结果中时，输入 `market + code` 发起真实查询
3. 由后端拉取基础股票信息并创建 security
4. 将该 security 加入 watchlist
5. 打开详情页查看核心股票信息
6. 手动触发同步后看到真实公告与真实新闻结果

## 3. 用户确认的关键决策

### 3.1 主流程
- 本轮以 **Add and track** 为主流程
- 原因：与当前 watchlist → detail → sync 结构最一致，改动集中，最适合快速交付

### 3.2 自定义股票代码添加方式
- 当本地搜索不到股票时，支持 **Fetch then create**
- 用户输入市场和股票代码
- 后端调用真实来源抓取基础股票信息
- 若抓取成功，则创建/更新 security 并加入 watchlist
- 若抓取失败，则返回明确错误，不创建空壳股票

### 3.3 股票信息呈现范围
- 采用 **Essential detail**
- 本轮重点展示：
  - market / code / name / industry
  - 最新价格快照（若有）
  - sync 状态反馈
  - 最新公告
  - 真实新闻

### 3.4 新闻恢复策略
- 采用 **Reliable first**
- 目标是优先保证“至少一个真实新闻源稳定可用”
- 不强求继续保留多个脆弱新闻源
- 如果第二来源未验证稳定，可以只保留一个稳定真实源

## 4. 总体方案

### 4.1 架构原则
本轮沿用现有分层与接口边界：
- 前端继续通过 watchlist 与 stocks API 交互
- 后端继续通过 repository + service + provider adapter 模式组织逻辑
- stock detail 的读取接口与 sync 写接口保持分离

### 4.2 需要新增或调整的能力

#### A. 自定义股票创建链路
新增“本地搜索未命中时的补充入口”：
- 前端在搜索区域显示“按市场+代码添加”的入口
- 后端新增按 `market + code` 查询真实股票基础信息的能力
- 后端将查询到的股票信息写入 `securities`
- 创建成功后复用现有 watchlist add 逻辑

#### B. 真实新闻同步恢复
调整现有 news provider 策略：
- 替换当前稳定返回空结果的失效新闻适配器实现
- 保留现有 aggregate provider 结构
- 将新闻源实现切换为“已验证可用的真实来源”
- 若存在多个候选源，只接入被验证稳定的实现

#### C. 详情页核心信息呈现增强
基于现有 `GET /api/stocks/{security_id}` 与 `POST /api/stocks/{security_id}/sync`：
- 强化 detail 页头部信息表达
- 明确显示股票身份信息与同步反馈
- 展示同步得到的最新公告和新闻
- 保持页面在无价格、无公告、无新闻时的显式空状态

## 5. 组件与边界

### 5.1 Backend

#### Security lookup / create service
新增一个专门服务负责：
- 校验 market / code
- 调用真实来源抓取股票基础信息
- 将结果标准化为本地 `Security`
- 使用现有 `SecurityRepository` 持久化

该服务只负责“查询并创建/更新 security”，不负责 watchlist 写入。

#### Watchlist API
保留现有 `POST /api/watchlist/items` 不变，用于已存在 security 的加入动作。

新增单独入口处理“自定义代码创建并加入 watchlist”，避免把两个责任混进同一已有接口。

#### News provider layer
保留 aggregate provider 结构：
- 继续让 sync service 不感知具体来源细节
- 在 raw news source adapter 下替换失效实现
- warning 机制保留，用于非致命源失败

### 5.2 Frontend

#### SearchBox / add flow
保留现有搜索体验，同时增加“本地没搜到时的自定义添加动作”：
- 用户先搜索
- 若无结果，可选择输入 market + code 添加
- 添加成功后自动刷新 watchlist
- 添加失败时显示明确错误

#### Stock detail page
保持当前 detail 页面结构不推翻，只做增强：
- header 展示更明确的 identity 信息
- sync 结果继续显示成功 / warning / error
- news 与 announcement 列表继续作为 detail 页面核心内容区

## 6. 数据流

### 6.1 自定义股票添加
1. 前端提交 `market + code`
2. 后端检查本地是否已有同 market/code 的 security
3. 若已有，直接加入 watchlist
4. 若不存在，调用真实 lookup provider 获取股票基础信息
5. 后端 upsert security
6. 后端加入 watchlist
7. 前端刷新 watchlist，并允许进入 detail

### 6.2 真实新闻同步
1. 用户打开 stock detail
2. 用户点击 sync
3. 后端读取 security 的 market/code
4. sync service 调用 aggregate news provider
5. provider 使用已验证稳定的真实新闻源抓取
6. 结果写入 news repository
7. 前端刷新 detail 并展示真实新闻

## 7. 错误处理

### 7.1 自定义代码添加失败
- market/code 非法：返回 422
- 真实 lookup 未找到该股票：返回可读错误
- 上游源异常：返回失败信息，不创建伪数据

### 7.2 新闻同步失败
- 若唯一真实新闻源失败：sync 返回 warning 或失败信息，页面显示同步反馈
- 若公告成功但新闻失败：继续保持 warning-aware partial success
- 若新闻为空但请求成功：显示明确空状态，不伪造内容

## 8. 测试策略

### Backend
- 自定义 market+code 创建接口测试
- 已存在 security 时的复用测试
- lookup 失败时不创建 security 的测试
- 真实新闻 provider 替换后的适配器测试
- stock sync API 在真实新闻返回时的集成测试

### Frontend
- 搜索无结果时显示自定义添加入口
- 自定义添加成功后刷新 watchlist
- 自定义添加失败时显示错误
- detail 页面展示核心股票信息
- sync 后展示真实新闻与同步反馈

## 9. 风险与控制

### 9.1 外部新闻源再次失效
- 采用 reliable-first 策略
- 只接入已验证稳定的来源
- 保持 provider 封装，后续可替换而不影响 sync service

### 9.2 自定义添加引入脏数据
- 只允许 fetch-then-create
- 不允许用户直接手填 name 创建空壳 security
- 本地持久化前统一做 market/code 标准化

### 9.3 范围扩张
- 本轮不做 holdings 管理
- 不做复杂公司画像扩展
- 不重构现有 detail 页面结构，只做必要增强

## 10. 下一步

下一步进入 implementation planning：
1. 先确定可用的真实股票 lookup 与新闻来源实现路径
2. 拆分 backend 的 custom add / real news provider / sync integration 任务
3. 再拆分 frontend 的 search fallback / custom add / detail presentation 任务
4. 最后执行并做端到端验收
