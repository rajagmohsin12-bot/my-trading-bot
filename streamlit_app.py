"""
PREMIUM INSTITUTIONAL MARKET SCANNER & TRADING DASHBOARD
Enterprise-Grade Quantitative Analysis Platform
Version: 2.5.0 (Strict Indentation Blueprint Fix)
"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# INSTITUTIONAL QUANTITATIVE STRATEGIES (DEEPSEEK ARCHITECTURE)
# ============================================================================

class KalmanFilterArbitrage:
    """Kalman Filter Statistical Arbitrage - Dynamic Equilibrium Tracking"""
    
    def __init__(self, transition_covariance: float = 0.01, observation_covariance: float = 0.5):
        self.transition_covariance = transition_covariance
        self.observation_covariance = observation_covariance
    
    def filter_signal(self, prices: np.ndarray) -> dict:
        """Apply Kalman Filter to detect statistical mispricings"""
        if len(prices) < 20:
            return {'kalman_value': np.nan, 'z_score': 0, 'signal': 'NEUTRAL'}
        
        n = len(prices)
        state_means = np.zeros(n)
        state_covs = np.zeros(n)
        
        state_means = prices
        state_covs = 1.0
        
        for i in range(1, n):
            pred_mean = state_means[i-1]
            pred_cov = state_covs[i-1] + self.transition_covariance
            
            kalman_gain = pred_cov / (pred_cov + self.observation_covariance)
            state_means[i] = pred_mean + kalman_gain * (prices[i] - pred_mean)
            state_covs[i] = (1 - kalman_gain) * pred_cov
        
        current_price = prices[-1]
        kalman_value = state_means[-1]
        residuals = prices - state_means
        std_dev = np.std(residuals[-20:]) if len(residuals) >= 20 else 1.0
        
        z_score = (current_price - kalman_value) / (std_dev if std_dev > 0 else 1.0)
        
        if z_score > 2.0:
            signal = 'SHORT'
        elif z_score < -2.0:
            signal = 'LONG'
        else:
            signal = 'NEUTRAL'
        
        return {
            'kalman_value': kalman_value,
            'z_score': z_score,
            'signal': signal,
            'current_price': current_price,
            'kalman_line': state_means
        }


class VolatilityBreakoutStrategy:
    """ATR Channel Breakout - Institutional Liquidity Sweep Detection"""
    
    def __init__(self, atr_period: int = 14, multiplier: float = 2.0):
        self.atr_period = atr_period
        self.multiplier = multiplier
    
    def calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
        """Calculate Average True Range"""
        high_low = high - low
        high_close = np.abs(high - close.shift())
        low_close = np.abs(low - close.shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return tr.rolling(window=self.atr_period).mean()
    
    def generate_signal(self, data: pd.DataFrame) -> dict:
        """Generate breakout signals with institutional volume confirmation"""
        if len(data) < self.atr_period + 20:
            return {'signal': 'NEUTRAL', 'atr_value': 0, 'upper_band': 0, 'lower_band': 0, 'volume_ratio': 1.0}
        
        atr = self.calculate_atr(data['High'], data['Low'], data['Close'])
        current_atr = atr.iloc[-1]
        
        sma = data['Close'].rolling(20).mean()
        upper_band = sma + (self.multiplier * atr)
        lower_band = sma - (self.multiplier * atr)
        
        current_price = data['Close'].iloc[-1]
        prev_price = data['Close'].iloc[-2]
        
        avg_volume = data['Volume'].rolling(20).mean().iloc[-1]
        current_volume = data['Volume'].iloc[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        
        if prev_price <= upper_band.iloc[-2] and current_price > upper_band.iloc[-1] and volume_ratio > 1.5:
            signal = 'LONG'
        elif prev_price >= lower_band.iloc[-2] and current_price < lower_band.iloc[-1] and volume_ratio > 1.5:
            signal = 'SHORT'
        else:
            signal = 'NEUTRAL'
        
        return {
            'signal': signal,
            'atr_value': current_atr,
            'upper_band': upper_band,
            'lower_band': lower_band,
            'volume_ratio': volume_ratio
        }


class OrderFlowImbalanceStrategy:
    """Fair Value Gaps & Institutional Block Detection"""
    
    def __init__(self, lookback: int = 50):
        self.lookback = lookback
    
    def detect_fair_value_gaps(self, data: pd.DataFrame) -> list:
        """Detect Fair Value Gaps (FVG) indicating institutional footprint"""
        gaps = []
        if len(data) < 3:
            return gaps
        
        for i in range(2, len(data)):
            if data['Low'].iloc[i] > data['High'].iloc[i-2]:
                gaps.append({
                    'type': 'BULLISH_FVG',
                    'price': (data['Low'].iloc[i] + data['High'].iloc[i-2]) / 2,
                    'strength': (data['Low'].iloc[i] - data['High'].iloc[i-2]) / data['Close'].iloc[i] * 100
                })
            elif data['High'].iloc[i] < data['Low'].iloc[i-2]:
                gaps.append({
                    'type': 'BEARISH_FVG',
                    'price': (data['High'].iloc[i] + data['Low'].iloc[i-2]) / 2,
                    'strength': (data['High'].iloc[i] - data['Low'].iloc[i-2]) / data['Close'].iloc[i] * 100
                })
        return gaps[-5:]
    
    def calculate_order_flow_imbalance(self, data: pd.DataFrame) -> float:
        """Calculate cumulative order flow imbalance proxy"""
        if len(data) < 20:
            return 0.0
        
        price_change = data['Close'].diff()
        volume = data['Volume']
        
        buy_pressure = (price_change > 0) & (volume > volume.rolling(20).mean())
        sell_pressure = (price_change < 0) & (volume > volume.rolling(20).mean())
        
        buy_volume = volume[buy_pressure].sum()
        sell_volume = volume[sell_pressure].sum()
        
        total_volume = buy_volume + sell_volume
        if total_volume == 0:
            return 0.0
        
        return float((buy_volume - sell_volume) / total_volume * 100)
    
    def generate_signal(self, data: pd.DataFrame) -> dict:
        if len(data) < self.lookback:
            return {'signal': 'NEUTRAL', 'imbalance': 0, 'fvg': [], 'institutional_activity': 30}
        
        imbalance = self.calculate_order_flow_imbalance(data)
        fvg = self.detect_fair_value_gaps(data)
        
        institutional_activity = min(100, abs(imbalance) * 3) if imbalance != 0 else 30
        
        bullish_fvgs = len([g for g in fvg if g['type'] == 'BULLISH_FVG'])
        bearish_fvgs = len([g for g in fvg if g['type'] == 'BEARISH_FVG'])
        
        if imbalance > 20 and bullish_fvgs > bearish_fvgs:
            signal = 'LONG'
        elif imbalance < -20 and bearish_fvgs > bullish_fvgs:
            signal = 'SHORT'
        else:
            signal = 'NEUTRAL'
        
        return {
            'signal': signal,
            'imbalance': imbalance,
            'fvg': fvg,
            'institutional_activity': institutional_activity
        }


class InstitutionalCertaintyScorer:
    """Unified Composite Scoring System for Institutional Certainty"""
    
    def __init__(self):
        self.weights = {'kalman': 0.35, 'volatility': 0.30, 'orderflow': 0.35}
    
    def calculate_score(self, kalman: dict, vol: dict, orderflow: dict) -> dict:
        score_mapping = {'LONG': 100, 'SHORT': -100, 'NEUTRAL': 0}
        
        k_score = score_mapping[kalman.get('signal', 'NEUTRAL')]
        v_score = score_mapping[vol.get('signal', 'NEUTRAL')]
        o_score = score_mapping[orderflow.get('signal', 'NEUTRAL')]
        
        composite = (k_score * self.weights['kalman'] + v_score * self.weights['volatility'] + o_score * self.weights['orderflow'])
        certainty_score = (composite + 100) / 2
        
        if certainty_score >= 75:
            signal = "STRONG BUY"
        elif certainty_score >= 60:
            signal = "BUY"
        elif certainty_score <= 25:
            signal = "STRONG SELL"
        elif certainty_score <= 40:
            signal = "SELL"
        else:
            signal = "HOLD"
            
        return {'certainty_score': round(certainty_score, 2), 'signal': signal}

# ============================================================================
# DASHBOARD UI & RENDERING PIPELINE (GLOBAL TEMPLATE METHODS)
# ============================================================================

def generate_analytical_chart(data: pd.DataFrame, kalman_line: np.ndarray, title: str):
    """Render analytical candlestick charts safely with mathematical overlay matrices"""
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
    
    fig.add_trace(go.Candlestick(
        x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name="Market Candlestick Vector",
        increasing_line_color='#26a69a', decreasing_line_color='#ef5350'
    ), row=1, col=1)
    
    if kalman_line is not None and not np.isnan(kalman_line).all():
        fig.add_trace(go.Scatter(
            x=data.index, y=kalman_line, name="Kalman Filter Signal Line", line=dict(color='#dd6b20', width=2, dash='dot')
        ), row=1, col=1)
        
    colors = ['#26a69a' if c >= o else '#ef5350' for o, c in zip(data['Open'], data['Close'])]
    fig.add_trace(go.Bar(x=data.index, y=data['Volume'], marker_color=colors, name="Institutional Net Volume", opacity=0.4), row=2, col=1)
    
    fig.update_layout(xaxis_rangeslider_visible=False, template='plotly_dark', height=550)
    return fig


class MarketDataFetcher:
