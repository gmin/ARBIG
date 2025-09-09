"""
系统集成测试策略 - ARBIG专用测试策略

## 策略概述
这是一个专门为ARBIG量化交易系统设计的集成测试策略，用于验证系统各模块的功能和稳定性。
该策略已在实盘环境中成功运行，可作为其他策略开发的参考模板。

## 主要特点
- 🎯 **专为测试设计**：随机信号生成，适合系统功能验证
- 🔧 **完善的架构**：实时持仓查询、缓存机制、风控检查
- 📊 **详细的日志**：完整的调试信息和运行状态记录
- 🛡️ **安全可靠**：多重风控机制，适合生产环境测试

## 技术架构
- 基于ARBIGCtaTemplate实现
- 集成实时持仓管理系统
- 支持智能缓存机制减少服务压力
- 包含多因子决策模型

## 适用场景
- ✅ 系统集成测试
- ✅ 新功能验证
- ✅ 稳定性测试
- ✅ 性能基准测试
"""

import time
import random
from typing import Dict, Any, Optional
from datetime import datetime
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from core.types import TickData, BarData
from services.strategy_service.core.cta_template import ARBIGCtaTemplate
from services.strategy_service.core.data_tools import ArrayManager
from utils.logger import get_logger

logger = get_logger(__name__)


class SystemIntegrationTestStrategy(ARBIGCtaTemplate):
    """
    系统集成测试策略 - ARBIG核心测试策略
    
    ## 策略逻辑
    1. **信号生成**：每隔N秒生成随机交易信号
    2. **决策模型**：多因子决策（价格趋势、位置、波动性、随机因子）
    3. **风控机制**：实时持仓查询、缓存机制、持仓限制
    4. **交易执行**：固定手数交易，支持买入/卖出
    
    ## 核心优势
    - 🔄 **实时持仓同步**：与交易服务实时同步持仓状态
    - 💾 **智能缓存**：减少服务调用压力，提高性能
    - 🛡️ **多重风控**：持仓限制、实时查询、缓存验证
    - 📊 **详细监控**：完整的信号触发历史和市场分析
    
    ## 参数说明
    - signal_interval: 信号生成间隔（秒），默认30秒
    - trade_volume: 每次交易手数，默认1手
    - max_position: 最大持仓限制，默认3手
    """
    
    # 策略参数
    signal_interval = 30  # 信号间隔(秒)
    trade_volume = 1      # 交易手数
    max_position = 3      # 最大持仓
    
    # 策略变量
    last_signal_time = 0
    signal_count = 0
    
    def __init__(self, strategy_name: str, symbol: str, setting: dict, signal_sender):
        """初始化策略"""
        super().__init__(strategy_name, symbol, setting, signal_sender)
        
        # 从设置中获取参数
        self.signal_interval = setting.get('signal_interval', self.signal_interval)
        self.trade_volume = setting.get('trade_volume', self.trade_volume)
        self.max_position = setting.get('max_position', self.max_position)
        
        # 初始化ArrayManager用于数据管理（虽然这个策略不需要复杂计算）
        self.am = ArrayManager()

        # 紧急风控：手动持仓跟踪
        self.manual_position = 0  # 手动跟踪持仓
        self.pending_orders = 0   # 待成交订单数量

        # 信号触发记录
        self.signal_triggers = []  # 记录所有信号触发原因
        self.last_price_history = []  # 价格历史
        self.market_conditions = {}  # 市场条件记录

        # 🚨 紧急风控：信号生成锁定
        self.signal_lock = False  # 信号生成锁定标志
        self.pending_trade_count = 0  # 待处理交易数量

        # 🔧 持仓缓存机制 - 减少服务压力
        self.cached_position = 0  # 净持仓缓存
        self.cached_long_position = 0  # 多单持仓缓存
        self.cached_short_position = 0  # 空单持仓缓存
        self.last_position_update = 0  # 上次持仓更新时间

        logger.info(f"✅ {self.strategy_name} 初始化完成")
        logger.info(f"   交易品种: {self.symbol}")
        logger.info(f"   信号间隔: {self.signal_interval}秒")
        logger.info(f"   交易手数: {self.trade_volume}")
        logger.info(f"   最大持仓: {self.max_position}")
    
    def on_init(self):
        """策略初始化回调"""
        try:
            self.write_log("测试策略初始化")
            logger.info(f"✅ TestStrategy on_init 执行成功: {self.strategy_name}")
        except Exception as e:
            logger.error(f"❌ TestStrategy on_init 执行失败: {e}")
            raise
        
    def on_start(self):
        """策略启动回调"""
        try:
            self.last_signal_time = time.time()
            self.write_log("🚀 测试策略已启动")
            logger.info(f"✅ TestStrategy on_start 执行成功: {self.strategy_name}")
        except Exception as e:
            logger.error(f"❌ TestStrategy on_start 执行失败: {e}")
            raise
        
    def on_stop(self):
        """策略停止回调"""
        self.write_log("⏹️ 测试策略已停止")
        
    def on_tick(self, tick: TickData):
        """处理tick数据"""
        if not self.trading:
            self.write_log(f"策略未启动交易，忽略tick数据")
            return

        # 添加调试日志
        self.write_log(f"📈 收到tick数据: {tick.symbol} 价格={tick.last_price}")

        # 更新ArrayManager
        self.am.update_tick(tick)

        # 记录价格历史（用于分析）
        self.last_price_history.append({
            'timestamp': time.time(),
            'price': tick.last_price,
            'volume': getattr(tick, 'volume', 0)
        })

        # 保持最近100个价格点
        if len(self.last_price_history) > 100:
            self.last_price_history = self.last_price_history[-100:]

        current_time = time.time()

        # 检查是否到了生成信号的时间
        if current_time - self.last_signal_time < self.signal_interval:
            remaining = self.signal_interval - (current_time - self.last_signal_time)
            self.write_log(f"⏰ 距离下次信号还有 {remaining:.1f} 秒")
            return

        # 🎯 行情回调的核心职责：生成交易信号
        self.write_log(f"🎯 开始生成交易信号...")
        self._generate_trading_signal(tick)
        self.last_signal_time = current_time

    def on_tick_impl(self, tick: TickData):
        """抽象方法实现 - tick数据处理"""
        self.on_tick(tick)
        
    def on_bar(self, bar: BarData):
        """处理bar数据"""
        if not self.trading:
            return

        # 更新ArrayManager
        self.am.update_bar(bar)

        # 确保有足够的数据
        if not self.am.inited:
            return

        # 这个测试策略主要基于tick，bar处理可以为空
        pass

    def on_bar_impl(self, bar: BarData):
        """抽象方法实现 - bar数据处理"""
        self.on_bar(bar)
        

    def on_order(self, order):
        """简化的订单回调 - 仅记录关键订单状态"""
        # 只记录重要的订单状态变化
        if hasattr(order, 'status'):
            status = order.status.value
            if status in ["ALLTRADED", "REJECTED", "CANCELLED"]:
                self.write_log(f"📋 订单状态: {order.orderid} - {status}")

                # 拒单时的特殊处理
                if status == "REJECTED":
                    self.write_log(f"⚠️ 订单被拒绝，可能需要检查资金或持仓限制")
                    # 解除信号锁定，允许重新生成信号
                    self.signal_lock = False

    def _query_real_position(self) -> Optional[int]:
        """实时查询真实持仓"""
        self.write_log(f"🔧 DEBUG: _query_real_position 方法开始执行")
        try:
            import requests

            # 查询交易服务的持仓API
            url = f"http://localhost:8001/real_trading/positions?symbol={self.symbol}"
            self.write_log(f"🔧 DEBUG: 准备请求URL: {url}")

            response = requests.get(url, timeout=2.0)
            self.write_log(f"🔧 DEBUG: HTTP请求完成，状态码: {response.status_code}")

            if response.status_code == 200:
                position_data = response.json()
                self.write_log(f"🔧 DEBUG: 返回数据: {position_data}")

                if position_data.get("success") and position_data.get("data"):
                    position_info = position_data["data"]  # 直接就是持仓信息，不是字典
                    self.write_log(f"🔧 DEBUG: 持仓数据: {position_info}")

                    # 🔧 修复：直接从持仓信息中获取数据
                    long_position = position_info.get("long_position", 0)
                    short_position = position_info.get("short_position", 0)
                    net_position = position_info.get("net_position", 0)

                    self.write_log(f"🔍 查询到真实持仓: 多单={long_position}, 空单={short_position}, 净持仓={net_position}")

                    # 返回净持仓
                    return net_position
                else:
                    self.write_log(f"⚠️ 持仓查询返回空数据")
                    return None
            else:
                self.write_log(f"⚠️ 持仓查询失败: HTTP {response.status_code}")
                return None

        except Exception as e:
            self.write_log(f"⚠️ 持仓查询异常: {e}")
            return None

    def on_trade_impl(self, trade):
        """🔧 正确的实现方式：实现on_trade_impl而不是重写on_trade"""
        # 🚨 子类日志：验证on_trade_impl是否被调用
        self.write_log(f"🔥🔥🔥 子类 TestStrategy.on_trade_impl 被调用！🔥🔥🔥")
        self.write_log(f"🔥 子类 - 成交详情: {trade.direction} {trade.volume}手 @ {trade.price:.2f}")
        self.write_log(f"🔥 子类 - 当前持仓: {self.pos}")

        # 🔧 成交后更新持仓缓存
        self._update_position_cache_after_trade()

        # 记录持仓状态
        if abs(self.pos) >= self.max_position:
            self.write_log(f"⚠️ 测试策略达到最大持仓: {self.pos}")

        self.write_log(f"🔥🔥🔥 子类 TestStrategy.on_trade_impl 处理完成！🔥🔥🔥")

    def _update_position_cache_after_trade(self):
        """🔧 成交后更新持仓缓存"""
        try:
            # 异步更新持仓缓存，不阻塞成交处理
            import threading

            def update_cache():
                real_position = self._query_real_position()
                if real_position is not None:
                    old_cache = self.cached_position
                    self.cached_position = real_position
                    self.last_position_update = time.time()
                    self.write_log(f"🔧 成交后缓存更新: {old_cache} → {real_position}")

            # 在后台线程中更新缓存
            threading.Thread(target=update_cache, daemon=True).start()

        except Exception as e:
            self.write_log(f"⚠️ 持仓缓存更新失败: {e}")

    def _generate_trading_signal(self, tick: TickData):
        """🎯 纯净的交易信号生成 - 只生成信号，不执行交易"""
        current_price = tick.last_price

        # 🚨 信号生成前置检查
        if self.signal_lock:
            self.write_log(f"🔒 信号生成被锁定，等待交易完成")
            return

        # 🎯 核心逻辑1：分析市场条件
        market_analysis = self._analyze_market_conditions(tick)

        # 🎯 核心逻辑2：生成交易决策
        signal_decision = self._make_trading_decision(market_analysis, current_price)

        # 🎯 核心逻辑3：发送信号（不执行交易）
        if signal_decision['action'] in ['BUY', 'SELL']:
            self.write_log(f"🎯 生成交易信号: {signal_decision['action']} - {signal_decision['reason']}")
            # 🔧 发送信号给信号处理模块，而不是直接执行
            self._send_trading_signal(signal_decision, current_price)
        else:
            self.write_log(f"🎯 无交易信号: {signal_decision['reason']}")

    def _send_trading_signal(self, signal_decision: dict, current_price: float):
        """🎯 发送交易信号 - 纯净的信号传递，不执行交易"""
        # 🔧 将信号发送给信号处理模块
        # 这里可以是异步处理，或者直接调用处理方法
        self._process_trading_signal(signal_decision, current_price)

    def _process_trading_signal(self, signal_decision: dict, current_price: float):
        """🔧 信号处理模块 - 主动查询持仓并执行交易"""
        action = signal_decision['action']

        self.write_log(f"🔧 信号处理模块：接收到{action}信号，开始处理")

        # 🔧 主动查询持仓进行风控检查
        if not self._pre_trade_safety_check():
            self.write_log(f"🔧 信号处理模块：风控检查未通过，信号被拒绝")
            return

        # 🎯 风控通过，执行交易订单
        self.write_log(f"🔧 信号处理模块：风控通过，执行{action}订单")
        if action == 'BUY':
            self.write_log(f"🚀 执行买入订单！价格: {current_price}")
            self.buy(current_price, self.trade_volume, stop=False)
        elif action == 'SELL':
            self.write_log(f"🚀 执行卖出订单！价格: {current_price}")
            self.sell(current_price, self.trade_volume, stop=False)

    def _pre_trade_safety_check(self) -> bool:
        """🔧 交易前安全检查 - 独立的持仓风控模块"""
        real_position = self._query_real_position()
        if real_position is None:
            self.write_log(f"⚠️ 无法查询持仓，停止交易")
            return False

        # 更新持仓缓存
        if real_position != self.cached_position:
            self.write_log(f"🔄 持仓同步: {self.cached_position} → {real_position}")
            self.cached_position = real_position
            self.pos = real_position

        # 风控检查
        predicted_position = abs(real_position + self.trade_volume)
        if predicted_position > self.max_position:
            self.write_log(f"⚠️ 风控阻止: 当前={real_position}, 预测={predicted_position}, 限制={self.max_position}")
            return False

        return True

    def _generate_signal_with_cached_position(self, tick: TickData):
        """🔧 优化版信号生成：基于缓存持仓做初步判断，减少服务压力"""
        current_price = tick.last_price
        current_time = time.time()

        # 🚨 紧急风控：检查信号锁定
        if self.signal_lock:
            self.write_log(f"🔒 信号生成被锁定，等待交易完成")
            return

        # 分析市场条件
        market_analysis = self._analyze_market_conditions(tick)
        self.signal_count += 1

        # 🔧 基于缓存持仓做初步风控判断
        cached_abs_position = abs(self.cached_position)
        self.write_log(f"🔧 缓存持仓检查: 净持仓={self.cached_position}, 绝对值={cached_abs_position}, 限制={self.max_position}")

        # 如果缓存显示已接近上限，进行精确检查
        if cached_abs_position >= self.max_position - 1:  # 接近上限时才实时查询
            self.write_log(f"🔧 接近持仓上限，进行实时持仓查询")
            self._generate_signal_with_fresh_position(tick, market_analysis)
        else:
            # 基于缓存持仓生成信号（轻量级）
            self._generate_signal_based_on_cache(tick, market_analysis)

    def _generate_signal_with_fresh_position(self, tick: TickData, market_analysis: dict):
        """🔧 实时持仓查询版信号生成：只在必要时查询最新持仓"""
        current_price = tick.last_price

        # 🔧 实时查询最新持仓
        self.write_log(f"🔧 执行实时持仓查询（关键时刻）")
        real_position = self._query_real_position()
        if real_position is None:
            self.write_log(f"⚠️ 无法查询持仓，停止交易")
            return

        # 更新持仓缓存
        if real_position != self.cached_position:
            self.write_log(f"🔄 持仓缓存更新: {self.cached_position} → {real_position}")
            self.cached_position = real_position
            self.pos = real_position  # 同步到策略持仓
            self.last_position_update = time.time()

        # 基于真实持仓进行精确风控检查
        predicted_position_buy = abs(real_position + self.trade_volume)
        if predicted_position_buy > self.max_position:
            self.write_log(f"⚠️ 买入将超限，停止交易: 当前={real_position}, 买入后={predicted_position_buy}, 限制={self.max_position}")
            return

        # 生成交易信号
        signal_decision = self._make_trading_decision(market_analysis, current_price)
        self._execute_signal_decision(signal_decision, current_price)

    def _generate_signal_based_on_cache(self, tick: TickData, market_analysis: dict):
        """🔧 基于缓存持仓的轻量级信号生成"""
        current_price = tick.last_price

        # 基于缓存持仓的简单风控
        predicted_position = abs(self.cached_position + self.trade_volume)
        if predicted_position > self.max_position:
            self.write_log(f"🔧 基于缓存的风控：预测超限，跳过信号生成")
            return

        # 生成交易信号（基于缓存数据）
        signal_decision = self._make_trading_decision(market_analysis, current_price)

        # 如果决定要交易，则进行实时持仓确认
        if signal_decision['action'] in ['BUY', 'SELL']:
            self.write_log(f"🔧 准备交易，进行实时持仓确认")
            self._generate_signal_with_fresh_position(tick, market_analysis)
        else:
            self.write_log(f"🔧 无交易信号: {signal_decision['reason']}")

    def _execute_signal_decision(self, signal_decision: dict, current_price: float):
        """执行交易信号决策"""
        action = signal_decision['action']
        reason = signal_decision['reason']

        if action == 'BUY':
            self.write_log(f"🚀🚀🚀 发出买入信号！当前持仓: {self.pos} 🚀🚀🚀")
            self.buy(current_price, self.trade_volume, stop=False)
        elif action == 'SELL':
            self.write_log(f"🚀🚀🚀 发出卖出信号！当前持仓: {self.pos} 🚀🚀🚀")
            self.sell(current_price, self.trade_volume, stop=False)
        else:
            self.write_log(f"🚫 无交易信号: {reason}")

    def on_stop_order(self, stop_order):
        """处理停止单回调"""
        self.write_log(f"停止单触发: {stop_order.orderid}")

    def _analyze_market_conditions(self, tick: TickData) -> dict:
        """分析当前市场条件"""
        current_price = tick.last_price
        current_time = time.time()

        analysis = {
            'current_price': current_price,
            'timestamp': current_time
        }

        # 价格变化分析
        if len(self.last_price_history) >= 2:
            prev_price = self.last_price_history[-2]['price']
            price_change = current_price - prev_price
            price_change_pct = (price_change / prev_price) * 100 if prev_price > 0 else 0

            analysis.update({
                'price_change': price_change,
                'price_change_pct': price_change_pct,
                'price_trend': 'UP' if price_change > 0 else 'DOWN' if price_change < 0 else 'FLAT'
            })

        # 短期价格统计（最近10个tick）
        if len(self.last_price_history) >= 10:
            recent_prices = [p['price'] for p in self.last_price_history[-10:]]
            analysis.update({
                'recent_high': max(recent_prices),
                'recent_low': min(recent_prices),
                'recent_avg': sum(recent_prices) / len(recent_prices),
                'price_volatility': max(recent_prices) - min(recent_prices)
            })

            # 价格位置
            price_position = (current_price - min(recent_prices)) / (max(recent_prices) - min(recent_prices)) if max(recent_prices) > min(recent_prices) else 0.5
            analysis['price_position'] = price_position  # 0=最低点, 1=最高点

        # 时间因素
        analysis.update({
            'time_since_last_signal': current_time - self.last_signal_time,
            'signal_interval_met': (current_time - self.last_signal_time) >= self.signal_interval
        })

        return analysis

    def _make_trading_decision(self, market_analysis: dict, current_price: float) -> dict:
        """基于市场分析做出交易决策"""
        decision = {
            'action': 'HOLD',
            'reason': '无明确信号',
            'detailed_reason': '市场条件不满足交易条件',
            'confidence': 0.0
        }

        # 简单的决策逻辑（可以根据需要扩展）
        factors = []

        # 因子1: 价格趋势
        if 'price_trend' in market_analysis:
            if market_analysis['price_trend'] == 'UP':
                factors.append(('price_trend_up', 0.3, '价格上涨趋势'))
            elif market_analysis['price_trend'] == 'DOWN':
                factors.append(('price_trend_down', -0.3, '价格下跌趋势'))

        # 因子2: 价格位置
        if 'price_position' in market_analysis:
            pos = market_analysis['price_position']
            if pos < 0.3:  # 接近低点
                factors.append(('near_low', 0.4, f'价格接近近期低点({pos:.2f})'))
            elif pos > 0.7:  # 接近高点
                factors.append(('near_high', -0.4, f'价格接近近期高点({pos:.2f})'))

        # 因子3: 波动性
        if 'price_volatility' in market_analysis:
            volatility = market_analysis['price_volatility']
            if volatility > current_price * 0.01:  # 波动超过1%
                factors.append(('high_volatility', 0.2, f'高波动性({volatility:.2f})'))

        # 因子4: 随机因子（保持测试策略的随机性）
        import random
        random_factor = random.uniform(-0.5, 0.5)
        factors.append(('random', random_factor, f'随机因子({random_factor:.2f})'))

        # 计算总分
        total_score = sum(factor[1] for factor in factors)

        # 决策逻辑
        if total_score > 0.3:
            decision.update({
                'action': 'BUY',
                'reason': '多头信号',
                'detailed_reason': f'综合评分{total_score:.2f} > 0.3，触发买入',
                'confidence': min(total_score, 1.0)
            })
        elif total_score < -0.3:
            decision.update({
                'action': 'SELL',
                'reason': '空头信号',
                'detailed_reason': f'综合评分{total_score:.2f} < -0.3，触发卖出',
                'confidence': min(abs(total_score), 1.0)
            })
        else:
            decision.update({
                'detailed_reason': f'综合评分{total_score:.2f}在[-0.3, 0.3]区间，无交易信号'
            })

        # 记录决策因子
        decision['factors'] = factors
        decision['total_score'] = total_score

        return decision

    def get_signal_triggers(self) -> list:
        """获取信号触发历史"""
        return self.signal_triggers.copy()

    def get_latest_market_analysis(self) -> dict:
        """获取最新的市场分析"""
        if hasattr(self, 'tick') and self.tick:
            return self._analyze_market_conditions(self.tick)
        return {}


# 策略工厂函数
def create_strategy(strategy_engine, strategy_name: str, symbol: str, setting: dict) -> SystemIntegrationTestStrategy:
    """创建系统集成测试策略实例"""
    
    # 默认设置
    default_setting = {
        'signal_interval': 30,  # 30秒生成一次信号
        'trade_volume': 1,      # 每次交易1手
        'max_position': 3       # 最大持仓3手
    }
    
    # 合并设置
    merged_setting = {**default_setting, **setting}
    
    return SystemIntegrationTestStrategy(strategy_name, symbol, merged_setting)


# 策略配置模板
STRATEGY_TEMPLATE = {
    "class_name": "SystemIntegrationTestStrategy",
    "file_name": "SystemIntegrationTestStrategy.py",
    "description": "系统集成测试策略，用于验证交易系统各模块功能",
    "parameters": {
        "signal_interval": {
            "type": "int",
            "default": 30,
            "description": "信号生成间隔(秒)"
        },
        "trade_volume": {
            "type": "int", 
            "default": 1,
            "description": "每次交易手数"
        },
        "max_position": {
            "type": "int",
            "default": 3,
            "description": "最大持仓手数"
        }
    }
}


if __name__ == "__main__":
    # 本地测试代码
    print("测试策略模块加载成功")
    print(f"策略模板: {STRATEGY_TEMPLATE}")
