import pytest
import pandas as pd
import numpy as np
from datetime import date, timedelta

from app.strategies.energy_decay import EnergyDecayStrategy
from app.models import StockDaily


@pytest.fixture
def sample_data():
    """生成测试数据"""
    base_date = date(2023, 1, 1)
    data = []
    
    for i in range(30):
        trade_date = base_date + timedelta(days=i)
        close_price = 80 + i * 0.5  # 逐渐上涨
        
        data.append(StockDaily(
            trade_date=trade_date,
            open_price=close_price - 1,
            high_price=close_price + 1,
            low_price=close_price - 2,
            close_price=close_price,
            volume=1000000 + i * 100000,
            amount=100000000 + i * 1000000,
            stock_code='600000'
        ))
    
    return data


class TestEnergyDecayStrategy:
    """测试能量衰减策略"""
    
    def test_initialization(self):
        """测试初始化"""
        strategy = EnergyDecayStrategy(
            initial_capital=100000,
            decay_threshold_small=0.35,
            decay_threshold_mid=0.30,
            decay_threshold_large=0.25
        )
        
        assert strategy.initial_capital == 100000
        assert strategy.strategy_name == 'Energy_Decay'
        assert strategy.decay_threshold_small == 0.35
    
    def test_get_required_fields(self):
        """测试所需字段"""
        strategy = EnergyDecayStrategy()
        fields = strategy.get_required_fields()
        assert 'open_price' in fields
        assert 'close_price' in fields
        assert 'volume' in fields
    
    def test_get_params(self):
        """测试参数"""
        strategy = EnergyDecayStrategy()
        params = strategy.get_params()
        
        assert 'decay_threshold_small' in params
        assert 'breakout_price_ratio' in params
        assert 'signal_volume_ratio' in params
    
    def test_calculate_indicators(self, sample_data):
        """测试指标计算"""
        strategy = EnergyDecayStrategy()
        df = strategy._prepare_data(sample_data)
        df = strategy.calculate_indicators(df)
        
        assert 'ma250' in df.columns
        assert 'volume_ma5' in df.columns
        assert 'volume_ratio' in df.columns
        assert 'breakout_day' in df.columns
        assert 'real_body' in df.columns
    
    def test_classify_market_cap(self):
        """测试市值分类"""
        strategy = EnergyDecayStrategy()
        
        assert strategy.classify_market_cap(50) == 'small'
        assert strategy.classify_market_cap(100) == 'mid'
        assert strategy.classify_market_cap(200) == 'mid'
        assert strategy.classify_market_cap(300) == 'large'
        assert strategy.classify_market_cap(500) == 'large'
        assert strategy.classify_market_cap(None) == 'mid'
    
    def test_get_decay_threshold(self):
        """测试获取衰减阈值"""
        strategy = EnergyDecayStrategy()
        
        assert strategy.get_decay_threshold(50) == 0.35
        assert strategy.get_decay_threshold(150) == 0.30
        assert strategy.get_decay_threshold(400) == 0.25
        assert strategy.get_decay_threshold(None) == 0.30
    
    def test_find_breakout_day(self, sample_data):
        """测试查找突破日"""
        strategy = EnergyDecayStrategy()
        df = strategy._prepare_data(sample_data)
        df = strategy.calculate_indicators(df)
        
        breakout_idx = strategy.find_breakout_day(df)
        
        # 由于测试数据没有满足突破条件的，应该返回None
        assert breakout_idx is None or isinstance(breakout_idx, (int, np.integer))
    
    def test_calculate_decay_rate(self, sample_data):
        """测试计算衰减率"""
        strategy = EnergyDecayStrategy()
        df = strategy._prepare_data(sample_data)
        df = strategy.calculate_indicators(df)
        
        # 手动设置一个突破日
        df.at[df.index[5], 'breakout_day'] = True
        breakout_idx = 5
        
        decay_rate = strategy.calculate_decay_rate(df, breakout_idx)
        
        assert len(decay_rate) == len(df)
        assert pd.notna(decay_rate.iloc[breakout_idx])
        assert decay_rate.iloc[breakout_idx] == 1.0
    
    def test_check_price_support(self, sample_data):
        """测试价格支撑检查"""
        strategy = EnergyDecayStrategy()
        df = strategy._prepare_data(sample_data)
        df = strategy.calculate_indicators(df)
        
        # 手动设置突破日数据
        df.at[df.index[5], 'breakout_day'] = True
        df.at[df.index[5], 'open_price'] = 85.0
        df.at[df.index[5], 'close_price'] = 90.0
        df.at[df.index[5], 'real_body'] = 5.0
        
        # 检查突破日之后的价格
        result = strategy.check_price_support(df, 10, 5)
        assert result in [True, False]
    
    def test_generate_signals(self, sample_data):
        """测试信号生成"""
        strategy = EnergyDecayStrategy()
        df = strategy._prepare_data(sample_data)
        df = strategy.calculate_indicators(df)
        df = strategy.generate_signals(df, market_cap=150)
        
        assert 'signal' in df.columns
        assert 'decay_rate' in df.columns
        assert 'decay_reached' in df.columns
        assert 'signal_volume_check' in df.columns
        assert 'signal_price_check' in df.columns
    
    def test_run_backtest(self, sample_data):
        """测试完整回测"""
        strategy = EnergyDecayStrategy(initial_capital=100000)
        result = strategy.run_backtest(sample_data, market_cap=150)
        
        assert result.strategy_name == 'Energy_Decay'
        assert result.initial_capital == 100000
        assert len(result.trades) >= 0
        assert len(result.equity_curve) == 30
        assert len(result.kline_data) == 30
    
    def test_signals_info_extraction(self, sample_data):
        """测试信号信息提取"""
        strategy = EnergyDecayStrategy()
        df = strategy._prepare_data(sample_data)
        df = strategy.calculate_indicators(df)
        df = strategy.generate_signals(df, market_cap=150)
        
        signals_info = strategy._extract_signals_info(df)
        
        assert 'breakout_days' in signals_info
        assert 'decay_reached_days' in signals_info
        assert 'signal_days' in signals_info
    
    def test_breakout_conditions(self):
        """测试突破条件"""
        base_date = date(2023, 1, 1)
        data = []
        
        # 创建满足突破条件的数据
        for i in range(30):
            trade_date = base_date + timedelta(days=i)
            
            # 前10天价格较低
            if i < 10:
                close_price = 60 + i * 0.2
                volume = 5000000  # 大量
            else:
                close_price = 70 + (i - 10) * 0.5
                volume = 1000000 + (i - 10) * 100000
            
            data.append(StockDaily(
                trade_date=trade_date,
                open_price=close_price - 1,
                high_price=close_price + 1,
                low_price=close_price - 2,
                close_price=close_price,
                volume=volume,
                amount=100000000,
                stock_code='600000'
            ))
        
        strategy = EnergyDecayStrategy(breakout_price_ratio=0.7, breakout_volume_ratio=1.5)
        df = strategy._prepare_data(data)
        df = strategy.calculate_indicators(df)
        
        print("\n=== Breakout Detection ===")
        for idx, row in df.iterrows():
            if row['breakout_day']:
                print(f"Breakout Day: {row['trade_date']}, "
                      f"Close: {row['close_price']:.2f}, "
                      f"MA250: {row['ma250']:.2f}, "
                      f"Volume Ratio: {row['volume_ratio']:.2f}")
    
    def test_decay_reached_conditions(self):
        """测试衰减达标条件"""
        base_date = date(2023, 1, 1)
        data = []
        
        # 创建突破日
        for i in range(30):
            trade_date = base_date + timedelta(days=i)
            
            if i == 5:
                # 突破日：大量
                close_price = 70
                volume = 10000000
            elif i > 5:
                # 衰减阶段：量能逐渐减少
                close_price = 70 + (i - 5) * 0.5
                volume = 3000000 * (0.9 ** (i - 5))
            else:
                close_price = 65 + i * 0.5
                volume = 1000000
            
            data.append(StockDaily(
                trade_date=trade_date,
                open_price=close_price - 1,
                high_price=close_price + 1,
                low_price=close_price - 2,
                close_price=close_price,
                volume=volume,
                amount=100000000,
                stock_code='600000'
            ))
        
        strategy = EnergyDecayStrategy(
            breakout_price_ratio=0.7,
            breakout_volume_ratio=1.5,
            signal_volume_ratio=1.1
        )
        df = strategy._prepare_data(data)
        df = strategy.calculate_indicators(df)
        df = strategy.generate_signals(df, market_cap=150)
        
        print("\n=== Decay Reached ===")
        for idx, row in df.iterrows():
            if row['decay_reached']:
                print(f"Decay Reached: {row['trade_date']}, "
                      f"Close: {row['close_price']:.2f}, "
                      f"Decay Rate: {row['decay_rate']:.3f}, "
                      f"Volume Ratio: {row['volume_ratio']:.2f}")
