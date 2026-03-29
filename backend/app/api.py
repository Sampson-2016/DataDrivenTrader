from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import date

from .database import get_db, init_db
from .models import StockDaily, BacktestResult, TradeRecord
from .schemas import (
    StockDailyResponse, 
    BacktestRequest, 
    BacktestResultResponse,
    BacktestDetailResponse,
    EquityCurvePoint,
    TradeRecordResponse,
    KLineData
)
from .data_fetcher import data_fetcher
from .backtest_engine import backtest_engine

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
    stock_data = data_fetcher.get_stock_data_from_db(
        db, 
        request.stock_code,
        request.start_date,
        request.end_date
    )
    
    if not stock_data:
        raise HTTPException(status_code=404, detail="No stock data found. Please fetch data first.")
    
    try:
        result, trades, equity_curve = backtest_engine.run_backtest(
            stock_data,
            ma_period=request.ma_period,
            initial_capital=request.initial_capital
        )
        
        backtest_result = backtest_engine.save_backtest_result(
            db,
            request.stock_code,
            f"MA{request.ma_period}_Cross",
            request.start_date,
            request.end_date,
            result,
            trades
        )
        
        trade_records = db.query(TradeRecord).filter(
            TradeRecord.backtest_id == backtest_result.id
        ).all()
        
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
            ) for e in equity_curve],
            kline_data=[KLineData(
                date=s.trade_date,
                open=s.open_price,
                close=s.close_price,
                high=s.high_price,
                low=s.low_price,
                volume=s.volume
            ) for s in stock_data]
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
