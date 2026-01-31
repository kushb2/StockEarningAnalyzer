"""
Streamlit Dashboard - Earnings Event Alpha Tool

Interactive dashboard for analyzing pre-earnings accumulation zones
with dual-mode support (Swing & Positional trading).
"""

import streamlit as st
import sys
from pathlib import Path
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.api.earnings_data import EarningsData
from src.api.data_fetcher import DataFetcher
from src.logic.analyzer import Analyzer


# Page config
st.set_page_config(
    page_title="Earnings Alpha Tool",
    page_icon="📈",
    layout="wide"
)

# Initialize components
@st.cache_resource
def init_components():
    """Initialize data components (cached)."""
    earnings_data = EarningsData()
    data_fetcher = DataFetcher()
    analyzer = Analyzer()
    return earnings_data, data_fetcher, analyzer


def main():
    """Main Streamlit app."""
    st.title("📈 Earnings Event Alpha Tool")
    st.markdown("*Analyze pre-earnings accumulation zones with dual-mode RVOL (Swing & Positional)*")
    
    # Initialize components
    earnings_data, data_fetcher, analyzer = init_components()
    
    # Create tabs for different views
    tab1, tab2, tab3 = st.tabs(["📊 Earnings Analysis", "🔍 Debug View", "📋 Bulk Analysis"])
    
    with tab1:
        earnings_analysis_view(earnings_data, data_fetcher, analyzer)
    
    with tab2:
        debug_view(data_fetcher)
    
    with tab3:
        bulk_analysis_view(earnings_data, data_fetcher, analyzer)


def earnings_analysis_view(earnings_data, data_fetcher, analyzer):
    """Earnings analysis view (original functionality)."""
    # Sidebar - Stock Selection
    st.sidebar.header("📊 Selection")
    
    # Get all available symbols
    all_symbols = earnings_data.get_all_symbols()
    
    if not all_symbols:
        st.error("No stocks found in earnings_dates.json")
        return
    
    # Stock selector
    selected_symbol = st.sidebar.selectbox(
        "Select Stock",
        options=all_symbols,
        index=0,
        help="Choose a stock from your watchlist"
    )
    
    # Quarter/Date selector (dynamic based on selected stock)
    try:
        available_quarters = earnings_data.get_available_quarters(selected_symbol)
        earnings_dates = earnings_data.get_earnings_dates(selected_symbol)
        
        if not available_quarters:
            st.sidebar.error(f"No earnings dates found for {selected_symbol}")
            return
        
        # Create quarter selector with date mapping
        quarter_options = {q: d for q, d in zip(available_quarters, earnings_dates)}
        
        selected_quarter = st.sidebar.selectbox(
            "Select Quarter",
            options=available_quarters,
            index=0,
            help="Choose an earnings event to analyze"
        )
        
        selected_earnings_date = quarter_options[selected_quarter]
        
    except ValueError as e:
        st.sidebar.error(str(e))
        return
    
    # Display selection info
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Current Selection:**")
    st.sidebar.info(f"**{selected_symbol}**\n\n{selected_quarter}\n\n{selected_earnings_date.strftime('%Y-%m-%d')}")
    
    # Fetch and analyze data
    with st.spinner(f"Analyzing {selected_symbol} - {selected_quarter}..."):
        analysis_result = perform_analysis(
            selected_symbol,
            selected_earnings_date,
            data_fetcher,
            earnings_data,
            analyzer
        )
    
    if analysis_result is None:
        st.error("Failed to fetch or analyze data. Please check your Kite Connect authentication.")
        return
    
    df, windows, result = analysis_result
    
    # Main area - Chart and Metrics
    st.markdown("---")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📉 Price Chart")
        chart = create_candlestick_chart(df, windows, result)
        st.plotly_chart(chart, use_container_width=True)
    
    with col2:
        st.subheader("📊 Metrics")
        display_metrics_panel(selected_symbol, selected_quarter, selected_earnings_date, result)
    
    # Footer
    st.markdown("---")
    st.caption("Earnings Event Alpha Tool | Dual-Mode Analysis (Swing & Positional)")


def debug_view(data_fetcher):
    """Debug/Bird's Eye View - 3-month stock behavior overview."""
    from datetime import datetime, timedelta
    from src.config.constants import (
        SMA_SHORT_PERIOD, SMA_MEDIUM_PERIOD, SMA_LONG_PERIOD, SMA_MAJOR_PERIOD,
        VOLUME_SMA_SHORT_PERIOD, VOLUME_SMA_MEDIUM_PERIOD,
        RSI_OVERSOLD, RSI_OVERBOUGHT,
        RSI_PERCENTILE_EXTREMELY_LOW, RSI_PERCENTILE_LOW,
        RSI_PERCENTILE_HIGH, RSI_PERCENTILE_EXTREMELY_HIGH
    )
    
    st.markdown("## 🔍 Debug View - Bird's Eye Overview")
    st.markdown("*Understand stock behavior over time: price movements, volume patterns, and momentum indicators*")
    
    # Sidebar - Stock Selection
    st.sidebar.header("🔍 Debug Settings")
    
    # Get all available symbols
    earnings_data = EarningsData()
    all_symbols = earnings_data.get_all_symbols()
    
    if not all_symbols:
        st.error("No stocks found in configuration")
        return
    
    # Stock selector
    selected_symbol = st.sidebar.selectbox(
        "Select Stock",
        options=all_symbols,
        index=0,
        key="debug_stock",
        help="Choose a stock to analyze"
    )
    
    # Date range selector
    st.sidebar.markdown("### Date Range")
    
    # Default: today - 3 months to today
    default_end = datetime.now().date()
    default_start = (datetime.now() - timedelta(days=90)).date()
    
    start_date = st.sidebar.date_input(
        "Start Date",
        value=default_start,
        max_value=default_end,
        key="debug_start"
    )
    
    end_date = st.sidebar.date_input(
        "End Date",
        value=default_end,
        min_value=start_date,
        key="debug_end"
    )
    
    # Calculate days
    days_range = (end_date - start_date).days
    st.sidebar.info(f"**Range:** {days_range} days (~{days_range//30} months)")
    
    # Fetch data
    with st.spinner(f"Fetching data for {selected_symbol}..."):
        df = data_fetcher.fetch_with_buffer(
            selected_symbol,
            pd.Timestamp(start_date),
            pd.Timestamp(end_date)
        )
    
    if df is None or df.empty:
        st.error("Failed to fetch data. Please check your Kite Connect authentication.")
        return
    
    # Filter to date range
    mask = (df['date'].dt.date >= start_date) & (df['date'].dt.date <= end_date)
    df_filtered = df[mask].copy()
    
    if df_filtered.empty:
        st.warning("No data available for the selected date range.")
        return
    
    # Display summary statistics
    st.markdown("---")
    display_debug_summary(df_filtered, selected_symbol, start_date, end_date)
    
    # Display charts
    st.markdown("---")
    display_debug_charts(df_filtered)
    
    # Display detailed data table
    st.markdown("---")
    display_debug_data_table(df_filtered)


def display_debug_summary(df, symbol, start_date, end_date):
    """Display summary statistics for the debug view."""
    st.markdown("### 📊 Summary Statistics")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    # Price statistics
    price_change = ((df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0]) * 100
    price_high = df['high'].max()
    price_low = df['low'].min()
    
    with col1:
        st.metric(
            "Price Change",
            f"{price_change:+.2f}%",
            delta=f"₹{df['close'].iloc[-1] - df['close'].iloc[0]:.2f}"
        )
    
    with col2:
        st.metric("Period High", f"₹{price_high:.2f}")
    
    with col3:
        st.metric("Period Low", f"₹{price_low:.2f}")
    
    # Volume statistics
    avg_volume = df['volume'].mean()
    max_volume = df['volume'].max()
    
    with col4:
        st.metric("Avg Volume", f"{avg_volume/1000:.0f}K")
    
    with col5:
        st.metric("Max Volume", f"{max_volume/1000:.0f}K")
    
    # RSI statistics
    st.markdown("---")
    col6, col7, col8, col9 = st.columns(4)
    
    current_rsi = df['RSI_14'].iloc[-1] if 'RSI_14' in df.columns else None
    current_rsi_pct = df['RSI_Percentile'].iloc[-1] if 'RSI_Percentile' in df.columns else None
    avg_rsi = df['RSI_14'].mean() if 'RSI_14' in df.columns else None
    
    with col6:
        if current_rsi is not None:
            st.metric("Current RSI", f"{current_rsi:.1f}")
        else:
            st.metric("Current RSI", "N/A")
    
    with col7:
        if current_rsi_pct is not None:
            st.metric("RSI Percentile", f"{current_rsi_pct:.1f}")
        else:
            st.metric("RSI Percentile", "N/A")
    
    with col8:
        if avg_rsi is not None:
            st.metric("Avg RSI", f"{avg_rsi:.1f}")
        else:
            st.metric("Avg RSI", "N/A")
    
    # Volatility
    current_atr = df['ATR_14'].iloc[-1] if 'ATR_14' in df.columns else None
    
    with col9:
        if current_atr is not None:
            st.metric("Current ATR", f"₹{current_atr:.2f}")
        else:
            st.metric("Current ATR", "N/A")


def display_debug_charts(df):
    """Display multi-panel charts for debug view."""
    from src.config.constants import (
        SMA_SHORT_PERIOD, SMA_MEDIUM_PERIOD, SMA_LONG_PERIOD, SMA_MAJOR_PERIOD,
        VOLUME_SMA_SHORT_PERIOD, VOLUME_SMA_MEDIUM_PERIOD,
        RSI_OVERSOLD, RSI_OVERBOUGHT
    )
    
    st.markdown("### 📈 Multi-Panel Analysis")
    
    # Create 4-panel chart
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.4, 0.2, 0.2, 0.2],
        subplot_titles=(
            "Price with Moving Averages",
            "Volume with SMAs",
            "RSI (14) with Percentile",
            "ATR (14) - Volatility"
        )
    )
    
    # Panel 1: Price with SMAs
    fig.add_trace(
        go.Candlestick(
            x=df['date'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name="Price",
            increasing_line_color='#26a69a',
            decreasing_line_color='#ef5350'
        ),
        row=1, col=1
    )
    
    # Add SMAs to price chart
    if 'SMA_20' in df.columns:
        fig.add_trace(
            go.Scatter(x=df['date'], y=df['SMA_20'], name=f"SMA {SMA_SHORT_PERIOD}",
                      line=dict(color='orange', width=1)),
            row=1, col=1
        )
    
    if 'SMA_50' in df.columns:
        fig.add_trace(
            go.Scatter(x=df['date'], y=df['SMA_50'], name=f"SMA {SMA_MEDIUM_PERIOD}",
                      line=dict(color='blue', width=1)),
            row=1, col=1
        )
    
    if 'SMA_100' in df.columns:
        fig.add_trace(
            go.Scatter(x=df['date'], y=df['SMA_100'], name=f"SMA {SMA_LONG_PERIOD}",
                      line=dict(color='purple', width=1)),
            row=1, col=1
        )
    
    if 'SMA_200' in df.columns:
        fig.add_trace(
            go.Scatter(x=df['date'], y=df['SMA_200'], name=f"SMA {SMA_MAJOR_PERIOD}",
                      line=dict(color='red', width=1)),
            row=1, col=1
        )
    
    # Panel 2: Volume with SMAs
    colors = ['#26a69a' if close >= open else '#ef5350' 
              for close, open in zip(df['close'], df['open'])]
    
    fig.add_trace(
        go.Bar(x=df['date'], y=df['volume'], name="Volume",
               marker_color=colors, showlegend=False),
        row=2, col=1
    )
    
    if 'Volume_SMA_20' in df.columns:
        fig.add_trace(
            go.Scatter(x=df['date'], y=df['Volume_SMA_20'], 
                      name=f"Vol SMA {VOLUME_SMA_SHORT_PERIOD}",
                      line=dict(color='orange', width=2)),
            row=2, col=1
        )
    
    if 'Volume_SMA_50' in df.columns:
        fig.add_trace(
            go.Scatter(x=df['date'], y=df['Volume_SMA_50'], 
                      name=f"Vol SMA {VOLUME_SMA_MEDIUM_PERIOD}",
                      line=dict(color='blue', width=2)),
            row=2, col=1
        )
    
    # Panel 3: RSI with Percentile
    if 'RSI_14' in df.columns:
        fig.add_trace(
            go.Scatter(x=df['date'], y=df['RSI_14'], name="RSI (14)",
                      line=dict(color='purple', width=2)),
            row=3, col=1
        )
        
        # Add RSI threshold lines
        fig.add_hline(y=RSI_OVERSOLD, line_dash="dash", line_color="green", 
                     annotation_text="Oversold (30)", row=3, col=1)
        fig.add_hline(y=RSI_OVERBOUGHT, line_dash="dash", line_color="red", 
                     annotation_text="Overbought (70)", row=3, col=1)
    
    if 'RSI_Percentile' in df.columns:
        fig.add_trace(
            go.Scatter(x=df['date'], y=df['RSI_Percentile'], name="RSI Percentile",
                      line=dict(color='cyan', width=1, dash='dot')),
            row=3, col=1
        )
    
    # Panel 4: ATR (Volatility)
    if 'ATR_14' in df.columns:
        fig.add_trace(
            go.Scatter(x=df['date'], y=df['ATR_14'], name="ATR (14)",
                      line=dict(color='orange', width=2), fill='tozeroy'),
            row=4, col=1
        )
    
    if 'ATR_Percentile' in df.columns:
        fig.add_trace(
            go.Scatter(x=df['date'], y=df['ATR_Percentile'], name="ATR Percentile",
                      line=dict(color='red', width=1, dash='dot')),
            row=4, col=1
        )
    
    # Update layout
    fig.update_layout(
        height=1200,
        hovermode='x unified',
        xaxis_rangeslider_visible=False,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    fig.update_yaxes(title_text="Price (₹)", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    fig.update_yaxes(title_text="RSI / Percentile", row=3, col=1)
    fig.update_yaxes(title_text="ATR (₹)", row=4, col=1)
    fig.update_xaxes(title_text="Date", row=4, col=1)
    
    st.plotly_chart(fig, use_container_width=True)


def display_debug_data_table(df):
    """Display detailed data table for debug view."""
    st.markdown("### 📋 Detailed Data Table")
    st.caption("Showing all indicators and calculated values")
    
    # Select relevant columns
    display_cols = [
        'date', 'open', 'high', 'low', 'close', 'volume',
        'RSI_14', 'RSI_Percentile',
        'ATR_14', 'ATR_Percentile',
        'Volume_Percentile',
        'SMA_20', 'SMA_50', 'SMA_100', 'SMA_200',
        'Volume_SMA_20', 'Volume_SMA_50',
        'Distance_SMA_50', 'Distance_SMA_100', 'Distance_SMA_200',
        'BB_Lower', 'BB_Upper', 'BB_Width'
    ]
    
    # Filter to available columns
    available_cols = [col for col in display_cols if col in df.columns]
    
    # Create display dataframe
    display_df = df[available_cols].copy()
    
    # Format date
    display_df['date'] = display_df['date'].dt.strftime('%Y-%m-%d')
    
    # Round numeric columns
    numeric_cols = display_df.select_dtypes(include=['float64', 'int64']).columns
    display_df[numeric_cols] = display_df[numeric_cols].round(2)
    
    # Display with pagination
    st.dataframe(
        display_df,
        use_container_width=True,
        height=400
    )
    
    # Download button
    csv = display_df.to_csv(index=False)
    st.download_button(
        label="📥 Download CSV",
        data=csv,
        file_name=f"debug_data_{display_df['date'].iloc[0]}_to_{display_df['date'].iloc[-1]}.csv",
        mime="text/csv"
    )


def perform_analysis(symbol, earnings_date, data_fetcher, earnings_data, analyzer):
    """Fetch data and perform analysis."""
    try:
        # Get trading days from cache (or fetch minimal data first)
        print("earnings_date", earnings_date, "symbol", symbol)
        trading_days = data_fetcher.get_trading_days(symbol)

        if not trading_days:
            # No cache, fetch 1 year of data first
            df_initial = data_fetcher.fetch_ohlcv(symbol)
            if df_initial is None or df_initial.empty:
                return None
            trading_days = df_initial['date'].tolist()
        
        # Calculate analysis windows
        windows = earnings_data.get_analysis_windows(earnings_date, trading_days)
        print("windows", windows)
        
        # Fetch data with buffer
        obs_start = windows['observation']['start']
        obs_end = windows['observation']['end']
        print("obs_start", obs_start, "obs_end", obs_end)
        
        if obs_start is None or obs_end is None:
            st.error("Unable to calculate observation window. Insufficient trading days data.")
            return None
        
        df = data_fetcher.fetch_with_buffer(symbol, obs_start, obs_end)
        
        if df is None or df.empty:
            return None
        
        # Perform analysis
        result = analyzer.analyze_earnings_event(df, windows)
        
        return df, windows, result
        
    except Exception as e:
        st.error(f"Error during analysis: {e}")
        return None


def create_candlestick_chart(df, windows, result):
    """Create candlestick chart with volume and markers."""
    # Filter to observation period
    obs_start = windows['observation']['start']
    obs_end = windows['observation']['end']
    
    mask = (df['date'].dt.date >= obs_start.date()) & (df['date'].dt.date <= obs_end.date())
    chart_df = df[mask].copy()
    
    # Create subplots: candlestick + volume
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3],
        subplot_titles=("Price", "Volume")
    )
    
    # Candlestick chart with RSI in hover info
    # Prepare custom hover text with RSI
    hover_text = []
    for idx, row in chart_df.iterrows():
        rsi_value = row.get('RSI_14', None)
        rsi_text = f"<br>RSI: {rsi_value:.1f}" if pd.notna(rsi_value) else "<br>RSI: N/A"
        hover_text.append(
            f"Date: {row['date'].strftime('%Y-%m-%d')}<br>"
            f"Open: ₹{row['open']:.2f}<br>"
            f"High: ₹{row['high']:.2f}<br>"
            f"Low: ₹{row['low']:.2f}<br>"
            f"Close: ₹{row['close']:.2f}"
            f"{rsi_text}"
        )
    
    fig.add_trace(
        go.Candlestick(
            x=chart_df['date'],
            open=chart_df['open'],
            high=chart_df['high'],
            low=chart_df['low'],
            close=chart_df['close'],
            name="Price",
            increasing_line_color='#26a69a',
            decreasing_line_color='#ef5350',
            hovertext=hover_text,
            hoverinfo='text'
        ),
        row=1, col=1
    )
    
    # Volume bars
    colors = ['#26a69a' if close >= open else '#ef5350' 
              for close, open in zip(chart_df['close'], chart_df['open'])]
    
    fig.add_trace(
        go.Bar(
            x=chart_df['date'],
            y=chart_df['volume'],
            name="Volume",
            marker_color=colors,
            showlegend=False
        ),
        row=2, col=1
    )
    
    # Add markers for key dates
    markers = []
    
    # Accumulation days - use typical price for marker position
    if result['accumulation_days']:
        for acc_day in result['accumulation_days']:
            markers.append({
                'date': acc_day['date'],
                'price': acc_day['typical_price'],  # Use typical price instead of low
                'label': 'Dip',
                'color': 'blue'
            })
    
    # Reference High
    if result['reference_high']['date'] is not None:
        markers.append({
            'date': result['reference_high']['date'],
            'price': result['reference_high']['price'],
            'label': 'Ref High',
            'color': 'purple'
        })
    
    # T-1
    if windows['t_minus_1'] is not None:
        t_minus_1_row = chart_df[chart_df['date'].dt.date == windows['t_minus_1'].date()]
        if not t_minus_1_row.empty:
            markers.append({
                'date': windows['t_minus_1'],
                'price': t_minus_1_row.iloc[0]['close'],
                'label': 'T-1',
                'color': 'orange'
            })
    
    # T+2
    if windows['t_plus_2'] is not None:
        t_plus_2_row = chart_df[chart_df['date'].dt.date == windows['t_plus_2'].date()]
        if not t_plus_2_row.empty:
            markers.append({
                'date': windows['t_plus_2'],
                'price': t_plus_2_row.iloc[0]['close'],
                'label': 'T+2',
                'color': 'green'
            })
    
    # T+5
    if windows['t_plus_5'] is not None:
        t_plus_5_row = chart_df[chart_df['date'].dt.date == windows['t_plus_5'].date()]
        if not t_plus_5_row.empty:
            markers.append({
                'date': windows['t_plus_5'],
                'price': t_plus_5_row.iloc[0]['close'],
                'label': 'T+5',
                'color': 'cyan'
            })
    
    # T+10
    if windows['t_plus_10'] is not None:
        t_plus_10_row = chart_df[chart_df['date'].dt.date == windows['t_plus_10'].date()]
        if not t_plus_10_row.empty:
            markers.append({
                'date': windows['t_plus_10'],
                'price': t_plus_10_row.iloc[0]['close'],
                'label': 'T+10',
                'color': 'magenta'
            })
    
    # T+20
    if windows['t_plus_20'] is not None:
        t_plus_20_row = chart_df[chart_df['date'].dt.date == windows['t_plus_20'].date()]
        if not t_plus_20_row.empty:
            markers.append({
                'date': windows['t_plus_20'],
                'price': t_plus_20_row.iloc[0]['close'],
                'label': 'T+20',
                'color': 'red'
            })
    
    # Add markers to chart
    for marker in markers:
        fig.add_trace(
            go.Scatter(
                x=[marker['date']],
                y=[marker['price']],
                mode='markers+text',
                marker=dict(size=12, color=marker['color'], symbol='diamond'),
                text=[marker['label']],
                textposition='top center',
                name=marker['label'],
                showlegend=True
            ),
            row=1, col=1
        )
    
    # Update layout
    obs_end_str = obs_end.strftime('%Y-%m-%d')
    fig.update_layout(
        title=f"Observation Period: T-20 to Current Date ({obs_end_str})",
        xaxis_title="Date",
        yaxis_title="Price",
        height=700,
        hovermode='x unified',
        xaxis_rangeslider_visible=False
    )
    
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    
    return fig


def display_metrics_panel(symbol, quarter, earnings_date, result):
    """Display metrics data panel."""
    # Stock Info
    st.markdown("### Stock Information")
    st.markdown(f"**Symbol:** {symbol}")
    st.markdown(f"**Quarter:** {quarter}")
    st.markdown(f"**Earnings Date:** {earnings_date.strftime('%Y-%m-%d')}")
    
    st.markdown("---")
    
    # Accumulation Zone
    st.markdown("### 🎯 Accumulation Zone")
    
    if result['accumulation_price'] is not None:
        st.metric("Accumulation Price (Typical)", f"₹{result['accumulation_price']:.2f}")
        st.caption("Typical Price = (Low + High + Close) / 3")
        
        # Accumulation Days Table
        if result['accumulation_days']:
            st.markdown("**Accumulation Days:**")
            
            acc_data = []
            for acc_day in result['accumulation_days']:
                acc_data.append({
                    "Date": acc_day['date'].strftime('%Y-%m-%d'),
                    "Low": f"₹{acc_day['low']:.2f}",
                    "High": f"₹{acc_day['high']:.2f}",
                    "Close": f"₹{acc_day['close']:.2f}",
                    "Typical": f"₹{acc_day['typical_price']:.2f}",
                    "RVOL_20": f"{acc_day['rvol_20']:.2f}" if acc_day['rvol_20'] is not None else "N/A",
                    "RVOL_50": f"{acc_day['rvol_50']:.2f}" if acc_day['rvol_50'] is not None else "N/A",
                    "RSI": f"{acc_day['rsi']:.1f}" if acc_day['rsi'] is not None else "N/A",
                    "RSI %ile": f"{acc_day['rsi_percentile']:.1f}" if acc_day.get('rsi_percentile') is not None else "N/A",
                    "Days Before": acc_day['days_before_earnings']
                })
            
            acc_df = pd.DataFrame(acc_data)
            st.dataframe(acc_df, use_container_width=True, hide_index=True)
    else:
        st.warning("No accumulation zone detected")
    
    st.markdown("---")
    
    # Reference High & Drawdown
    st.markdown("### 📈 Reference High & Drawdown")
    
    if result['reference_high']['price'] is not None:
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("Reference High", f"₹{result['reference_high']['price']:.2f}")
        with col_b:
            if result['reference_high']['date'] is not None:
                st.caption(f"Date: {result['reference_high']['date'].strftime('%Y-%m-%d')}")
        
        if result['max_drawdown_pct'] is not None:
            st.metric(
                "Max Drawdown",
                f"{result['max_drawdown_pct']:.2f}%",
                delta=None,
                delta_color="inverse"
            )
    else:
        st.warning("Reference high not available")
    
    st.markdown("---")
    
    # Returns
    st.markdown("### 💰 Returns Analysis")
    
    returns = result['returns']
    
    # Strategy Returns
    st.markdown("**Strategy Returns:**")
    col1, col2 = st.columns(2)
    
    with col1:
        run_up = returns['run_up']
        if run_up is not None:
            st.metric("Run-Up Trade", f"{run_up:.2f}%", help="Dip → T-1")
        else:
            st.metric("Run-Up Trade", "N/A")
    
    with col2:
        event = returns['event']
        if event is not None:
            st.metric("Event Trade", f"{event:.2f}%", help="T-1 → T+2")
        else:
            st.metric("Event Trade", "N/A")
    
    # Fixed-Interval Exits
    st.markdown("**Fixed-Interval Exits (T+0 to T+6):**")
    st.caption("Returns from accumulation price using different exit price methods")
    
    exit_data = []
    for day in range(0, 7):  # T+0 to T+6
        close_return = returns.get(f'profit_t{day}_close')
        low_return = returns.get(f'profit_t{day}_low')
        high_return = returns.get(f'profit_t{day}_high')
        typical_return = returns.get(f'profit_t{day}_typical')
        
        exit_data.append({
            "Day": f"T+{day}",
            "Close": f"{close_return:.2f}%" if close_return is not None else "N/A",
            "Low": f"{low_return:.2f}%" if low_return is not None else "N/A",
            "High": f"{high_return:.2f}%" if high_return is not None else "N/A",
            "Typical": f"{typical_return:.2f}%" if typical_return is not None else "N/A"
        })
    
    exit_df = pd.DataFrame(exit_data)
    st.dataframe(exit_df, use_container_width=True, hide_index=True)
    
    st.caption("**Close**: Standard close price | **Low**: Worst case | **High**: Best case | **Typical**: (L+H+C)/3")
    
    # Interpretation hints
    st.markdown("---")
    st.markdown("### 💡 Interpretation")
    st.caption("**RVOL_20**: Tactical/Swing signal (monthly liquidity)")
    st.caption("**RVOL_50**: Strategic/Positional signal (quarterly liquidity)")
    st.caption("**RSI**: 14-period momentum (0-100, <30 oversold, >70 overbought)")
    st.caption("**RSI %ile**: Relative RSI vs 252-day history (0-100)")
    st.caption("  • 0-20: Extremely oversold historically")
    st.caption("  • 20-40: Below average")
    st.caption("  • 40-60: Average range")
    st.caption("  • 60-80: Above average")
    st.caption("  • 80-100: Extremely overbought historically")
    st.caption("**High RVOL + Low Price**: Potential accumulation (institutions buying)")
    st.caption("**Low RVOL + Low Price**: Drift/trap (no support, avoid)")


def bulk_analysis_view(earnings_data, data_fetcher, analyzer):
    """Bulk Analysis View - Analyze all stocks and quarters to validate hypothesis."""
    st.markdown("## 📋 Bulk Analysis - Hypothesis Validation")
    st.markdown("*Analyze all stocks and quarters to identify patterns and optimal entry/exit points*")
    
    # Sidebar controls
    st.sidebar.header("📋 Bulk Analysis Settings")
    
    # Get all symbols
    all_symbols = earnings_data.get_all_symbols()
    
    # Stock selection
    selected_stocks = st.sidebar.multiselect(
        "Select Stocks",
        options=all_symbols,
        default=all_symbols[:5] if len(all_symbols) > 5 else all_symbols,
        help="Choose stocks to analyze (default: first 5)"
    )
    
    if not selected_stocks:
        st.warning("Please select at least one stock to analyze.")
        return
    
    # Analysis button
    if st.sidebar.button("🚀 Run Bulk Analysis", type="primary"):
        run_bulk_analysis(selected_stocks, earnings_data, data_fetcher, analyzer)
    else:
        st.info("👈 Select stocks and click 'Run Bulk Analysis' to start")


def run_bulk_analysis(selected_stocks, earnings_data, data_fetcher, analyzer):
    """Execute bulk analysis for selected stocks."""
    results = []
    
    # Progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_items = sum([len(earnings_data.get_earnings_dates(symbol)) for symbol in selected_stocks])
    current_item = 0
    
    # Analyze each stock and quarter
    for symbol in selected_stocks:
        try:
            earnings_dates = earnings_data.get_earnings_dates(symbol)
            quarters = earnings_data.get_available_quarters(symbol)
            
            for earnings_date, quarter in zip(earnings_dates, quarters):
                current_item += 1
                status_text.text(f"Analyzing {symbol} - {quarter} ({current_item}/{total_items})...")
                progress_bar.progress(current_item / total_items)
                
                try:
                    # Fetch and analyze
                    trading_days = data_fetcher.get_trading_days(symbol)
                    if not trading_days:
                        df_initial = data_fetcher.fetch_ohlcv(symbol)
                        if df_initial is None or df_initial.empty:
                            continue
                        trading_days = df_initial['date'].tolist()
                    
                    windows = earnings_data.get_analysis_windows(earnings_date, trading_days)
                    
                    obs_start = windows['observation']['start']
                    obs_end = windows['observation']['end']
                    
                    if obs_start is None or obs_end is None:
                        continue
                    
                    df = data_fetcher.fetch_with_buffer(symbol, obs_start, obs_end)
                    
                    if df is None or df.empty:
                        continue
                    
                    result = analyzer.analyze_earnings_event(df, windows)
                    
                    # Extract key metrics
                    if result['accumulation_price'] is not None and result['accumulation_days']:
                        # Get first accumulation day (earliest)
                        first_acc_day = min(result['accumulation_days'], key=lambda x: x['date'])
                        
                        # Calculate best exit day based on returns
                        best_exit_day = None
                        best_exit_return = None
                        
                        for day in range(0, 7):
                            close_return = result['returns'].get(f'profit_t{day}_close')
                            if close_return is not None:
                                if best_exit_return is None or close_return > best_exit_return:
                                    best_exit_return = close_return
                                    best_exit_day = f"T+{day}"
                        
                        results.append({
                            "Symbol": symbol,
                            "Quarter": quarter,
                            "Earnings Date": earnings_date.strftime('%Y-%m-%d'),
                            "Acc Price": result['accumulation_price'],
                            "Days Before": first_acc_day['days_before_earnings'],
                            "Num Acc Days": len(result['accumulation_days']),
                            "Avg RVOL_20": sum([d['rvol_20'] for d in result['accumulation_days'] if d['rvol_20'] is not None]) / len([d for d in result['accumulation_days'] if d['rvol_20'] is not None]) if any(d['rvol_20'] is not None for d in result['accumulation_days']) else None,
                            "Avg RVOL_50": sum([d['rvol_50'] for d in result['accumulation_days'] if d['rvol_50'] is not None]) / len([d for d in result['accumulation_days'] if d['rvol_50'] is not None]) if any(d['rvol_50'] is not None for d in result['accumulation_days']) else None,
                            "Avg RSI": sum([d['rsi'] for d in result['accumulation_days'] if d['rsi'] is not None]) / len([d for d in result['accumulation_days'] if d['rsi'] is not None]) if any(d['rsi'] is not None for d in result['accumulation_days']) else None,
                            "Ref High": result['reference_high']['price'],
                            "Drawdown %": result['max_drawdown_pct'],
                            "Run-Up %": result['returns']['run_up'],
                            "Event %": result['returns']['event'],
                            "T+0 %": result['returns'].get('profit_t0_close'),
                            "T+1 %": result['returns'].get('profit_t1_close'),
                            "T+2 %": result['returns'].get('profit_t2_close'),
                            "T+3 %": result['returns'].get('profit_t3_close'),
                            "T+4 %": result['returns'].get('profit_t4_close'),
                            "T+5 %": result['returns'].get('profit_t5_close'),
                            "T+6 %": result['returns'].get('profit_t6_close'),
                            "Best Exit": best_exit_day,
                            "Best Return %": best_exit_return
                        })
                
                except Exception as e:
                    st.warning(f"Error analyzing {symbol} - {quarter}: {e}")
                    continue
        
        except Exception as e:
            st.warning(f"Error processing {symbol}: {e}")
            continue
    
    # Clear progress indicators
    progress_bar.empty()
    status_text.empty()
    
    # Display results
    if not results:
        st.error("No results found. Please check your data and try again.")
        return
    
    st.success(f"✅ Analysis complete! Found {len(results)} valid accumulation events.")
    
    # Convert to DataFrame
    df_results = pd.DataFrame(results)
    
    # Display summary statistics
    display_bulk_summary(df_results)
    
    # Display detailed table
    st.markdown("---")
    st.markdown("### 📊 Detailed Results")
    display_bulk_table(df_results)
    
    # Display insights
    st.markdown("---")
    display_bulk_insights(df_results)


def display_bulk_summary(df):
    """Display summary statistics for bulk analysis."""
    st.markdown("### 📈 Summary Statistics")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Events", len(df))
    
    with col2:
        avg_drawdown = df['Drawdown %'].mean()
        st.metric("Avg Drawdown", f"{avg_drawdown:.2f}%")
    
    with col3:
        avg_run_up = df['Run-Up %'].mean()
        st.metric("Avg Run-Up", f"{avg_run_up:.2f}%")
    
    with col4:
        avg_best_return = df['Best Return %'].mean()
        st.metric("Avg Best Return", f"{avg_best_return:.2f}%")
    
    with col5:
        win_rate = (df['Best Return %'] > 0).sum() / len(df) * 100
        st.metric("Win Rate", f"{win_rate:.1f}%")
    
    # Additional metrics
    st.markdown("---")
    col6, col7, col8, col9 = st.columns(4)
    
    with col6:
        avg_days_before = df['Days Before'].mean()
        st.metric("Avg Days Before Earnings", f"{avg_days_before:.1f}")
    
    with col7:
        avg_rvol_20 = df['Avg RVOL_20'].mean()
        st.metric("Avg RVOL_20", f"{avg_rvol_20:.2f}")
    
    with col8:
        avg_rvol_50 = df['Avg RVOL_50'].mean()
        st.metric("Avg RVOL_50", f"{avg_rvol_50:.2f}")
    
    with col9:
        avg_rsi = df['Avg RSI'].mean()
        st.metric("Avg RSI", f"{avg_rsi:.1f}")


def display_bulk_table(df):
    """Display detailed bulk analysis table."""
    # Format numeric columns
    display_df = df.copy()
    
    # Round numeric columns
    numeric_cols = ['Acc Price', 'Ref High', 'Drawdown %', 'Run-Up %', 'Event %',
                    'T+0 %', 'T+1 %', 'T+2 %', 'T+3 %', 'T+4 %', 'T+5 %', 'T+6 %',
                    'Best Return %', 'Avg RVOL_20', 'Avg RVOL_50', 'Avg RSI']
    
    for col in numeric_cols:
        if col in display_df.columns:
            display_df[col] = display_df[col].round(2)
    
    # Color code returns
    def color_returns(val):
        if pd.isna(val):
            return ''
        try:
            if float(val) > 0:
                return 'background-color: #d4edda'  # Light green
            elif float(val) < 0:
                return 'background-color: #f8d7da'  # Light red
        except:
            pass
        return ''
    
    # Apply styling
    styled_df = display_df.style.applymap(
        color_returns,
        subset=['Run-Up %', 'Event %', 'T+0 %', 'T+1 %', 'T+2 %', 'T+3 %', 
                'T+4 %', 'T+5 %', 'T+6 %', 'Best Return %']
    )
    
    st.dataframe(styled_df, use_container_width=True, height=600)
    
    # Download button
    csv = display_df.to_csv(index=False)
    st.download_button(
        label="📥 Download CSV",
        data=csv,
        file_name=f"bulk_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )


def display_bulk_insights(df):
    """Display insights and patterns from bulk analysis."""
    st.markdown("### 💡 Key Insights")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📊 Best Exit Day Distribution")
        exit_day_counts = df['Best Exit'].value_counts().sort_index()
        st.bar_chart(exit_day_counts)
        
        st.markdown("#### 🎯 Optimal Exit Strategy")
        most_common_exit = df['Best Exit'].mode()[0] if not df['Best Exit'].mode().empty else "N/A"
        st.info(f"Most profitable exit day: **{most_common_exit}**")
        
        # Show average return for each exit day
        st.markdown("**Average Returns by Exit Day:**")
        for day in range(0, 7):
            col_name = f'T+{day} %'
            if col_name in df.columns:
                avg_return = df[col_name].mean()
                st.caption(f"T+{day}: {avg_return:.2f}%")
    
    with col2:
        st.markdown("#### 📉 Drawdown Analysis")
        st.markdown(f"**Min Drawdown:** {df['Drawdown %'].min():.2f}%")
        st.markdown(f"**Max Drawdown:** {df['Drawdown %'].max():.2f}%")
        st.markdown(f"**Median Drawdown:** {df['Drawdown %'].median():.2f}%")
        
        st.markdown("#### 🔍 RVOL Patterns")
        high_rvol_20 = (df['Avg RVOL_20'] > 1.5).sum()
        high_rvol_50 = (df['Avg RVOL_50'] > 1.5).sum()
        st.markdown(f"**Events with RVOL_20 > 1.5:** {high_rvol_20} ({high_rvol_20/len(df)*100:.1f}%)")
        st.markdown(f"**Events with RVOL_50 > 1.5:** {high_rvol_50} ({high_rvol_50/len(df)*100:.1f}%)")
        
        # Correlation between RVOL and returns
        if df['Avg RVOL_20'].notna().any() and df['Best Return %'].notna().any():
            corr = df['Avg RVOL_20'].corr(df['Best Return %'])
            st.markdown(f"**RVOL_20 vs Best Return correlation:** {corr:.3f}")
    
    # Hypothesis validation
    st.markdown("---")
    st.markdown("### ✅ Hypothesis Validation")
    
    # Check if hypothesis holds
    positive_returns = (df['Best Return %'] > 0).sum()
    total_events = len(df)
    success_rate = positive_returns / total_events * 100
    
    if success_rate > 60:
        st.success(f"✅ **Hypothesis VALIDATED**: {success_rate:.1f}% of accumulation events resulted in positive returns!")
    elif success_rate > 50:
        st.info(f"⚠️ **Hypothesis PARTIALLY VALIDATED**: {success_rate:.1f}% success rate (slightly better than random)")
    else:
        st.warning(f"❌ **Hypothesis NOT VALIDATED**: Only {success_rate:.1f}% success rate")
    
    # Key findings
    st.markdown("**Key Findings:**")
    st.markdown(f"- Average accumulation starts **{df['Days Before'].mean():.1f} days** before earnings")
    st.markdown(f"- Average drawdown from reference high: **{df['Drawdown %'].mean():.2f}%**")
    st.markdown(f"- Average run-up to T-1: **{df['Run-Up %'].mean():.2f}%**")
    st.markdown(f"- Best average return: **{df['Best Return %'].mean():.2f}%** at **{df['Best Exit'].mode()[0] if not df['Best Exit'].mode().empty else 'N/A'}**")


if __name__ == "__main__":
    main()
