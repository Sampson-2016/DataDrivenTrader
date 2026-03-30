import pytest
import pandas as pd
from datetime import date, timedelta
from unittest.mock import MagicMock

from app.backtest_engine import BacktestEngine, Trade, Position
from app.models import StockDaily


class TestBacktestEngine:
    """测试回测引擎"""
    
    def test_initialization(self):
        """测试初始化"""
        engine = BacktestEngine(initial_capital=100000)
        assert engine.initial_capital == 100000
        assert engine.commission_rate == 0.0003
        assert engine.stamp_duty_rate == 0.001
    
    def test_calculate_commission(self):
        """测试手续费计算"""
        engine = BacktestEngine()
        
        # 买入手续费
        commission = engine.calculate_commission(100000, is_sell=False)
        assert commission >= 5.0
        
        # 卖出手续费（包含印花税）
        sell_commission = engine.calculate_commission(100000, is_sell=True)
        assert sell_commission > commission
    
    def test_calculate_ma(self):
        """测试计算移动平均线"""
        engine = BacktestEngine()
        
        prices = pd.Series([100, 102, 105, 103, 107])
        ma = engine.calculate_ma(prices, 3)
        
        assert len(ma) == 5
        assert pd.isna(ma.iloc[0])
        assert pd.isna(ma.iloc[1])
        assert pd.notna(ma.iloc[2])
    
    def test_generate_signals(self):
        """测试生成信号"""
        engine = BacktestEngine()
        
        df = pd.DataFrame({
            'close_price': [100, 102, 105, 103, 107, 108, 110, 109, 107, 105]
        })
        
        df = engine.generate_signals(df, ma_period=3)
        
        assert 'ma' in df.columns
        assert 'signal' in df.columns
        assert 'prev_close' in df.columns
        assert 'prev_ma' in df.columns
    
    def test_run_backtest(self):
        """测试完整回测"""
        engine = BacktestEngine(initial_capital=100000)
        
        base_date = date(2023, 1, 1)
        stock_data = []
        
        for i in range(30):
            stock_data.append(StockDaily(
                trade_date=base_date + timedelta(days=i),
                open_price=100 + i,
                high_price=105 + i,
                low_price=99 + i,
                close_price=102 + i,
                volume=1000000 + i * 1000,
                amount=100000000 + i * 10000
            ))
        
        result, trades, equity_curve = engine.run_backtest(stock_data, ma_period=5)
        
        assert 'initial_capital' in result
        assert 'final_capital' in result
        assert 'total_return' in result
        assert 'win_rate' in result
        assert len(equity_curve) == 30
    
    def test_run_backtest_insufficient_data(self):
        """测试数据不足的情况"""
        engine = BacktestEngine()
        
        base_date = date(2023, 1, 1)
        stock_data = []
        
        for i in range(5):
            stock_data.append(StockDaily(
                trade_date=base_date + timedelta(days=i),
                open_price=100 + i,
                high_price=105 + i,
                low_price=99 + i,
                close_price=102 + i,
                volume=1000000,
                amount=100000000
            ))
        
        with pytest.raises(ValueError):
            engine.run_backtest(stock_data, ma_period=5)
    
    def test_position_empty(self):
        """测试空仓位"""
        position = Position()
        assert position.is_empty()
        
        position.shares = 100
        assert not position.is_empty()
    
    def test_save_backtest_result(self):
        """测试保存回测结果"""
        engine = BacktestEngine()
        
        mock_db = MagicMock()
        mock_backtest = MagicMock()
        mock_backtest.id = 1
        mock_db.add = MagicMock()
        mock_db.flush = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock(return_value=mock_backtest)
        
        result = {
            'initial_capital': 100000,
            'final_capital': 120000,
            'total_return': 20.0,
            'annual_return': 25.0,
            'max_drawdown': -10.0,
            'win_rate': 60.0,
            'total_trades': 10,
            'profit_trades': 6,
            'loss_trades': 4
        }
        
        trades = [
            Trade(trade_type='buy', date=date(2023, 1, 1), price=100, shares=100, amount=10000),
            Trade(trade_type='sell', date=date(2023, 1, 2), price=120, shares=100, amount=12000)
        ]
        
        backtest_result = engine.save_backtest_result(
            mock_db, '600000', 'MA5_Cross', date(2023, 1, 1), date(2023, 12, 31), result, trades
        )
        
        assert backtest_result is not None
        mock_db.add.call_count >= 3
        mock_db.commit.assert_called_once()


class TestTrade:
    """测试交易记录"""
    
    def test_trade_creation(self):
        """测试创建交易"""
        trade = Trade(
            trade_type='buy',
            date=date(2023, 1, 1),
            price=100.0,
            shares=100,
            amount=10000.0
        )
        
        assert trade.trade_type == 'buy'
        assert trade.price == 100.0
        assert trade.shares == 100
        assert trade.amount == 10000.0
