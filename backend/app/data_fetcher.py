import akshare as ak
import pandas as pd
from datetime import date, datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.dialects.mysql import insert
from .models import StockDaily
from .database import SessionLocal
import time
import random
import logging

logger = logging.getLogger(__name__)


USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]


class DataFetcher:
    def __init__(self, max_retries=3, retry_delay=2, sleep_min=2.0, sleep_max=5.0):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.sleep_min = sleep_min
        self.sleep_max = sleep_max
        self._last_request_time: Optional[float] = None
    
    def _set_random_user_agent(self) -> None:
        """设置随机 User-Agent"""
        try:
            random_ua = random.choice(USER_AGENTS)
            logger.debug(f"设置 User-Agent: {random_ua[:50]}...")
        except Exception as e:
            logger.debug(f"设置 User-Agent 失败: {e}")
    
    def _enforce_rate_limit(self) -> None:
        """强制执行速率限制,防止被封禁"""
        if self._last_request_time is not None:
            elapsed = time.time() - self._last_request_time
            min_interval = self.sleep_min
            if elapsed < min_interval:
                additional_sleep = min_interval - elapsed
                logger.debug(f"补充休眠 {additional_sleep:.2f} 秒")
                time.sleep(additional_sleep)
        
        self._last_request_time = time.time()
        random_sleep = random.uniform(self.sleep_min, self.sleep_max)
        logger.debug(f"随机休眠 {random_sleep:.2f} 秒")
        time.sleep(random_sleep)
    
    def _fetch_stock_data_em(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """东方财富数据源"""
        self._set_random_user_agent()
        self._enforce_rate_limit()
        
        logger.info(f"[API调用] ak.stock_zh_a_hist(symbol={stock_code}, start={start_date}, end={end_date})")
        
        try:
            df = ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"
            )
            
            logger.info(f"[API返回] 东方财富成功: {len(df)} 行数据")
            return df
            
        except Exception as e:
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in ['banned', 'blocked', '频率', 'rate', '限制']):
                logger.warning(f"[东方财富] 可能被限流: {e}")
            raise e
    
    def _fetch_stock_data_sina(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """新浪财经数据源"""
        self._enforce_rate_limit()
        
        symbol = f"sh{stock_code}" if stock_code.startswith("6") else f"sz{stock_code}"
        
        try:
            df = ak.stock_zh_a_daily(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"
            )
            
            if df is not None and not df.empty:
                df = df.rename(columns={
                    'date': '日期',
                    'open': '开盘',
                    'high': '最高',
                    'low': '最低',
                    'close': '收盘',
                    'volume': '成交量',
                    'amount': '成交额'
                })
                logger.info(f"[API返回] 新浪财经成功: {len(df)} 行数据")
                return df
            return pd.DataFrame()
            
        except Exception as e:
            logger.warning(f"[新浪财经] 获取失败: {e}")
            raise e
    
    def _fetch_stock_data_tx(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """腾讯财经数据源"""
        self._enforce_rate_limit()
        
        symbol = f"sh{stock_code}" if stock_code.startswith("6") else f"sz{stock_code}"
        
        try:
            df = ak.stock_zh_a_hist_tx(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"
            )
            
            if df is not None and not df.empty:
                df = df.rename(columns={
                    'date': '日期',
                    'open': '开盘',
                    'high': '最高',
                    'low': '最低',
                    'close': '收盘',
                    'volume': '成交量',
                    'amount': '成交额'
                })
                logger.info(f"[API返回] 腾讯财经成功: {len(df)} 行数据")
                return df
            return pd.DataFrame()
            
        except Exception as e:
            logger.warning(f"[腾讯财经] 获取失败: {e}")
            raise e
    
    def _fetch_with_fallback(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """带数据源降级的数据获取"""
        methods = [
            # (self._fetch_stock_data_em, "东方财富"),  # 东方财富被封禁,暂时禁用
            (self._fetch_stock_data_sina, "新浪财经"),
            (self._fetch_stock_data_tx, "腾讯财经"),
        ]
        
        last_error = None
        
        for fetch_method, source_name in methods:
            try:
                logger.info(f"[数据源] 尝试使用 {source_name} 获取 {stock_code}...")
                df = fetch_method(stock_code, start_date, end_date)
                
                if df is not None and not df.empty:
                    logger.info(f"[数据源] {source_name} 获取成功")
                    return df
            except Exception as e:
                last_error = e
                logger.warning(f"[数据源] {source_name} 获取失败: {e}")
        
        raise last_error if last_error else Exception("所有数据源获取失败")
    
    def fetch_stock_daily(
        self, 
        stock_code: str, 
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                if start_date:
                    start_date_clean = start_date.replace('-', '')
                else:
                    start_date_clean = "20200101"
                    
                if end_date:
                    end_date_clean = end_date.replace('-', '')
                else:
                    end_date_clean = datetime.now().strftime("%Y%m%d")
                
                print(f"Fetching data: symbol={stock_code}, start={start_date_clean}, end={end_date_clean} (attempt {attempt + 1}/{self.max_retries})")
                
                df = self._fetch_with_fallback(stock_code, start_date_clean, end_date_clean)
                
                print(f"Raw data shape: {df.shape if not df.empty else 'empty'}")
                if not df.empty:
                    print(f"Columns: {df.columns.tolist()}")
                
                if df.empty:
                    return pd.DataFrame()
                
                df = df.rename(columns={
                    '日期': 'trade_date',
                    '开盘': 'open_price',
                    '收盘': 'close_price',
                    '最高': 'high_price',
                    '最低': 'low_price',
                    '成交量': 'volume',
                    '成交额': 'amount',
                    '振幅': 'amplitude',
                    '涨跌幅': 'change_pct',
                    '涨跌额': 'change_amount',
                    '换手率': 'turnover'
                })
                
                df['trade_date'] = pd.to_datetime(df['trade_date']).dt.date
                df['stock_code'] = stock_code
                
                # 清理数据：处理后复权数据可能出现的负值
                price_columns = ['open_price', 'close_price', 'high_price', 'low_price']
                for col in price_columns:
                    if col in df.columns:
                        df.loc[df[col] < 0, col] = None
                        df[col] = df[col].fillna(0.0).astype(float)
                
                for col in price_columns:
                    if col in df.columns:
                        df.loc[df[col] <= 0, col] = 0.0
                
                return df
                
            except Exception as e:
                last_error = e
                print(f"Attempt {attempt + 1} failed for {stock_code}: {e}")
                
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay + random.uniform(0, 1)
                    print(f"Retrying in {delay:.1f} seconds...")
                    time.sleep(delay)
        
        import traceback
        print(f"Error fetching data for {stock_code} after {self.max_retries} attempts: {last_error}")
        traceback.print_exc()
        return pd.DataFrame()
    
    def save_to_db(self, db: Session, df: pd.DataFrame, stock_code: str) -> int:
        if df.empty:
            return 0
        
        saved_count = 0
        for _, row in df.iterrows():
            try:
                stmt = insert(StockDaily).values(
                    stock_code=stock_code,
                    trade_date=row['trade_date'],
                    open_price=float(row['open_price']),
                    high_price=float(row['high_price']),
                    low_price=float(row['low_price']),
                    close_price=float(row['close_price']),
                    volume=float(row['volume']),
                    amount=float(row['amount']) if pd.notna(row.get('amount')) else None,
                    amplitude=float(row['amplitude']) if pd.notna(row.get('amplitude')) else None,
                    change_pct=float(row['change_pct']) if pd.notna(row.get('change_pct')) else None,
                    change_amount=float(row['change_amount']) if pd.notna(row.get('change_amount')) else None,
                    turnover=float(row['turnover']) if pd.notna(row.get('turnover')) else None,
                )
                
                stmt = stmt.on_duplicate_key_update(
                    open_price=float(row['open_price']),
                    high_price=float(row['high_price']),
                    low_price=float(row['low_price']),
                    close_price=float(row['close_price']),
                    volume=float(row['volume']),
                    amount=float(row['amount']) if pd.notna(row.get('amount')) else None,
                    amplitude=float(row['amplitude']) if pd.notna(row.get('amplitude')) else None,
                    change_pct=float(row['change_pct']) if pd.notna(row.get('change_pct')) else None,
                    change_amount=float(row['change_amount']) if pd.notna(row.get('change_amount')) else None,
                    turnover=float(row['turnover']) if pd.notna(row.get('turnover')) else None,
                )
                
                db.execute(stmt)
                saved_count += 1
            except Exception as e:
                print(f"Error saving row: {e}")
                continue
        
        db.commit()
        return saved_count
    
    def fetch_and_save(
        self, 
        stock_code: str, 
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> dict:
        df = self.fetch_stock_daily(stock_code, start_date, end_date)
        
        if df.empty:
            return {"success": False, "message": "No data fetched", "count": 0}
        
        db = SessionLocal()
        try:
            saved_count = self.save_to_db(db, df, stock_code)
            return {
                "success": True, 
                "message": f"Successfully saved {saved_count} records",
                "count": saved_count
            }
        finally:
            db.close()
    
    def get_stock_data_from_db(
        self,
        db: Session,
        stock_code: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[StockDaily]:
        query = db.query(StockDaily).filter(StockDaily.stock_code == stock_code)
        
        if start_date:
            query = query.filter(StockDaily.trade_date >= start_date)
        if end_date:
            query = query.filter(StockDaily.trade_date <= end_date)
        
        return query.order_by(StockDaily.trade_date).all()


data_fetcher = DataFetcher()
