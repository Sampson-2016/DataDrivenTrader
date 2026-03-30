#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试新的数据获取方法(多数据源降级) - 完整版
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.data_fetcher import DataFetcher

def test_new_fetcher():
    """测试新的数据获取器"""
    fetcher = DataFetcher(max_retries=2, retry_delay=1, sleep_min=1.0, sleep_max=2.0)
    
    print("=" * 60)
    print("测试新的多数据源数据获取器(东方财富已禁用)")
    print("=" * 60)
    
    test_cases = [
        {
            "name": "测试1: 茅台 (600519) - 2020年数据",
            "stock_code": "600519",
            "start_date": "2020-01-01",
            "end_date": "2020-12-31",
        },
        {
            "name": "测试2: 深市股票 (000001) - 平安银行",
            "stock_code": "000001",
            "start_date": "2020-01-01",
            "end_date": "2020-12-31",
        },
        {
            "name": "测试3: 最近数据 (600519) - 2026年3月",
            "stock_code": "600519",
            "start_date": "2026-03-01",
            "end_date": "2026-03-30",
        }
    ]
    
    results = []
    
    for test_case in test_cases:
        print(f"\n{'#'*60}")
        print(f"{test_case['name']}")
        print(f"{'#'*60}")
        
        try:
            df = fetcher.fetch_stock_daily(
                stock_code=test_case['stock_code'],
                start_date=test_case['start_date'],
                end_date=test_case['end_date']
            )
            
            if not df.empty:
                print(f"✓ 数据获取成功!")
                print(f"数据行数: {len(df)}")
                print(f"列名: {df.columns.tolist()}")
                print(f"\n前3行数据预览:")
                print(df[['trade_date', 'open_price', 'close_price', 'high_price', 'low_price']].head(3))
                results.append((test_case['name'], True, None))
            else:
                print(f"✗ 获取到空数据")
                results.append((test_case['name'], False, "Empty data"))
                
        except Exception as e:
            print(f"✗ 数据获取失败!")
            print(f"错误类型: {type(e).__name__}")
            print(f"错误信息: {str(e)}")
            results.append((test_case['name'], False, str(e)))
    
    print(f"\n{'='*60}")
    print("测试结果汇总")
    print(f"{'='*60}")
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    for name, success, error in results:
        status = "✓ 通过" if success else f"✗ 失败 - {error}"
        print(f"{status} - {name}")
    
    print(f"\n总计: {passed}/{total} 通过")
    print("=" * 60)

if __name__ == "__main__":
    test_new_fetcher()
