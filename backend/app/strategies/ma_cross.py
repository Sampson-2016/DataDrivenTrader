import pandas as pd

from .base import StrategyBase, StrategyRegistry


@StrategyRegistry.register
class MACrossStrategy(StrategyBase):
    """MA交叉策略 - 基于均线交叉的传统策略"""
    
    def __init__(self, initial_capital: float = 100000.0, ma_period: int = 5):
        super().__init__(initial_capital)
        self.ma_period = ma_period
        self.strategy_name = f'MA{ma_period}_Cross'
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算MA指标"""
        df = df.copy()
        df[f'ma{self.ma_period}'] = df['close_price'].rolling(window=self.ma_period).mean()
        return df
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """生成MA交叉信号"""
        df = df.copy()
        
        prev_close = df['close_price'].shift(1)
        prev_ma = df[f'ma{self.ma_period}'].shift(1)
        current_ma = df[f'ma{self.ma_period}']
        
        df['signal'] = 0
        df.loc[
            (prev_close <= prev_ma) & (df['close_price'] > current_ma),
            'signal'
        ] = 1
        
        df.loc[
            (prev_close >= prev_ma) & (df['close_price'] < current_ma),
            'signal'
        ] = -1
        
        return df
    
    def get_required_fields(self) -> list:
        return ['close_price']
    
    def get_strategy_name(self) -> str:
        return self.strategy_name
    
    def get_params(self) -> dict:
        return {'ma_period': self.ma_period}
