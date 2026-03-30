import pytest
from datetime import datetime, timedelta

from app.market_cap.fetcher import MarketCapFetcher
from app.market_cap.manager import MarketCapManager


class TestMarketCapFetcher:
    """测试市值数据获取器"""
    
    def test_initialization(self):
        """测试初始化"""
        fetcher = MarketCapFetcher()
        assert fetcher.cache_ttl == 3600 * 24
        assert isinstance(fetcher.cache, dict)
    
    def test_get_market_cap(self):
        """测试获取市值"""
        fetcher = MarketCapFetcher()
        
        # 测试不同股票代码
        cap1 = fetcher.get_market_cap('300001')
        cap2 = fetcher.get_market_cap('600000')
        cap3 = fetcher.get_market_cap('000001')
        
        # 应该返回市值（亿元）
        assert isinstance(cap1, (int, float)) and cap1 > 0
        assert isinstance(cap2, (int, float)) and cap2 > 0
        assert isinstance(cap3, (int, float)) and cap3 > 0
    
    def test_get_market_cap_with_date(self):
        """测试指定日期的市值"""
        fetcher = MarketCapFetcher()
        trade_date = datetime(2023, 1, 1)
        
        cap = fetcher.get_market_cap('600000', trade_date)
        
        assert isinstance(cap, (int, float)) and cap > 0
    
    def test_batch_fetch_market_caps(self):
        """测试批量获取市值"""
        fetcher = MarketCapFetcher()
        stock_codes = ['300001', '600000', '000001']
        
        caps = fetcher.batch_fetch_market_caps(stock_codes)
        
        assert isinstance(caps, dict)
        assert len(caps) == 3
        for code, cap in caps.items():
            assert code in stock_codes
            assert isinstance(cap, (int, float)) and cap > 0
    
    def test_get_market_cap_category(self):
        """测试市值分类"""
        fetcher = MarketCapFetcher()
        
        assert fetcher.get_market_cap_category(50) == 'small'
        assert fetcher.get_market_cap_category(100) == 'mid'
        assert fetcher.get_market_cap_category(200) == 'mid'
        assert fetcher.get_market_cap_category(300) == 'large'
        assert fetcher.get_market_cap_category(500) == 'large'
        assert fetcher.get_market_cap_category(None) == 'mid'


class TestMarketCapManager:
    """测试市值数据管理器"""
    
    def test_initialization(self):
        """测试初始化"""
        manager = MarketCapManager()
        assert isinstance(manager.market_caps, dict)
        assert isinstance(manager.default_thresholds, dict)
    
    def test_get_decay_threshold(self):
        """测试获取衰减阈值"""
        manager = MarketCapManager()
        
        # 直接测试不同市值的阈值
        assert manager.get_decay_threshold('300001') == 0.35  # 小盘股
        assert manager.get_decay_threshold('600000') == 0.30  # 中盘股
        assert manager.get_decay_threshold('601398') == 0.25  # 大盘股
    
    def test_classify_market_cap(self):
        """测试市值分类"""
        manager = MarketCapManager()
        
        assert manager.classify_market_cap(50) == 'small'
        assert manager.classify_market_cap(100) == 'mid'
        assert manager.classify_market_cap(300) == 'large'
        assert manager.classify_market_cap(None) == 'mid'
    
    def test_update_market_caps(self):
        """测试更新市值数据"""
        manager = MarketCapManager()
        stock_codes = ['300001', '600000']
        
        updated = manager.update_market_caps(stock_codes)
        
        assert isinstance(updated, dict)
        assert len(updated) == 2
    
    def test_get_statistics(self):
        """测试获取统计信息"""
        manager = MarketCapManager()
        
        stats = manager.get_statistics()
        
        assert 'total_stocks' in stats
        assert 'small_cap_stocks' in stats
        assert 'mid_cap_stocks' in stats
        assert 'large_cap_stocks' in stats
    
    def test_get_all_categories(self):
        """测试获取所有分类"""
        manager = MarketCapManager()
        
        categories = manager.get_all_categories()
        
        assert 'small' in categories
        assert 'mid' in categories
        assert 'large' in categories
