#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AKShare 数据获取测试脚本
仅调用外部数据源,不写入数据库

使用方法:
    cd backend
    .venv/bin/python ../test_api_simple.py

测试用例说明:
    1. 基础测试 - 茅台 (600519) - 2020年数据
    2. 问题股票 - 600734 (已知有负值)
    3. 深市股票 - 平安银行 (000001)
    4. 创业板股票 - 宁德时代 (300750)
    5. 最近数据 - 茅台 (2026年3月)
"""

import sys
sys.path.insert(0, '.')

import akshare as ak
import pandas as pd
from datetime import datetime


def fetch_stock_data(stock_code: str, start_date: str, end_date: str, adjust: str = "hfq"):
    """
    获取股票数据
    
    Args:
        stock_code: 股票代码 (如 "600519")
        start_date: 开始日期 (格式: "20200101")
        end_date: 结束日期 (格式: "20260330")
        adjust: 复权方式 ("hfq" 后复权, "qfq" 前复权)
    
    Returns:
        tuple: (成功标志, DataFrame或错误信息)
    """
    try:
        print(f"\n正在获取: {stock_code} ({start_date} 至 {end_date})...")
        
        df = ak.stock_zh_a_hist(
            symbol=stock_code,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust=adjust
        )
        
        return (True, df)
        
    except Exception as e:
        return (False, str(e))


def print_data_summary(stock_code: str, success: bool, data):
    """打印数据摘要"""
    print(f"\n{'='*70}")
    print(f"股票代码: {stock_code}")
    print(f"状态: {'✓ 成功' if success else '✗ 失败'}")
    
    if success and isinstance(data, pd.DataFrame):
        print(f"数据行数: {len(data)}")
        print(f"列名: {data.columns.tolist()}")
        
        if not data.empty:
            print(f"\n前3行数据:")
            print(data[['日期', '开盘', '收盘', '最高', '最低']].head(3))
            
            print(f"\n后3行数据:")
            print(data[['日期', '开盘', '收盘', '最高', '最低']].tail(3))
            
            # 检查负值
            price_cols = ['开盘', '收盘', '最高', '最低']
            has_negative = False
            for col in price_cols:
                if col in data.columns:
                    negative_count = (data[col] < 0).sum()
                    if negative_count > 0:
                        print(f"\n⚠️  警告: {col} 列有 {negative_count} 个负值")
                        has_negative = True
            
            if not has_negative:
                print(f"\n✓ 所有价格字段均为非负值")
    else:
        print(f"错误信息: {data}")
    
    print(f"{'='*70}\n")


def main():
    """运行测试"""
    print("="*70)
    print("AKShare 数据获取测试")
    print("仅测试数据获取,不写入数据库")
    print("="*70)
    
    # 测试用例
    test_cases = [
        {
            "name": "测试1: 茅台 (600519) - 2020年数据",
            "stock_code": "600519",
            "start_date": "20200101",
            "end_date": "20201231",
            "adjust": "hfq"
        }
        # {
        #     "name": "测试2: 问题股票 (600734) - 2005年数据 (已知有负值)",
        #     "stock_code": "600734",
        #     "start_date": "20050501",
        #     "end_date": "20050520",
        #     "adjust": "hfq"
        # },
        # {
        #     "name": "测试3: 深市股票 (000001) - 平安银行",
        #     "stock_code": "000001",
        #     "start_date": "20200101",
        #     "end_date": "20201231",
        #     "adjust": "hfq"
        # },
        # {
        #     "name": "测试4: 创业板股票 (300750) - 宁德时代",
        #     "stock_code": "300750",
        #     "start_date": "20200101",
        #     "end_date": "20201231",
        #     "adjust": "hfq"
        # },
        # {
        #     "name": "测试5: 最近数据 (600519) - 2026年3月",
        #     "stock_code": "600519",
        #     "start_date": "20260301",
        #     "end_date": "20260330",
        #     "adjust": "hfq"
        # },
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'#'*70}")
        print(f"{test_case['name']}")
        print(f"{'#'*70}")
        
        success, data = fetch_stock_data(
            test_case['stock_code'],
            test_case['start_date'],
            test_case['end_date'],
            test_case['adjust']
        )
        
        print_data_summary(test_case['stock_code'], success, data)
        
        results.append({
            "name": test_case['name'],
            "success": success
        })
    
    # 汇总
    print(f"\n\n{'='*70}")
    print("测试结果汇总")
    print(f"{'='*70}")
    
    for result in results:
        status = "✓ 通过" if result['success'] else "✗ 失败"
        print(f"{status} - {result['name']}")
    
    passed = sum(1 for r in results if r['success'])
    total = len(results)
    print(f"\n总计: {passed}/{total} 通过")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
