# ETF份额数据分析工具

上海证券交易所ETF份额历史数据采集与分析工具。

## 项目结构

```
etf-project/
├── src/etf/              # 核心包
│   ├── __init__.py
│   ├── database.py       # 数据库操作
│   ├── fetcher.py        # 数据拉取
│   ├── queries.py         # 数据查询
│   └── cli.py            # CLI入口
├── src/macro_economy/    # 宏观经济数据
│   ├── __init__.py
│   └── usa.py            # FRED数据获取（CPI/失业率/利率）
├── scripts/              # 独立工具
│   ├── etf_trend.py      # 趋势图生成
│   └── etf_compare.py    # ETF对比
├── data/                 # 数据目录
│   └── etf_data.db       # SQLite数据库
├── skills/               # Claude Code技能
│   └── etf/
└── tests/                # 测试目录
```

## 常用命令

```bash
# 采集数据
python -m src.etf.cli fetch 5

# 查看证券ETF份额变化（支持排序+近N日跨度）
python -m src.etf.cli securities change 5

# 查看某行业ETF份额变化（支持排序+近N日跨度）
python -m src.etf.cli industry 医药 change 5

# 份额增加前10
python -m src.etf.cli top 10

# 份额增幅前10
python -m src.etf.cli top_pct 10

# 查看某ETF趋势
python -m src.etf.cli trend 512880

# 查看ETF份额-价格详细走势
python -m src.etf.cli detail 5181 30

# 检查数据完整性
python -m src.etf.cli check [天数]    # 检查数据完整性（默认20天）

# 生成趋势图HTML
python scripts/etf_trend.py 512880 500

# 生成对比图
python scripts/etf_compare.py 510300 500

# 汇金系买卖趋势分析（自定义日期范围）
python scripts/huijin_trade.py 2025-12-31 2026-06-09

# 汇金系持仓ETF份额/价格走势（控制台Top10 + CSV全量）
python -m src.etf.cli huijin 10

# 查询宏观数据系列（值和同比/环比增长）
python -m src.etf.cli macro UNRATE              # 查询失业率当前月
python -m src.etf.cli macro CPIAUCSL 2026-05    # 查询CPI指定月份
```

## 数据更新时机

**重要**: A股清算后数据才更新，约晚上8-10点后能查到当天数据。

## 数据库字段

### etf_info / etf_daily_share / etf_top_holders

- `sec_name` - ETF简称（如"证券ETF"）
- `full_name` - ETF全称（含公司，如"证券ETF国泰"）
- `tot_vol` - 总份额（单位：万份）

### macro_index - 宏观经济指标

- `indicator_code` - 指标代码（如 CPIAUCSL / UNRATE / FEDFUNDS）
- `indicator_name_cn` - 指标中文名
- `observation_date` - 数据日期
- `value` - 数值
- `yoy_growth` - 同比增长（YoY，%）
- `mom_growth` - 环比增长（MoM，%）
- 唯一约束：(country, indicator_code, observation_date)
- 建表DDL：`data/sqlite3.sql`
