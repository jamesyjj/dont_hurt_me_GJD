import datetime

import akshare as ak
import pandas as pd

from src.etf.database import get_connection


def fetch_index_daily_hk(symbol: str):
    """抓取港股指数历史日线数据（新浪财经），写入 index_daily 表。

    从 index_info 表查询该指数元信息（须已入库且 market='HK'），
    仅抓取日线数据写入 index_daily，不重复写入 index_info。

    Args:
        symbol: 港股指数代码，如 "HSI"、"HSCEI"、"HSTECH"、"CES100"

    Returns:
        写入的日线条数
    """
    # 1. 从数据库验证指数存在且为港股
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT index_name FROM index_info
        WHERE index_code = ? AND market = 'HK'
        LIMIT 1
    """, (symbol,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        print(f'[index_daily_hk] 未在 index_info 中找到 {symbol}（或 market 不是 HK）')
        return 0
    display_name = row[0]

    # 2. 拉取历史日线
    df = ak.stock_hk_index_daily_sina(symbol=symbol)
    if df is None or df.empty:
        print(f'[index_daily_hk] 未获取到数据: {symbol}')
        return 0

    # 3. 列名映射
    col_map = {
        'date':   'trade_date',
        'open':   'open',
        'high':   'high',
        'low':    'low',
        'close':  'close',
        'volume': 'volume',
        'amount': 'amount',
    }
    df = df.rename(columns=col_map)

    # 4. 构造 records（正向排序，从收盘价计算涨跌幅(%)/涨跌额）
    df = df.sort_values('trade_date')
    records = []
    prev_close = None
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    for _, row in df.iterrows():
        raw_date = row.get('trade_date')
        if raw_date is None:
            continue
        trade_date = int(str(raw_date).replace('-', '')[:8])

        close = row.get('close')
        if pd.notna(close):
            close = float(close)
        else:
            close = None

        change_percent = None
        change_amount = None
        if close is not None and prev_close is not None and prev_close != 0:
            change_amount = close - prev_close
            change_percent = round(change_amount / prev_close * 100, 5)  # %值，保留5位小数
        prev_close = close

        records.append({
            'index_code': symbol,
            'trade_date': trade_date,
            'open': row.get('open'),
            'high': row.get('high'),
            'low': row.get('low'),
            'close': close,
            'volume': row.get('volume'),
            'amount': row.get('amount'),
            'amplitude': None,
            'change_percent': change_percent,
            'change_amount': change_amount,
            'turnover_rate': None,
            'source': 'sina',
            'create_time': now,
            'update_time': now,
        })

    # 5. 写入 index_daily（index_info 已在之前写入，不再重复操作）
    conn2 = get_connection()
    cursor2 = conn2.cursor()
    inserted = 0
    for rec in records:
        try:
            cursor2.execute("""
                INSERT OR REPLACE INTO index_daily
                (index_code, trade_date, open, high, low, close,
                 volume, amount, amplitude, change_percent, change_amount,
                 turnover_rate, source, create_time, update_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rec['index_code'], rec['trade_date'],
                rec['open'], rec['high'], rec['low'], rec['close'],
                rec['volume'], rec['amount'],
                rec['amplitude'], rec['change_percent'], rec['change_amount'],
                rec['turnover_rate'], rec['source'],
                rec['create_time'], rec['update_time'],
            ))
            inserted += 1
        except Exception as e:
            print(f'[index_daily_hk] 插入失败 {symbol} {rec["trade_date"]}: {e}')

    conn2.commit()
    conn2.close()
    print(f'[index_daily_hk] {symbol}({display_name}) 写入 {inserted} 条 (共 {len(records)} 条)')
    return inserted


def fetch_all_hk_indices():
    """批量抓取所有已知港股指数日线数据。"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT index_code FROM index_info WHERE market = 'HK'")
    codes = [r[0] for r in cursor.fetchall()]
    conn.close()

    import time
    for code in codes:
        fetch_index_daily_hk(code)
        time.sleep(2)

def fetch_index_daily_hk_now():
    """获取港股指数实时行情，写入 index_daily 表（仅当天数据）。

    调用 ak.stock_hk_index_spot_sina() 获取全量实时数据，
    筛选 index_info 中 market='HK' 的指数后写入。
    """
    # 1. 从 index_info 获取所有港股指数代码
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT index_code FROM index_info WHERE market = 'HK'")
    hk_codes = {r[0] for r in cursor.fetchall()}
    conn.close()

    if not hk_codes:
        print('[index_daily_hk_now] index_info 中没有 market=HK 的指数')
        return 0

    # 2. 获取实时行情
    df = ak.stock_hk_index_spot_sina()
    if df is None or df.empty:
        print('[index_daily_hk_now] 未获取到实时行情')
        return 0

    # 3. 筛选仅保留 index_info 中已有的指数
    df = df[df['代码'].isin(hk_codes)].copy()
    if df.empty:
        print('[index_daily_hk_now] 实时行情中没有匹配的港股指数')
        return 0
    pd.set_option('display.max_columns', None)
    print(df)

    # 4. 列映射 + 补充 trade_date
    now = datetime.datetime.now()
    trade_date = int(now.strftime('%Y%m%d'))
    now_str = now.strftime('%Y-%m-%d %H:%M:%S')

    records = []
    for _, row in df.iterrows():
        records.append({
            'index_code':      row['代码'],
            'trade_date':      trade_date,
            'open':            row.get('今开'),
            'high':            row.get('最高'),
            'low':             row.get('最低'),
            'close':           row.get('最新价'),
            'volume':          None,
            'amount':          None,
            'amplitude':       None,
            'change_percent':  round(float(row.get('涨跌幅')), 5) if pd.notna(row.get('涨跌幅')) else None,  # %值，保留5位小数
            'change_amount':   row.get('涨跌额'),
            'turnover_rate':   None,
            'source':          'sina',
            'create_time':     now_str,
            'update_time':     now_str,
        })

    # 5. 写入 index_daily
    conn2 = get_connection()
    cursor2 = conn2.cursor()
    inserted = 0
    for rec in records:
        try:
            cursor2.execute("""
                INSERT OR REPLACE INTO index_daily
                (index_code, trade_date, open, high, low, close,
                 volume, amount, amplitude, change_percent, change_amount,
                 turnover_rate, source, create_time, update_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rec['index_code'], rec['trade_date'],
                rec['open'], rec['high'], rec['low'], rec['close'],
                rec['volume'], rec['amount'],
                rec['amplitude'], rec['change_percent'], rec['change_amount'],
                rec['turnover_rate'], rec['source'],
                rec['create_time'], rec['update_time'],
            ))
            inserted += 1
        except Exception as e:
            print(f'[index_daily_hk_now] 插入失败 {rec["index_code"]}: {e}')

    conn2.commit()
    conn2.close()
    print(f'[index_daily_hk_now] {trade_date} 写入 {inserted} 条港股指数实时数据')
    return inserted


def fetch_index_daily_hk_now_em():
    """获取港股指数实时行情（东方财富），写入 index_daily 表。

    调用 ak.stock_hk_index_spot_em() 获取全量实时数据，
    筛选 index_info 中 market='HK' 的指数后写入。
    相比新浪接口多了成交量/成交额字段。
    """
    # 1. 从 index_info 获取所有港股指数代码
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT index_code FROM index_info WHERE market = 'HK'")
    hk_codes = {r[0] for r in cursor.fetchall()}
    conn.close()

    if not hk_codes:
        print('[index_daily_hk_now_em] index_info 中没有 market=HK 的指数')
        return 0

    # 2. 获取实时行情
    df = ak.stock_hk_index_spot_em()
    if df is None or df.empty:
        print('[index_daily_hk_now_em] 未获取到实时行情')
        return 0

    # 3. 筛选仅保留 index_info 中已有的指数
    df = df[df['代码'].isin(hk_codes)].copy()
    if df.empty:
        print('[index_daily_hk_now_em] 实时行情中没有匹配的港股指数')
        return 0
    pd.set_option('display.max_columns', None)
    print(df)

    # 4. 列映射 + 补充 trade_date
    now = datetime.datetime.now()
    trade_date = int(now.strftime('%Y%m%d'))
    now_str = now.strftime('%Y-%m-%d %H:%M:%S')

    records = []
    for _, row in df.iterrows():
        records.append({
            'index_code':      row['代码'],
            'trade_date':      trade_date,
            'open':            row.get('今开'),
            'high':            row.get('最高'),
            'low':             row.get('最低'),
            'close':           row.get('最新价'),
            'volume':          row.get('成交量'),
            'amount':          row.get('成交额'),
            'amplitude':       None,
            'change_percent':  round(float(row.get('涨跌幅')), 5) if pd.notna(row.get('涨跌幅')) else None,  # %值，保留5位小数
            'change_amount':   row.get('涨跌额'),
            'turnover_rate':   None,
            'source':          'eastmoney',
            'create_time':     now_str,
            'update_time':     now_str,
        })

    # 5. 写入 index_daily
    conn2 = get_connection()
    cursor2 = conn2.cursor()
    inserted = 0
    for rec in records:
        try:
            cursor2.execute("""
                INSERT OR REPLACE INTO index_daily
                (index_code, trade_date, open, high, low, close,
                 volume, amount, amplitude, change_percent, change_amount,
                 turnover_rate, source, create_time, update_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rec['index_code'], rec['trade_date'],
                rec['open'], rec['high'], rec['low'], rec['close'],
                rec['volume'], rec['amount'],
                rec['amplitude'], rec['change_percent'], rec['change_amount'],
                rec['turnover_rate'], rec['source'],
                rec['create_time'], rec['update_time'],
            ))
            inserted += 1
        except Exception as e:
            print(f'[index_daily_hk_now_em] 插入失败 {rec["index_code"]}: {e}')

    conn2.commit()
    conn2.close()
    print(f'[index_daily_hk_now_em] {trade_date} 写入 {inserted} 条港股指数实时数据')
    return inserted


if __name__ == '__main__':
    fetch_index_daily_hk("HSI")
    fetch_index_daily_hk_now()
    # fetch_index_daily_hk_now_em()
