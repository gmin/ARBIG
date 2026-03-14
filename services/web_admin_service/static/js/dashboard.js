/**
 * ARBIG 总控台 - 合并交易管理功能
 * 包含：行情、账户、持仓管理、智能平仓、策略触发记录
 */

class Dashboard {
    constructor() {
        this.updateInterval = 2000;
        this.isUpdating = false;
        this.mainContract = 'au2512';
        this.init();
    }

    async init() {
        console.log('ARBIG 总控台初始化...');
        await this.loadMainContract();
        this.bindEvents();
        await this.loadInitialData();
        this.startAutoUpdate();
    }

    // ========== 合约配置 ==========

    async loadMainContract() {
        try {
            const response = await fetch('/api/v1/trading/config/main_contract');
            if (response.ok) {
                const result = await response.json();
                if (result.success && result.data && result.data.main_contract) {
                    this.mainContract = result.data.main_contract;
                    this.supportedContracts = result.data.supported_contracts || [];
                    const el = document.getElementById('main-contract-symbol');
                    if (el) el.textContent = this.mainContract;
                }
            }
        } catch (error) {
            console.error('加载合约配置失败:', error);
        }
    }

    // ========== 事件绑定 & 自动刷新 ==========

    bindEvents() {
        window.addEventListener('beforeunload', () => this.stopAutoUpdate());
    }

    startAutoUpdate() {
        this.updateTimer = setInterval(() => {
            if (!this.isUpdating) this.updateData();
        }, this.updateInterval);
    }

    stopAutoUpdate() {
        if (this.updateTimer) clearInterval(this.updateTimer);
    }

    async loadInitialData() {
        await this.updateData();
    }

    async updateData() {
        if (this.isUpdating) return;
        this.isUpdating = true;
        try {
            await Promise.all([
                this.updateMarketData(),
                this.updatePositions(),
                this.updateAccountInfo(),
                this.updateSystemStatus(),
                this.updateTriggers()
            ]);
        } catch (error) {
            console.error('数据更新失败:', error);
        } finally {
            this.isUpdating = false;
        }
    }

    // ========== 行情数据 ==========

    async updateMarketData() {
        try {
            const response = await fetch('/api/v1/trading/ctp_status');
            if (response.ok) {
                const statusData = await response.json();
                if (statusData.success && statusData.data.tick_data && statusData.data.tick_data[this.mainContract]) {
                    this.displayMarketData(statusData.data.tick_data[this.mainContract]);
                    this.setMarketStatus('online');
                    return;
                }
            }
            // 回退：直接获取 tick
            const tickResp = await fetch(`/api/v1/trading/tick/${this.mainContract}`);
            if (tickResp.ok) {
                const tickResult = await tickResp.json();
                if (tickResult.success && tickResult.data && tickResult.data.response) {
                    const inner = JSON.parse(tickResult.data.response);
                    if (inner.success && inner.data) {
                        this.displayMarketData(inner.data);
                        this.setMarketStatus('online');
                        return;
                    }
                }
            }
            this.setMarketStatus('offline');
        } catch (error) {
            console.error('行情更新失败:', error);
            this.setMarketStatus('offline');
        }
    }

    displayMarketData(tick) {
        const lastPrice = tick.last_price || tick.current_price || 0;
        const bidPrice = tick.bid_price_1 || tick.bid_price || 0;
        const askPrice = tick.ask_price_1 || tick.ask_price || 0;
        const vol = tick.volume || 0;
        const bidVol = tick.bid_volume_1 || tick.bid_volume || 0;
        const askVol = tick.ask_volume_1 || tick.ask_volume || 0;

        this.setText('last-price', this.fmtNum(lastPrice));
        this.setText('bid-price', this.fmtNum(bidPrice));
        this.setText('ask-price', this.fmtNum(askPrice));
        this.setText('volume', vol.toLocaleString());
        this.setText('bid-volume', bidVol > 0 ? bidVol.toString() : '--');
        this.setText('ask-volume', askVol > 0 ? askVol.toString() : '--');

        const change = tick.pre_close_price
            ? ((lastPrice - tick.pre_close_price) / tick.pre_close_price * 100) : 0;
        const changeEl = document.getElementById('price-change');
        if (changeEl) {
            if (change > 0) {
                changeEl.textContent = `+${change.toFixed(2)}%`;
                changeEl.className = 'price-change price-up';
            } else if (change < 0) {
                changeEl.textContent = `${change.toFixed(2)}%`;
                changeEl.className = 'price-change price-down';
            } else {
                changeEl.textContent = '0.00%';
                changeEl.className = 'price-change';
            }
        }
    }

    setMarketStatus(status) {
        const el = document.getElementById('market-status');
        if (el) {
            el.className = `status-indicator ${status}`;
            el.innerHTML = `<span class="status-dot"></span>${status === 'online' ? '已连接' : '连接断开'}`;
        }
    }

    // ========== 账户信息 ==========

    async updateAccountInfo() {
        try {
            const response = await fetch('/api/v1/trading/account');
            if (!response.ok) throw new Error('获取失败');
            const result = await response.json();
            if (result.success && result.data && result.data.response) {
                const inner = JSON.parse(result.data.response);
                if (inner.success && inner.data) {
                    this.displayAccountInfo(inner.data);
                    return;
                }
            }
            this.showAccountError();
        } catch (error) {
            console.error('账户信息更新失败:', error);
            this.showAccountError();
        }
    }

    displayAccountInfo(account) {
        this.setText('account-balance', this.fmtCurrency(account.balance || 0));
        this.setText('available-funds', this.fmtCurrency(account.available || 0));
        this.setText('margin-used', this.fmtCurrency(account.margin || 0));

        const pnl = account.total_pnl || account.close_profit || 0;
        const pnlEl = document.getElementById('total-pnl-display');
        if (pnlEl) {
            pnlEl.textContent = this.fmtCurrency(pnl);
            pnlEl.style.color = pnl > 0 ? 'var(--success-color)' : pnl < 0 ? 'var(--error-color)' : 'var(--text-primary)';
        }
    }

    showAccountError() {
        ['account-balance', 'available-funds', 'margin-used', 'total-pnl-display'].forEach(id => this.setText(id, '--'));
    }

    // ========== 系统状态 ==========

    async updateSystemStatus() {
        try {
            const response = await fetch('/api/v1/trading/ctp_status');
            if (response.ok) {
                const result = await response.json();
                const data = result.success ? result.data : {};
                const ctpEl = document.getElementById('ctp-connection-status');
                if (ctpEl) {
                    const connected = data.trading_connected && data.market_connected;
                    ctpEl.textContent = connected ? '已连接' : '连接断开';
                    ctpEl.className = `status-value ${connected ? 'online' : 'offline'}`;
                }
            }
        } catch (error) {
            const ctpEl = document.getElementById('ctp-connection-status');
            if (ctpEl) { ctpEl.textContent = '连接断开'; ctpEl.className = 'status-value offline'; }
        }

        try {
            const resp = await fetch('/api/v1/system/status');
            const el = document.getElementById('trading-service-status');
            if (resp.ok) {
                const r = await resp.json();
                if (el) { el.textContent = r.success ? '运行中' : '异常'; el.className = `status-value ${r.success ? 'online' : 'offline'}`; }
            } else if (el) {
                el.textContent = '离线'; el.className = 'status-value offline';
            }
        } catch (error) {
            const el = document.getElementById('trading-service-status');
            if (el) { el.textContent = '离线'; el.className = 'status-value offline'; }
        }
    }

    // ========== 持仓管理 ==========

    async updatePositions() {
        try {
            const response = await fetch('/api/v1/trading/positions');
            if (!response.ok) throw new Error('获取失败');
            const result = await response.json();

            let arr = [];
            if (Array.isArray(result)) {
                arr = result.map(p => ({
                    symbol: p.symbol, direction: p.direction, volume: p.volume,
                    open_price: p.avg_price || p.open_price || 0,
                    current_price: p.current_price || 0,
                    unrealized_pnl: p.unrealized_pnl || 0
                }));
            } else if (result.success && result.data) {
                Object.keys(result.data).forEach(sym => {
                    const p = result.data[sym];
                    if (p.long_position > 0) arr.push({ symbol: sym, direction: 'LONG', volume: p.long_position, open_price: p.long_price, current_price: p.current_price || 0, unrealized_pnl: p.long_pnl || 0 });
                    if (p.short_position > 0) arr.push({ symbol: sym, direction: 'SHORT', volume: p.short_position, open_price: p.short_price, current_price: p.current_price || 0, unrealized_pnl: p.short_pnl || 0 });
                });
            }

            this.displayPositions(arr);
        } catch (error) {
            console.error('持仓更新失败:', error);
            this.showElement('positions-loading', false);
            this.showElement('positions-content', false);
            this.showElement('no-positions', true);
        }
    }

    displayPositions(positions) {
        this.showElement('positions-loading', false);
        if (!positions || positions.length === 0) {
            this.showElement('positions-content', false);
            this.showElement('no-positions', true);
            return;
        }
        this.showElement('positions-content', true);
        this.showElement('no-positions', false);

        const tbody = document.getElementById('positions-table');
        if (!tbody) return;
        tbody.innerHTML = '';

        positions.forEach(pos => {
            if (pos.volume === 0) return;
            const dir = pos.direction === 'LONG' ? '多头' : '空头';
            const pnl = pos.unrealized_pnl || 0;
            const pnlClass = pnl >= 0 ? 'price-up' : 'price-down';
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${pos.symbol}</td>
                <td>${dir}</td>
                <td>${pos.volume}</td>
                <td>${(pos.open_price || 0).toFixed(2)}</td>
                <td>${(pos.current_price || 0).toFixed(2)}</td>
                <td class="${pnlClass}">${pnl.toFixed(0)}</td>
            `;
            tbody.appendChild(row);
        });
    }

    // ========== 策略触发记录 ==========

    async updateTriggers() {
        try {
            const response = await fetch('/api/v1/trading/strategy/triggers?limit=10');
            if (!response.ok) throw new Error('获取失败');
            const result = await response.json();
            const triggers = (result.success && Array.isArray(result.data)) ? result.data : [];
            this.displayTriggers(triggers);
        } catch (error) {
            console.error('触发记录更新失败:', error);
            this.showElement('triggers-loading', false);
            this.showElement('triggers-content', false);
            this.showElement('no-triggers', true);
        }
    }

    displayTriggers(triggers) {
        this.showElement('triggers-loading', false);
        if (!triggers || triggers.length === 0) {
            this.showElement('triggers-content', false);
            this.showElement('no-triggers', true);
            return;
        }
        this.showElement('triggers-content', true);
        this.showElement('no-triggers', false);

        const tbody = document.getElementById('triggers-table');
        if (!tbody) return;
        tbody.innerHTML = '';
        triggers.forEach(t => {
            const row = document.createElement('tr');
            const time = t.timestamp ? new Date(t.timestamp).toLocaleTimeString() : '--';
            row.innerHTML = `
                <td>${time}</td>
                <td>${t.strategy_name || '--'}</td>
                <td>${t.signal_type || '--'}</td>
                <td>${t.direction || '--'}</td>
                <td>${t.volume || '--'}</td>
            `;
            tbody.appendChild(row);
        });
    }

    // ========== 工具方法 ==========

    fmtNum(v) { return (v == null || v === 0) ? '--' : parseFloat(v).toFixed(2); }
    fmtCurrency(v) { return (v == null || v === 0) ? '--' : parseFloat(v).toFixed(0); }

    setText(id, text) {
        const el = document.getElementById(id);
        if (el) el.textContent = text;
    }

    showElement(id, show) {
        const el = document.getElementById(id);
        if (el) el.style.display = show ? '' : 'none';
    }
}

// ========== 全局函数 ==========

function refreshPositions() {
    if (window.dashboard) window.dashboard.updatePositions();
}

function refreshData() {
    if (window.dashboard) window.dashboard.updateData();
}

async function emergencyStop() {
    if (!confirm('确定要执行紧急停止吗？这将停止所有交易活动！')) return;
    try {
        const resp = await fetch('/api/v1/trading/emergency_stop', { method: 'POST' });
        const r = await resp.json();
        alert(r.success ? '紧急停止执行成功' : '紧急停止失败: ' + (r.message || '未知错误'));
    } catch (error) {
        alert('紧急停止失败: ' + error.message);
    }
}

// ========== 页面初始化 ==========

document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new Dashboard();
});

document.addEventListener('visibilitychange', () => {
    if (window.dashboard) {
        if (document.hidden) window.dashboard.stopAutoUpdate();
        else window.dashboard.startAutoUpdate();
    }
});

