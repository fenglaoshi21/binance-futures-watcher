"""
LLM 提示词模板
==============
系统提示词（固定）+ 动态用户Prompt（每次填充实时数据+RAG历史）
"""

# ============================================================
# 系统提示词（固定不变，每次调用千问都带上）
# ============================================================
SYSTEM_PROMPT = """你是加密合约行情观测分析师，仅基于给定数据客观分析，严禁给出"买入、做多、做空、加仓、止盈止损"的直接交易指令，所有输出仅作为复盘参考。

## 基础规则
1. 当前观测标的：币安USDT永续合约涨幅榜第一名，已过滤股票合约、ETF合约、商品合约。
2. 你只能使用【本次实时数据】+【RAG检索到的历史相似观测记录】，禁止联网、不能使用外部你记忆里的实时行情。
3. 分析维度固定：24h涨跌幅、24h成交量、持仓量OI变化、资金费率、多空爆仓数据、聪明钱/大户多空比、量价背离判断、资金行为特征。
4. 区分短期脉冲行情与趋势行情：区分是消息拉动、资金拉盘、空头爆仓轧空、还是存量博弈反弹。
5. 风险评估必须单独一段，客观列出当前标的风险点。
6. 输出格式严格按照下面【输出模板】，不要自由发挥，不要多余闲聊。

## 输出模板（强制遵守）
【标的基本信息】
交易对：
24h涨跌幅：
当前价格：
24h成交量变化：
持仓量OI：
资金费率：
24小时多头爆仓：
24小时空头爆仓：
聪明钱多空比：
大户多空比：

【行情定性】
一句话定性当前行情属于哪一类：快速脉冲拉涨 / 空头爆仓轧空 / 趋势延续上涨 / 存量小幅反弹。

【数据拆解分析】
1. 量价分析：成交量和涨幅是否匹配，放量上涨还是缩量拉盘
2. 持仓OI：持仓是同步增加（增量资金进场）还是持仓下降（存量筹码博弈）
3. 资金费率：正/负费率含义，反映多空持仓情绪，极端费率意味着什么
4. 爆仓结构：多头爆仓、空头爆仓规模，判断拉盘是否为扫空行情
5. 聪明钱/大户行为：聪明钱和大户多空比方向是否一致，有无分歧，2m/30m/4h变化趋势

【历史相似案例对比（RAG检索到的记录）】
对比本次行情和历史相似观测样本的共性、差异；历史后续行情演化情况；本次需要留意的异同点。
> 如果没有检索到相似历史，写：本次无匹配相似历史观测记录。

【风险清单】
逐条列出风险：流动性风险、脉冲行情回撤风险、消息兑现回落风险、合约插针风险、资金费率极端反转风险等。

【观测结论（仅参考，非交易建议）】
总结当前盘面特征，给出后续重点需要持续监控的指标。禁止给出开仓方向。"""


# ============================================================
# 动态用户Prompt模板（每次填充实时数据+RAG历史）
# ============================================================
USER_PROMPT_TEMPLATE = """===== 本次实时观测数据 =====
观测时间：{observe_time}
标的Symbol：{symbol}
当前价格：{current_price}
24h涨跌幅：{change_24h}%
24h成交量变化：{volume_change_24h}%
24h成交量(USDT)：{volume_24h_usd}
持仓量OI(USDT)：{open_interest_usd}
OI 24h变化：{oi_change_24h}%
资金费率(OI加权)：{funding_rate}
24h多头爆仓(USDT)：{long_liq_24h}
24h空头爆仓(USDT)：{short_liq_24h}
24h总爆仓(USDT)：{total_liq_24h}
多空比(24h)：{long_short_ratio_24h}

--- 聪明钱(LSR trader) ---
聪明钱多空比：{lsr_trader_ratio}
聪明钱2m变化：{lsr_trader_delta_2m}
聪明钱30m变化：{lsr_trader_delta_30m}
聪明钱4h变化：{lsr_trader_delta_4h}
聪明钱多头人数：{lsr_trader_long_traders}
聪明钱空头人数：{lsr_trader_short_traders}

--- 大户(LSR whale) ---
大户多空比：{lsr_whale_ratio}
大户2m变化：{lsr_whale_delta_2m}
大户30m变化：{lsr_whale_delta_30m}
大户4h变化：{lsr_whale_delta_4h}
大户多头持仓量：{lsr_whale_long_qty}
大户空头持仓量：{lsr_whale_short_qty}

原始数据源：Coinglass专业版 + LSR聪明钱/大户数据

===== RAG检索匹配的相似历史观测记录（top3，按向量相似度排序）=====
{retrieved_history_text}

===== 任务 =====
基于上面本次实时数据 + 历史RAG记录，严格遵守系统提示词规则，按照规定模板输出分析报告。
记住：禁止任何买卖、多空操作建议，结论只做行情观测复盘参考。"""


def build_user_prompt(market_data: dict, lsr_data: dict, observe_time: str, retrieved_history: str = "") -> str:
    """
    组装动态用户Prompt
    market_data: coins-markets 返回的单条数据（74字段）
    lsr_data: {"trader": {...}, "whale": {...}}
    observe_time: 观测时间
    retrieved_history: RAG检索到的历史记录文本
    """
    md = market_data or {}
    trader = (lsr_data or {}).get("trader") or {}
    whale = (lsr_data or {}).get("whale") or {}

    def safe(val, default="N/A"):
        return val if val is not None else default

    return USER_PROMPT_TEMPLATE.format(
        observe_time=observe_time,
        symbol=safe(md.get("symbol")),
        current_price=safe(md.get("current_price")),
        change_24h=safe(md.get("price_change_percent_24h")),
        volume_change_24h=safe(md.get("volume_change_percent_24h")),
        volume_24h_usd=safe(md.get("volume_change_usd_24h")),
        open_interest_usd=safe(md.get("open_interest_usd")),
        oi_change_24h=safe(md.get("open_interest_change_percent_24h")),
        funding_rate=safe(md.get("avg_funding_rate_by_oi")),
        long_liq_24h=safe(md.get("long_liquidation_usd_24h")),
        short_liq_24h=safe(md.get("short_liquidation_usd_24h")),
        total_liq_24h=safe(md.get("liquidation_usd_24h")),
        long_short_ratio_24h=safe(md.get("long_short_ratio_24h")),
        # LSR 聪明钱
        lsr_trader_ratio=safe(trader.get("ratio")),
        lsr_trader_delta_2m=safe(trader.get("delta_2m")),
        lsr_trader_delta_30m=safe(trader.get("delta_30m")),
        lsr_trader_delta_4h=safe(trader.get("delta_4h")),
        lsr_trader_long_traders=safe(trader.get("ov_long_traders")),
        lsr_trader_short_traders=safe(trader.get("ov_short_traders")),
        # LSR 大户
        lsr_whale_ratio=safe(whale.get("whale_ratio", whale.get("ratio"))),
        lsr_whale_delta_2m=safe(whale.get("whale_delta_2m", whale.get("delta_2m"))),
        lsr_whale_delta_30m=safe(whale.get("whale_delta_30m", whale.get("delta_30m"))),
        lsr_whale_delta_4h=safe(whale.get("whale_delta_4h", whale.get("delta_4h"))),
        lsr_whale_long_qty=safe(whale.get("whale_long_qty", whale.get("ov_long_whales_qty"))),
        lsr_whale_short_qty=safe(whale.get("whale_short_qty", whale.get("ov_short_whales_qty"))),
        retrieved_history_text=retrieved_history or "本次无匹配相似历史观测记录。",
    )
