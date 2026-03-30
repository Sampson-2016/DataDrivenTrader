import akshare as ak
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime


class StockListFetcher:
    """股票列表获取器"""
    
    def __init__(self):
        pass
    
    def get_all_stock_codes(self) -> List[str]:
        """获取所有A股股票代码（非ST）"""
        try:
            # 获取沪市股票
            sh_stocks = ak.stock_info_sh_name_code()
            # 获取深市股票
            sz_stocks = ak.stock_info_sz_name_code()
            
            # 统一列名：将沪市的列名转换为深市的格式
            if '证券代码' in sh_stocks.columns and 'A股代码' not in sh_stocks.columns:
                sh_stocks = sh_stocks.rename(columns={
                    '证券代码': 'A股代码',
                    '证券简称': 'A股名称'
                })
            
            # 合并
            all_stocks = pd.concat([sh_stocks, sz_stocks], ignore_index=True)
            
            # 过滤ST股票
            code_col = 'A股代码'
            name_col = 'A股名称' if 'A股名称' in all_stocks.columns else '证券简称'
            
            non_st_stocks = all_stocks[
                ~all_stocks[code_col].astype(str).str.contains('ST') &
                ~all_stocks[code_col].astype(str).str.contains('退') &
                ~all_stocks[name_col].astype(str).str.contains('ST') &
                ~all_stocks[name_col].astype(str).str.contains('退')
            ]
            
            # 提取股票代码
            stock_codes = non_st_stocks[code_col].astype(str).tolist()
            
            # 格式化代码（确保6位）
            formatted_codes = []
            for code in stock_codes:
                code = str(code).zfill(6)
                if code.endswith('000000') or code.endswith('000001'):
                    continue  # 过滤特殊代码
                formatted_codes.append(code)
            
            return formatted_codes
        except Exception as e:
            print(f"Error fetching stock list: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_stock_names(self) -> Dict[str, str]:
        """获取股票代码和名称的映射"""
        try:
            sh_stocks = ak.stock_info_sh_name_code()
            sz_stocks = ak.stock_info_sz_name_code()
            
            all_stocks = pd.concat([sh_stocks, sz_stocks], ignore_index=True)
            
            non_st_stocks = all_stocks[
                ~all_stocks['A股代码'].str.contains('ST') &
                ~all_stocks['A股代码'].str.contains('退') &
                ~all_stocks['A股名称'].str.contains('ST') &
                ~all_stocks['A股名称'].str.contains('退')
            ]
            
            stock_map = {}
            for _, row in non_st_stocks.iterrows():
                code = str(row['A股代码']).zfill(6)
                name = row['A股名称']
                if not code.endswith('000000') and not code.endswith('000001'):
                    stock_map[code] = name
            
            return stock_map
        except Exception as e:
            print(f"Error fetching stock names: {e}")
            return {}
    
    def get_latest_trading_date(self) -> Optional[str]:
        """获取最新交易日期"""
        try:
            # 获取上证指数历史数据，最后一行就是最新日期
            df = ak.stock_zh_a_hist(symbol="000001", period="daily", 
                                   start_date="20240101", 
                                   end_date=datetime.now().strftime("%Y%m%d"))
            
            if not df.empty:
                latest_date = df.iloc[-1]['日期']
                return str(latest_date).split(' ')[0]
            return None
        except Exception as e:
            print(f"Error fetching latest trading date: {e}")
            return None


stock_list_fetcher = StockListFetcher()
