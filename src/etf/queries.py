"""
ETF数据查询模块
"""
import sqlite3
from typing import List, Tuple, Optional, Dict
from .database import get_connection


def get_latest_dates(n: int = 2) -> List[str]:
    """获取最近n个有数据的交易日"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT stat_date FROM etf_daily_share ORDER BY stat_date DESC LIMIT ?', (n,))
    dates = [d[0] for d in cursor.fetchall()]
    conn.close()
    return dates


def query_rising_etfs(days: int = 126) -> List[Tuple]:
    """查询最近days天份额上升的ETF"""
    conn = get_connection()
    cursor = conn.cursor()

    query = '''
        WITH period AS (
            SELECT sec_code, stat_date, tot_vol
            FROM etf_daily_share
            WHERE stat_date >= date('now', '-' || ? || ' days')
        ),
        first_last AS (
            SELECT p1.sec_code,
                COUNT(*) as data_days,
                (SELECT tot_vol FROM period p2 WHERE p2.sec_code = p1.sec_code ORDER BY stat_date ASC LIMIT 1) as start_vol,
                (SELECT tot_vol FROM period p3 WHERE p3.sec_code = p1.sec_code ORDER BY stat_date DESC LIMIT 1) as latest_vol,
                (SELECT stat_date FROM period p4 WHERE p4.sec_code = p1.sec_code ORDER BY stat_date ASC LIMIT 1) as start_date,
                (SELECT stat_date FROM period p5 WHERE p5.sec_code = p1.sec_code ORDER BY stat_date DESC LIMIT 1) as end_date
            FROM period p1
            GROUP BY sec_code
        )
        SELECT
            f.sec_code,
            i.sec_name,
            f.data_days,
            f.start_vol,
            f.latest_vol,
            ROUND((f.latest_vol - f.start_vol) / f.start_vol * 100, 2) as change_pct,
            f.start_date,
            f.end_date
        FROM first_last f
        LEFT JOIN etf_info i ON f.sec_code = i.sec_code
        WHERE f.start_vol > 0 AND f.latest_vol > f.start_vol
        ORDER BY change_pct DESC
    '''
    cursor.execute(query, (days,))
    results = cursor.fetchall()
    conn.close()
    return results


def query_etf_trend(sec_code: str, days: int = 100) -> List[Tuple]:
    """查询某ETF的历史趋势"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT stat_date, tot_vol
        FROM etf_daily_share
        WHERE sec_code = ? AND stat_date >= date('now', '-' || ? || ' days')
        ORDER BY stat_date
    ''', (sec_code, days))
    results = cursor.fetchall()
    conn.close()
    return results if results else []

def query_etf_info(sec_code: str) -> Optional[Dict]:
    """查询某ETF的详细信息"""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
                   SELECT *
                   FROM etf_info
                   WHERE sec_code = ?
                   ''', (sec_code,))
    results = cursor.fetchone()
    conn.close()
    return results if results else None

def query_securities_etf(sorted_by: str = 'volume', span: int = 1) -> List[Tuple]:
    """
    查询证券ETF份额变化

    Args:
        sorted_by: 'volume' 按份额排序, 'change' 按变化排序, 'pct' 按百分比排序
        span: 跨度天数，1=对比前1个交易日，5=对比5个交易日前

    Returns:
        (results, latest_date, prev_date)
    """
    conn = get_connection()
    cursor = conn.cursor()

    dates = get_latest_dates(span + 1)
    if len(dates) < 2:
        conn.close()
        return [], None, None

    latest_date, prev_date = dates[0], dates[-1]

    # 先获取所有证券相关ETF
    cursor.execute("""
        SELECT DISTINCT sec_code
        FROM etf_info
        WHERE full_name LIKE '%证券%' OR full_name LIKE '%保险%'
    """)
    target_codes = [row[0] for row in cursor.fetchall()]

    if not target_codes:
        conn.close()
        return []

    placeholders = ','.join(['?' for _ in target_codes])
    order_col = {
        'volume': 'd1.tot_vol DESC',
        'change': 'change DESC',
        'pct': 'pct_change DESC'
    }.get(sorted_by, 'd1.tot_vol DESC')

    query = f'''
        SELECT d1.sec_code, i.full_name,
               d1.tot_vol as vol_latest,
               d0.tot_vol as vol_prev,
               (d1.tot_vol - d0.tot_vol) as change,
               (d1.tot_vol - d0.tot_vol) * 100.0 / d0.tot_vol as pct_change
        FROM etf_daily_share d1
        JOIN etf_daily_share d0 ON d1.sec_code = d0.sec_code
        JOIN etf_info i ON d1.sec_code = i.sec_code
        WHERE d1.stat_date = ? AND d0.stat_date = ?
          AND d1.sec_code IN ({placeholders})
        ORDER BY {order_col}
    '''

    cursor.execute(query, [latest_date, prev_date] + target_codes)
    results = cursor.fetchall()
    conn.close()
    return results, latest_date, prev_date


def query_industry_etf(keyword: str, sorted_by: str = 'volume', span: int = 1) -> List[Tuple]:
    """按行业关键词查询ETF份额变化

    Args:
        keyword: 行业关键词，如 医药/银行/科技/消费/军工，支持模糊匹配
        sorted_by: 'volume' 按份额排序, 'change' 按变化排序, 'pct' 按百分比排序
        span: 跨度天数，1=对比前1个交易日，5=对比5个交易日前

    Returns:
        (results, latest_date, prev_date)
    """
    conn = get_connection()
    cursor = conn.cursor()

    dates = get_latest_dates(span + 1)
    if len(dates) < 2:
        conn.close()
        return [], None, None

    latest_date, prev_date = dates[0], dates[-1]

    cursor.execute("""
        SELECT DISTINCT sec_code
        FROM etf_info
        WHERE full_name LIKE ? OR sec_name LIKE ?
    """, (f'%{keyword}%', f'%{keyword}%'))
    target_codes = [row[0] for row in cursor.fetchall()]

    if not target_codes:
        conn.close()
        return [], latest_date, prev_date

    placeholders = ','.join(['?' for _ in target_codes])
    order_col = {
        'volume': 'd1.tot_vol DESC',
        'change': 'change DESC',
        'pct': 'pct_change DESC'
    }.get(sorted_by, 'd1.tot_vol DESC')

    query = f'''
        SELECT d1.sec_code, i.full_name,
               d1.tot_vol as vol_latest,
               d0.tot_vol as vol_prev,
               (d1.tot_vol - d0.tot_vol) as change,
               (d1.tot_vol - d0.tot_vol) * 100.0 / d0.tot_vol as pct_change
        FROM etf_daily_share d1
        JOIN etf_daily_share d0 ON d1.sec_code = d0.sec_code
        JOIN etf_info i ON d1.sec_code = i.sec_code
        WHERE d1.stat_date = ? AND d0.stat_date = ?
          AND d1.sec_code IN ({placeholders})
        ORDER BY {order_col}
    '''

    cursor.execute(query, [latest_date, prev_date] + target_codes)
    results = cursor.fetchall()
    conn.close()
    return results, latest_date, prev_date


def query_top_etfs(n: int = 10, by: str = 'change') -> Tuple:
    """
    查询份额变化最多的ETF

    Args:
        n: 返回数量
        by: 'change' 按绝对变化, 'pct' 按百分比变化

    Returns:
        (results, latest_date, prev_date)
    """
    conn = get_connection()
    cursor = conn.cursor()

    dates = get_latest_dates(2)
    if len(dates) < 2:
        conn.close()
        return [], None, None

    latest_date, prev_date = dates[0], dates[1]

    if by == 'pct':
        order_clause = 'pct_change DESC'
    else:
        order_clause = 'change DESC'

    query = '''
        SELECT d1.sec_code, i.full_name,
               d1.tot_vol as vol_latest,
               d0.tot_vol as vol_prev,
               (d1.tot_vol - d0.tot_vol) as change,
               (d1.tot_vol - d0.tot_vol) * 100.0 / d0.tot_vol as pct_change
        FROM etf_daily_share d1
        JOIN etf_daily_share d0 ON d1.sec_code = d0.sec_code
        JOIN etf_info i ON d1.sec_code = i.sec_code
        WHERE d1.stat_date = ? AND d0.stat_date = ?
          AND d0.tot_vol > 0
        ORDER BY {order_clause}
        LIMIT ?
    '''.format(order_clause=order_clause)

    cursor.execute(query, [latest_date, prev_date, n])
    results = cursor.fetchall()
    conn.close()
    return results, latest_date, prev_date


def query_etf_detail(sec_code: str, days: int = 30) -> List[Tuple]:
    """查询某ETF的份额+价格+排名详细走势

    Returns:
        [(stat_date, tot_vol, daily_chg, daily_chg_pct, close_price, daily_ret, rank), ...]
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT stat_date, tot_vol, close_price, num
        FROM etf_daily_share
        WHERE sec_code = ?
        ORDER BY stat_date DESC
        LIMIT ?
    ''', (sec_code, days))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return []

    rows = list(reversed(rows))  # 按时间升序

    result = []
    prev_vol = None
    prev_price = None

    for stat_date, tot_vol, close_price, num in rows:
        # 日份额变化 & 份额增幅
        daily_chg = 0
        daily_chg_pct = None
        if prev_vol is not None and tot_vol != prev_vol and prev_vol > 0:
            daily_chg = tot_vol - prev_vol
            daily_chg_pct = round(daily_chg / prev_vol * 100, 2)

        # 日价格收益
        daily_ret = None
        if prev_price and close_price and prev_price:
            daily_ret = round((close_price - prev_price) / prev_price * 100, 2)

        result.append((stat_date, tot_vol, daily_chg, daily_chg_pct, close_price, daily_ret, num))

        prev_vol = tot_vol
        if close_price:
            prev_price = close_price

    return result


def query_huijin_etf_trend(days: int = 10) -> List[Tuple]:
    """查询汇金系持仓ETF的份额-价格走势

    从十大持有人中筛选汇金系（汇金/证金）持仓占比>=0.5%的ETF，
    同一ETF代码只取占比最高的一条（去重）。

    Returns:
        [(sec_code, sec_name, holder_pct, [(stat_date, tot_vol, close_price), ...]), ...]
        按 holder_pct 降序排列
    """
    conn = get_connection()
    cursor = conn.cursor()

    # 获取最新报告期
    cursor.execute('SELECT stat_date FROM etf_top_holders GROUP BY stat_date ORDER BY COUNT(*) DESC LIMIT 1')
    latest_report = cursor.fetchone()[0]

    # 汇金系ETF代码（去重，取同一代码中占比最高的那条）
    cursor.execute('''
        SELECT h.sec_code, MAX(h.holder_pct) as max_pct
        FROM etf_top_holders h
        WHERE h.stat_date = ?
          AND (h.holder_name LIKE '%汇金%' OR h.holder_name LIKE '%证金%')
          AND h.holder_pct >= 0.5
        GROUP BY h.sec_code
        ORDER BY max_pct DESC
        LIMIT 50
    ''', (latest_report,))
    huijin_codes = cursor.fetchall()

    if not huijin_codes:
        conn.close()
        return []

    # 获取这些ETF的名称和最近days天的份额/价格
    placeholders = ','.join(['?' for _ in huijin_codes])
    codes = [c[0] for c in huijin_codes]
    pct_map = {c[0]: c[1] for c in huijin_codes}

    # 获取最近日期范围
    cursor.execute('''
        SELECT DISTINCT stat_date FROM etf_daily_share
        ORDER BY stat_date DESC LIMIT ?
    ''', (days + 5,))  # 多取几天防止节假日缺失
    all_dates = sorted([d[0] for d in cursor.fetchall()])
    recent_dates = all_dates[-days:] if len(all_dates) >= days else all_dates

    # 批量获取每个ETF在最近日期的数据
    cursor.execute(f'''
        SELECT d.sec_code, d.stat_date, d.tot_vol, d.close_price, i.sec_name
        FROM etf_daily_share d
        JOIN etf_info i ON d.sec_code = i.sec_code
        WHERE d.sec_code IN ({placeholders})
          AND d.stat_date >= ?
        ORDER BY d.sec_code, d.stat_date
    ''', codes + [recent_dates[0]])

    # 组织数据: {code: {name, pct, dates: {date: (vol, price)}}}
    raw = {}
    name_map = {}
    for row in cursor.fetchall():
        code, date, vol, price, name = row
        if code not in raw:
            raw[code] = {}
            name_map[code] = name or code
        raw[code][date] = (vol, price)

    conn.close()

    # 按日期对齐，只保留有数据的最近days天
    result = []
    for code, max_pct in huijin_codes:
        name = name_map.get(code, code)
        data = []
        for d in recent_dates:
            if d in raw.get(code, {}):
                data.append((d, raw[code][d][0], raw[code][d][1]))
        if data:
            result.append((code, name, max_pct, data))

    return result


def check_data_completeness(days: int = 20) -> List[Tuple]:
    """检查数据库数据完整性

    Args:
        days: 检查最近N天的数据

    Returns:
        [(stat_date, cnt), ...]  日期和当日ETF数量
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT stat_date, COUNT(*) as cnt
        FROM etf_daily_share
        GROUP BY stat_date
        ORDER BY stat_date DESC
        LIMIT ?
    ''', (days,))
    daily_counts = cursor.fetchall()
    conn.close()
    return daily_counts


def query_top_holders(sec_code: str) -> Tuple:
    """
    查询某ETF的十大持有人

    Args:
        sec_code: ETF代码

    Returns:
        (holders_list, stat_date)
    """
    conn = get_connection()
    cursor = conn.cursor()

    # 获取最新报告期
    cursor.execute('''
        SELECT stat_date FROM etf_top_holders
        WHERE sec_code = ?
        ORDER BY stat_date DESC
        LIMIT 1
    ''', (sec_code,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return [], None
    stat_date = row[0]

    # 获取十大持有人
    cursor.execute('''
        SELECT rank, holder_name, holder_share, holder_pct
        FROM etf_top_holders
        WHERE sec_code = ? AND stat_date = ?
        ORDER BY rank
    ''', (sec_code, stat_date))
    holders = cursor.fetchall()
    conn.close()
    return holders, stat_date


def query_holders_by_type(holder_type: str = None, min_pct: float = 1.0) -> List[Tuple]:
    """
    按持有人类型查询（如保险公司、信托等）

    Args:
        holder_type: 持有人类型关键词，如 "保险"、"信托"、"私募"
        min_pct: 最小持有比例

    Returns:
        [(sec_code, full_name, holder_name, holder_pct, stat_date), ...]
    """
    conn = get_connection()
    cursor = conn.cursor()

    # 获取数据量最多的报告期（因为有些ETF日期解析可能出错）
    cursor.execute('''
        SELECT stat_date FROM etf_top_holders
        GROUP BY stat_date
        ORDER BY COUNT(*) DESC
        LIMIT 1
    ''')
    latest_date = cursor.fetchone()[0]

    if holder_type:
        cursor.execute('''
            SELECT h.sec_code, i.full_name, h.holder_name, h.holder_pct, h.stat_date
            FROM etf_top_holders h
            LEFT JOIN etf_info i ON h.sec_code = i.sec_code
            WHERE h.stat_date = ?
              AND h.holder_name LIKE ?
              AND h.holder_pct >= ?
            ORDER BY h.holder_pct DESC
            LIMIT 100
        ''', (latest_date, f'%{holder_type}%', min_pct))
    else:
        cursor.execute('''
            SELECT h.sec_code, i.full_name, h.holder_name, h.holder_pct, h.stat_date
            FROM etf_top_holders h
            LEFT JOIN etf_info i ON h.sec_code = i.sec_code
            WHERE h.stat_date = ?
              AND h.holder_pct >= ?
            ORDER BY h.holder_pct DESC
            LIMIT 100
        ''', (latest_date, min_pct))

    results = cursor.fetchall()
    conn.close()
    return results
