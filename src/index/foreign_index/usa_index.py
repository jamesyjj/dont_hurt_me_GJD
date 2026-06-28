import datetime

import akshare as ak
import pandas as pd

from src.etf.database import get_connection

# 美股指数代码 → (显示名称, 市场, 货币, 发布机构)
USA_INDEX_MAP = {
    ".INX":  ("S&P 500",                "US", "USD", "S&P Dow Jones Indices"),
    ".DJI":  ("Dow Jones Industrial Average", "US", "USD", "S&P Dow Jones Indices"),
    ".NDX":  ("Nasdaq 100",             "US", "USD", "Nasdaq Inc."),
    ".IXIC": ("Nasdaq Composite",       "US", "USD", "Nasdaq Inc."),
}


def fetch_usa_index(symbol: str):
    """抓取美股指数历史日线数据，写入 index_daily 表。

    自动将指数元信息同步到 index_info 表（若不存在则插入）。

    Args:
        symbol: akshare 符号，如 ".INX"、".DJI"、".NDX"、".IXIC"

    Returns:
        写入的日线条数
    """
    # 1. 获取指数元信息
    info = USA_INDEX_MAP.get(symbol)
    if info is None:
        print(f'[usa_index] 未知指数符号: {symbol}')
        return 0
    display_name, market, currency, publisher = info
    code = symbol  # .INX / .DJI / .NDX / .IXIC

    # 2. 拉取历史日线
    df = ak.index_us_stock_sina(symbol=symbol)
    if df is None or df.empty:
        print(f'[usa_index] 未获取到数据: {symbol}')
        return 0

    # 3. 列名映射（akshare 英文 → index_daily 字段）
    col_map = {
        'date': 'trade_date',
        'open': 'open',
        'high': 'high',
        'low': 'low',
        'close': 'close',
        'volume': 'volume',
        'amount': 'amount',
    }
    df = df.rename(columns=col_map)

    # 4. 构造 records（按日期正向排序，从收盘价计算涨跌幅(%)/涨跌额）
    df = df.sort_values('trade_date')  # 确保从旧到新
    records = []
    prev_close = None
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    for _, row in df.iterrows():
        raw_date = row.get('trade_date')
        if raw_date is None:
            continue
        # 日期统一为 YYYYMMDD 整数
        if isinstance(raw_date, (int, float)):
            trade_date = int(raw_date)
        else:
            trade_date = int(str(raw_date).replace('-', '')[:8])

        close = row.get('close')
        if pd.notna(close):
            close = float(close)
        else:
            close = None

        # 从收盘价计算涨跌幅(%)和涨跌额
        change_percent = None
        change_amount = None
        if close is not None and prev_close is not None and prev_close != 0:
            change_amount = close - prev_close
            change_percent = round(change_amount / prev_close * 100, 5)  # %值，保留5位小数
        prev_close = close

        records.append({
            'index_code': code,
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

    # 5. 写入数据库
    conn = get_connection()
    cursor = conn.cursor()

    # 5a. 确保 index_info 有此指数
    cursor.execute("""
        INSERT OR IGNORE INTO index_info
        (index_code, index_name, market, publisher, category, currency,
         create_time, update_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (code, display_name, market, publisher, "宽基", currency, now, now))

    # 5b. 批量插入 index_daily
    inserted = 0
    for rec in records:
        try:
            cursor.execute("""
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
            print(f'[usa_index] 插入失败 {code} {rec["trade_date"]}: {e}')

    conn.commit()
    conn.close()
    print(f'[usa_index] {symbol}({display_name}) 写入 {inserted} 条 (共 {len(records)} 条)')
    return inserted


def fetch_all_usa_indices():
    """批量抓取美股四大指数日线数据。"""
    for sym in (".INX", ".DJI", ".NDX", ".IXIC"):
        fetch_usa_index(sym)
        import time
        time.sleep(2)


if __name__ == '__main__':
    # 抓取单个
    # fetch_usa_index(".INX")
    # 批量
    fetch_all_usa_indices()
