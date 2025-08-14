/**
 * ARBIG策略管理前端JavaScript
 * 负责策略列表、参数编辑、回测等功能
 */

class StrategyManager {
    constructor() {
        this.strategies = {};
        this.activeStrategy = null;
        this.strategyStatus = 'STOPPED';
        this.currentEditingStrategy = null;
        
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

        // 模态框关闭
        document.querySelector('.close')?.addEventListener('click', () => {
            this.closeModal();
        });

        document.getElementById('cancel-params')?.addEventListener('click', () => {
            this.closeModal();
        });

        // 参数表单提交
        document.getElementById('params-form')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveStrategyParams();
        });

        // 点击模态框外部关闭
        document.getElementById('params-modal')?.addEventListener('click', (e) => {
            if (e.target.id === 'params-modal') {
                this.closeModal();
            }
        });
    }

    async loadStrategies() {
        try {
            console.log('加载策略列表...');

            const response = await fetch('/api/v1/trading/strategies');
            const result = await response.json();
            
            if (result.success) {
                this.strategies = result.data.strategies;
                this.activeStrategy = result.data.active_strategy;
                this.strategyStatus = result.data.status;
                
                this.updateStrategyOverview();
                this.renderStrategyGrid();
                this.updateBacktestOptions();
                
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

    renderStrategyGrid() {
        const gridContainer = document.getElementById('strategy-grid');
        if (!gridContainer) return;

        gridContainer.innerHTML = '';

        Object.entries(this.strategies).forEach(([strategyName, strategy]) => {
            const strategyCard = this.createStrategyCard(strategyName, strategy);
            gridContainer.appendChild(strategyCard);
        });
    }

    createStrategyCard(strategyName, strategy) {
        const card = document.createElement('div');
        card.className = `card strategy-card ${this.activeStrategy === strategyName ? 'active' : ''}`;

        const isRunning = this.activeStrategy === strategyName && this.strategyStatus === 'RUNNING';

        card.innerHTML = `
            <div class="card-header">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span>🎯 ${strategy.name}</span>
                    <span class="status-indicator ${strategy.enabled ? 'online' : 'offline'}">
                        ${strategy.enabled ? '启用' : '禁用'}
                    </span>
                </div>
            </div>
            <div class="card-body">
                <p style="color: var(--text-secondary); margin-bottom: 16px;">${strategy.description}</p>

                <div class="grid grid-2" style="gap: 8px; margin-bottom: 16px;">
                    ${this.renderParamsPreview(strategy.params)}
                </div>

                <div class="strategy-actions" style="display: flex; gap: 8px;">
                    <button class="btn btn-outline btn-sm" onclick="strategyManager.editParams('${strategyName}')">
                        ⚙️ 编辑参数
                    </button>
                    ${isRunning ?
                        `<button class="btn btn-danger btn-sm" onclick="strategyManager.stopStrategy('${strategyName}')">
                            ⏹️ 停止策略
                        </button>` :
                        `<button class="btn btn-success btn-sm" onclick="strategyManager.startStrategy('${strategyName}')"
                            ${this.strategyStatus === 'RUNNING' ? 'disabled' : ''}>
                            ▶️ 启动策略
                        </button>`
                    }
                </div>
            </div>
        `;

        return card;
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
            'ma_short': '短期均线',
            'ma_long': '长期均线',
            'initial_capital': '初始资金',
            'stop_loss': '止损比例',
            'take_profit': '止盈比例',
            'rsi_period': 'RSI周期',
            'rsi_overbought': 'RSI超买',
            'rsi_oversold': 'RSI超卖',
            'max_position': '最大持仓'
        };
        return labels[param] || param;
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

    editParams(strategyName) {
        console.log('编辑策略参数:', strategyName);
        
        this.currentEditingStrategy = strategyName;
        const strategy = this.strategies[strategyName];
        
        if (!strategy) {
            this.showNotification('策略不存在', 'error');
            return;
        }
        
        this.renderParamsForm(strategy.params);
        this.showModal();
    }

    renderParamsForm(params) {
        const container = document.getElementById('params-container');
        if (!container) return;
        
        container.innerHTML = '';
        
        Object.entries(params).forEach(([key, value]) => {
            const formGroup = document.createElement('div');
            formGroup.className = 'form-group';
            
            formGroup.innerHTML = `
                <label for="param-${key}">${this.getParamLabel(key)}:</label>
                <input 
                    type="${typeof value === 'number' ? 'number' : 'text'}" 
                    id="param-${key}" 
                    name="${key}"
                    class="form-control" 
                    value="${value}"
                    ${typeof value === 'number' ? 'step="any"' : ''}
                >
            `;
            
            container.appendChild(formGroup);
        });
    }

    async saveStrategyParams() {
        if (!this.currentEditingStrategy) return;
        
        try {
            const formData = new FormData(document.getElementById('params-form'));
            const params = {};
            
            for (let [key, value] of formData.entries()) {
                // 尝试转换为数字
                const numValue = parseFloat(value);
                params[key] = isNaN(numValue) ? value : numValue;
            }
            
            console.log('保存策略参数:', this.currentEditingStrategy, params);
            
            const response = await fetch(`/api/v1/trading/strategies/${this.currentEditingStrategy}/params`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(params)
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showNotification('参数保存成功', 'success');
                this.closeModal();
                await this.loadStrategies(); // 重新加载策略
            } else {
                throw new Error(result.message || '参数保存失败');
            }
        } catch (error) {
            console.error('保存参数失败:', error);
            this.showNotification('保存参数失败: ' + error.message, 'error');
        }
    }

    showModal() {
        const modal = document.getElementById('params-modal');
        if (modal) {
            modal.style.display = 'block';
        }
    }

    closeModal() {
        const modal = document.getElementById('params-modal');
        if (modal) {
            modal.style.display = 'none';
        }
        this.currentEditingStrategy = null;
    }

    updateBacktestOptions() {
        const select = document.getElementById('backtest-strategy');
        if (!select) return;
        
        select.innerHTML = '<option value="">请选择策略</option>';
        
        Object.entries(this.strategies).forEach(([strategyName, strategy]) => {
            const option = document.createElement('option');
            option.value = strategyName;
            option.textContent = strategy.name;
            select.appendChild(option);
        });
    }

    async runBacktest() {
        try {
            const strategyName = document.getElementById('backtest-strategy').value;
            const symbol = document.getElementById('backtest-symbol').value;
            const interval = document.getElementById('backtest-interval').value;
            const count = parseInt(document.getElementById('backtest-count').value);

            if (!strategyName) {
                this.showNotification('请选择策略', 'warning');
                return;
            }

            console.log('运行回测:', { strategyName, symbol, interval, count });

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
