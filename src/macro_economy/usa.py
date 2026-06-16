import akshare as ak
import pandas as pd

def get_gdp():
    macro_usa_gdp_monthly_df = ak.macro_usa_gdp_monthly()
    print(macro_usa_gdp_monthly_df)

# 获取fred数据
# req: 所需数据全称
# 全程列表如下：CPIAUCSL，UNRATE，FEDFUNDS（待补充）

def get_fred(series_id):
    url = (
        "https://fred.stlouisfed.org/graph/fredgraph.csv"
        f"?id={series_id}"
    )
    df = pd.read_csv(url)
    print(df.tail())
    print("总条数:", len(df))
    print("最早日期:", df.iloc[0])
    print("最新日期:", df.iloc[-1])



def get_cpi_from_fred():
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCSL"
    df = pd.read_csv(url)
    print(df.tail())
    print("总条数:", len(df))
    print("最早日期:", df.iloc[0])
    print("最新日期:", df.iloc[-1])



if __name__ == '__main__':
    # get_gdp()
    # get_cpi_from_fred()

    cpi = get_fred("CPIAUCSL")
    unrate = get_fred("UNRATE")
    fedfunds = get_fred("FEDFUNDS")