---
name: etf
description: ETF份额数据分析工具 - 查询证券ETF份额变化、份额增减排行、ETF趋势等
user-invocable: true
---

# ETF份额数据分析工具

基于上海证券交易所数据的ETF份额分析工具。

## 文档同步约定

当用户说「更新skill」「更新readme」「同步文档」等指令时，必须同步更新以下 **4个文件**：

| 文件 | 说明 |
|------|------|
| `.claude/skills/etf/SKILL.md` | Claude Code 技能定义（主） |
| `skills/etf/SKILL.md` | 项目内技能副本（与上保持完全一致） |
| `README.md` | 项目说明文档 |
| `CLAUDE.md` | 项目级 Claude 指令 |

**同步规则**：
- 新增 CLI 命令或脚本 → 4个文件都要加
- SKILL.md 两份文件内容必须完全一致，用 `cp` 同步
- README.md 和 CLAUDE.md 的命令列表保持对齐

## 数据更新时机

**重要**: A股清算后数据才更新，约晚上8-10点后能查到当天数据。白天查不到当天数据是正常的。

## 常用命令

### 1. 更新数据
```bash
python -m src.etf.cli fetch 5
```

### 2. 证券ETF份额变化
```bash
python -m src.etf.cli securities              # 按份额从高到低（近1日）
python -m src.etf.cli securities change 5     # 按变化排序，近5日跨度
python -m src.etf.cli securities pct 10       # 按增幅排序，近10日跨度
```

### 3. 行业ETF查询
```bash
python -m src.etf.cli industry 医药              # 医药行业（按份额，近1日）
python -m src.etf.cli industry 医药 change 5     # 按变化排序，近5日跨度
python -m src.etf.cli industry 银行 pct 10       # 按增幅排序，近10日跨度
```

### 4. 份额增加/增幅排行
```bash
python -m src.etf.cli top 10      # 份额增加前10
python -m src.etf.cli top_pct 10 # 份额增幅前10
```

### 5. 特定ETF查询
```bash
python -m src.etf.cli trend 510300   # 沪深300ETF（份额趋势）
python -m src.etf.cli trend 512880   # 证券ETF

# 份额+价格+日变化+日收益+排名 详细走势
python -m src.etf.cli detail 513180 30    # 恒生科技ETF，近30天
python -m src.etf.cli detail 512880       # 默认30天
```

### 6. 检查数据完整性
```bash
python -m src.etf.cli check
```

### 7. 十大持有人数据
```bash
python -m src.etf.cli holders              # 采集所有ETF十大持有人（从新浪财经）
python -m src.etf.cli holders 512880       # 查看某ETF十大持有人
python -m src.etf.cli holders_type 保险    # 按持有人类型查询（如：保险/信托/私募）
```

### 8. 汇金系持仓ETF走势
```bash
# 控制台显示Top10汇金系持仓ETF近N天的份额/价格变化，全量导出CSV
python -m src.etf.cli huijin 10
```

### 9. 生成趋势图HTML
```bash
python scripts/etf_trend.py 512880 500
```

### 10. 生成ETF对比图
```bash
python scripts/etf_compare.py 510300 500
```

### 11. 汇金系买卖趋势分析
```bash
# 固定基准日2025-12-31
python scripts/huijin_analysis.py

# 自定义起始日/结束日
python scripts/huijin_trade.py 2025-12-31 2026-06-09
python scripts/huijin_trade.py 2026-03-01 2026-06-09
```

### 12. 价格-份额双折线图HTML
```bash
# 指定日期范围生成Plotly双折线图
python scripts/etf_price_volume.py 513180 2026-05-01 2026-06-03
# 依赖: pip install plotly
```

## 数据库字段说明

### etf_info - ETF基本信息

| 字段      | 类型 | 说明              |
| --------- | ---- | ----------------- |
| sec_code  | TEXT | ETF代码 (PK)      |
| sec_name  | TEXT | ETF简称           |
| full_name | TEXT | ETF全称（含公司） |
| etf_type  | TEXT | ETF类型           |

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

> 数据来源：新浪财经基金档案页，每年4-5月更新年报，8-9月更新半年报。实时性约滞后4-5个月。

---

## 编码模板：新增CLI命令

当需要新增一个 `python -m src.etf.cli xxx` 命令时，遵循以下两步模板。

### 步骤1：在 `src/etf/queries.py` 添加查询函数

```python
def query_xxx(param1: str, param2: int = 30) -> List[Tuple]:
    """查询描述

    Args:
        param1: 参数1说明
        param2: 参数2说明

    Returns:
        [(col1, col2, ...), ...]  明确列出返回的列含义
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT col1, col2, ...
        FROM etf_daily_share d
        LEFT JOIN etf_info i ON d.sec_code = i.sec_code
        WHERE ...
        ORDER BY ...
        LIMIT ?
    ''', (param2,))
    rows = cursor.fetchall()
    conn.close()

    # 如果需要后处理（如计算日变化），在这里进行
    result = []
    prev_val = None
    for row in rows:
        daily_chg = (row[1] - prev_val) if prev_val else 0
        result.append((*row, daily_chg))
        prev_val = row[1]
    return result
```

**关键约定**：
- 始终用 `get_connection()` 获取连接（已配置好 `data/etf_data.db`）
- 查询字符串用三引号，保持SQL可读性
- LEFT JOIN `etf_info` 获取ETF名称
- 返回类型标注 `List[Tuple]`，列顺序固定

### 步骤2：在 `src/etf/cli.py` 添加命令

```python
# 1) 在文件顶部导入处添加函数名
from .queries import (
    ...
    query_xxx,   # ← 新增
)

# 2) 在 main() 的 help 文本中添加用法
    python -m src.etf.cli xxx [参数]       # 说明

# 3) 在 main() 中添加 elif 分支
    elif cmd == 'xxx':
        param1 = sys.argv[2] if len(sys.argv) > 2 else 'default'
        param2 = int(sys.argv[3]) if len(sys.argv) > 3 else 30
        results = query_xxx(param1, param2)
        if not results:
            print('无数据')
            return
        # 打印表格
        print(f'\n标题 ({param1}):')
        print(f"{'='*100}")
        print(f"{'列1':<10} {'列2':>14} {'列3':>8}")
        print(f"{'-'*100}")
        for row in results:
            # 对 None 值兜底: (row[1] or row[0]) 或 (row[1] or 'N/A')
            print(f'{row[0]:<10} {row[1]:>14.2f} {row[2]:>8}')
        print(f"{'='*100}")
```

**关键约定**：
- `sys.argv` 取值用 `if len(sys.argv) > n else 'default'`
- 所有格式化输出必须对 `None` 值兜底（如 `(name or code)`, `(price or 0)`）
- 使用 Python 格式化字符串，不用 `str.format()`
- 列宽固定，中文标题对齐用 `:<` `:>` 格式符
- 日期占12列 `<12`，代码占10列 `<10`，份额用 `>14,.0f`，价格用 `>8.3f`
- 日变化/日收益用 `:>+` 显示正负号

### 步骤3（可选）：同步更新文档

更新以下文件中的命令列表：
- `skills/etf/SKILL.md` 和 `.claude/skills/etf/SKILL.md` — 添加命令说明
- `CLAUDE.md` — 添加一行示例
- `README.md` — 添加一行示例

### 常见问题

| 问题 | 原因 | 修复 |
|------|------|------|
| `TypeError: NoneType.__format__` | 数据库字段为NULL | 用 `(val or fallback)` 兜底 |
| 中文输出乱码 | Windows GBK编码 | 用 `chcp 65001` 或忽略，不影响功能 |
| 格式化列对不齐 | 中文字符宽度 | 中文列宽=2字节，适当加宽 |
| CSV路径错误 `src/data/...` | `__file__` 层级不对 | 从 `src/etf/cli.py` 需 `parent × 3` 到项目根 |

### 特殊模式：宽表格透视 + CSV导出

当需要输出「日期为行、多只ETF为列」的透视表格时：

```python
# 1) 查询函数返回: [(code, name, pct, [(date, vol, price), ...]), ...]

# 2) CLI: 对齐所有日期的数据
all_dates = sorted({d for _, _, _, data in results for d, _, _ in data})
etf_map = {code: {'dmap': {d: (v, p) for d, v, p in data}, 'name': name, 'pct': pct} for code, name, pct, data in results}

# 3) 控制台: 前N只作为列，双行表头（代码行+名称(占比)行）
topN = results[:10]
COL_W = 15  # 每列宽，容纳 "2819929/4.93"
SEP_W = 12 + len(topN) * (COL_W + 1)
for d in dates:
    cells = [d]
    for code, _, _, _ in topN:
        entry = etf_map[code]['dmap'].get(d)
        cells.append(f'{entry[0]:,.0f}/{entry[1]:.3f}' if entry else '-')
    print(' '.join(f'{c:>{COL_W}}' if i > 0 else f'{c:<12}' for i, c in enumerate(cells)))

# 4) CSV: 全量导出，encoding='utf-8-sig'（Excel兼容中文）
csv_path = os.path.join(PROJECT_ROOT, 'data', 'huijin_etf_trend.csv')
with open(csv_path, 'w', encoding='utf-8-sig') as f:
    headers = ['日期'] + [f'{code}({name},{pct:.1f}%)' for code, name, pct, _ in results]
    f.write(','.join(headers) + '\n')
    for d in dates:
        row = [d] + [f'{v:,.0f}/{p:.3f}' if (entry := etf_map[code]['dmap'].get(d)) else '-'
                     for code, _, _, _ in results]
        f.write(','.join(row) + '\n')
```
