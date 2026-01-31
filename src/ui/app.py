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
    
    # Candlestick chart
    fig.add_trace(
        go.Candlestick(
            x=chart_df['date'],
            open=chart_df['open'],
            high=chart_df['high'],
            low=chart_df['low'],
            close=chart_df['close'],
            name="Price",
            increasing_line_color='#26a69a',
            decreasing_line_color='#ef5350'
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
    
    # Accumulation days
    if result['accumulation_days']:
        for acc_day in result['accumulation_days']:
            markers.append({
                'date': acc_day['date'],
                'price': acc_day['low'],
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
    fig.update_layout(
        title=f"Observation Period: T-20 to T+40",
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
        st.metric("Accumulation Price", f"₹{result['accumulation_price']:.2f}")
        
        # Accumulation Days Table
        if result['accumulation_days']:
            st.markdown("**Accumulation Days:**")
            
            acc_data = []
            for acc_day in result['accumulation_days']:
                acc_data.append({
                    "Date": acc_day['date'].strftime('%Y-%m-%d'),
                    "Low": f"₹{acc_day['low']:.2f}",
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
    st.markdown("**Fixed-Interval Exits:**")
    
    exit_data = []
    for interval, label in [
        ('profit_t2', 'T+2'),
        ('profit_t5', 'T+5'),
        ('profit_t10', 'T+10'),
        ('profit_t20', 'T+20')
    ]:
        value = returns[interval]
        exit_data.append({
            "Exit": label,
            "Return": f"{value:.2f}%" if value is not None else "N/A"
        })
    
    exit_df = pd.DataFrame(exit_data)
    st.dataframe(exit_df, use_container_width=True, hide_index=True)
    
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


if __name__ == "__main__":
    main()
