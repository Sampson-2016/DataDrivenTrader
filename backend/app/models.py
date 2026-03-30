from sqlalchemy import Column, Integer, String, Float, Date, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from .database import Base

class StockDaily(Base):
    __tablename__ = "stock_daily"
    
    id = Column(Integer, primary_key=True, index=True)
    stock_code = Column(String(10), nullable=False, index=True, comment="股票代码")
    trade_date = Column(Date, nullable=False, index=True, comment="交易日期")
    open_price = Column(Float, nullable=False, comment="开盘价")
    high_price = Column(Float, nullable=False, comment="最高价")
    low_price = Column(Float, nullable=False, comment="最低价")
    close_price = Column(Float, nullable=False, comment="收盘价")
    volume = Column(Float, nullable=False, comment="成交量")
    amount = Column(Float, nullable=True, comment="成交额")
    amplitude = Column(Float, nullable=True, comment="振幅")
    change_pct = Column(Float, nullable=True, comment="涨跌幅")
    change_amount = Column(Float, nullable=True, comment="涨跌额")
    turnover = Column(Float, nullable=True, comment="换手率")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        UniqueConstraint('stock_code', 'trade_date', name='uq_stock_date'),
    )


class BacktestResult(Base):
    __tablename__ = "backtest_result"
    
    id = Column(Integer, primary_key=True, index=True)
    stock_code = Column(String(10), nullable=False, index=True)
    strategy_name = Column(String(50), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    initial_capital = Column(Float, nullable=False)
    final_capital = Column(Float, nullable=False)
    total_return = Column(Float, nullable=False)
    annual_return = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)
    win_rate = Column(Float, nullable=True)
    total_trades = Column(Integer, nullable=True)
    profit_trades = Column(Integer, nullable=True)
    loss_trades = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class TradeRecord(Base):
    __tablename__ = "trade_record"
    
    id = Column(Integer, primary_key=True, index=True)
    backtest_id = Column(Integer, nullable=False, index=True)
    stock_code = Column(String(10), nullable=False)
    trade_type = Column(String(10), nullable=False, comment="buy/sell")
    trade_date = Column(Date, nullable=False)
    price = Column(Float, nullable=False)
    shares = Column(Integer, nullable=False)
    amount = Column(Float, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class DataUpdateLog(Base):
    __tablename__ = "data_update_log"
    
    id = Column(Integer, primary_key=True, index=True)
    update_type = Column(String(50), nullable=False, comment="update_type: bulk_download, single_stock")
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    total_stocks = Column(Integer, nullable=True)
    success_count = Column(Integer, nullable=True)
    fail_count = Column(Integer, nullable=True)
    message = Column(String(500), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
