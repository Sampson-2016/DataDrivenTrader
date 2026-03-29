# DataDrivenTrader

数据驱动的量化回测系统 - 基于价格行为的A股策略研究平台

## 项目简介

DataDrivenTrader 是一个面向日线级别的股票回测系统，以纯价格行为为核心的策略研究方式。系统支持通过均线交叉等策略进行回测，并提供直观的K线图和资金曲线展示。

### 核心功能

- **数据获取**: 通过 AkShare 获取A股历史行情数据
- **策略回测**: 支持均线交叉策略（收盘价上穿均线买入，跌破均线卖出）
- **K线展示**: 专业K线图展示，支持缩放、拖拽，标记买卖点（B/S）
- **收益分析**: 资金曲线、收益率、最大回撤、胜率等指标展示
- **历史记录**: 保存回测结果，方便对比分析

## 技术栈

### 后端
- Python 3.12+
- FastAPI - 高性能Web框架
- SQLAlchemy - ORM框架
- MySQL - 数据存储
- AkShare - A股数据获取
- Pandas - 数据处理

### 前端
- Vue 3 - 渐进式JavaScript框架
- Element Plus - UI组件库
- ECharts - 图表可视化
- Axios - HTTP请求
- Vite - 构建工具

## 项目结构

```
DataDrivenTrader/
├── backend/                    # 后端代码
│   ├── app/
│   │   ├── api.py             # API路由
│   │   ├── backtest_engine.py # 回测引擎
│   │   ├── data_fetcher.py    # 数据获取
│   │   ├── database.py        # 数据库连接
│   │   ├── models.py          # 数据模型
│   │   ├── schemas.py         # 数据模式
│   │   └── main.py            # 应用入口
│   ├── requirements.txt       # Python依赖
│   └── .env                   # 环境配置
├── frontend/                   # 前端代码
│   ├── src/
│   │   └── App.vue            # 主组件
│   ├── package.json           # Node依赖
│   └── vite.config.js         # Vite配置
└── README.md
```

## 快速开始

### 环境要求

- Python 3.12+
- Node.js 16+
- MySQL 8.0+

### 1. 数据库配置

创建数据库：

```sql
CREATE DATABASE stock_backtesting CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

配置后端环境变量（`backend/.env`）：

```
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=stock_backtesting
```

### 2. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

### 3. 安装前端依赖

```bash
cd frontend
npm install
```

### 4. 启动服务

**启动后端（终端1）：**

```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```

**启动前端（终端2）：**

```bash
cd frontend
npm run dev
```

### 5. 访问系统

打开浏览器访问：http://localhost:3000

## 使用说明

### 回测流程

1. **获取数据**: 输入股票代码（如 600519 茅台），选择日期范围，点击"获取数据"
2. **设置参数**: 配置均线周期（默认5日）、初始资金（默认50万）
3. **运行回测**: 点击"运行回测"按钮
4. **查看结果**: 
   - 回测指标：总收益率、年化收益、最大回撤、胜率等
   - K线图：展示价格走势、均线、买卖点标记
   - 资金曲线：策略资金与基准资金对比
   - 交易记录：详细买卖记录

### 策略说明

**均线交叉策略**：
- 买入信号：收盘价上穿N日均线
- 卖出信号：收盘价跌破N日均线
- 仓位管理：每次买入最大可买股数（100股整数倍）
- 交易成本：佣金万三（最低5元）+ 印花税千一（卖出）

### K线图操作

- **缩放**: 鼠标滚轮或底部滑块
- **平移**: 拖拽图表
- **详情**: 鼠标悬停显示开高低收、成交量
- **买卖点**: 红色B标记买入，蓝色S标记卖出

## 注意事项

1. **数据获取**: 首次使用需要先点击"获取数据"，AkShare从网络获取数据可能需要几秒钟
2. **资金设置**: 高股价股票（如茅台）建议设置较大初始资金（50万以上），否则可能无法买入
3. **交易一致性**: 相同策略不同资金的交易日期一致，收益率差异来自手续费比例不同
4. **数据库**: 确保MySQL服务已启动，数据库已创建
5. **端口占用**: 后端默认8001端口，前端默认3000端口，如有冲突请修改配置

## API接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/data/fetch` | POST | 获取股票数据 |
| `/api/backtest/run` | POST | 运行回测 |
| `/api/backtest/results` | GET | 获取历史回测记录 |
| `/api/backtest/{id}` | GET | 获取回测详情 |

## 开发计划

- [ ] 支持更多策略（MACD、RSI等）
- [ ] 添加股票池管理
- [ ] 支持多股票组合回测
- [ ] 添加风险指标（夏普比率、索提诺比率）
- [ ] 支持策略参数优化

## License

MIT License
