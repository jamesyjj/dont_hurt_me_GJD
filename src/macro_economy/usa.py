import akshare as ak

def get_gdp():
    macro_usa_gdp_monthly_df = ak.macro_usa_gdp_monthly()
    print(macro_usa_gdp_monthly_df)



if __name__ == '__main__':
    get_gdp()