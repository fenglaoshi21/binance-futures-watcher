-- ============================================================
-- RAG 向量检索函数（在 Supabase SQL Editor 中执行）
-- 用于 pgvector 余弦相似度检索，匹配最相似的历史观测记录
-- ============================================================

-- 删除旧函数（如果存在）
DROP FUNCTION IF EXISTS match_observations(vector, int);

-- 创建匹配函数
CREATE OR REPLACE FUNCTION match_observations(
  query_embedding vector(1536),
  match_count int DEFAULT 3
)
RETURNS TABLE (
  id bigint,
  market_id bigint,
  report_text text,
  create_time timestamptz,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    e.id,
    e.market_id,
    e.report_text,
    e.create_time,
    1 - (e.embedding <=> query_embedding) AS similarity
  FROM observation_embedding e
  ORDER BY e.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- ============================================================
-- 使用说明：
-- 在 Supabase SQL Editor 中执行上面的函数创建语句
-- 然后 Python 客户端调用：
--   client.rpc('match_observations', {
--     'query_embedding': '[0.1,0.2,...]',
--     'match_count': 3
--   })
-- ============================================================
