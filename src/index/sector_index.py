import akshare as ak


def get_sector_index():

    stock_zh_index_daily_df = ak.stock_zh_index_daily(symbol="sz399552")
    print(stock_zh_index_daily_df)

    stock_zh_index_daily_tx_df = ak.stock_zh_index_daily_tx(symbol="sh000001", start_date="20260101", end_date="20260429")
    print(stock_zh_index_daily_tx_df)