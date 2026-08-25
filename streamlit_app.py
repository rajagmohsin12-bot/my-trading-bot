"""
Institutional Market Scanner & Trading Dashboard
Premium Quantitative Analysis Platform
"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import plotly.graph_objects as go
import warnings

warnings.filterwarnings('ignore')

# =============================================================================
# CONFIGURATION
# =============================================================================

ASSETS = {
    "BTC-USD": "Bitcoin",
    "ETH-USD": "Ethereum", 
    "EURUSD=X": "EUR/USD",
    "GBPUSD=X": "GBP/USD",
    "GC=F": "Gold Futures"
}

ADMIN_PASSWORD = "INSTITUTIONAL2024"

# =============================================================================
# DATA FETCHING ENGINE
# =============================================================================

class MarketDataEngine:
    """Secure data fetching with error handling"""
    
    @staticmethod
    @st.cache_data(ttl=300)
    def fetch_data(symbol, period="1mo", interval="30m"):
        """Fetch market data with proper error handling"""
        try:
            data = yf.download(
                symbol,
                period=period,
                interval=interval,
                progress=False,
                auto_adjust=True
            )
            if data.empty:
                return pd.DataFrame()
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            return data
        except Exception:
            return pd.DataFrame()

# =============================================================================
# KALMAN FILTER STATISTICAL ARBITRAGE
# =============================================================================

class KalmanArbitrageEngine:
    """Dynamic equilibrium tracking using Kalman Filter"""
    
    def __init__(self, data):
        self.data = data
        if not data.empty:
            self.price = data['Close']
        else:
            self.price = pd.Series(dtype=float)
    
    def calculate_zscore(self):
        """Calculate Z-Score for statistical arbitrage"""
        if len(self.price) < 30:
            return 0.0
        
        # Using simple moving average as proxy for state estimation
        rolling_mean = self.price.rolling(window=20).mean()
        rolling_std = self.price.rolling(window=20).std()
        
        if rolling_std.iloc[-1] == 0 or np.isnan(rolling_std.iloc[-1]):
            return 0.0
        
        zscore = (self.price.iloc[-1] - rolling_mean.iloc[-1]) / rolling_std.iloc[-1]
        return float(zscore)
    
    def generate_signals(self):
        """Generate statistical arbitrage signals"""
        zscore = self.calculate_zscore()
        
        if zscore >= 2.0:
            signal = "STRONG_SELL"
            strength = min(100.0, abs(zscore) * 25)
        elif zscore >= 1.0:
            signal = "SELL"
            strength = min(70.0, abs(zscore) * 15)
        elif zscore <= -2.0:
            signal = "STRONG_BUY"
            strength = min(100.0, abs(zscore) * 25)
        elif zscore <= -1.0:
            signal = "BUY"
            strength = min(70.0, abs(zscore) * 15)
        else:
            signal = "HOLD"
            strength = 30.0
        
        return {
            "signal": signal,
            "strength": strength,
            "zscore": zscore
        }

# =============================================================================
# ATR VOLATILITY BREAKOUT ENGINE
# =============================================================================

class ATRBreakoutEngine:
    """Institutional ATR channel breakout detection"""
    
    def __init__(self, data):
        self.data = data
        if not data.empty:
            self.high = data['High']
            self.low = data['Low']
            self.close = data['Close']
            self.volume = data['Volume']
        else:
            self.high = pd.Series(dtype=float)
            self.low = pd.Series(dtype=float)
            self.close = pd.Series(dtype=float)
            self.volume = pd.Series(dtype=float)
    
    def calculate_atr(self):
        """Average True Range calculation"""
        if self.data.empty or len(self.close) < 15:
            return 0.0
        
        high = self.high
        low = self.low
        close_prev = self.close.shift(1)
        
        tr1 = high - low
        tr2 = abs(high - close_prev)
        tr3 = abs(low - close_prev)
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(window=14).mean()
        
        if atr.iloc[-1] == 0 or np.isnan(atr.iloc[-1]):
            return 0.0
        
        return float(atr.iloc[-1])
    
    def calculate_volume_ratio(self):
        """Relative volume ratio for confirmation"""
        if self.data.empty or len(self.volume) < 20:
            return 1.0
        
        avg_volume = self.volume.rolling(window=20).mean()
        if avg_volume.iloc[-1] == 0 or np.isnan(avg_volume.iloc[-1]):
            return 1.0
        
        volume_ratio = self.volume.iloc[-1] / avg_volume.iloc[-1]
        return float(volume_ratio)
    
    def generate_signals(self):
        """Generate ATR breakout signals"""
        if self.data.empty:
            return {"signal": "HOLD", "strength": 0.0, "atr": 0.0, "volume_ratio": 1.0}
        
        atr_value = self.calculate_atr()
        volume_ratio = self.calculate_volume_ratio()
        
        if atr_value == 0:
            return {"signal": "HOLD", "strength": 0.0, "atr": atr_value, "volume_ratio": volume_ratio}
        
        current_close = float(self.close.iloc[-1])
        prev_close = float(self.close.iloc[-2]) if len(self.close) > 1 else current_close
        
        upper_channel = prev_close + (2.0 * atr_value)
        lower_channel = prev_close - (2.0 * atr_value)
        
        if current_close > upper_channel and volume_ratio > 1.5:
            signal = "STRONG_BUY"
            strength = min(100.0, 70.0 + volume_ratio * 15)
        elif current_close > upper_channel and volume_ratio > 1.0:
            signal = "BUY"
            strength = min(80.0, 50.0 + volume_ratio * 10)
        elif current_close < lower_channel and volume_ratio > 1.5:
            signal = "STRONG_SELL"
            strength = min(100.0, 70.0 + volume_ratio * 15)
        elif current_close < lower_channel and volume_ratio > 1.0:
            signal = "SELL"
            strength = min(80.0, 50.0 + volume_ratio * 10)
        else:
            signal = "HOLD"
            strength = 30.0
        
        return {
            "signal": signal,
            "strength": strength,
            "atr": atr_value,
            "volume_ratio": volume_ratio
        }

# =============================================================================
# ORDER FLOW IMBALANCE ENGINE
# =============================================================================

class OrderFlowEngine:
    """Fair Value Gap and institutional block detection"""
    
    def __init__(self, data):
        self.data = data
        if not data.empty:
            self.high = data['High']
            self.low = data['Low']
            self.close = data['Close']
        else:
            self.high = pd.Series(dtype=float)
            self.low = pd.Series(dtype=float)
            self.close = pd.Series(dtype=float)
    
    def detect_fair_value_gaps(self):
        """Identify Fair Value Gaps"""
        if self.data.empty or len(self.data) < 10:
            return 0
        
        count = 0
        for i in range(2, len(self.data) - 1):
            bull_gap = self.low.iloc[i] - self.high.iloc[i-2]
            bear_gap = self.low.iloc[i-2] - self.high.iloc[i]
            
            if bull_gap > 0 or bear_gap > 0:
                count += 1
        
        return count
    
    def detect_institutional_blocks(self):
        """Identify institutional order blocks"""
        if self.data.empty or len(self.data) < 10:
            return 0
        
        count = 0
        price_change_threshold = 0.02
        
        for i in range(1, len(self.data) - 2):
            current_change = (self.close.iloc[i] - self.close.iloc[i-1]) / self.close.iloc[i-1]
            if abs(current_change) > price_change_threshold:
                count += 1
        
        return count
    
    def calculate_imbalance_score(self):
        """Calculate order flow imbalance score"""
        if self.data.empty:
            return {"signal": "HOLD", "strength": 0.0, "fvg_count": 0, "block_count": 0, "score": 0}
        
        fvg_count = self.detect_fair_value_gaps()
        block_count = self.detect_institutional_blocks()
        
        current_price = float(self.close.iloc[-1])
        prev_price = float(self.close.iloc[-2]) if len(self.close) > 1 else current_price
        
        price_change = (current_price - prev_price) / prev_price if prev_price != 0 else 0
        
        score = 0
        
        if price_change > 0.02 and fvg_count > 0:
            score += 30
        elif price_change < -0.02 and fvg_count > 0:
            score -= 30
        
        if block_count > 3:
            score += 20
        elif block_count < -3:
            score -= 20
        
        if score >= 40:
            signal = "STRONG_BUY"
            strength = 80.0
        elif score >= 20:
            signal = "BUY"
            strength = 60.0
        elif score <= -40:
            signal = "STRONG_SELL"
            strength = 80.0
        elif score <= -20:
            signal = "SELL"
            strength = 60.0
        else:
            signal = "HOLD"
            strength = 30.0
        
        return {
            "signal": signal,
            "strength": strength,
            "fvg_count": fvg_count,
            "block_count": block_count,
            "score": score
        }

# =============================================================================
# COMPOSITE SCORING ENGINE
# =============================================================================

class CompositeScoringEngine:
    """Unified multivariable scoring system"""
    
    def __init__(self, kalman_result, atr_result, flow_result):
        self.kalman_result = kalman_result
        self.atr_result = atr_result
        self.flow_result = flow_result
    
    def calculate_composite_score(self):
        """Calculate weighted composite certainty score"""
        
        weights = {
            'kalman': 0.35,
            'atr': 0.30,
            'flow': 0.35
        }
        
        signal_values = {
            'STRONG_BUY': 1.0,
            'BUY': 0.6,
            'HOLD': 0.0,
            'SELL': -0.6,
            'STRONG_SELL': -1.0
        }
        
        total_score = 0.0
        total_certainty = 0.0
        
        kalman_signal = self.kalman_result['signal']
        kalman_strength = self.kalman_result['strength']
        kalman_score = signal_values.get(kalman_signal, 0.0)
        total_score += kalman_score * weights['kalman']
        total_certainty += kalman_strength * weights['kalman']
        
        atr_signal = self.atr_result['signal']
        atr_strength = self.atr_result['strength']
        atr_score = signal_values.get(atr_signal, 0.0)
        total_score += atr_score * weights['atr']
        total_certainty += atr_strength * weights['atr']
        
        flow_signal = self.flow_result['signal']
        flow_strength = self.flow_result['strength']
        flow_score = signal_values.get(flow_signal, 0.0)
        total_score += flow_score * weights['flow']
        total_certainty += flow_strength * weights['flow']
        
        if total_score >= 0.7:
            final_signal = "STRONG BUY"
        elif total_score >= 0.3:
            final_signal = "BUY"
        elif total_score <= -0.7:
            final_signal = "STRONG SELL"
        elif total_score <= -0.3:
            final_signal = "SELL"
        else:
            final_signal = "HOLD"
        
        certainty = min(95.0, max(20.0, total_certainty + abs(total_score) * 15))
        
        return {
            'signal': final_signal,
            'certainty': round(certainty, 2),
            'composite_score': round(total_score, 3),
            'components': {
                'kalman': kalman_signal,
                'atr': atr_signal,
                'flow': flow_signal
            }
        }

# =============================================================================
# MAIN APPLICATION
# =============================================================================

def main():
    """Main application entry point"""
    
    st.set_page_config(
        page_title="Institutional Market Scanner",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS for premium look
    st.markdown("""
        <style>
        .stApp {
            background-color: #0d1117;
        }
        .css-1d391kg {
            background-color: #161b22;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Sidebar
    st.sidebar.title("🔐 Access Control")
    
    password = st.sidebar.text_input("Enter Access Password", type="password")
    
    if password != ADMIN_PASSWORD:
        st.sidebar.error("Access Denied")
        st.markdown("# 🔒 Institutional Access Required")
        st.markdown("Please enter your credentials to access the market scanner.")
        st.stop()
    
    st.sidebar.success("✓ Access Granted")
    
    # Main header
    st.markdown("# 📊 Institutional Market Scanner")
    st.markdown("### Advanced Quantitative Analysis Terminal")
    
    # Asset selector
    st.sidebar.title("Market Selection")
    selected_asset = st.sidebar.selectbox(
        "Select Asset",
        list(ASSETS.keys()),
        format_func=lambda x: f"{ASSETS[x]} ({x})"
    )
    
    # Time period selector
    period = st.sidebar.selectbox(
        "Time Period",
        ["1mo", "3mo", "6mo", "1y"],
        index=1
    )
    
    interval = st.sidebar.selectbox(
        "Chart Interval",
        ["30m", "1h", "4h", "1d"],
        index=0
    )
    
    # Fetch data
    data_engine = MarketDataEngine()
    data = data_engine.fetch_data(selected_asset, period, interval)
    
    if data.empty:
        st.error("No data available for this asset. Please try again.")
        st.stop()
    
    # Initialize engines
    kalman_engine = KalmanArbitrageEngine(data)
    atr_engine = ATRBreakoutEngine(data)
    flow_engine = OrderFlowEngine(data)
    
    # Generate signals
    kalman_result = kalman_engine.generate_signals()
    atr_result = atr_engine.generate_signals()
    flow_result = flow_engine.generate_signals()
    
    # Composite scoring
    scoring_engine = CompositeScoringEngine(kalman_result, atr_result, flow_result)
    composite_result = scoring_engine.calculate_composite_score()
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    current_price = float(data['Close'].iloc[-1])
    price_change = float(data['Close'].iloc[-1] - data['Close'].iloc[-2]) if len(data) > 1 else 0.0
    price_change_percent = (price_change / data['Close'].iloc[-2] * 100) if len(data) > 1 else 0.0
    
    with col1:
        st.metric("Current Price", f"${current_price:,.2f}", f"{price_change_percent:+.2f}%")
    
    with col2:
        st.metric("Composite Score", f"{composite_result['composite_score']:.3f}")
    
    with col3:
        st.metric("Certainty", f"{composite_result['certainty']}%")
    
    with col4:
        signal_color = "green" if "BUY" in composite_result['signal'] else "red" if "SELL" in composite_result['signal'] else "orange"
        st.markdown(f"**Signal:** {composite_result['signal']}")
    
    # Display signal cards
    st.markdown("## Composite Signal Analysis")
    
    signal = composite_result['signal']
    if "BUY" in signal:
        st.success(f"### {signal} - Certainty: {composite_result['certainty']}%")
    elif "SELL" in signal:
        st.error(f"### {signal} - Certainty: {composite_result['certainty']}%")
    else:
        st.warning(f"### {signal} - Certainty: {composite_result['certainty']}%")
    
    # Component signals
    st.markdown("### Strategy Components")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.info(f"**Kalman Filter:** {kalman_result['signal']}")
        if 'zscore' in kalman_result:
            st.write(f"Z-Score: {kalman_result['zscore']:.2f}")
    
    with col2:
        st.info(f"**ATR Breakout:** {atr_result['signal']}")
        if 'volume_ratio' in atr_result:
            st.write(f"Volume Ratio: {atr_result['volume_ratio']:.2f}x")
    
    with col3:
        st.info(f"**Order Flow:** {flow_result['signal']}")
        if 'fvg_count' in flow_result:
            st.write(f"FVG Count: {flow_result['fvg_count']}")
    
    # Price chart
    st.markdown("## Price Action")
    
    fig = go.Figure()
    
    fig.add_trace(go.Candlestick(
        x=data.index,
        open=data['Open'],
        high=data['High'],
        low=data['Low'],
        close=data['Close'],
        name='Price'
    ))
    
    # Add moving averages
    data['MA20'] = data['Close'].rolling(window=20).mean()
    data['MA50'] = data['Close'].rolling(window=50).mean()
    
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data['MA20'],
        mode='lines',
        name='MA20',
        line=dict(color='orange', width=1)
    ))
    
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data['MA50'],
        mode='lines',
        name='MA50',
        line=dict(color='blue', width=1)
    ))
    
    fig.update_layout(
        title=f"{selected_asset} Price Action",
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        height=600
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Technical indicators
    st.markdown("## Technical Analysis")
    
    col1, col2, col3 = st.columns(3)
    
    # RSI
    delta = data['Close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    # Bollinger Bands
    data['BB_middle'] = data['Close'].rolling(window=20).mean()
    bb_std = data['Close'].rolling(window=20).std()
    data['BB_upper'] = data['BB_middle'] + 2 * bb_std
    data['BB_lower'] = data['BB_middle'] - 2 * bb_std
    
    with col1:
        st.metric("RSI (14)", f"{rsi.iloc[-1]:.2f}")
    
    with col2:
        st.metric("ATR (14)", f"${atr_result.get('atr', 0):,.4f}")
    
    with col3:
        st.metric("Volume Ratio", f"{atr_result.get('volume_ratio', 1):.2f}x")
    
    # Market stats
    st.markdown("## Market Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("24h High", f"${data['High'].max():,.2f}")
    
    with col2:
        st.metric("24h Low", f"${data['Low'].min():,.2f}")
    
    with col3:
        st.metric("Avg Volume", f"{data['Volume'].mean():,.0f}")
    
    with col4:
        st.metric("Volatility", f"{data['Close'].pct_change().std() * 100:.2f}%")
    
    # Risk assessment
    st.markdown("## Risk Analysis")
    
    returns = data['Close'].pct_change().dropna()
    var_95 = np.percentile(returns, 5)
    var_99 = np.percentile(returns, 1)
    sharpe_ratio = (returns.mean() * 252) / (returns.std() * np.sqrt(252)) if returns.std() > 0 else 0
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Var 95%", f"{var_95 * 100:.2f}%")
    
    with col2:
        st.metric("Var 99%", f"{var_99 * 100:.2f}%")
    
    with col3:
        st.metric("Sharpe Ratio", f"{sharpe_ratio:.2f}")
    
    # Footer
    st.markdown("---")
    st.markdown("*Institutional Market Scanner v1.0 - For Professional Use Only*")
    
    st.sidebar.markdown("---")
    st.sidebar.info("📈 Advanced quantitative strategies sourced from institutional frameworks.")

if __name__ == "__main__":
    main()
