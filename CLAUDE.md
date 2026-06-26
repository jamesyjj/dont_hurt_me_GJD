# ETF份额数据分析工具

上海证券交易所ETF份额历史数据采集与分析工具。

## 行为约束

**强制规则1**: 当用户下达的命令存在歧义或不明确时，必须先向用户询问澄清，待用户明确答复后再执行操作。禁止自行猜测用户意图并直接操作。

**强制规则2**: 所有数据分析命令（查询、排行、趋势、图表等）只允许进行数据库**读操作**，禁止执行任何 INSERT、UPDATE、DELETE 等写操作。如需更新数据，必须明确调用 `fetch` 命令或经用户确认后方可执行。

## 项目结构

```
etf-project/
├── src/etf/              # 核心包
│   ├── __init__.py
│   ├── database.py       # 数据库操作
│   ├── fetcher.py        # 数据拉取
│   ├── queries.py         # 数据查询
│   └── cli.py            # CLI入口
├── src/index/            # 指数数据
│   ├── __init__.py
│   ├── fetcher_index.py  # 指数K线拉取
│   ├── sector_index.py   # 行业板块指数
│   └── foreign_index/    # 海外指数
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

### index_info - 指数基本信息

- `index_code` - 指数代码 (PK)，如 000300、399006
- `index_name` - 指数名称
- `market` - 交易所（SH / SZ / HK / US）
- `publisher` - 发布机构
- `category` - 分类（宽基 / 行业 / 主题 / 策略）

### index_daily - 指数日线数据

- `index_code` - 指数代码（逻辑外键 → index_info.index_code）
- `trade_date` - 交易日（YYYYMMDD）
- `open` / `high` / `low` / `close` - OHLC价格
- `volume` - 成交量
- `amount` - 成交额
- `amplitude` - 振幅（%）
- `change_percent` - 涨跌幅（%）
- `change_amount` - 涨跌额
- `source` - 数据来源（akshare / eastmoney / manual）
- 主键：(index_code, trade_date)

### update_log - 数据更新日志

- `module` - 模块名（index / macro / etf / stock）
- `target_code` - 目标代码（如 000300 / CPIAUCSL）
- `update_type` - 更新类型（full / increment / manual）
- `start_time` / `end_time` - 起止时间
- `last_trade_date` - 更新到的数据日期（YYYYMMDD）
- `status` - 状态（1=成功 0=失败）
- `message` - 错误信息或备注
