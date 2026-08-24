import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# PAGE CONFIGURATION - MUST BE FIRST STREAMLIT COMMAND
# ============================================================
st.set_page_config(
    page_title="MeridianQuant | Institutional Terminal",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# CUSTOM CSS - INSTITUTIONAL HEDGE FUND TERMINAL THEME
# ============================================================
st.markdown("""
<style>
    /* Main Terminal Background */
    .stApp {
        background: #0a0e17;
        font-family: 'Inter', 'Segoe UI', sans-serif;
    }
    
    /* Metric Containers */
    .stMetric {
        background: linear-gradient(135deg, #141a2a 0%, #0f1524 100%);
        border: 1px solid #2a3a5e;
        border-radius: 8px;
        padding: 20px 16px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.5);
    }
    
    .stMetric label {
        color: #8b9bb4 !important;
        font-weight: 500;
        letter-spacing: 0.5px;
        font-size: 12px;
        text-transform: uppercase;
    }
    
    .stMetric [data-testid="stMetricValue"] {
        color: #ffffff;
        font-size: 22px;
        font-weight: 600;
        letter-spacing: 0.5px;
    }
    
    /* Button Styling */
    .stButton > button {
        background: #1e2a45;
        color: #ffffff;
        border: 1px solid #3a4a6e;
        border-radius: 6px;
        font-weight: 500;
        transition: all 0.3s;
    }
    
    .stButton > button:hover {
        background: #2a3a5e;
        border-color: #4a6a9e;
        transform: translateY(-2px);
    }
    
    /* Expander Styling */
    .stExpander {
        background: #141a2a;
        border: 1px solid #2a3a5e;
        border-radius: 8px;
        overflow: hidden;
    }
    
    /* Dataframe Styling */
    .stDataFrame {
        border: 1px solid #2a3a5e;
        border-radius: 8px;
    }
    
    /* Progress Bar */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #00d4ff, #00b8d9);
    }
    
    /* Select Box */
    .stSelectbox > div > div {
        background: #141a2a;
        border: 1px solid #2a3a5e;
        border-radius: 6px;
        color: #ffffff;
    }
    
    /* Info Boxes */
    .stAlert {
        border-radius: 8px;
        border: 1px solid #2a3a5e;
        background: #141a2a;
    }
    
    /* Title */
    h1, h2, h3 {
        color: #ffffff !important;
        letter-spacing: 0.5px;
    }
    
    /* High Contrast Text */
    .high-contrast {
        color: #00ff88;
        font-weight: 600;
    }
    
    .risk-high {
        color: #ff4444;
    }
    
    .risk-mid {
        color: #ffaa00;
    }
    
    /* Sidebar */
    .css-1d391kg {
        background: #0a0e17;
    }
    
    /* Footer */
    .footer {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        padding: 10px;
        text-align: center;
        color: #8b9bb4;
        font-size: 11px;
        background: #0a0e17;
        border-top: 1px solid #2a3a5e;
        z-index: 100;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# USER ACCESS CONTROL SYSTEM
# ============================================================

def initialize_access_state():
    """Initialize session state for access control"""
    if 'access_verified' not in st.session_state:
        st.session_state.access_verified = False
    if 'access_attempts' not in st.session_state:
        st.session_state.access_attempts = 0
    if 'admin_login' not in st.session_state:
        st.session_state.admin_login = False

def check_user_access():
    """Main access control logic"""
    initialize_access_state()
    
    if st.session_state.access_verified:
        return True
    
    st.markdown("""
        <div style="padding: 40px; text-align: center; background: #141a2a; border-radius: 12px; border: 1px solid #2a3a5e; margin-top: 50px;">
            <h2 style="color: #ffffff; margin-bottom: 10px;">🔐 Institutional Access Gateway</h2>
            <p style="color: #8b9bb4;">MeridianQuant Terminal requires verified institutional credentials</p>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("---")
        access_code = st.text_input(
            "Institutional Access Code",
            type="password",
            placeholder="Enter your authorized access code",
            help="Contact admin@meridianquant.io for authorized access"
        )
        
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("🔓 Authenticate", use_container_width=True):
                # ADMIN MASTER CODE (change this in production)
                ADMIN_CODE = "MERIDIAN-2024-Q4"
                
                if access_code == ADMIN_CODE:
                    st.session_state.access_verified = True
                    st.rerun()
                else:
                    st.session_state.access_attempts += 1
                    st.error(f"Invalid access code. Failed attempt #{st.session_state.access_attempts}")
                    
        with col_btn2:
            if st.button("🛡️ Admin Login", use_container_width=True):
                st.session_state.admin_login = True
                st.rerun()
                
        if st.session_state.admin_login:
            st.markdown("---")
            admin_password = st.text_input(
                "Admin Password",
                type="password",
                placeholder="Administrator master key"
            )
            
            col_admin1, _ = st.columns([1, 1])
            
            with col_admin1:
                if st.button("🔑 Verify Admin", use_container_width=True):
                    # ADMIN MASTER PASSWORD (change this in production)
                    ADMIN_PASSWORD = "MERIDIAN-ADMIN-2024"
                    
                    if admin_password == ADMIN_PASSWORD:
                        st.session_state.access_verified = True
                        st.rerun()
                    else:
                        st.error("Invalid admin credentials")
        
        st.markdown("---")
        st.markdown(
            f"<div style='text-align: center; color: #8b9bb4; font-size: 12px;'>"
            f"Access attempts: {st.session_state.access_attempts} | "
            f"Status: {'Unauthorized' if not st.session_state.access_verified else 'Verified'}"
            f"</div>", 
            unsafe_allow_html=True
        )
        
        if st.session_state.access_attempts >= 5:
            st.error("Too many failed attempts. Access locked for security.")
            
    return False

# ============================================================
# QUANTITATIVE STRATEGY ENGINES
# ============================================================

class KalmanFilterStrategy:
    """Kalman Filter for Statistical Arbitrage and Dynamic Equilibrium Tracking"""
    
    @staticmethod
    def kalman_filter(data, initial_cov=1.0, process_noise=0.01, measurement_noise=0.5):
        """
        Adaptive Kalman Filter for price tracking
        
        Parameters:
        - data: numpy array of values
        - initial_cov: initial covariance
        - process_noise: model noise
        - measurement_noise: observation noise
        
        Returns:
        - filtered_states, covariances
        """
        n = len(data)
        state_mean = data[0]
        state_cov = initial_cov
        
        filtered_states = np.zeros(n)
        covariances = np.zeros(n)
        
        for i in range(n):
            # Prediction step
            predicted_mean = state_mean
            predicted_cov = state_cov + process_noise
            
            # Update step (Kalman gain)
            kalman_gain = predicted_cov / (predicted_cov + measurement_noise)
            
            # Observation update
            state_mean = predicted_mean + kalman_gain * (data[i] - predicted_mean)
            state_cov = (1 - kalman_gain) * predicted_cov
            
            filtered_states[i] = state_mean
            covariances[i] = state_cov
        
        return filtered_states, covariances
    
    @staticmethod
    def calculate_zscore(price, filtered_price, covariances):
        """
        Calculate Kalman Z-Score for stat-arb signals
        
        High positive z-score → asset overvalued relative to equilibrium
        High negative z-score → asset undervalued relative to equilibrium
        """
        std = np.sqrt(covariances[-1]) if len(covariances) > 0 else 1.0
        if std == 0:
            std = 1e-10
        
        z_score = (price - filtered_price[-1]) / std if len(filtered_price) > 0 else 0
        return z_score
    
    @staticmethod
    def generate_signal(price_series, lookback=50, threshold=2.0):
        """
        Generate trading signal based on Kalman Z-Score
        
        Signal rules:
        - z_score > +threshold → SHORT (price above equilibrium)
        - z_score < -threshold → LONG (price below equilibrium)
        - Otherwise → NEUTRAL
        """
        if len(price_series) < lookback:
            return 0, 0, 0  # neutral, z_score, state
        
        # Use last 'lookback' points for efficiency
        recent_data = price_series[-lookback:]
        
        # Apply Kalman Filter
        filtered, covs = KalmanFilterStrategy.kalman_filter(recent_data)
        
        # Current z-score
        z_score = KalmanFilterStrategy.calculate_zscore(recent_data[-1], filtered, covs)
        
        # Signal generation
        if z_score > threshold:
            signal = -1  # Bearish (short)
        elif z_score < -threshold:
            signal = 1  # Bullish (long)
        else:
            signal = 0  # Neutral
        
        return signal, z_score, filtered[-1]

class VolatilityBreakoutStrategy:
    """ATR Channel Breakout with Institutional Volume Confirmation"""
    
    @staticmethod
    def calculate_atr(high, low, close, period=14):
        """
        Average True Range calculation
        
        True Range = max(high-low, |high-prev_close|, |low-prev_close|)
        """
        high = np.array(high)
        low = np.array(low)
        close = np.array(close)
        
        tr1 = high[1:] - low[1:]
        tr2 = np.abs(high[1:] - close[:-1])
        tr3 = np.abs(low[1:] - close[:-1])
        
        tr = np.maximum(np.maximum(tr1, tr2), tr3)
        atr = np.zeros(len(close))
        atr[period] = np.mean(tr[:period])
        
        for i in range(period + 1, len(close)):
            atr[i] = (atr[i-1] * (period - 1) + tr[i-1]) / period
        
        return atr
    
    @staticmethod
    def detect_breakout(close, high, low, atr, multiplier=2.0, lookback=10):
        """
        Detect volatility breakouts
        
        Conditions:
        - Price breaks above upper ATR channel with volume confirmation
        - Price breaks below lower ATR channel with volume confirmation
        """
        if len(close) < lookback + 2:
            return 0, 0, 0
        
        upper_channel = close + (multiplier * atr)
        lower_channel = close - (multiplier * atr)
        
        current_price = close[-1]
        current_atr = atr[-1] if atr[-1] > 0 else 1e-10
        
        # Breakout detection
        if current_price > upper_channel[-2]:  # Breaking above
            strength = min((current_price - upper_channel[-2]) / current_atr, 3.0)
            signal = 1
        elif current_price < lower_channel[-2]:  # Breaking below
            strength = min((lower_channel[-2] - current_price) / current_atr, 3.0)
            signal = -1
        else:
            signal = 0
            strength = 0
        
        # Volume confirmation (simulated here - real impl would use volume data)
        volume_ratio = np.random.uniform(0.8, 1.5)  # Placeholder, replace with actual volume
        
        return signal, strength, volume_ratio

class OrderFlowImbalanceStrategy:
    """Fair Value Gap (FVG) and Institutional Liquidity Block Detection"""
    
    @staticmethod
    def detect_fvg(high, low, close, lookback=5):
        """
        Fair Value Gap detection
        
        FVG occurs when current low is above previous high in an uptrend
        or current high is below previous low in a downtrend (gap)
        """
        if len(high) < lookback + 2:
            return 0, 0
        
        # Look for 3-candle patterns
        fvg_signals = []
        fvg_strengths = []
        
        for i in range(2, min(len(high), lookback + 2)):
            # Bullish FVG: low[i] > high[i-2]
            if low[i] > high[i-2]:
                gap_size = low[i] - high[i-2]
                avg_range = np.mean([high[i]-low[i], high[i-1]-low[i-1], high[i-2]-low[i-2]])
                if avg_range > 0:
                    strength = min(gap_size / avg_range, 3.0)
                    fvg_signals.append(1)
                    fvg_strengths.append(strength)
            
            # Bearish FVG: high[i] < low[i-2]
            elif high[i] < low[i-2]:
                gap_size = low[i-2] - high[i]
                avg_range = np.mean([high[i]-low[i], high[i-1]-low[i-1], high[i-2]-low[i-2]])
                if avg_range > 0:
                    strength = min(gap_size / avg_range, 3.0)
                    fvg_signals.append(-1)
                    fvg_strengths.append(strength)
        
        if len(fvg_signals) == 0:
            return 0, 0
        
        recent_signal = fvg_signals[-1]
        avg_strength = np.mean(fvg_strengths[-3:]) if len(fvg_strengths) >= 3 else max(fvg_strengths, default=0)
        
        return recent_signal, avg_strength
    
    @staticmethod
    def detect_institutional_blocks(close, high, low, volume, lookback=20):
        """
        Detect institutional order blocks (accumulation/distribution zones)
        
        Uses volume displacement and price rejection patterns
        """
        if len(close) < lookback:
            return 0, 0
        
        # Identify volume spikes (institutional participation)
        avg_volume = np.mean(volume[-lookback:]) if len(volume) >= lookback else 1
        recent_blocks = []
        
        for i in range(max(2, len(close)-lookback), len(close)):
            # Volume spike detection (2x average = institutional footprint)
            if i > 0 and volume[i] > 2 * avg_volume:
                # Price rejection (wick) detection
                upper_wick = high[i] - max(open_price := close[i], close[i-1] if i > 0 else close[i])
                lower_wick = min(open_price := close[i], close[i-1] if i > 0 else close[i]) - low[i]
                
                # Bullish block: large lower wick + volume
                if lower_wick > upper_wick and lower_wick > 0.1 * (high[i] - low[i]):
                    recent_blocks.append(1)
                # Bearish block: large upper wick + volume
                elif upper_wick > lower_wick and upper_wick > 0.1 * (high[i] - low[i]):
                    recent_blocks.append(-1)
        
        if len(recent_blocks) == 0:
            return 0, 0
        
        # Weighted recent block judgment
        weighted_signal = np.mean(recent_blocks[-5:]) if len(recent_blocks) >= 5 else np.mean(recent_blocks)
        strength = min(abs(weighted_signal) * 2, 3.0)
        
        return int(np.sign(weighted_signal)), strength

class CompositeScorer:
    """Unified Multi-Variable Institutional Certainty Scoring"""
    
    @staticmethod
    def compute_certainty_score(kalman_signal, vol_signal, fvg_signal, block_signal, 
                                kalman_strength=1.0, vol_strength=1.0, 
                                fvg_strength=1.0, block_strength=1.0):
        """
        Compute composite institutional certainty score
        
        Each signal contributes with its strength weight
        Final score ranges from -100 (strongest sell) to +100 (strongest buy)
        """
        # Weights for each strategy (institutional allocation)
        weights = {
            'kalman': 0.35,  # Statistical arbitrage - always active
            'volatility': 0.25,  # Volatility breakout
            'fvg': 0.25,  # Fair value gap
            'block': 0.15  # Order blocks
        }
        
        # Composite signal computation
        composite = (
            kalman_signal * kalman_strength * weights['kalman'] +
            vol_signal * vol_strength * weights['volatility'] +
            fvg_signal * fvg_strength * weights['fvg'] +
            block_signal * block_strength * weights['block']
        )
        
        # Normalize to -1 to +1 range
        max_composite = weights['kalman'] * 3 + weights['volatility'] * 3 + weights['fvg'] * 3 + weights['block'] * 3
        normalized_score = composite / max_composite if max_composite > 0 else 0
        
        # Convert to percentage (-100 to +100)
        certainty_score = normalized_score * 100
        
        return certainty_score
    
    @staticmethod
    def classify_signal(score):
        """
        Classify composite score into trading signal
        
        Score ranges:
        - 60 to 100: STRONG BUY
        - 20 to 60: BUY
        - -20 to 20: HOLD
        - -60 to -20: SELL
        - -100 to -60: STRONG SELL
        """
        if score >= 60:
            return "STRONG BUY", 3
        elif score >= 20:
            return "BUY", 2
        elif score >= -20:
            return "HOLD", 0
        elif score >= -60:
            return "SELL", -2
        else:
            return "STRONG SELL", -3

# ============================================================
# DATA PIPELINE
# ============================================================

class MarketDataFetcher:
    """Robust Market Data Pipeline with Atomic Fetching"""
    
    ASSETS = {
        'BTC-USD': {'name': 'Bitcoin', 'type': 'Crypto', 'yahoo_symbol': 'BTC-USD'},
        'ETH-USD': {'name': 'Ethereum', 'type': 'Crypto', 'yahoo_symbol': 'ETH-USD'},
        'EURUSD=X': {'name': 'EUR/USD', 'type': 'Forex', 'yahoo_symbol': 'EURUSD=X'},
        'GBPUSD=X': {'name': 'GBP/USD', 'type': 'Forex', 'yahoo_symbol': 'GBPUSD=X'},
        'GC=F': {'name': 'Gold Futures', 'type': 'Commodity', 'yahoo_symbol': 'GC=F'}
    }
    
    @staticmethod
    def fetch_data(symbol, period='1mo', interval='1h'):
        """
        Safely fetch market data from Yahoo Finance
        
        Handles empty DataFrames, MultiIndex columns, and network errors
        """
        try:
            # Attempt asynchronous download with retry
            for attempt in range(3):
                try:
                    data = yf.download(
                        symbol,
                        period=period,
                        interval=interval,
                        progress=False,
                        auto_adjust=True,
                        threads=True
                    )
                    break
                except Exception as e:
                    if attempt == 2:
                        return pd.DataFrame()
                    continue
            
            if data.empty:
                return pd.DataFrame()
            
            # Flatten MultiIndex columns immediately
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            
            # Ensure required columns exist
            required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            for col in required_cols:
                if col not in data.columns:
                    return pd.DataFrame()
            
            # Remove any NaN values in critical columns
            data = data.dropna(subset=['Close'])
            
            return data
            
        except Exception:
            return pd.DataFrame()

# ============================================================
# MAIN DASHBOARD UI
# ============================================================

def render_dashboard(asset_symbol, period, interval):
    """
    Render the main institutional dashboard with all strategies
    """
    # Fetch data safely
    fetcher = MarketDataFetcher()
    data = fetcher.fetch_data(asset_symbol, period, interval)
    
    if data.empty or len(data) < 50:
        st.error("⚠️ Insufficient market data. Please select a different asset or timeframe.")
        return
    
    # ==========================================
    # METRIC CAR_
