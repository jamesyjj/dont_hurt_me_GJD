import akshare as ak

def get_qd2_index():
    qdii_e_index_jsl_df = ak.qdii_e_index_jsl()
    print(qdii_e_index_jsl_df)

if __name__ == '__main__':
    get_qd2_index()