"""
研究员Agent - 分析用户关注的股票并生成报告
支持断点续传、并发分析、429限速退避
"""
import json
import logging
import os
import socket
import threading
import concurrent.futures
import time as _time
from datetime import datetime

# 全局 socket 超时兜底
socket.setdefaulttimeout(60)

from core import llm_client
from core.models import StockScore, ResearchReport
from core.data_provider import (
    get_stock_history, get_market_overview, get_northbound_flow_summary,
    get_sector_top_movers, get_realtime_snapshot,
    calculate_technical_indicators, get_valuation_batch, get_last_trading_day,
)
from core.search_provider import search_stock_news, search_market_news
from core.config import get_config, get_data_dir
from core.storage import load_research_report as _load_research_report
from core.prompts import DEFAULT_SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

STOCK_ANALYZE_TIMEOUT = 300
_CHECKPOINT_LOCK = threading.Lock()

logger = logging.getLogger(__name__)


def _get_checkpoint_path(date_str):
    return os.path.join(get_data_dir(), 'research', f'{date_str}.checkpoint.json')


def _load_checkpoint(date_str):
    path = _get_checkpoint_path(date_str)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        result = {}
        for s in data.get('scores', []):
            score = StockScore.from_dict(s)
            result[score.stock_code] = score
        logger.info(f"恢复checkpoint: 已有 {len(result)} 只股票的评分")
        return result
    except Exception as e:
        logger.warning(f"checkpoint读取失败: {e}")
        return {}


def _save_checkpoint(date_str, scores_dict):
    path = _get_checkpoint_path(date_str)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = {'scores': [s.to_dict() for s in scores_dict.values()]}
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _remove_checkpoint(date_str):
    path = _get_checkpoint_path(date_str)
    if os.path.exists(path):
        os.remove(path)


def _get_system_prompt(config):
    """获取系统提示词：用户自定义 > 默认"""
    custom = config.get('custom_prompt', '').strip()
    if custom:
        # 将用户的自定义指令追加到默认提示词后面
        return DEFAULT_SYSTEM_PROMPT + f"\n\n【用户自定义分析指令】\n{custom}"
    return DEFAULT_SYSTEM_PROMPT


def _build_market_context(date_str=""):
    """构建市场宏观上下文，供所有股票分析共用"""
    parts = []

    overview = get_market_overview()
    if overview:
        lines = []
        for name, data in overview.items():
            lines.append(f"  {name}: {data['latest']:.2f} (1日:{data['pct_1d']:+.2f}%, 5日:{data['pct_5d']:+.2f}%)")
        parts.append("【大盘指数】\n" + "\n".join(lines))

    north = get_northbound_flow_summary()
    if north:
        lines = []
        for name, data in north.items():
            net = data.get('net_buy', 0)
            lines.append(f"  {name}: 净买入 {net/1e8:.2f}亿" if isinstance(net, (int, float)) else f"  {name}: {net}")
        parts.append("【北向资金】\n" + "\n".join(lines))

    sectors = get_sector_top_movers(5)
    if sectors:
        parts.append("【板块涨幅前5】\n  " + " | ".join(sectors.get('top', [])[:5]))
        parts.append("【板块跌幅前5】\n  " + " | ".join(sectors.get('bottom', [])[:5]))

    market_news = search_market_news(date_str=date_str)
    if market_news:
        lines = [f"  - {n['title']}: {n['content'][:150]}" for n in market_news[:3]]
        parts.append("【市场新闻】\n" + "\n".join(lines))

    return "\n\n".join(parts) if parts else ""


def _build_user_prompt(stock_code, stock_name, date_str, price_data, news,
                       market_context="", snapshot_price=None,
                       tech_indicators=None, valuation=None, prev_score=None):
    """构建用户提示词"""
    price_info = "无可用数据"
    pct_1d = pct_5d = pct_20d = "N/A"
    pct_1d_val = None
    latest_price = "N/A"

    if price_data is not None and not price_data.empty:
        recent = price_data.tail(10)
        rows = []
        for _, r in recent.iterrows():
            rows.append(f"  {r.get('date', 'N/A')} | 开:{r.get('open', 'N/A')} | 收:{r.get('close', 'N/A')} | "
                        f"高:{r.get('high', 'N/A')} | 低:{r.get('low', 'N/A')} | "
                        f"量:{r.get('volume', 'N/A')} | 涨跌幅:{r.get('pct_change', 'N/A')}%")
        price_info = "\n".join(rows)

        closes = price_data['close'].tolist()
        if len(closes) >= 2:
            pct_1d_val = ((closes[-1] / closes[-2]) - 1) * 100
            pct_1d = f"{pct_1d_val:.2f}"
        if len(closes) >= 6:
            pct_5d = f"{((closes[-1] / closes[-6]) - 1) * 100:.2f}"
        if len(closes) >= 21:
            pct_20d = f"{((closes[-1] / closes[-21]) - 1) * 100:.2f}"
        latest_price = f"{closes[-1]:.2f}"

    if latest_price == "N/A" and snapshot_price is not None:
        latest_price = f"{snapshot_price:.2f}（新浪快照）"

    news_text = "无相关新闻"
    if news:
        items = []
        for n in news:
            src = n.get('source', '')
            items.append(f"  [{src}] {n.get('title', '')}\n    {n.get('content', '')[:200]}")
        news_text = "\n".join(items)

    prompt = USER_PROMPT_TEMPLATE.format(
        stock_code=stock_code, stock_name=stock_name, date_str=date_str,
        price_info=price_info, pct_1d=pct_1d, pct_5d=pct_5d, pct_20d=pct_20d,
        latest_price=latest_price, news_text=news_text,
    )

    extra_sections = []

    # 前日评分对比
    if prev_score is not None:
        prev_val = prev_score.score
        prev_summary = prev_score.summary[:80]
        extra_sections.append(
            f"【前日评分】{prev_val:+.2f} | \"{prev_summary}\""
        )

    # 技术指标
    if tech_indicators:
        ti = tech_indicators
        parts = []
        if 'ma_status' in ti and ti['ma_status']:
            parts.append(f"均线偏离: {ti['ma_status']}")
        if 'rsi14' in ti:
            rsi = ti['rsi14']
            rsi_note = '（超买）' if rsi > 70 else ('（超卖）' if rsi < 30 else '')
            parts.append(f"RSI(14)={rsi}{rsi_note}")
        if 'vol_trend' in ti:
            parts.append(f"量能={ti['vol_trend']}")
        if parts:
            extra_sections.append("【技术指标】\n  " + " | ".join(parts))

    # 估值
    if valuation:
        parts = []
        if 'pe' in valuation:
            parts.append(f"PE(TTM)={valuation['pe']}")
        if 'pb' in valuation:
            parts.append(f"PB={valuation['pb']}")
        if parts:
            extra_sections.append("【估值参考】\n  " + " | ".join(parts))

    # 数据缺失警告
    data_warnings = []
    if price_data is None or (hasattr(price_data, 'empty') and price_data.empty):
        if snapshot_price is not None:
            data_warnings.append(f"K线数据获取失败，已用新浪快照昨收价 {snapshot_price:.2f} 元作为参考")
        else:
            data_warnings.append("K线数据获取失败，请基于已有信息谨慎评分，不要编造具体数据")
    if not news:
        data_warnings.append("新闻数据为空，不要编造新闻事件")
    if data_warnings:
        extra_sections.append("【数据缺失警告】\n" + "\n".join(data_warnings))

    _FINAL = "\n\n请输出JSON评分。"
    if extra_sections:
        insert_str = "\n\n" + "\n\n".join(extra_sections)
        prompt = prompt.replace(_FINAL, insert_str + _FINAL, 1)

    if market_context:
        prompt = f"【市场环境】\n{market_context}\n\n{prompt}"

    return prompt


def _analyze_one_safe(stock, date_str, config, market_context,
                      snapshot_cache, valuation_cache=None, prev_score_cache=None):
    """并发 worker：分析单只股票，含429退避"""
    _snap = snapshot_cache.get(stock.code, {})
    _snapshot_price = _snap.get('prev_close') or _snap.get('price') or None
    _valuation = (valuation_cache or {}).get(stock.code)
    _prev_score = (prev_score_cache or {}).get(stock.code)

    for attempt in range(3):
        try:
            return analyze_stock(
                stock.code, stock.name, date_str, config, market_context,
                snapshot_price=_snapshot_price,
                valuation=_valuation, prev_score=_prev_score,
            )
        except Exception as e:
            err_str = str(e)
            is_rate_limit = (
                '429' in err_str
                or 'rate limit' in err_str.lower()
                or 'too many requests' in err_str.lower()
            )
            if is_rate_limit and attempt < 2:
                wait_s = 15 * (2 ** attempt)
                logger.warning(f"[限速] {stock.code} {stock.name} attempt {attempt + 1}/3，等待 {wait_s}s")
                _time.sleep(wait_s)
            else:
                logger.error(f"[失败] {stock.code} {stock.name}: {e}")
                return None, None

    logger.error(f"[限速放弃] {stock.code} {stock.name}: 3次重试后仍失败")
    return None, None


def analyze_stock(stock_code, stock_name, date_str, config, market_context="",
                  snapshot_price=None, valuation=None, prev_score=None):
    """分析单只股票，返回 (StockScore, data_status)"""
    history_days = config.get('data', {}).get('history_days', 30)
    price_data = get_stock_history(stock_code, days_back=history_days)
    news = search_stock_news(stock_name, stock_code, date_str=date_str)
    tech_indicators = calculate_technical_indicators(price_data)

    has_price = price_data is not None and not price_data.empty
    has_news = bool(news)
    data_status = {'has_price': has_price, 'has_news': has_news}

    user_prompt = _build_user_prompt(
        stock_code, stock_name, date_str, price_data, news, market_context,
        snapshot_price=snapshot_price,
        tech_indicators=tech_indicators, valuation=valuation, prev_score=prev_score,
    )

    system_prompt = _get_system_prompt(config)
    model = config.get('llm', {}).get('model', 'deepseek-chat')
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    raw_response = llm_client.chat(messages, model=model)
    parsed = llm_client.parse_json_response(raw_response)

    if parsed is None:
        logger.warning(f"  {stock_code} LLM返回无法解析，使用默认评分0")
        return StockScore(
            date=date_str, stock_code=stock_code, stock_name=stock_name,
            score=0, summary="LLM响应解析失败",
            raw_llm_response=raw_response or "",
        ), data_status

    return StockScore(
        date=date_str, stock_code=stock_code, stock_name=stock_name,
        score=max(-5.0, min(5.0, round(float(parsed.get('score', 0)), 2))),
        summary=parsed.get('summary', ''),
        raw_llm_response=raw_response or "",
    ), data_status


def run_research(stocks, date_str, config):
    """对所有股票进行研究分析，支持断点续传"""
    logger.info(f"开始研究分析，日期: {date_str}，共 {len(stocks)} 只股票")

    # 加载checkpoint
    completed = _load_checkpoint(date_str)
    remaining = [s for s in stocks if s.code not in completed]
    if completed:
        logger.info(f"已完成 {len(completed)} 只，剩余 {len(remaining)} 只")

    if not remaining:
        logger.info("所有股票已完成分析（从checkpoint恢复）")
        scores = [completed[s.code] for s in stocks if s.code in completed]
        report = ResearchReport(
            date=date_str, scores=scores,
            run_timestamp=datetime.now().isoformat(),
            model_used=config.get('llm', {}).get('model', 'deepseek-chat'),
            errors=[],
        )
        _remove_checkpoint(date_str)
        return report

    # 宏观上下文
    logger.info("获取市场宏观数据...")
    market_context = _build_market_context(date_str)

    # 加载前日评分
    prev_score_cache = {}
    try:
        prev_date = get_last_trading_day(before_date=date_str)
        if prev_date and prev_date != date_str:
            prev_report = _load_research_report(prev_date)
            if prev_report:
                prev_score_cache = {s.stock_code: s for s in prev_report.scores}
                logger.info(f"加载前日评分: {len(prev_score_cache)} 只 (日期: {prev_date})")
    except Exception as e:
        logger.warning(f"加载前日评分失败: {e}")

    # 预取数据
    logger.info("预取行情快照、估值数据...")
    snapshot_cache = {}
    try:
        snapshot_cache = get_realtime_snapshot([s.code for s in stocks])
    except Exception as e:
        logger.warning(f"预取快照失败: {e}")
    valuation_cache = {}
    try:
        valuation_cache = get_valuation_batch([s.code for s in stocks])
    except Exception as e:
        logger.warning(f"预取PE/PB失败: {e}")

    # 并发分析
    errors = []
    missing_price = 0
    missing_news = 0
    total_analyzed = 0

    max_workers = config.get('research_workers', 3)
    _estimated = 90 * len(remaining) / max(max_workers, 1)
    total_timeout = min(_estimated * 2 + 300, 7200)
    logger.info(f"并发分析: {max_workers} workers，{len(remaining)} 只待分析")

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_stock = {
            executor.submit(
                _analyze_one_safe,
                stock, date_str, config, market_context,
                snapshot_cache, valuation_cache, prev_score_cache,
            ): stock
            for stock in remaining
        }

        try:
            for future in concurrent.futures.as_completed(future_to_stock, timeout=total_timeout):
                stock = future_to_stock[future]
                score, data_status = None, None
                try:
                    score, data_status = future.result(timeout=STOCK_ANALYZE_TIMEOUT)
                except concurrent.futures.TimeoutError:
                    logger.error(f"  {stock.code} {stock.name} 超时(>{STOCK_ANALYZE_TIMEOUT}s)")
                except Exception as e:
                    logger.error(f"  {stock.code} {stock.name} 异常: {e}")

                with _CHECKPOINT_LOCK:
                    if score is not None:
                        completed[stock.code] = score
                        total_analyzed += 1
                        if not data_status['has_price']:
                            missing_price += 1
                        if not data_status['has_news']:
                            missing_news += 1
                        n_done = len(completed)
                        logger.info(f"[{n_done}/{len(stocks)}] {stock.name}({stock.code}) score={score.score:+.2f}")
                        if n_done % 3 == 0 or n_done == len(stocks):
                            _save_checkpoint(date_str, completed)
                    else:
                        errors.append(f"{stock.code} {stock.name}: 分析失败")
                        _save_checkpoint(date_str, completed)
        except concurrent.futures.TimeoutError:
            hung = [s for f, s in future_to_stock.items() if not f.done()]
            logger.error(f"并发总超时，{len(hung)} 只未完成")
            for f in future_to_stock:
                f.cancel()
            for s in hung:
                errors.append(f"{s.code} {s.name}: 总超时")
            _save_checkpoint(date_str, completed)

    scores = [completed[s.code] for s in stocks if s.code in completed]

    report = ResearchReport(
        date=date_str, scores=scores,
        run_timestamp=datetime.now().isoformat(),
        model_used=config.get('llm', {}).get('model', 'deepseek-chat'),
        errors=errors,
    )

    _remove_checkpoint(date_str)
    logger.info(f"研究完成: {len(scores)} 只成功, {len(errors)} 只失败")
    return report
