<template>
  <div id="app">
    <el-container>
      <el-header>
        <div class="header-content">
          <div class="header-title">
            <h1>DataDrivenTrader</h1>
            <p class="subtitle">数据驱动的量化回测系统</p>
          </div>
          <div class="header-info">
            <span class="data-time" v-if="databaseInfo.latest_date">
              数据更新至: {{ databaseInfo.latest_date }}
              <el-tag size="small" type="success">{{ databaseInfo.stock_count }}只股票</el-tag>
            </span>
            <el-button 
              v-if="!isDownloading" 
              type="primary" 
              size="small" 
              @click="showDownloadDialog"
            >
              全量更新数据
            </el-button>
            <el-button 
              v-else 
              type="info" 
              size="small" 
              disabled
            >
              正在更新...
            </el-button>
          </div>
        </div>
      </el-header>
      
      <el-main>
        <!-- 批量下载进度对话框 -->
        <el-dialog 
          v-model="downloadDialogVisible" 
          title="批量下载进度" 
          width="500px" 
          :close-on-click-modal="false"
          :destroy-on-close="true"
        >
          <div class="download-progress">
            <div class="progress-info">
              <span>状态: {{ downloadStatus.message || '准备中...' }}</span>
              <span>进度: {{ downloadProgress }}%</span>
            </div>
            <el-progress 
              :percentage="downloadProgress" 
              :status="downloadStatusMessage === 'completed' ? 'success' : (downloadStatusMessage === 'error' ? 'exception' : null)"
            />
            <div class="download-stats" v-if="downloadStatus.total > 0">
              <span>已完成: {{ downloadStatus.current }} / {{ downloadStatus.total }}</span>
            </div>
          </div>
          <template #footer>
            <el-button 
              v-if="isDownloading" 
              type="danger" 
              @click="stopDownload"
            >
              停止下载
            </el-button>
            <el-button 
              v-else 
              @click="downloadDialogVisible = false"
            >
              关闭
            </el-button>
          </template>
        </el-dialog>
        
        <el-card class="control-panel">
          <el-form :inline="true" :model="form">
            <el-form-item label="股票代码">
              <el-input v-model="form.stockCode" placeholder="如: 600519" />
            </el-form-item>
            <el-form-item label="开始日期">
              <el-date-picker v-model="form.startDate" type="date" placeholder="选择日期" />
            </el-form-item>
            <el-form-item label="结束日期">
              <el-date-picker v-model="form.endDate" type="date" placeholder="选择日期" />
            </el-form-item>
            <el-form-item label="策略">
              <el-select v-model="form.strategyName" placeholder="选择策略">
                <el-option label="MA交叉策略" value="MA_Cross" />
                <el-option label="能量衰减策略" value="Energy_Decay" />
              </el-select>
            </el-form-item>
            <el-form-item label="均线周期">
              <el-input-number v-model="form.maPeriod" :min="2" :max="60" />
            </el-form-item>
            <el-form-item label="初始资金">
              <el-input-number v-model="form.initialCapital" :min="10000" :step="10000" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="fetchData" :loading="fetching" :disabled="isDownloading">获取数据</el-button>
              <el-button type="success" @click="runBacktest" :loading="running" :disabled="!hasData || isDownloading">
                运行回测
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
        
        <!-- 数据加载遮罩层 -->
        <div v-if="isDownloading" class="loading-overlay">
          <div class="loading-content">
            <el-spin size="large" tip="正在下载数据，请稍候..." />
          </div>
        </div>

        <el-card v-if="fetchResult" class="result-card">
          <template #header>
            <span>数据获取结果</span>
          </template>
          <el-alert 
            :title="fetchResult.message" 
            :type="fetchResult.success ? 'success' : 'error'" 
            show-icon 
          />
        </el-card>

        <el-card v-if="backtestResult" class="result-card">
          <template #header>
            <span>回测结果 - {{ backtestResult.result.strategy_name }}</span>
          </template>
          
          <el-row :gutter="20">
            <el-col :span="6">
              <el-statistic title="总收益率" :value="backtestResult.result.total_return" suffix="%" :precision="2">
                <template #prefix>
                  <span :style="{ color: backtestResult.result.total_return >= 0 ? '#67C23A' : '#F56C6C' }">
                    {{ backtestResult.result.total_return >= 0 ? '↑' : '↓' }}
                  </span>
                </template>
              </el-statistic>
            </el-col>
            <el-col :span="6">
              <el-statistic title="年化收益率" :value="backtestResult.result.annual_return" suffix="%" :precision="2" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="最大回撤" :value="backtestResult.result.max_drawdown" suffix="%" :precision="2">
                <template #prefix>
                  <span style="color: #F56C6C">↓</span>
                </template>
              </el-statistic>
            </el-col>
            <el-col :span="6">
              <el-statistic title="胜率" :value="backtestResult.result.win_rate" suffix="%" :precision="2" />
            </el-col>
          </el-row>

          <el-divider />

          <el-row :gutter="20">
            <el-col :span="6">
              <el-statistic title="初始资金" :value="backtestResult.result.initial_capital" prefix="¥" :precision="2" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="最终资金" :value="backtestResult.result.final_capital" prefix="¥" :precision="2" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="总交易次数" :value="backtestResult.result.total_trades" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="盈利/亏损次数" :value="`${backtestResult.result.profit_trades}/${backtestResult.result.loss_trades}`" />
            </el-col>
          </el-row>
        </el-card>

        <el-card v-if="backtestResult && backtestResult.kline_data.length > 0" class="kline-card">
          <template #header>
            <div class="kline-header">
              <span>K线图</span>
              <div class="kline-legend">
                <span class="legend-item"><span class="legend-color" style="background: #ef5350;"></span> 阴线(跌)</span>
                <span class="legend-item"><span class="legend-color" style="background: #26a69a;"></span> 阳线(涨)</span>
                <span class="legend-item"><span class="legend-marker buy">B</span> 买入点</span>
                <span class="legend-item"><span class="legend-marker sell">S</span> 卖出点</span>
              </div>
            </div>
          </template>
          <div ref="klineChart" class="kline-container"></div>
        </el-card>

        <el-card v-if="backtestResult" class="chart-card">
          <template #header>
            <span>资金曲线</span>
          </template>
          <div ref="equityChart" class="chart-container"></div>
        </el-card>

        <el-card v-if="backtestResult && backtestResult.result.trades.length > 0" class="trades-card">
          <template #header>
            <span>交易记录</span>
          </template>
          <el-table :data="backtestResult.result.trades" stripe max-height="400">
            <el-table-column prop="trade_type" label="类型" width="80">
              <template #default="scope">
                <el-tag :type="scope.row.trade_type === 'buy' ? 'success' : 'danger'">
                  {{ scope.row.trade_type === 'buy' ? '买入' : '卖出' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="trade_date" label="日期" width="120" />
            <el-table-column prop="price" label="价格" width="100">
              <template #default="scope">
                ¥{{ scope.row.price.toFixed(2) }}
              </template>
            </el-table-column>
            <el-table-column prop="shares" label="股数" width="100" />
            <el-table-column prop="amount" label="金额">
              <template #default="scope">
                ¥{{ scope.row.amount.toFixed(2) }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <el-card v-if="backtestResult && backtestResult.signals_info" class="signals-card">
          <template #header>
            <span>信号信息</span>
          </template>
          
          <el-descriptions :column="1" border v-if="backtestResult.signals_info.signal_days.length > 0">
            <template #header>
              <el-tag type="success" size="small">买入信号日 ({{ backtestResult.signals_info.signal_days.length }})</el-tag>
            </template>
            <el-descriptions-item label="信号详情">
              <el-table :data="backtestResult.signals_info.signal_days" size="small" max-height="200">
                <el-table-column prop="date" label="日期" width="120" />
                <el-table-column prop="price" label="价格" width="100">
                  <template #default="scope">¥{{ scope.row.price.toFixed(2) }}</template>
                </el-table-column>
              </el-table>
            </el-descriptions-item>
          </el-descriptions>
          
          <el-descriptions :column="1" border v-if="backtestResult.signals_info.breakout_days.length > 0">
            <template #header>
              <el-tag type="warning" size="small">突破日 ({{ backtestResult.signals_info.breakout_days.length }})</el-tag>
            </template>
            <el-descriptions-item label="突破详情">
              <el-table :data="backtestResult.signals_info.breakout_days" size="small" max-height="150">
                <el-table-column prop="date" label="日期" width="120" />
                <el-table-column prop="price" label="价格" width="100">
                  <template #default="scope">¥{{ scope.row.price.toFixed(2) }}</template>
                </el-table-column>
              </el-table>
            </el-descriptions-item>
          </el-descriptions>
          
          <el-descriptions :column="1" border v-if="backtestResult.signals_info.decay_reached_days.length > 0">
            <template #header>
              <el-tag type="info" size="small">衰减达标日 ({{ backtestResult.signals_info.decay_reached_days.length }})</el-tag>
            </template>
            <el-descriptions-item label="衰减详情">
              <el-table :data="backtestResult.signals_info.decay_reached_days" size="small" max-height="150">
                <el-table-column prop="date" label="日期" width="120" />
                <el-table-column prop="price" label="价格" width="100">
                  <template #default="scope">¥{{ scope.row.price.toFixed(2) }}</template>
                </el-table-column>
                <el-table-column prop="decay_rate" label="衰减率" width="100">
                  <template #default="scope">{{ (scope.row.decay_rate * 100).toFixed(2) }}%</template>
                </el-table-column>
              </el-table>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>

        <el-card class="history-card">
          <template #header>
            <span>历史回测记录</span>
          </template>
          <el-table :data="historyResults" stripe @row-click="showDetail">
            <el-table-column prop="stock_code" label="股票代码" width="100" />
            <el-table-column prop="strategy_name" label="策略" width="120" />
            <el-table-column prop="start_date" label="开始日期" width="120" />
            <el-table-column prop="end_date" label="结束日期" width="120" />
            <el-table-column prop="total_return" label="总收益率" width="100">
              <template #default="scope">
                <span :style="{ color: scope.row.total_return >= 0 ? '#67C23A' : '#F56C6C' }">
                  {{ scope.row.total_return.toFixed(2) }}%
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="win_rate" label="胜率" width="80">
              <template #default="scope">
                {{ scope.row.win_rate ? scope.row.win_rate.toFixed(2) + '%' : '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" />
          </el-table>
        </el-card>
      </el-main>
    </el-container>
  </div>
</template>

<script>
import { ref, computed, onMounted, nextTick } from 'vue'
import axios from 'axios'
import * as echarts from 'echarts'

export default {
  name: 'App',
  setup() {
    const form = ref({
      stockCode: '600519',
      startDate: new Date('2020-01-01'),
      endDate: new Date(),
      strategyName: 'MA_Cross',
      maPeriod: 5,
      initialCapital: 500000
    })

    const fetching = ref(false)
    const running = ref(false)
    const hasData = ref(false)
    const fetchResult = ref(null)
    const backtestResult = ref(null)
    const historyResults = ref([])
    const equityChart = ref(null)
    const klineChart = ref(null)
    const databaseInfo = ref({
      latest_date: null,
      stock_count: 0,
      min_date: null
    })
    const isDownloading = ref(false)
    const downloadDialogVisible = ref(false)
    const downloadStatus = ref({})
    let equityChartInstance = null
    let klineChartInstance = null

    const formatDate = (date) => {
      if (!date) return null
      const d = new Date(date)
      return d.toISOString().split('T')[0]
    }

    const fetchData = async () => {
      fetching.value = true
      fetchResult.value = null
      
      try {
        const response = await axios.post('/api/data/fetch', null, {
          params: {
            stock_code: form.value.stockCode,
            start_date: formatDate(form.value.startDate),
            end_date: formatDate(form.value.endDate)
          }
        })
        
        fetchResult.value = response.data
        if (response.data.success) {
          hasData.value = true
        }
      } catch (error) {
        fetchResult.value = {
          success: false,
          message: error.response?.data?.detail || '获取数据失败'
        }
      } finally {
        fetching.value = false
      }
    }

    const runBacktest = async () => {
      running.value = true
      
      try {
        const response = await axios.post('/api/backtest/run', {
          stock_code: form.value.stockCode,
          start_date: formatDate(form.value.startDate),
          end_date: formatDate(form.value.endDate),
          initial_capital: form.value.initialCapital,
          ma_period: form.value.maPeriod,
          strategy_name: form.value.strategyName || 'MA_Cross'
        })
        
        backtestResult.value = response.data
        await nextTick()
        renderEquityChart()
        renderKlineChart()
        loadHistory()
      } catch (error) {
        console.error('Backtest error:', error)
      } finally {
        running.value = false
      }
    }

    const renderEquityChart = () => {
      if (!equityChart.value || !backtestResult.value) return

      if (equityChartInstance) {
        equityChartInstance.dispose()
      }

      equityChartInstance = echarts.init(equityChart.value)

      const dates = backtestResult.value.equity_curve.map(e => e.date)
      const equities = backtestResult.value.equity_curve.map(e => e.equity)
      const benchmarks = backtestResult.value.equity_curve.map(e => e.benchmark)

      const option = {
        tooltip: {
          trigger: 'axis'
        },
        legend: {
          data: ['策略资金', '基准资金']
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '3%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          data: dates,
          axisLabel: {
            rotate: 45
          }
        },
        yAxis: {
          type: 'value',
          axisLabel: {
            formatter: '¥{value}'
          }
        },
        series: [
          {
            name: '策略资金',
            type: 'line',
            data: equities,
            smooth: true,
            lineStyle: {
              width: 2
            },
            areaStyle: {
              opacity: 0.1
            }
          },
          {
            name: '基准资金',
            type: 'line',
            data: benchmarks,
            smooth: true,
            lineStyle: {
              width: 2,
              type: 'dashed'
            }
          }
        ]
      }

      equityChartInstance.setOption(option)
    }

    const renderKlineChart = () => {
      if (!klineChart.value || !backtestResult.value) return

      if (klineChartInstance) {
        klineChartInstance.dispose()
      }

      klineChartInstance = echarts.init(klineChart.value)

      const klineData = backtestResult.value.kline_data
      const trades = backtestResult.value.result.trades

      const dates = klineData.map(k => {
        const d = new Date(k.date)
        return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
      })

      const ohlc = klineData.map(k => [k.open, k.close, k.low, k.high])
      const volumes = klineData.map(k => k.volume)

      const tradeDateSet = new Set()
      const buyPoints = {}
      const sellPoints = {}
      
      trades.forEach(t => {
        const dateStr = t.trade_date
        tradeDateSet.add(dateStr)
        if (t.trade_type === 'buy') {
          buyPoints[dateStr] = t.price
        } else {
          sellPoints[dateStr] = t.price
        }
      })

      const maData = []
      const period = form.value.maPeriod
      for (let i = 0; i < klineData.length; i++) {
        if (i < period - 1) {
          maData.push('-')
        } else {
          let sum = 0
          for (let j = 0; j < period; j++) {
            sum += klineData[i - j].close
          }
          maData.push((sum / period).toFixed(2))
        }
      }

      const markPoints = []
      dates.forEach((date, idx) => {
        if (buyPoints[date]) {
          markPoints.push({
            name: 'B',
            coord: [date, klineData[idx].low],
            value: 'B',
            itemStyle: { color: '#f44336' },
            symbol: 'circle',
            symbolSize: 1
          })
        }
        if (sellPoints[date]) {
          markPoints.push({
            name: 'S',
            coord: [date, klineData[idx].high],
            value: 'S',
            itemStyle: { color: '#2196f3' },
            symbol: 'circle',
            symbolSize: 1
          })
        }
      })

      const option = {
        animation: false,
        legend: {
          data: ['K线', `MA${period}`, '成交量'],
          top: 10
        },
        tooltip: {
          trigger: 'axis',
          axisPointer: {
            type: 'cross'
          },
          backgroundColor: 'rgba(245, 245, 245, 0.95)',
          borderWidth: 1,
          borderColor: '#ccc',
          padding: 10,
          textStyle: {
            color: '#000'
          },
          formatter: function(params) {
            let result = params[0].axisValue + '<br/>'
            params.forEach(param => {
              if (param.seriesName === 'K线') {
                const data = param.data
                result += `开盘: ${data[1]}<br/>`
                result += `收盘: ${data[2]}<br/>`
                result += `最低: ${data[3]}<br/>`
                result += `最高: ${data[4]}<br/>`
              } else if (param.seriesName === '成交量') {
                result += `成交量: ${(param.data / 10000).toFixed(2)}万<br/>`
              } else {
                result += `${param.seriesName}: ${param.data}<br/>`
              }
            })
            return result
          }
        },
        axisPointer: {
          link: [{ xAxisIndex: 'all' }],
          label: {
            backgroundColor: '#777'
          }
        },
        dataZoom: [
          {
            type: 'inside',
            xAxisIndex: [0, 1],
            start: 0,
            end: 100
          },
          {
            show: true,
            xAxisIndex: [0, 1],
            type: 'slider',
            bottom: 10,
            start: 0,
            end: 100
          }
        ],
        xAxis: [
          {
            type: 'category',
            data: dates,
            boundaryGap: false,
            axisLine: { onZero: false },
            splitLine: { show: false },
            axisLabel: {
              rotate: 45
            },
            min: 'dataMin',
            max: 'dataMax'
          },
          {
            type: 'category',
            gridIndex: 1,
            data: dates,
            boundaryGap: false,
            axisLine: { onZero: false },
            axisTick: { show: false },
            splitLine: { show: false },
            axisLabel: { show: false },
            min: 'dataMin',
            max: 'dataMax'
          }
        ],
        yAxis: [
          {
            scale: true,
            splitArea: {
              show: true
            }
          },
          {
            scale: true,
            gridIndex: 1,
            splitNumber: 2,
            axisLabel: {
              formatter: function(value) {
                return (value / 10000).toFixed(0) + '万'
              }
            },
            axisLine: { show: false },
            axisTick: { show: false },
            splitLine: { show: false }
          }
        ],
        grid: [
          {
            left: '10%',
            right: '8%',
            height: '55%'
          },
          {
            left: '10%',
            right: '8%',
            top: '70%',
            height: '15%'
          }
        ],
        series: [
          {
            name: 'K线',
            type: 'candlestick',
            data: ohlc,
            itemStyle: {
              color: '#26a69a',
              color0: '#ef5350',
              borderColor: '#26a69a',
              borderColor0: '#ef5350'
            },
            markPoint: {
              symbol: 'circle',
              symbolSize: 0,
              data: markPoints,
              label: {
                show: true,
                formatter: function(param) {
                  return param.value
                },
                fontSize: 14,
                fontWeight: 'bold',
                color: param => param.name === 'B' ? '#f44336' : '#2196f3'
              }
            }
          },
          {
            name: `MA${period}`,
            type: 'line',
            data: maData,
            smooth: true,
            lineStyle: {
              width: 1,
              opacity: 0.8
            },
            symbol: 'none'
          },
          {
            name: '成交量',
            type: 'bar',
            xAxisIndex: 1,
            yAxisIndex: 1,
            data: volumes,
            itemStyle: {
              color: function(params) {
                const idx = params.dataIndex
                if (idx === 0) return '#26a69a'
                return klineData[idx].close >= klineData[idx].open ? '#26a69a' : '#ef5350'
              }
            }
          }
        ]
      }

      klineChartInstance.setOption(option)
    }

    const loadHistory = async () => {
      try {
        const response = await axios.get('/api/backtest/results', {
          params: {
            stock_code: form.value.stockCode
          }
        })
        historyResults.value = response.data
      } catch (error) {
        console.error('Load history error:', error)
      }
    }

    const showDetail = async (row) => {
      try {
        const response = await axios.get(`/api/backtest/${row.id}`)
        backtestResult.value = response.data
        await nextTick()
        renderEquityChart()
        renderKlineChart()
      } catch (error) {
        console.error('Load detail error:', error)
      }
    }

    onMounted(() => {
      loadDatabaseInfo()
      loadHistory()
      
      window.addEventListener('resize', () => {
        if (equityChartInstance) {
          equityChartInstance.resize()
        }
        if (klineChartInstance) {
          klineChartInstance.resize()
        }
      })
    })

    const loadDatabaseInfo = async () => {
      try {
        const response = await axios.get('/api/database/info')
        databaseInfo.value = response.data
        if (response.data.latest_date) {
          hasData.value = true
        }
      } catch (error) {
        console.error('Load database info error:', error)
      }
    }

    const showDownloadDialog = async () => {
      downloadDialogVisible.value = true
      await startBulkDownload()
      checkDownloadStatus()
    }

    const startBulkDownload = async () => {
      try {
        const response = await axios.post('/api/bulk-download/start', {
          task_id: 'bulk_download_' + Date.now()
        })
        downloadStatus.value = response.data.download_status || {}
        isDownloading.value = response.data.is_downloading
      } catch (error) {
        console.error('Start download error:', error)
        downloadStatus.value = { message: '启动失败: ' + (error.response?.data?.detail || '未知错误') }
      }
    }

    const checkDownloadStatus = async () => {
      try {
        const response = await axios.get('/api/bulk-download/status')
        const data = response.data
        
        if (data.download_status) {
          downloadStatus.value = data.download_status
        }
        
        isDownloading.value = data.is_downloading
        
        if (data.is_downloading) {
          setTimeout(checkDownloadStatus, 3000)
        }
      } catch (error) {
        console.error('Check status error:', error)
      }
    }

    const stopDownload = async () => {
      try {
        // 这里可以添加停止下载的API调用
        // 暂时只更新状态
        isDownloading.value = false
        downloadDialogVisible.value = false
        downloadStatus.value = { message: '已停止下载' }
      } catch (error) {
        console.error('Stop download error:', error)
      }
    }

    const downloadProgress = computed(() => {
      return downloadStatus.value.progress || 0
    })

    const downloadStatusMessage = computed(() => {
      return downloadStatus.value.status || 'pending'
    })

    return {
      form,
      fetching,
      running,
      hasData,
      fetchResult,
      backtestResult,
      historyResults,
      databaseInfo,
      isDownloading,
      downloadDialogVisible,
      downloadStatus,
      downloadProgress,
      downloadStatusMessage,
      equityChart,
      klineChart,
      fetchData,
      runBacktest,
      showDetail,
      showDownloadDialog,
      stopDownload
    }
  }
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

#app {
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', Arial, sans-serif;
  background-color: #f5f7fa;
  min-height: 100vh;
}

.el-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px;
  text-align: center;
}

.el-header h1 {
  font-size: 28px;
  margin-bottom: 5px;
}

.el-header .subtitle {
  font-size: 14px;
  opacity: 0.8;
}

.el-main {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.control-panel {
  margin-bottom: 20px;
}

.result-card {
  margin-bottom: 20px;
}

.kline-card {
  margin-bottom: 20px;
}

.kline-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.kline-legend {
  display: flex;
  gap: 15px;
  font-size: 12px;
  font-weight: normal;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.legend-color {
  width: 12px;
  height: 12px;
  border-radius: 2px;
}

.legend-marker {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: bold;
  color: white;
}

.legend-marker.buy {
  background: #f44336;
}

.legend-marker.sell {
  background: #2196f3;
}

.kline-container {
  width: 100%;
  height: 500px;
}

.chart-card {
  margin-bottom: 20px;
}

.chart-container {
  width: 100%;
  height: 400px;
}

.trades-card {
  margin-bottom: 20px;
}

.signals-card {
  margin-bottom: 20px;
}

.history-card {
  margin-bottom: 20px;
}

.el-table {
  cursor: pointer;
}

.el-statistic {
  text-align: center;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 8px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-title {
  text-align: left;
  flex: 1;
}

.header-info {
  display: flex;
  align-items: center;
  gap: 15px;
}

.data-time {
  font-size: 14px;
  color: #fff;
  display: flex;
  align-items: center;
  gap: 10px;
}

.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 1000;
  display: flex;
  justify-content: center;
  align-items: center;
}

.loading-content {
  background: white;
  padding: 40px;
  border-radius: 10px;
  text-align: center;
}

.download-progress {
  padding: 20px 0;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  margin-bottom: 15px;
  font-size: 14px;
}

.download-stats {
  margin-top: 10px;
  text-align: center;
  font-size: 14px;
  color: #606266;
}
</style>
