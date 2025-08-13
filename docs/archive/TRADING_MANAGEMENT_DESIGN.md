# ARBIG交易管理功能设计方案

## 项目概述

基于微服务架构的ARBIG量化交易系统，Web管理界面交易管理功能的详细设计方案。

## 功能模块设计

### 1. 系统管理（已完成）
- 查询和管理系统状态
- 服务启停控制
- 健康检查和监控

### 2. 交易管理（待实施）

#### 2.1 实时行情
**功能需求：**
- 主力合约实时价格显示
- 实时Tick数据推送
- 基础行情统计信息

**技术规格：**
- 合约范围：仅主力合约（如au2509）
- 推送方式：WebSocket订阅，有变动就推送
- 数据来源：Redis Stream
- 重连机制：递增间隔重连，最多5-10次

#### 2.2 仓位管理
**功能需求：**
- 当前持仓展示
- 实时盈亏计算
- 平仓操作（二次确认）

**技术规格：**
- 盈亏计算：`(当前价 - 成本价) × 持仓数量 × 1000`
- 合约乘数：1000克/手
- 更新频率：跟随行情实时更新
- 操作确认：平仓需要二次确认，不支持批量操作

#### 2.3 策略管理
**功能需求：**
- 策略启停控制
- 策略运行状态监控
- 策略触发记录查看

**技术规格：**
- 不支持热切换
- 参数修改需重启系统生效
- 不支持多策略并行
- 重点记录策略触发情况

#### 2.4 账户情况
**功能需求：**
- 账户资金状况
- 交易记录查询
- 资金曲线图

**技术规格：**
- 实时资金监控
- 历史交易记录
- 资金变化趋势图表

## 技术架构设计

### 数据流向架构
```
上期所 -> CTP -> 核心交易服务 -> Redis (行情数据)
                              -> MySQL (交易数据)
                              
Web服务 -> Redis (获取行情)
        -> 核心交易服务 (获取交易数据)
        
前端 -> Web服务 (API请求 + WebSocket)
```

### WebSocket实时推送设计

#### 推送策略
- **触发条件**：行情数据有变动就推送
- **数据格式**：根据CTP的Tick数据结构确定
- **推送内容**：价格、成交量、买卖盘口等

#### 重连机制
```
重连间隔：1s -> 2s -> 4s -> 8s -> 16s -> 30s -> 60s -> 120s -> 300s -> 600s
最多重连：5-10次后停止，需要手动刷新页面
连接状态：显示连接状态指示器
错误处理：记录连接错误日志
```

### 数据存储设计

#### MySQL表结构
```sql
-- 账户表
CREATE TABLE accounts (
    id INT PRIMARY KEY AUTO_INCREMENT,
    account_id VARCHAR(50) UNIQUE NOT NULL,
    balance DECIMAL(15,2) NOT NULL,
    available DECIMAL(15,2) NOT NULL,
    margin DECIMAL(15,2) NOT NULL,
    unrealized_pnl DECIMAL(15,2) DEFAULT 0,
    realized_pnl DECIMAL(15,2) DEFAULT 0,
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 持仓表
CREATE TABLE positions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    account_id VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    direction ENUM('long', 'short') NOT NULL,
    volume INT NOT NULL,
    avg_price DECIMAL(10,2) NOT NULL,
    current_price DECIMAL(10,2),
    unrealized_pnl DECIMAL(15,2),
    margin DECIMAL(15,2),
    open_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_account_symbol_direction (account_id, symbol, direction)
);

-- 交易记录表
CREATE TABLE trades (
    id INT PRIMARY KEY AUTO_INCREMENT,
    trade_id VARCHAR(50) UNIQUE NOT NULL,
    order_id VARCHAR(50) NOT NULL,
    account_id VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    direction ENUM('buy', 'sell') NOT NULL,
    volume INT NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    commission DECIMAL(10,2) DEFAULT 0,
    trade_time TIMESTAMP NOT NULL,
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 策略配置表
CREATE TABLE strategy_configs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    strategy_name VARCHAR(100) NOT NULL,
    config_data JSON NOT NULL,
    is_active BOOLEAN DEFAULT FALSE,
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 策略触发记录表（重要）
CREATE TABLE strategy_triggers (
    id INT PRIMARY KEY AUTO_INCREMENT,
    strategy_name VARCHAR(100) NOT NULL,
    trigger_time TIMESTAMP NOT NULL,
    trigger_condition TEXT NOT NULL,
    trigger_price DECIMAL(10,2),
    action_type ENUM('buy', 'sell', 'close', 'hold') NOT NULL,
    execution_result ENUM('success', 'failed', 'pending') NOT NULL,
    order_id VARCHAR(50),
    error_message TEXT,
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Redis数据结构
```
# 使用Stream存储行情数据
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

### 主力合约管理

#### 配置文件结构
```json
{
  "market_data": {
    "main_contract": "au2509",
    "contract_multiplier": 1000,
    "exchange": "SHFE",
    "last_update": "2025-08-06",
    "auto_subscribe": true
  }
}
```

#### 合约切换流程
1. Web界面输入新的主力合约代码
2. 更新配置文件
3. 重启行情订阅
4. 清空Redis中旧合约数据
5. 开始订阅新合约行情

### 页面设计架构

#### 多页面结构
```
/                    - 系统管理首页
/market             - 实时行情页面
/positions          - 仓位管理页面  
/account            - 账户情况页面
/strategy           - 策略管理页面
/trades             - 交易记录页面
```

#### 实时刷新区域
- **行情页面**：价格、成交量、盘口数据
- **仓位页面**：持仓盈亏、当前价格
- **账户页面**：资金余额、总盈亏
- **策略页面**：策略状态、最新触发记录

#### 图表需求
- **资金曲线图**：使用ECharts展示账户资金变化
- **实时价格图**：简单的分时图（可选）

## 系统约束和限制

### 功能限制
- 不支持多合约监控
- 不支持策略热切换
- 不支持多策略并行
- 不支持批量操作
- 不支持操作权限分级
- 不支持多用户同时使用
- 暂不考虑移动端访问

### 数据限制
- 历史行情数据不保存
- Redis只保存最新行情
- MySQL和Redis不需要数据同步

### 性能要求
- 行情推送延迟 < 100ms
- 页面响应时间 < 1s
- WebSocket连接稳定性 > 99%

## 实施计划

### 第一阶段：数据基础设施
1. 设计并创建MySQL表结构
2. 实现Redis Stream行情存储
3. 完善WebSocket推送机制
4. 实现主力合约配置管理

### 第二阶段：基础交易界面
1. 实时行情显示页面
2. 账户资金状况页面
3. 当前持仓信息页面
4. 基础的页面导航

### 第三阶段：交易操作功能
1. 平仓操作（带二次确认）
2. 策略启停控制
3. 策略触发记录查看
4. 系统紧急停止功能

### 第四阶段：历史数据和分析
1. 交易记录查询页面
2. 资金曲线图实现
3. 基础统计分析功能
4. 策略触发统计分析

## 风险控制

### 操作安全
- 重要操作需要二次确认
- 操作日志记录
- 错误状态提示

### 数据安全
- 数据库连接池管理
- Redis连接异常处理
- WebSocket连接状态监控

### 系统稳定性
- 服务异常自动恢复
- 数据获取失败降级处理
- 前端错误边界处理

## 技术栈

### 后端
- FastAPI (Web服务框架)
- MySQL (关系数据库)
- Redis (缓存和行情数据)
- WebSocket (实时推送)

### 前端
- HTML5 + CSS3 + JavaScript
- ECharts (图表库)
- WebSocket API (实时通信)
- Bootstrap (UI框架，可选)

### 部署
- vnpy conda环境
- 微服务架构
- 独立进程部署

---

**文档版本**: v1.0  
**创建时间**: 2025-08-06  
**最后更新**: 2025-08-06  
**状态**: 待实施
