import requests

from src.index.fetcher_index import get_index_kline
import akshare as ak

if __name__ == '__main__':
    # df = get_index_kline("1.000300", 10)
    # print(df)

    print(requests.__version__)

    print(
        requests.get(
            "https://www.baidu.com"
        ).status_code
    )

    print(
        requests.get(
            "https://www.eastmoney.com"
        )
    )



    df = ak.stock_zh_index_daily("sh000300")
    print(df.tail(10))

