import sqlite3
import os

import akshare as ak
import pandas as pd

from pathlib import Path


def _get_db_path() -> str:
    """获取数据库路径（相对此脚本位置：项目根/data/etf_data.db）"""
    return os.path.join(Path(__file__).parent.parent.parent, 'data', 'etf_data.db')


# FRED 系列ID → (英文名, 中文名, 频率)
FRED_SERIES = {
    "CPIAUCSL":  ("CPI All Items",             "消费者物价指数", "M"),
    "UNRATE":    ("Unemployment Rate",          "失业率",         "M"),
    "FEDFUNDS":  ("Federal Funds Effective Rate", "联邦基金利率",  "M"),
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


if __name__ == '__main__':
    series_id = "CPIAUCSL"
    df = get_fred(series_id)

    save_to_sqlite(df, series_id=series_id, country="US")

    # 如需获取其他指标，取消注释以下行：
    # for sid in ("UNRATE", "FEDFUNDS"):
    #     df = get_fred(sid)
    #     save_to_sqlite(df, series_id=sid, country="US")