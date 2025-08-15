/**
 * 交易日志管理JavaScript
 */

class TradingLogsManager {
    constructor() {
        this.logs = [];
        this.currentPage = 1;
        this.pageSize = 100;
        this.totalLogs = 0;
        this.filters = {
            strategy_name: '',
            log_type: '',
            start_date: '',
            end_date: '',
            limit: 100
        };
        
        this.init();
    }

    init() {
        console.log('交易日志管理器初始化...');
        
        // 绑定事件
        this.bindEvents();
        
        // 设置默认日期
        this.setDefaultDates();
        
        // 加载数据
        this.loadLogs();
        this.loadStats();
        
        // 定时更新
        this.startAutoRefresh();
        
        console.log('交易日志管理器初始化完成');
    }

    bindEvents() {
        // 刷新按钮
        document.getElementById('refresh-btn')?.addEventListener('click', () => {
            this.loadLogs();
            this.loadStats();
        });

        // 应用过滤按钮
        document.getElementById('apply-filter-btn')?.addEventListener('click', () => {
            this.applyFilters();
        });

        // 导出按钮
        document.getElementById('export-btn')?.addEventListener('click', () => {
            this.exportLogs();
        });

        // 清理按钮
        document.getElementById('clear-btn')?.addEventListener('click', () => {
            this.clearOldLogs();
        });

        // 分页按钮
        document.getElementById('prev-page-btn')?.addEventListener('click', () => {
            this.previousPage();
        });

        document.getElementById('next-page-btn')?.addEventListener('click', () => {
            this.nextPage();
        });

        // 模态框关闭
        document.querySelector('.close')?.addEventListener('click', () => {
            this.closeModal();
        });

        // 点击模态框外部关闭
        document.getElementById('log-detail-modal')?.addEventListener('click', (e) => {
            if (e.target.id === 'log-detail-modal') {
                this.closeModal();
            }
        });

        // 策略选择变化
        document.getElementById('filter-strategy')?.addEventListener('change', (e) => {
            const strategyName = e.target.value;
            if (strategyName) {
                this.loadStrategyPerformance(strategyName);
            }
        });
    }

    setDefaultDates() {
        const today = new Date();
        const yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);

        const startDateInput = document.getElementById('filter-start-date');
        const endDateInput = document.getElementById('filter-end-date');

        if (startDateInput) {
            startDateInput.value = yesterday.toISOString().split('T')[0];
        }
        if (endDateInput) {
            endDateInput.value = today.toISOString().split('T')[0];
        }
    }

    async loadLogs() {
        try {
            console.log('加载交易日志...');
            
            // 构建查询参数
            const params = new URLSearchParams();
            
            if (this.filters.strategy_name) {
                params.append('strategy_name', this.filters.strategy_name);
            }
            if (this.filters.log_type) {
                params.append('log_type', this.filters.log_type);
            }
            if (this.filters.start_date) {
                params.append('start_date', this.filters.start_date);
            }
            if (this.filters.end_date) {
                params.append('end_date', this.filters.end_date);
            }
            
            params.append('limit', this.filters.limit.toString());
            params.append('offset', ((this.currentPage - 1) * this.pageSize).toString());

            const response = await fetch(`/api/v1/trading/trading_logs/logs?${params}`);
            const result = await response.json();

            if (result.success) {
                this.logs = result.data.logs;
                this.totalLogs = result.data.total;
                this.renderLogsTable();
                this.updatePagination();
                console.log(`加载了 ${this.logs.length} 条日志`);
            } else {
                throw new Error(result.message || '加载日志失败');
            }

        } catch (error) {
            console.error('加载日志失败:', error);
            this.showNotification('加载日志失败: ' + error.message, 'error');
        }
    }

    async loadStats() {
        try {
            console.log('加载日志统计...');
            
            const response = await fetch('/api/v1/trading/trading_logs/logs/summary?days=1');
            const result = await response.json();

            if (result.success) {
                const summary = result.data.summary;
                
                // 更新今日统计
                document.getElementById('today-orders').textContent = summary.order || 0;
                document.getElementById('today-trades').textContent = summary.trade || 0;
                document.getElementById('today-errors').textContent = summary.error || 0;
                
                // 更新总数
                document.getElementById('total-logs').textContent = result.data.total_count || 0;
                
                console.log('统计数据加载完成');
            }

        } catch (error) {
            console.error('加载统计失败:', error);
        }
    }

    async loadStrategyPerformance(strategyName) {
        try {
            console.log('加载策略表现:', strategyName);
            
            const response = await fetch(`/api/v1/trading/trading_logs/performance/${strategyName}?days=7`);
            const result = await response.json();

            if (result.success && result.data.performance) {
                const perf = result.data.performance;
                
                const performanceHtml = `
                    <div class="performance-stats">
                        <div class="stat-row">
                            <span>总交易:</span>
                            <span>${perf.total_trades}</span>
                        </div>
                        <div class="stat-row">
                            <span>胜率:</span>
                            <span>${perf.win_rate}%</span>
                        </div>
                        <div class="stat-row">
                            <span>总盈亏:</span>
                            <span class="${perf.total_pnl >= 0 ? 'profit' : 'loss'}">${perf.total_pnl}</span>
                        </div>
                        <div class="stat-row">
                            <span>平均盈亏:</span>
                            <span class="${perf.avg_profit >= 0 ? 'profit' : 'loss'}">${perf.avg_profit}</span>
                        </div>
                    </div>
                `;
                
                document.getElementById('strategy-performance').innerHTML = performanceHtml;
            } else {
                document.getElementById('strategy-performance').innerHTML = '<p>暂无交易数据</p>';
            }

        } catch (error) {
            console.error('加载策略表现失败:', error);
            document.getElementById('strategy-performance').innerHTML = '<p>加载失败</p>';
        }
    }

    renderLogsTable() {
        const tbody = document.getElementById('logs-tbody');
        if (!tbody) return;

        if (this.logs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="10" class="text-center">暂无日志数据</td></tr>';
            return;
        }

        tbody.innerHTML = this.logs.map(log => {
            const time = new Date(log.timestamp).toLocaleString();
            const typeClass = this.getLogTypeClass(log.log_type);
            const statusClass = log.is_success ? 'success' : 'error';
            const statusText = log.is_success ? '成功' : '失败';
            
            return `
                <tr>
                    <td>${time}</td>
                    <td><span class="log-type ${typeClass}">${log.log_type}</span></td>
                    <td>${log.strategy_name || '--'}</td>
                    <td>${log.symbol || '--'}</td>
                    <td>${log.direction || '--'}</td>
                    <td>${log.volume || '--'}</td>
                    <td>${log.price || '--'}</td>
                    <td><span class="status ${statusClass}">${statusText}</span></td>
                    <td class="message-cell" title="${log.message || ''}">${this.truncateText(log.message || '', 30)}</td>
                    <td>
                        <button class="btn btn-outline btn-xs" onclick="tradingLogsManager.showLogDetail('${log.id}')">
                            详情
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
    }

    getLogTypeClass(logType) {
        const typeClasses = {
            'ORDER': 'order',
            'TRADE': 'trade',
            'SIGNAL': 'signal',
            'ERROR': 'error',
            'INFO': 'info'
        };
        return typeClasses[logType] || 'default';
    }

    truncateText(text, maxLength) {
        if (!text) return '';
        return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
    }

    showLogDetail(logId) {
        const log = this.logs.find(l => l.id == logId);
        if (!log) return;

        const detailHtml = `
            <div class="log-detail">
                <div class="detail-row">
                    <label>时间:</label>
                    <span>${new Date(log.timestamp).toLocaleString()}</span>
                </div>
                <div class="detail-row">
                    <label>类型:</label>
                    <span class="log-type ${this.getLogTypeClass(log.log_type)}">${log.log_type}</span>
                </div>
                <div class="detail-row">
                    <label>策略:</label>
                    <span>${log.strategy_name || '--'}</span>
                </div>
                <div class="detail-row">
                    <label>品种:</label>
                    <span>${log.symbol || '--'}</span>
                </div>
                <div class="detail-row">
                    <label>方向:</label>
                    <span>${log.direction || '--'}</span>
                </div>
                <div class="detail-row">
                    <label>数量:</label>
                    <span>${log.volume || '--'}</span>
                </div>
                <div class="detail-row">
                    <label>价格:</label>
                    <span>${log.price || '--'}</span>
                </div>
                <div class="detail-row">
                    <label>订单ID:</label>
                    <span>${log.order_id || '--'}</span>
                </div>
                <div class="detail-row">
                    <label>状态:</label>
                    <span class="status ${log.is_success ? 'success' : 'error'}">${log.is_success ? '成功' : '失败'}</span>
                </div>
                <div class="detail-row">
                    <label>消息:</label>
                    <span>${log.message || '--'}</span>
                </div>
                ${log.error_message ? `
                <div class="detail-row">
                    <label>错误信息:</label>
                    <span class="error">${log.error_message}</span>
                </div>
                ` : ''}
                ${log.details ? `
                <div class="detail-row">
                    <label>详细信息:</label>
                    <pre>${JSON.stringify(log.details, null, 2)}</pre>
                </div>
                ` : ''}
            </div>
        `;

        document.getElementById('log-detail-content').innerHTML = detailHtml;
        document.getElementById('log-detail-modal').style.display = 'block';
    }

    closeModal() {
        document.getElementById('log-detail-modal').style.display = 'none';
    }

    applyFilters() {
        // 获取过滤条件
        this.filters.strategy_name = document.getElementById('filter-strategy').value;
        this.filters.log_type = document.getElementById('filter-type').value;
        this.filters.start_date = document.getElementById('filter-start-date').value;
        this.filters.end_date = document.getElementById('filter-end-date').value;
        this.filters.limit = parseInt(document.getElementById('filter-limit').value);

        // 重置分页
        this.currentPage = 1;

        // 重新加载数据
        this.loadLogs();
        this.showNotification('过滤条件已应用', 'success');
    }

    updatePagination() {
        const totalPages = Math.ceil(this.totalLogs / this.pageSize);
        
        document.getElementById('pagination-info').textContent = 
            `显示 ${this.logs.length} 条记录，共 ${this.totalLogs} 条`;
        
        document.getElementById('page-info').textContent = 
            `第 ${this.currentPage} 页，共 ${totalPages} 页`;

        document.getElementById('prev-page-btn').disabled = this.currentPage <= 1;
        document.getElementById('next-page-btn').disabled = this.currentPage >= totalPages;
    }

    previousPage() {
        if (this.currentPage > 1) {
            this.currentPage--;
            this.loadLogs();
        }
    }

    nextPage() {
        const totalPages = Math.ceil(this.totalLogs / this.pageSize);
        if (this.currentPage < totalPages) {
            this.currentPage++;
            this.loadLogs();
        }
    }

    exportLogs() {
        this.showNotification('导出功能开发中...', 'info');
    }

    clearOldLogs() {
        if (confirm('确定要清理30天前的日志吗？此操作不可恢复。')) {
            this.showNotification('清理功能开发中...', 'info');
        }
    }

    startAutoRefresh() {
        // 每30秒自动刷新一次
        setInterval(() => {
            this.loadLogs();
        }, 30000);

        // 每分钟更新一次时间
        setInterval(() => {
            document.getElementById('current-time').textContent = new Date().toLocaleTimeString();
        }, 1000);
    }

    showNotification(message, type = 'info') {
        // 简单的通知实现
        console.log(`[${type.toUpperCase()}] ${message}`);
        
        // 可以在这里实现更复杂的通知UI
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            background: ${type === 'error' ? '#f56565' : type === 'success' ? '#48bb78' : '#4299e1'};
            color: white;
            border-radius: 4px;
            z-index: 1000;
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 3000);
    }
}

// 创建全局实例
const tradingLogsManager = new TradingLogsManager();
