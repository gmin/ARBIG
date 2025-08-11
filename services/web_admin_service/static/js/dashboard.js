// ARBIG Dashboard JavaScript
class Dashboard {
    constructor() {
        this.updateInterval = 2000; // 2秒更新一次
        this.isUpdating = false;
        this.mainContract = 'au2510'; // 默认值，将从配置加载
        this.init();
    }

    async init() {
        console.log('🚀 ARBIG Dashboard 初始化...');
        await this.loadMainContract();
        this.bindEvents();
        await this.loadInitialData();
        this.startAutoUpdate();
    }

    async loadMainContract() {
        try {
            const response = await fetch('/api/v1/trading/config/main_contract');
            if (response.ok) {
                const result = await response.json();
                if (result.success && result.data.main_contract) {
                    this.mainContract = result.data.main_contract;
                    console.log(`✅ 主力合约配置加载成功: ${this.mainContract}`);

                    // 更新页面显示
                    const symbolElement = document.getElementById('main-contract-symbol');
                    if (symbolElement) {
                        symbolElement.textContent = this.mainContract;
                    }
                }
            }
        } catch (error) {
            console.error('❌ 加载主力合约配置失败:', error);
        }
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
                this.updateSystemStatus(),
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
            // 优先从CTP状态接口获取数据，确保数据来源一致
            const response = await fetch('/api/v1/trading/ctp_status');
            if (response.ok) {
                const statusData = await response.json();
                if (statusData.success && statusData.data.tick_data && statusData.data.tick_data[this.mainContract]) {
                    const tick = statusData.data.tick_data[this.mainContract];
                    this.displayMarketData(tick);
                    this.updateMarketStatus('online');
                    return;
                }
            }

            // 如果状态接口失败，尝试直接API
            const tickResponse = await fetch(`/api/v1/trading/tick/${this.mainContract}`);
            if (tickResponse.ok) {
                const tickResult = await tickResponse.json();
                if (tickResult.success && tickResult.data && tickResult.data.response) {
                    // 解析ServiceClient包装的响应
                    const innerData = JSON.parse(tickResult.data.response);
                    if (innerData.success && innerData.data) {
                        const tick = innerData.data;
                        this.displayMarketData(tick);
                        this.updateMarketStatus('online');
                        return;
                    }
                }
            }

            throw new Error('无法获取行情数据');
        } catch (error) {
            console.error('❌ 行情数据更新失败:', error);
            this.updateMarketStatus('offline');
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
        document.getElementById('volume').textContent = volume.toLocaleString();

        // 显示买卖量（如果有的话）
        const bidVolumeElement = document.getElementById('bid-volume');
        const askVolumeElement = document.getElementById('ask-volume');
        if (bidVolumeElement) {
            bidVolumeElement.textContent = bidVolume > 0 ? bidVolume.toString() : '--';
        }
        if (askVolumeElement) {
            askVolumeElement.textContent = askVolume > 0 ? askVolume.toString() : '--';
        }

        // 计算价格变化（简化版）
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

            // 处理持仓数据格式 - API现在直接返回数组
            let positionsArray = [];
            if (Array.isArray(result)) {
                // API直接返回数组格式
                positionsArray = result.map(pos => ({
                    symbol: pos.symbol || this.mainContract,
                    direction: pos.direction,
                    volume: pos.volume,
                    open_price: pos.open_price || pos.avg_price,
                    current_price: pos.current_price || 0,
                    unrealized_pnl: pos.unrealized_pnl || 0
                }));
            } else if (result.success && result.data) {
                if (Array.isArray(result.data)) {
                    positionsArray = result.data.map(pos => ({
                        symbol: pos.symbol || this.mainContract,
                        direction: pos.direction,
                        volume: pos.volume,
                        open_price: pos.open_price || pos.avg_price,
                        current_price: pos.current_price || 0,
                        unrealized_pnl: pos.unrealized_pnl || 0
                    }));
                } else {
                    // 兼容旧的对象格式
                    Object.keys(result.data).forEach(symbol => {
                        const pos = result.data[symbol];
                        if (pos.long_position > 0) {
                            positionsArray.push({
                                symbol: symbol,
                                direction: 'LONG',
                                volume: pos.long_position,
                                open_price: pos.long_price,
                                current_price: pos.current_price || 0,
                                unrealized_pnl: pos.long_pnl || 0
                            });
                        }
                        if (pos.short_position > 0) {
                            positionsArray.push({
                                symbol: symbol,
                                direction: 'SHORT',
                                volume: pos.short_position,
                                open_price: pos.short_price,
                                current_price: pos.current_price || 0,
                                unrealized_pnl: pos.short_pnl || 0
                            });
                        }
                    });
                }
            }

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
            this.updatePositionStats(0, 0);
            return;
        }

        // 显示持仓表格
        contentElement.style.display = 'block';
        noPositionsElement.style.display = 'none';

        // 清空表格
        tableBody.innerHTML = '';

        let totalPositions = 0;
        let totalPnl = 0;

        positions.forEach(position => {
            if (position.volume === 0) return; // 跳过空仓位

            const row = document.createElement('tr');
            const direction = position.direction === 'LONG' ? '多头' : '空头';
            const pnl = position.unrealized_pnl || 0;
            const pnlClass = pnl >= 0 ? 'price-up' : 'price-down';

            row.innerHTML = `
                <td>${direction}</td>
                <td>${position.volume}</td>
                <td>${(position.open_price || 0).toFixed(2)}</td>
                <td class="${pnlClass}">${pnl.toFixed(0)}</td>
            `;
            tableBody.appendChild(row);

            totalPositions += Math.abs(position.volume);
            totalPnl += pnl;
        });

        this.updatePositionStats(totalPositions, totalPnl);
    }

    updatePositionStats(totalPositions, totalPnl) {
        document.getElementById('total-positions').textContent = totalPositions;
        
        const pnlElement = document.getElementById('total-pnl');
        pnlElement.textContent = totalPnl.toFixed(0);
        
        const pnlChangeElement = document.getElementById('pnl-change');
        if (totalPnl > 0) {
            pnlChangeElement.textContent = '盈利';
            pnlChangeElement.className = 'stat-change positive';
        } else if (totalPnl < 0) {
            pnlChangeElement.textContent = '亏损';
            pnlChangeElement.className = 'stat-change negative';
        } else {
            pnlChangeElement.textContent = '持平';
            pnlChangeElement.className = 'stat-change';
        }
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

    async updateSystemStatus() {
        try {
            // 检查核心交易服务状态
            const tradingResponse = await fetch('/api/v1/system/status');
            const tradingResult = await tradingResponse.json();
            
            if (tradingResult.success) {
                this.updateServiceStatus('trading-service-status', 'online');
            } else {
                this.updateServiceStatus('trading-service-status', 'offline');
            }
        } catch (error) {
            console.error('❌ 系统状态更新失败:', error);
            this.updateServiceStatus('trading-service-status', 'offline');
        }
    }

    updateMarketStatus(status) {
        const element = document.getElementById('market-status');
        element.className = `status-indicator ${status}`;
        element.innerHTML = `
            <span class="status-dot"></span>
            ${status === 'online' ? '已连接' : '连接断开'}
        `;
    }

    updateServiceStatus(elementId, status) {
        const element = document.getElementById(elementId);
        if (element) {
            element.className = `status-indicator ${status}`;
            element.innerHTML = `
                <span class="status-dot"></span>
                ${status === 'online' ? '运行中' : '离线'}
            `;
        }
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
        // 更新账户信息显示
        const balance = account.balance || 0;
        const available = account.available || 0;
        const margin = account.margin || 0;
        const closeProfit = account.close_profit || 0;

        document.getElementById('account-balance').textContent = this.formatCurrency(balance);
        document.getElementById('available-funds').textContent = this.formatCurrency(available);
        document.getElementById('margin-used').textContent = this.formatCurrency(margin);

        const pnlElement = document.getElementById('total-pnl-display');
        pnlElement.textContent = this.formatCurrency(closeProfit);

        // 根据盈亏设置颜色
        if (closeProfit > 0) {
            pnlElement.style.color = 'var(--success-color)';
        } else if (closeProfit < 0) {
            pnlElement.style.color = 'var(--error-color)';
        } else {
            pnlElement.style.color = 'var(--text-primary)';
        }
    }

    showAccountError() {
        document.getElementById('account-balance').textContent = '--';
        document.getElementById('available-funds').textContent = '--';
        document.getElementById('margin-used').textContent = '--';
        document.getElementById('total-pnl-display').textContent = '--';
    }
}

// 全局函数
function refreshData() {
    console.log('🔄 手动刷新数据...');
    if (window.dashboard) {
        window.dashboard.updateData();
    }
}

function viewLogs() {
    console.log('📋 查看日志...');
    // 可以实现日志查看功能
    alert('日志查看功能开发中...');
}

function emergencyStop() {
    if (confirm('⚠️ 确定要执行紧急停止吗？这将停止所有交易活动。')) {
        console.log('🛑 执行紧急停止...');
        fetch('/api/v1/system/emergency_stop', { method: 'POST' })
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    alert('✅ 紧急停止执行成功');
                } else {
                    alert('❌ 紧急停止执行失败: ' + result.message);
                }
            })
            .catch(error => {
                console.error('❌ 紧急停止失败:', error);
                alert('❌ 紧急停止执行失败');
            });
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new Dashboard();
});

// 页面可见性变化处理
document.addEventListener('visibilitychange', () => {
    if (window.dashboard) {
        if (document.hidden) {
            window.dashboard.stopAutoUpdate();
        } else {
            window.dashboard.startAutoUpdate();
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
