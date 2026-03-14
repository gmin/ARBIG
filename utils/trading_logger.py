"""
交易日志管理器（基于文件日志）
从 utils/logger.py 写入的日志文件中解析和查询交易相关记录
"""

import os
import re
import glob
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path


# 日志文件目录和基础文件名
_LOG_DIR = Path(__file__).parent.parent / "logs"
_BASE_LOG = _LOG_DIR / "gold_arbitrage.log"

# TimedRotatingFileHandler 滚动后的文件名格式: gold_arbitrage.log.20260313
_ROTATED_PATTERN = str(_BASE_LOG) + ".*"

# 标准日志行格式: "2026-03-13 10:30:45,123 - module - LEVEL - message"
_LINE_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ - (.+?) - (INFO|WARNING|ERROR|DEBUG) - (.*)$"
)

# 从日志消息中推断交易日志类型的关键词映射
_TYPE_PATTERNS = {
    "ORDER": [
        re.compile(r"(订单发送成功|订单发送失败|发送订单|撤销订单|订单被拒绝|收到策略信号|📨|📋)"),
    ],
    "TRADE": [
        re.compile(r"(成交回调|成交数据|🔥)"),
    ],
    "SIGNAL": [
        re.compile(r"(策略信号|信号生成|_send_order|开仓前|平仓)"),
    ],
    "ERROR": [
        re.compile(r"(失败|异常|错误|❌|🚨)"),
    ],
}


def _infer_log_type(message: str, level: str) -> str:
    """根据日志消息内容推断交易日志类型"""
    if level == "ERROR":
        return "ERROR"
    for log_type, patterns in _TYPE_PATTERNS.items():
        for pat in patterns:
            if pat.search(message):
                return log_type
    return "INFO"


def _infer_strategy_name(message: str) -> Optional[str]:
    """从日志消息中提取策略名称"""
    # 常见格式: "[StrategyName]" 或 "策略 StrategyName" 或 "strategy_name: xxx"
    m = re.search(r"\[(\w+Strategy\w*)\]", message)
    if m:
        return m.group(1)
    m = re.search(r"策略[:\s]+(\w+)", message)
    if m:
        return m.group(1)
    # 策略信号格式: "收到策略信号: MaRsi BUY ..."
    m = re.search(r"收到策略信号:\s*(\w+)", message)
    if m:
        return m.group(1)
    return None


def _infer_symbol(message: str) -> Optional[str]:
    """从日志消息中提取合约代码"""
    m = re.search(r"\b(au\d{4}|ag\d{4}|cu\d{4}|[a-z]{1,3}\d{3,4})\b", message)
    return m.group(1) if m else None


def _collect_log_files(start_time: Optional[datetime] = None,
                       end_time: Optional[datetime] = None) -> List[str]:
    """收集需要读取的日志文件列表，按时间降序排列"""
    files = []

    # 当前日志文件
    if _BASE_LOG.exists():
        files.append(str(_BASE_LOG))

    # 滚动后的日志文件
    for f in glob.glob(_ROTATED_PATTERN):
        if f != str(_BASE_LOG):
            files.append(f)

    # 按文件修改时间降序（最新的在前面）
    files.sort(key=lambda f: os.path.getmtime(f), reverse=True)

    return files


def _parse_line(line: str) -> Optional[Dict]:
    """解析单行日志为结构化字典"""
    m = _LINE_RE.match(line.strip())
    if not m:
        return None

    timestamp_str, module, level, message = m.groups()
    try:
        timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None

    log_type = _infer_log_type(message, level)

    return {
        "timestamp": timestamp.isoformat(),
        "log_type": log_type,
        "level": level,
        "module": module,
        "strategy_name": _infer_strategy_name(message),
        "symbol": _infer_symbol(message),
        "message": message,
        "is_success": level != "ERROR",
    }


class TradingLogger:
    """基于文件的交易日志查询器"""

    def get_logs(self,
                 strategy_name: Optional[str] = None,
                 log_type: Optional[str] = None,
                 start_time: Optional[datetime] = None,
                 end_time: Optional[datetime] = None,
                 limit: int = 100,
                 offset: int = 0) -> List[Dict]:
        """查询交易日志"""
        results = []
        skipped = 0
        files = _collect_log_files(start_time, end_time)

        for filepath in files:
            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    # 逆序读取（最新的在后面），所以先读全部再反转
                    lines = f.readlines()
            except OSError:
                continue

            for line in reversed(lines):
                entry = _parse_line(line)
                if entry is None:
                    continue

                # 时间过滤
                entry_time = datetime.fromisoformat(entry["timestamp"])
                if start_time and entry_time < start_time:
                    continue
                if end_time and entry_time > end_time:
                    continue

                # 策略名过滤
                if strategy_name and entry.get("strategy_name") != strategy_name:
                    continue

                # 类型过滤
                if log_type and entry["log_type"] != log_type:
                    continue

                # offset 跳过
                if skipped < offset:
                    skipped += 1
                    continue

                results.append(entry)
                if len(results) >= limit:
                    return results

        return results

    def get_strategy_performance(self,
                                 strategy_name: str,
                                 days: int = 30) -> Dict:
        """从日志文件中统计策略性能（简化版）"""
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)

        # 获取该策略的所有交易类型日志
        trade_logs = self.get_logs(
            strategy_name=strategy_name,
            log_type="TRADE",
            start_time=start_time,
            end_time=end_time,
            limit=10000,
        )

        order_logs = self.get_logs(
            strategy_name=strategy_name,
            log_type="ORDER",
            start_time=start_time,
            end_time=end_time,
            limit=10000,
        )

        error_logs = self.get_logs(
            strategy_name=strategy_name,
            log_type="ERROR",
            start_time=start_time,
            end_time=end_time,
            limit=10000,
        )

        total_orders = len(order_logs)
        successful_orders = len([o for o in order_logs if o.get("is_success")])
        failed_orders = total_orders - successful_orders

        return {
            "strategy_name": strategy_name,
            "total_trades": len(trade_logs),
            "total_orders": total_orders,
            "successful_orders": successful_orders,
            "failed_orders": failed_orders,
            "total_errors": len(error_logs),
            "win_rate": round(successful_orders / total_orders * 100, 2) if total_orders > 0 else 0,
            "days": days,
        }


# 全局单例
_trading_logger = None


def get_trading_logger() -> TradingLogger:
    """获取交易日志管理器实例"""
    global _trading_logger
    if _trading_logger is None:
        _trading_logger = TradingLogger()
    return _trading_logger
