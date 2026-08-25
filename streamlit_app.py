"""
Institutional Market Scanner & Trading Dashboard
Premium Quantitative Analysis Platform
Author: Elite Quant Developer
"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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
    """Secure atomic data fetching with error handling"""
    
    @staticmethod
    @st.cache_data(ttl=300)
    def fetch_data(symbol, period="1mo", interval="30m"):
        """Fetch market data with proper error handling and index flattening"""
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
            data.columns = data.columns.get_level_values(0)
            return data
        except Exception as e:
            st.sidebar.error(f"Data fetch error: {str(e)}")
            return pd.DataFrame()

# =============================================================================
# KALMAN FILTER STATISTICAL ARBITRAGE
# =============================================================================

class KalmanArbitrageEngine:
    """Dynamic equilibrium tracking using Kalman Filter"""
    
    def __init__(self, data, window_size=30):
        self.data = data
        self.window_size = window_size
        self.price = data['Close'] if not data.empty else pd.Series(dtype=float)
        self.volatility = data['High'] - data['Low'] if not data.empty else pd.Series(dtype=float)
    
    def calculate_rolling_volatility(self):
        """Calculate rolling volatility for positions"""
        if len(self.volatility) >= 15:
            returns = self.volatility.pct_change().dropna()
            return returns.rolling(window=15).std() * np.sqrt(365)
        return pd.Series(index=self.data.index, dtype=float)
    
    def estimate_state_mean(self):
        """Kalman filter state estimation using recursive calculation"""
        if len(self.price) < 3:
            return pd.Series(index=self.data.index, dtype=float)
        
        state_means = []
        current_mean = self.price.iloc[0]
        process_noise = 0.01
        observation_noise = 0.05
        estimate_cov = 1.0
        
        for price in self.price.values:
            # Prediction
            predicted_mean = current_mean
            predicted_cov = estimate_cov + process_noise
            
            # Update
            kalman_gain = predicted_cov / (predicted_cov + observation_noise)
            current_mean = predicted_mean + kalman_gain * (price - predicted_mean)
            estimate_cov = (1 - kalman_gain) * predicted_cov
            state_means.append(current_mean)
        
        return pd.Series(state_means, index=self.price.index)
    
    def calculate_zscore(self):
        """Calculate Z-Score for statistical arbitrage"""
        state_mean = self.estimate_state_mean()
        if len(state_mean) < 20:
            return pd.Series(index=self.data.index, dtype=float)
        
        spread = self.price - state_mean
        rolling_std = spread.rolling(window=20).std()
        zscore = (spread - spread.rolling(window=20).mean()) / rolling_std
        return zscore.replace([np.inf, -np.inf], 0).fillna(0)
    
    def generate_signals(self):
        """Generate statistical arbitrage signals"""
        zscore = self.calculate_zscore()
        if zscore.empty:
            return {"signal": "HOLD", "strength": 0.0, "zscore": 0.0}
        
        current_zscore = zscore.iloc[-1] if not zscore.empty else 0.0
        abs_zscore = abs(current_zscore)
        
        if current_zscore >= 2.0:
            signal = "STRONG_SELL"
            strength = min(100.0, abs_zscore * 30)
        elif current_zscore >= 1.0:
            signal = "SELL"
            strength = min(70.0, abs_zscore * 20)
        elif current_zscore <= -2.0:
            signal = "STRONG_BUY"
            strength = min(100.0, abs_zscore * 30)
        elif current_zscore <= -1.0:
            signal = "BUY"
            strength = min(70.0, abs_zscore * 20)
        else:
            signal = "HOLD"
            strength = max(20.0, 30.0 - abs_zscore * 10)
        
        return {
            "signal": signal,
            "strength": strength,
            "zscore": current_zscore
        }

# =============================================================================
# ATR VOLATILITY BREAKOUT ENGINE
# =============================================================================

class ATRBreakoutEngine:
    """Institutional ATR channel breakout detection"""
    
    def __init__(self, data, atr_period=14, multiplier=2.0):
        self.data = data
        self.atr_period = atr_period
        self.multiplier = multiplier
        
        if not data.empty:
            self.high = data['High']
            self.low = data['Low']
            self.close = data['Close']
            self.volume = data['Volume']
    
    def calculate_atr(self):
        """Average True Range calculation"""
        if self.data.empty:
            return pd.Series(dtype=float)
        
        high = self.high
        low = self.low
        close = self.close.shift(1)
        
        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(window=self.atr_period).mean()
        return atr.fillna(0)
    
    def calculate_channels(self):
        """Calculate ATR upper and lower channels"""
        atr = self.calculate_atr()
        if self.data.empty or atr.empty:
            return pd.DataFrame()
        
        upper_channel = self.close.shift(1) + (self.multiplier * atr)
        lower_channel = self.close.shift(1) - (self.multiplier * atr)
        
        channels = pd.DataFrame({
            'Upper': upper_channel,
            'Lower': lower_channel,
            'Middle': self.close.shift(1)
        })
        return channels.fillna(method='bfill')
    
    def calculate_volume_ratio(self):
        """Relative volume ratio for confirmation"""
        if self.data.empty or len(self.volume) < 20:
            return pd.Series(dtype=float)
        
        avg_volume = self.volume.rolling(window=20).mean()
        volume_ratio = self.volume / avg_volume
        return volume_ratio.replace([np.inf, -np.inf], 0).fillna(0)
    
    def generate_signals(self):
        """Generate ATR breakout signals"""
        if self.data.empty:
            return {"signal": "HOLD", "strength": 0.0, "atr": 0.0}
        
        channels = self.calculate_channels()
        volume_ratio = self.calculate_volume_ratio()
        
        if channels.empty or len(volume_ratio) < 1:
            return {"signal": "HOLD", "strength": 0.0, "atr": 0.0}
        
        current_close = self.close.iloc[-1]
        upper = channels['Upper'].iloc[-1]
        lower = channels['Lower'].iloc[-1]
        current_volume_ratio = volume_ratio.iloc[-1]
        atr_value = self.calculate_atr().iloc[-1]
        
        strong_volume = current_volume_ratio > 1.5
        moderate_volume = current_volume_ratio > 1.0
        
        if current_close > upper and strong_volume:
            signal = "STRONG_BUY"
            strength = min(100.0, 70.0 + current_volume_ratio * 15)
        elif current_close > upper and moderate_volume:
            signal = "BUY"
            strength = min(80.0, 50.0 + current_volume_ratio * 10)
        elif current_close < lower and strong_volume:
            signal = "STRONG_SELL"
            strength = min(100.0, 70.0 + current_volume_ratio * 15)
        elif current_close < lower and moderate_volume:
            signal = "SELL"
            strength = min(80.0, 50.0 + current_volume_ratio * 10)
        else:
            signal = "HOLD"
            strength = 30.0
        
        return {
            "signal": signal,
            "strength": strength,
            "atr": atr_value,
            "volume_ratio": current_volume_ratio
        }

# =============================================================================
# ORDER FLOW IMBALANCE ENGINE (FVG & INSTITUTIONAL BLOCKS)
# =============================================================================

class OrderFlowEngine:
    """Fair Value Gap and institutional block detection"""
    
    def __init__(self, data):
        self.data = data
        if not data.empty:
            self.high = data['High']
            self.low = data['Low']
            self.open = data['Open']
            self.close = data['Close']
    
    def detect_fair_value_gaps(self, lookback=5):
        """Identify Fair Value Gaps (3-candle displacement pattern)"""
        if self.data.empty or len(self.data) < 10:
            return pd.DataFrame()
        
        fvg_data = []
        
        for i in range(2, len(self.data) - 1):
            # Bullish FVG: Current low > Previous two candles high
            if self.low.iloc[i] > self.high.iloc[i-2]:
                gap_size = self.low.iloc[i] - self.high.iloc[i-2]
                if gap_size > 0:
                    fvg_data.append({
                        'index': self.data.index[i],
                        'type': 'bullish',
                        'top': self.low.iloc[i],
                        'bottom': self.high.iloc[i-2],
                        'size': gap_size
                    })
            
            # Bearish FVG: Current high < Previous two candles low
            if self.high.iloc[i] < self.low.iloc[i-2]:
                gap_size = self.low.iloc[i-2] - self.high.iloc[i]
                if gap_size > 0:
                    fvg_data.append({
                        'index': self.data.index[i],
                        'type': 'bearish',
                        'top': self.low.iloc[i-2],
                        'bottom': self.high.iloc[i],
                        'size': gap_size
                    })
        
        return pd.DataFrame(fvg_data)
    
    def detect_institutional_blocks(self, lookback=10):
        """Identify institutional order blocks (last opposite candle before strong move)"""
        if self.data.empty or len(self.data) < lookback:
            return pd.DataFrame()
        
        block_data = []
        price_change_threshold = 0.02  # 2% minimum move
        
        for i in range(1, len(self.data) - 2):
            current_change = (self.close.iloc[i] - self.close.iloc[i-1]) / self.close.iloc[i-1]
            
            if abs(current_change) > price_change_threshold:
                if current_change > 0:  # Bullish move
                    block_type = 'bullish'
                    block_price = self.low.iloc[i-1]
                else:  # Bearish move
                    block_type = 'bearish'
                    block_price = self.high.iloc[i-1]
                
                block_data.append({
                    'index': self.data.index[i-1],
                    'type': block_type,
                    'price': block_price,
                    'move': current_change * 100
                })
        
        return pd.DataFrame(block_data)
    
    def calculate_imbalance_score(self):
        """Calculate order flow imbalance score"""
        fvg_data = self.detect_fair_value_gaps()
        block_data = self.detect_institutional_blocks()
        
        if self.data.empty:
            return {"signal": "HOLD", "strength": 0.0, "fvg_count": 0, "block_count": 0}
        
        current_price = self.close.iloc[-1] if not self.close.empty else 0
        
        # Count relevant FVGs near current price (within 1%)
        score = 0
        bullish_indicators = 0
        bearish_indicators = 0
        
        if not fvg_data.empty:
            recent_fvg = fvg_data.tail(3)
            for _, fvg in recent_fvg.iterrows():
                if abs(fvg['top'] - current_price) / current_price < 0.01:
                    if fvg['type'] == 'bullish':
                        bullish_indicators += 1
                        score += 20
                    else:
                        bearish_indicators += 1
                        score -= 20
        
        if not block_data.empty:
            recent_blocks = block_data.tail(2)
            for _, block in recent_blocks.iterrows():
                if abs(block['price'] - current_price) / current_price < 0.01:
                    if block['type'] == 'bullish':
                        bullish_indicators += 1
                        score += 15
                    else:
                        bearish_indicators += 1
                        score -= 15
        
        if score >= 40:
            signal = "STRONG_BUY"
            strength = min(95.0, score + bullish_indicators * 5)
        elif score >= 20:
            signal = "BUY"
            strength = min(75.0, score + bullish_indicators * 3)
        elif score <= -40:
            signal = "STRONG_SELL"
            strength = min(95.0, abs(score) + bearish_indicators * 5)
        elif score <= -20:
            signal = "SELL"
            strength = min(75.0, abs(score) + bearish_indicators * 3)
        else:
            signal = "HOLD"
            strength = 30.0
        
        return {
            "signal": signal,
            "strength": strength,
            "fvg_count": len(fvg_data) if not fvg_data.empty else 0,
            "block_count": len(block_data) if not block_data.empty else 0,
            "score": score
        }

# =============================================================================
# COMPOSITE CERTAINTY SCORING ENGINE
# =============================================================================

class CompositeScoringEngine:
    """Unified multivariable scoring system"""
    
    def __init__(self, kalman_result, atr_result, flow_result):
        self.kalman_result = kalman_result
        self.atr_result = atr_result
        self.flow_result = flow_result
    
    def calculate_composite_score(self):
        """Calculate weighted composite certainty score"""
        
        # Weights for each strategy
        weights = {
            'kalman': 0.35,
            'atr': 0.30,
            'flow': 0.35
        }
        
        # Signal mapping for numerical scoring
        signal_values = {
            'STRONG_BUY': 1.0,
            'BUY': 0.6,
            'HOLD': 0.0,
            'SELL': -0.6,
            'STRONG_SELL': -1.0
        }
        
        # Calculate weighted score
        total_score = 0.0
        total_certainty = 0.0
        
        # Kalman component
        kalman_signal = self.kalman_result['signal']
        kalman_strength = self.kalman_result['strength']
        kalman_score = signal_values.get(kalman_signal, 0.0)
        total_score += kalman_score * weights['kalman']
        total_certainty += kalman_strength * weights['kalman']
        
        # ATR component
        atr_signal = self.atr_result['signal']
        atr_strength = self.atr_result['strength']
        atr_score = signal_values.get(atr_signal, 0.0)
        total_score += atr_score * weights['atr']
        total_certainty += atr_strength * weights['atr']
        
        # Order Flow component
        flow_signal = self.flow_result['signal']
        flow_strength = self.flow_result['strength']
        flow_score = signal_values.get(flow_signal, 0.0)
        total_score += flow_score * weights['flow']
        total_certainty += flow_strength * weights['flow']
        
        # Determine final signal
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
        
        # Calculate certainty percentage
        certainty = min(95.0, max(20.0, total_certainty + abs(total_score) * 15))
        
        # Generate reasoning
        reasoning = self.generate_reasoning()
        
        return {
            'signal': final_signal,
            'certainty': round(certainty, 2),
            'composite_score': round(total_score, 3),
            'reasoning': reasoning,
            'components': {
                'kalman': kalman_signal,
                'atr': atr_signal,
                'flow': flow_signal
            }
        }
    
    def generate_reasoning(self):
        """Generate mathematical reasoning for signals"""
        reasons = []
        
        # Kalman reasoning
        kalman_signal = self.kalman_result['signal']
        zscore = self.kalman_result.get('zscore', 0)
        if kalman_signal == 'STRONG_BUY':
            reasons.append(f"Kalman Z-Score at {zscore:.2f} indicates extreme undervaluation")
        elif kalman_signal == 'STRONG_SELL':
            reasons.append(f"Kalman Z-Score at {zscore:.2f} indicates extreme overvaluation")
        elif kalman_signal == 'BUY':
            reasons.append(f"Kalman Z-Score at {zscore:.2f} suggests mean reversion opportunity")
        elif kalman_signal == 'SELL':
            reasons.append(f"Kalman Z-Score at {zscore:.2f} suggests overextension")
        else:
            reasons.append(f"Kalman Z-Score at {zscore:.2f} within equilibrium range")
        
        # ATR reasoning
        atr_value = self.atr_result.get('atr', 0)
        volume_ratio = self.atr_result.get('volume_ratio', 0)
        if volume_ratio > 1.5:
            reasons.append(f"High volume breakout ({volume_ratio:.2f}x average) with ATR {atr_value:.4f}")
        elif volume_ratio > 1.0:
            reasons.append(f"Moderate volume confirmation {volume_ratio:.2f}x with ATR {atr_value:.4f}")
        else:
            reasons.append(f"Volume below threshold {volume_ratio:.2f}x; breakout unconfirmed")
        
        # Order flow reasoning
        fvg_count = self.flow_result.get('fvg_count', 0)
        block_count = self.flow_result.get('block_count', 0)
        imbalance_score = self.flow_result.get('score', 0)
        reasons.append(f"Order flow imbalance score of {imbalance_score} with {fvg_count} FVGs and {block_count} institutional blocks detected")
        
        return reasons

# =============================================================================
# UI COMPONENTS
# =============================================================================

class InstitutionalUI:
    """Premium institutional UI components"""
    
    @staticmethod
    def inject_css():
        """Inject custom CSS for premium look"""
        st.markdown("""
        <style>
        .stApp {
            background-color: #0d1117;
            color: #c9d1d9;
        }
        .plot-container {
            border: 1px solid #21262d;
            border-radius: 8px;
            padding: 10px;
            margin: 10px 0;
        }
        .signal-card-buy {
            background: linear-gradient(135deg, #0e4429, #1a1b27);
            border-left: 4px solid #26a69a;
            border-radius: 6px;
            padding: 15px;
            margin: 5px 0;
        }
        .signal-card-sell {
            background: linear-gradient(135deg, #4a1d24, #1a1b27);
            border-left: 4px solid #ef5350;
            border-radius: 6px;
            padding: 15px;
            margin: 5px 0;
        }
        .signal-card-hold {
            background: linear-gradient(135deg, #2d1b4e, #1a1b27);
            border-left: 4px solid #ab47bc;
            border-radius: 6px;
            padding: 15px;
            margin: 5px 0;
        }
        .metric-container {
            background-color: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 15px;
            margin: 5px 0;
        }
        .stButton > button {
            background-color: #238636;
            color: white;
            border-radius: 6px;
            border: none;
            padding: 10px 25px;
            font-weight: bold;
        }
        .stButton > button:hover {
            background-color: #
