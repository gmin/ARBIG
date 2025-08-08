# ARBIG数据库配置信息

## 数据库基本信息

### MySQL配置
- **主机**: localhost
- **端口**: 3306
- **用户名**: root
- **密码**: arbig123
- **数据库名**: arbig_trading
- **字符集**: utf8mb4
- **排序规则**: utf8mb4_unicode_ci

### Redis配置
- **主机**: localhost
- **端口**: 6379
- **数据库**: 0 (默认)
- **密码**: 无
- **服务状态**: 已安装并运行
- **安装路径**: /usr/bin/redis-server
- **配置文件**: /etc/redis/redis.conf (默认)
- **日志文件**: /var/log/redis/redis-server.log (默认)
- **数据目录**: /var/lib/redis (默认)

## 数据库表结构

### 核心业务表

#### 1. accounts (账户表)
```sql
CREATE TABLE accounts (
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
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
);
```

#### 2. positions (持仓表)
```sql
CREATE TABLE positions (
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
    UNIQUE KEY uk_account_symbol_direction (account_id, symbol, direction)
);
```

#### 3. orders (订单表)
```sql
CREATE TABLE orders (
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
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
);
```

#### 4. trades (交易记录表)
```sql
CREATE TABLE trades (
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
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
);
```

#### 5. strategy_configs (策略配置表)
```sql
CREATE TABLE strategy_configs (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    strategy_name VARCHAR(100) NOT NULL COMMENT '策略名称',
    strategy_class VARCHAR(100) NOT NULL COMMENT '策略类名',
    config_data JSON NOT NULL COMMENT '策略配置数据',
    is_active BOOLEAN DEFAULT FALSE COMMENT '是否激活',
    description TEXT COMMENT '策略描述',
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
);
```

#### 6. strategy_triggers (策略触发记录表) - 重要
```sql
CREATE TABLE strategy_triggers (
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
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
);
```

#### 7. system_logs (系统日志表)
```sql
CREATE TABLE system_logs (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    log_level ENUM('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL') NOT NULL COMMENT '日志级别',
    module VARCHAR(100) NOT NULL COMMENT '模块名称',
    message TEXT NOT NULL COMMENT '日志消息',
    details JSON COMMENT '详细信息',
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
);
```

### 数据库视图

#### 1. account_summary (账户总览视图)
```sql
CREATE VIEW account_summary AS
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
```

#### 2. daily_trade_summary (今日交易统计视图)
```sql
CREATE VIEW daily_trade_summary AS
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
```

#### 3. strategy_trigger_summary (策略触发统计视图)
```sql
CREATE VIEW strategy_trigger_summary AS
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
```

## Redis数据结构

### 行情数据存储 (Stream格式)
```
# 主力合约行情数据流
XADD market_data:au2509 * 
  timestamp 1691234567890
  last_price 450.50
  volume 1000
  bid_price 450.45
  ask_price 450.55
  bid_volume 10
  ask_volume 15
  high_price 451.00
  low_price 449.80
  open_price 450.00

# 获取最新行情
XREVRANGE market_data:au2509 + - COUNT 1

# 获取行情流
XREAD STREAMS market_data:au2509 $
```

## 初始化数据

### 默认账户
- **账户ID**: 123456789
- **初始余额**: 1,000,000.00 CNY
- **可用资金**: 800,000.00 CNY
- **保证金占用**: 200,000.00 CNY

### 默认策略配置
- **策略名称**: ArbitrageStrategy
- **策略类**: ArbitrageStrategy
- **配置参数**:
  ```json
  {
    "symbol": "au2509",
    "position_size": 1,
    "spread_threshold": 0.5,
    "stop_loss": 0.02,
    "take_profit": 0.05
  }
  ```

## 数据库操作命令

### MySQL操作
#### 连接数据库
```bash
mysql -u root -p'arbig123' arbig_trading
```

#### 创建数据库
```bash
mysql -u root -p'arbig123' -e "CREATE DATABASE IF NOT EXISTS arbig_trading DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

#### 执行SQL文件
```bash
mysql -u root -p'arbig123' arbig_trading < shared/database/schema.sql
```

#### 初始化数据库
```bash
conda activate vnpy
cd /root/ARBIG
python scripts/init_database.py
```

#### 查看表结构
```sql
USE arbig_trading;
SHOW TABLES;
DESCRIBE accounts;
SELECT COUNT(*) FROM accounts;
```

### Redis操作
#### 连接Redis
```bash
redis-cli
```

#### 查看Redis信息
```bash
redis-cli info
```

#### 查看所有键
```bash
redis-cli keys "*"
```

#### 查看行情数据流
```bash
# 查看主力合约行情流
redis-cli XREVRANGE market_data:au2509 + - COUNT 5

# 查看流信息
redis-cli XINFO STREAM market_data:au2509
```

#### 清空Redis数据
```bash
redis-cli FLUSHDB
```

#### Redis服务管理
```bash
# 启动Redis服务
sudo systemctl start redis

# 停止Redis服务
sudo systemctl stop redis

# 查看Redis状态
sudo systemctl status redis

# 重启Redis服务
sudo systemctl restart redis
```

## 备份和恢复

### 备份数据库
```bash
mysqldump -u root -p'arbig123' arbig_trading > arbig_trading_backup.sql
```

### 恢复数据库
```bash
mysql -u root -p'arbig123' arbig_trading < arbig_trading_backup.sql
```

## 安全注意事项

1. **密码安全**: 生产环境中应使用更强的密码
2. **用户权限**: 建议创建专用的数据库用户，而不是使用root
3. **网络安全**: 生产环境中应限制数据库访问IP
4. **数据备份**: 定期备份重要数据

## 性能优化

1. **索引优化**: 已为常用查询字段创建索引
2. **连接池**: 使用连接池管理数据库连接
3. **查询优化**: 使用视图简化复杂查询
4. **数据清理**: 定期清理过期的日志数据

---

**创建时间**: 2025-08-06  
**最后更新**: 2025-08-06  
**状态**: 已部署并验证
