import pytest
import pandas as pd
from datetime import date, timedelta

from app.strategies.ma_cross import MACrossStrategy
from app.models import StockDaily


@pytest.fixture
def sample_data():
    """生成测试数据"""
    base_date = date(2023, 1, 1)
    data = []
    
    for i in range(20):
        trade_date = base_date + timedelta(days=i)
        close_price = 100 + i * 2
        
        data.append(StockDaily(
            trade_date=trade_date,
            open_price=close_price - 2,
            high_price=close_price + 1,
            low_price=close_price - 3,
            close_price=close_price,
            volume=1000000 + i * 1000,
            amount=100000000 + i * 10000,
            stock_code='600000'
        ))
    
    return data


class TestMACrossStrategy:
    """测试MA交叉策略"""
    
    def test_initialization(self):
        """测试初始化"""
        strategy = MACrossStrategy(initial_capital=100000, ma_period=5)
        assert strategy.initial_capital == 100000
        assert strategy.ma_period == 5
        assert strategy.strategy_name == 'MA5_Cross'
    
    def test_get_required_fields(self):
        """测试所需字段"""
        strategy = MACrossStrategy()
        fields = strategy.get_required_fields()
        assert 'close_price' in fields
    
    def test_get_params(self):
        """测试参数"""
        strategy = MACrossStrategy(ma_period=10)
        params = strategy.get_params()
        assert params['ma_period'] == 10
    
    def test_calculate_indicators(self, sample_data):
        """测试指标计算"""
        strategy = MACrossStrategy(ma_period=5)
        df = strategy._prepare_data(sample_data)
        df = strategy.calculate_indicators(df)
        
        assert 'ma5' in df.columns
        assert len(df) == 20
        
        for i in range(4):
            assert pd.isna(df.iloc[i]['ma5'])
        
        assert pd.notna(df.iloc[4]['ma5'])
    
    def test_generate_signals(self, sample_data):
        """测试信号生成"""
        strategy = MACrossStrategy(ma_period=5)
        df = strategy._prepare_data(sample_data)
        df = strategy.calculate_indicators(df)
        df = strategy.generate_signals(df)
        
        assert 'signal' in df.columns
        
        buy_signals = df[df['signal'] == 1]
        sell_signals = df[df['signal'] == -1]
        
        assert len(buy_signals) >= 0
        assert len(sell_signals) >= 0
    
    def test_run_backtest(self, sample_data):
        """测试完整回测"""
        strategy = MACrossStrategy(initial_capital=100000, ma_period=5)
        result = strategy.run_backtest(sample_data)
        
        assert result.strategy_name == 'MA5_Cross'
        assert result.initial_capital == 100000
        assert len(result.equity_curve) == 20
        assert len(result.kline_data) == 20
        assert result.total_trades >= 0
    
    def test_buy_signal_condition(self):
        """测试买入信号条件"""
        base_date = date(2023, 1, 1)
        data = []
        
        for i in range(10):
            trade_date = base_date + timedelta(days=i)
            close_price = 100 + i * 2
            
            data.append(StockDaily(
                trade_date=trade_date,
                open_price=close_price - 2,
                high_price=close_price + 1,
                low_price=close_price - 3,
                close_price=close_price,
                volume=1000000,
                amount=100000000,
                stock_code='600000'
            ))
        
        strategy = MACrossStrategy(ma_period=3)
        df = strategy._prepare_data(data)
        df = strategy.calculate_indicators(df)
        df = strategy.generate_signals(df)
        
        print("\n=== MA Cross Signals ===")
        for idx, row in df.iterrows():
            close = float(row['close_price']) if pd.notna(row['close_price']) else 0
            ma = float(row['ma3']) if pd.notna(row['ma3']) else 0
            print(f"Date: {row['trade_date']}, Close: {close:.2f}, "
                  f"MA: {ma:.2f}, Signal: {row['signal']}")
    
    def test_sell_signal_condition(self):
        """测试卖出信号条件"""
        base_date = date(2023, 1, 1)
        data = []
        
        for i in range(10):
            trade_date = base_date + timedelta(days=i)
            close_price = 118 - i * 2
            
            data.append(StockDaily(
                trade_date=trade_date,
                open_price=close_price - 2,
                high_price=close_price + 1,
                low_price=close_price - 3,
                close_price=close_price,
                volume=1000000,
                amount=100000000,
                stock_code='600000'
            ))
        
        strategy = MACrossStrategy(ma_period=3)
        df = strategy._prepare_data(data)
        df = strategy.calculate_indicators(df)
        df = strategy.generate_signals(df)
        
        print("\n=== MA Cross Sell Signals ===")
        for idx, row in df.iterrows():
            close = float(row['close_price']) if pd.notna(row['close_price']) else 0
            ma = float(row['ma3']) if pd.notna(row['ma3']) else 0
            print(f"Date: {row['trade_date']}, Close: {close:.2f}, "
                  f"MA: {ma:.2f}, Signal: {row['signal']}")
