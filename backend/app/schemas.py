from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import date, datetime

class StockDailyBase(BaseModel):
    stock_code: str
    trade_date: date
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float
    amount: Optional[float] = None
    amplitude: Optional[float] = None
    change_pct: Optional[float] = None
    change_amount: Optional[float] = None
    turnover: Optional[float] = None

class StockDailyResponse(StockDailyBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class BacktestRequest(BaseModel):
    stock_code: str
    start_date: date
    end_date: date
    initial_capital: float = 100000.0
    ma_period: int = 5
    strategy_name: str = "MA_Cross"
    market_cap: Optional[float] = None

class StrategyInfo(BaseModel):
    name: str
    params: Dict[str, Any]

class SignalInfo(BaseModel):
    breakout_days: List[Dict[str, Any]] = []
    decay_reached_days: List[Dict[str, Any]] = []
    signal_days: List[Dict[str, Any]] = []
    volume_check_days: List[Dict[str, Any]] = []
    price_check_days: List[Dict[str, Any]] = []

class TradeRecordResponse(BaseModel):
    id: int
    trade_type: str
    trade_date: date
    price: float
    shares: int
    amount: float
    
    class Config:
        from_attributes = True

class BacktestResultResponse(BaseModel):
    id: int
    stock_code: str
    strategy_name: str
    start_date: date
    end_date: date
    initial_capital: float
    final_capital: float
    total_return: float
    annual_return: Optional[float]
    max_drawdown: Optional[float]
    win_rate: Optional[float]
    total_trades: Optional[int]
    profit_trades: Optional[int]
    loss_trades: Optional[int]
    trades: List[TradeRecordResponse] = []
    
    class Config:
        from_attributes = True

class EquityCurvePoint(BaseModel):
    date: date
    equity: float
    benchmark: Optional[float] = None

class KLineData(BaseModel):
    date: date
    open: float
    close: float
    high: float
    low: float
    volume: float

class BacktestDetailResponse(BaseModel):
    result: BacktestResultResponse
    equity_curve: List[EquityCurvePoint]
    kline_data: List[KLineData] = []
    signals_info: Optional[SignalInfo] = None

class StrategyListResponse(BaseModel):
    strategies: List[StrategyInfo]


class BulkDownloadRequest(BaseModel):
    task_id: Optional[str] = None


class BulkDownloadStatus(BaseModel):
    is_downloading: bool
    last_update_time: Optional[str]
    download_status: Dict[str, Any] = {}


class DatabaseInfo(BaseModel):
    latest_date: Optional[str]
    stock_count: int
    min_date: Optional[str]
