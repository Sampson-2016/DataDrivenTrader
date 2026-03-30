#!/usr/bin/env python
"""
DataDrivenTrader 整体测试脚本
测试所有模块的功能集成
"""

import sys
import os

# 添加backend路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from datetime import date, timedelta
from app.models import StockDaily
from app.strategies.energy_decay import EnergyDecayStrategy
from app.strategies.ma_cross import MACrossStrategy
from app.market_cap.fetcher import MarketCapFetcher
from app.market_cap.manager import MarketCapManager
from app.data_fetcher import DataFetcher
from app.backtest_engine import BacktestEngine
from app.stock_list.fetcher import stock_list_fetcher
from app.bulk_download.manager import bulk_download_manager


def test_energy_decay_strategy():
    """测试能量衰减策略"""
    print("\n=== 测试能量衰减策略 ===")
    
    base_date = date(2023, 1, 1)
    stock_data = []
    
    # 创建突破日数据
    for i in range(30):
        stock_data.append(StockDaily(
            trade_date=base_date + timedelta(days=i),
            open_price=80 + i * 0.5,
            high_price=85 + i * 0.5,
            low_price=78 + i * 0.5,
            close_price=82 + i * 0.5,
            volume=1000000 + i * 100000,
            amount=100000000 + i * 1000000,
            stock_code='600000'
        ))
    
    strategy = EnergyDecayStrategy(initial_capital=100000)
    result = strategy.run_backtest(stock_data, market_cap=150)
    
    print(f"策略名称: {result.strategy_name}")
    print(f"初始资金: {result.initial_capital}")
    print(f"最终资金: {result.final_capital:.2f}")
    print(f"总收益率: {result.total_return:.2f}%")
    print(f"总交易次数: {result.total_trades}")
    print(f"信号信息: {result.signals_info}")
    
    assert result.strategy_name == 'Energy_Decay'
    print("✓ 能量衰减策略测试通过")


def test_ma_cross_strategy():
    """测试MA交叉策略"""
    print("\n=== 测试MA交叉策略 ===")
    
    base_date = date(2023, 1, 1)
    stock_data = []
    
    for i in range(30):
        stock_data.append(StockDaily(
            trade_date=base_date + timedelta(days=i),
            open_price=100 + i,
            high_price=105 + i,
            low_price=99 + i,
            close_price=102 + i,
            volume=1000000,
            amount=100000000,
            stock_code='600000'
        ))
    
    strategy = MACrossStrategy(initial_capital=100000, ma_period=5)
    result = strategy.run_backtest(stock_data)
    
    print(f"策略名称: {result.strategy_name}")
    print(f"初始资金: {result.initial_capital}")
    print(f"最终资金: {result.final_capital:.2f}")
    print(f"总收益率: {result.total_return:.2f}%")
    print(f"总交易次数: {result.total_trades}")
    
    assert result.strategy_name == 'MA5_Cross'
    print("✓ MA交叉策略测试通过")


def test_market_cap():
    """测试市值模块"""
    print("\n=== 测试市值模块 ===")
    
    fetcher = MarketCapFetcher()
    
    # 测试获取市值
    cap = fetcher.get_market_cap('300001')
    print(f"300001 市值: {cap} 亿元")
    
    # 测试分类
    category = fetcher.get_market_cap_category(50)
    print(f"50亿市值分类: {category}")
    
    assert category == 'small'
    print("✓ 市值模块测试通过")


def test_backtest_engine():
    """测试回测引擎"""
    print("\n=== 测试回测引擎 ===")
    
    base_date = date(2023, 1, 1)
    stock_data = []
    
    for i in range(30):
        stock_data.append(StockDaily(
            trade_date=base_date + timedelta(days=i),
            open_price=100 + i,
            high_price=105 + i,
            low_price=99 + i,
            close_price=102 + i,
            volume=1000000,
            amount=100000000,
            stock_code='600000'
        ))
    
    engine = BacktestEngine(initial_capital=100000)
    result, trades, equity_curve = engine.run_backtest(stock_data, ma_period=5)
    
    print(f"初始资金: {result['initial_capital']}")
    print(f"最终资金: {result['final_capital']:.2f}")
    print(f"总收益率: {result['total_return']:.2f}%")
    print(f"交易次数: {result['total_trades']}")
    
    assert 'initial_capital' in result
    print("✓ 回测引擎测试通过")


def test_stock_list_fetcher():
    """测试股票列表获取器"""
    print("\n=== 测试股票列表获取器 ===")
    
    stock_codes = stock_list_fetcher.get_all_stock_codes()
    print(f"找到 {len(stock_codes)} 只非ST股票")
    
    assert len(stock_codes) > 0
    print("✓ 股票列表获取器测试通过")


def test_bulk_download_manager():
    """测试批量下载管理器"""
    print("\n=== 测试批量下载管理器 ===")
    
    manager = bulk_download_manager
    
    # 测试获取最新更新时间
    latest_time = manager.last_update_time
    print(f"最新更新时间: {latest_time}")
    
    # 测试获取状态
    status = manager.get_all_status()
    print(f"状态: {status}")
    
    assert 'is_downloading' in status
    assert 'last_update_time' in status
    print("✓ 批量下载管理器测试通过")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("DataDrivenTrader 整体测试")
    print("=" * 60)
    
    try:
        test_energy_decay_strategy()
        test_ma_cross_strategy()
        test_market_cap()
        test_backtest_engine()
        test_stock_list_fetcher()
        test_bulk_download_manager()
        
        print("\n" + "=" * 60)
        print("✓ 所有测试通过!")
        print("=" * 60)
        return 0
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
