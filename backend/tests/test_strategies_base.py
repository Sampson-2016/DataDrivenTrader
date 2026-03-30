import pytest
import pandas as pd
from datetime import date, timedelta
from unittest.mock import MagicMock

from app.strategies.base import StrategyBase, StrategyRegistry, StrategyResult
from app.models import StockDaily


class MockStrategy(StrategyBase):
    """用于测试的模拟策略"""
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df['ma5'] = df['close_price'].rolling(window=5).mean()
        return df
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df['signal'] = 0
        df.loc[df['close_price'] > df['ma5'], 'signal'] = 1
        df.loc[df['close_price'] < df['ma5'], 'signal'] = -1
        return df
    
    def get_required_fields(self) -> list:
        return ['close_price', 'volume']
    
    def get_strategy_name(self) -> str:
        return 'MockStrategy'
    
    def get_params(self) -> dict:
        return {'threshold': 0.05}


@pytest.fixture
def sample_stock_data():
    """生成测试用的股票数据"""
    base_date = date(2023, 1, 1)
    data = []
    
    for i in range(30):
        trade_date = base_date + timedelta(days=i)
        data.append(StockDaily(
            trade_date=trade_date,
            open_price=100 + i,
            high_price=105 + i,
            low_price=98 + i,
            close_price=102 + i,
            volume=1000000 + i * 1000,
            amount=100000000 + i * 10000,
            stock_code='600000'
        ))
    
    return data


@pytest.fixture
def mock_strategy():
    """创建模拟策略实例"""
    return MockStrategy(initial_capital=100000)


class TestStrategyBase:
    """测试策略基类"""
    
    def test_strategy_initialization(self, mock_strategy):
        """测试策略初始化"""
        assert mock_strategy.strategy_name == 'MockStrategy'
        assert mock_strategy.initial_capital == 100000
    
    def test_get_required_fields(self, mock_strategy):
        """测试获取所需字段"""
        fields = mock_strategy.get_required_fields()
        assert 'close_price' in fields
        assert 'volume' in fields
    
    def test_get_strategy_name(self, mock_strategy):
        """测试获取策略名称"""
        name = mock_strategy.get_strategy_name()
        assert name == 'MockStrategy'
    
    def test_get_params(self, mock_strategy):
        """测试获取参数"""
        params = mock_strategy.get_params()
        assert params['threshold'] == 0.05
    
    def test_prepare_data(self, mock_strategy, sample_stock_data):
        """测试数据准备"""
        df = mock_strategy._prepare_data(sample_stock_data)
        
        assert len(df) == 30
        assert 'trade_date' in df.columns
        assert 'close_price' in df.columns
        assert 'volume' in df.columns
        assert df.iloc[0]['trade_date'] == date(2023, 1, 1)
    
    def test_calculate_indicators(self, mock_strategy, sample_stock_data):
        """测试指标计算"""
        df = mock_strategy._prepare_data(sample_stock_data)
        df = mock_strategy.calculate_indicators(df)
        
        assert 'ma5' in df.columns
        assert pd.isna(df.iloc[0]['ma5'])
        assert pd.notna(df.iloc[4]['ma5'])
    
    def test_generate_signals(self, mock_strategy, sample_stock_data):
        """测试信号生成"""
        df = mock_strategy._prepare_data(sample_stock_data)
        df = mock_strategy.calculate_indicators(df)
        df = mock_strategy.generate_signals(df)
        
        assert 'signal' in df.columns
        assert df['signal'].dtype == 'int64'
    
    def test_execute_backtest(self, mock_strategy, sample_stock_data):
        """测试回测执行"""
        df = mock_strategy._prepare_data(sample_stock_data)
        df = mock_strategy.calculate_indicators(df)
        df = mock_strategy.generate_signals(df)
        
        result = mock_strategy._execute_backtest(df, 100000)
        
        assert isinstance(result, StrategyResult)
        assert result.initial_capital == 100000
        assert len(result.trades) > 0
        assert len(result.equity_curve) == 30
        assert len(result.kline_data) == 30
    
    def test_calculate_commission(self, mock_strategy):
        """测试手续费计算"""
        amount = 100000
        commission = mock_strategy._calculate_commission(amount, is_sell=False)
        assert commission >= 5.0
        
        sell_commission = mock_strategy._calculate_commission(amount, is_sell=True)
        assert sell_commission > commission


class TestStrategyRegistry:
    """测试策略注册器"""
    
    def test_register_strategy(self):
        """测试注册策略"""
        @StrategyRegistry.register
        class TestStrategy(StrategyBase):
            def calculate_indicators(self, df):
                return df
            
            def generate_signals(self, df):
                return df
            
            def get_required_fields(self):
                return []
            
            def get_strategy_name(self):
                return 'TestStrategy'
            
            def get_params(self):
                return {}
        
        assert 'TestStrategy' in StrategyRegistry._strategies
    
    def test_get_strategy(self):
        """测试获取策略"""
        @StrategyRegistry.register
        class TestStrategy2(StrategyBase):
            def calculate_indicators(self, df):
                return df
            
            def generate_signals(self, df):
                return df
            
            def get_required_fields(self):
                return []
            
            def get_strategy_name(self):
                return 'TestStrategy2'
            
            def get_params(self):
                return {}
        
        strategy = StrategyRegistry.get_strategy('TestStrategy2', initial_capital=50000)
        assert strategy.initial_capital == 50000
        assert strategy.get_strategy_name() == 'TestStrategy2'
    
    def test_get_all_strategies(self):
        """测试获取所有策略"""
        strategies = StrategyRegistry.get_all_strategies()
        assert len(strategies) >= 1
        
        strategy_names = [s['name'] for s in strategies]
        assert 'MA5_Cross' in strategy_names
    
    def test_get_nonexistent_strategy(self):
        """测试获取不存在的策略"""
        with pytest.raises(ValueError):
            StrategyRegistry.get_strategy('NonexistentStrategy')


class TestStrategyResult:
    """测试策略结果"""
    
    def test_strategy_result_creation(self):
        """测试策略结果创建"""
        result = StrategyResult(
            strategy_name='TestStrategy',
            stock_code='600000',
            start_date='2023-01-01',
            end_date='2023-12-31',
            initial_capital=100000,
            final_capital=120000,
            total_return=20.0,
            annual_return=25.0,
            max_drawdown=-10.0,
            win_rate=60.0,
            total_trades=10,
            profit_trades=6,
            loss_trades=4,
            trades=[],
            equity_curve=[],
            kline_data=[]
        )
        
        assert result.strategy_name == 'TestStrategy'
        assert result.total_return == 20.0
        assert result.win_rate == 60.0
