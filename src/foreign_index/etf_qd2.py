import akshare as ak

def get_qd2_index():
    cookie = "kbzw__Session=23fn5mv6f8q2b9rrsg9d94e8k0; Hm_lvt_164fe01b1433a19b507595a43bf58262=1780894236; HMACCOUNT=D73720A266AD4DE8; kbz_newcookie=1; kbzw__user_login=7Obd08_P1ebax9aXwZKumq6wqKuTo4KvpuXK7N_u0ejF1dSe3Jihw9ndqJ_bpKiS2MSop9WxmtHCq9umzK2h2sSqlqiYrqXW2cXS1qCbrJ2smayXmLKgubXOvp-qrKGppLCWqpanmK6ltrG_0aTC2PPV487XkKylo5iJx8ri3eTg7IzFtpaSp6Wjs4HHyuKvqaSZ5K2Wn4G45-PkxsfG1sTe3aihqpmklK2Xm8OpxK7ApZXV4tfcgr3G2uLioYGzyebo4s6onauapJGlp6GogcPC2trn0qihqpmklK0.; Hm_lpvt_164fe01b1433a19b507595a43bf58262=1780900685"
    qdii_e_index_jsl_df = ak.qdii_e_index_jsl(cookie)
    print(qdii_e_index_jsl_df)
    ak.stock_zh_index_daily_em()

if __name__ == '__main__':
    get_qd2_index()