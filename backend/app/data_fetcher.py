import akshare as ak
import pandas as pd
from datetime import date, datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.dialects.mysql import insert
from .models import StockDaily
from .database import SessionLocal


class DataFetcher:
    def __init__(self):
        pass
    
    def fetch_stock_daily(
        self, 
        stock_code: str, 
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        try:
            if start_date:
                start_date = start_date.replace('-', '')
            if end_date:
                end_date = end_date.replace('-', '')
            
            start = start_date or "20200101"
            end = end_date or datetime.now().strftime("%Y%m%d")
            
            print(f"Fetching data: symbol={stock_code}, start={start}, end={end}")
            
            df = ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                start_date=start,
                end_date=end,
                adjust="qfq"
            )
            
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
            
            return df
        except Exception as e:
            import traceback
            print(f"Error fetching data for {stock_code}: {e}")
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
