import requests
import pandas as pd


def get_index_kline(secid: str, limit: int = 10):
    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"

    params = {
        "secid": secid,
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58",
        "klt": "101",
        "fqt": "0",
        "lmt": str(limit)
    }

    resp = requests.get(
        url,
        params=params,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    klines = resp.json()["data"]["klines"]

    return pd.DataFrame([
        {
            "date": k[0],
            "open": k[1],
            "close": k[2],
            "high": k[3],
            "low": k[4],
            "volume": k[5],
            "amount": k[6],
        }
        for k in map(lambda x: x.split(","), klines)
    ])
