/**
 * ARBIG增强策略管理前端JavaScript
 * 包含性能监控、参数管理、实时状态更新等功能
 */

class EnhancedStrategyManager {
    constructor() {
        this.strategies = {};
        this.strategiesPerformance = {};
        this.activeStrategy = null;
        this.selectedStrategy = null;
        this.refreshInterval = null;
        this.performanceChart = null;

        this.init();
    }

    async init() {
        console.log('初始化增强策略管理器...');
        this.bindEvents();
        await this.loadStrategies();
        await this.loadStrategiesPerformance();
        this.startAutoRefresh();
        this.initializeCharts();
    }

    bindEvents() {
        // 刷新按钮
        document.getElementById('refresh-btn')?.addEventListener('click', () => {
            this.loadStrategies();
            this.loadStrategiesPerformance();
        });

        // 添加策略按钮
        document.getElementById('add-strategy-btn')?.addEventListener('click', () => {
            this.showAddStrategyDialog();
        });

        // 性能监控切换
        document.getElementById('performance-toggle')?.addEventListener('click', () => {
            this.togglePerformanceView();
        });
    }

    async loadStrategies() {
        try {
            console.log('加载策略类型...');
            // 加载可用的策略类型
            const response = await fetch('/api/v1/trading/strategies/types');
            const result = await response.json();

            if (result.success && result.data) {
                this.strategies = result.data;
                this.renderStrategiesList();
                this.updateStrategiesOverview();
                console.log('策略类型加载成功:', Object.keys(this.strategies).length, '个策略类型');
            } else {
                console.error('加载策略类型失败:', result);
                this.showError('加载策略类型失败');
            }
        } catch (error) {
            console.error('加载策略类型异常:', error);
            this.showError('加载策略类型失败: ' + error.message);
        }
    }

    async loadStrategiesPerformance() {
        try {
            console.log('加载策略性能数据...');
            const response = await fetch('/api/v1/trading/strategies/performance');
            const result = await response.json();

            if (result.success && result.data) {
                this.strategiesPerformance = result.data;
                this.renderPerformanceData();
            } else {
                console.warn('无性能数据:', result);
            }
        } catch (error) {
            console.error('加载性能数据异常:', error);
        }
    }

    renderStrategiesList() {
        const container = document.getElementById('strategies-list');
        if (!container) return;

        if (!this.strategies || Object.keys(this.strategies).length === 0) {
            container.innerHTML = '<div class="empty-state">暂无策略</div>';
            return;
        }

        const strategiesHtml = Object.entries(this.strategies).map(([name, strategy]) => {
            const performance = this.strategiesPerformance[name];
            const isRunning = strategy.status === 'running';

            return `
                <div class="strategy-card ${this.selectedStrategy === name ? 'selected' : ''}" 
                     onclick="strategyManager.selectStrategy('${name}')">
                    <div class="strategy-header">
                        <div class="strategy-info">
                            <h4>${strategy.strategy_name || name}</h4>
                            <span class="strategy-type">${strategy.class_name || '未知类型'}</span>
                        </div>
                        <div class="strategy-status">
                            <span class="status-badge ${isRunning ? 'running' : 'stopped'}">
                                ${isRunning ? '运行中' : '已停止'}
                            </span>
                        </div>
                    </div>
                    
                    <div class="strategy-metrics">
                        <div class="metric">
                            <span class="metric-label">合约</span>
                            <span class="metric-value">${strategy.symbol || '-'}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">持仓</span>
                            <span class="metric-value">${strategy.pos || 0}</span>
                        </div>
                        ${performance ? `
                            <div class="metric">
                                <span class="metric-label">今日盈亏</span>
                                <span class="metric-value ${performance.today.net_pnl >= 0 ? 'positive' : 'negative'}">
                                    ${performance.today.net_pnl.toFixed(2)}
                                </span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">胜率</span>
                                <span class="metric-value">${(performance.win_rate * 100).toFixed(1)}%</span>
                            </div>
                        ` : ''}
                    </div>
                    
                    <div class="strategy-actions">
                        ${isRunning ? 
                            `<button class="btn btn-danger btn-sm" onclick="event.stopPropagation(); strategyManager.stopStrategy('${name}')">停止</button>` :
                            `<button class="btn btn-success btn-sm" onclick="event.stopPropagation(); strategyManager.startStrategy('${name}')">启动</button>`
                        }
                        <button class="btn btn-outline btn-sm" onclick="event.stopPropagation(); strategyManager.editStrategy('${name}')">编辑</button>
                        <button class="btn btn-outline btn-sm" onclick="event.stopPropagation(); strategyManager.deleteStrategy('${name}')">删除</button>
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = strategiesHtml;
    }

    renderPerformanceData() {
        if (!this.selectedStrategy || !this.strategiesPerformance[this.selectedStrategy]) {
            return;
        }

        const performance = this.strategiesPerformance[this.selectedStrategy];
        this.renderPerformanceMetrics(performance);
        this.updatePerformanceChart(performance);
    }

    renderPerformanceMetrics(performance) {
        const container = document.getElementById('performance-metrics');
        if (!container) return;

        container.innerHTML = `
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-title">总盈亏</div>
                    <div class="metric-value ${performance.net_pnl >= 0 ? 'positive' : 'negative'}">
                        ${performance.net_pnl.toFixed(2)}
                    </div>
                    <div class="metric-subtitle">净收益</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-title">今日盈亏</div>
                    <div class="metric-value ${performance.today.net_pnl >= 0 ? 'positive' : 'negative'}">
                        ${performance.today.net_pnl.toFixed(2)}
                    </div>
                    <div class="metric-subtitle">今日净收益</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-title">胜率</div>
                    <div class="metric-value">${(performance.win_rate * 100).toFixed(1)}%</div>
                    <div class="metric-subtitle">${performance.winning_trades}/${performance.total_trades}</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-title">最大回撤</div>
                    <div class="metric-value negative">${(performance.max_drawdown * 100).toFixed(2)}%</div>
                    <div class="metric-subtitle">风险指标</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-title">夏普比率</div>
                    <div class="metric-value">${performance.sharpe_ratio.toFixed(2)}</div>
                    <div class="metric-subtitle">风险调整收益</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-title">盈亏比</div>
                    <div class="metric-value">${performance.profit_factor.toFixed(2)}</div>
                    <div class="metric-subtitle">收益风险比</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-title">当前持仓</div>
                    <div class="metric-value">${performance.current_position}</div>
                    <div class="metric-subtitle">最大持仓: ${performance.max_position}</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-title">运行时间</div>
                    <div class="metric-value">${performance.runtime_hours.toFixed(1)}h</div>
                    <div class="metric-subtitle">累计运行</div>
                </div>
            </div>
        `;
    }

    initializeCharts() {
        const canvas = document.getElementById('performance-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        this.performanceChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: '净值曲线',
                    data: [],
                    borderColor: '#007bff',
                    backgroundColor: 'rgba(0, 123, 255, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            displayFormats: {
                                hour: 'HH:mm',
                                day: 'MM-DD'
                            }
                        }
                    },
                    y: {
                        beginAtZero: false,
                        grid: {
                            color: 'rgba(0,0,0,0.1)'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                },
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                }
            }
        });
    }

    updatePerformanceChart(performance) {
        if (!this.performanceChart) return;

        // 这里需要从策略服务获取净值曲线数据
        // 暂时使用模拟数据
        const labels = [];
        const data = [];
        
        // 生成示例数据点
        const now = new Date();
        for (let i = 23; i >= 0; i--) {
            const time = new Date(now.getTime() - i * 60 * 60 * 1000);
            labels.push(time);
            data.push(performance.net_pnl * (1 + (Math.random() - 0.5) * 0.1));
        }

        this.performanceChart.data.labels = labels;
        this.performanceChart.data.datasets[0].data = data;
        this.performanceChart.update();
    }

    updateStrategiesOverview() {
        const totalStrategies = Object.keys(this.strategies).length;
        const activeStrategies = Object.values(this.strategies).filter(s => s.status === 'running').length;

        // 更新概览数据
        const strategyCountEl = document.getElementById('strategy-count');
        if (strategyCountEl) {
            strategyCountEl.textContent = totalStrategies;
        }

        const activeStrategyEl = document.getElementById('active-strategy');
        const statusIndicatorEl = document.getElementById('strategy-status-indicator');
        if (activeStrategyEl && statusIndicatorEl) {
            if (activeStrategies > 0) {
                activeStrategyEl.textContent = `${activeStrategies} 个策略运行中`;
                statusIndicatorEl.textContent = '▶️';
            } else {
                activeStrategyEl.textContent = '无活跃策略';
                statusIndicatorEl.textContent = '⏸️';
            }
        }
    }

    selectStrategy(strategyName) {
        this.selectedStrategy = strategyName;
        this.renderStrategiesList(); // 重新渲染以更新选中状态
        this.renderPerformanceData(); // 渲染性能数据
        this.loadStrategyDetails(strategyName);
    }

    async loadStrategyDetails(strategyName) {
        try {
            // 从已加载的策略类型中获取详情
            const strategy = this.strategies[strategyName];
            if (strategy) {
                this.renderStrategyDetails(strategy, strategyName);
            } else {
                console.error('策略类型未找到:', strategyName);
            }
        } catch (error) {
            console.error('加载策略详情失败:', error);
        }
    }

    renderStrategyDetails(strategy, strategyName) {
        const container = document.getElementById('strategy-details');
        if (!container) return;

        container.innerHTML = `
            <div class="strategy-details-content">
                <div class="details-header">
                    <h3>${strategy.name || strategyName}</h3>
                    <div class="details-actions">
                        <button class="btn btn-primary" onclick="strategyManager.showRegisterDialog('${strategyName}')">注册实例</button>
                        <button class="btn btn-outline" onclick="strategyManager.editStrategyParams('${strategyName}')">编辑参数</button>
                    </div>
                </div>
                
                <div class="details-body">
                    <div class="details-section">
                        <h4>策略类型信息</h4>
                        <div class="info-grid">
                            <div class="info-item">
                                <span class="info-label">类名:</span>
                                <span class="info-value">${strategy.class_name || strategyName}</span>
                            </div>
                            <div class="info-item">
                                <span class="info-label">描述:</span>
                                <span class="info-value">${strategy.description || '暂无描述'}</span>
                            </div>
                            <div class="info-item">
                                <span class="info-label">文件路径:</span>
                                <span class="info-value">${strategy.file_path || '未知'}</span>
                            </div>
                            <div class="info-item">
                                <span class="info-label">状态:</span>
                                <span class="info-value status-available">可用</span>
                            </div>
                        </div>
                    </div>
                    
                    <div class="details-section">
                        <h4>默认参数</h4>
                        <div class="params-grid">
                            ${strategy.default_params ? this.renderStrategyParams(strategy.default_params) : '<p class="no-params">暂无默认参数</p>'}
                        </div>
                    </div>
                    
                    <div class="details-section">
                        <h4>策略说明</h4>
                        <div class="strategy-description">
                            <p>${strategy.description || '暂无详细说明'}</p>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    renderStrategyParams(params) {
        return Object.entries(params).map(([key, value]) => `
            <div class="param-item">
                <span class="param-label">${key}:</span>
                <span class="param-value">${value}</span>
            </div>
        `).join('');
    }

    async startStrategy(strategyName) {
        try {
            const response = await fetch(`/api/v1/trading/strategies/${strategyName}/start`, {
                method: 'POST'
            });
            const result = await response.json();

            if (result.success) {
                this.showSuccess(`策略 ${strategyName} 启动成功`);
                await this.loadStrategies();
            } else {
                this.showError(`启动策略失败: ${result.message}`);
            }
        } catch (error) {
            this.showError(`启动策略失败: ${error.message}`);
        }
    }

    async stopStrategy(strategyName) {
        try {
            const response = await fetch(`/api/v1/trading/strategies/${strategyName}/stop`, {
                method: 'POST'
            });
            const result = await response.json();

            if (result.success) {
                this.showSuccess(`策略 ${strategyName} 停止成功`);
                await this.loadStrategies();
            } else {
                this.showError(`停止策略失败: ${result.message}`);
            }
        } catch (error) {
            this.showError(`停止策略失败: ${error.message}`);
        }
    }

    startAutoRefresh() {
        // 每30秒刷新一次数据
        this.refreshInterval = setInterval(() => {
            this.loadStrategies();
            this.loadStrategiesPerformance();
        }, 30000);
    }

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    showSuccess(message) {
        this.showNotification(message, 'success');
    }

    showError(message) {
        this.showNotification(message, 'error');
    }

    showNotification(message, type = 'info') {
        // 创建通知元素
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;

        // 添加到页面
        document.body.appendChild(notification);

        // 3秒后自动移除
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 3000);
    }

    // 占位方法，待实现
    showAddStrategyDialog() {
        console.log('显示添加策略对话框');
        // TODO: 实现添加策略对话框
    }

    showRegisterDialog(strategyType) {
        console.log('显示策略注册对话框:', strategyType);
        const strategy = this.strategies[strategyType];
        console.log('找到的策略对象:', strategy);
        if (!strategy) {
            console.log('策略类型不存在，可用策略:', Object.keys(this.strategies));
            this.showError('策略类型不存在');
            return;
        }

        // 先移除可能存在的旧对话框
        const existingModal = document.getElementById('register-modal');
        if (existingModal) {
            existingModal.remove();
        }

        // 创建注册对话框HTML - 使用更简单的结构
        const dialogHtml = `
            <div class="modal-overlay" id="register-modal" style="position: fixed !important; top: 0 !important; left: 0 !important; width: 100% !important; height: 100% !important; background: rgba(0,0,0,0.8) !important; display: flex !important; justify-content: center !important; align-items: center !important; z-index: 10000 !important;">
                <div class="modal-content" style="background: white !important; padding: 20px !important; border-radius: 8px !important; max-width: 600px !important; width: 90% !important; max-height: 90vh !important; overflow-y: auto !important;">
                    <div class="modal-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 1px solid #eee; padding-bottom: 10px;">
                        <h3 style="margin: 0;">注册策略实例</h3>
                        <button class="modal-close" onclick="strategyManager.closeRegisterDialog()" style="background: none; border: none; font-size: 24px; cursor: pointer;">&times;</button>
                    </div>
                    <div class="modal-body">
                        <div class="form-group" style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px; font-weight: bold;">策略类型:</label>
                            <input type="text" value="${strategy.class_name || strategyType}" readonly style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; background: #f5f5f5;">
                        </div>
                        <div class="form-group" style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px; font-weight: bold;">实例名称:</label>
                            <input type="text" id="instance-name" placeholder="请输入策略实例名称" required style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                        </div>
                        <div class="form-group" style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px; font-weight: bold;">交易合约:</label>
                            <input type="text" id="symbol" placeholder="如: au2510" value="au2510" required style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                        </div>
                        <div class="form-group" style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px; font-weight: bold;">策略描述:</label>
                            <textarea id="description" placeholder="可选：策略实例描述" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; min-height: 60px;"></textarea>
                        </div>
                        <div class="form-section" style="margin-top: 20px; padding-top: 15px; border-top: 1px solid #eee;">
                            <h4 style="margin-bottom: 10px;">策略参数</h4>
                            <div id="strategy-params">
                                ${this.renderParamInputs(strategy.parameters || {})}
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer" style="margin-top: 20px; padding-top: 15px; border-top: 1px solid #eee; display: flex; justify-content: flex-end; gap: 10px;">
                        <button class="btn btn-secondary" onclick="strategyManager.closeRegisterDialog()" style="padding: 8px 16px; border: 1px solid #ccc; background: #f8f9fa; border-radius: 4px; cursor: pointer;">取消</button>
                        <button class="btn btn-primary" onclick="strategyManager.submitRegistration('${strategyType}')" style="padding: 8px 16px; border: none; background: #007bff; color: white; border-radius: 4px; cursor: pointer;">注册实例</button>
                    </div>
                </div>
            </div>
        `;

        // 先创建一个简单的测试元素
        const testDiv = document.createElement('div');
        testDiv.id = 'test-element';
        testDiv.style.cssText = 'position: fixed; top: 50px; left: 50px; background: red; color: white; padding: 10px; z-index: 10000;';
        testDiv.textContent = '测试元素 - 如果你看到这个，DOM操作正常';
        document.body.appendChild(testDiv);
        console.log('测试元素已添加');
        
        // 添加到页面
        document.body.insertAdjacentHTML('beforeend', dialogHtml);
        console.log('对话框HTML已插入到页面');
        
        // 检查是否成功插入
        const modal = document.getElementById('register-modal');
        console.log('找到的模态对话框元素:', modal);
        if (modal) {
            console.log('模态对话框样式:', window.getComputedStyle(modal).display);
            console.log('模态对话框位置:', modal.getBoundingClientRect());
        }
        
        // 5秒后移除测试元素
        setTimeout(() => {
            if (testDiv.parentNode) {
                testDiv.parentNode.removeChild(testDiv);
                console.log('测试元素已移除');
            }
        }, 5000);
    }

    closeRegisterDialog() {
        console.log('关闭注册对话框');
        const modal = document.getElementById('register-modal');
        if (modal) {
            modal.remove();
            console.log('注册对话框已移除');
        }
    }

    editStrategy(strategyName) {
        console.log('编辑策略:', strategyName);
        // TODO: 实现策略编辑功能
    }

    editStrategyParams(strategyName) {
        console.log('编辑策略参数:', strategyName);
        // TODO: 实现参数编辑功能
    }

    deleteStrategy(strategyName) {
        if (confirm(`确定要删除策略 ${strategyName} 吗？`)) {
            console.log('删除策略:', strategyName);
            // TODO: 实现策略删除功能
        }
    }

    renderParamInputs(params) {
        if (!params || Object.keys(params).length === 0) {
            return '<p class="no-params" style="color: #666; font-style: italic; text-align: center; padding: 20px;">该策略没有可配置参数</p>';
        }

        return Object.entries(params).map(([key, value]) => {
            let displayValue, inputType, inputElement;
            
            // 处理不同类型的参数值
            if (typeof value === 'object' && value !== null) {
                // 对象类型参数，转换为JSON字符串显示
                displayValue = JSON.stringify(value, null, 2);
                inputType = 'textarea';
                inputElement = `<textarea id="param-${key}" name="${key}" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; min-height: 80px; font-family: monospace;">${displayValue}</textarea>`;
            } else if (typeof value === 'number') {
                displayValue = value;
                inputType = 'number';
                inputElement = `<input type="number" id="param-${key}" name="${key}" value="${displayValue}" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;" />`;
            } else if (typeof value === 'boolean') {
                displayValue = value;
                inputType = 'checkbox';
                inputElement = `<input type="checkbox" id="param-${key}" name="${key}" ${value ? 'checked' : ''} style="margin-right: 10px;" />`;
            } else {
                // 字符串或其他类型
                displayValue = String(value);
                inputType = 'text';
                inputElement = `<input type="text" id="param-${key}" name="${key}" value="${displayValue}" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;" />`;
            }
            
            return `
                <div class="param-input-group" style="margin-bottom: 16px; padding: 12px; background: #f8f9fa; border-radius: 6px;">
                    <label for="param-${key}" style="display: block; font-weight: 500; color: #495057; margin-bottom: 6px;">${key}:</label>
                    ${inputElement}
                    <span class="param-help" style="font-size: 12px; color: #6c757d; font-style: italic; display: block; margin-top: 4px;">
                        默认值: ${typeof value === 'object' ? JSON.stringify(value) : String(displayValue)}
                    </span>
                </div>
            `;
        }).join('');
    }

    closeRegisterDialog() {
        const modal = document.getElementById('register-modal');
        if (modal) {
            modal.remove();
        }
    }

    async submitRegistration(strategyType) {
        try {
            // 收集表单数据
            const instanceName = document.getElementById('instance-name').value.trim();
            const symbol = document.getElementById('symbol').value.trim();
            const description = document.getElementById('description').value.trim();

            if (!instanceName) {
                alert('请输入策略实例名称');
                return;
            }

            if (!symbol) {
                alert('请输入交易合约');
                return;
            }

            // 收集策略参数
            const params = {};
            const paramInputs = document.querySelectorAll('#strategy-params input, #strategy-params textarea');
            paramInputs.forEach(input => {
                let value;
                if (input.type === 'number') {
                    value = parseFloat(input.value);
                } else if (input.type === 'checkbox') {
                    value = input.checked;
                } else if (input.tagName === 'TEXTAREA') {
                    // 尝试解析JSON，如果失败则作为字符串处理
                    try {
                        value = JSON.parse(input.value);
                    } catch (e) {
                        value = input.value;
                    }
                } else {
                    value = input.value;
                }
                params[input.name] = value;
            });

            // 构建注册数据
            const registrationData = {
                strategy_type: strategyType,
                instance_name: instanceName,
                symbol: symbol,
                description: description,
                params: params
            };

            console.log('注册策略实例:', registrationData);

            // 发送注册请求
            const response = await fetch('/api/v1/trading/strategies/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(registrationData)
            });

            const result = await response.json();

            if (result.success) {
                this.showSuccess(`策略实例 "${instanceName}" 注册成功！`);
                this.closeRegisterDialog();
                this.loadStrategies(); // 重新加载策略列表
            } else {
                this.showError(`注册失败: ${result.detail || result.message || '未知错误'}`);
            }

        } catch (error) {
            console.error('注册策略失败:', error);
            this.showError('注册策略失败: ' + error.message);
        }
    }

    togglePerformanceView() {
        const performanceSection = document.getElementById('performance-section');
        if (performanceSection) {
            performanceSection.style.display = 
                performanceSection.style.display === 'none' ? 'block' : 'none';
        }
    }
}

// 全局实例
let strategyManager;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    strategyManager = new EnhancedStrategyManager();
});
