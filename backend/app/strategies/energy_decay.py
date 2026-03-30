import pandas as pd
import numpy as np
from typing import Optional, Dict, Any

from .base import StrategyBase, StrategyRegistry


class EnergyDecayStrategy(StrategyBase):
    """能量衰减策略 - 基于量能衰减的启动信号策略
    
    策略逻辑：
    1. 低位突破日识别：股价 < MA250 * 0.7 且 量比 >= 1.5
    2. 量能衰减达标：当前量能 / 突破日量能 <= 动态阈值
       - 小盘股(<100亿): ≤ 0.35
       - 中盘股(100-300亿): ≤ 0.30
       - 大盘股(>=300亿): ≤ 0.25
    3. 启动信号确认：量比 >= 1.1 (5日均量) 且 价格 >= 突破日阳线实体 * 2/3
    """
    
    def __init__(
        self,
        initial_capital: float = 100000.0,
        decay_threshold_small: float = 0.35,
        decay_threshold_mid: float = 0.30,
        decay_threshold_large: float = 0.25,
        breakout_price_ratio: float = 0.7,
        breakout_volume_ratio: float = 1.5,
        signal_volume_ratio: float = 1.1,
        price_support_ratio: float = 0.667
    ):
        super().__init__(initial_capital)
        self.strategy_name = 'Energy_Decay'
        
        self.decay_threshold_small = decay_threshold_small
        self.decay_threshold_mid = decay_threshold_mid
        self.decay_threshold_large = decay_threshold_large
        
        self.breakout_price_ratio = breakout_price_ratio
        self.breakout_volume_ratio = breakout_volume_ratio
        self.signal_volume_ratio = signal_volume_ratio
        self.price_support_ratio = price_support_ratio
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算策略所需指标"""
        df = df.copy()
        
        # 计算MA250 (年线)
        df['ma250'] = df['close_price'].rolling(window=250).mean()
        
        # 计算5日均量
        df['volume_ma5'] = df['volume'].rolling(window=5).mean()
        
        # 计算量比 (当日量能 / 5日均量)
        df['volume_ratio'] = df['volume'] / df['volume_ma5']
        
        # 计算阳线实体
        df['real_body'] = df['close_price'] - df['open_price']
        df['real_body_abs'] = df['real_body'].abs()
        
        # 标记突破日
        df['breakout_day'] = (
            (df['close_price'] < df['ma250'] * self.breakout_price_ratio) &
            (df['volume_ratio'] >= self.breakout_volume_ratio)
        )
        
        return df
    
    def find_breakout_day(self, df: pd.DataFrame) -> Optional[int]:
        """查找最近一次低位突破日
        
        Args:
            df: 包含指标的DataFrame
            
        Returns:
            突破日的索引，如果没有找到则返回None
        """
        breakout_days = df[df['breakout_day']].index.tolist()
        
        if not breakout_days:
            return None
        
        # 返回最近一次突破日
        return breakout_days[-1]
    
    def classify_market_cap(self, market_cap: Optional[float]) -> str:
        """根据市值分类
        
        Args:
            market_cap: 市值（亿元）
            
        Returns:
            'small' | 'mid' | 'large'
        """
        if market_cap is None:
            return 'mid'  # 默认使用中等阈值
        
        if market_cap < 100:
            return 'small'
        elif market_cap < 300:
            return 'mid'
        else:
            return 'large'
    
    def get_decay_threshold(self, market_cap: Optional[float]) -> float:
        """获取动态衰减阈值"""
        category = self.classify_market_cap(market_cap)
        
        if category == 'small':
            return self.decay_threshold_small
        elif category == 'mid':
            return self.decay_threshold_mid
        else:
            return self.decay_threshold_large
    
    def calculate_decay_rate(self, df: pd.DataFrame, breakout_idx: int) -> pd.Series:
        """计算量能衰减率
        
        Args:
            df: DataFrame
            breakout_idx: 突破日索引
            
        Returns:
            衰减率序列
        """
        breakout_volume = df.iloc[breakout_idx]['volume']
        
        if breakout_volume == 0:
            return pd.Series([np.nan] * len(df))
        
        decay_rate = df['volume'] / breakout_volume
        return decay_rate
    
    def check_price_support(
        self,
        df: pd.DataFrame,
        current_idx: int,
        breakout_idx: int
    ) -> bool:
        """检查价格是否维持在突破日阳线2/3位置以上
        
        Args:
            df: DataFrame
            current_idx: 当前索引
            breakout_idx: 突破日索引
            
        Returns:
            True=满足支撑条件, False=不满足
        """
        breakout_row = df.iloc[breakout_idx]
        current_row = df.iloc[current_idx]
        
        # 突破日阳线实体
        breakout_body = breakout_row['real_body']
        
        # 突破日阳线实体2/3位置
        support_level = breakout_row['open_price'] + abs(breakout_body) * self.price_support_ratio
        
        # 当前价格是否在支撑位以上
        return current_row['close_price'] >= support_level
    
    def generate_signals(self, df: pd.DataFrame, market_cap: Optional[float] = None) -> pd.DataFrame:
        """生成能量衰减策略信号
        
        Args:
            df: 包含指标的DataFrame
            market_cap: 市值（亿元），用于动态阈值
            
        Returns:
            添加了signal列的DataFrame
        """
        df = df.copy()
        df['signal'] = 0
        df['decay_rate'] = np.nan
        df['decay_reached'] = False
        df['signal_volume_check'] = False
        df['signal_price_check'] = False
        
        # 查找突破日
        breakout_idx = self.find_breakout_day(df)
        
        if breakout_idx is None:
            return df
        
        # 计算衰减率
        df['decay_rate'] = self.calculate_decay_rate(df, breakout_idx)
        
        # 获取动态阈值
        decay_threshold = self.get_decay_threshold(market_cap)
        
        # 从突破日后开始检查
        for idx in range(breakout_idx + 1, len(df)):
            decay_rate = df.iloc[idx]['decay_rate']
            
            # 检查是否达标
            if decay_rate <= decay_threshold:
                df.at[df.index[idx], 'decay_reached'] = True
                
                # 检查5日均量比
                volume_ratio_5day = df.iloc[idx]['volume_ratio']
                volume_check = volume_ratio_5day >= self.signal_volume_ratio
                df.at[df.index[idx], 'signal_volume_check'] = volume_check
                
                # 检查价格支撑
                price_check = self.check_price_support(df, idx, breakout_idx)
                df.at[df.index[idx], 'signal_price_check'] = price_check
                
                # 同时满足两个条件才生成买入信号
                if volume_check and price_check:
                    df.at[df.index[idx], 'signal'] = 1
        
        return df
    
    def get_required_fields(self) -> list:
        return ['open_price', 'close_price', 'volume']
    
    def get_strategy_name(self) -> str:
        return self.strategy_name
    
    def get_params(self) -> dict:
        return {
            'decay_threshold_small': self.decay_threshold_small,
            'decay_threshold_mid': self.decay_threshold_mid,
            'decay_threshold_large': self.decay_threshold_large,
            'breakout_price_ratio': self.breakout_price_ratio,
            'breakout_volume_ratio': self.breakout_volume_ratio,
            'signal_volume_ratio': self.signal_volume_ratio,
            'price_support_ratio': self.price_support_ratio
        }
    
    def _extract_signals_info(self, df: pd.DataFrame) -> Dict[str, Any]:
        """提取信号信息"""
        signals_info = {
            'breakout_days': [],
            'decay_reached_days': [],
            'volume_check_days': [],
            'price_check_days': [],
            'signal_days': []
        }
        
        for idx, row in df.iterrows():
            if row.get('breakout_day'):
                signals_info['breakout_days'].append({
                    'date': str(row['trade_date']),
                    'price': row['close_price'],
                    'volume_ratio': row['volume_ratio']
                })
            
            if row.get('decay_reached'):
                signals_info['decay_reached_days'].append({
                    'date': str(row['trade_date']),
                    'price': row['close_price'],
                    'decay_rate': row['decay_rate']
                })
            
            if row.get('signal_volume_check'):
                signals_info['volume_check_days'].append({
                    'date': str(row['trade_date']),
                    'price': row['close_price'],
                    'volume_ratio': row['volume_ratio']
                })
            
            if row.get('signal_price_check'):
                signals_info['price_check_days'].append({
                    'date': str(row['trade_date']),
                    'price': row['close_price']
                })
            
            if row.get('signal') == 1:
                signals_info['signal_days'].append({
                    'date': str(row['trade_date']),
                    'price': row['close_price']
                })
        
        return signals_info
