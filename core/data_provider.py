"""
行情数据获取模块
数据源：AkShare（免费） + 新浪财经（免费）
"""
import akshare as ak
import logging
import time as _time
import concurrent.futures as _cf
from datetime import datetime, timedelta
from core.models import StockInfo

logger = logging.getLogger(__name__)

_trading_days_cache = None
_spot_em_cache = None  # 全A股实时数据缓存（名称+估值共用，每次运行只取一次）


def _fetch_spot_em_with_retry(max_retries=3):
    """获取东财全A股实时数据，带重试。结果全局缓存。"""
    global _spot_em_cache
    if _spot_em_cache is not None:
        return _spot_em_cache

    for attempt in range(max_retries):
        try:
            with _cf.ThreadPoolExecutor(max_workers=1) as ex:
                df = ex.submit(ak.stock_zh_a_spot_em).result(timeout=30)
            if df is not None and not df.empty:
                _spot_em_cache = df
                return df
        except _cf.TimeoutError:
            logger.warning(f"东财全A数据超时 (第{attempt+1}次)")
        except Exception as e:
            logger.warning(f"东财全A数据失败 (第{attempt+1}次): {e}")
        if attempt < max_retries - 1:
            _time.sleep(3 * (attempt + 1))

    logger.warning("东财全A数据: 所有重试均失败")
    return None


def _resolve_names_via_sina(codes):
    """新浪备选方案：通过新浪快照获取股票名称"""
    snapshot = get_realtime_snapshot(codes)
    result = {}
    for code in codes:
        c = str(code).zfill(6)
        info = snapshot.get(c, {})
        name = info.get('name', '').strip()
        result[c] = StockInfo(code=c, name=name if name else c)
    return result


def resolve_stock_name(code):
    """通过股票代码查询股票名称"""
    batch = resolve_stock_names_batch([code])
    return batch.get(str(code).zfill(6), StockInfo(code=code, name=code)).name


def resolve_stock_names_batch(codes):
    """批量查询股票名称，返回 {code: StockInfo}。东财失败自动走新浪备选。"""
    result = {}
    df = _fetch_spot_em_with_retry()

    if df is not None and not df.empty:
        code_col = next((c for c in df.columns if '代码' in str(c)), df.columns[0])
        name_col = next((c for c in df.columns if '名称' in str(c)), df.columns[1])
        code_set = set(str(c).zfill(6) for c in codes)
        for _, row in df.iterrows():
            c = str(row[code_col]).zfill(6)
            if c in code_set:
                result[c] = StockInfo(code=c, name=str(row[name_col]))

    # 检查哪些没查到
    missing = [str(c).zfill(6) for c in codes if str(c).zfill(6) not in result]
    if missing:
        logger.info(f"东财未获取到 {len(missing)} 只股票名称，尝试新浪备选...")
        sina_result = _resolve_names_via_sina(missing)
        result.update(sina_result)

    # 最后兜底
    for c in codes:
        c_padded = str(c).zfill(6)
        if c_padded not in result:
            result[c_padded] = StockInfo(code=c_padded, name=c_padded)

    return result


def get_stock_history(symbol, days_back=30):
    """获取股票历史日线数据，优先新浪，失败切东财。每个数据源限时30s。"""
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=days_back + 15)).strftime('%Y%m%d')

    # 1. 新浪（稳定）
    try:
        prefix = 'sh' if symbol.startswith('6') else 'sz'
        with _cf.ThreadPoolExecutor(max_workers=1) as _ex:
            df = _ex.submit(ak.stock_zh_a_daily, symbol=f"{prefix}{symbol}", adjust='qfq').result(timeout=30)
        if df is not None and not df.empty:
            if 'date' not in df.columns:
                df['date'] = df.index.astype(str)
            df['pct_change'] = df['close'].pct_change() * 100
            return df.tail(days_back)
    except _cf.TimeoutError:
        logger.warning(f"新浪K线超时(30s) {symbol}，切东财")
    except Exception as e:
        logger.warning(f"新浪K线失败 {symbol}，切东财: {e}")

    # 2. 东方财富 fallback
    try:
        with _cf.ThreadPoolExecutor(max_workers=1) as _ex:
            df = _ex.submit(
                ak.stock_zh_a_hist,
                symbol=symbol, period="daily",
                start_date=start_date, end_date=end_date,
                adjust="qfq"
            ).result(timeout=30)
        if df is None or df.empty:
            logger.warning(f"东财K线也无数据 {symbol}")
            return None
        col_map = {
            '日期': 'date', '开盘': 'open', '收盘': 'close',
            '最高': 'high', '最低': 'low',
            '成交量': 'volume', '涨跌幅': 'pct_change',
        }
        df = df.rename(columns=col_map)
        return df.tail(days_back)
    except _cf.TimeoutError:
        logger.error(f"东财K线也超时(30s) {symbol}")
        return None
    except Exception as e:
        logger.error(f"获取 {symbol} 历史数据失败(新浪+东财均失败): {e}")
        return None


def get_realtime_snapshot(symbols):
    """批量获取实时行情快照（新浪财经接口）"""
    import urllib.request
    import re
    if not symbols:
        return {}
    try:
        sina_codes = []
        for s in symbols:
            prefix = 'sh' if s.startswith('6') else 'sz'
            sina_codes.append(f"{prefix}{s}")
        url = f'https://hq.sinajs.cn/list={",".join(sina_codes)}'
        req = urllib.request.Request(url, headers={'Referer': 'https://finance.sina.com.cn'})
        resp = urllib.request.urlopen(req, timeout=10)
        data = resp.read().decode('gbk')

        result = {}
        for line in data.strip().split('\n'):
            m = re.match(r'var hq_str_(\w{2})(\d{6})="(.*)";', line)
            if not m or not m.group(3):
                continue
            symbol = m.group(2)
            fields = m.group(3).split(',')
            if len(fields) < 32:
                continue
            prev_close = float(fields[2]) if fields[2] else 0
            price = float(fields[3]) if fields[3] else 0
            if price <= 0:
                continue
            pct = ((price / prev_close) - 1) * 100 if prev_close > 0 else 0
            result[symbol] = {
                'name': fields[0], 'price': price,
                'prev_close': prev_close,
                'pct_change': round(pct, 2),
            }
        return result
    except Exception as e:
        logger.warning(f"批量获取实时行情失败: {e}")
        return {}


def get_stock_news_em(symbol):
    """从东方财富获取个股新闻（免费），带重试"""
    for attempt in range(2):
        try:
            with _cf.ThreadPoolExecutor(max_workers=1) as _ex:
                df = _ex.submit(ak.stock_news_em, symbol=symbol).result(timeout=15)
            if df is None or df.empty:
                return []
            results = []
            for _, row in df.head(5).iterrows():
                results.append({
                    'title': str(row.get('新闻标题', '')),
                    'content': str(row.get('新闻内容', ''))[:300],
                    'time': str(row.get('发布时间', '')),
                    'source': str(row.get('新闻来源', '')),
                })
            return results
        except _cf.TimeoutError:
            logger.debug(f"东财新闻超时(15s) {symbol} (第{attempt+1}次)")
        except Exception as e:
            logger.debug(f"获取 {symbol} 东财新闻失败 (第{attempt+1}次): {e}")
        if attempt < 1:
            _time.sleep(2)
    return []


def get_stock_news_xueqiu(symbol):
    """从雪球获取个股动态/新闻（免费，无需API Key）"""
    import urllib.request
    import json as _json
    try:
        prefix = 'SH' if symbol.startswith('6') else 'SZ'
        xq_symbol = f"{prefix}{symbol}"
        url = f"https://stock.xueqiu.com/v5/stock/news.json?symbol={xq_symbol}&count=5&source=all"
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://xueqiu.com/',
        })
        # 需要先访问主页拿cookie
        cookie_req = urllib.request.Request('https://xueqiu.com/', headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        })
        import http.cookiejar
        cj = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        opener.open(cookie_req, timeout=10)
        resp = opener.open(req, timeout=10)
        data = _json.loads(resp.read().decode('utf-8'))

        results = []
        for item in (data.get('data', {}).get('items', []) or [])[:5]:
            title = item.get('title', '') or ''
            text = item.get('text', '') or ''
            # 雪球的text是HTML，简单清理
            import re
            text = re.sub(r'<[^>]+>', '', text)[:300]
            if title or text:
                results.append({
                    'title': title,
                    'content': text,
                    'time': '',
                    'source': '雪球',
                })
        return results
    except Exception as e:
        logger.debug(f"获取 {symbol} 雪球新闻失败: {e}")
        return []


def get_market_overview():
    """获取大盘指数近期行情"""
    indices = {
        'sh000001': '上证指数',
        'sz399001': '深证成指',
        'sz399006': '创业板指',
    }
    result = {}
    for symbol, name in indices.items():
        try:
            df = ak.stock_zh_index_daily(symbol=symbol)
            if df is not None and not df.empty:
                recent = df.tail(5)
                closes = recent['close'].tolist()
                pct_1d = ((closes[-1] / closes[-2]) - 1) * 100 if len(closes) >= 2 else 0
                pct_5d = ((closes[-1] / closes[0]) - 1) * 100 if len(closes) >= 2 else 0
                result[name] = {
                    'latest': closes[-1],
                    'pct_1d': round(pct_1d, 2),
                    'pct_5d': round(pct_5d, 2),
                }
        except Exception as e:
            logger.debug(f"获取 {name} 指数失败: {e}")
    return result


def get_northbound_flow_summary():
    """获取北向资金流向摘要"""
    try:
        df = ak.stock_hsgt_fund_flow_summary_em()
        if df is None or df.empty:
            return None
        result = {}
        for _, row in df.iterrows():
            type_name = str(row.get('类型', ''))
            if '沪股通' in type_name or '深股通' in type_name or '北向' in type_name:
                result[type_name] = {
                    'net_buy': row.get('成交净买额', 0),
                }
        return result
    except Exception as e:
        logger.debug(f"获取北向资金失败: {e}")
        return None


def get_sector_top_movers(n=5):
    """获取涨幅前N和跌幅前N的行业板块"""
    try:
        df = ak.stock_board_industry_name_em()
        if df is None or df.empty:
            return None
        df = df.sort_values('涨跌幅', ascending=False)
        top = [f"{row.get('板块名称', '')} {row.get('涨跌幅', 0):+.2f}%" for _, row in df.head(n).iterrows()]
        bottom = [f"{row.get('板块名称', '')} {row.get('涨跌幅', 0):+.2f}%" for _, row in df.tail(n).iterrows()]
        return {'top': top, 'bottom': bottom}
    except Exception as e:
        logger.debug(f"获取板块数据失败: {e}")
        return None


def get_valuation_batch(codes):
    """批量获取股票PE/PB（复用东财缓存，不额外请求）"""
    if not codes:
        return {}
    code_set = set(str(c).zfill(6) for c in codes)
    try:
        df = _fetch_spot_em_with_retry()
        if df is None or df.empty:
            return {}
        code_col = next((c for c in df.columns if '代码' in str(c)), df.columns[0])
        pe_col = next((c for c in df.columns if '市盈率' in str(c)), None)
        pb_col = next((c for c in df.columns if '市净率' in str(c)), None)
        result = {}
        for _, row in df.iterrows():
            code = str(row[code_col]).zfill(6)
            if code not in code_set:
                continue
            item = {}
            if pe_col:
                try:
                    pe = float(row[pe_col] or 0)
                    if 0 < pe < 10000:
                        item['pe'] = round(pe, 1)
                except (ValueError, TypeError):
                    pass
            if pb_col:
                try:
                    pb = float(row[pb_col] or 0)
                    if 0 < pb < 100:
                        item['pb'] = round(pb, 1)
                except (ValueError, TypeError):
                    pass
            if item:
                result[code] = item
        return result
    except Exception as e:
        logger.warning(f"PE/PB批量预取失败: {e}")
        return {}


def calculate_technical_indicators(df):
    """基于K线计算技术指标（MA/RSI/量能），零API调用"""
    if df is None or df.empty or len(df) < 5:
        return {}

    try:
        closes = [float(v) for v in df['close'].tolist()
                  if v is not None and str(v) not in ('nan', 'None', '')]
    except Exception:
        return {}
    if len(closes) < 5:
        return {}

    result = {}
    latest = closes[-1]

    # 移动平均线
    for n, key in [(5, 'ma5'), (10, 'ma10'), (20, 'ma20')]:
        if len(closes) >= n:
            result[key] = round(sum(closes[-n:]) / n, 2)

    # 价格偏离MA状态
    parts = []
    for key, label in [('ma5', 'MA5'), ('ma10', 'MA10'), ('ma20', 'MA20')]:
        if key in result and result[key] > 0:
            pct = (latest / result[key] - 1) * 100
            sign = '+' if pct >= 0 else ''
            parts.append(f"{label}{sign}{pct:.1f}%")
    result['ma_status'] = ' | '.join(parts) if parts else ''

    # RSI-14
    if len(closes) >= 15:
        changes = [closes[i] - closes[i - 1] for i in range(len(closes) - 14, len(closes))]
        gains = sum(c for c in changes if c > 0)
        losses = sum(-c for c in changes if c < 0)
        avg_gain = gains / 14
        avg_loss = losses / 14
        if avg_loss == 0:
            result['rsi14'] = 100.0
        else:
            rs = avg_gain / avg_loss
            result['rsi14'] = round(100 - 100 / (1 + rs), 1)

    # 量能趋势
    if 'volume' in df.columns:
        try:
            vols = [float(v) for v in df['volume'].tolist()
                    if v is not None and str(v) not in ('nan', 'None') and float(v) > 0]
            if len(vols) >= 10:
                vol5 = sum(vols[-5:]) / 5
                n = min(20, len(vols))
                vol_n = sum(vols[-n:]) / n
                if vol_n > 0:
                    ratio = vol5 / vol_n
                    if ratio > 1.3:
                        result['vol_trend'] = f"放量({ratio:.2f}x)"
                    elif ratio < 0.7:
                        result['vol_trend'] = f"缩量({ratio:.2f}x)"
                    else:
                        result['vol_trend'] = f"平量({ratio:.2f}x)"
        except Exception:
            pass

    return result


# ============ 交易日历 ============

def get_trading_days():
    global _trading_days_cache
    if _trading_days_cache is not None:
        return _trading_days_cache
    try:
        df = ak.tool_trade_date_hist_sina()
        _trading_days_cache = set(str(d) for d in df['trade_date'].tolist())
        return _trading_days_cache
    except Exception as e:
        logger.error(f"获取交易日历失败: {e}")
        return None


def is_trading_day(date_str):
    days = get_trading_days()
    if days is None:
        d = datetime.strptime(date_str, '%Y-%m-%d')
        return d.weekday() < 5
    return date_str in days


def get_last_trading_day(before_date=None):
    if before_date is None:
        before_date = datetime.now().strftime('%Y-%m-%d')
    days = get_trading_days()
    if days is None:
        from datetime import timedelta
        d = datetime.strptime(before_date, '%Y-%m-%d')
        while d.weekday() >= 5:
            d -= timedelta(days=1)
        return d.strftime('%Y-%m-%d')
    sorted_days = sorted([d for d in days if d <= before_date], reverse=True)
    return sorted_days[0] if sorted_days else None


def clear_caches():
    """清除所有数据缓存（每次新分析前调用，避免跨天使用旧数据）"""
    global _spot_em_cache, _trading_days_cache
    _spot_em_cache = None
    _trading_days_cache = None
