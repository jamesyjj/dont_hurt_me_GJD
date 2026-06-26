import akshare as ak

def get_american_index():
    index_us_stock_sina_df = ak.index_us_stock_sina(symbol=".INX")
    print(index_us_stock_sina_df)
    index_us_stock_sina_df2 = ak.index_us_stock_sina(symbol=".DJI")
    index_us_stock_sina_df2 = ak.index_us_stock_sina(symbol=".INX")
    index_us_stock_sina_df2 = ak.index_us_stock_sina(symbol=".NDX")



if __name__ == '__main__':
    get_american_index()