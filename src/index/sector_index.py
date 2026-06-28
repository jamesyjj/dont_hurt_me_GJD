import datetime
import sys
import os

import akshare as ak
import pandas as pd

# 允许从项目根导入 src.etf.database
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from src.etf.database import get_connection

def fetch_index_info_cn():
    """从 akshare 获取全量指数列表，写入 index_info 表。"""
    df = ak.index_stock_info()
    if df is None or df.empty:
        print('[index_info] 未获取到数据')
        return 0

    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    inserted = 0

    for _, row in df.iterrows():
        code = str(row['index_code'])
        # 确定市场：0开头 → 上海，其他 → 深圳
        market = 'SH' if code[0] == '0' else 'SZ'

        try:
            cursor.execute('''
                INSERT OR REPLACE INTO index_info
                (index_code, index_name, market, publisher, category,
                 currency, create_time, update_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                code,
                row['display_name'],
                market,
                None,
                None,
                'CNY',
                now,
                now,
            ))
            inserted += 1
        except Exception as e:
            print(f'[index_info] 插入失败 {code}: {e}')

    conn.commit()
    conn.close()
    print(f'[index_info] 写入 {inserted} 条')
    return inserted



def _determine_symbol(index_code: str) -> tuple:
    """补全指数代码前缀，供 akshare 使用。

    Args:
        index_code: 指数代码，如 000300、sh000300、399006

    Returns:
        (symbol, clean_code) — symbol 用于 akshare，clean_code 入库（不带前缀）
    """
    code = index_code.strip().lower()
    if code.startswith('sh') or code.startswith('sz'):
        clean = code[2:]
        return code, clean
    # 纯数字代码：首位 0 → 上海，其他 → 深圳
    if code[0] == '0':
        return f'sh{code}', code
    else:
        return f'sz{code}', code


def fetch_sector_index(index_code: str):
    """抓取A股指数的历史日线数据（akshare），写入 index_daily 表。

    从 akshare 拉取日线，由收盘价自行计算 change_percent（%值，保留5位小数）；
    amplitude / turnover_rate 来自 akshare 已是%值，保留2位小数。

    Args:
        index_code: 指数代码，如 000300、sh000300、399006

    Returns:
        写入的日线条数
    """
    symbol, clean_code = _determine_symbol(index_code)

    # 1. 拉取历史日线数据
    df = ak.stock_zh_index_daily(symbol)
    if df is None or df.empty:
        print(f'[sector_index] 未获取到数据: {symbol}')
        return 0

    # 2. 列名映射（akshare 英文列名 → index_daily 字段；change_percent 由收盘价自行计算，amplitude/turnover_rate 来自 akshare 已是%值）
    col_map = {
        'date': 'trade_date',
        'open': 'open',
        'high': 'high',
        'low': 'low',
        'close': 'close',
        'volume': 'volume',
        'amount': 'amount',
        'amplitude': 'amplitude',
        'turnover_rate': 'turnover_rate',
    }
    df = df.rename(columns=col_map)

    # 3. 构造 index_daily 所需字段（按日期正向排序，从收盘价计算涨跌幅(%)/涨跌额）
    df = df.sort_values('trade_date')
    records = []
    prev_close = None
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    for _, row in df.iterrows():
        raw_date = row.get('trade_date')
        if raw_date is None:
            continue
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

        rec = {
            'index_code': clean_code,
            'trade_date': trade_date,
            'open': row.get('open'),
            'high': row.get('high'),
            'low': row.get('low'),
            'close': close,
            'volume': row.get('volume'),
            'amount': row.get('amount'),
            'amplitude': round(float(row.get('amplitude')), 2) if pd.notna(row.get('amplitude')) else None,  # %值，保留2位小数
            'change_percent': change_percent,
            'change_amount': change_amount,
            'turnover_rate': round(float(row.get('turnover_rate')), 2) if pd.notna(row.get('turnover_rate')) else None,  # %值，保留2位小数
            'source': 'akshare',
            'create_time': now,
            'update_time': now,
        }
        records.append(rec)

    # 4. 写入数据库
    conn = get_connection()
    cursor = conn.cursor()
    inserted = 0

    for rec in records:
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO index_daily
                (index_code, trade_date, open, high, low, close,
                 volume, amount, amplitude, change_percent, change_amount,
                 turnover_rate, source, create_time, update_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                rec['index_code'], rec['trade_date'],
                rec['open'], rec['high'], rec['low'], rec['close'],
                rec['volume'], rec['amount'],
                rec['amplitude'], rec['change_percent'], rec['change_amount'],
                rec['turnover_rate'], rec['source'],
                rec['create_time'], rec['update_time'],
            ))
            inserted += 1
        except Exception as e:
            print(f'[sector_index] 插入失败 {symbol} {rec["trade_date"]}: {e}')

    conn.commit()
    conn.close()

    print(f'[sector_index] {symbol} 写入 {inserted} 条 (共 {len(records)} 条)')
    return inserted


if __name__ == '__main__':
    # 示例：获取全量指数列表并入库
    fetch_index_info_cn()
    # 示例：抓取深圳399552（证券龙头）指数日线
    # fetch_sector_index('sz399552')
