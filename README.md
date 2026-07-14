# Stock Viewer

A Streamlit stock dashboard for **US equities**. Browse macro market data, quotes, charts, news, and manage a local portfolio.

## Features

- **Macro market**: Major US indices (S&P 500, Nasdaq, Dow, Russell 2000) and sector ETFs
- **Stock overview**: Live price, change, volume, market cap, 52-week range, and more
- **Price charts**: Line or candlestick charts with volume, from 1 week to 5 years
- **Ownership & trend analysis**: Institutional holdings and technical trend signals
- **Recent news**: Headlines from Yahoo Finance
- **Top stocks**: Sidebar ranking of liquid US large caps
- **Favorites**: Star stocks for quick access
- **Portfolio**: Track cost basis and unrealized P&L locally
- **Languages**: English (default), Simplified Chinese, Traditional Chinese

## Install

```bash
git clone https://github.com/moking/stock-viewer.git
cd stock-viewer
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

Your browser opens at `http://localhost:8501`.

## Symbol format

This app supports **US tickers only**, for example:

| Example | Description |
|---------|-------------|
| `AAPL` | Apple |
| `TSLA` | Tesla |
| `NVDA` | NVIDIA |
| `BRK-B` | Berkshire Hathaway Class B |

Data source: [Yahoo Finance](https://finance.yahoo.com/) via the `yfinance` library. Quotes may be delayed and are for reference only.

## Local data

- Portfolio: `data/portfolio.json`
- Favorites: `data/favorites.json`

Both files stay on your machine and are not uploaded anywhere.

---

# 股票信息查看器

基于 Streamlit 的 **美股** 行情查看工具，支持宏观市场、个股行情、图表、新闻与本地持仓管理。

## 功能

- **宏观市场**：标普 500、纳斯达克、道琼斯、罗素 2000 等美股指数及板块 ETF
- **行情概览**：实时价格、涨跌幅、成交量、市值、52 周高低等
- **价格走势**：折线图或 K 线图 + 成交量，可选 1 周至 5 年区间
- **持仓分析 & 趋势分析**：机构持仓与技术面信号
- **最近消息**：来自 Yahoo Finance 的新闻
- **热门股票**：侧边栏展示流动性较好的美股 Top 15
- **收藏列表**：星标收藏，快速切换
- **我的持仓**：记录成本，自动计算浮动盈亏
- **多语言**：英文（默认）、简体中文、繁体中文

## 安装

```bash
git clone https://github.com/moking/stock-viewer.git
cd stock-viewer
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

本应用**仅支持美股代码**，例如：

| 示例 | 说明 |
|------|------|
| `AAPL` | 苹果 |
| `TSLA` | 特斯拉 |
| `NVDA` | 英伟达 |
| `BRK-B` | 伯克希尔 B 股 |

数据来源：[Yahoo Finance](https://finance.yahoo.com/)（通过 `yfinance` 库）。行情可能存在延迟，仅供参考。

## 本地数据

- 持仓记录：`data/portfolio.json`
- 收藏列表：`data/favorites.json`

以上文件仅保存在本地，不会上传。
