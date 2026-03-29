import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple
from dataclasses import dataclass
from sqlalchemy.orm import Session

from .models import StockDaily, BacktestResult, TradeRecord


@dataclass
class Trade:
    trade_type: str
    date: date
    price: float
    shares: int
    amount: float


@dataclass
class Position:
    shares: int = 0
    cost_price: float = 0.0
    
    def is_empty(self) -> bool:
        return self.shares == 0


class BacktestEngine:
    def __init__(
        self,
        initial_capital: float = 100000.0,
        commission_rate: float = 0.0003,
        stamp_duty_rate: float = 0.001,
        min_commission: float = 5.0
    ):
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.stamp_duty_rate = stamp_duty_rate
        self.min_commission = min_commission
    
    def calculate_commission(self, amount: float, is_sell: bool = False) -> float:
        commission = max(amount * self.commission_rate, self.min_commission)
        stamp_duty = amount * self.stamp_duty_rate if is_sell else 0
        return commission + stamp_duty
    
    def calculate_ma(self, prices: pd.Series, period: int) -> pd.Series:
        return prices.rolling(window=period).mean()
    
    def generate_signals(self, df: pd.DataFrame, ma_period: int = 5) -> pd.DataFrame:
        df = df.copy()
        df['ma'] = self.calculate_ma(df['close_price'], ma_period)
        df['prev_close'] = df['close_price'].shift(1)
        df['prev_ma'] = df['ma'].shift(1)
        
        df['signal'] = 0
        df.loc[(df['prev_close'] <= df['prev_ma']) & (df['close_price'] > df['ma']), 'signal'] = 1
        df.loc[(df['prev_close'] >= df['prev_ma']) & (df['close_price'] < df['ma']), 'signal'] = -1
        
        return df
    
    def run_backtest(
        self,
        stock_data: List[StockDaily],
        ma_period: int = 5,
        initial_capital: float = None
    ) -> Tuple[dict, List[Trade], List[dict]]:
        if len(stock_data) < ma_period + 1:
            raise ValueError(f"Insufficient data: need at least {ma_period + 1} records")
        
        init_cap = initial_capital or self.initial_capital
        
        df = pd.DataFrame([{
            'trade_date': s.trade_date,
            'open_price': s.open_price,
            'high_price': s.high_price,
            'low_price': s.low_price,
            'close_price': s.close_price,
            'volume': s.volume
        } for s in stock_data])
        
        df = self.generate_signals(df, ma_period)
        
        cash = init_cap
        position = Position()
        trades: List[Trade] = []
        equity_curve: List[dict] = []
        
        for idx, row in df.iterrows():
            current_date = row['trade_date']
            close_price = row['close_price']
            signal = row['signal']
            
            if signal == 1 and position.is_empty():
                max_shares = int(cash / (close_price * 100)) * 100
                while max_shares >= 100:
                    amount = max_shares * close_price
                    commission = self.calculate_commission(amount, is_sell=False)
                    total_cost = amount + commission
                    
                    if total_cost <= cash:
                        position.shares = max_shares
                        position.cost_price = close_price
                        cash -= total_cost
                        
                        trades.append(Trade(
                            trade_type='buy',
                            date=current_date,
                            price=close_price,
                            shares=max_shares,
                            amount=amount
                        ))
                        break
                    else:
                        max_shares -= 100
            
            elif signal == -1 and not position.is_empty():
                amount = position.shares * close_price
                commission = self.calculate_commission(amount, is_sell=True)
                cash += amount - commission
                
                trades.append(Trade(
                    trade_type='sell',
                    date=current_date,
                    price=close_price,
                    shares=position.shares,
                    amount=amount
                ))
                
                position = Position()
            
            market_value = position.shares * close_price if not position.is_empty() else 0
            total_equity = cash + market_value
            
            equity_curve.append({
                'date': current_date,
                'equity': total_equity,
                'benchmark': init_cap * (close_price / df.iloc[ma_period]['close_price'])
            })
        
        if not position.is_empty():
            last_price = df.iloc[-1]['close_price']
            amount = position.shares * last_price
            commission = self.calculate_commission(amount, is_sell=True)
            cash += amount - commission
            
            trades.append(Trade(
                trade_type='sell',
                date=df.iloc[-1]['trade_date'],
                price=last_price,
                shares=position.shares,
                amount=amount
            ))
        
        final_equity = cash
        total_return = (final_equity - init_cap) / init_cap * 100
        
        trading_days = len(df)
        years = trading_days / 252
        annual_return = ((final_equity / init_cap) ** (1 / years) - 1) * 100 if years > 0 else 0
        
        equity_series = pd.Series([e['equity'] for e in equity_curve])
        rolling_max = equity_series.expanding().max()
        drawdown = (equity_series - rolling_max) / rolling_max
        max_drawdown = drawdown.min() * 100
        
        buy_trades = [t for t in trades if t.trade_type == 'buy']
        sell_trades = [t for t in trades if t.trade_type == 'sell']
        
        profit_trades = 0
        loss_trades = 0
        
        for buy, sell in zip(buy_trades, sell_trades):
            if sell.price > buy.price:
                profit_trades += 1
            else:
                loss_trades += 1
        
        total_trades = len(buy_trades)
        win_rate = profit_trades / total_trades * 100 if total_trades > 0 else 0
        
        result = {
            'initial_capital': init_cap,
            'final_capital': final_equity,
            'total_return': total_return,
            'annual_return': annual_return,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'total_trades': total_trades,
            'profit_trades': profit_trades,
            'loss_trades': loss_trades
        }
        
        return result, trades, equity_curve
    
    def save_backtest_result(
        self,
        db: Session,
        stock_code: str,
        strategy_name: str,
        start_date: date,
        end_date: date,
        result: dict,
        trades: List[Trade]
    ) -> BacktestResult:
        backtest_result = BacktestResult(
            stock_code=stock_code,
            strategy_name=strategy_name,
            start_date=start_date,
            end_date=end_date,
            initial_capital=result['initial_capital'],
            final_capital=result['final_capital'],
            total_return=result['total_return'],
            annual_return=result['annual_return'],
            max_drawdown=result['max_drawdown'],
            win_rate=result['win_rate'],
            total_trades=result['total_trades'],
            profit_trades=result['profit_trades'],
            loss_trades=result['loss_trades']
        )
        
        db.add(backtest_result)
        db.flush()
        
        for trade in trades:
            trade_record = TradeRecord(
                backtest_id=backtest_result.id,
                stock_code=stock_code,
                trade_type=trade.trade_type,
                trade_date=trade.date,
                price=trade.price,
                shares=trade.shares,
                amount=trade.amount
            )
            db.add(trade_record)
        
        db.commit()
        db.refresh(backtest_result)
        
        return backtest_result


backtest_engine = BacktestEngine()
