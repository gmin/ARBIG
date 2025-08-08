-- ARBIG量化交易系统数据库表结构
-- 创建时间: 2025-08-06
-- 版本: v1.0

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS arbig_trading DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE arbig_trading;

-- 账户表
CREATE TABLE IF NOT EXISTS accounts (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    account_id VARCHAR(50) UNIQUE NOT NULL COMMENT '账户ID',
    balance DECIMAL(15,2) NOT NULL DEFAULT 0 COMMENT '账户余额',
    available DECIMAL(15,2) NOT NULL DEFAULT 0 COMMENT '可用资金',
    margin DECIMAL(15,2) NOT NULL DEFAULT 0 COMMENT '保证金占用',
    unrealized_pnl DECIMAL(15,2) DEFAULT 0 COMMENT '未实现盈亏',
    realized_pnl DECIMAL(15,2) DEFAULT 0 COMMENT '已实现盈亏',
    currency VARCHAR(10) DEFAULT 'CNY' COMMENT '币种',
    risk_ratio DECIMAL(5,4) DEFAULT 0 COMMENT '风险度',
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_account_id (account_id),
    INDEX idx_update_time (update_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='账户信息表';

-- 持仓表
CREATE TABLE IF NOT EXISTS positions (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    account_id VARCHAR(50) NOT NULL COMMENT '账户ID',
    symbol VARCHAR(20) NOT NULL COMMENT '合约代码',
    direction ENUM('long', 'short') NOT NULL COMMENT '持仓方向',
    volume INT NOT NULL DEFAULT 0 COMMENT '持仓数量',
    avg_price DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '平均成本价',
    current_price DECIMAL(10,2) DEFAULT 0 COMMENT '当前价格',
    unrealized_pnl DECIMAL(15,2) DEFAULT 0 COMMENT '未实现盈亏',
    margin DECIMAL(15,2) DEFAULT 0 COMMENT '保证金占用',
    open_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '开仓时间',
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_account_symbol_direction (account_id, symbol, direction),
    INDEX idx_account_id (account_id),
    INDEX idx_symbol (symbol),
    INDEX idx_update_time (update_time),
    FOREIGN KEY (account_id) REFERENCES accounts(account_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='持仓信息表';

-- 订单表
CREATE TABLE IF NOT EXISTS orders (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    order_id VARCHAR(50) UNIQUE NOT NULL COMMENT '订单ID',
    account_id VARCHAR(50) NOT NULL COMMENT '账户ID',
    symbol VARCHAR(20) NOT NULL COMMENT '合约代码',
    direction ENUM('buy', 'sell') NOT NULL COMMENT '买卖方向',
    order_type ENUM('market', 'limit', 'stop', 'stop_limit') NOT NULL DEFAULT 'limit' COMMENT '订单类型',
    volume INT NOT NULL COMMENT '订单数量',
    price DECIMAL(10,2) COMMENT '订单价格',
    filled_volume INT DEFAULT 0 COMMENT '已成交数量',
    avg_price DECIMAL(10,2) DEFAULT 0 COMMENT '平均成交价',
    status ENUM('pending', 'partial_filled', 'filled', 'cancelled', 'rejected') NOT NULL DEFAULT 'pending' COMMENT '订单状态',
    order_time TIMESTAMP NOT NULL COMMENT '下单时间',
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_order_id (order_id),
    INDEX idx_account_id (account_id),
    INDEX idx_symbol (symbol),
    INDEX idx_status (status),
    INDEX idx_order_time (order_time),
    FOREIGN KEY (account_id) REFERENCES accounts(account_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='订单信息表';

-- 交易记录表
CREATE TABLE IF NOT EXISTS trades (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    trade_id VARCHAR(50) UNIQUE NOT NULL COMMENT '成交ID',
    order_id VARCHAR(50) NOT NULL COMMENT '订单ID',
    account_id VARCHAR(50) NOT NULL COMMENT '账户ID',
    symbol VARCHAR(20) NOT NULL COMMENT '合约代码',
    direction ENUM('buy', 'sell') NOT NULL COMMENT '买卖方向',
    volume INT NOT NULL COMMENT '成交数量',
    price DECIMAL(10,2) NOT NULL COMMENT '成交价格',
    commission DECIMAL(10,2) DEFAULT 0 COMMENT '手续费',
    trade_time TIMESTAMP NOT NULL COMMENT '成交时间',
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_trade_id (trade_id),
    INDEX idx_order_id (order_id),
    INDEX idx_account_id (account_id),
    INDEX idx_symbol (symbol),
    INDEX idx_trade_time (trade_time),
    FOREIGN KEY (account_id) REFERENCES accounts(account_id) ON DELETE CASCADE,
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='交易记录表';

-- 策略配置表
CREATE TABLE IF NOT EXISTS strategy_configs (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    strategy_name VARCHAR(100) NOT NULL COMMENT '策略名称',
    strategy_class VARCHAR(100) NOT NULL COMMENT '策略类名',
    config_data JSON NOT NULL COMMENT '策略配置数据',
    is_active BOOLEAN DEFAULT FALSE COMMENT '是否激活',
    description TEXT COMMENT '策略描述',
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_strategy_name (strategy_name),
    INDEX idx_is_active (is_active),
    INDEX idx_update_time (update_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='策略配置表';

-- 策略触发记录表（重要）
CREATE TABLE IF NOT EXISTS strategy_triggers (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    strategy_name VARCHAR(100) NOT NULL COMMENT '策略名称',
    trigger_time TIMESTAMP NOT NULL COMMENT '触发时间',
    trigger_condition TEXT NOT NULL COMMENT '触发条件描述',
    trigger_price DECIMAL(10,2) COMMENT '触发时价格',
    signal_type ENUM('buy', 'sell', 'close_long', 'close_short', 'hold') NOT NULL COMMENT '信号类型',
    action_type ENUM('buy', 'sell', 'close', 'hold') NOT NULL COMMENT '执行动作',
    execution_result ENUM('success', 'failed', 'pending', 'ignored') NOT NULL COMMENT '执行结果',
    order_id VARCHAR(50) COMMENT '关联订单ID',
    volume INT COMMENT '操作数量',
    error_message TEXT COMMENT '错误信息',
    execution_time TIMESTAMP COMMENT '执行时间',
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_strategy_name (strategy_name),
    INDEX idx_trigger_time (trigger_time),
    INDEX idx_signal_type (signal_type),
    INDEX idx_execution_result (execution_result),
    INDEX idx_create_time (create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='策略触发记录表';

-- 系统日志表
CREATE TABLE IF NOT EXISTS system_logs (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    log_level ENUM('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL') NOT NULL COMMENT '日志级别',
    module VARCHAR(100) NOT NULL COMMENT '模块名称',
    message TEXT NOT NULL COMMENT '日志消息',
    details JSON COMMENT '详细信息',
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_log_level (log_level),
    INDEX idx_module (module),
    INDEX idx_create_time (create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统日志表';

-- 插入默认数据

-- 插入默认账户（示例）
INSERT IGNORE INTO accounts (account_id, balance, available, margin) 
VALUES ('123456789', 1000000.00, 800000.00, 200000.00);

-- 插入默认策略配置（示例）
INSERT IGNORE INTO strategy_configs (strategy_name, strategy_class, config_data, description) 
VALUES (
    'ArbitrageStrategy', 
    'ArbitrageStrategy',
    JSON_OBJECT(
        'symbol', 'au2509',
        'position_size', 1,
        'spread_threshold', 0.5,
        'stop_loss', 0.02,
        'take_profit', 0.05
    ),
    '套利策略 - 基于价差的套利交易'
);

-- 创建视图：账户总览
CREATE OR REPLACE VIEW account_summary AS
SELECT 
    a.account_id,
    a.balance,
    a.available,
    a.margin,
    a.unrealized_pnl,
    a.realized_pnl,
    a.risk_ratio,
    COUNT(p.id) as position_count,
    COALESCE(SUM(p.unrealized_pnl), 0) as total_position_pnl,
    a.update_time
FROM accounts a
LEFT JOIN positions p ON a.account_id = p.account_id AND p.volume > 0
GROUP BY a.account_id;

-- 创建视图：今日交易统计
CREATE OR REPLACE VIEW daily_trade_summary AS
SELECT 
    account_id,
    DATE(trade_time) as trade_date,
    COUNT(*) as trade_count,
    SUM(CASE WHEN direction = 'buy' THEN volume ELSE 0 END) as buy_volume,
    SUM(CASE WHEN direction = 'sell' THEN volume ELSE 0 END) as sell_volume,
    SUM(commission) as total_commission,
    MIN(trade_time) as first_trade_time,
    MAX(trade_time) as last_trade_time
FROM trades
GROUP BY account_id, DATE(trade_time);

-- 创建视图：策略触发统计
CREATE OR REPLACE VIEW strategy_trigger_summary AS
SELECT 
    strategy_name,
    DATE(trigger_time) as trigger_date,
    COUNT(*) as total_triggers,
    SUM(CASE WHEN execution_result = 'success' THEN 1 ELSE 0 END) as success_count,
    SUM(CASE WHEN execution_result = 'failed' THEN 1 ELSE 0 END) as failed_count,
    SUM(CASE WHEN signal_type IN ('buy', 'sell') THEN 1 ELSE 0 END) as signal_count,
    AVG(trigger_price) as avg_trigger_price
FROM strategy_triggers
GROUP BY strategy_name, DATE(trigger_time);

-- 显示表结构信息
SHOW TABLES;

-- 显示创建完成信息
SELECT 'ARBIG数据库表结构创建完成！' as message;
