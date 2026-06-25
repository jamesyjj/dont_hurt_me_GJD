import datetime
import sqlite3
import os
import time

import akshare as ak
import pandas as pd

from pathlib import Path


def _get_db_path() -> str:
    """获取数据库路径（相对此脚本位置：项目根/data/etf_data.db）"""
    return os.path.join(Path(__file__).parent.parent.parent, 'data', 'etf_data.db')


# FRED 系列ID → (英文名, 中文名, 频率)
FRED_SERIES = {
    # "CPIAUCSL": ("CPI All Items", "消费者物价指数", "M"),
    "UNRATE": ("Unemployment Rate", "失业率", "M"),
    "FEDFUNDS": ("Federal Funds Effective Rate", "联邦基金利率", "M"),
    "CPILFESL": ("Core CPI", "核心CPI", "M"),
    "PPIACO": ("Producer Price Index by Commodity", "工业品出厂价格指数PPI", "M"),
    "PCEPI": ("Personal Consumption Expenditures", "个人消费支出价格指数PCE", "M"),
    "PCEPILFE": ("Personal Consumption Expenditures Excluding Food and Energy", "核心PCE", "M"),
    "DGS10": ("Market Yield on U.S. Treasury Securities at 10-Year Constant Maturity, Quoted on an Investment Basis", "美国10年国债收益率", "M")
}


def get_gdp():
    """获取美国GDP数据（akshare）"""
    macro_usa_gdp_monthly_df = ak.macro_usa_gdp_monthly()
    print(macro_usa_gdp_monthly_df)

# 获取fred数据
# req: 所需数据全称
# 全程列表如下：CPIAUCSL，UNRATE，FEDFUNDS（待补充）
def get_fred(series_id: str) -> pd.DataFrame:
    """从FRED下载CSV数据

    Args:
        series_id: FRED系列ID（如 CPIAUCSL / UNRATE / FEDFUNDS）

    Returns:
        包含 observation_date 和 series_id 列的DataFrame
    """
    url = (
        "https://fred.stlouisfed.org/graph/fredgraph.csv"
        f"?id={series_id}"
    )
    df = pd.read_csv(url, parse_dates=["observation_date"])
    print(df.tail())
    print("总条数:", len(df))
    print("最早日期:", df.iloc[0])
    print("最新日期:", df.iloc[-1])
    return df


def calc_yoy_growth(month: str, series_id: str, country: str = "US") -> float | None:
    """计算同比增长（YoY）——本月值 / 去年同月值 - 1

    Args:
        month: 月份，格式 "YYYY-MM"，如 "2026-06"
        series_id: FRED系列ID，如 "CPIAUCSL"
        country: 国家代码，默认 US

    Returns:
        同比增长率（小数），如 0.032 表示 +3.2%；数据不足时返回 None
    """
    year, mon = month.split("-")
    current_month = f"{year}-{mon}"
    last_year_month = f"{int(year) - 1}-{mon}"

    conn = sqlite3.connect(_get_db_path())
    cursor = conn.cursor()

    cursor.execute("""
        SELECT value FROM macro_index
        WHERE country = ? AND indicator_code = ?
          AND strftime('%Y-%m', observation_date) = ?
        ORDER BY observation_date DESC LIMIT 1
    """, (country, series_id, current_month))
    row_current = cursor.fetchone()

    cursor.execute("""
        SELECT value FROM macro_index
        WHERE country = ? AND indicator_code = ?
          AND strftime('%Y-%m', observation_date) = ?
        ORDER BY observation_date DESC LIMIT 1
    """, (country, series_id, last_year_month))
    row_last_year = cursor.fetchone()

    conn.close()

    if row_current is None or row_last_year is None:
        return None

    current_val, last_year_val = row_current[0], row_last_year[0]
    if last_year_val == 0:
        return None

    return (current_val - last_year_val) / last_year_val


def calc_mom_growth(month: str, series_id: str, country: str = "US") -> float | None:
    """计算环比增长（MoM）——本月值 / 上月值 - 1

    Args:
        month: 月份，格式 "YYYY-MM"，如 "2026-06"
        series_id: FRED系列ID，如 "CPIAUCSL"
        country: 国家代码，默认 US

    Returns:
        环比增长率（小数），如 -0.001 表示 -0.1%；数据不足时返回 None
    """
    conn = sqlite3.connect(_get_db_path())
    cursor = conn.cursor()

    cursor.execute("""
        SELECT observation_date, value FROM macro_index
        WHERE country = ? AND indicator_code = ?
          AND strftime('%Y-%m', observation_date) <= ?
        ORDER BY observation_date DESC
        LIMIT 2
    """, (country, series_id, month))
    rows = cursor.fetchall()
    conn.close()

    if len(rows) < 2:
        return None

    current_val, prev_val = rows[0][1], rows[1][1]
    if prev_val == 0:
        return None

    return (current_val - prev_val) / prev_val


def query_series(series_id: str, month: str = None, country: str = "US"):
    """查询指定系列在指定月份的值和同比/环比增长率

    Args:
        series_id: FRED系列ID，如 "CPIAUCSL"
        month: 月份，格式 "YYYY-MM"，默认当前月份
        country: 国家代码，默认 US

    Returns:
        dict：{"value": 数值, "yoy": 同比增长, "mom": 环比增长}
        数据不存在时对应值为 None
    """
    if month is None:
        month = datetime.date.today().strftime("%Y-%m")

    conn = sqlite3.connect(_get_db_path())
    cursor = conn.cursor()
    cursor.execute("""
        SELECT value, yoy_growth, mom_growth
        FROM macro_index
        WHERE country = ? AND indicator_code = ?
          AND strftime('%Y-%m', observation_date) = ?
        ORDER BY observation_date DESC
        LIMIT 1
    """, (country, series_id, month))
    row = cursor.fetchone()
    conn.close()

    name_cn = FRED_SERIES.get(series_id, (series_id, series_id, "M"))[1]

    if row is None:
        print(f"{name_cn}({series_id}) {month} 无数据")
        return {"value": None, "yoy": None, "mom": None}

    value, yoy, mom = row
    yoy_str = f"{yoy:+.3%}" if yoy is not None else "N/A"
    mom_str = f"{mom:+.3%}" if mom is not None else "N/A"
    print(f"{name_cn}({series_id}) {month}: 值={value}  同比={yoy_str}  环比={mom_str}")
    return {"value": value, "yoy": yoy, "mom": mom}


"""=================DAO层====================="""

def save_to_sqlite(df: pd.DataFrame, series_id: str, country: str = "US"):
    """将FRED数据存入 macro_index 表

    Args:
        df: FRED下载的DataFrame（含 observation_date 和 series_id 列）
        series_id: FRED系列ID
        country: 国家代码，默认 US
    """
    # 查找系列元信息
    name_en, name_cn, freq = FRED_SERIES.get(series_id, (series_id, series_id, "M"))

    conn = sqlite3.connect(_get_db_path())
    cursor = conn.cursor()

    # 确保存在唯一约束，否则 ON CONFLICT 会报错
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_macro_unique
        ON macro_index(country, indicator_code, observation_date)
    """)

    sql = """
    INSERT INTO macro_index (
        country, indicator_code, indicator_name,
        indicator_name_cn, frequency, observation_date, value
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(country, indicator_code, observation_date)
    DO UPDATE SET
        value = excluded.value,
        indicator_name = excluded.indicator_name,
        indicator_name_cn = excluded.indicator_name_cn,
        frequency = excluded.frequency
    """

    skipped = 0
    for _, row in df.iterrows():
        val = row[series_id]
        obs_date = row["observation_date"]
        if pd.isna(val) or pd.isna(obs_date):
            skipped += 1
            continue
        cursor.execute(sql, (
            country,
            series_id,
            name_en,
            name_cn,
            freq,
            obs_date.strftime("%Y-%m-%d"),
            float(val)
        ))

    conn.commit()
    conn.close()
    print(f"已保存 {len(df) - skipped} 条 {name_cn}({series_id}) 数据" +
          (f"，跳过 {skipped} 条空值" if skipped else ""))


def save_yoy_growth(month: str, series_id: str, country: str = "US") -> float | None:
    """计算并保存同比增长（YoY）到 macro_index.yoy_growth

    Args:
        month: 月份，格式 "YYYY-MM"
        series_id: FRED系列ID
        country: 国家代码，默认 US

    Returns:
        保存的同比增长率，数据不足时返回 None
    """
    growth = calc_yoy_growth(month, series_id, country)
    if growth is None:
        print(f"数据不足，无法计算 {series_id} {month} 同比增长")
        return None

    conn = sqlite3.connect(_get_db_path())
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE macro_index
        SET yoy_growth = ?
        WHERE country = ? AND indicator_code = ?
          AND strftime('%Y-%m', observation_date) = ?
    """, (growth, country, series_id, month))
    conn.commit()
    conn.close()
    print(f"已保存 {series_id} {month} 同比增长: {growth:+.4%}")
    return growth


def save_mom_growth(month: str, series_id: str, country: str = "US") -> float | None:
    """计算并保存环比增长（MoM）到 macro_index.mom_growth

    Args:
        month: 月份，格式 "YYYY-MM"
        series_id: FRED系列ID
        country: 国家代码，默认 US

    Returns:
        保存的环比增长率，数据不足时返回 None
    """
    growth = calc_mom_growth(month, series_id, country)
    if growth is None:
        print(f"数据不足，无法计算 {series_id} {month} 环比增长")
        return None

    conn = sqlite3.connect(_get_db_path())
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE macro_index
        SET mom_growth = ?
        WHERE country = ? AND indicator_code = ?
          AND strftime('%Y-%m', observation_date) = ?
    """, (growth, country, series_id, month))
    conn.commit()
    conn.close()
    print(f"已保存 {series_id} {month} 环比增长: {growth:+.4%}")
    return growth


def update_all_growth(series_id: str, country: str = "US"):
    """批量计算并保存指定指标所有月份的同比/环比增长

    遍历 macro_index 表中该指标的所有月份，
    逐月计算 yoy_growth 和 mom_growth 并写入对应字段。

    Args:
        series_id: FRED系列ID
        country: 国家代码，默认 US
    """
    conn = sqlite3.connect(_get_db_path())
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT strftime('%Y-%m', observation_date) AS month
        FROM macro_index
        WHERE country = ? AND indicator_code = ?
          AND value IS NOT NULL
        ORDER BY month
    """, (country, series_id))
    months = [row[0] for row in cursor.fetchall()]
    conn.close()

    yoy_ok = mom_ok = 0
    for month in months:
        if save_yoy_growth(month, series_id, country) is not None:
            yoy_ok += 1
        if save_mom_growth(month, series_id, country) is not None:
            mom_ok += 1

    print(f"\n{series_id} 批量完成：同比增长更新 {yoy_ok} 条，环比增长更新 {mom_ok} 条，共 {len(months)} 个月")


"""
宏观经济数据主入口
循环获取所有 FRED 系列数据并存入数据库，可选自动计算同比/环比增长
"""
def fetch_and_save_all(calc_growth: bool = True, country: str = "US"):
    """获取 FRED_SERIES 中所有指标数据并存入 macro_index 表

    Args:
        calc_growth: True 时在保存后自动计算并写入同比/环比增长
        country: 国家代码，默认 US
    """
    total_series = len(FRED_SERIES)
    print(f"开始获取 {total_series} 个 FRED 数据系列...\n{'=' * 50}")

    for i, series_id in enumerate(FRED_SERIES, 1):
        name_cn = FRED_SERIES[series_id][1]
        print(f"\n[{i}/{total_series}] {name_cn} ({series_id})")
        try:
            df = get_fred(series_id)
            save_to_sqlite(df, series_id=series_id, country=country)
            if calc_growth:
                update_all_growth(series_id, country=country)
            time.sleep(1)  # 礼貌性间隔，避免请求过快
        except Exception as e:
            print(f"[!] 获取 {series_id} 失败: {e}")

    print(f"\n{'=' * 50}\n全部完成！共处理 {total_series} 个系列。")

    # 打印各系列最新数据概览
    print("\n各系列最新值概览（环比/同比）：")
    print("-" * 60)
    today = datetime.date.today()
    month = today.strftime("%Y-%m")
    for series_id, (_, name_cn, _) in FRED_SERIES.items():
        yoy = calc_yoy_growth(month, series_id, country)
        mom = calc_mom_growth(month, series_id, country)
        yoy_str = f"{yoy:+.3%}" if yoy is not None else "N/A"
        mom_str = f"{mom:+.3%}" if mom is not None else "N/A"
        print(f"{name_cn:<24} 同比 {yoy_str:>10}  环比 {mom_str:>10}")





if __name__ == '__main__':
    series_id = "CPIAUCSL"
    # df = get_fred(series_id)

    # save_to_sqlite(df, series_id=series_id, country="US")

    # 如需获取其他指标，取消注释以下行：
    # for sid in ("UNRATE", "FEDFUNDS"):
    #     df = get_fred(sid)
    #     save_to_sqlite(df, series_id=sid, country="US")

    # res = calc_yoy_growth("2026-05", series_id, country="US")
    # print(res)
    # update_all_growth(series_id, country="US")

    # fetch_and_save_all(calc_growth=True)

    query_series(series_id)