import threading
import time
from typing import Dict, Optional
from datetime import date, datetime
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models import StockDaily
from ..data_fetcher import data_fetcher
from ..stock_list.fetcher import stock_list_fetcher


class BulkDownloadManager:
    """批量下载管理器"""
    
    _instance = None
    _download_status = {}
    _download_progress = {}
    _is_downloading = False
    _last_update_time = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @property
    def is_downloading(self) -> bool:
        return self._is_downloading
    
    @property
    def last_update_time(self) -> Optional[str]:
        """获取最新更新时间"""
        if self._last_update_time:
            return self._last_update_time.strftime("%Y-%m-%d %H:%M:%S")
        
        # 从数据库查询最新数据日期
        db = SessionLocal()
        try:
            result = db.query(StockDaily.trade_date).order_by(
                StockDaily.trade_date.desc()
            ).first()
            
            if result:
                self._last_update_time = result[0]
                return self._last_update_time.strftime("%Y-%m-%d")
            return None
        finally:
            db.close()
    
    def get_download_status(self, task_id: str) -> Dict:
        """获取下载状态"""
        return self._download_status.get(task_id, {
            "status": "not_found",
            "progress": 0,
            "current": 0,
            "total": 0,
            "message": ""
        })
    
    def get_all_status(self) -> Dict:
        """获取所有状态"""
        return {
            "is_downloading": self._is_downloading,
            "last_update_time": self.last_update_time,
            "download_status": self._download_status
        }
    
    def start_bulk_download(self, task_id: str) -> bool:
        """开始批量下载"""
        if self._is_downloading:
            return False
        
        self._is_downloading = True
        self._download_status[task_id] = {
            "status": "running",
            "progress": 0,
            "current": 0,
            "total": 0,
            "message": "开始下载..."
        }
        
        # 启动后台下载线程
        thread = threading.Thread(
            target=self._bulk_download_task,
            args=(task_id,),
            daemon=True
        )
        thread.start()
        
        return True
    
    def _bulk_download_task(self, task_id: str):
        """批量下载任务"""
        try:
            # 获取股票列表
            stock_codes = stock_list_fetcher.get_all_stock_codes()
            total = len(stock_codes)
            
            self._download_status[task_id]["total"] = total
            self._download_status[task_id]["message"] = f"找到 {total} 只股票"
            
            success_count = 0
            fail_count = 0
            
            for idx, stock_code in enumerate(stock_codes):
                if not self._is_downloading:
                    break
                
                # 更新进度
                self._download_status[task_id]["current"] = idx + 1
                self._download_status[task_id]["progress"] = int((idx + 1) / total * 100)
                self._download_status[task_id]["message"] = f"正在下载 {stock_code}..."
                
                try:
                    # 下载并保存数据
                    result = data_fetcher.fetch_and_save(stock_code)
                    
                    if result["success"]:
                        success_count += 1
                    else:
                        fail_count += 1
                        
                except Exception as e:
                    fail_count += 1
                    print(f"下载 {stock_code} 失败: {e}")
                
                # 避免请求过快
                time.sleep(1)
            
            # 更新完成状态
            self._download_status[task_id]["status"] = "completed"
            self._download_status[task_id]["message"] = f"下载完成: 成功{success_count}只, 失败{fail_count}只"
            self._download_status[task_id]["progress"] = 100
            
            # 更新最后时间
            self._last_update_time = datetime.now()
            
        except Exception as e:
            self._download_status[task_id]["status"] = "error"
            self._download_status[task_id]["message"] = f"下载出错: {e}"
        
        finally:
            self._is_downloading = False
    
    def stop_download(self):
        """停止下载"""
        self._is_downloading = False


bulk_download_manager = BulkDownloadManager()
