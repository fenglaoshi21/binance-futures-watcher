-- ============================================================
-- 币安USDT永续合约涨幅榜监控系统 - 数据库 Schema
-- 数据库：Supabase PostgreSQL + pgvector
-- 执行顺序：在 Supabase SQL Editor 中依次执行
-- ============================================================

-- 1. 开启向量扩展（RAG 长期记忆用）
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. 主业务数据表：每30分钟一条观测记录
CREATE TABLE IF NOT EXISTS market_observation (
  id              BIGSERIAL PRIMARY KEY,
  observe_time    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  symbol          TEXT,                          -- 交易对，如 BTCUSDT
  change_24h      NUMERIC,                       -- 24h涨跌幅(%)
  volume_24h      NUMERIC,                       -- 24h成交量(USDT)
  open_interest   NUMERIC,                       -- 持仓量OI
  funding_rate    NUMERIC,                       -- 资金费率
  long_liq_24h    NUMERIC,                       -- 24h多头爆仓
  short_liq_24h   NUMERIC,                       -- 24h空头爆仓
  raw_data        JSONB,                         -- 中转站API返回的完整原始JSON
  llm_report      TEXT,                          -- 千问生成的分析报告
  task_status     TEXT DEFAULT 'pending',        -- pending / processing / completed / fail
  error_msg       TEXT,                          -- 失败时的错误信息
  note            TEXT
);

-- 3. RAG向量记忆表：存储每次报告的embedding，用于检索相似历史行情
CREATE TABLE IF NOT EXISTS observation_embedding (
  id           BIGSERIAL PRIMARY KEY,
  market_id    BIGINT REFERENCES market_observation(id) ON DELETE CASCADE,
  embedding    vector(1536),                     -- 千问 text-embedding-v1 输出维度1536
  report_text  TEXT,                             -- 向量化的报告文本
  create_time  TIMESTAMPTZ DEFAULT NOW()
);

-- 4. 索引
CREATE INDEX IF NOT EXISTS idx_observe_time     ON market_observation(observe_time DESC);
CREATE INDEX IF NOT EXISTS idx_task_status      ON market_observation(task_status);
CREATE INDEX IF NOT EXISTS idx_embedding_market ON observation_embedding(market_id);
-- HNSW 向量索引，加速余弦相似度检索（数据量大时性能提升明显）
CREATE INDEX IF NOT EXISTS idx_embedding_vector ON observation_embedding USING hnsw (embedding vector_cosine_ops);

-- 5. 注释
COMMENT ON TABLE market_observation IS '每轮观测的原始行情+LLM分析报告';
COMMENT ON TABLE observation_embedding IS 'RAG向量记忆，报告文本的1536维embedding';
