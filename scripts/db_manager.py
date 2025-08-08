#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据库管理工具
提供数据库的常用管理操作
"""

import sys
import os
import argparse
import asyncio
import json
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.database.connection import init_database, get_db_manager
from utils.logger import get_logger

logger = get_logger(__name__)

class DatabaseManager:
    """数据库管理工具类"""
    
    def __init__(self):
        """初始化数据库管理器"""
        self.db_manager = None
        
        # 加载数据库配置
        config_file = project_root / "config" / "database.json"
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        else:
            logger.error(f"配置文件不存在: {config_file}")
            sys.exit(1)
    
    async def init_connection(self):
        """初始化数据库连接"""
        mysql_config = self.config['mysql']
        redis_config = self.config['redis']
        
        success = await init_database(mysql_config, redis_config)
        if not success:
            logger.error("数据库连接初始化失败")
            return False
        
        self.db_manager = get_db_manager()
        return True
    
    async def show_tables(self):
        """显示所有表"""
        try:
            result = await self.db_manager.execute_query("SHOW TABLES")
            
            logger.info("数据库表列表:")
            logger.info("-" * 40)
            for row in result:
                table_name = list(row.values())[0]
                logger.info(f"📋 {table_name}")
            
            logger.info(f"\n总计: {len(result)} 个表")
            
        except Exception as e:
            logger.error(f"显示表列表失败: {e}")
    
    async def show_table_info(self, table_name: str):
        """显示表信息"""
        try:
            # 获取表结构
            result = await self.db_manager.execute_query(f"DESCRIBE {table_name}")
            
            logger.info(f"表 {table_name} 结构:")
            logger.info("-" * 80)
            logger.info(f"{'字段名':<20} {'类型':<20} {'空值':<8} {'键':<8} {'默认值':<15} {'额外'}")
            logger.info("-" * 80)
            
            for row in result:
                logger.info(f"{row['Field']:<20} {row['Type']:<20} {row['Null']:<8} {row['Key']:<8} {str(row['Default']):<15} {row['Extra']}")
            
            # 获取记录数
            count_result = await self.db_manager.execute_query(f"SELECT COUNT(*) as count FROM {table_name}")
            record_count = count_result[0]['count'] if count_result else 0
            
            logger.info(f"\n记录数: {record_count}")
            
        except Exception as e:
            logger.error(f"显示表信息失败: {e}")
    
    async def show_accounts(self):
        """显示账户信息"""
        try:
            result = await self.db_manager.execute_query("""
                SELECT account_id, balance, available, margin, 
                       unrealized_pnl, realized_pnl, risk_ratio, update_time
                FROM accounts
                ORDER BY update_time DESC
            """)
            
            if not result:
                logger.info("没有账户数据")
                return
            
            logger.info("账户信息:")
            logger.info("-" * 100)
            logger.info(f"{'账户ID':<12} {'余额':<12} {'可用':<12} {'保证金':<12} {'未实现盈亏':<12} {'已实现盈亏':<12} {'风险度':<8}")
            logger.info("-" * 100)
            
            for row in result:
                logger.info(f"{row['account_id']:<12} {row['balance']:<12.2f} {row['available']:<12.2f} "
                          f"{row['margin']:<12.2f} {row['unrealized_pnl']:<12.2f} {row['realized_pnl']:<12.2f} "
                          f"{row['risk_ratio']:<8.4f}")
            
        except Exception as e:
            logger.error(f"显示账户信息失败: {e}")
    
    async def show_positions(self):
        """显示持仓信息"""
        try:
            result = await self.db_manager.execute_query("""
                SELECT account_id, symbol, direction, volume, avg_price, 
                       current_price, unrealized_pnl, margin, open_time
                FROM positions
                WHERE volume > 0
                ORDER BY open_time DESC
            """)
            
            if not result:
                logger.info("没有持仓数据")
                return
            
            logger.info("持仓信息:")
            logger.info("-" * 120)
            logger.info(f"{'账户ID':<12} {'合约':<10} {'方向':<6} {'数量':<6} {'成本价':<10} {'当前价':<10} {'盈亏':<12} {'保证金':<12} {'开仓时间'}")
            logger.info("-" * 120)
            
            for row in result:
                logger.info(f"{row['account_id']:<12} {row['symbol']:<10} {row['direction']:<6} "
                          f"{row['volume']:<6} {row['avg_price']:<10.2f} {row['current_price']:<10.2f} "
                          f"{row['unrealized_pnl']:<12.2f} {row['margin']:<12.2f} {row['open_time']}")
            
        except Exception as e:
            logger.error(f"显示持仓信息失败: {e}")
    
    async def show_recent_trades(self, limit: int = 10):
        """显示最近交易记录"""
        try:
            result = await self.db_manager.execute_query("""
                SELECT trade_id, order_id, account_id, symbol, direction, 
                       volume, price, commission, trade_time
                FROM trades
                ORDER BY trade_time DESC
                LIMIT %s
            """, (limit,))
            
            if not result:
                logger.info("没有交易记录")
                return
            
            logger.info(f"最近 {len(result)} 条交易记录:")
            logger.info("-" * 120)
            logger.info(f"{'成交ID':<15} {'订单ID':<15} {'账户ID':<12} {'合约':<10} {'方向':<6} {'数量':<6} {'价格':<10} {'手续费':<10} {'成交时间'}")
            logger.info("-" * 120)
            
            for row in result:
                logger.info(f"{row['trade_id']:<15} {row['order_id']:<15} {row['account_id']:<12} "
                          f"{row['symbol']:<10} {row['direction']:<6} {row['volume']:<6} "
                          f"{row['price']:<10.2f} {row['commission']:<10.2f} {row['trade_time']}")
            
        except Exception as e:
            logger.error(f"显示交易记录失败: {e}")
    
    async def show_strategy_triggers(self, limit: int = 10):
        """显示策略触发记录"""
        try:
            result = await self.db_manager.execute_query("""
                SELECT strategy_name, trigger_time, trigger_condition, trigger_price,
                       signal_type, execution_result, order_id, volume
                FROM strategy_triggers
                ORDER BY trigger_time DESC
                LIMIT %s
            """, (limit,))
            
            if not result:
                logger.info("没有策略触发记录")
                return
            
            logger.info(f"最近 {len(result)} 条策略触发记录:")
            logger.info("-" * 120)
            logger.info(f"{'策略名称':<20} {'触发时间':<20} {'信号类型':<10} {'触发价格':<10} {'执行结果':<10} {'订单ID':<15} {'数量':<6}")
            logger.info("-" * 120)
            
            for row in result:
                logger.info(f"{row['strategy_name']:<20} {str(row['trigger_time']):<20} "
                          f"{row['signal_type']:<10} {row['trigger_price'] or 0:<10.2f} "
                          f"{row['execution_result']:<10} {row['order_id'] or '':<15} {row['volume'] or 0:<6}")
            
        except Exception as e:
            logger.error(f"显示策略触发记录失败: {e}")
    
    async def backup_database(self, backup_file: str = None):
        """备份数据库"""
        try:
            if not backup_file:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = f"arbig_trading_backup_{timestamp}.sql"
            
            mysql_config = self.config['mysql']
            cmd = f"mysqldump -u {mysql_config['user']} -p'{mysql_config['password']}' {mysql_config['database']} > {backup_file}"
            
            import subprocess
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"✅ 数据库备份成功: {backup_file}")
            else:
                logger.error(f"❌ 数据库备份失败: {result.stderr}")
            
        except Exception as e:
            logger.error(f"备份数据库失败: {e}")
    
    async def close(self):
        """关闭数据库连接"""
        if self.db_manager:
            await self.db_manager.close()

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='ARBIG数据库管理工具')
    parser.add_argument('action', choices=[
        'tables', 'info', 'accounts', 'positions', 'trades', 'triggers', 'backup'
    ], help='操作类型')
    parser.add_argument('--table', type=str, help='表名（用于info操作）')
    parser.add_argument('--limit', type=int, default=10, help='记录数限制')
    parser.add_argument('--file', type=str, help='备份文件名')
    
    args = parser.parse_args()
    
    db_mgr = DatabaseManager()
    
    try:
        # 初始化数据库连接
        if not await db_mgr.init_connection():
            sys.exit(1)
        
        # 执行相应操作
        if args.action == 'tables':
            await db_mgr.show_tables()
        elif args.action == 'info':
            if not args.table:
                logger.error("请指定表名: --table <table_name>")
                sys.exit(1)
            await db_mgr.show_table_info(args.table)
        elif args.action == 'accounts':
            await db_mgr.show_accounts()
        elif args.action == 'positions':
            await db_mgr.show_positions()
        elif args.action == 'trades':
            await db_mgr.show_recent_trades(args.limit)
        elif args.action == 'triggers':
            await db_mgr.show_strategy_triggers(args.limit)
        elif args.action == 'backup':
            await db_mgr.backup_database(args.file)
        
    except Exception as e:
        logger.error(f"操作失败: {e}")
        sys.exit(1)
    finally:
        await db_mgr.close()

if __name__ == "__main__":
    asyncio.run(main())
