// ARBIG Web管理界面工具函数

// API工具类
class APIClient {
    constructor(baseURL = '') {
        this.baseURL = baseURL;
    }

    async request(url, options = {}) {
        const fullURL = this.baseURL + url;
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
        };

        const finalOptions = { ...defaultOptions, ...options };

        try {
            const response = await fetch(fullURL, finalOptions);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || `HTTP error! status: ${response.status}`);
            }

            return data;
        } catch (error) {
            console.error('API请求失败:', error);
            throw error;
        }
    }

    async get(url) {
        return this.request(url, { method: 'GET' });
    }

    async post(url, data) {
        return this.request(url, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async put(url, data) {
        return this.request(url, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }

    async delete(url) {
        return this.request(url, { method: 'DELETE' });
    }
}

// WebSocket管理类
class WebSocketManager {
    constructor(url) {
        this.url = url;
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectInterval = 1000; // 初始重连间隔1秒
        this.listeners = new Map();
        this.isConnected = false;
    }

    connect() {
        try {
            this.ws = new WebSocket(this.url);
            
            this.ws.onopen = (event) => {
                console.log('WebSocket连接已建立');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                this.reconnectInterval = 1000;
                this.emit('connected', event);
            };

            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.emit('message', data);
                    
                    // 根据消息类型分发
                    if (data.type) {
                        this.emit(data.type, data);
                    }
                } catch (error) {
                    console.error('解析WebSocket消息失败:', error);
                }
            };

            this.ws.onclose = (event) => {
                console.log('WebSocket连接已关闭');
                this.isConnected = false;
                this.emit('disconnected', event);
                
                // 自动重连
                if (this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.scheduleReconnect();
                }
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket错误:', error);
                this.emit('error', error);
            };

        } catch (error) {
            console.error('WebSocket连接失败:', error);
            this.scheduleReconnect();
        }
    }

    scheduleReconnect() {
        this.reconnectAttempts++;
        console.log(`尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
        
        setTimeout(() => {
            this.connect();
        }, this.reconnectInterval);
        
        // 递增重连间隔
        this.reconnectInterval = Math.min(this.reconnectInterval * 2, 30000);
    }

    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        } else {
            console.warn('WebSocket未连接，无法发送消息');
        }
    }

    subscribe(topic) {
        this.send({
            type: 'subscribe',
            topic: topic
        });
    }

    unsubscribe(topic) {
        this.send({
            type: 'unsubscribe',
            topic: topic
        });
    }

    on(event, callback) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, []);
        }
        this.listeners.get(event).push(callback);
    }

    off(event, callback) {
        if (this.listeners.has(event)) {
            const callbacks = this.listeners.get(event);
            const index = callbacks.indexOf(callback);
            if (index > -1) {
                callbacks.splice(index, 1);
            }
        }
    }

    emit(event, data) {
        if (this.listeners.has(event)) {
            this.listeners.get(event).forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`事件处理器错误 (${event}):`, error);
                }
            });
        }
    }

    close() {
        if (this.ws) {
            this.ws.close();
        }
    }
}

// 工具函数
const Utils = {
    // 格式化数字
    formatNumber(num, decimals = 2) {
        if (num === null || num === undefined) return '--';
        return Number(num).toFixed(decimals);
    },

    // 格式化货币
    formatCurrency(amount, currency = 'CNY') {
        if (amount === null || amount === undefined) return '--';
        return new Intl.NumberFormat('zh-CN', {
            style: 'currency',
            currency: currency,
            minimumFractionDigits: 2
        }).format(amount);
    },

    // 格式化百分比
    formatPercent(value, decimals = 2) {
        if (value === null || value === undefined) return '--';
        return (value * 100).toFixed(decimals) + '%';
    },

    // 格式化时间
    formatTime(timestamp) {
        if (!timestamp) return '--';
        const date = new Date(timestamp);
        return date.toLocaleString('zh-CN');
    },

    // 格式化相对时间
    formatRelativeTime(timestamp) {
        if (!timestamp) return '--';
        const now = new Date();
        const date = new Date(timestamp);
        const diff = now - date;
        
        const seconds = Math.floor(diff / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);
        
        if (days > 0) return `${days}天前`;
        if (hours > 0) return `${hours}小时前`;
        if (minutes > 0) return `${minutes}分钟前`;
        return `${seconds}秒前`;
    },

    // 获取价格变化样式类
    getPriceChangeClass(change) {
        if (change > 0) return 'positive';
        if (change < 0) return 'negative';
        return 'neutral';
    },

    // 显示通知
    showNotification(message, type = 'info', duration = 3000) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        
        // 添加样式
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            border-radius: 5px;
            color: white;
            font-weight: 500;
            z-index: 10000;
            animation: slideIn 0.3s ease-out;
        `;
        
        // 根据类型设置背景色
        const colors = {
            info: '#17a2b8',
            success: '#28a745',
            warning: '#ffc107',
            error: '#dc3545'
        };
        notification.style.backgroundColor = colors[type] || colors.info;
        
        document.body.appendChild(notification);
        
        // 自动移除
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease-in';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, duration);
    },

    // 确认对话框
    confirm(message, callback) {
        if (window.confirm(message)) {
            callback();
        }
    },

    // 防抖函数
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    // 节流函数
    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
};

// 添加CSS动画
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// 导出到全局
window.APIClient = APIClient;
window.WebSocketManager = WebSocketManager;
window.Utils = Utils;
