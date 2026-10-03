# 币安USDT永续合约涨幅榜监控系统

> 每30分钟自动抓取币安USDT永续合约涨幅榜第一名，结合 Coinglass 专业数据 + 通义千问 LLM + RAG 长期记忆，生成结构化行情研判报告。
>
> ⚠️ **免责声明**：本系统仅为行情数据统计与复盘分析工具，不构成任何投资建议。加密货币合约自带高杠杆，风险极高。

## 架构总览

```
cron-job.org (每30分钟)
    │  GET /api/task/trigger
    ▼
Vercel Serverless (Python FastAPI)  ← 轻量触发，仅写入pending任务，<1s返回
    │
    ▼
Supabase PostgreSQL + pgvector  ← 业务数据 + RAG向量记忆
    │
    ▼
Supabase Edge Function (Node.js)  ← 核心逻辑：拉Coinglass数据 → 过滤合约 → RAG检索 → 千问分析 → 写库
    │
    ▼
Vue 前端看板  ← 实时观测 + 历史查询 + 复盘对比
```

## 为什么这样设计（适配 Vercel 免费版）

| 限制 | 解决方案 |
|------|----------|
| Vercel Hobby 无内置 Cron | 用 cron-job.org 免费定时服务，每30分钟GET触发接口 |
| Vercel Serverless 最大10s | 触发接口只写一条pending记录；重逻辑放 Supabase Edge Function（最长60s） |
| Vercel 无持久化磁盘 | 数据全部存 Supabase PostgreSQL；向量用 pgvector 扩展 |
| 免费额度 | Supabase 免费层 500MB 数据库 + Edge Function 50万次/月，足够前期 |

## 目录结构

```
binance-futures-watcher/
├── api/                          # Vercel Serverless 后端（Python）
│   └── task/
│       └── trigger.py            # 轻量触发接口：cron-job.org调用，写入pending任务
├── supabase/
│   └── functions/
│       └── market_analysis/      # Supabase Edge Function（核心业务逻辑）
│           └── index.js
├── frontend/                     # Vue 前端看板
│   └── src/
├── sql/
│   └── schema.sql                # 数据库建表SQL（pgvector + 业务表 + 向量表）
├── docs/                         # 项目文档
├── .env.example                  # 环境变量模板（复制为.env后填值）
├── .gitignore
├── vercel.json                   # Vercel部署配置
├── requirements.txt              # Python依赖
└── README.md
```

## 数据流（每一轮观测）

1. cron-job.org 每30分钟 GET `https://你的域名/api/task/trigger`
2. Vercel 接口在 `market_observation` 表插入一条 `task_status='pending'` 记录，立即返回
3. Supabase Edge Function 轮询/被触发，取最早一条 pending 任务
4. 调用 Coinglass 中转站 API，获取币安USDT永续合约涨幅榜
5. 过滤：剔除股票合约、ETF合约，只保留USDT永续
6. 按24h涨幅排序，取第一名（可配置TOP_N）
7. 把本次行情数据更新进 `market_observation`
8. 调用千问 `text-embedding-v1` 生成向量，在 pgvector 中检索 Top3 相似历史记录（RAG）
9. 组装【系统提示词 + 实时数据 + RAG历史片段】，调用千问 `qwen-turbo` 生成分析报告
10. 报告写入 `market_observation.llm_report`，状态改为 `completed`
11. 报告文本向量化，写入 `observation_embedding`，供后续RAG检索

## 快速开始（本地开发）

### 1. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env，填入 Supabase / Coinglass / DashScope 的真实密钥
```

### 2. 初始化数据库
在 Supabase SQL Editor 中执行 `sql/schema.sql`

### 3. 本地运行后端
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn api.main:app --reload
```

### 4. 部署（需经你确认后执行）
- Vercel：导入 Git 仓库，配置环境变量
- Supabase Edge Function：`supabase functions deploy market_analysis`
- cron-job.org：新建定时任务，URL 填 Vercel 触发接口，cron 表达式 `*/30 * * * *`

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | Vue 3 + Vite |
| 后端触发 | Python FastAPI (Vercel Serverless) |
| 核心逻辑 | Node.js (Supabase Edge Function) |
| 数据库 | Supabase PostgreSQL + pgvector |
| LLM | 通义千问 qwen-turbo + text-embedding-v1 |
| 定时 | cron-job.org |
| 部署 | Vercel (前端+触发) + Supabase (DB+Edge Function) |
