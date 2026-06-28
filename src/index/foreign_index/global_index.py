import datetime

import akshare as ak
import pandas as pd

from src.etf.database import get_connection


def get_american_index():
    index_us_stock_sina_df = ak.index_us_stock_sina(symbol=".INX")
    print(index_us_stock_sina_df)
    index_us_stock_sina_df2 = ak.index_us_stock_sina(symbol=".DJI")
    index_us_stock_sina_df2 = ak.index_us_stock_sina(symbol=".INX")
    index_us_stock_sina_df2 = ak.index_us_stock_sina(symbol=".NDX")


# 全球指数代码 → (市场, 货币)
GLOBAL_INDEX_MAP = {
    "UKX":       ("UK",  "GBP"),
    "DAX":       ("DE",  "EUR"),
    "INDEXCF":   ("RU",  "RUB"),
    "CAC":       ("FR",  "EUR"),
    "SWI20":     ("CH",  "CHF"),
    "FTSEMIB":   ("IT",  "EUR"),
    "AEX":       ("NL",  "EUR"),
    "IBEX":      ("ES",  "EUR"),
    "SX5E":      ("EU",  "EUR"),
    "GSPTSE":    ("CA",  "CAD"),
    "MXX":       ("MX",  "MXN"),
    "IBOV":      ("BR",  "BRL"),
    "TWJQ":      ("TW",  "TWD"),
    "NKY":       ("JP",  "JPY"),
    "KOSPI":     ("KR",  "KRW"),
    "JCI":       ("ID",  "IDR"),
    "SENSEX":    ("IN",  "INR"),
    "AS51":      ("AU",  "AUD"),
    "NZ250":     ("NZ",  "NZD"),
    "CASE":      ("EG",  "EGP"),
}


def fetch_index_info_global():
    """从 akshare 获取全球指数列表，写入 index_info 表。

    数据来源：ak.index_global_name_table()，返回 20 只全球主要股指。
    使用 GLOBAL_INDEX_MAP 映射确定市场和货币，未映射的代码默认 (US, USD)。
    """
    df = ak.index_global_name_table()
    if df is None or df.empty:
        print('[index_info_global] 未获取到数据')
        return 0

    # 统一列名
    col_map = {df.columns[0]: 'index_name', df.columns[1]: 'index_code'}
    df = df.rename(columns=col_map)

    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    inserted = 0

    for _, row in df.iterrows():
        code = str(row['index_code']).strip()
        # 从映射取市场/货币，未知代码默认 (US, USD)
        market, currency = GLOBAL_INDEX_MAP.get(code, ("US", "USD"))

        try:
            cursor.execute('''
                INSERT OR REPLACE INTO index_info
                (index_code, index_name, market, publisher, category,
                 currency, create_time, update_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                code,
                row['index_name'],
                market,
                None,
                None,
                currency,
                now,
                now,
            ))
            inserted += 1
        except Exception as e:
            print(f'[index_info_global] 插入失败 {code}: {e}')

    conn.commit()
    conn.close()
    print(f'[index_info_global] 写入 {inserted} 条全球指数')
    return inserted


def fetch_index_daily_global(index_code: str):
    """抓取全球指数历史日线数据（新浪财经），写入 index_daily 表。

    从 index_info 表读取名称后直接传给新浪财经接口（无需转换命名）。
    仅适用于非港股、非美股的全球指数（如英/德/法/日/澳等）。

    Args:
        index_code: 新浪财经代码（与 index_global_name_table 一致），
                    如 "UKX"、"DAX"、"NKY"、"CAC"
    """
    # 1. 从数据库 index_info 读指数名称
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT index_name FROM index_info
        WHERE index_code = ? AND market NOT IN ('US', 'HK')
        LIMIT 1
    """, (index_code,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        print(f'[index_daily_global] 未在 index_info 中找到 {index_code}（或该指数属于 US/HK 市场）')
        return 0

    name = row[0]

    # 2. 拉取历史日线（新浪接口直接用原名，无需转换）
    df = ak.index_global_hist_sina(symbol=name)
    if df is None or df.empty:
        print(f'[index_daily_global] 未获取到数据: {index_code}({name})')
        return 0

    # 3. 列名映射（新浪返回固定列：date/open/high/low/close/volume）
    col_map = {
        'date':   'trade_date',
        'open':   'open',
        'high':   'high',
        'low':    'low',
        'close':  'close',
        'volume': 'volume',
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
            'index_code': index_code,
            'trade_date': trade_date,
            'open': row.get('open'),
            'high': row.get('high'),
            'low': row.get('low'),
            'close': close,
            'volume': row.get('volume'),
            'amount': None,
            'amplitude': None,
            'change_percent': change_percent,
            'change_amount': change_amount,
            'turnover_rate': None,
            'source': 'sina',
            'create_time': now,
            'update_time': now,
        })

    # 5. 写入数据库
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
            print(f'[index_daily_global] 插入失败 {index_code} {rec["trade_date"]}: {e}')

    conn2.commit()
    conn2.close()
    print(f'[index_daily_global] {index_code}({name}) 写入 {inserted} 条 (共 {len(records)} 条)')
    return inserted

if __name__ == '__main__':
    # df = ak.index_global_name_table()
    # print(df)
    # fetch_index_info_global()
    fetch_index_daily_global("KOSPI")