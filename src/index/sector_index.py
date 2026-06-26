import datetime
import sys
import os

import akshare as ak

# 允许从项目根导入 src.etf.database
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from src.etf.database import get_connection

def get_index_info_cn():
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


def get_sector_index(index_code: str):
    """抓取指定指数的历史日线数据，写入 index_daily 表。

    Args:
        index_code: 指数代码，如 000300、sh000300、399006
    """
    symbol, clean_code = _determine_symbol(index_code)

    # 1. 拉取历史日线数据
    df = ak.stock_zh_index_daily(symbol)
    if df is None or df.empty:
        print(f'[sector_index] 未获取到数据: {symbol}')
        return 0

    # 2. 列名映射（akshare 英文列名 → index_daily 字段）
    col_map = {
        'date': 'trade_date',
        'open': 'open',
        'high': 'high',
        'low': 'low',
        'close': 'close',
        'volume': 'volume',
        'amount': 'amount',
        'amplitude': 'amplitude',
        'pct_change': 'change_percent',
        'change': 'change_amount',
        'turnover_rate': 'turnover_rate',
    }
    df_renamed = df.rename(columns=col_map)

    # 3. 构造 index_daily 所需字段
    records = []
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    for _, row in df_renamed.iterrows():
        raw_date = row.get('trade_date')
        if raw_date is None:
            continue
        if isinstance(raw_date, (int, float)):
            trade_date = int(raw_date)
        else:
            trade_date = int(str(raw_date).replace('-', '')[:8])

        rec = {
            'index_code': clean_code,
            'trade_date': trade_date,
            'open': row.get('open'),
            'high': row.get('high'),
            'low': row.get('low'),
            'close': row.get('close'),
            'volume': row.get('volume'),
            'amount': row.get('amount'),
            'amplitude': row.get('amplitude'),
            'change_percent': row.get('change_percent'),
            'change_amount': row.get('change_amount'),
            'turnover_rate': row.get('turnover_rate'),
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
    get_index_info_cn()
    # 示例：抓取深圳399552（证券龙头）指数日线
    # get_sector_index('sz399552')
