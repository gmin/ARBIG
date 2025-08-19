// ARBIG Trading Management JavaScript

// 交易配置
const TRADING_CONFIG = {
    // 默认合约 (将从服务器动态获取)
    DEFAULT_SYMBOL: 'au2510',

    // 支持的合约列表 (将从服务器动态获取)
    SUPPORTED_SYMBOLS: [],

    // 获取当前选中的合约
    getCurrentSymbol() {
        const symbolInput = document.getElementById('symbol');
        if (symbolInput && symbolInput.value) {
            return symbolInput.value;
        }
        // 如果选择器没有值，返回默认主力合约
        return this.DEFAULT_SYMBOL || 'au2510';
    },

    // 从服务器加载合约配置
    async loadContractsConfig() {
        try {
            const response = await fetch('/api/v1/trading/config/main_contract');
            const result = await response.json();

            if (result.success) {
                this.DEFAULT_SYMBOL = result.data.main_contract;
                this.SUPPORTED_SYMBOLS = result.data.supported_contracts || [
                    { symbol: result.data.main_contract, name: `黄金主力 (${result.data.main_contract})`, is_main: true },
                    { symbol: 'au2508', name: '黄金2508 (au2508)', is_main: false },
                    { symbol: 'au2509', name: '黄金2509 (au2509)', is_main: false },
                    { symbol: 'au2510', name: '黄金2510 (au2510)', is_main: false },
                    { symbol: 'ag2508', name: '白银主力 (ag2508)', is_main: false },
                    { symbol: 'cu2508', name: '铜主力 (cu2508)', is_main: false }
                ];

                console.log('✅ 合约配置加载成功:', this.SUPPORTED_SYMBOLS);
                return true;
            } else {
                console.error('❌ 合约配置加载失败:', result);
                return false;
            }
        } catch (error) {
            console.error('❌ 合约配置加载异常:', error);
            // 使用默认配置作为备用
            this.SUPPORTED_SYMBOLS = [
                { symbol: 'au2510', name: '黄金2510', is_main: true }
            ];
            return false;
        }
    },

    // 更新合约选择器
    updateSymbolSelector() {
        const symbolSelect = document.getElementById('symbol');
        if (!symbolSelect) return;

        // 清空现有选项
        symbolSelect.innerHTML = '';

        // 添加合约选项
        this.SUPPORTED_SYMBOLS.forEach(contract => {
            const option = document.createElement('option');
            option.value = contract.symbol;
            option.textContent = contract.name;
            if (contract.is_main || contract.symbol === this.DEFAULT_SYMBOL) {
                option.selected = true;
            }
            symbolSelect.appendChild(option);
        });

        // 更新行情显示的合约名称
        const marketSymbolElement = document.getElementById('market-symbol');
        if (marketSymbolElement) {
            marketSymbolElement.textContent = this.DEFAULT_SYMBOL;
        }
    },

    // 获取合约显示名称
    getSymbolDisplayName(symbol) {
        const contract = this.SUPPORTED_SYMBOLS.find(s => s.symbol === symbol);
        return contract ? contract.name : symbol;
    },

    // 获取合约显示名称
    getSymbolDisplayName(symbol) {
        const config = this.SUPPORTED_SYMBOLS.find(s => s.code === symbol);
        return config ? `${config.name} (${config.code})` : symbol;
    }
};

class TradingManager {
    constructor() {
        this.updateInterval = 2000; // 2秒更新一次
        this.isUpdating = false;
        this.init();
    }

    init() {
        console.log('🚀 ARBIG 交易管理初始化...');
        this.startAutoUpdate();
        this.bindEvents();
        this.loadInitialData();
    }

    bindEvents() {
        // 绑定事件处理器
        window.addEventListener('beforeunload', () => {
            this.stopAutoUpdate();
        });
    }

    startAutoUpdate() {
        this.updateTimer = setInterval(() => {
            if (!this.isUpdating) {
                this.updateData();
            }
        }, this.updateInterval);
        console.log('✅ 自动更新已启动');
    }

    stopAutoUpdate() {
        if (this.updateTimer) {
            clearInterval(this.updateTimer);
            console.log('⏹️ 自动更新已停止');
        }
    }

    async loadInitialData() {
        console.log('📊 加载初始数据...');
        await this.updateData();
    }

    async updateData() {
        if (this.isUpdating) return;
        this.isUpdating = true;

        try {
            await Promise.all([
                this.updateMarketData(),
                this.updatePositions(),
                this.updateStrategyStatus(),
                this.updateTriggers(),
                this.updateAccountInfo()
            ]);
        } catch (error) {
            console.error('❌ 数据更新失败:', error);
        } finally {
            this.isUpdating = false;
        }
    }

    async updateMarketData() {
        try {
            const currentSymbol = TRADING_CONFIG.getCurrentSymbol();

            // 优先从CTP状态接口获取数据，确保数据来源一致
            const response = await fetch('/api/v1/trading/ctp_status');
            if (!response.ok) throw new Error('CTP状态获取失败');

            const statusData = await response.json();
            if (statusData.success && statusData.data.tick_data && statusData.data.tick_data[currentSymbol]) {
                const tick = statusData.data.tick_data[currentSymbol];
                this.displayMarketData(tick);
                this.updateConnectionStatus('online');
                return;
            }

            // 如果状态接口失败，尝试直接API
            const tickResponse = await fetch(`/api/v1/trading/tick/${currentSymbol}`);
            if (tickResponse.ok) {
                const tickResult = await tickResponse.json();
                if (tickResult.success && tickResult.data && tickResult.data.response) {
                    // 解析ServiceClient包装的响应
                    const innerData = JSON.parse(tickResult.data.response);
                    if (innerData.success && innerData.data) {
                        const tick = innerData.data;
                        this.displayMarketData(tick);
                        this.updateConnectionStatus('online');
                        return;
                    }
                }
            }

            throw new Error('无法获取行情数据');
        } catch (error) {
            console.error('❌ 行情数据更新失败:', error);
            this.updateConnectionStatus('offline');
        }
    }

    displayMarketData(tick) {
        // 更新价格显示
        const lastPrice = tick.last_price || tick.current_price || 0;
        const bidPrice = tick.bid_price_1 || tick.bid_price || 0;
        const askPrice = tick.ask_price_1 || tick.ask_price || 0;
        const volume = tick.volume || 0;
        const bidVolume = tick.bid_volume_1 || tick.bid_volume || 0;
        const askVolume = tick.ask_volume_1 || tick.ask_volume || 0;

        // 订单簿显示
        document.getElementById('last-price').textContent = this.formatNumber(lastPrice);
        document.getElementById('bid-price').textContent = this.formatNumber(bidPrice);
        document.getElementById('ask-price').textContent = this.formatNumber(askPrice);
        document.getElementById('volume-display').textContent = volume.toLocaleString();

        // 显示买卖量（如果有的话）
        const bidVolumeElement = document.getElementById('bid-volume');
        const askVolumeElement = document.getElementById('ask-volume');
        if (bidVolumeElement) {
            bidVolumeElement.textContent = bidVolume > 0 ? bidVolume.toString() : '--';
        }
        if (askVolumeElement) {
            askVolumeElement.textContent = askVolume > 0 ? askVolume.toString() : '--';
        }

        // 计算价格变化
        const priceChange = tick.pre_close_price ?
            ((lastPrice - tick.pre_close_price) / tick.pre_close_price * 100) : 0;

        const changeElement = document.getElementById('price-change');
        if (priceChange > 0) {
            changeElement.textContent = `+${priceChange.toFixed(2)}%`;
            changeElement.className = 'price-change price-up';
        } else if (priceChange < 0) {
            changeElement.textContent = `${priceChange.toFixed(2)}%`;
            changeElement.className = 'price-change price-down';
        } else {
            changeElement.textContent = '0.00%';
            changeElement.className = 'price-change';
        }
    }

    async updatePositions() {
        try {
            const response = await fetch('/api/v1/trading/positions');
            if (!response.ok) throw new Error('持仓数据获取失败');

            const result = await response.json();
            console.log('📊 持仓数据响应:', result);

            // 处理持仓数据格式
            let positionsArray = [];
            
            // 检查是否是数组格式（新的API格式）
            if (Array.isArray(result)) {
                positionsArray = result.map(pos => ({
                    symbol: pos.symbol,
                    direction: pos.direction,
                    volume: pos.volume,
                    open_price: pos.avg_price || pos.open_price || 0,
                    current_price: pos.current_price || 0,
                    unrealized_pnl: pos.unrealized_pnl || 0,
                    today_volume: pos.today_volume || 0,
                    yd_volume: pos.yd_volume || 0,
                    position_detail: pos.position_detail || {
                        total: pos.volume,
                        today: pos.today_volume || 0,
                        yesterday: pos.yd_volume || 0
                    }
                }));
            } 
            // 兼容旧的对象格式
            else if (result.success && result.data) {
                Object.keys(result.data).forEach(symbol => {
                    const pos = result.data[symbol];
                    if (pos.long_position > 0) {
                        positionsArray.push({
                            symbol: symbol,
                            direction: 'LONG',
                            volume: pos.long_position,
                            open_price: pos.long_price,
                            current_price: pos.current_price || 0,
                            unrealized_pnl: pos.long_pnl || 0,
                            today_volume: pos.long_today || 0,
                            yd_volume: pos.long_yesterday || 0,
                            position_detail: pos.position_detail?.long || {
                                total: pos.long_position,
                                today: pos.long_today || 0,
                                yesterday: pos.long_yesterday || 0
                            }
                        });
                    }
                    if (pos.short_position > 0) {
                        positionsArray.push({
                            symbol: symbol,
                            direction: 'SHORT',
                            volume: pos.short_position,
                            open_price: pos.short_price,
                            current_price: pos.current_price || 0,
                            unrealized_pnl: pos.short_pnl || 0,
                            today_volume: pos.short_today || 0,
                            yd_volume: pos.short_yesterday || 0,
                            position_detail: pos.position_detail?.short || {
                                total: pos.short_position,
                                today: pos.short_today || 0,
                                yesterday: pos.short_yesterday || 0
                            }
                        });
                    }
                });
            }

            console.log('📊 处理后的持仓数据:', positionsArray);

            // 保存当前持仓数据供其他函数使用
            this.currentPositions = positionsArray;
            this.displayPositions(positionsArray);
        } catch (error) {
            console.error('❌ 持仓数据更新失败:', error);
            this.showPositionsError();
        }
    }

    displayPositions(positions) {
        const loadingElement = document.getElementById('positions-loading');
        const contentElement = document.getElementById('positions-content');
        const noPositionsElement = document.getElementById('no-positions');
        const tableBody = document.getElementById('positions-table');

        loadingElement.style.display = 'none';

        if (!positions || positions.length === 0) {
            contentElement.style.display = 'none';
            noPositionsElement.style.display = 'block';
            return;
        }

        // 显示持仓表格
        contentElement.style.display = 'block';
        noPositionsElement.style.display = 'none';

        // 清空表格
        tableBody.innerHTML = '';

        positions.forEach((position, index) => {
            if (position.volume === 0) return; // 跳过空仓位

            const row = document.createElement('tr');
            const direction = position.direction === 'LONG' ? '多头' : '空头';
            const pnl = position.unrealized_pnl || 0;
            const pnlClass = pnl >= 0 ? 'price-up' : 'price-down';
            const currentPrice = position.current_price || 0;

            const symbol = position.symbol || TRADING_CONFIG.DEFAULT_SYMBOL;

            // 创建平仓按钮，传递完整的position信息
            const closeButton = document.createElement('button');
            closeButton.className = 'btn btn-danger';
            closeButton.style.cssText = 'font-size: 12px; padding: 4px 8px;';
            closeButton.textContent = '平仓';
            closeButton.onclick = () => closePosition(symbol, position.direction, position.volume, position.position_detail);

            row.innerHTML = `
                <td>${symbol}</td>
                <td>${direction}</td>
                <td>${position.volume}</td>
                <td>${(position.open_price || 0).toFixed(2)}</td>
                <td>${currentPrice.toFixed(2)}</td>
                <td class="${pnlClass}">${pnl.toFixed(0)}</td>
                <td></td>
            `;

            // 将按钮添加到最后一个单元格
            row.lastElementChild.appendChild(closeButton);
            tableBody.appendChild(row);
        });
    }

    updatePositionStats(totalPositions, totalPnl) {
        document.getElementById('total-positions-count').textContent = totalPositions;
        
        const pnlElement = document.getElementById('total-unrealized-pnl');
        pnlElement.textContent = totalPnl.toFixed(0);
        
        // 根据盈亏设置颜色
        if (totalPnl > 0) {
            pnlElement.style.color = 'var(--success-color)';
        } else if (totalPnl < 0) {
            pnlElement.style.color = 'var(--error-color)';
        } else {
            pnlElement.style.color = 'var(--text-primary)';
        }
    }

    async updateStrategyStatus() {
        try {
            const response = await fetch('/api/v1/trading/strategy/status');
            if (!response.ok) throw new Error('策略状态获取失败');

            const result = await response.json();
            if (result.success && result.data) {
                this.displayStrategyStatus(result.data);
            }
        } catch (error) {
            console.error('❌ 策略状态更新失败:', error);
            this.showStrategyError();
        }

        // 同时更新系统状态
        this.updateSystemStatus();
    }

    async updateSystemStatus() {
        try {
            // 获取CTP连接状态
            const response = await fetch('/api/v1/trading/ctp_status');
            if (response.ok) {
                const result = await response.json();

                // 更新CTP连接状态
                const ctpStatusElement = document.getElementById('ctp-status');
                if (ctpStatusElement) {
                    if (result.success && result.data.trading_connected && result.data.market_connected) {
                        ctpStatusElement.textContent = '已连接';
                        ctpStatusElement.className = 'status-value online';
                    } else {
                        ctpStatusElement.textContent = '连接断开';
                        ctpStatusElement.className = 'status-value offline';
                    }
                }
            } else {
                // API调用失败，显示断开状态
                const ctpStatusElement = document.getElementById('ctp-status');
                if (ctpStatusElement) {
                    ctpStatusElement.textContent = '连接断开';
                    ctpStatusElement.className = 'status-value offline';
                }
            }
        } catch (error) {
            console.error('❌ 获取CTP状态失败:', error);
            const ctpStatusElement = document.getElementById('ctp-status');
            if (ctpStatusElement) {
                ctpStatusElement.textContent = '连接断开';
                ctpStatusElement.className = 'status-value offline';
            }
        }

        // 更新策略状态 (暂时硬编码，后续可以从API获取)
        const strategyStatusElement = document.getElementById('strategy-status');
        if (strategyStatusElement) {
            strategyStatusElement.textContent = '运行中';
            strategyStatusElement.className = 'status-value online';
        }
    }

    displayStrategyStatus(status) {
        const loadingElement = document.getElementById('strategy-status');
        const controlsElement = document.getElementById('strategy-controls');
        const statusDisplay = document.getElementById('strategy-status-display');

        // 检查元素是否存在
        if (loadingElement) loadingElement.style.display = 'none';
        if (controlsElement) controlsElement.style.display = 'block';

        // 显示策略状态
        if (statusDisplay) {
            const isRunning = status.is_running || false;
            statusDisplay.innerHTML = `
                <span class="status-indicator ${isRunning ? 'online' : 'offline'}">
                    <span class="status-dot"></span>
                    ${isRunning ? '运行中' : '已停止'}
                </span>
            `;
        }
    }

    async updateTriggers() {
        try {
            const response = await fetch('/api/v1/trading/strategy/triggers?limit=20');
            if (!response.ok) throw new Error('交易记录获取失败');

            const result = await response.json();
            console.log('📊 交易记录API响应:', result);

            if (result.success && result.data) {
                // 确保数据是数组格式
                const triggers = Array.isArray(result.data) ? result.data : [];
                console.log('📊 交易记录数据:', triggers.length, '条记录');
                this.displayTriggers(triggers);
            } else {
                console.log('❌ 交易记录API返回失败或无数据');
                this.displayTriggers([]);
            }
        } catch (error) {
            console.error('❌ 交易记录更新失败:', error);
            this.showTriggersError();
        }
    }

    displayTriggers(triggers) {
        const loadingElement = document.getElementById('triggers-loading');
        const contentElement = document.getElementById('triggers-content');
        const noTriggersElement = document.getElementById('no-triggers');
        const tableBody = document.getElementById('triggers-table');

        loadingElement.style.display = 'none';

        if (!triggers || triggers.length === 0) {
            contentElement.style.display = 'none';
            noTriggersElement.style.display = 'block';
            return;
        }

        contentElement.style.display = 'block';
        noTriggersElement.style.display = 'none';

        // 清空表格
        tableBody.innerHTML = '';

        // 确保triggers是数组
        const triggerArray = Array.isArray(triggers) ? triggers : [];

        if (triggerArray.length === 0) {
            contentElement.style.display = 'none';
            noTriggersElement.style.display = 'block';
            return;
        }

        triggerArray.forEach(trigger => {
            const row = document.createElement('tr');
            const time = new Date(trigger.timestamp).toLocaleString();
            
            row.innerHTML = `
                <td>${time}</td>
                <td>${trigger.strategy_name || '--'}</td>
                <td>${trigger.signal_type || '--'}</td>
                <td>${trigger.symbol || '--'}</td>
                <td>${trigger.direction || '--'}</td>
                <td>${trigger.volume || '--'}</td>
                <td>${trigger.price ? trigger.price.toFixed(2) : '--'}</td>
            `;
            tableBody.appendChild(row);
        });
    }

    updateConnectionStatus(status) {
        const element = document.getElementById('connection-status');
        element.innerHTML = `
            <span class="status-indicator ${status}">
                <span class="status-dot"></span>
                ${status === 'online' ? '已连接' : '连接断开'}
            </span>
        `;
    }

    showPositionsError() {
        const loadingElement = document.getElementById('positions-loading');
        const contentElement = document.getElementById('positions-content');
        const noPositionsElement = document.getElementById('no-positions');

        loadingElement.style.display = 'none';
        contentElement.style.display = 'none';
        noPositionsElement.style.display = 'block';
        noPositionsElement.textContent = '数据加载失败';
    }

    showStrategyError() {
        const loadingElement = document.getElementById('strategy-status-display');
        if (loadingElement) {
            loadingElement.innerHTML = '<div style="color: var(--error-color);">策略状态加载失败</div>';
        }
    }

    showTriggersError() {
        const loadingElement = document.getElementById('triggers-loading');
        const contentElement = document.getElementById('triggers-content');
        const noTriggersElement = document.getElementById('no-triggers');

        loadingElement.style.display = 'none';
        contentElement.style.display = 'none';
        noTriggersElement.style.display = 'block';
        noTriggersElement.textContent = '数据加载失败';
    }

    // 工具函数
    formatNumber(value) {
        if (value === null || value === undefined || value === 0) return '--';
        return parseFloat(value).toFixed(2);
    }

    formatCurrency(value) {
        if (value === null || value === undefined || value === 0) return '--';
        return parseFloat(value).toFixed(0);
    }

    async updateAccountInfo() {
        try {
            const response = await fetch('/api/v1/trading/account');
            if (!response.ok) throw new Error('账户信息获取失败');

            const result = await response.json();
            if (result.success && result.data && result.data.response) {
                // 解析ServiceClient包装的响应
                const innerData = JSON.parse(result.data.response);
                if (innerData.success && innerData.data) {
                    this.displayAccountInfo(innerData.data);
                }
            }
        } catch (error) {
            console.error('❌ 账户信息更新失败:', error);
            this.showAccountError();
        }
    }

    displayAccountInfo(account) {
        // 主要指标
        const balance = account.balance || 0;
        const available = account.available || 0;
        const margin = account.margin || 0;
        const closeProfit = account.close_profit || 0;
        const preBalance = account.pre_balance || 0;
        const frozen = account.frozen || 0;
        const commission = account.commission || 0;

        // 更新主要指标
        document.getElementById('account-balance').textContent = this.formatCurrency(balance);
        document.getElementById('available-funds').textContent = this.formatCurrency(available);
        document.getElementById('margin-used').textContent = this.formatCurrency(margin);

        const pnlElement = document.getElementById('total-pnl-display');
        pnlElement.textContent = this.formatCurrency(closeProfit);

        // 根据盈亏设置颜色
        if (closeProfit > 0) {
            pnlElement.style.color = 'var(--success-color)';
            pnlElement.className = 'metric-value positive';
        } else if (closeProfit < 0) {
            pnlElement.style.color = 'var(--error-color)';
            pnlElement.className = 'metric-value negative';
        } else {
            pnlElement.style.color = 'var(--text-primary)';
            pnlElement.className = 'metric-value';
        }

        // 更新详细信息 - 资金状况
        document.getElementById('pre-balance').textContent = this.formatCurrency(preBalance);
        document.getElementById('frozen-funds').textContent = this.formatCurrency(frozen);
        document.getElementById('commission').textContent = this.formatCurrency(commission);

        // 风险控制指标 - 使用API返回的计算值或自己计算
        const riskRatio = account.risk_ratio || (balance > 0 ? (margin / balance * 100) : 0);
        const marginRatio = account.margin_ratio || (available > 0 ? (margin / available * 100) : 0);
        const availableLots = account.available_lots || this.calculateAvailableLots(available);

        document.getElementById('risk-ratio').textContent = riskRatio.toFixed(2) + '%';
        document.getElementById('margin-ratio').textContent = marginRatio.toFixed(2) + '%';
        document.getElementById('available-lots').textContent = availableLots + ' 手';

        // 盈亏统计 - 使用API返回的完整数据
        const realizedPnl = account.realized_pnl || closeProfit;
        const unrealizedPnl = account.unrealized_pnl || 0;
        const dailyPnl = account.daily_pnl || (balance - preBalance);

        this.updatePnlDisplay('realized-pnl', realizedPnl);
        this.updatePnlDisplay('unrealized-pnl', unrealizedPnl);
        this.updatePnlDisplay('daily-pnl', dailyPnl);

        // 更新变化指示
        this.updateChangeIndicators(account);

        // 记录完整账户信息用于调试
        console.log('📊 完整账户信息:', account);
    }

    updatePnlDisplay(elementId, value) {
        const element = document.getElementById(elementId);
        element.textContent = this.formatCurrency(value);

        if (value > 0) {
            element.className = 'detail-value positive';
        } else if (value < 0) {
            element.className = 'detail-value negative';
        } else {
            element.className = 'detail-value';
        }
    }

    calculateAvailableLots(available) {
        // 简化计算，假设每手需要保证金10000元
        const marginPerLot = 10000;
        return Math.floor(available / marginPerLot);
    }

    updateChangeIndicators(account) {
        // 这里可以添加与上次数据的比较逻辑
        // 暂时显示静态内容
        const changeElements = ['balance-change', 'available-change', 'margin-change', 'pnl-change'];
        changeElements.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = '--';
                element.className = 'metric-change';
            }
        });
    }

    showAccountError() {
        // 主要指标
        document.getElementById('account-balance').textContent = '--';
        document.getElementById('available-funds').textContent = '--';
        document.getElementById('margin-used').textContent = '--';
        document.getElementById('total-pnl-display').textContent = '--';

        // 详细信息
        const detailIds = [
            'pre-balance', 'frozen-funds', 'commission',
            'risk-ratio', 'margin-ratio', 'available-lots',
            'realized-pnl', 'unrealized-pnl', 'daily-pnl'
        ];

        detailIds.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = '--';
                element.className = 'detail-value';
            }
        });

        // 变化指示
        const changeIds = ['balance-change', 'available-change', 'margin-change', 'pnl-change'];
        changeIds.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = '--';
                element.className = 'metric-change';
            }
        });
    }
}

// 全局函数
async function submitOrder(direction) {
    const symbol = document.getElementById('symbol').value;
    const volume = parseInt(document.getElementById('volume').value);
    const resultElement = document.getElementById('order-result');

    if (!symbol || !volume || volume <= 0) {
        showOrderResult('请输入有效的合约代码和交易数量', 'error');
        return;
    }

    showOrderResult('正在提交订单...', 'info');

    try {
        const response = await fetch('/api/v1/trading/manual_order', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                symbol: symbol,
                direction: direction,
                volume: volume,
                order_type: 'MARKET'
            })
        });

        const result = await response.json();

        if (result.success) {
            showOrderResult(`✅ 订单提交成功！订单ID: ${result.data.order_id}`, 'success');
            // 刷新持仓数据
            if (window.tradingManager) {
                setTimeout(() => window.tradingManager.updatePositions(), 1000);
            }
        } else {
            showOrderResult(`❌ 订单提交失败: ${result.message}`, 'error');
        }
    } catch (error) {
        console.error('❌ 订单提交失败:', error);
        showOrderResult(`❌ 订单提交失败: ${error.message}`, 'error');
    }
}

function showOrderResult(message, type) {
    const resultElement = document.getElementById('order-result');
    resultElement.style.display = 'block';
    resultElement.textContent = message;

    // 设置样式
    if (type === 'success') {
        resultElement.style.background = 'rgba(82, 196, 26, 0.1)';
        resultElement.style.color = 'var(--success-color)';
        resultElement.style.border = '1px solid var(--success-color)';
    } else if (type === 'error') {
        resultElement.style.background = 'rgba(255, 77, 79, 0.1)';
        resultElement.style.color = 'var(--error-color)';
        resultElement.style.border = '1px solid var(--error-color)';
    } else {
        resultElement.style.background = 'rgba(24, 144, 255, 0.1)';
        resultElement.style.color = 'var(--primary-color)';
        resultElement.style.border = '1px solid var(--primary-color)';
    }

    // 3秒后自动隐藏成功消息
    if (type === 'success') {
        setTimeout(() => {
            resultElement.style.display = 'none';
        }, 3000);
    }
}

// 旧的closePosition函数已删除，现在使用智能平仓对话框

function refreshPositions() {
    console.log('🔄 手动刷新持仓数据...');
    if (window.tradingManager) {
        window.tradingManager.updatePositions();
    }
}

async function startStrategy() {
    try {
        const response = await fetch('/api/v1/trading/strategy/shfe_quant/start', {
            method: 'POST'
        });
        const result = await response.json();

        if (result.success) {
            alert('✅ 策略启动成功！');
            if (window.tradingManager) {
                window.tradingManager.updateStrategyStatus();
            }
        } else {
            alert(`❌ 策略启动失败: ${result.message}`);
        }
    } catch (error) {
        console.error('❌ 策略启动失败:', error);
        alert(`❌ 策略启动失败: ${error.message}`);
    }
}

async function stopStrategy() {
    if (!confirm('确定要停止策略吗？')) {
        return;
    }

    try {
        const response = await fetch('/api/v1/trading/strategy/shfe_quant/stop', {
            method: 'POST'
        });
        const result = await response.json();

        if (result.success) {
            alert('✅ 策略停止成功！');
            if (window.tradingManager) {
                window.tradingManager.updateStrategyStatus();
            }
        } else {
            alert(`❌ 策略停止失败: ${result.message}`);
        }
    } catch (error) {
        console.error('❌ 策略停止失败:', error);
        alert(`❌ 策略停止失败: ${error.message}`);
    }
}

async function closeAllPositions() {
    if (!confirm('⚠️ 确定要平掉所有持仓吗？这个操作不可撤销！')) {
        return;
    }

    try {
        // 获取当前持仓
        const response = await fetch('/api/v1/trading/positions');
        const result = await response.json();

        if (!result.success || !result.data) {
            alert('当前没有持仓需要平仓');
            return;
        }

        // 使用TradingManager的当前持仓数据（已经解析过的）
        const positions = window.tradingManager?.currentPositions || [];
        if (positions.length === 0) {
            alert('当前没有持仓需要平仓');
            return;
        }

        let successCount = 0;
        let failCount = 0;

        // 逐个平仓 - 使用智能平仓逻辑
        for (const position of positions) {
            if (position.volume === 0) continue;

            try {
                // 使用前端智能平仓逻辑
                const closeResult = await smartClosePosition(
                    position.symbol || TRADING_CONFIG.DEFAULT_SYMBOL,
                    position.direction,
                    position.volume,
                    position.today_volume || 0,
                    position.yd_volume || 0
                );

                if (closeResult.orders.length > 0) {
                    successCount++;
                } else {
                    failCount++;
                }
            } catch (error) {
                failCount++;
            }
        }

        alert(`平仓完成！成功: ${successCount}, 失败: ${failCount}`);

        // 刷新持仓数据
        if (window.tradingManager) {
            setTimeout(() => window.tradingManager.updatePositions(), 1000);
        }
    } catch (error) {
        console.error('❌ 全部平仓失败:', error);
        alert(`❌ 全部平仓失败: ${error.message}`);
    }
}

async function emergencyStop() {
    if (!confirm('⚠️ 确定要执行紧急停止吗？这将停止所有交易活动！')) {
        return;
    }

    try {
        const response = await fetch('/api/v1/trading/emergency_stop', {
            method: 'POST'
        });
        const result = await response.json();

        if (result.success) {
            alert('✅ 紧急停止执行成功！所有交易活动已停止。');
        } else {
            alert(`❌ 紧急停止执行失败: ${result.message}`);
        }
    } catch (error) {
        console.error('❌ 紧急停止失败:', error);
        alert(`❌ 紧急停止执行失败: ${error.message}`);
    }
}



// 页面可见性变化处理
document.addEventListener('visibilitychange', () => {
    if (window.tradingManager) {
        if (document.hidden) {
            window.tradingManager.stopAutoUpdate();
        } else {
            window.tradingManager.startAutoUpdate();
        }
    }
});

// 用户登录/退出功能
function logout() {
    if (confirm('确定要退出登录吗？')) {
        console.log('🚪 用户退出登录...');
        // 这里可以实现实际的退出逻辑
        // 比如清除token、跳转到登录页面等
        alert('退出登录功能开发中...');
        // window.location.href = '/login';
    }
}

// 合约切换功能
function onSymbolChange() {
    const currentSymbol = TRADING_CONFIG.getCurrentSymbol();
    console.log('📈 切换合约到:', currentSymbol);

    // 更新页面标题
    const marketSymbolElement = document.getElementById('market-symbol');
    if (marketSymbolElement) {
        marketSymbolElement.textContent = TRADING_CONFIG.getSymbolDisplayName(currentSymbol);
    }

    // 立即更新行情数据
    if (window.tradingManager) {
        window.tradingManager.updateMarketData();
        window.tradingManager.updatePositions();
    }
}

// 交易操作函数
function useMarketPrice() {
    document.getElementById('price-input').value = '';
    document.getElementById('price-input').placeholder = '市价单';
    console.log('💰 使用市价单');
}

// 这个函数已被移除，使用下面的submitOrder函数

async function pauseStrategy() {
    if (confirm('确定要暂停所有策略吗？')) {
        console.log('⏸️ 暂停策略...');
        try {
            const response = await fetch('/api/v1/trading/strategy/pause', {
                method: 'POST'
            });
            const result = await response.json();
            if (result.success) {
                alert('✅ 策略已暂停');
                updateStrategyStatus();
            } else {
                alert('❌ 暂停策略失败');
            }
        } catch (error) {
            console.error('❌ 暂停策略错误:', error);
            alert('❌ 暂停策略失败');
        }
    }
}

async function resumeStrategy() {
    if (confirm('确定要恢复所有策略吗？')) {
        console.log('▶️ 恢复策略...');
        try {
            const response = await fetch('/api/v1/trading/strategy/resume', {
                method: 'POST'
            });
            const result = await response.json();
            if (result.success) {
                alert('✅ 策略已恢复');
                updateStrategyStatus();
            } else {
                alert('❌ 恢复策略失败');
            }
        } catch (error) {
            console.error('❌ 恢复策略错误:', error);
            alert('❌ 恢复策略失败');
        }
    }
}

// 重复的closeAllPositions函数已删除

function updateStrategyStatus() {
    // 更新策略状态显示
    if (window.tradingManager) {
        window.tradingManager.updateStrategyStatus();
    }
}

// 平仓功能 - 全局变量存储当前平仓信息
let currentClosePosition = null;

// 打开平仓对话框
function closePosition(symbol, direction, totalVolume, positionDetail) {
    console.log('🔍 平仓对话框调用参数:', { symbol, direction, totalVolume, positionDetail });

    // 从当前持仓数据中获取详细信息
    const currentPositions = window.tradingManager?.currentPositions || [];
    console.log('🔍 当前持仓数据:', currentPositions);

    const position = currentPositions.find(p =>
        p.symbol === symbol && p.direction === direction
    );
    console.log('🔍 找到的持仓:', position);

    // 优先使用position中的今昨仓数据
    let todayVolume = 0;
    let yesterdayVolume = 0;

    if (position) {
        todayVolume = position.today_volume || 0;
        yesterdayVolume = position.yd_volume || 0;
    } else if (positionDetail) {
        todayVolume = positionDetail.today || 0;
        yesterdayVolume = positionDetail.yesterday || 0;
    } else {
        // 默认全部为昨仓
        todayVolume = 0;
        yesterdayVolume = totalVolume;
    }

    console.log('🔍 最终今昨仓数量:', { todayVolume, yesterdayVolume, totalVolume });

    currentClosePosition = {
        symbol,
        direction,
        totalVolume,
        todayVolume,
        yesterdayVolume
    };

    // 填充对话框信息
    document.getElementById('close-symbol').textContent = symbol;
    document.getElementById('close-direction').textContent = direction === 'LONG' ? '多头' : '空头';
    document.getElementById('close-total-volume').textContent = `${totalVolume}手`;

    // 显示今昨仓详情
    document.getElementById('close-today-volume').textContent = `${todayVolume}手`;
    document.getElementById('close-yesterday-volume').textContent = `${yesterdayVolume}手`;

    // 设置默认平仓数量
    const volumeInput = document.getElementById('close-volume');
    volumeInput.value = 1;
    volumeInput.max = totalVolume;

    // 显示模态框
    document.getElementById('close-position-modal').style.display = 'flex';
}

// 关闭模态框
function closeModal() {
    document.getElementById('close-position-modal').style.display = 'none';
    currentClosePosition = null;
}

// 设置平仓数量
function setCloseVolume(type) {
    if (!currentClosePosition) return;

    const volumeInput = document.getElementById('close-volume');
    const totalVolume = currentClosePosition.totalVolume;

    if (type === 'half') {
        volumeInput.value = Math.max(1, Math.floor(totalVolume / 2));
    } else if (type === 'all') {
        volumeInput.value = totalVolume;
    }
}

// 前端智能平仓逻辑
async function smartClosePosition(symbol, direction, volume, todayVolume, yesterdayVolume) {
    const orders = [];
    let remainingVolume = volume;

    console.log(`🎯 前端智能平仓: ${symbol} ${direction} 需平${volume}手, 今仓${todayVolume}手, 昨仓${yesterdayVolume}手`);

    // 第一步：优先平今仓
    if (todayVolume > 0 && remainingVolume > 0) {
        const todayCloseVolume = Math.min(remainingVolume, todayVolume);

        try {
            const response = await fetch('/api/v1/trading/simple_close', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    symbol: symbol,
                    direction: direction.toLowerCase(), // LONG -> long, SHORT -> short
                    volume: todayCloseVolume,
                    offset_type: 'TODAY',
                    order_type: 'MARKET'
                })
            });

            const result = await response.json();
            if (result.success) {
                orders.push(result.data);
                remainingVolume -= todayCloseVolume;
                console.log(`✅ 平今仓成功: ${todayCloseVolume}手, 剩余: ${remainingVolume}手`);
            } else {
                console.warn(`⚠️ 平今仓失败: ${result.message}`);
            }
        } catch (error) {
            console.error(`❌ 平今仓异常:`, error);
        }
    }

    // 第二步：平昨仓
    if (yesterdayVolume > 0 && remainingVolume > 0) {
        const yesterdayCloseVolume = Math.min(remainingVolume, yesterdayVolume);

        try {
            const response = await fetch('/api/v1/trading/simple_close', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    symbol: symbol,
                    direction: direction.toLowerCase(),
                    volume: yesterdayCloseVolume,
                    offset_type: 'YESTERDAY',
                    order_type: 'MARKET'
                })
            });

            const result = await response.json();
            if (result.success) {
                orders.push(result.data);
                remainingVolume -= yesterdayCloseVolume;
                console.log(`✅ 平昨仓成功: ${yesterdayCloseVolume}手, 剩余: ${remainingVolume}手`);
            } else {
                console.warn(`⚠️ 平昨仓失败: ${result.message}`);
            }
        } catch (error) {
            console.error(`❌ 平昨仓异常:`, error);
        }
    }

    return { orders, remainingVolume };
}

// 确认平仓
async function confirmClosePosition() {
    if (!currentClosePosition) return;

    const volume = parseInt(document.getElementById('close-volume').value);
    const { symbol, direction, totalVolume, todayVolume, yesterdayVolume } = currentClosePosition;

    // 验证输入
    if (isNaN(volume) || volume <= 0) {
        alert('❌ 请输入有效的平仓数量');
        return;
    }

    if (volume > totalVolume) {
        alert(`❌ 平仓数量不能超过持仓数量 (${totalVolume}手)`);
        return;
    }

    // 关闭模态框
    closeModal();

    console.log('📤 前端控制平仓:', { symbol, direction, volume, todayVolume, yesterdayVolume });

    try {
        // 使用前端智能平仓逻辑
        const result = await smartClosePosition(symbol, direction, volume, todayVolume || 0, yesterdayVolume || 0);

        if (result.orders.length > 0) {
            const successCount = result.orders.length;
            const totalClosed = volume - result.remainingVolume;
            alert(`✅ 平仓成功: ${symbol} ${direction === 'LONG' ? '多头' : '空头'} ${totalClosed}手 (发送${successCount}个订单)`);

            if (result.remainingVolume > 0) {
                alert(`⚠️ 还有${result.remainingVolume}手未能平仓`);
            }
        } else {
            alert(`❌ 平仓失败: 没有订单成功发送`);
        }

        // 刷新持仓数据
        if (window.tradingManager) {
            setTimeout(() => window.tradingManager.updatePositions(), 1000);
        }

    } catch (error) {
        console.error('❌ 平仓错误:', error);
        alert('❌ 平仓失败，请检查网络连接');
    }
}

// 刷新持仓
function refreshPositions() {
    if (window.tradingManager) {
        window.tradingManager.updatePositions();
    }
}

// 键盘事件处理
document.addEventListener('keydown', function(event) {
    // ESC键关闭模态框
    if (event.key === 'Escape') {
        closeModal();
    }

    // Enter键确认平仓（当模态框打开时）
    if (event.key === 'Enter' && currentClosePosition) {
        confirmClosePosition();
    }
});

// 点击模态框背景关闭
document.addEventListener('click', function(event) {
    const modal = document.getElementById('close-position-modal');
    if (event.target === modal) {
        closeModal();
    }
});

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', async function() {
    console.log('🚀 交易管理页面加载完成');

    try {
        // 首先加载合约配置
        console.log('📋 加载合约配置...');
        await TRADING_CONFIG.loadContractsConfig();

        // 更新合约选择器和显示
        console.log('🔄 更新合约选择器...');
        TRADING_CONFIG.updateSymbolSelector();

        // 创建交易管理器实例
        console.log('🎯 创建交易管理器...');
        window.tradingManager = new TradingManager();

        // 开始自动更新
        console.log('⏰ 开始自动更新...');
        window.tradingManager.startAutoUpdate();

        console.log('✅ 交易管理页面初始化完成');
    } catch (error) {
        console.error('❌ 交易管理页面初始化失败:', error);
    }
});


