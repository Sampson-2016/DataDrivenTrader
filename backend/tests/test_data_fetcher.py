import pytest
import pandas as pd
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from app.data_fetcher import DataFetcher
from app.models import StockDaily


class TestDataFetcher:
    """测试数据获取器"""
    
    def test_initialization(self):
        """测试初始化"""
        fetcher = DataFetcher()
        assert fetcher is not None
    
    @patch('app.data_fetcher.ak.stock_zh_a_hist')
    def test_fetch_stock_daily_success(self, mock_ak_hist):
        """测试成功获取股票数据"""
        mock_df = pd.DataFrame({
            '日期': ['2023-01-01', '2023-01-02'],
            '开盘': [100.0, 102.0],
            '收盘': [105.0, 107.0],
            '最高': [106.0, 108.0],
            '最低': [99.0, 101.0],
            '成交量': [1000000, 1100000],
            '成交额': [100000000, 110000000],
            '振幅': [5.0, 5.0],
            '涨跌幅': [5.0, 5.0],
            '涨跌额': [5.0, 5.0],
            '换手率': [1.0, 1.0]
        })
        mock_ak_hist.return_value = mock_df
        
        fetcher = DataFetcher()
        df = fetcher.fetch_stock_daily('600000', '2023-01-01', '2023-01-31')
        
        assert not df.empty
        assert 'trade_date' in df.columns
        assert 'open_price' in df.columns
        assert 'close_price' in df.columns
        assert len(df) == 2
    
    @patch('app.data_fetcher.ak.stock_zh_a_hist')
    def test_fetch_stock_daily_empty(self, mock_ak_hist):
        """测试获取空数据"""
        mock_df = pd.DataFrame()
        mock_ak_hist.return_value = mock_df
        
        fetcher = DataFetcher()
        df = fetcher.fetch_stock_daily('600000', '2023-01-01', '2023-01-31')
        
        assert df.empty
    
    @patch('app.data_fetcher.ak.stock_zh_a_hist')
    def test_fetch_stock_daily_error(self, mock_ak_hist):
        """测试获取数据错误"""
        mock_ak_hist.side_effect = Exception("Network error")
        
        fetcher = DataFetcher()
        df = fetcher.fetch_stock_daily('600000', '2023-01-01', '2023-01-31')
        
        assert df.empty
    
    def test_save_to_db(self):
        """测试保存到数据库"""
        fetcher = DataFetcher()
        
        df = pd.DataFrame({
            'trade_date': [date(2023, 1, 1), date(2023, 1, 2)],
            'open_price': [100.0, 102.0],
            'high_price': [105.0, 107.0],
            'low_price': [99.0, 101.0],
            'close_price': [105.0, 107.0],
            'volume': [1000000, 1100000],
            'amount': [100000000, 110000000],
            'amplitude': [5.0, 5.0],
            'change_pct': [5.0, 5.0],
            'change_amount': [5.0, 5.0],
            'turnover': [1.0, 1.0]
        })
        
        db = MagicMock()
        db.execute = MagicMock()
        db.commit = MagicMock()
        
        count = fetcher.save_to_db(db, df, '600000')
        
        assert count == 2
        assert db.execute.call_count == 2
        db.commit.assert_called_once()
    
    def test_save_to_db_empty(self):
        """测试保存空数据"""
        fetcher = DataFetcher()
        db = MagicMock()
        
        df = pd.DataFrame()
        count = fetcher.save_to_db(db, df, '600000')
        
        assert count == 0
        db.execute.assert_not_called()
    
    def test_get_stock_data_from_db(self):
        """测试从数据库获取股票数据"""
        fetcher = DataFetcher()
        
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        
        mock_stock1 = StockDaily(
            stock_code='600000',
            trade_date=date(2023, 1, 1),
            open_price=100.0,
            high_price=105.0,
            low_price=99.0,
            close_price=105.0,
            volume=1000000,
            amount=100000000
        )
        mock_stock2 = StockDaily(
            stock_code='600000',
            trade_date=date(2023, 1, 2),
            open_price=102.0,
            high_price=107.0,
            low_price=101.0,
            close_price=107.0,
            volume=1100000,
            amount=110000000
        )
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [mock_stock1, mock_stock2]
        
        result = fetcher.get_stock_data_from_db(mock_session, '600000')
        
        assert len(result) == 2
        assert result[0].stock_code == '600000'
        assert result[0].trade_date == date(2023, 1, 1)
    
    def test_get_stock_data_from_db_with_date_range(self):
        """测试带日期范围的查询"""
        fetcher = DataFetcher()
        
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter
        mock_filter.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_filter
        mock_filter.all.return_value = []
        
        start_date = date(2023, 1, 1)
        end_date = date(2023, 1, 31)
        
        result = fetcher.get_stock_data_from_db(mock_session, '600000', start_date, end_date)
        
        assert result == []
        assert mock_filter.filter.call_count == 2
