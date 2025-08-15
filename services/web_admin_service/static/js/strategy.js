/**
 * ARBIG策略管理前端JavaScript
 * 负责策略列表、参数编辑、回测等功能
 */

class StrategyManager {
    constructor() {
        this.strategies = {};
        this.activeStrategy = null;
        this.strategyStatus = 'STOPPED';
        this.selectedStrategy = null;  // 当前选中的策略

        this.init();
    }

    async init() {
        console.log('初始化策略管理器...');
        
        // 绑定事件
        this.bindEvents();
        
        // 加载策略数据
        await this.loadStrategies();
        
        // 定时更新状态
        this.startStatusUpdater();
        
        console.log('策略管理器初始化完成');
    }

    bindEvents() {
        // 刷新按钮
        document.getElementById('refresh-btn')?.addEventListener('click', () => {
            this.loadStrategies();
        });

        // 回测按钮
        document.getElementById('run-backtest-btn')?.addEventListener('click', () => {
            this.runBacktest();
        });

        // 其他事件绑定可以在这里添加
    }

    async loadStrategies() {
        try {
            console.log('加载策略列表...');

            const response = await fetch('/api/v1/trading/strategies');
            console.log('API响应状态:', response.status);

            const result = await response.json();
            console.log('API返回数据:', result);
            
            if (result.success) {
                this.strategies = result.data.strategies;
                this.activeStrategy = result.data.active_strategy;
                this.strategyStatus = result.data.status;
                
                this.updateStrategyOverview();
                this.renderStrategyList();
                
                console.log('策略列表加载成功:', Object.keys(this.strategies).length, '个策略');
            } else {
                throw new Error('获取策略列表失败');
            }
        } catch (error) {
            console.error('加载策略失败:', error);
            this.showNotification('加载策略失败: ' + error.message, 'error');
        }
    }

    updateStrategyOverview() {
        // 更新策略状态概览
        const activeStrategyEl = document.getElementById('active-strategy');
        const strategyStatusIndicator = document.getElementById('strategy-status-indicator');
        const strategyCountEl = document.getElementById('strategy-count');

        if (activeStrategyEl) {
            activeStrategyEl.textContent = this.activeStrategy || '无活跃策略';
        }

        if (strategyStatusIndicator) {
            if (this.strategyStatus === 'RUNNING') {
                strategyStatusIndicator.textContent = '▶️';
                strategyStatusIndicator.className = 'status-indicator online';
            } else {
                strategyStatusIndicator.textContent = '⏸️';
                strategyStatusIndicator.className = 'status-indicator offline';
            }
        }

        if (strategyCountEl) {
            strategyCountEl.textContent = Object.keys(this.strategies).length;
        }
    }

    renderStrategyList() {
        console.log('渲染策略列表...');
        const listContainer = document.getElementById('strategy-list');
        if (!listContainer) {
            console.error('找不到strategy-list元素');
            return;
        }

        console.log('策略数据:', this.strategies);
        listContainer.innerHTML = '';

        Object.entries(this.strategies).forEach(([strategyName, strategy]) => {
            console.log('创建策略项目:', strategyName, strategy);
            const strategyItem = this.createStrategyItem(strategyName, strategy);
            listContainer.appendChild(strategyItem);
        });

        // 如果没有选中的策略，默认选中第一个
        if (!this.selectedStrategy && Object.keys(this.strategies).length > 0) {
            const firstStrategy = Object.keys(this.strategies)[0];
            console.log('默认选中策略:', firstStrategy);
            this.selectStrategy(firstStrategy);
        }
    }

    createStrategyItem(strategyName, strategy) {
        const item = document.createElement('div');
        item.className = `strategy-item ${this.selectedStrategy === strategyName ? 'selected' : ''}`;

        const isRunning = this.activeStrategy === strategyName && this.strategyStatus === 'RUNNING';

        item.innerHTML = `
            <div class="strategy-item-header">
                <div class="strategy-info">
                    <h4>${strategy.name}</h4>
                    <p>${strategy.description}</p>
                </div>
                <div class="strategy-status">
                    ${isRunning ?
                        '<span class="status-indicator online">运行中</span>' :
                        '<span class="status-indicator offline">已停止</span>'
                    }
                </div>
            </div>
        `;

        item.addEventListener('click', () => {
            this.selectStrategy(strategyName);
        });

        return item;
    }

    selectStrategy(strategyName) {
        this.selectedStrategy = strategyName;

        // 更新选中状态
        document.querySelectorAll('.strategy-item').forEach(item => {
            item.classList.remove('selected');
        });

        // 找到对应的策略项目并添加选中状态
        document.querySelectorAll('.strategy-item').forEach(item => {
            if (item.textContent.includes(this.strategies[strategyName]?.name)) {
                item.classList.add('selected');
            }
        });

        // 显示策略配置
        this.renderStrategyConfig(strategyName);
    }

    renderStrategyConfig(strategyName) {
        const configContainer = document.getElementById('strategy-config');
        if (!configContainer) return;

        const strategy = this.strategies[strategyName];
        if (!strategy) return;

        const isRunning = this.activeStrategy === strategyName && this.strategyStatus === 'RUNNING';

        configContainer.innerHTML = `
            <div class="strategy-config-content">
                <div class="config-header">
                    <h3>${strategy.name}</h3>
                    <div class="config-actions">
                        ${isRunning ?
                            `<button class="btn btn-danger" onclick="strategyManager.stopStrategy('${strategyName}')">
                                ⏹️ 停止策略
                            </button>` :
                            `<button class="btn btn-success" onclick="strategyManager.startStrategy('${strategyName}')"
                                ${this.strategyStatus === 'RUNNING' ? 'disabled' : ''}>
                                ▶️ 启动策略
                            </button>`
                        }
                    </div>
                </div>

                <div class="config-body">
                    <h4>策略参数</h4>
                    <form id="strategy-params-form" onsubmit="strategyManager.saveStrategyParams(event, '${strategyName}')">
                        ${this.renderParamsForm(strategy.params)}
                        <div class="form-actions">
                            <button type="submit" class="btn btn-primary">💾 保存参数</button>
                            <button type="button" class="btn btn-outline" onclick="strategyManager.resetParams('${strategyName}')">
                                🔄 重置参数
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        `;
    }

    renderParamsPreview(params) {
        const mainParams = ['ma_short', 'ma_long', 'initial_capital', 'stop_loss'];
        let html = '';

        mainParams.forEach(param => {
            if (params[param] !== undefined) {
                html += `
                    <div class="param-item" style="display: flex; justify-content: space-between; padding: 4px 0;">
                        <span style="color: var(--text-secondary); font-size: 0.9rem;">${this.getParamLabel(param)}</span>
                        <span style="color: var(--text-primary); font-weight: 500;">${params[param]}</span>
                    </div>
                `;
            }
        });

        return html;
    }

    getParamLabel(param) {
        const labels = {
            'ma_short': '短期均线周期',
            'ma_long': '长期均线周期',
            'signal_interval': '信号间隔(秒)',
            'trade_volume': '交易手数',
            'max_position': '最大持仓',
            'stop_loss': '止损比例',
            'take_profit': '止盈比例',
            'rsi_period': 'RSI周期',
            'rsi_overbought': 'RSI超买线',
            'rsi_oversold': 'RSI超卖线'
        };
        return labels[param] || param;
    }

    getParamHelp(param) {
        const helps = {
            'ma_short': '短期移动平均线的计算周期，建议5-20',
            'ma_long': '长期移动平均线的计算周期，建议20-60',
            'signal_interval': '策略生成信号的时间间隔，单位秒',
            'trade_volume': '每次交易的手数',
            'max_position': '策略允许的最大持仓手数',
            'stop_loss': '止损比例，如0.05表示5%',
            'take_profit': '止盈比例，如0.08表示8%',
            'rsi_period': 'RSI指标的计算周期',
            'rsi_overbought': 'RSI超买阈值，通常70-80',
            'rsi_oversold': 'RSI超卖阈值，通常20-30'
        };
        return helps[param] || '';
    }

    async startStrategy(strategyName) {
        try {
            console.log('启动策略:', strategyName);
            
            const response = await fetch(`/api/v1/trading/strategies/${strategyName}/start`, {
                method: 'POST'
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showNotification(result.message, 'success');
                await this.loadStrategies(); // 重新加载状态
            } else {
                throw new Error(result.message || '启动策略失败');
            }
        } catch (error) {
            console.error('启动策略失败:', error);
            this.showNotification('启动策略失败: ' + error.message, 'error');
        }
    }

    async stopStrategy(strategyName) {
        try {
            console.log('停止策略:', strategyName);
            
            const response = await fetch(`/api/v1/trading/strategies/${strategyName}/stop`, {
                method: 'POST'
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showNotification(result.message, 'success');
                await this.loadStrategies(); // 重新加载状态
            } else {
                throw new Error(result.message || '停止策略失败');
            }
        } catch (error) {
            console.error('停止策略失败:', error);
            this.showNotification('停止策略失败: ' + error.message, 'error');
        }
    }

    // editParams方法已移除，现在使用内联编辑

    renderParamsForm(params) {
        let html = '';

        // 排除资金相关参数，因为使用账户资金
        const excludeParams = ['initial_capital', 'capital', 'balance'];

        Object.entries(params).forEach(([key, value]) => {
            if (excludeParams.includes(key)) {
                return; // 跳过资金参数
            }

            html += `
                <div class="form-group">
                    <label for="param-${key}">${this.getParamLabel(key)}</label>
                    <input
                        type="${typeof value === 'number' ? 'number' : 'text'}"
                        id="param-${key}"
                        name="${key}"
                        class="form-control"
                        value="${value}"
                        ${typeof value === 'number' ? 'step="any"' : ''}
                    >
                    <small class="param-help">${this.getParamHelp(key)}</small>
                </div>
            `;
        });

        return html;
    }

    async saveStrategyParams(event, strategyName) {
        event.preventDefault();

        try {
            const formData = new FormData(document.getElementById('strategy-params-form'));
            const params = {};

            for (let [key, value] of formData.entries()) {
                // 尝试转换为数字
                const numValue = parseFloat(value);
                params[key] = isNaN(numValue) ? value : numValue;
            }

            console.log('保存策略参数:', strategyName, params);

            const response = await fetch(`/api/v1/trading/strategies/${strategyName}/params`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(params)
            });

            const result = await response.json();

            if (result.success) {
                this.showNotification('参数保存成功', 'success');
                await this.loadStrategies(); // 重新加载策略
                this.renderStrategyConfig(strategyName); // 刷新配置显示
            } else {
                throw new Error(result.message || '参数保存失败');
            }
        } catch (error) {
            console.error('保存参数失败:', error);
            this.showNotification('保存参数失败: ' + error.message, 'error');
        }
    }

    resetParams(strategyName) {
        // 重新渲染配置，恢复原始参数
        this.renderStrategyConfig(strategyName);
        this.showNotification('参数已重置', 'info');
    }

    // 模态框相关方法已移除，现在使用内联编辑

    async runBacktest() {
        try {
            const strategyName = this.selectedStrategy;
            const symbol = document.getElementById('backtest-symbol').value;
            const period = document.getElementById('backtest-period').value;
            const interval = document.getElementById('backtest-interval').value;

            if (!strategyName) {
                this.showNotification('请先选择策略', 'warning');
                return;
            }

            // 根据时间期间计算数据条数
            const count = this.calculateDataCount(period, interval);

            console.log('运行回测:', { strategyName, symbol, period, interval, count });

            this.showNotification(`开始回测: ${this.strategies[strategyName].name} (${period})`, 'info');

            // 显示加载状态
            const runBtn = document.getElementById('run-backtest-btn');
            const originalText = runBtn.textContent;
            runBtn.textContent = '回测中...';
            runBtn.disabled = true;

            // 获取策略参数
            const strategy = this.strategies[strategyName];
            const strategyParams = strategy ? strategy.params : {};

            const response = await fetch('/api/v1/trading/backtest', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    strategy_name: strategyName,
                    symbol: symbol,
                    interval: interval,
                    count: count,
                    strategy_params: strategyParams
                })
            });

            const result = await response.json();

            if (result.success) {
                this.displayBacktestResults(result.data.backtest_result);
                this.showNotification('回测完成', 'success');
            } else {
                throw new Error(result.message || '回测失败');
            }
        } catch (error) {
            console.error('回测失败:', error);
            this.showNotification('回测失败: ' + error.message, 'error');
        } finally {
            // 恢复按钮状态
            const runBtn = document.getElementById('run-backtest-btn');
            runBtn.textContent = '运行回测';
            runBtn.disabled = false;
        }
    }

    displayBacktestResults(results) {
        console.log('显示回测结果:', results);

        const resultsContainer = document.getElementById('backtest-results');
        if (!resultsContainer) return;

        // 显示结果容器
        resultsContainer.style.display = 'block';

        // 更新各项指标
        this.updateResultValue('total-return', results.total_return, '%', results.total_return >= 0);
        this.updateResultValue('max-drawdown', results.max_drawdown, '%', false);
        this.updateResultValue('total-trades', results.total_trades, '次');
        this.updateResultValue('initial-capital', results.initial_capital, '元');
        this.updateResultValue('final-capital', results.final_capital, '元', results.final_capital >= results.initial_capital);

        // 滚动到结果区域
        resultsContainer.scrollIntoView({ behavior: 'smooth' });
    }

    updateResultValue(elementId, value, unit = '', isPositive = null) {
        const element = document.getElementById(elementId);
        if (!element) return;

        const formattedValue = typeof value === 'number' ?
            (value >= 1000 ? this.formatCurrency(value) : value.toFixed(2)) :
            value;

        element.textContent = `${formattedValue}${unit}`;

        // 设置颜色 - 使用CSS变量
        if (isPositive !== null) {
            element.style.color = isPositive ? 'var(--success-color)' : 'var(--error-color)';
        } else {
            element.style.color = 'var(--text-primary)';
        }
    }

    formatCurrency(value) {
        return new Intl.NumberFormat('zh-CN', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(value);
    }

    calculateDataCount(period, interval) {
        // 根据时间期间和K线周期计算需要的数据条数
        const periodMinutes = {
            '1h': 60,
            '4h': 240,
            '1d': 1440,
            '3d': 4320,
            '1w': 10080,
            '1m': 43200
        };

        const intervalMinutes = {
            '1m': 1,
            '5m': 5,
            '15m': 15,
            '1h': 60
        };

        const totalMinutes = periodMinutes[period] || 1440;
        const barMinutes = intervalMinutes[interval] || 1;

        return Math.min(Math.max(Math.floor(totalMinutes / barMinutes), 10), 1000);
    }

    startStatusUpdater() {
        // 每5秒更新一次状态
        setInterval(() => {
            this.loadStrategies();
        }, 5000);
    }

    showNotification(message, type = 'info') {
        // 创建通知元素
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        
        // 添加样式
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            border-radius: 4px;
            color: white;
            font-weight: 500;
            z-index: 10000;
            max-width: 300px;
            word-wrap: break-word;
        `;
        
        // 根据类型设置背景色
        const colors = {
            'success': '#28a745',
            'error': '#dc3545',
            'warning': '#ffc107',
            'info': '#17a2b8'
        };
        notification.style.backgroundColor = colors[type] || colors.info;
        
        // 添加到页面
        document.body.appendChild(notification);
        
        // 3秒后自动移除
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 3000);
    }
}

// 全局策略管理器实例
let strategyManager;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    strategyManager = new StrategyManager();
});
