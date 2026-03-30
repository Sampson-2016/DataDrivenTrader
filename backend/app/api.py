from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from .database import get_db, init_db, SessionLocal
from .models import StockDaily, BacktestResult, TradeRecord, DataUpdateLog
from .schemas import (
    StockDailyResponse, 
    BacktestRequest, 
    BacktestResultResponse,
    BacktestDetailResponse,
    EquityCurvePoint,
    TradeRecordResponse,
    KLineData,
    StrategyInfo,
    SignalInfo,
    StrategyListResponse,
    BulkDownloadRequest,
    BulkDownloadStatus,
    DatabaseInfo
)
from .data_fetcher import data_fetcher
from .backtest_engine import backtest_engine
from .strategies.base import StrategyRegistry
from .bulk_download.manager import bulk_download_manager

router = APIRouter()


@router.on_event("startup")
async def startup():
    init_db()


@router.get("/")
async def root():
    return {"message": "Stock Backtesting API"}


@router.post("/data/fetch")
async def fetch_data(
    stock_code: str,
    start_date: str = None,
    end_date: str = None
):
    result = data_fetcher.fetch_and_save(stock_code, start_date, end_date)
    return result


@router.get("/data/{stock_code}", response_model=List[StockDailyResponse])
async def get_stock_data(
    stock_code: str,
    start_date: date = None,
    end_date: date = None,
    db: Session = Depends(get_db)
):
    data = data_fetcher.get_stock_data_from_db(db, stock_code, start_date, end_date)
    return data


@router.post("/backtest/run", response_model=BacktestDetailResponse)
async def run_backtest(
    request: BacktestRequest,
    db: Session = Depends(get_db)
):
    # 获取数据库中的数据范围
    db_info = get_database_info()
    latest_date = db_info.latest_date
    
    if not latest_date:
        raise HTTPException(status_code=400, detail="No data in database. Please download data first.")
    
    # 智能时间范围调整
    adjusted_start_date = request.start_date
    adjusted_end_date = request.end_date
    
    # 如果用户选择的开始日期大于数据库最新日期，不允许回测
    if adjusted_start_date > date.fromisoformat(latest_date):
        raise HTTPException(
            status_code=400, 
            detail=f"Start date ({adjusted_start_date}) is later than database latest date ({latest_date}). Please select an earlier start date or download more data."
        )
    
    # 如果用户选择的结束日期大于数据库最新日期，调整为数据库最新日期
    if adjusted_end_date > date.fromisoformat(latest_date):
        adjusted_end_date = date.fromisoformat(latest_date)
    
    stock_data = data_fetcher.get_stock_data_from_db(
        db, 
        request.stock_code,
        adjusted_start_date,
        adjusted_end_date
    )
    
    if not stock_data:
        raise HTTPException(
            status_code=404, 
            detail=f"No stock data found for {request.stock_code} in date range [{adjusted_start_date}, {adjusted_end_date}]. Please download data first."
        )
    
    try:
        from .strategies.energy_decay import EnergyDecayStrategy
        from .strategies.ma_cross import MACrossStrategy
        
        strategy_map = {
            'MA_Cross': MACrossStrategy,
            'Energy_Decay': EnergyDecayStrategy
        }
        
        strategy_class = strategy_map.get(request.strategy_name, MACrossStrategy)
        strategy = strategy_class(initial_capital=request.initial_capital)
        
        if request.strategy_name == 'MA_Cross':
            strategy.ma_period = request.ma_period
        
        result = strategy.run_backtest(
            stock_data,
            market_cap=request.market_cap
        )
        
        backtest_result = backtest_engine.save_backtest_result(
            db,
            request.stock_code,
            result.strategy_name,
            request.start_date,
            request.end_date,
            {
                'initial_capital': result.initial_capital,
                'final_capital': result.final_capital,
                'total_return': result.total_return,
                'annual_return': result.annual_return,
                'max_drawdown': result.max_drawdown,
                'win_rate': result.win_rate,
                'total_trades': result.total_trades,
                'profit_trades': result.profit_trades,
                'loss_trades': result.loss_trades
            },
            []
        )
        
        trade_records = db.query(TradeRecord).filter(
            TradeRecord.backtest_id == backtest_result.id
        ).all()
        
        signals_info = SignalInfo(
            breakout_days=result.signals_info.get('breakout_days', []) if result.signals_info else [],
            decay_reached_days=result.signals_info.get('decay_reached_days', []) if result.signals_info else [],
            signal_days=result.signals_info.get('signal_days', []) if result.signals_info else [],
            volume_check_days=result.signals_info.get('volume_check_days', []) if result.signals_info else [],
            price_check_days=result.signals_info.get('price_check_days', []) if result.signals_info else []
        )
        
        return BacktestDetailResponse(
            result=BacktestResultResponse(
                id=backtest_result.id,
                stock_code=backtest_result.stock_code,
                strategy_name=backtest_result.strategy_name,
                start_date=backtest_result.start_date,
                end_date=backtest_result.end_date,
                initial_capital=backtest_result.initial_capital,
                final_capital=backtest_result.final_capital,
                total_return=backtest_result.total_return,
                annual_return=backtest_result.annual_return,
                max_drawdown=backtest_result.max_drawdown,
                win_rate=backtest_result.win_rate,
                total_trades=backtest_result.total_trades,
                profit_trades=backtest_result.profit_trades,
                loss_trades=backtest_result.loss_trades,
                trades=[TradeRecordResponse(
                    id=t.id,
                    trade_type=t.trade_type,
                    trade_date=t.trade_date,
                    price=t.price,
                    shares=t.shares,
                    amount=t.amount
                ) for t in trade_records]
            ),
            equity_curve=[EquityCurvePoint(
                date=e['date'],
                equity=e['equity'],
                benchmark=e['benchmark']
            ) for e in result.equity_curve],
            kline_data=[KLineData(
                date=s.trade_date,
                open=s.open_price,
                close=s.close_price,
                high=s.high_price,
                low=s.low_price,
                volume=s.volume
            ) for s in stock_data],
            signals_info=signals_info
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/backtest/results", response_model=List[BacktestResultResponse])
async def get_backtest_results(
    stock_code: str = None,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    query = db.query(BacktestResult)
    
    if stock_code:
        query = query.filter(BacktestResult.stock_code == stock_code)
    
    results = query.order_by(BacktestResult.created_at.desc()).limit(limit).all()
    
    response = []
    for r in results:
        trades = db.query(TradeRecord).filter(TradeRecord.backtest_id == r.id).all()
        response.append(BacktestResultResponse(
            id=r.id,
            stock_code=r.stock_code,
            strategy_name=r.strategy_name,
            start_date=r.start_date,
            end_date=r.end_date,
            initial_capital=r.initial_capital,
            final_capital=r.final_capital,
            total_return=r.total_return,
            annual_return=r.annual_return,
            max_drawdown=r.max_drawdown,
            win_rate=r.win_rate,
            total_trades=r.total_trades,
            profit_trades=r.profit_trades,
            loss_trades=r.loss_trades,
            trades=[TradeRecordResponse(
                id=t.id,
                trade_type=t.trade_type,
                trade_date=t.trade_date,
                price=t.price,
                shares=t.shares,
                amount=t.amount
            ) for t in trades]
        ))
    
    return response


@router.get("/backtest/{backtest_id}", response_model=BacktestDetailResponse)
async def get_backtest_detail(
    backtest_id: int,
    db: Session = Depends(get_db)
):
    result = db.query(BacktestResult).filter(BacktestResult.id == backtest_id).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Backtest result not found")
    
    trades = db.query(TradeRecord).filter(TradeRecord.backtest_id == backtest_id).all()
    
    stock_data = data_fetcher.get_stock_data_from_db(
        db,
        result.stock_code,
        result.start_date,
        result.end_date
    )
    
    _, _, equity_curve = backtest_engine.run_backtest(stock_data)
    
    return BacktestDetailResponse(
        result=BacktestResultResponse(
            id=result.id,
            stock_code=result.stock_code,
            strategy_name=result.strategy_name,
            start_date=result.start_date,
            end_date=result.end_date,
            initial_capital=result.initial_capital,
            final_capital=result.final_capital,
            total_return=result.total_return,
            annual_return=result.annual_return,
            max_drawdown=result.max_drawdown,
            win_rate=result.win_rate,
            total_trades=result.total_trades,
            profit_trades=result.profit_trades,
            loss_trades=result.loss_trades,
            trades=[TradeRecordResponse(
                id=t.id,
                trade_type=t.trade_type,
                trade_date=t.trade_date,
                price=t.price,
                shares=t.shares,
                amount=t.amount
            ) for t in trades]
        ),
        equity_curve=[EquityCurvePoint(
            date=e['date'],
            equity=e['equity'],
            benchmark=e['benchmark']
        ) for e in equity_curve]
    )


@router.get("/strategies", response_model=StrategyListResponse)
async def list_strategies():
    """获取所有可用策略"""
    strategies = StrategyRegistry.get_all_strategies()
    strategy_list = []
    
    for s in strategies:
        try:
            strategy_instance = s['class']()
            strategy_list.append(StrategyInfo(
                name=s['name'],
                params=strategy_instance.get_params()
            ))
        except Exception:
            continue
    
    return StrategyListResponse(strategies=strategy_list)


@router.post("/bulk-download/start", response_model=BulkDownloadStatus)
async def start_bulk_download(request: BulkDownloadRequest):
    """开始批量下载"""
    task_id = request.task_id or "default"
    success = bulk_download_manager.start_bulk_download(task_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Download is already running")
    
    return bulk_download_manager.get_all_status()


@router.get("/bulk-download/status", response_model=BulkDownloadStatus)
async def get_bulk_download_status():
    """获取批量下载状态"""
    return bulk_download_manager.get_all_status()


@router.get("/database/info", response_model=DatabaseInfo)
async def get_database_info():
    """获取数据库信息"""
    db = SessionLocal()
    try:
        # 获取最新数据日期
        result = db.query(StockDaily.trade_date).order_by(
            StockDaily.trade_date.desc()
        ).first()
        
        latest_date = result[0].strftime("%Y-%m-%d") if result else None
        
        # 获取股票数量
        stock_count = db.query(StockDaily.stock_code).distinct().count()
        
        # 获取数据范围
        min_date_result = db.query(StockDaily.trade_date).order_by(
            StockDaily.trade_date.asc()
        ).first()
        min_date = min_date_result[0].strftime("%Y-%m-%d") if min_date_result else None
        
        return DatabaseInfo(
            latest_date=latest_date,
            stock_count=stock_count,
            min_date=min_date
        )
    finally:
        db.close()
