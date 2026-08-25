"""Institutional Market Scanner and Trading Dashboard
Enterprise-grade quantitative analysis platform with Kalman Filter Arbitrage,
ATR Volatility Breakout, Order Flow Imbalance, and Composite Certainty Scoring.
"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from pykalman import KalmanFilter
import warnings

warnings.filterwarnings('ignore')

# ============================================================================
# ACCESS CONTROL SYSTEM
# ============================================================================

# Admin credentials - CHANGE THESE IN PRODUCTION
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "InstQ2024!"

def check_access():
    """Verify user credentials before showing dashboard"""
    st.set_page_config(
        page_title="Institutional Market Scanner",
        page_icon="🏦",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    if 'authenticated' not in st.session_state:
        st.session_state['authenticated'] = False
    
    if st.session_state['authenticated']:
        return True
    
    st.markdown("""
    <style>
    .login-container {
        padding: 2rem;
        border-radius: 10px;
        background-color: #1e1e1e;
        margin-top: 5rem;
    }
    .login-title {
        color: #00d4aa;
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown('<div class="login-title">🏦 Institutional Access</div>', unsafe_allow_html=True)
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.button("Authenticate", use_container_width=True):
            if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
                st.session_state['authenticated'] = True
                st.rerun()
            else:
                st.error("Invalid credentials. Access denied.")
                return False
        
        st.markdown('</div>', unsafe_allow_html=True)
        st.info("Contact your administrator for access credentials.")
        return False
    return True

# ============================================================================
# QUANTITATIVE STRATEGY ENGINES
# ============================================================================

class KalmanArbitrageEngine:
    """Advanced Kalman Filter for statistical arbitrage detection"""
    
    def __init__(self, transition_cov=0.01, observation_cov=0.5):
        self.transition_cov = transition_cov
        self.observation_cov = observation_cov
        self.kf = None
    
    def calculate_zscore(self, prices, lookback=30):
        """Calculate dynamic z-score using Kalman Filter state estimates"""
        if len(prices) < lookback:
            return 0.0, 0.0
        
        # Initialize and fit Kalman Filter
        initial_state = prices[0]
        self.kf = KalmanFilter(
            initial_state_mean=initial_state,
            initial_state_covariance=1.0,
            transition_matrices=[1],
            observation_matrices=[1],
            transition_covariance=self.transition_cov,
            observation_covariance=self.observation_cov
        )
        
        # Get filtered state means
        state_means, _ = self.kf.filter(prices[:lookback])
        filtered_state = state_means[-1, 0]
        
        # Calculate standard deviation of price vs state
        std_dev = np.std(prices[-lookback:] - state_means.flatten())
        
        if std_dev == 0:
            return 0.0, 0.0
        
        # Z-score = current deviation from equilibrium
        zscore = (prices[-1] - filtered_state) / std_dev
        
        return zscore, filtered_state
    
    def generate_signal(self, zscore):
        """Generate signal based on z-score thresholds"""
        if zscore < -2.0:
            return "STRONG BUY", 1.0
        elif zscore < -1.0:
            return "BUY", 0.7
        elif zscore > 2.0:
            return "STRONG SELL", 1.0
        elif zscore > 1.0:
            return "SELL", 0.7
        else:
            return "HOLD", 0.3

class ATRBreakoutEngine:
    """Institutional ATR Channel Breakout with volume confirmation"""
    
    def __init__(self, period=14, multiplier=2.0, volume_period=20):
        self.period = period
        self.multiplier = multiplier
        self.volume_period = volume_period
    
    def calculate_atr(self, df, period=14):
        """Calculate Average True Range"""
        high = df['High'].values
        low = df['Low'].values
        close = df['Close'].values
        
        tr = np.zeros(len(close))
        tr[0] = high[0] - low[0]
        
        for i in range(1, len(close)):
            tr[i] = max(
                high[i] - low[i],
                abs(high[i] - close[i-1]),
                abs(low[i] - close[i-1])
            )
        
        atr = pd.Series(tr).rolling(window=period).mean().values
        return atr
    
    def detect_breakout(self, df):
        """Detect volatility breakouts with volume confirmation"""
        if len(df) < self.period + self.volume_period:
            return "HOLD", 0.0
        
        atr = self.calculate_atr(df, self.period)
        volume = df['Volume'].values
        close = df['Close'].values
        
        # Volume ratio (current vs average)
        avg_volume = np.mean(volume[-self.volume_period:])
        current_volume = volume[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        
        # Upper and lower channels
        upper_channel = close[-1] + (self.multiplier * atr[-1])
        lower_channel = close[-1] - (self.multiplier * atr[-1])
        
        # Breakout detection
        if close[-1] > upper_channel and volume_ratio > 1.2:
            return "BUY", min(volume_ratio / 2.0, 1.0)
        elif close[-1] < lower_channel and volume_ratio > 1.2:
            return "SELL", min(volume_ratio / 2.0, 1.0)
        else:
            # Check for channel squeeze
            atr_pct = (atr[-1] / close[-1]) * 100
            if atr_pct < 1.0:
                return "HOLD", 0.2
            return "HOLD", 0.1

class OrderFlowImbalanceEngine:
    """Fair Value Gap and institutional liquidity detection"""
    
    def __init__(self, lookback=10):
        self.lookback = lookback
    
    def find_fair_value_gaps(self, df):
        """Identify Fair Value Gaps in price structure"""
        if len(df) < 20:
            return 0.0, 0.0
        
        high = df['High'].values
        low = df['Low'].values
        close = df['Close'].values
        
        # Detect FVG (3-candle pattern)
        bullish_fvg = False
        bearish_fvg = False
        
        for i in range(len(df) - 3, len(df) - 1):
            # Bullish FVG: gap between low[i+2] and high[i]
            if low[i+2] > high[i]:
                bullish_fvg = True
            # Bearish FVG: gap between high[i+2] and low[i]
            if high[i+2] < low[i]:
                bearish_fvg = True
        
        # Calculate order flow imbalance
        buy_volume = 0
        sell_volume = 0
        for i in range(max(0, len(df) - self.lookback), len(df)):
            if close[i] > df['Open'].values[i]:
                buy_volume += df['Volume'].values[i]
            else:
                sell_volume += df['Volume'].values[i]
        
        total_volume = buy_volume + sell_volume
        if total_volume == 0:
            return 0.0, 0.0
        
        imbalance_ratio = (buy_volume - sell_volume) / total_volume
        
        if bullish_fvg and imbalance_ratio > 0.3:
            return "BUY", imbalance_ratio
        elif bearish_fvg and imbalance_ratio < -0.3:
            return "SELL", abs(imbalance_ratio)
        else:
            return "HOLD", abs(imbalance_ratio) * 0.5

class CompositeScorer:
    """Unified scoring engine for composite signal generation"""
    
    def __init__(self):
        self.weights = {
            'kalman': 0.4,
            'atr': 0.35,
            'orderflow': 0.25
        }
        
        self.signal_scores = {
            'STRONG BUY': 2.0,
            'BUY': 1.0,
            'HOLD': 0.0,
            'SELL': -1.0,
            'STRONG SELL': -2.0
        }
    
    def calculate_composite_score(self, signals):
        """Calculate weighted composite score with certainty"""
        total_score = 0.0
        total_certainty = 0.0
        
        for strategy, signal in signals.items():
            if signal['signal'] in self.signal_scores:
                weight = self.weights.get(strategy, 0)
                score = self.signal_scores[signal['signal']]
                certainty = signal['certainty']
                
                total_score += weight * score * certainty
                total_certainty += weight * certainty
        
        if total_certainty == 0:
            return "HOLD", 0.0
        
        # Normalize to percentage
        normalized_score = total_score / 2.0
        certainty_pct = min(abs(normalized_score) * 100, 100.0)
        
        # Determine final signal
        if normalized_score > 0.7:
            final_signal = "STRONG BUY"
        elif normalized_score > 0.3:
            final_signal = "BUY"
        elif normalized_score < -0.7:
            final_signal = "STRONG SELL"
        elif normalized_score < -0.3:
            final_signal = "SELL"
        else:
            final_signal = "HOLD"
        
        return final_signal, certainty_pct

# ============================================================================
# DATA FETCHING AND PROCESSING
# ============================================================================

def fetch_market_data(ticker, period="1mo", interval="1d"):
    """Safely fetch historical data from Yahoo Finance"""
    try:
        data = yf.download(ticker, period=period, interval=interval, progress=False)
        if data.empty:
            return None
        
        # Flatten MultiIndex columns safely
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        
        # Ensure all required columns exist
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in required_cols:
            if col not in data.columns:
                data[col] = np.nan
        
        return data.dropna()
    except Exception as e:
        st.error(f"Data fetch error for {ticker}: {str(e)}")
        return None

def get_live_price(ticker):
    """Get current live price for ticker"""
    try:
        ticker_data = yf.Ticker(ticker)
        hist = ticker_data.history(period="1d")
        if not hist.empty:
            return hist['Close'].iloc[-1]
        return None
    except Exception:
        return None

# ============================================================================
# VISUALIZATION FUNCTIONS
# ============================================================================

def create_price_chart(df, ticker):
    """Create interactive price chart with indicators"""
    fig = make_subplots(
        rows=3, cols=1,
        row_heights=[0.6, 0.2, 0.2],
        vertical_spacing=0.03
    )
    
    # Price candlesticks
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name="Price",
            increasing_line_color='#00d4aa',
            decreasing_line_color='#ff4d4d'
        ),
        row=1, col=1
    )
    
    # Volume bars
    colors = ['#00d4aa' if df['Close'].iloc[i] >= df['Open'].iloc[i] 
              else '#ff4d4d' for i in range(len(df))]
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df['Volume'],
            name="Volume",
            marker_color=colors,
            opacity=0.3
        ),
        row=2, col=1
    )
    
    # Simple moving averages
    if len(df) >= 20:
        sma20 = df['Close'].rolling(window=20).mean()
        fig.add_trace(
            go.Scatter(
                x=df.index, y=sma20,
                name="SMA 20",
                line=dict(color='#ffd700', width=1.5)
            ),
            row=1, col=1
        )
    
    if len(df) >= 50:
        sma50 = df['Close'].rolling(window=50).mean()
        fig.add_trace(
            go.Scatter(
                x=df.index, y=sma50,
                name="SMA 50",
                line=dict(color='#ff69b4', width=1.5)
            ),
            row=1, col=1
        )
    
    # RSI
    if len(df) >= 14:
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        fig.add_trace(
            go.Scatter(
                x=df.index, y=rsi,
                name="RSI",
                line=dict(color='#ffffff', width=1.5)
            ),
            row=3, col=1
        )
        
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)
    
    fig.update_layout(
        title=f"{ticker} - Institutional Analysis",
        xaxis_rangeslider_visible=False,
        height=800,
        showlegend=False,
        paper_bgcolor='#0e1117',
        plot_bgcolor='#0e1117',
        font=dict(color='#ffffff'),
        template="plotly_dark"
    )
    
    return fig

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main application entry point"""
    
    # Access control
    if not check_access():
        return
    
    # Custom CSS for premium look
    st.markdown("""
    <style>
    .main-header {
        color: #00d4aa;
        font-size: 2rem;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    .signal-box {
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    .metric-label {
        color: #8b949e;
        font-size: 0.85rem;
    }
    .metric-value {
        color: #ffffff;
        font-size: 1.5rem;
        font-weight: bold;
    }
    .sidebar-header {
        color: #00d4aa;
        font-size: 1.2rem;
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Sidebar configuration
    with st.sidebar:
        st.markdown('<div class="sidebar-header">🏦 Scanner Configuration</div>', unsafe_allow_html=True)
        
        # Asset selector
        available_assets = {
            "Bitcoin": "BTC-USD",
            "Ethereum": "ETH-USD",
            "EUR/USD": "EURUSD=X",
            "GBP/USD": "GBPUSD=X",
            "Gold": "GC=F"
        }
        
        selected_asset = st.selectbox(
            "Select Asset",
            list(available_assets.keys())
        )
        
        ticker = available_assets[selected_asset]
        
        # Time period selector
        period_options = {
            "1 Day": "1d",
            "5 Days": "5d",
            "1 Month": "1mo",
            "3 Months": "3mo"
        }
        
        selected_period = st.selectbox(
            "Analysis Period",
            list(period_options.keys())
        )
        
        period = period_options[selected_period]
        
        # Advanced settings
        with st.expander("Advanced Parameters"):
            kalman_transition = st.slider(
                "Kalman Transition Covariance",
                min_value=0.001,
                max_value=0.1,
                value=0.01,
                step=0.001,
                format="%.3f"
            )
            
            atr_multiplier = st.slider(
                "ATR Multiplier",
                min_value=1.0,
                max_value=3.0,
                value=2.0,
                step=0.1
            )
        
        st.divider()
        
        # Logout button
        if st.button("Logout", use_container_width=True):
            st.session_state['authenticated'] = False
            st.rerun()
    
    # Main header
    st.markdown('<div class="main-header">📊 Institutional Market Intelligence</div>', unsafe_allow_html=True)
    
    # Fetch data
    with st.spinner(f"Fetching {selected_asset} market data..."):
        df = fetch_market_data(ticker, period=period)
    
    if df is None:
        st.error(f"Failed to load data for {selected_asset}. Please try again.")
        return
    
    # Get live price
    live_price = get_live_price(ticker)
    
    # Initialize strategy engines
    kalman_engine = KalmanArbitrageEngine(
        transition_cov=kalman_transition
    )
    atr_engine = ATRBreakoutEngine(multiplier=atr_multiplier)
    orderflow_engine = OrderFlowImbalanceEngine()
    scorer = CompositeScorer()
    
    # Calculate signals
    kalman_zscore, equilibrium = kalman_engine.calculate_zscore(
        df['Close'].values
    )
    kalman_signal, kalman_certainty = kalman_engine.generate_signal(kalman_zscore)
    
    atr_signal, atr_certainty = atr_engine.detect_breakout(df)
    
    orderflow_signal, orderflow_certainty = orderflow_engine.find_fair_value_gaps(df)
    
    # Combine signals
    all_signals = {
        'kalman': {'signal': kalman_signal, 'certainty': kalman_certainty},
        'atr': {'signal': atr_signal, 'certainty': atr_certainty},
        'orderflow': {'signal': orderflow_signal, 'certainty': orderflow_certainty}
    }
    
    final_signal, certainty_pct = scorer.calculate_composite_score(all_signals)
    
    # Display metrics row
    col_metric1, col_metric2, col_metric3, col_metric4 = st.columns(4)
    
    with col_metric1:
        st.markdown('<div class="metric-label">Current Price</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-value">${live_price:,.2f}</div>' 
                    if live_price else '<div class="metric-value">N/A</div>', 
                    unsafe_allow_html=True)
    
    with col_metric2:
        st.markdown('<div class="metric-label">24h Change</div>', unsafe_allow_html=True)
        if len(df) >= 2:
            change = ((df['Close'].iloc[-1] - df['Close'].iloc[-2]) / 
                     df['Close'].iloc[-2] * 100)
            color = "#00d4aa" if change >= 0 else "#ff4d4d"
            st.markdown(
                f'<div class="metric-value" style="color: {color}">{change:+.2f}%</div>',
                unsafe_allow_html=True
            )
    
    with col_metric3:
        st.markdown('<div class="metric-label">Volume (24h)</div>', unsafe_allow_html=True)
        volume_billions = df['Volume'].iloc[-1] / 1e9
        st.markdown(
            f'<div class="metric-value">${volume_billions:.*_
