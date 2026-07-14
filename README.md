# 股票信息查看器

带 UI 的股票行情查看工具，支持实时价格、成交量、历史 K 线图和本地持仓管理。

## 功能

- **行情概览**：当前价格、涨跌幅、成交量、市值、52 周高低等
- **价格走势**：K 线图 + 成交量柱状图，可选 1 周至 5 年区间
- **我的持仓**：记录持仓成本，自动计算浮动盈亏

## 安装

```bash
cd stock
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 运行

```bash
streamlit run app.py
```

浏览器会自动打开 `http://localhost:8501`。

## 股票代码格式

| 市场 | 示例 | 说明 |
|------|------|------|
| 美股 | `AAPL`, `TSLA` | 直接使用 ticker |
| A股（沪） | `600519.SS` | 上交所后缀 `.SS` |
| A股（深） | `000001.SZ` | 深交所后缀 `.SZ` |
| 港股 | `0700.HK` | 港交所后缀 `.HK` |

数据来源：[Yahoo Finance](https://finance.yahoo.com/)（通过 `yfinance` 库）。

## 持仓数据

持仓记录保存在 `data/portfolio.json`，仅存储在本地，不会上传。
