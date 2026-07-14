"""Stock viewer UI — run with: streamlit run app.py"""

from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.trend_analysis import fetch_trend_analysis  # noqa: E402
from src.format_utils import fmt_num, fmt_pct, style_numeric_dataframe  # noqa: E402
from src.holdings_analysis import fetch_ownership_analysis  # noqa: E402
from src.favorites import (  # noqa: E402
    is_favorite,
    load_favorites,
    remove_favorite,
    toggle_favorite,
    add_favorite,
)
from src.portfolio import (  # noqa: E402
    add_holding,
    compute_portfolio_summary,
    load_holdings,
    remove_holding,
    update_holding,
)
from src.stock_data import compute_period_trading_summary, fetch_history, fetch_quote, get_period_bounds, is_us_symbol, normalize_symbol  # noqa: E402
from src.macro_overview import INDEX_NAME_KEYS, fetch_macro_snapshot  # noqa: E402
from src.instrument_detail import fetch_instrument_detail  # noqa: E402
from src.stock_news import fetch_recent_news  # noqa: E402
from src.top_stocks import TOP_SORT_KEYS, fetch_top_stocks  # noqa: E402
from src.i18n import (  # noqa: E402
    CHART_KEYS,
    NAV_KEYS,
    PERIOD_KEYS,
    PERIOD_TO_INTERNAL,
    chart_label,
    get_lang,
    init_language,
    nav_label,
    period_label,
    render_language_selector,
    stock_nav_label,
    stock_title,
    t,
    translate_rating_label,
    top_sort_label,
)

PAYPAL_DONATE_EMAIL = "nifan.man@gmail.com"
PAYPAL_DONATE_AMOUNT = "3.99"
PAYPAL_DONATE_URL = (
    "https://www.paypal.com/cgi-bin/webscr?"
    f"cmd=_donations&business={quote_plus(PAYPAL_DONATE_EMAIL)}"
    f"&amount={PAYPAL_DONATE_AMOUNT}"
    "&item_name=Coffee+Donation&currency_code=USD"
)

st.set_page_config(
    page_title="股票信息查看器",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
    .block-container {
        padding-top: 4rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 100%;
    }
    .main-nav-spacer {
        height: 1.25rem;
    }
    .main-nav-area {
        margin-top: 0.5rem;
        margin-bottom: 0.75rem;
    }
    div[data-testid="stVerticalBlock"] > div:has([data-testid="stSegmentedControl"]) {
        margin-top: 0.75rem;
        margin-bottom: 0.5rem;
    }
    [data-testid="stSegmentedControl"] > div {
        flex-wrap: wrap;
        gap: 0.35rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #1a1f2e 0%, #252b3b 100%);
        border: 1px solid #2d3548;
        border-radius: 12px;
        padding: 0.85rem 1rem;
        margin-bottom: 0.5rem;
        min-height: 4.5rem;
        overflow: visible;
    }
    button[kind="tertiary"] {
        background: transparent !important;
        border: none !important;
        color: #60a5fa !important;
        padding: 0.2rem 0 !important;
        font-weight: 500 !important;
        text-align: left !important;
        box-shadow: none !important;
        min-height: 0 !important;
    }
    button[kind="tertiary"]:hover {
        color: #93c5fd !important;
        text-decoration: underline !important;
    }
    div[data-testid="stHorizontalBlock"]:has(button[kind="tertiary"]) {
        border-bottom: 1px solid #1f2937;
        padding: 0.15rem 0;
        align-items: center;
    }
    div[data-testid="stHorizontalBlock"]:has(.macro-table-header) {
        border-bottom: 1px solid #2d3548;
        padding-bottom: 0.35rem;
        margin-bottom: 0.15rem;
    }
    .macro-table-header {
        color: #8b95a8;
        font-size: 0.82rem;
        font-weight: 600;
    }
    .top-stock-name {
        color: #d1d5db;
        font-size: 0.85rem;
        line-height: 1.35;
        padding: 0.15rem 0;
    }
    .top-stock-name-selected {
        color: #93c5fd;
        font-weight: 500;
    }
    div[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has(.top-stock-name) {
        border-bottom: 1px solid #1f2937;
        padding: 0.05rem 0;
        align-items: center;
    }
    .metric-label {
        color: #8b95a8;
        font-size: 0.8rem;
        margin-bottom: 0.2rem;
        white-space: normal;
        line-height: 1.3;
    }
    .metric-value {
        color: #f0f2f5;
        font-size: clamp(1rem, 2vw, 1.4rem);
        font-weight: 600;
        white-space: normal;
        word-break: break-word;
        line-height: 1.3;
    }
    .positive { color: #22c55e !important; }
    .negative { color: #ef4444 !important; }
    div[data-testid="stSidebar"] { background: #12151c; }
    div[data-testid="stSidebar"] div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: #2d3548;
    }
    .app-footer {
        margin-top: 2.5rem;
        padding: 1rem 0 1.5rem;
        border-top: 1px solid #2d3548;
        color: #8b95a8;
        font-size: 0.8rem;
        line-height: 1.6;
    }
    .app-footer strong {
        color: #cbd5e1;
    }
    .risk-banner {
        margin: 0;
        padding: 0;
        color: #f87171;
        font-size: 0.88rem;
        font-weight: 500;
        text-align: left;
        line-height: 1.4;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def render_sidebar_donation():
    st.sidebar.markdown(f"**☕ {t('donation')}**")
    st.sidebar.link_button(
        t("paypal_donate"),
        PAYPAL_DONATE_URL,
        use_container_width=True,
        help=t("paypal_help", email=PAYPAL_DONATE_EMAIL, amount=PAYPAL_DONATE_AMOUNT),
    )


def render_footer():
    st.markdown(
        f"""
        <div class="app-footer">
            <strong>{t("footer_source_title")}</strong><br>
            {t("footer_source_body")}<br><br>
            <strong>{t("footer_legal_title")}</strong><br>
            {t("footer_legal_body")}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(label: str, value: str, delta: str | None = None, positive: bool | None = None):
    delta_html = ""
    if delta:
        cls = "positive" if positive else "negative" if positive is False else ""
        delta_html = f'<div class="{cls}" style="font-size:0.9rem;margin-top:0.25rem;">{delta}</div>'
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _macro_table_weights(columns: list[tuple[str, str]]) -> list[float]:
    weights: list[float] = []
    for field, _ in columns:
        if field == "name_key":
            weights.append(2.0)
        elif field in ("etf_codes", "symbol"):
            weights.append(1.5)
        else:
            weights.append(1.0)
    return weights


def _render_macro_detail_table(
    source_df: pd.DataFrame,
    columns: list[tuple[str, str]],
    key_prefix: str,
):
    """Table with a clickable name column (opens detail dialog)."""
    weights = _macro_table_weights(columns)
    header = st.columns(weights)
    for col, (_, label) in zip(header, columns):
        col.markdown(f'<div class="macro-table-header">{label}</div>', unsafe_allow_html=True)

    for _, row in source_df.iterrows():
        row_cols = st.columns(weights)
        for idx, (field, _) in enumerate(columns):
            with row_cols[idx]:
                if field == "name_key":
                    name = t(row["name_key"])
                    if st.button(name, key=f"{key_prefix}_{row['symbol']}", type="tertiary"):
                        show_macro_instrument_dialog(row["symbol"], row["name_key"])
                elif field == "etf_codes":
                    st.write(row.get("etf_codes") or "—")
                elif field == "price":
                    st.write(fmt_num(row.get("price")))
                elif field == "symbol":
                    st.write(row.get("symbol", "—"))
                elif field == "day_change_pct":
                    st.write(_format_change_pct(row.get("day_change_pct")))
                elif field == "period_change_pct":
                    st.write(_format_change_pct(row.get("period_change_pct")))


def _chart_layout(fig: go.Figure, height: int = 480) -> go.Figure:
    fig.update_layout(
        height=height,
        template="plotly_dark",
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        xaxis_rangeslider_visible=False,
        margin=dict(l=40, r=40, t=40, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=True, gridcolor="#2d3548")
    fig.update_yaxes(showgrid=True, gridcolor="#2d3548")
    return fig


def build_line_chart(df: pd.DataFrame, symbol: str, period_label_text: str) -> go.Figure:
    plot_df = df.copy()
    plot_df["MA5"] = plot_df["Close"].rolling(5).mean()
    plot_df["MA20"] = plot_df["Close"].rolling(20).mean()

    start_price = plot_df["Close"].iloc[0]
    end_price = plot_df["Close"].iloc[-1]
    is_up = end_price >= start_price
    line_color = "#22c55e" if is_up else "#ef4444"
    fill_color = "rgba(34, 197, 94, 0.12)" if is_up else "rgba(239, 68, 68, 0.12)"

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.72, 0.28],
        subplot_titles=(t("chart_close_title", symbol=symbol, period=period_label_text), t("volume")),
    )

    fig.add_trace(
        go.Scatter(
            x=plot_df["Date"],
            y=plot_df["Close"],
            name=t("close_price"),
            mode="lines",
            line=dict(color=line_color, width=2.5),
            fill="tozeroy",
            fillcolor=fill_color,
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=plot_df["Date"],
            y=plot_df["MA5"],
            name="MA5",
            mode="lines",
            line=dict(color="#f59e0b", width=1.2, dash="dot"),
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=plot_df["Date"],
            y=plot_df["MA20"],
            name="MA20",
            mode="lines",
            line=dict(color="#60a5fa", width=1.2, dash="dash"),
        ),
        row=1,
        col=1,
    )

    colors = ["#22c55e" if c >= o else "#ef4444" for c, o in zip(plot_df["Close"], plot_df["Open"])]
    fig.add_trace(
        go.Bar(x=plot_df["Date"], y=plot_df["Volume"], name=t("volume"), marker_color=colors, opacity=0.65),
        row=2,
        col=1,
    )

    return _chart_layout(fig, height=560)


def build_candlestick_chart(df: pd.DataFrame, symbol: str, period_label_text: str) -> go.Figure:
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.72, 0.28],
        subplot_titles=(t("chart_candle_title", symbol=symbol, period=period_label_text), t("volume")),
    )

    fig.add_trace(
        go.Candlestick(
            x=df["Date"],
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name=t("candlestick"),
            increasing_line_color="#22c55e",
            decreasing_line_color="#ef4444",
        ),
        row=1,
        col=1,
    )

    colors = ["#22c55e" if c >= o else "#ef4444" for c, o in zip(df["Close"], df["Open"])]
    fig.add_trace(
        go.Bar(x=df["Date"], y=df["Volume"], name=t("volume"), marker_color=colors, opacity=0.65),
        row=2,
        col=1,
    )

    fig.update_layout(showlegend=False)
    return _chart_layout(fig, height=560)


def build_price_chart(df: pd.DataFrame, symbol: str, period_label_text: str, chart_key: str) -> go.Figure:
    if chart_key == "candle":
        return build_candlestick_chart(df, symbol, period_label_text)
    return build_line_chart(df, symbol, period_label_text)


def render_period_banner(period_key: str, history: pd.DataFrame):
    start, end = get_period_bounds(history)
    label = period_label(period_key)
    if start is not None and end is not None:
        st.info(t("period_banner", start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"), period=label))
    else:
        st.info(t("period_banner_short", period=label))


def render_period_trading_summary(history: pd.DataFrame):
    summary = compute_period_trading_summary(history)
    if not summary:
        return

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        change = summary.get("period_change_pct")
        render_metric_card(
            t("metric_period_change"),
            fmt_pct(change) if change is not None else "—",
            positive=change is not None and change >= 0,
        )
    with c2:
        render_metric_card(t("metric_period_high"), fmt_num(summary.get("period_high")))
    with c3:
        render_metric_card(t("metric_period_low"), fmt_num(summary.get("period_low")))
    with c4:
        render_metric_card(t("metric_avg_volume"), fmt_num(summary.get("avg_volume"), decimals=0))

    c5, c6, c7, _ = st.columns(4)
    with c5:
        render_metric_card(t("metric_trading_days"), str(summary.get("trading_days", "—")))
    with c6:
        render_metric_card(t("metric_total_volume"), fmt_num(summary.get("total_volume"), decimals=0))
    with c7:
        render_metric_card(t("metric_avg_price"), fmt_num(summary.get("avg_close")))


def render_price_chart(history: pd.DataFrame, symbol: str, period_key: str, chart_key: str):
    if history.empty:
        st.warning(t("no_history"))
        return

    render_period_trading_summary(history)
    period_text = period_label(period_key)

    st.plotly_chart(
        build_price_chart(history, symbol, period_text, chart_key),
        use_container_width=True,
        key=f"chart_{symbol}_{period_key}_{chart_key}_{get_lang()}",
    )


def render_favorite_button(symbol: str, name: str = "", *, key: str, help_text: str | None = None):
    starred = is_favorite(symbol)
    label = "⭐" if starred else "☆"
    if st.button(label, key=key, help=help_text or t("fav_toggle")):
        toggle_favorite(symbol, name)
        st.rerun()


def render_sidebar_favorites():
    st.sidebar.markdown(f"**⭐ {t('favorites')}**")
    favorites = load_favorites()

    if not favorites:
        st.sidebar.caption(t("fav_empty"))
        return

    for fav in favorites:
        label = fav.symbol
        if fav.name:
            label = f"{fav.symbol} · {fav.name}"
        row_btn, row_star = st.sidebar.columns([5, 1])
        with row_btn:
            st.button(
                label,
                key=f"pick_fav_{fav.symbol}",
                use_container_width=True,
                on_click=_select_stock,
                kwargs={"symbol": fav.symbol},
            )
        with row_star:
            if st.button("✕", key=f"drop_fav_{fav.symbol}", help=t("fav_remove")):
                remove_favorite(fav.symbol)
                st.rerun()


def render_news_list(news_df: pd.DataFrame, *, empty_message: str):
    if news_df.empty:
        st.info(empty_message)
        return

    with st.container(height=320, border=False):
        for _, row in news_df.iterrows():
            title = row.get("标题", "—")
            source = row.get("来源", "—")
            date = row.get("日期", "—")
            summary = row.get("摘要", "")
            link = row.get("链接")
            if link:
                st.markdown(f"**{date}** · {source}  \n[{title}]({link})")
            else:
                st.markdown(f"**{date}** · {source}  \n{title}")
            if summary:
                st.caption(summary)
            st.markdown("---")


@st.cache_data(ttl=900, show_spinner=False)
def load_recent_news(symbol: str) -> pd.DataFrame:
    return fetch_recent_news(symbol)


def render_recent_news(symbol: str):
    st.markdown(f"### {stock_title('recent_news', symbol)}")
    with st.spinner(t("loading_news")):
        news_df = load_recent_news(symbol)
    render_news_list(news_df, empty_message=t("no_recent_news"))


def render_quote_overview(quote: dict, history: pd.DataFrame, period_key: str, chart_key: str):
    currency = quote.get("currency", "")
    price = quote.get("price")
    change = quote.get("change")
    change_pct = quote.get("change_pct")
    is_up = change is not None and change >= 0

    title_col, fav_col = st.columns([10, 1])
    with title_col:
        st.markdown(f"## {stock_title('nav_overview', quote['symbol'])}")
        st.caption(f"{quote.get('name', quote['symbol'])} · {quote['symbol']} · {quote.get('exchange', '—')}")
    with fav_col:
        st.write("")
        render_favorite_button(
            quote["symbol"],
            quote.get("name", ""),
            key=f"fav_main_{quote['symbol']}",
        )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        delta = None
        if change is not None and change_pct is not None:
            sign = "+" if change >= 0 else ""
            delta = f"{sign}{fmt_num(change)} ({fmt_pct(change_pct)})"
        render_metric_card(t("metric_current_price"), fmt_num(price, prefix=f"{currency} "), delta=delta, positive=is_up)
    with c2:
        render_metric_card(t("metric_volume"), fmt_num(quote.get("volume"), decimals=0))
    with c3:
        render_metric_card(t("metric_avg_daily_volume"), fmt_num(quote.get("avg_volume"), decimals=0))
    with c4:
        render_metric_card(t("metric_market_cap"), fmt_num(quote.get("market_cap"), prefix=f"{currency} "))

    with st.expander(t("more_metrics"), expanded=False):
        c5, c6, c7, c8 = st.columns(4)
        with c5:
            render_metric_card(t("metric_day_high"), fmt_num(quote.get("day_high"), prefix=f"{currency} "))
        with c6:
            render_metric_card(t("metric_day_low"), fmt_num(quote.get("day_low"), prefix=f"{currency} "))
        with c7:
            render_metric_card(t("metric_52w_high"), fmt_num(quote.get("fifty_two_week_high"), prefix=f"{currency} "))
        with c8:
            render_metric_card(t("metric_52w_low"), fmt_num(quote.get("fifty_two_week_low"), prefix=f"{currency} "))

        c9, c10, c11, c12 = st.columns(4)
        with c9:
            render_metric_card(t("metric_prev_close"), fmt_num(quote.get("prev_close"), prefix=f"{currency} "))
        with c10:
            pe = quote.get("pe_ratio")
            render_metric_card(t("metric_pe"), fmt_num(pe) if pe else "—")
        with c11:
            dy = quote.get("dividend_yield")
            render_metric_card(t("metric_dividend_yield"), f"{fmt_num(dy * 100)}%" if dy else "—")
        with c12:
            updated = quote.get("updated_at")
            render_metric_card(t("metric_updated_at"), updated.strftime("%H:%M:%S") if updated else "—")

    st.markdown(f"### {t('price_curve')}")
    render_price_chart(history, quote["symbol"], period_key, chart_key)


def build_ownership_pie(breakdown: dict) -> go.Figure | None:
    segments = [
        (t("seg_institution"), breakdown.get("institution_pct"), "#60a5fa"),
        (t("seg_insider"), breakdown.get("insider_pct"), "#f59e0b"),
        (t("seg_public"), breakdown.get("retail_pct"), "#22c55e"),
    ]
    labels = []
    values = []
    colors = []
    for label, value, color in segments:
        if value is not None and value > 0:
            labels.append(label)
            values.append(value)
            colors.append(color)

    if not values:
        return None

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.45,
                marker=dict(colors=colors),
                textinfo="label+percent",
                hovertemplate="%{label}<br>%{percent}<br>%{value:.2f}%<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        height=360,
        template="plotly_dark",
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        margin=dict(l=20, r=20, t=20, b=20),
        showlegend=True,
    )
    return fig


def render_ownership_analysis_tab(symbol: str, period_key: str, history: pd.DataFrame):
    st.subheader(stock_title("ownership_title", symbol))
    render_period_banner(period_key, history)
    st.caption(t("ownership_caption"))

    with st.spinner(t("loading_ownership")):
        analysis = fetch_ownership_analysis(symbol, PERIOD_TO_INTERNAL[period_key])

    if not analysis["has_data"]:
        st.warning(t("no_ownership_data"))
        return

    breakdown = analysis["breakdown"]
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_metric_card(t("metric_inst_reports"), str(analysis["institution_count"] or "0"))
    with c2:
        render_metric_card(t("metric_fund_reports"), str(analysis["mutualfund_count"] or "0"))
    with c3:
        render_metric_card(t("metric_insider_count"), str(analysis["insider_count"] or "—"))
    with c4:
        inst_pct = breakdown.get("institution_pct")
        render_metric_card(t("metric_inst_pct"), f"{fmt_num(inst_pct)}%" if inst_pct is not None else "—")

    pie_col, stat_col = st.columns([1, 1])
    with pie_col:
        st.markdown(f"#### {t('ownership_structure')}")
        st.caption(t("ownership_structure_note"))
        pie = build_ownership_pie(breakdown)
        if pie:
            st.plotly_chart(pie, use_container_width=True)
        else:
            st.info(t("no_ownership_data"))

    with stat_col:
        st.markdown(f"#### {t('structure_detail')}")
        rows = [
            (t("inst_holding"), breakdown.get("institution_pct")),
            (t("insider_holding"), breakdown.get("insider_pct")),
            (t("fund_holding"), breakdown.get("mutual_fund_pct")),
            (t("inst_float"), breakdown.get("institution_float_pct")),
            (t("public_other"), breakdown.get("retail_pct")),
        ]
        stat_df = pd.DataFrame(
            [{t("item"): name, t("ratio_pct"): f"{fmt_num(val)}%" if val is not None else "—"} for name, val in rows]
        )
        st.dataframe(stat_df, use_container_width=True, hide_index=True)

    st.markdown(f"#### {t('inst_reports_range')}")
    if analysis["institutional_holders"].empty:
        st.info(t("no_inst_reports"))
    else:
        st.dataframe(style_numeric_dataframe(analysis["institutional_holders"]), use_container_width=True, hide_index=True)

    st.markdown(f"#### {t('fund_reports_range')}")
    if analysis["mutualfund_holders"].empty:
        st.info(t("no_fund_reports"))
    else:
        st.dataframe(style_numeric_dataframe(analysis["mutualfund_holders"]), use_container_width=True, hide_index=True)

    st.markdown(f"#### {t('insider_holdings')}")
    st.caption(t("insider_holdings_note"))
    if analysis["insider_roster"].empty:
        st.info(t("no_insider_holdings"))
    else:
        st.dataframe(style_numeric_dataframe(analysis["insider_roster"]), use_container_width=True, hide_index=True)

    st.markdown(f"#### {t('insider_trades_range')}")
    if analysis["insider_transactions"].empty:
        st.info(t("no_insider_trades"))
    else:
        st.dataframe(style_numeric_dataframe(analysis["insider_transactions"]), use_container_width=True, hide_index=True)

    st.markdown(f"#### {t('volume_spike_range')}")
    st.caption(t("volume_spike_note"))
    if analysis["large_volume_days"].empty:
        st.info(t("no_volume_spike"))
    else:
        st.dataframe(style_numeric_dataframe(analysis["large_volume_days"]), use_container_width=True, hide_index=True)


def build_recommendation_bar(distribution: dict) -> go.Figure | None:
    if not distribution:
        return None
    labels = [translate_rating_label(k) for k in distribution.keys()]
    values = list(distribution.values())
    colors = {
        translate_rating_label("强力买入"): "#16a34a",
        translate_rating_label("买入"): "#22c55e",
        translate_rating_label("持有"): "#f59e0b",
        translate_rating_label("卖出"): "#ef4444",
        translate_rating_label("强力卖出"): "#b91c1c",
    }
    fig = go.Figure(
        data=[
            go.Bar(
                x=labels,
                y=values,
                marker_color=[colors.get(label, "#60a5fa") for label in labels],
            )
        ]
    )
    fig.update_layout(
        height=320,
        template="plotly_dark",
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        margin=dict(l=40, r=20, t=20, b=40),
        yaxis_title=t("analyst_count_axis"),
    )
    return fig


def build_price_target_chart(current: float | None, low: float | None, mean: float | None, high: float | None) -> go.Figure | None:
    items = [
        (t("target_low_short"), low, "#ef4444"),
        (t("target_current"), current, "#60a5fa"),
        (t("target_mean_short"), mean, "#22c55e"),
        (t("target_high_short"), high, "#16a34a"),
    ]
    labels = []
    values = []
    colors = []
    for label, value, color in items:
        if value is not None:
            labels.append(label)
            values.append(value)
            colors.append(color)
    if not values:
        return None

    fig = go.Figure(
        data=[go.Bar(x=labels, y=values, marker_color=colors, text=[fmt_num(v) for v in values], textposition="outside")]
    )
    fig.update_layout(
        height=320,
        template="plotly_dark",
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        margin=dict(l=40, r=20, t=20, b=40),
        yaxis_title=t("price_axis"),
    )
    return fig


def build_growth_chart(growth_df: pd.DataFrame) -> go.Figure | None:
    if growth_df.empty:
        return None
    fig = go.Figure()
    color_map = {
        "个股增长预期%": "#22c55e",
        "行业增长预期%": "#60a5fa",
        "板块增长预期%": "#f59e0b",
        "指数增长预期%": "#a78bfa",
    }
    for col in growth_df.columns:
        if col == "周期":
            continue
        fig.add_trace(
            go.Bar(name=col, x=growth_df["周期"], y=growth_df[col], marker_color=color_map.get(col, "#94a3b8"))
        )
    fig.update_layout(
        barmode="group",
        height=340,
        template="plotly_dark",
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        margin=dict(l=40, r=20, t=20, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def render_trend_analysis_tab(symbol: str, period_key: str, history: pd.DataFrame, current_price: float | None):
    st.subheader(stock_title("trend_title", symbol))
    render_period_banner(period_key, history)
    st.caption(t("trend_caption"))

    with st.spinner(t("loading_trend")):
        analysis = fetch_trend_analysis(symbol, PERIOD_TO_INTERNAL[period_key], current_price=current_price)

    if not analysis["has_data"]:
        st.warning(t("no_trend_data"))
        return

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_metric_card(t("consensus_rating"), analysis.get("consensus_rating", "—"))
    with c2:
        score = analysis.get("consensus_score")
        render_metric_card(t("rating_score"), fmt_num(score) if score is not None else "—")
    with c3:
        render_metric_card(t("analyst_coverage"), fmt_num(analysis.get("analyst_count"), decimals=0) if analysis.get("analyst_count") else "—")
    with c4:
        upside = analysis.get("upside_pct")
        render_metric_card(
            t("target_upside"),
            fmt_pct(upside) if upside is not None else "—",
            positive=upside is not None and upside >= 0,
        )

    t1, t2 = st.columns(2)
    with t1:
        st.markdown(f"#### {t('analyst_targets')}")
        target_chart = build_price_target_chart(
            analysis.get("current_price"),
            analysis.get("target_low"),
            analysis.get("target_mean"),
            analysis.get("target_high"),
        )
        if target_chart:
            st.plotly_chart(target_chart, use_container_width=True)
        else:
            st.info(t("no_target_data"))
    with t2:
        st.markdown(f"#### {t('rating_distribution')}")
        dist_chart = build_recommendation_bar(analysis.get("latest_distribution", {}))
        if dist_chart:
            st.plotly_chart(dist_chart, use_container_width=True)
        else:
            st.info(t("no_rating_dist"))

    c5, c6, c7, c8 = st.columns(4)
    with c5:
        render_metric_card(t("target_mean"), fmt_num(analysis.get("target_mean")))
    with c6:
        render_metric_card(t("target_high"), fmt_num(analysis.get("target_high")))
    with c7:
        render_metric_card(t("target_low"), fmt_num(analysis.get("target_low")))
    with c8:
        rating_text = analysis.get("average_rating_text")
        render_metric_card(t("avg_rating_text"), rating_text if rating_text else "—")

    st.markdown(f"#### {t('rating_changes')}")
    st.caption(t("rating_changes_note"))
    if analysis["upgrades_downgrades"].empty:
        st.info(t("no_rating_changes"))
    else:
        st.dataframe(style_numeric_dataframe(analysis["upgrades_downgrades"]), use_container_width=True, hide_index=True)

    st.markdown(f"#### {t('growth_forecast')}")
    growth_chart = build_growth_chart(analysis["growth_estimates"])
    if growth_chart:
        st.plotly_chart(growth_chart, use_container_width=True)
    if analysis["growth_estimates"].empty:
        st.info(t("no_growth_forecast"))
    else:
        st.dataframe(style_numeric_dataframe(analysis["growth_estimates"]), use_container_width=True, hide_index=True)

    eps_col1, eps_col2 = st.columns(2)
    with eps_col1:
        st.markdown(f"##### {t('eps_trend')}")
        if analysis["eps_trend"].empty:
            st.info(t("no_eps_trend"))
        else:
            st.dataframe(style_numeric_dataframe(analysis["eps_trend"]), use_container_width=True, hide_index=True)
    with eps_col2:
        st.markdown(f"##### {t('eps_revisions')}")
        if analysis["eps_revisions"].empty:
            st.info(t("no_eps_revisions"))
        else:
            st.dataframe(style_numeric_dataframe(analysis["eps_revisions"]), use_container_width=True, hide_index=True)

    if not analysis["recommendation_trend"].empty:
        st.markdown(f"#### {t('rating_trend_monthly')}")
        st.dataframe(style_numeric_dataframe(analysis["recommendation_trend"]), use_container_width=True, hide_index=True)

    st.markdown(f"#### {t('news_views')}")
    render_news_list(analysis["news"], empty_message=t("no_news"))


def render_portfolio_tab():
    st.subheader(t("portfolio_title"))

    summary = compute_portfolio_summary()
    if summary["rows"]:
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            render_metric_card(t("metric_cost"), fmt_num(summary["total_cost"], prefix="$ "))
        with m2:
            render_metric_card(t("metric_value"), fmt_num(summary["total_value"], prefix="$ "))
        with m3:
            pnl = summary["total_pnl"]
            render_metric_card(
                t("metric_pnl"),
                fmt_num(pnl, prefix="$ "),
                delta=fmt_pct(summary["total_pnl_pct"]),
                positive=pnl >= 0,
            )
        with m4:
            render_metric_card(t("metric_positions"), str(len(summary["rows"])))

        df = pd.DataFrame(summary["rows"])
        display = df[
            ["symbol", "name", "shares", "cost_basis", "current_price", "cost_total", "market_value", "pnl", "pnl_pct", "note"]
        ].copy()
        display.columns = [
            t("col_symbol"), t("col_name"), t("col_shares"), t("col_cost_basis"), t("col_current"),
            t("col_cost_total"), t("col_market_value"), t("col_pnl"), t("col_pnl_pct"), t("col_note"),
        ]
        display[t("col_pnl_pct")] = display[t("col_pnl_pct")].apply(lambda x: fmt_pct(x) if pd.notna(x) else "—")

        st.dataframe(
            display.style.format(
                {
                    t("col_shares"): "{:,.2f}",
                    t("col_cost_basis"): "{:,.2f}",
                    t("col_current"): "{:,.2f}",
                    t("col_cost_total"): "{:,.2f}",
                    t("col_market_value"): "{:,.2f}",
                    t("col_pnl"): "{:+,.2f}",
                },
                na_rep="—",
            ),
            use_container_width=True,
            hide_index=True,
        )

        st.markdown(f"##### {t('delete_position')}")
        del_col1, del_col2 = st.columns([3, 1])
        with del_col1:
            to_delete = st.selectbox(t("select_delete"), [h.symbol for h in load_holdings()], key="del_select")
        with del_col2:
            st.write("")
            st.write("")
            if st.button(t("delete"), type="secondary", key="del_btn"):
                remove_holding(to_delete)
                st.rerun()
    else:
        st.info(t("no_portfolio"))

    st.markdown("---")
    st.markdown(f"##### {t('add_update_position')}")
    with st.form("holding_form", clear_on_submit=True):
        fc1, fc2, fc3, fc4 = st.columns(4)
        with fc1:
            h_symbol = st.text_input(t("symbol"), placeholder="AAPL")
        with fc2:
            h_shares = st.number_input(t("shares"), min_value=0.0, step=1.0, format="%.2f")
        with fc3:
            h_cost = st.number_input(t("cost_per_share"), min_value=0.0, step=0.01, format="%.2f")
        with fc4:
            h_note = st.text_input(t("col_note"), placeholder=t("note_optional"))
        submitted = st.form_submit_button(t("save_position"), type="primary")
        if submitted:
            if not h_symbol.strip():
                st.error(t("err_need_symbol"))
            elif not is_us_symbol(h_symbol):
                st.error(t("err_non_us_symbol"))
            elif h_shares <= 0:
                st.error(t("err_shares"))
            elif h_cost <= 0:
                st.error(t("err_cost"))
            else:
                existing = {h.symbol for h in load_holdings()}
                sym = h_symbol.strip().upper()
                if sym in existing:
                    update_holding(sym, h_shares, h_cost, h_note)
                    st.success(t("updated_symbol", symbol=sym))
                else:
                    add_holding(sym, h_shares, h_cost, h_note)
                    st.success(t("added_symbol", symbol=sym))
                st.rerun()


def render_risk_banner():
    st.markdown(f'<div class="risk-banner">⚠️ {t("risk_banner")}</div>', unsafe_allow_html=True)


def render_top_bar(symbol: str = "") -> tuple[str, str, str]:
    risk_col, controls_col = st.columns([1.5, 2.5])
    with risk_col:
        render_risk_banner()
    with controls_col:
        period_col, chart_col, lang_col = st.columns([1, 1, 0.95])
        with period_col:
            period_key = st.selectbox(
                t("period"),
                PERIOD_KEYS,
                format_func=period_label,
                key="period_key",
            )
        with chart_col:
            chart_key = st.selectbox(
                t("chart_type"),
                CHART_KEYS,
                format_func=chart_label,
                key="chart_key",
            )
        with lang_col:
            render_language_selector()

    nav_labels = [stock_nav_label(k, symbol) for k in NAV_KEYS]
    if "nav_key" not in st.session_state:
        st.session_state["nav_key"] = NAV_KEYS[0]
    current_nav = st.session_state.get("nav_key", NAV_KEYS[0])
    if current_nav not in NAV_KEYS:
        current_nav = NAV_KEYS[0]
    if st.session_state.get("main_nav") not in nav_labels:
        st.session_state["main_nav"] = stock_nav_label(current_nav, symbol)

    selected = st.segmented_control(
        t("nav_label"),
        nav_labels,
        label_visibility="collapsed",
        width="stretch",
        key="main_nav",
    )
    nav_key = NAV_KEYS[nav_labels.index(selected)]
    st.session_state["nav_key"] = nav_key
    st.markdown("---")
    return nav_key, period_key, chart_key


def _init_app_state():
    if "symbol" not in st.session_state:
        st.session_state["symbol"] = ""
    if "_view_symbol" not in st.session_state:
        st.session_state["_view_symbol"] = st.session_state["symbol"]
    if "nav_key" not in st.session_state:
        st.session_state["nav_key"] = NAV_KEYS[0]
    if "main_nav" not in st.session_state:
        st.session_state["main_nav"] = nav_label(NAV_KEYS[0])
    if "period_key" not in st.session_state:
        st.session_state["period_key"] = "3mo"
    if "chart_key" not in st.session_state:
        st.session_state["chart_key"] = CHART_KEYS[0]


def _sync_stock_view(symbol: str):
    prev = st.session_state.get("_view_symbol")
    if prev != symbol:
        st.session_state["_view_symbol"] = symbol
        if prev is not None and st.session_state.get("nav_key") in ("macro", "portfolio"):
            st.session_state["nav_key"] = "overview"
            st.session_state["main_nav"] = stock_nav_label("overview", symbol)


def _normalize_symbol_input():
    st.session_state["symbol"] = normalize_symbol(str(st.session_state.get("symbol", "")))
    _sync_stock_view(st.session_state["symbol"])


def _select_stock(symbol: str):
    st.session_state["symbol"] = normalize_symbol(symbol)
    st.session_state["nav_key"] = "overview"
    st.session_state["main_nav"] = stock_nav_label("overview", st.session_state["symbol"])
    st.session_state["_view_symbol"] = st.session_state["symbol"]
    st.session_state["_goto_overview"] = True


@st.cache_data(ttl=3600, show_spinner=False)
def load_top_stocks(period_internal: str, sort_by: str) -> pd.DataFrame:
    return fetch_top_stocks(period_internal, sort_by)


@st.cache_data(ttl=1800, show_spinner=False)
def load_macro_snapshot(period_internal: str) -> dict:
    return fetch_macro_snapshot(period_internal)


def _format_change_pct(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    sign = "+" if value >= 0 else ""
    return f"{sign}{fmt_num(value)}%"


def build_macro_index_chart(index_histories: dict[str, pd.DataFrame]) -> go.Figure | None:
    fig = go.Figure()
    has_data = False
    for symbol, df in index_histories.items():
        if df.empty or len(df) < 2:
            continue
        base = df["Close"].iloc[0]
        if not base:
            continue
        norm = df["Close"] / base * 100
        fig.add_trace(
            go.Scatter(
                x=df["Date"],
                y=norm,
                name=t(INDEX_NAME_KEYS.get(symbol, symbol)),
                mode="lines",
                line=dict(width=2),
            )
        )
        has_data = True

    if not has_data:
        return None

    return _chart_layout(fig, height=420)


def build_sector_bar_chart(sectors_df: pd.DataFrame) -> go.Figure | None:
    if sectors_df.empty:
        return None
    plot_df = sectors_df.dropna(subset=["period_change_pct"]).copy()
    if plot_df.empty:
        return None

    labels = [t(row["name_key"]) for _, row in plot_df.iterrows()]
    values = plot_df["period_change_pct"].tolist()
    colors = ["#22c55e" if (v is not None and v >= 0) else "#ef4444" for v in values]

    fig = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker_color=colors,
            text=[_format_change_pct(v) for v in values],
            textposition="outside",
        )
    )
    fig.update_layout(
        height=max(360, len(labels) * 36),
        template="plotly_dark",
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        margin=dict(l=40, r=60, t=30, b=30),
        xaxis_title=t("macro_col_period_change"),
    )
    fig.update_xaxes(showgrid=True, gridcolor="#2d3548")
    fig.update_yaxes(showgrid=False)
    return fig


@st.cache_data(ttl=3600, show_spinner=False)
def load_instrument_detail(symbol: str) -> dict:
    return fetch_instrument_detail(symbol)


@st.dialog(t("macro_detail_title"), width="large")
def show_macro_instrument_dialog(symbol: str, name_key: str):
    with st.spinner(t("loading_macro_detail")):
        detail = load_instrument_detail(symbol)

    title_name = t(name_key) if name_key else detail.get("name", symbol)
    st.markdown(f"### {title_name}")
    type_label = t("macro_detail_type_etf") if detail.get("is_etf") else t("macro_detail_type_index")
    st.caption(f"{detail['symbol']} · {type_label}")

    meta_cols = st.columns(4)
    with meta_cols[0]:
        if detail.get("total_assets"):
            render_metric_card(t("macro_detail_total_assets"), fmt_num(detail["total_assets"], decimals=0))
    with meta_cols[1]:
        if detail.get("expense_ratio") is not None:
            render_metric_card(t("macro_detail_expense_ratio"), f"{fmt_num(float(detail['expense_ratio']) * 100)}%")
    with meta_cols[2]:
        if detail.get("dividend_yield") is not None:
            render_metric_card(t("macro_detail_yield"), f"{fmt_num(float(detail['dividend_yield']) * 100)}%")
    with meta_cols[3]:
        if detail.get("category"):
            render_metric_card(t("macro_detail_category"), str(detail["category"]))

    if detail.get("fund_family"):
        st.caption(f"{t('macro_detail_fund_family')}: {detail['fund_family']}")

    desc = detail.get("description") or ""
    if not desc and detail.get("description_key"):
        desc = t(detail["description_key"])
    st.markdown(f"**{t('macro_detail_intro')}**")
    st.write(desc or "—")

    holdings = detail.get("holdings", pd.DataFrame())
    components = detail.get("components", pd.DataFrame())
    sectors = detail.get("sectors", pd.DataFrame())

    if detail.get("is_etf") and not holdings.empty:
        st.markdown(f"**{t('macro_detail_holdings')}**")
        show = holdings.copy()
        if "weight_pct" in show.columns:
            show["weight_pct"] = show["weight_pct"].apply(
                lambda v: f"{fmt_num(v)}%" if pd.notna(v) else "—"
            )
        show = show.rename(
            columns={
                "symbol": t("col_symbol"),
                "name": t("col_name"),
                "weight_pct": t("macro_col_weight"),
            }
        )
        st.dataframe(show, use_container_width=True, hide_index=True)
    elif detail.get("is_index") and not components.empty:
        st.markdown(f"**{t('macro_detail_components')}**")
        st.caption(t("macro_detail_components_note"))
        show = components.copy()
        if "weight_pct" in show.columns:
            show["weight_pct"] = show["weight_pct"].apply(
                lambda v: f"{fmt_num(v)}%" if pd.notna(v) else "—"
            )
        show = show.rename(
            columns={
                "symbol": t("col_symbol"),
                "name": t("col_name"),
                "weight_pct": t("macro_col_weight"),
            }
        )
        st.dataframe(show, use_container_width=True, hide_index=True)
    elif detail.get("is_etf"):
        st.caption(t("macro_detail_no_holdings"))

    if not sectors.empty:
        st.markdown(f"**{t('macro_detail_sectors')}**")
        show = sectors.copy()
        if "weight_pct" in show.columns:
            show["weight_pct"] = show["weight_pct"].apply(
                lambda v: f"{fmt_num(v)}%" if pd.notna(v) else "—"
            )
        show = show.rename(columns={"sector": t("macro_col_sector"), "weight_pct": t("macro_col_weight")})
        st.dataframe(show, use_container_width=True, hide_index=True)

    if detail.get("is_etf"):
        st.button(
            t("macro_detail_view_etf"),
            type="primary",
            use_container_width=True,
            on_click=_select_stock,
            kwargs={"symbol": detail["symbol"]},
            key=f"macro_etf_view_{detail['symbol']}",
        )


def render_macro_overview(macro: dict, period_key: str):
    indices_df = macro.get("indices", pd.DataFrame())
    sectors_df = macro.get("sectors", pd.DataFrame())
    index_histories = macro.get("index_histories", {})

    st.markdown(f"## {t('macro_title')}")
    st.caption(period_label(period_key))

    st.markdown(f"### {t('macro_indices')}")
    if indices_df.empty:
        st.info(t("no_history"))
    else:
        cols = st.columns(min(len(indices_df), 5))
        for i, row in indices_df.iterrows():
            with cols[i % len(cols)]:
                day_chg = row.get("day_change_pct")
                is_up = day_chg is not None and day_chg >= 0
                render_metric_card(
                    t(row["name_key"]),
                    fmt_num(row.get("price")),
                    _format_change_pct(day_chg),
                    is_up if day_chg is not None else None,
                )

        _render_macro_detail_table(
            indices_df,
            [
                ("name_key", t("macro_col_name")),
                ("etf_codes", t("macro_col_etf_codes")),
                ("price", t("macro_col_price")),
                ("day_change_pct", t("macro_col_day_change")),
                ("period_change_pct", t("macro_col_period_change")),
            ],
            "macro_tbl_idx",
        )

    st.markdown(f"### {t('macro_index_chart')}")
    index_fig = build_macro_index_chart(index_histories)
    if index_fig:
        st.plotly_chart(index_fig, use_container_width=True)
    else:
        st.caption(t("no_history"))

    st.markdown(f"### {t('macro_sectors')}")
    sector_fig = build_sector_bar_chart(sectors_df)
    if sector_fig:
        st.plotly_chart(sector_fig, use_container_width=True)

    if not sectors_df.empty:
        _render_macro_detail_table(
            sectors_df,
            [
                ("name_key", t("macro_col_name")),
                ("symbol", t("col_symbol")),
                ("price", t("macro_col_price")),
                ("day_change_pct", t("macro_col_day_change")),
                ("period_change_pct", t("macro_col_period_change")),
            ],
            "macro_tbl_sec",
        )


def render_top_stocks_picker(period_internal: str):
    sort_by = st.sidebar.selectbox(
        t("top_sort"),
        TOP_SORT_KEYS,
        index=0,
        format_func=top_sort_label,
        key="top_sort_by",
    )
    top_df = load_top_stocks(period_internal, sort_by)
    if top_df.empty:
        st.sidebar.caption(t("top_stocks_empty"))
        return

    current = st.session_state.get("symbol", "")
    st.sidebar.caption(t("top_stocks_pick"))

    header = st.sidebar.columns([1, 2.2])
    header[0].markdown(f'<div class="macro-table-header">{t("col_symbol")}</div>', unsafe_allow_html=True)
    header[1].markdown(f'<div class="macro-table-header">{t("col_name")}</div>', unsafe_allow_html=True)

    for _, row in top_df.iterrows():
        sym = row["symbol"]
        name = row["name"]
        row_cols = st.sidebar.columns([1, 2.2])
        with row_cols[0]:
            st.button(
                sym,
                key=f"top_pick_{sym}_{sort_by}",
                type="tertiary",
                on_click=_select_stock,
                kwargs={"symbol": sym},
            )
        with row_cols[1]:
            name_cls = "top-stock-name"
            if sym == current:
                name_cls += " top-stock-name-selected"
            st.markdown(f'<div class="{name_cls}">{name}</div>', unsafe_allow_html=True)


def _fill_top_stocks_sidebar(slot, period_internal: str):
    with slot.container():
        render_top_stocks_picker(period_internal)


def render_stock_views(nav_key: str, symbol: str, quote: dict, history: pd.DataFrame, period_key: str, chart_key: str):
    if nav_key == "overview":
        render_period_banner(period_key, history)
        render_quote_overview(quote, history, period_key, chart_key)
    elif nav_key == "price":
        st.subheader(stock_title("price_trend_title", symbol))
        render_period_banner(period_key, history)
        render_price_chart(history, symbol, period_key, chart_key)

        if not history.empty:
            with st.expander(t("raw_data")):
                show_df = history.copy()
                show_df["Date"] = show_df["Date"].dt.strftime("%Y-%m-%d")
                st.dataframe(style_numeric_dataframe(show_df), use_container_width=True, hide_index=True)
    elif nav_key == "ownership":
        render_ownership_analysis_tab(symbol, period_key, history)
    elif nav_key == "trend":
        render_trend_analysis_tab(symbol, period_key, history, quote.get("price"))
    elif nav_key == "news":
        render_recent_news(symbol)


def main():
    init_language()
    _init_app_state()
    st.sidebar.title(f"📈 {t('app_title')}")
    st.sidebar.markdown(t("app_subtitle"))
    render_sidebar_donation()
    st.sidebar.markdown("---")

    sym_col, fav_col = st.sidebar.columns([5, 1])
    with sym_col:
        st.text_input(
            t("symbol"),
            key="symbol",
            on_change=_normalize_symbol_input,
            help=t("symbol_help"),
        )
    symbol = normalize_symbol(st.session_state.get("symbol", ""))
    if st.session_state.get("symbol") != symbol:
        st.session_state["symbol"] = symbol
    _sync_stock_view(symbol)
    with fav_col:
        st.write("")
        if symbol:
            render_favorite_button(symbol, key=f"fav_sidebar_{symbol}")

    st.sidebar.markdown("---")
    render_sidebar_favorites()

    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**{t('top_stocks')}**")
    top_stocks_slot = st.sidebar.empty()
    period_internal = PERIOD_TO_INTERNAL[st.session_state.get("period_key", "3mo")]

    if st.session_state.pop("_goto_overview", False):
        st.session_state["nav_key"] = "overview"
        st.session_state["main_nav"] = stock_nav_label("overview", symbol)

    try:
        nav_key, period_key, chart_key = render_top_bar(symbol)
        period_internal = PERIOD_TO_INTERNAL[period_key]

        if nav_key == "macro":
            try:
                with st.spinner(t("loading_macro")):
                    macro = load_macro_snapshot(period_internal)
                render_macro_overview(macro, period_key)
            except Exception as exc:
                st.error(t("err_macro", error=exc))
            render_footer()
            return

        if nav_key == "portfolio":
            render_portfolio_tab()
            render_footer()
            return

        if not symbol:
            st.warning(t("warn_no_symbol"))
            render_footer()
            return

        if not is_us_symbol(symbol):
            st.warning(t("err_non_us_symbol"))
            render_footer()
            return

        try:
            with st.spinner(t("loading_quote")):
                quote = fetch_quote(symbol)
                history = fetch_history(symbol, period_internal)
        except Exception as exc:
            st.error(t("err_fetch", error=exc))
            st.info(t("err_retry"))
            render_footer()
            return

        if quote.get("price") is None:
            st.error(t("err_no_symbol", symbol=symbol))
            render_footer()
            return

        if is_favorite(symbol) and quote.get("name"):
            add_favorite(symbol, quote["name"])

        render_stock_views(nav_key, symbol, quote, history, period_key, chart_key)
        render_footer()
    finally:
        _fill_top_stocks_sidebar(top_stocks_slot, period_internal)


if __name__ == "__main__":
    main()
