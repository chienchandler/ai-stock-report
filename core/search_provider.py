"""
搜索与新闻聚合模块
优先 Brave Search，Tavily 作为 fallback，东方财富免费新闻兜底
"""
import logging
import urllib.request
import json as _json
import concurrent.futures as _cf
from datetime import datetime, timedelta
from core.config import get_config
from core.data_provider import get_stock_news_em, get_stock_news_xueqiu

logger = logging.getLogger(__name__)

# ---- Brave Search ----

def _brave_search(query, count=5, timeout=15):
    config = get_config()
    api_key = config.get('search', {}).get('brave_api_key', '') or config.get('brave_search_api_key', '')
    if not api_key:
        return [], 'Brave API key 未设置'

    encoded_q = urllib.request.quote(query)
    url = f"https://api.search.brave.com/res/v1/web/search?q={encoded_q}&count={count}"
    req = urllib.request.Request(url, headers={
        'Accept': 'application/json',
        'X-Subscription-Token': api_key,
    })
    try:
        with _cf.ThreadPoolExecutor(max_workers=1) as ex:
            resp = ex.submit(urllib.request.urlopen, req, timeout=timeout).result(timeout=timeout + 5)
        data = _json.loads(resp.read().decode('utf-8'))

        if data.get('type') == 'ErrorResponse' or 'error' in data:
            return [], str(data.get('error', data))

        results = []
        for r in (data.get('web', {}).get('results', []) or []):
            results.append({
                'title': r.get('title', ''),
                'content': (r.get('description', '') or '')[:300],
                'source': 'Brave',
            })
        return results, None
    except _cf.TimeoutError:
        return [], f'Brave搜索超时({timeout}s)'
    except Exception as e:
        return [], str(e)


# ---- Tavily (fallback) ----

_tavily_client = None
_tavily_disabled = False


def _get_tavily_client():
    global _tavily_client, _tavily_disabled
    if _tavily_disabled:
        return None
    if _tavily_client is not None:
        return _tavily_client

    config = get_config()
    api_key = config.get('search', {}).get('tavily_api_key', '') or config.get('tavily_api_key', '')
    if not api_key:
        return None

    try:
        from tavily import TavilyClient
        _tavily_client = TavilyClient(api_key=api_key)
        return _tavily_client
    except Exception as e:
        logger.error(f"初始化Tavily客户端失败: {e}")
        return None


def _tavily_search(query, max_results=5, search_depth='basic', timeout=20):
    global _tavily_disabled
    client = _get_tavily_client()
    if client is None:
        return [], 'Tavily不可用'

    try:
        with _cf.ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(
                client.search, query=query,
                max_results=max_results, search_depth=search_depth,
                include_answer=True,
            )
            response = fut.result(timeout=timeout)

        results = []
        answer = response.get('answer', '')
        if answer:
            results.append({'title': 'AI搜索摘要', 'content': answer[:500], 'source': 'Tavily'})
        for r in response.get('results', []):
            results.append({
                'title': r.get('title', ''),
                'content': r.get('content', '')[:300],
                'source': 'Tavily',
            })
        return results, None
    except _cf.TimeoutError:
        return [], f'Tavily搜索超时({timeout}s)'
    except Exception as e:
        err_str = str(e)
        if 'usage limit' in err_str.lower() or 'exceeded' in err_str.lower():
            _tavily_disabled = True
            logger.warning("Tavily配额耗尽，本次进程内禁用")
        return [], err_str


# ---- 搜索失败统计 ----

_search_fail_count = 0
_search_total_count = 0


def get_search_stats():
    return _search_total_count, _search_fail_count


def _build_date_suffix(date_str):
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        yesterday = dt - timedelta(days=1)
        return f"{yesterday.strftime('%Y年%m月%d日')} {dt.strftime('%Y年%m月%d日')}"
    except Exception:
        return ''


# ---- 对外接口 ----

def _dedup_news(news_list):
    """按标题去重，保留首次出现的"""
    seen = set()
    result = []
    for n in news_list:
        title = n.get('title', '').strip()
        if not title:
            continue
        # 用标题前20字作为去重key（避免不同源标题微小差异）
        key = title[:20]
        if key not in seen:
            seen.add(key)
            result.append(n)
    return result


def search_stock_news(stock_name, stock_code, date_str=None):
    """聚合搜索：Brave/Tavily + 东方财富 + 雪球个股新闻"""
    global _search_fail_count, _search_total_count
    _search_total_count += 1

    all_news = []

    # 1. 东方财富新闻（免费）
    try:
        em_news = get_stock_news_em(stock_code)
        for n in em_news:
            all_news.append({
                'title': n.get('title', ''),
                'content': n.get('content', '')[:300],
                'source': f"东财 {n.get('source', '')}",
            })
    except Exception as e:
        logger.debug(f"东财新闻获取失败 {stock_code}: {e}")

    # 2. 雪球新闻（免费）
    try:
        xq_news = get_stock_news_xueqiu(stock_code)
        for n in xq_news:
            all_news.append({
                'title': n.get('title', ''),
                'content': n.get('content', '')[:300],
                'source': '雪球',
            })
    except Exception as e:
        logger.debug(f"雪球新闻获取失败 {stock_code}: {e}")

    # 3. 网络搜索
    date_suffix = _build_date_suffix(date_str) if date_str else ''
    query = f"{stock_name} {stock_code} 最新消息 {date_suffix}".strip()

    config = get_config()
    max_results = config.get('search', {}).get('max_results', 5)

    # 3a. Brave
    results, err = _brave_search(query, count=max_results)
    if results:
        all_news.extend(results)
        return _dedup_news(all_news)

    if err:
        logger.debug(f"Brave搜索失败 {stock_code}: {err}")

    # 3b. Tavily fallback
    results, err = _tavily_search(query, max_results=max_results)
    if results:
        all_news.extend(results)
        return _dedup_news(all_news)

    if err:
        logger.debug(f"Tavily搜索也失败 {stock_code}: {err}")

    if not all_news:
        _search_fail_count += 1

    return _dedup_news(all_news)


def search_market_news(date_str=None):
    """搜索市场整体新闻"""
    date_suffix = _build_date_suffix(date_str) if date_str else ''
    query = f"A股 市场 行情分析 政策 资金面 {date_suffix}".strip()

    results, err = _brave_search(query, count=5)
    if results:
        return results

    results, err = _tavily_search(query, max_results=5)
    if results:
        return results

    return []
