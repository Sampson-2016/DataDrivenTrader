#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
手动测试AKShare数据获取接口
仅调用外部数据源,不写入数据库
用于测试不同股票和日期范围的数据获取情况
"""

import akshare as ak
import pandas as pd
from datetime import datetime


def test_stock_data_fetch(stock_code: str, start_date: str, end_date: str, adjust: str = "hfq"):
    """
    测试单只股票的数据获取
    
    Args:
        stock_code: 股票代码 (如 "600000")
        start_date: 开始日期 (格式: "20200101")
        end_date: 结束日期 (格式: "20260330")
        adjust: 复权方式 ("hfq" 后复权, "qfq" 前复权, None 不复权)
    """
    print(f"\n{'='*60}")
    print(f"测试股票: {stock_code}")
    print(f"日期范围: {start_date} 至 {end_date}")
    print(f"复权方式: {adjust if adjust else '不复权'}")
    print(f"{'='*60}")
    
    try:
        df = ak.stock_zh_a_hist(
            symbol=stock_code,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust=adjust if adjust else "qfq"
        )
        
        print(f"✓ 数据获取成功!")
        print(f"数据行数: {len(df)}")
        print(f"列名: {df.columns.tolist()}")
        
        if not df.empty:
            print(f"\n前5行数据预览:")
            print(df.head())
            
            print(f"\n后5行数据预览:")
            print(df.tail())
            
            # 检查价格字段是否有负值
            price_cols = ['开盘', '收盘', '最高', '最低']
            has_negative = False
            for col in price_cols:
                if col in df.columns:
                    negative_count = (df[col] < 0).sum()
                    if negative_count > 0:
                        print(f"\n⚠️  警告: {col} 列有 {negative_count} 个负值")
                        has_negative = True
            
            if not has_negative:
                print(f"\n✓ 所有价格字段均为非负值")
        
        return True
        
    except Exception as e:
        print(f"✗ 数据获取失败!")
        print(f"错误类型: {type(e).__name__}")
        print(f"错误信息: {str(e)}")
        return False


def main():
    """测试用例"""
    print("AKShare 数据获取手动测试")
    print("本脚本仅测试数据获取,不写入数据库")
    
    # 测试用例列表
    test_cases = [
        # 基础测试
        {
            "name": "基础测试 - 茅台",
            "params": {
                "stock_code": "600519",
                "start_date": "20200101",
                "end_date": "20201231",
                "adjust": "hfq"
            }
        },
        # 问题股票测试
        {
            "name": "问题股票 - 600734 (已知有负值)",
            "params": {
                "stock_code": "600734",
                "start_date": "20050501",
                "end_date": "20050520",
                "adjust": "hfq"
            }
        },
        # 不同复权方式测试
        {
            "name": "复权方式对比 - 前复权",
            "params": {
                "stock_code": "600000",
                "start_date": "20200101",
                "end_date": "20201231",
                "adjust": "qfq"
            }
        },
        {
            "name": "复权方式对比 - 不复权",
            "params": {
                "stock_code": "600000",
                "start_date": "20200101",
                "end_date": "20201231",
                "adjust": None
            }
        },
        # 大日期范围测试
        {
            "name": "大日期范围 - 10年数据",
            "params": {
                "stock_code": "000001",
                "start_date": "20150101",
                "end_date": "20251231",
                "adjust": "hfq"
            }
        },
        # 最近数据测试
        {
            "name": "最近数据 - 1个月",
            "params": {
                "stock_code": "600519",
                "start_date": "20260301",
                "end_date": "20260330",
                "adjust": "hfq"
            }
        },
        # 深市股票测试
        {
            "name": "深市股票 - 平安银行",
            "params": {
                "stock_code": "000001",
                "start_date": "20200101",
                "end_date": "20201231",
                "adjust": "hfq"
            }
        },
        # 创业板股票测试
        {
            "name": "创业板股票 - 宁德时代",
            "params": {
                "stock_code": "300750",
                "start_date": "20200101",
                "end_date": "20201231",
                "adjust": "hfq"
            }
        },
    ]
    
    print(f"\n共有 {len(test_cases)} 个测试用例")
    print("请逐个运行测试,观察结果")
    
    # 运行所有测试
    results = []
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n\n{'#'*80}")
        print(f"测试 {i}/{len(test_cases)}: {test_case['name']}")
        print(f"{'#'*80}")
        
        success = test_stock_data_fetch(**test_case['params'])
        results.append({
            "name": test_case['name'],
            "success": success
        })
    
    # 汇总结果
    print(f"\n\n{'='*80}")
    print("测试结果汇总")
    print(f"{'='*80}")
    
    for result in results:
        status = "✓ 通过" if result['success'] else "✗ 失败"
        print(f"{status} - {result['name']}")
    
    passed = sum(1 for r in results if r['success'])
    total = len(results)
    print(f"\n总计: {passed}/{total} 通过")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
