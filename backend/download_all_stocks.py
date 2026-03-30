#!/usr/bin/env python
"""
批量下载所有A股非ST股票数据脚本
使用方法: python backend/download_all_stocks.py
"""

import sys
import os
import time
from datetime import datetime

# 添加backend路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.database import SessionLocal, init_db
from app.data_fetcher import data_fetcher
from app.stock_list.fetcher import stock_list_fetcher


def download_all_stocks():
    """批量下载所有A股非ST股票数据"""
    print("=" * 60)
    print("开始批量下载A股非ST股票数据")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 初始化数据库
    init_db()
    
    # 获取股票列表
    print("\n正在获取股票列表...")
    stock_codes = stock_list_fetcher.get_all_stock_codes()
    print(f"找到 {len(stock_codes)} 只非ST股票")
    
    if not stock_codes:
        print("未找到任何股票，退出")
        return
    
    # 确认下载
    response = input(f"\n确定要下载 {len(stock_codes)} 只股票的数据吗？(y/n): ")
    if response.lower() != 'y':
        print("已取消下载")
        return
    
    # 开始下载
    db = SessionLocal()
    success_count = 0
    fail_count = 0
    total = len(stock_codes)
    
    try:
        for idx, stock_code in enumerate(stock_codes):
            progress = (idx + 1) / total * 100
            
            print(f"\r[{idx + 1}/{total}] [{progress:.1f}%] 正在下载 {stock_code}...", end='', flush=True)
            
            try:
                result = data_fetcher.fetch_and_save(stock_code)
                
                if result["success"]:
                    success_count += 1
                else:
                    fail_count += 1
                    print(f"\n[失败] {stock_code}: {result.get('message', '未知错误')}")
                    
            except Exception as e:
                fail_count += 1
                print(f"\n[异常] {stock_code}: {e}")
            
            # 避免请求过快
            time.sleep(0.1)
        
        print(f"\n\n{'=' * 60}")
        print("下载完成!")
        print(f"成功: {success_count} 只")
        print(f"失败: {fail_count} 只")
        print(f"总耗时: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
    finally:
        db.close()


if __name__ == '__main__':
    try:
        download_all_stocks()
    except KeyboardInterrupt:
        print("\n\n下载已中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n下载出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
