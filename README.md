# ETF份额数据分析工具

上海证券交易所ETF份额历史数据采集与分析工具。

## 行为约束

**强制规则1**: 当用户下达的命令存在歧义或不明确时，必须先向用户询问澄清，待用户明确答复后再执行操作。禁止自行猜测用户意图并直接操作。

**强制规则2**: 所有数据分析命令（查询、排行、趋势、图表等）只允许进行数据库**读操作**，禁止执行任何 INSERT、UPDATE、DELETE 等写操作。如需更新数据，必须明确调用 `fetch` 命令或经用户确认后方可执行。

## 功能特性

- 自动采集ETF每日份额数据（支持全量800+只ETF）
- SQLite本地数据库存储
- 智能分页处理
- 节假日自动跳过
- 并发加速采集
- 份额趋势HTML可视化
- 支持简称/全称切换展示

## 项目结构

```
etf-project/
├── src/etf/              # ETF核心包
│   ├── __init__.py
│   ├── database.py       # 数据库操作
│   ├── fetcher.py        # 数据拉取
│   ├── queries.py        # 数据查询
│   └── cli.py            # 命令行入口
├── src/index/            # 指数数据
│   ├── __init__.py
│   ├── fetcher_index.py  # 指数K线拉取（东方财富）
│   ├── sector_index.py   # 行业板块指数（akshare）
│   └── foreign_index/    # 海外指数
│       ├── __init__.py
│       ├── american_index.py  # 美股三大指数
│       └── etf_qd2.py         # QDII跨境指数
├── src/macro_economy/    # 宏观经济数据
│   ├── __init__.py
│   └── usa.py            # FRED数据获取
├── scripts/              # 独立脚本
│   ├── etf_trend.py      # 趋势图生成
│   └── etf_compare.py    # ETF对比工具
├── data/                 # 数据目录（含 etf_data.db、sqlite3.sql 建表DDL）
├── tests/                # 测试目录
├── docs/                 # 文档目录
├── .claude/skills/etf/   # Claude Code技能
├── README.md
├── requirements.txt
└── pyproject.toml
```

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 命令行工具（推荐）

```bash
# 采集数据
python -m src.etf.cli fetch 5

# 查询份额上升的ETF
python -m src.etf.cli query 126

# 查看证券ETF份额变化（支持排序 + 近N日跨度）
python -m src.etf.cli securities change 5

# 查看某行业ETF份额变化（支持排序 + 近N日跨度）
python -m src.etf.cli industry 保险 change 300

# 份额增加前10名
python -m src.etf.cli top 20

# 份额增幅前10名
python -m src.etf.cli top_pct 10

# 份额减少前10名
python -m src.etf.cli bottom 20

# 份额降幅前10名
python -m src.etf.cli bottom_pct 10

# 查看某ETF趋势
python -m src.etf.cli trend 513180

# 查看ETF份额-价格详细走势（含日变化/日收益/排名）
python -m src.etf.cli detail 510720 330

# 检查数据完整性
python -m src.etf.cli check [天数]    # 检查数据完整性（默认20天）

# 更新ETF完整名称
python -m src.etf.cli update_names

# 采集所有ETF十大持有人（从新浪财经）
python -m src.etf.cli holders      

# 查看某ETF十大持有人        
python -m src.etf.cli holders 510720   

# 按持有人类型查询（如：保险/信托/私募） 
python -m src.etf.cli holders_type 汇金    

# 汇金系持仓ETF份额/价格走势（控制台Top10+CSV全量）
python -m src.etf.cli huijin 20

```

### 独立脚本

```bash
# 生成ETF趋势HTML图
python scripts/etf_trend.py 513180 500

# ETF价格-份额双折线图
python scripts/etf_price_volume.py 515050 2025-05-01 2026-06-03

# 对比两只ETF
python scripts/etf_compare.py 512880 512070

# 查询某ETF的汇金系持仓及估算买卖情况
python scripts/huijin_etf.py 510330

# 汇金系ETF买卖趋势分析（基准日2025.12.31，固定）
python scripts/huijin_analysis.py

# 汇金系买卖趋势分析（自定义起始日/结束日）
python scripts/huijin_trade.py 2025-12-31 2026-06-09
python scripts/huijin_trade.py 2026-06-04 2026-06-10


```

### 宏观数据（FRED）

通过 `src/macro_economy/usa.py` 从 FRED 获取宏观数据并存入 `macro_index` 表，
数据结构见下方数据库表结构；建表DDL 见 `data/sqlite3.sql`。

```bash
# 查询宏观数据系列（值和同比/环比增长，默认当前月）
python -m src.etf.cli macro CPIAUCSL             # 查询CPI
python -m src.etf.cli macro UNRATE 2026-05        # 查询失业率指定月份

# 可用指标：
#   CPIAUCSL   - 消费者物价指数（CPI，月频）
#   UNRATE     - 失业率（月频）
#   FEDFUNDS   - 联邦基金利率（月频）
#   CPILFESL   - 核心CPI
#   PPIACO     - 工业品出厂价格指数PPI
#   PCEPI      - 个人消费支出价格指数PCE
#   PCEPILFE   - 核心PCE
#   DGS10      - 美国10年国债收益率
```

### usa.py 方法参考

**数据抓取（主动获取外部数据源）**

| 方法 | 说明 |
|------|------|
| `get_fred(series_id: str) -> pd.DataFrame` | 从FRED下载CSV原始数据，返回含 observation_date 和 series_id 列的DataFrame |
| `fetch_and_save_all(calc_growth=True, country="US")` | **主入口**：一键拉取 FRED_SERIES 中全部指标数据并入库，可选自动计算同比/环比 |

**辅助函数（计算/存储/查询）**

| 方法 | 说明 |
|------|------|
| `cal_yoy_growth(month, series_id, country) -> float \| None` | 计算同比增长率（YoY），返回%值，保留5位小数 |
| `cal_mom_growth(month, series_id, country) -> float \| None` | 计算环比增长率（MoM），返回%值，保留5位小数 |
| `save_to_sqlite(df, series_id, country)` | FRED原始数据写入 macro_index 表（UPSERT，重复时更新value） |
| `save_yoy_growth(month, series_id, country) -> float \| None` | 计算并保存同比增长率到 DB（调用 `cal_yoy_growth`） |
| `save_mom_growth(month, series_id, country) -> float \| None` | 计算并保存环比增长率到 DB（调用 `cal_mom_growth`） |
| `update_all_growth(series_id, country)` | 批量更新某指标全部月份的同比/环比 |
| `query_series(series_id, month, country) -> dict` | 查询某月值和增长率，返回 `{"value", "yoy", "mom"}` |

### sector_index / foreign_index 方法参考

**sector_index.py（A股指数）**

| 方法 | 说明 |
|------|------|
| `fetch_index_info_cn() -> int` | 从 akshare 获取全量A股指数列表，写入 `index_info` 表 |
| `fetch_sector_index(index_code: str) -> int` | 抓取A股指数历史日线（akshare），写入 `index_daily`。`change_percent` 由收盘价计算（%值，5位小数），`amplitude`/`turnover_rate` 来自 akshare（%值，2位小数） |

**foreign_index/ — 海外指数**

| 方法 | 文件 | 说明 |
|------|------|------|
| `fetch_index_info_global() -> int` | global_index.py | 从 akshare 获取全球指数列表，写入 `index_info` |
| `fetch_index_daily_global(index_code) -> int` | global_index.py | 抓取全球指数历史日线（新浪），写入 `index_daily` |
| `fetch_usa_index(symbol) -> int` | usa_index.py | 抓取美股指数历史日线（新浪），写入 `index_daily` + 同步 `index_info` |
| `fetch_all_usa_indices()` | usa_index.py | 批量抓取美股四大指数（.INX/.DJI/.NDX/.IXIC） |
| `fetch_index_daily_hk(symbol) -> int` | hk_index.py | 抓取港股指数历史日线（新浪），写入 `index_daily` |
| `fetch_index_daily_hk_now() -> int` | hk_index.py | 获取港股指数实时行情（新浪 spot），写入当天 `index_daily` |
| `fetch_index_daily_hk_now_em() -> int` | hk_index.py | 获取港股指数实时行情（东方财富 spot），写入当天 `index_daily` |
| `fetch_all_hk_indices()` | hk_index.py | 批量抓取所有已知港股指数日线 |

> `index_daily` 中 `change_percent` 统一为 %值（保留5位小数），`amplitude`/`turnover_rate` 为 %值（保留2位小数）。

## 数据库表结构

### etf_info - ETF基本信息
| 字段 | 类型 | 说明 |
|------|------|------|
| sec_code | TEXT | ETF代码 (PK) |
| sec_name | TEXT | ETF简称 |
| full_name | TEXT | ETF全称（含公司） |
| etf_type | TEXT | ETF类型 |

### etf_daily_share - 每日份额
| 字段        | 类型    | 说明           |
| ----------- | ------- | -------------- |
| sec_code    | TEXT    | ETF代码 (PK)   |
| stat_date   | TEXT    | 日期 (PK)      |
| tot_vol     | REAL    | 总份额（万份） |
| num         | INTEGER | 排名           |
| close_price | REAL    | 收盘价         |
| market      | TEXT    | 交易所         |

### etf_top_holders - ETF十大持有人
| 字段        | 类型    | 说明               |
| ----------- | ------- | ------------------ |
| sec_code    | TEXT    | ETF代码            |
| stat_date   | TEXT    | 报告期（如2025-12-31） |
| rank        | INTEGER | 排名（1-10）      |
| holder_name | TEXT    | 持有人名称         |
| holder_share| REAL    | 持有份额（份）     |
| holder_pct  | REAL    | 占总份额比（%）    |
| create_at | TEXT | 日期 |

*数据来源：新浪财经基金档案页，每年4-5月更新年报，8-9月更新半年报。实时性约滞后4-5个月。*

### macro_index - 宏观经济指标

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 自增主键 |
| country | TEXT | 国家代码（US / CN / EU）|
| indicator_code | TEXT | 指标代码（如 CPIAUCSL / UNRATE / FEDFUNDS）|
| indicator_name | TEXT | 指标英文名 |
| indicator_name_cn | TEXT | 指标中文名 |
| frequency | TEXT | 频率（D=日 / W=周 / M=月 / Q=季），默认 'M' |
| observation_date | DATE | 数据日期（核心维度）|
| value | REAL | 数值 |
| yoy_growth | REAL | 同比增长（YoY，%）|
| mom_growth | REAL | 环比增长（MoM，%）|
| source | TEXT | 数据来源，默认 'FRED' |
| create_time | TEXT | 创建时间 |

> 唯一约束：(country, indicator_code, observation_date)，重复时更新全部字段。建表DDL：`data/sqlite3.sql`

### index_info - 指数基本信息
| 字段 | 类型 | 说明 |
|------|------|------|
| index_code | TEXT | 指数代码 (PK)，如 000300、399006 |
| index_name | TEXT | 指数名称 |
| market | TEXT | 交易所（SH / SZ / HK / US） |
| publisher | TEXT | 发布机构（如 中证指数有限公司） |
| category | TEXT | 分类（宽基 / 行业 / 主题 / 策略 等） |
| currency | TEXT | 币种，默认 'CNY' |
| create_time | TEXT | 创建时间 |
| update_time | TEXT | 更新时间 |

### index_daily - 指数日线数据
| 字段 | 类型 | 说明                                   |
|------|------|--------------------------------------|
| index_code | TEXT | 指数代码（逻辑外键 → index_info.index_code）   |
| trade_date | INTEGER | 交易日（YYYYMMDD）                        |
| open | REAL | 开盘价                                  |
| high | REAL | 最高价                                  |
| low | REAL | 最低价                                  |
| close | REAL | 收盘价                                  |
| volume | REAL | 成交量                                  |
| amount | REAL | 成交额                                  |
| amplitude | REAL | 振幅（%，保留2位小数）                                |
| change_percent | REAL | 涨跌幅（%，保留5位小数）                               |
| change_amount | REAL | 涨跌额                                  |
| turnover_rate | REAL | 换手率（%，保留2位小数；指数通常为空）                         |
| source | TEXT | 数据来源（akshare / eastmoney / manual …） |
| create_time | TEXT | 创建时间                                 |
| update_time | TEXT | 更新时间                                 |

> 主键：(index_code, trade_date)。另有 trade_date、source 索引。

### update_log - 数据更新日志
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 自增主键 |
| module | TEXT | 模块名（index / macro / etf / stock …） |
| target_code | TEXT | 目标代码（如 000300 / CPIAUCSL） |
| update_type | TEXT | 更新类型（full / increment / manual） |
| start_time | TEXT | 开始时间 |
| end_time | TEXT | 结束时间 |
| last_trade_date | INTEGER | 更新到的数据日期（YYYYMMDD） |
| status | INTEGER | 状态（1=成功 0=失败） |
| message | TEXT | 错误信息或备注 |
| create_time | TEXT | 创建时间 |

> 另有 module、target_code、create_time、status 索引。

## 数据来源

上海证券交易所 (SSE) 官方接口
- 份额接口: `commonQuery.do?sqlId=COMMON_SSE_ZQPZ_ETFZL_XXPL_ETFGM_SEARCH_L`
- 全称接口: `security/stock/queryExpandName.do`
- 每日更新频率: 收盘后清算完成后（约20:00-22:00）
