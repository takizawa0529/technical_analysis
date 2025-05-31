import streamlit as st
st.set_page_config(layout="wide")

import os
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.dates import date2num, DateFormatter
import matplotlib.ticker as mticker
from mplfinance.original_flavor import candlestick_ohlc
import pandas as pd
import japanize_matplotlib


def download_price_data(symbol, interval_mode):
    period_map = {"1d": "3mo", "1wk": "1y", "1mo": "5y"}
    period = period_map.get(interval_mode, "3mo")
    return yf.download(symbol, period=period, interval=interval_mode)


def calculate_indicators(df, sma_settings, show_bbands):
    if sma_settings.get("short"):
        df['SMA5'] = df['Close'].rolling(window=5).mean()
    if sma_settings.get("mid"):
        df['SMA25'] = df['Close'].rolling(window=25).mean()
    if sma_settings.get("long"):
        df['SMA50'] = df['Close'].rolling(window=50).mean()
    if show_bbands:
        ma = df['Close'].rolling(window=25).mean()
        std = df['Close'].rolling(window=25).std()
        df['BB_Upper'] = ma + 2 * std
        df['BB_Lower'] = ma - 2 * std
    return df


def prepare_ohlc_data(df):
    df_plot = df[['Open', 'High', 'Low', 'Close']].copy()
    df_plot.reset_index(inplace=True)
    df_plot['Date'] = df_plot['Date'].apply(date2num)
    ohlc = df_plot[['Date', 'Open', 'High', 'Low', 'Close']]
    return ohlc, df_plot


def plot_chart(symbol, df, df_plot, ohlc, sma_settings, show_bbands, save_path='chart.png'):
    fig, ax = plt.subplots(figsize=(12, 6))
    fig.patch.set_facecolor('black')
    ax.set_facecolor('black')

    # 発光効果
    glow_blue   = [pe.withStroke(linewidth=1.5, foreground='lightblue')]
    glow_orange = [pe.withStroke(linewidth=1.5, foreground='navajowhite')]
    glow_purple = [pe.withStroke(linewidth=1.5, foreground='plum')]
    glow_gray   = [pe.withStroke(linewidth=1.2, foreground='lightgray')]

    # ローソク足
    candlestick_ohlc(ax, ohlc.values, width=0.4, colorup='lime', colordown='red')

    if sma_settings.get("short"):
        ax.plot(df_plot['Date'], df['SMA5'], label='5日移動平均',
                color='blue', linewidth=0.8, alpha=0.8, path_effects=glow_blue)
    if sma_settings.get("mid"):
        ax.plot(df_plot['Date'], df['SMA25'], label='25日移動平均',
                color='orange', linewidth=0.8, alpha=0.8, path_effects=glow_orange)
    if sma_settings.get("long"):
        ax.plot(df_plot['Date'], df['SMA50'], label='50日移動平均',
                color='plum', linewidth=0.8, alpha=0.8, path_effects=glow_purple)

    if show_bbands:
        ax.plot(df_plot['Date'], df['BB_Upper'], label='BB +2σ',
                linestyle='--', color='lightgray', linewidth=0.6, alpha=0.6, path_effects=glow_gray)
        ax.plot(df_plot['Date'], df['BB_Lower'], label='BB -2σ',
                linestyle='--', color='lightgray', linewidth=0.6, alpha=0.6, path_effects=glow_gray)

    ax.xaxis.set_major_formatter(DateFormatter('%Y-%m-%d'))
    ax.xaxis.set_major_locator(mticker.MaxNLocator(6))
    plt.xticks(rotation=45, color='white')
    plt.yticks(color='white')
    ax.tick_params(colors='white')
    ax.spines['bottom'].set_color('white')
    ax.spines['left'].set_color('white')
    plt.title(f"{symbol} のローソク足チャート", color='white')
    plt.xlabel("日付", color='white')
    plt.ylabel("価格 (USD)", color='white')

    plt.legend(
        loc='center left',
        bbox_to_anchor=(1.02, 0.5),
        borderaxespad=0,
        facecolor=(0, 0, 0, 0.5),
        edgecolor='white',
        labelcolor='white',
        fontsize=10
    )
    plt.tight_layout()
    plt.savefig(save_path, dpi=250, facecolor=fig.get_facecolor())
    plt.close()


# ===============================
# Streamlit アプリ本体
# ===============================
st.title("📈 株価ローソク足チャート可視化ツール")

df = pd.read_excel('./data_j.xls')
df_filter = df[df['市場・商品区分'].str.contains('内国株式')].reset_index(drop=True)
df_filter['企業コード'] = df_filter['コード'].astype(str) + '.T'
df_filter['表示名'] = df_filter['銘柄名'] + '（' + df_filter['コード'].astype(str) + '）'

selection = df_filter['表示名'].to_list()
name = st.selectbox("企業のティッカーコードを入力（例: AAPL, 7253.T）", options=selection)

select_code = df_filter[df_filter['表示名'] == name].iloc[0]
symbol_input = select_code['企業コード']
company_name = select_code['銘柄名']

#print(symbol_input, company_name)
#interval = st.selectbox("足種", options=["1d", "1wk", "1mo"], format_func=lambda x: {"1d": "日足", "1wk": "週足", "1mo": "月足"}[x])
interval = st.radio(
    "足種",
    options=["1d", "1wk", "1mo"],
    format_func=lambda x: {"1d": "日足", "1wk": "週足", "1mo": "月足"}[x],
    horizontal=True  # 横並びにする
)

show_bbands = st.radio('ボリンジャーバンドを表示しますか？', options=[True, False], horizontal=True)
print(show_bbands)
if st.button("チャート生成"):
    save_path = f"./picture/{company_name}_{interval}.png"
    try:
        if save_path in os.listdir('./picture'):
            st.image(f'./picture/{company_name}_{interval}.png', caption=f"{symbol_input} のチャート", use_container_width=True)
            st.success("キャッシュからチャートを表示しました。")
            st.stop()

        else:
            df = download_price_data(symbol_input, interval)
            if df.empty:
                st.error("データが取得できませんでした。ティッカーコードや足種を確認してください。")
            else:
                sma_settings = {"short": True, "mid": True, "long": True}
                
                df = calculate_indicators(df, sma_settings, show_bbands)
                ohlc, df_plot = prepare_ohlc_data(df)
                plot_chart(company_name, df, df_plot, ohlc, sma_settings, show_bbands, save_path=save_path)
                st.image(save_path, caption=f"{company_name} のチャート", use_container_width=True)
    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
