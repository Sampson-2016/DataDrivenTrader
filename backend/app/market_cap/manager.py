from typing import Optional, Dict, List
from datetime import datetime

from .fetcher import MarketCapFetcher


class MarketCapManager:
    """市值数据管理器
    
    负责市值数据的缓存、更新和查询
    """
    
    def __init__(self, fetcher: MarketCapFetcher = None):
        self.fetcher = fetcher or MarketCapFetcher()
        self.market_caps: Dict[str, Dict[str, float]] = {}
        self.default_thresholds = {
            'small': 0.35,
            'mid': 0.30,
            'large': 0.25
        }
    
    def get_market_cap(self, stock_code: str, trade_date: Optional[datetime] = None) -> Optional[float]:
        """获取股票市值
        
        Args:
            stock_code: 股票代码
            trade_date: 交易日期
            
        Returns:
            市值（亿元）
        """
        return self.fetcher.get_market_cap(stock_code, trade_date)
    
    def get_decay_threshold(self, stock_code: str, trade_date: Optional[datetime] = None) -> float:
        """根据市值获取衰减阈值
        
        Args:
            stock_code: 股票代码
            trade_date: 交易日期
            
        Returns:
            衰减阈值
        """
        market_cap = self.get_market_cap(stock_code, trade_date)
        category = self.fetcher.get_market_cap_category(market_cap)
        
        return self.default_thresholds[category]
    
    def classify_market_cap(self, market_cap: Optional[float]) -> str:
        """市值分类
        
        Args:
            market_cap: 市值（亿元）
            
        Returns:
            'small' | 'mid' | 'large'
        """
        return self.fetcher.get_market_cap_category(market_cap)
    
    def update_market_caps(self, stock_codes: List[str], trade_date: Optional[datetime] = None) -> Dict[str, float]:
        """更新市值数据
        
        Args:
            stock_codes: 股票代码列表
            trade_date: 交易日期
            
        Returns:
            更新后的市值字典
        """
        market_caps = self.fetcher.batch_fetch_market_caps(stock_codes, trade_date)
        
        if trade_date not in self.market_caps:
            self.market_caps[trade_date or 'latest'] = {}
        
        self.market_caps[trade_date or 'latest'].update(market_caps)
        
        return market_caps
    
    def get_all_categories(self) -> Dict[str, List[str]]:
        """获取所有市值分类
        
        Returns:
            {category: [stock_codes]}
        """
        categories = {'small': [], 'mid': [], 'large': []}
        
        for stock_code, market_caps in self.market_caps.items():
            for code, cap in market_caps.items():
                category = self.classify_market_cap(cap)
                if code not in categories[category]:
                    categories[category].append(code)
        
        return categories
    
    def get_statistics(self) -> Dict[str, any]:
        """获取市值统计信息
        
        Returns:
            统计信息字典
        """
        all_caps = []
        for market_caps in self.market_caps.values():
            all_caps.extend(market_caps.values())
        
        if not all_caps:
            return {
                'total_stocks': 0,
                'small_cap_stocks': 0,
                'mid_cap_stocks': 0,
                'large_cap_stocks': 0,
                'avg_market_cap': 0,
                'min_market_cap': 0,
                'max_market_cap': 0
            }
        
        small_count = sum(1 for c in all_caps if c < 100)
        mid_count = sum(1 for c in all_caps if 100 <= c < 300)
        large_count = sum(1 for c in all_caps if c >= 300)
        
        return {
            'total_stocks': len(all_caps),
            'small_cap_stocks': small_count,
            'mid_cap_stocks': mid_count,
            'large_cap_stocks': large_count,
            'avg_market_cap': sum(all_caps) / len(all_caps),
            'min_market_cap': min(all_caps),
            'max_market_cap': max(all_caps)
        }
