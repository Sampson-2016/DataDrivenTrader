from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import pandas as pd

from ..models import StockDaily


@dataclass
class StrategyResult:
    strategy_name: str
    stock_code: str
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float
    total_return: float
    annual_return: Optional[float]
    max_drawdown: Optional[float]
    win_rate: Optional[float]
    total_trades: Optional[int]
    profit_trades: Optional[int]
    loss_trades: Optional[int]
    trades: List[Dict[str, Any]]
    equity_curve: List[Dict[str, Any]]
    kline_data: List[Dict[str, Any]]
    signals_info: Optional[Dict[str, Any]] = None


class StrategyBase(ABC):
    """策略基类，定义策略接口规范"""
    
    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.strategy_name = self.__class__.__name__
    
    @abstractmethod
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算策略所需的指标
        
        Args:
            df: 包含股票数据的DataFrame
            
        Returns:
            添加了策略指标的DataFrame
        """
        pass
    
    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """生成交易信号
        
        Args:
            df: 包含股票数据和指标的DataFrame
            
        Returns:
            添加了signal列的DataFrame (1=买入, -1=卖出, 0=持有)
        """
        pass
    
    @abstractmethod
    def get_required_fields(self) -> List[str]:
        """获取策略需要的字段列表
        
        Returns:
            字段名列表
        """
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """获取策略名称
        
        Returns:
            策略名称字符串
        """
        pass
    
    @abstractmethod
    def get_params(self) -> Dict[str, Any]:
        """获取策略参数配置
        
        Returns:
            参数字典
        """
        pass
    
    def run_backtest(
        self,
        stock_data: List[StockDaily],
        initial_capital: float = None,
        **kwargs
    ) -> StrategyResult:
        """运行回测
        
        Args:
            stock_data: 股票数据列表
            initial_capital: 初始资金
            **kwargs: 策略特定参数（如market_cap）
            
        Returns:
            StrategyResult对象
        """
        init_cap = initial_capital or self.initial_capital
        
        df = self._prepare_data(stock_data)
        df = self.calculate_indicators(df)
        df = self.generate_signals(df, **kwargs)
        
        result = self._execute_backtest(df, init_cap)
        
        return result
    
    def _prepare_data(self, stock_data: List[StockDaily]) -> pd.DataFrame:
        """准备数据"""
        data = []
        for s in stock_data:
            data.append({
                'trade_date': s.trade_date,
                'open_price': s.open_price,
                'high_price': s.high_price,
                'low_price': s.low_price,
                'close_price': s.close_price,
                'volume': s.volume,
                'amount': s.amount,
                'stock_code': s.stock_code
            })
        
        df = pd.DataFrame(data)
        df = df.sort_values('trade_date').reset_index(drop=True)
        return df
    
    def _execute_backtest(
        self,
        df: pd.DataFrame,
        initial_capital: float
    ) -> StrategyResult:
        """执行回测逻辑"""
        cash = initial_capital
        position = 0
        cost_price = 0.0
        trades = []
        equity_curve = []
        
        for idx, row in df.iterrows():
            current_date = row['trade_date']
            close_price = row['close_price']
            signal = row.get('signal', 0)
            
            if signal == 1 and position == 0:
                max_shares = int(cash / (close_price * 100)) * 100
                while max_shares >= 100:
                    amount = max_shares * close_price
                    commission = self._calculate_commission(amount, is_sell=False)
                    total_cost = amount + commission
                    
                    if total_cost <= cash:
                        position = max_shares
                        cost_price = close_price
                        cash -= total_cost
                        
                        trades.append({
                            'trade_type': 'buy',
                            'date': current_date,
                            'price': close_price,
                            'shares': max_shares,
                            'amount': amount,
                            'commission': commission
                        })
                        break
                    else:
                        max_shares -= 100
            
            elif signal == -1 and position > 0:
                amount = position * close_price
                commission = self._calculate_commission(amount, is_sell=True)
                cash += amount - commission
                
                trades.append({
                    'trade_type': 'sell',
                    'date': current_date,
                    'price': close_price,
                    'shares': position,
                    'amount': amount,
                    'commission': commission
                })
                
                position = 0
                cost_price = 0.0
            
            market_value = position * close_price if position > 0 else 0
            total_equity = cash + market_value
            
            equity_curve.append({
                'date': current_date,
                'equity': total_equity,
                'benchmark': initial_capital * (close_price / df.iloc[0]['close_price'])
            })
        
        if position > 0:
            last_price = df.iloc[-1]['close_price']
            amount = position * last_price
            commission = self._calculate_commission(amount, is_sell=True)
            cash += amount - commission
            
            trades.append({
                'trade_type': 'sell',
                'date': df.iloc[-1]['trade_date'],
                'price': last_price,
                'shares': position,
                'amount': amount,
                'commission': commission
            })
        
        final_equity = cash
        total_return = (final_equity - initial_capital) / initial_capital * 100
        
        trading_days = len(df)
        years = trading_days / 252
        annual_return = ((final_equity / initial_capital) ** (1 / years) - 1) * 100 if years > 0 else 0
        
        equity_series = pd.Series([e['equity'] for e in equity_curve])
        rolling_max = equity_series.expanding().max()
        drawdown = (equity_series - rolling_max) / rolling_max
        max_drawdown = drawdown.min() * 100
        
        buy_trades = [t for t in trades if t['trade_type'] == 'buy']
        sell_trades = [t for t in trades if t['trade_type'] == 'sell']
        
        profit_trades = 0
        loss_trades = 0
        
        for buy, sell in zip(buy_trades, sell_trades):
            if sell['price'] > buy['price']:
                profit_trades += 1
            else:
                loss_trades += 1
        
        total_trades = len(buy_trades)
        win_rate = profit_trades / total_trades * 100 if total_trades > 0 else 0
        
        kline_data = []
        for idx, row in df.iterrows():
            kline_data.append({
                'date': row['trade_date'],
                'open': row['open_price'],
                'close': row['close_price'],
                'high': row['high_price'],
                'low': row['low_price'],
                'volume': row['volume']
            })
        
        return StrategyResult(
            strategy_name=self.strategy_name,
            stock_code=df.iloc[0]['stock_code'] if len(df) > 0 else '',
            start_date=str(df.iloc[0]['trade_date']) if len(df) > 0 else '',
            end_date=str(df.iloc[-1]['trade_date']) if len(df) > 0 else '',
            initial_capital=initial_capital,
            final_capital=final_equity,
            total_return=total_return,
            annual_return=annual_return,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            total_trades=total_trades,
            profit_trades=profit_trades,
            loss_trades=loss_trades,
            trades=trades,
            equity_curve=equity_curve,
            kline_data=kline_data,
            signals_info=self._extract_signals_info(df)
        )
    
    def _calculate_commission(self, amount: float, is_sell: bool = False) -> float:
        """计算手续费"""
        commission_rate = 0.0003
        min_commission = 5.0
        commission = max(amount * commission_rate, min_commission)
        stamp_duty = amount * 0.001 if is_sell else 0
        return commission + stamp_duty
    
    def _extract_signals_info(self, df: pd.DataFrame) -> Dict[str, Any]:
        """提取信号信息"""
        signals_info = {
            'breakout_days': [],
            'decay_reached_days': [],
            'signal_days': []
        }
        
        for idx, row in df.iterrows():
            if row.get('breakout_day_marked'):
                signals_info['breakout_days'].append({
                    'date': str(row['trade_date']),
                    'price': row['close_price']
                })
            
            if row.get('decay_reached'):
                signals_info['decay_reached_days'].append({
                    'date': str(row['trade_date']),
                    'decay_rate': row.get('decay_rate', 0)
                })
            
            if row.get('signal') == 1:
                signals_info['signal_days'].append({
                    'date': str(row['trade_date']),
                    'price': row['close_price']
                })
        
        return signals_info


class StrategyRegistry:
    """策略注册器，管理所有策略"""
    
    _strategies = {}
    
    @classmethod
    def register(cls, strategy_class):
        """注册策略"""
        instance = strategy_class()
        cls._strategies[instance.get_strategy_name()] = strategy_class
        return strategy_class
    
    @classmethod
    def get_strategy(cls, name: str, **kwargs) -> StrategyBase:
        """获取策略实例"""
        if name not in cls._strategies:
            raise ValueError(f"Strategy '{name}' not found")
        return cls._strategies[name](**kwargs)
    
    @classmethod
    def get_all_strategies(cls) -> List[Dict[str, Any]]:
        """获取所有策略"""
        return [
            {
                'name': name,
                'class': cls._strategies[name]
            }
            for name in cls._strategies.keys()
        ]
