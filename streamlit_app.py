import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings('ignore')
from typing import Dict, Tuple, Any

# ============================================================================
# CONFIGURATION
# ============================================================================

ASSETS = {
    "BTC-USD": "Bitcoin",
    "ETH-USD": "Ethereum",
    "EURUSD=X": "EUR/USD",
    "GBPUSD=X": "GBP/USD",
    "GC=F": "Gold Futures"
}

ADMIN_PASSWORD = "INSTITUTIONAL2024"

TIMEFRAMES = {
    "1 Month": "1mo",
    "3 Months": "3mo",
    "6 Months": "6mo",
    "1 Year": "1y"
}

INTERVALS = {
    "5 Min": "5m",
    "15 Min": "15m",
    "30 Min": "30m",
    "1 Hour": "1h",
    "4 Hours": "4h",
    "1 Day": "1d"
}

st.set_page_config(
    page_title="Institutional Market Scanner",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# DATA ENGINE
# ============================================================================

class MarketDataEngine:
    """Secure and efficient market data handling"""
    
    @staticmethod
    @st.cache_data(ttl=300)
    def fetch_data(symbol: str, period: str, interval: str) -> pd.DataFrame:
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
                st.sidebar.warning(f"No data available for {symbol}")
                return pd.DataFrame()
            
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            
            data = data.dropna()
            return data
            
        except Exception as e:
            st.sidebar.error(f"Error fetching {symbol}: {str(e)}")
            return pd.DataFrame()

    @staticmethod
    def get_current_price(data: pd.DataFrame) -> float:
        """Extract current market price safely"""
        if data.empty:
            return 0.0
        try:
            return float(data['Close'].iloc[-1])
        except:
            return 0.0

# ============================================================================
# KALMAN FILTER ENGINE
# ============================================================================

class KalmanFilterEngine:
    """Kalman Filter for statistical arbitrage detection"""
    
    def __init__(self, data: pd.DataFrame, window: int = 30):
        self.data = data
        self.window = window
        self.price = data['Close'] if not data.empty else pd.Series(dtype=float)
        self.high = data['High'] if not data.empty else pd.Series(dtype=float)
        self.low = data['Low'] if not data.empty else pd.Series(dtype=float)
    
    def calculate_kalman_state(self) -> pd.Series:
        """Calculate Kalman state estimates recursively"""
        if len(self.price) < 3:
            return pd.Series(index=self.price.index, dtype=float)
        
        state_means = []
        current_state = self.price.iloc[0]
        current_covariance = 1.0
        process_noise = 0.01
        observation_noise = 0.05
        
        for price in self.price.values:
            predicted_state = current_state
            predicted_covariance = current_covariance + process_noise
            
            kalman_gain = predicted_covariance / (predicted_covariance + observation_noise)
            current_state = predicted_state + kalman_gain * (price - predicted_state)
            current_covariance = (1 - kalman_gain) * predicted_covariance
            state_means.append(current_state)
        
        return pd.Series(state_means, index=self.price.index)
    
    def calculate_zscore(self) -> pd.Series:
        """Calculate Z-score for mean reversion detection"""
        state = self.calculate_kalman_state()
        if len(state) < 20:
            return pd.Series(index=self.price.index, dtype=float)
        
        spread = self.price - state
        spread_mean = spread.rolling(window=20).mean()
        spread_std = spread.rolling(window=20).std()
        
        zscore = (spread - spread_mean) / spread_std
        return zscore.replace([np.inf, -np.inf], 0).fillna(0)
    
    def generate_signals(self) -> Dict[str, Any]:
        """Generate signals based on Kalman filter state"""
        zscore = self.calculate_zscore()
        if zscore.empty:
            return {"signal": "HOLD", "strength": 0.0, "zscore": 0.0}
        
        current_zscore = zscore.iloc[-1]
        
        if current_zscore < -1.5:
            signal = "BUY"
            strength = min(100.0, abs(current_zscore) * 40)
        elif current_zscore > 1.5:
            signal = "SELL"
            strength = min(100.0, abs(current_zscore) * 40)
        else:
            signal = "HOLD"
            strength = 30.0
        
        return {
            "signal": signal,
            "strength": strength,
            "zscore": current_zscore
        }

# ============================================================================
# ATR VOLATILITY BREAKOUT ENGINE
# ============================================================================

class ATRBreakoutEngine:
    """ATR channel breakout detection with volume confirmation"""
    
    def __init__(self, data: pd.DataFrame, atr_period: int = 14, multiplier: float = 2.0):
        self.data = data
        self.atr_period = atr_period
        self.multiplier = multiplier
        
        if not data.empty:
            self.high = data['High']
            self.low = data['Low']
            self.close = data['Close']
            self.volume = data['Volume']
    
    def calculate_atr(self) -> pd.Series:
        """Calculate Average True Range"""
        if self.data.empty:
            return pd.Series(dtype=float)
        
        prev_close = self.close.shift(1)
        tr1 = self.high - self.low
        tr2 = (self.high - prev_close).abs()
        tr3 = (self.low - prev_close).abs()
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(window=self.atr_period).mean()
        return atr.fillna(atr.mean()) if atr.notna().any() else pd.Series(0, index=self.data.index)
    
    def calculate_channels(self) -> Tuple[pd.Series, pd.Series]:
        """Calculate upper and lower ATR channels"""
        atr = self.calculate_atr()
        if atr.empty:
            return pd.Series(index=self.data.index), pd.Series(index=self.data.index)
        
        upper_channel = self.close.shift(1) + (self.multiplier * atr)
        lower_channel = self.close.shift(1) - (self.multiplier * atr)
        
        return upper_channel.fillna(method='bfill'), lower_channel.fillna(method='bfill')
    
    def calculate_volume_ratio(self) -> float:
        """Calculate current volume ratio vs average"""
        if self.data.empty or len(self.volume) < 20:
            return 1.0
        
        avg_volume = self.volume.rolling(window=20).mean().iloc[-1]
        current_volume = self.volume.iloc[-1]
        
        if avg_volume == 0:
            return 1.0
        
        return current_volume / avg_volume
    
    def generate_signals(self) -> Dict[str, Any]:
        """Generate ATR breakout signals"""
        if self.data.empty:
            return {"signal": "HOLD", "strength": 0.0, "atr": 0.0}
        
        upper, lower = self.calculate_channels()
        volume_ratio = self.calculate_volume_ratio()
        atr_value = self.calculate_atr().iloc[-1]
        
        current_close = self.close.iloc[-1]
        
        if current_close > upper.iloc[-1] and volume_ratio > 1.5:
            signal = "BUY"
            strength = min(100.0, 60.0 + (volume_ratio - 1.0) * 40)
        elif current_close < lower.iloc[-1] and volume_ratio > 1.5:
            signal = "SELL"
            strength = min(100.0, 60.0 + (volume_ratio - 1.0) * 40)
        else:
            signal = "HOLD"
            strength = 20.0
        
        return {
            "signal": signal,
            "strength": strength,
            "atr": atr_value,
            "volume_ratio": volume_ratio
        }

# ============================================================================
# ORDER FLOW ENGINE
# ============================================================================

class OrderFlowEngine:
    """Institutional order flow and FVG detection"""
    
    def __init__(self, data: pd.DataFrame):
        self.data = data
        if not data.empty:
            self.high = data['High']
            self.low = data['Low']
            self.open = data['Open']
            self.close = data['Close']
            self.volume = data['Volume']
    
    def detect_fair_value_gaps(self) -> pd.DataFrame:
        """Detect Fair Value Gaps in price action"""
        if self.data.empty or len(self.data) < 10:
            return pd.DataFrame()
        
        fvg_list = []
        
        for i in range(2, len(self.data)):
            # Bullish FVG
            if self.low.iloc[i] > self.high.iloc[i - 2]:
                gap_size = self.low.iloc[i] - self.high.iloc[i - 2]
                fvg_list.append({
                    'index': self.data.index[i],
                    'type': 'bullish',
                    'top': self.low.iloc[i],
                    'bottom': self.high.iloc[i - 2],
                    'size': gap_size
                })
            # Bearish FVG
            elif self.high.iloc[i] < self.low.iloc[i - 2]:
                gap_size = self.low.iloc[i - 2] - self.high.iloc[i]
                fvg_list.append({
                    'index': self.data.index[i],
                    'type': 'bearish',
                    'top': self.low.iloc[i - 2],
                    'bottom': self.high.iloc[i],
                    'size': gap_size
                })
        
        return pd.DataFrame(fvg_list)
    
    def detect_liquidity_sweeps(self) -> pd.DataFrame:
        """Detect liquidity sweeps (stop hunts)"""
        if self.data.empty or len(self.data) < 5:
            return pd.DataFrame()
        
        sweep_list = []
        
        for i in range(1, len(self.data) - 1):
            prev_high = self.high.iloc[:i].max() if i > 0 else self.high.iloc[i]
            prev_low = self.low.iloc[:i].min() if i > 0 else self.low.iloc[i]
            
            if self.high.iloc[i] > prev_high and self.close.iloc[i] < self.high.iloc[i]:
                sweep_list.append({
                    'index': self.data.index[i],
                    'type': 'bullish_sweep'
                })
            elif self.low.iloc[i] < prev_low and self.close.iloc[i] > self.low.iloc[i]:
                sweep_list.append({
                    'index': self.data.index[i],
                    'type': 'bearish_sweep'
                })
        
        return pd.DataFrame(sweep_list)
    
    def calculate_imbalance_score(self) -> float:
        """Calculate order flow imbalance score"""
        fvg_data = self.detect_fair_value_gaps()
        sweep_data = self.detect_liquidity_sweeps()
        
        score = 0
        
        # Count recent FVGs within 1% of current price
        if not fvg_data.empty and not self.data.empty:
            current_price = self.close.iloc[-1]
            recent_fvg = fvg_data.tail(3)
            
            for _, fvg in recent_fvg.iterrows():
                distance = abs(fvg['top'] - current_price) / current_price
                if distance < 0.01:
                    if fvg['type'] == 'bullish':
                        score += 20
                    else:
                        score -= 20
        
        # Count recent liquidity sweeps
        if not sweep_data.empty:
            recent_sweeps = sweep_data.tail(5)
            
            for _, sweep in recent_sweeps.iterrows():
                if sweep['type'] == 'bullish_sweep':
                    score += 15
                elif sweep['type'] == 'bearish_sweep':
                    score -= 15
        
        return score
    
    def generate_signals(self) -> Dict[str, Any]:
        """Generate order flow signals"""
        if self.data.empty:
            return {"signal": "HOLD", "strength": 0.0, "fvg_count": 0}
        
        fvg_data = self.detect_fair_value_gaps()
        sweep_data = self.detect_liquidity_sweeps()
        imbalance_score = self.calculate_imbalance_score()
        
        if imbalance_score >= 30:
            signal = "BUY"
            strength = min(100.0, 50.0 + imbalance_score)
        elif imbalance_score <= -30:
            signal = "SELL"
            strength = min(100.0, 50.0 + abs(imbalance_score))
        else:
            signal = "HOLD"
            strength = 20.0
        
        return {
            "signal": signal,
            "strength": strength,
            "imbalance_score": imbalance_score,
            "fvg_count": len(fvg_data) if not fvg_data.empty else 0,
            "sweep_count": len(sweep_data) if not sweep_data.empty else 0
        }

# ============================================================================
# COMPOSITE SCORING ENGINE
# ============================================================================

class CompositeScoringEngine:
    """Aggregate all signals into composite certainty score"""
    
    def __init__(self, kalman_signal: Dict, atr_signal: Dict, flow_signal: Dict):
        self.kalman = kalman_signal
        self.atr = atr_signal
        self.flow = flow_signal
    
    def calculate_composite(self) -> Dict[str, Any]:
        """Calculate weighted composite signal and certainty"""
        
        weights = {
            'kalman': 0.35,
            'atr': 0.30,
            'flow': 0.35
        }
        
        signal_map = {
            'BUY': 1.0,
            'HOLD': 0.0,
            'SELL': -1.0
        }
        
        weighted_score = 0.0
        total_certainty = 0.0
        
        for component, weight in weights.items():
            signal = getattr(self, component).get('signal', 'HOLD')
            strength = getattr(self, component).get('strength', 0.0)
            weighted_score += signal_map.get(signal, 0.0) * weight
            total_certainty += strength * weight
        
        if weighted_score >= 0.5:
            final_signal = "STRONG BUY"
            final_strength = min(95.0, total_certainty + 20)
        elif weighted_score >= 0.1:
            final_signal = "BUY"
            final_strength = total_certainty
        elif weighted_score <= -0.5:
            final_signal = "STRONG SELL"
            final_strength = min(95.0, total_certainty + 20)
        elif weighted_score <= -0.1:
            final_signal = "SELL"
            final_strength = total_certainty
        else:
            final_signal = "HOLD"
            final_strength = max(20.0, total_certainty)
        
        reasoning = self.generate_reasoning()
        
        return {
            'signal': final_signal,
            'certainty': round(min(100.0, max(0.0, final_strength)), 2),
            'composite_score': weighted_score,
            'reasoning': reasoning,
            'components': {
                'kalman': self.kalman.get('signal', 'HOLD'),
                'atr': self.atr.get('signal', 'HOLD'),
                'flow': self.flow.get('signal', 'HOLD')
            }
        }
    
    def generate_reasoning(self) -> list:
        """Generate mathematical reasoning for signals"""
        reasons = []
        
        kalman_zscore = self.kalman.get('zscore', 0.0)
        if abs(kalman_zscore) > 1.5:
            direction = "overbought" if kalman_zscore > 0 else "oversold"
            reasons.append(f"Kalman Z-score {kalman_zscore:.2f} indicates {direction} conditions")
        else:
            reasons.append(f"Kalman Z-score {kalman_zscore:.2f} within normal bounds")
        
        volume_ratio = self.atr.get('volume_ratio', 1.0)
        if volume_ratio > 1.5:
            reasons.append(f"Abbormal volume {volume_ratio:.2f}x confirms ATR breakout")
        else:
            reasons.append(f"Volume {volume_ratio:.2f}x below breakout threshold")
        
        fvg_count = self.flow.get('fvg_count', 0)
        sweep_count = self.flow.get('sweep_count', 0)
        imbalance = self.flow.get('imbalance_score', 0)
        reasons.append(f"Order flow shows {fvg_count} FVGs and {sweep_count} liquidity sweeps with imbalance score {imbalance}")
        
        return reasons

# ============================================================================
# CHART ENGINE
# ============================================================================

class ChartEngine:
    """Professional chart generation"""
    
    @staticmethod
    def create_price_chart(data: pd.DataFrame, symbol: str, kalman_state: pd.Series = None) -> go.Figure:
        """Create candlestick chart with technical overlays"""
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.7, 0.3]
        )
        
        fig.add_trace(
            go.Candlestick(
                x=data.index,
                open=data['Open'],
                high=data['High'],
                low=data['Low'],
                close=data['Close'],
                name='Price',
                increasing_line_color='#26a69a',
                decreasing_line_color='#ef5350'
            ),
            row=1, col=1
        )
        
        if kalman_state is not None and len(kalman_state) > 0:
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=kalman_state,
                    name='Kalman Filter',
                    line=dict(color='#58a6ff', width=2)
                ),
                row=1, col=1
            )
        
        fig.add_trace(
            go.Bar(
                x=data.index,
                y=data['Volume'],
                name='Volume',
                marker_color='#238636',
                opacity=0.7
            ),
            row=2, col=1
        )
        
        fig.update_layout(
            title=f'{symbol} Institutional Analysis',
            xaxis_rangeslider_visible=False,
            height=600,
            template='plotly_dark',
            showlegend=True,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        
        fig.update_xaxes(gridcolor='#21262d', row=1, col=1)
        fig.update_xaxes(gridcolor='#21262d', row=2, col=1)
        fig.update_yaxes(gridcolor='#21262d', row=1, col=1)
        fig.update_yaxes(gridcolor='#21262d', row=2, col=1)
        
        return fig
    
    @staticmethod
    def create_signal_dashboard(signal_data: Dict) -> go.Figure:
        """Create signal strength visualization"""
        components = signal_data.get('components', {})
        
        fig = go.Figure()
        
        categories = ['Kalman Filter', 'ATR Breakout', 'Order Flow']
        values = []
        colors = []
        
        for comp in categories:
            signal = components.get(comp.lower().replace(' ', '_'), 'HOLD')
            if signal == 'BUY':
                values.append(1.0)
                colors.append('#26a69a')
            elif signal == 'SELL':
                values.append(-1.0)
                colors.append('#ef5350')
            else:
                values.append(0.0)
                colors.append('#ab47bc')
        
        fig.add_trace(go.Bar(
            x=categories,
            y=values,
            marker_color=colors,
            name='Signal Strength'
        ))
        
        fig.update_layout(
            title='Strategy Components Analysis',
            height=400,
            template='plotly_dark',
            showlegend=False,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            yaxis_title='Signal Direction',
            yaxis=dict(tickvals=[-1, 0, 1], ticktext=['SELL', 'HOLD', 'BUY'])
        )
        
        fig.update_xaxes(gridcolor='#21262d')
        fig.update_yaxes(gridcolor='#21262d')
        
        return fig

# ============================================================================
# MAIN APPLICATION
# ============================================================================

class InstitutionalMarketScanner:
    """Main application controller"""
    
    def __init__(self):
        self.data_engine = MarketDataEngine()
        self.chart_engine = ChartEngine()
    
    def check_access(self) -> bool:
        """Verify user access credentials"""
        st.sidebar.title("🔐 Secure Access")
        
        password = st.sidebar.text_input("Institutional Password", type="password")
        
        if password == ADMIN_PASSWORD:
            st.sidebar.success("Access Granted")
            return True
        elif password:
            st.sidebar.error("Invalid Password")
            return False
        else:
            st.sidebar.info("Please enter institutional access code")
            return False
    
    def render_sidebar(self) -> tuple:
        """Render sidebar controls"""
        st.sidebar.title("📊 Controls")
        
        selected_asset = st.sidebar.selectbox(
            "Select Asset",
            list(ASSETS.keys()),
            format_func=lambda x: f"{ASSETS[x]} ({x})"
        )
        
        timeframe = st.sidebar.selectbox(
            "Timeframe",
            list(TIMEFRAMES.keys()),
            index=1
        )
        
        interval = st.sidebar.selectbox(
            "Chart Interval",
            list(INTERVALS.keys()),
            index=2
        )
        
        return selected_asset, TIMEFRAMES[timeframe], INTERVALS[interval]
    
    def render_metrics_row(self, data: pd.DataFrame, signal_result: Dict) -> None:
        """Render top metrics row"""
        if data.empty:
            return
        
        current_price = float(data['Close'].iloc[-1])
        prev_price = float(data['Close'].iloc[-2]) if len(data) > 1 else current_price
        price_change = ((current_price - prev_price) / prev_price) * 100
        
        high_52 = float(data['High'].max())
        low_52 = float(data['Low'].min())
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Current Price",
                f"${current_price:,.4f}",
                f"{price_change:+.2f}%"
            )
        
        with col2:
            st.metric(
                "Period High",
                f"${high_52:,.4f}",
                f"{(current_price - high_52) / high_52 * 100:+.2f}% from high"
            )
        
        with col3:
            st.metric(
                "Period Low",
                f"${low_52:,.4f}",
                f"{(current_price - low_52) / low_52 * 100:+.2f}% from low"
            )
        
        with col4:
            signal = signal_result.get('signal', 'HOLD')
            certainty = signal_result.get('certainty', 0)
            
            if signal == "STRONG BUY" or signal == "BUY":
                color = "green"
                delta = f"{certainty:.1f}% confidence"
            elif signal == "STRONG SELL" or signal == "SELL":
                color = "red"
                delta = f"{certainty:.1f}% confidence"
            else:
                color = "orange"
                delta = f"{certainty:.1f}% confidence"
            
            st.metric(
                "Composite Signal",
                signal,
                delta,*_

