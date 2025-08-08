#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据库初始化脚本
创建MySQL表结构和初始化数据
"""

import sys
import os
import asyncio
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.database.connection import init_database, get_db_manager
from utils.logger import get_logger

logger = get_logger(__name__)

async def create_database_schema():
    """创建数据库表结构"""
    try:
        db_manager = get_db_manager()
        
        # 读取SQL文件
        schema_file = project_root / "shared" / "database" / "schema.sql"
        if not schema_file.exists():
            logger.error(f"SQL文件不存在: {schema_file}")
            return False
        
        with open(schema_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # 分割SQL语句
        sql_statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
        
        logger.info("开始创建数据库表结构...")
        
        # 执行SQL语句
        for i, sql in enumerate(sql_statements):
            if sql.upper().startswith(('CREATE', 'INSERT', 'USE', 'SHOW', 'SELECT')):
                try:
                    if sql.upper().startswith('SELECT'):
                        result = await db_manager.execute_query(sql)
                        if result:
                            logger.info(f"执行结果: {result[0]}")
                    else:
                        await db_manager.execute_update(sql)
                        logger.debug(f"执行SQL语句 {i+1}: {sql[:50]}...")
                except Exception as e:
                    logger.error(f"执行SQL语句失败: {sql[:50]}... - {e}")
                    return False
        
        logger.info("✅ 数据库表结构创建完成")
        return True
        
    except Exception as e:
        logger.error(f"创建数据库表结构失败: {e}")
        return False

async def verify_database_schema():
    """验证数据库表结构"""
    try:
        db_manager = get_db_manager()
        
        # 检查表是否存在
        tables_to_check = [
            'accounts', 'positions', 'orders', 'trades', 
            'strategy_configs', 'strategy_triggers', 'system_logs'
        ]
        
        logger.info("验证数据库表结构...")
        
        for table in tables_to_check:
            result = await db_manager.execute_query(
                "SELECT COUNT(*) as count FROM information_schema.tables WHERE table_schema = 'arbig_trading' AND table_name = %s",
                (table,)
            )
            
            if result and result[0]['count'] > 0:
                logger.info(f"✅ 表 {table} 存在")
            else:
                logger.error(f"❌ 表 {table} 不存在")
                return False
        
        # 检查视图是否存在
        views_to_check = ['account_summary', 'daily_trade_summary', 'strategy_trigger_summary']
        
        for view in views_to_check:
            result = await db_manager.execute_query(
                "SELECT COUNT(*) as count FROM information_schema.views WHERE table_schema = 'arbig_trading' AND table_name = %s",
                (view,)
            )
            
            if result and result[0]['count'] > 0:
                logger.info(f"✅ 视图 {view} 存在")
            else:
                logger.warning(f"⚠️ 视图 {view} 不存在")
        
        logger.info("✅ 数据库表结构验证完成")
        return True
        
    except Exception as e:
        logger.error(f"验证数据库表结构失败: {e}")
        return False

async def init_sample_data():
    """初始化示例数据"""
    try:
        db_manager = get_db_manager()
        
        logger.info("初始化示例数据...")
        
        # 检查是否已有数据
        result = await db_manager.execute_query("SELECT COUNT(*) as count FROM accounts")
        if result and result[0]['count'] > 0:
            logger.info("账户表已有数据，跳过示例数据初始化")
            return True
        
        # 插入示例账户数据
        await db_manager.execute_insert(
            """INSERT INTO accounts (account_id, balance, available, margin, currency) 
               VALUES (%s, %s, %s, %s, %s)""",
            ('123456789', 1000000.00, 800000.00, 200000.00, 'CNY')
        )
        
        # 插入示例策略配置
        import json
        strategy_config = {
            'symbol': 'au2509',
            'position_size': 1,
            'spread_threshold': 0.5,
            'stop_loss': 0.02,
            'take_profit': 0.05
        }
        
        await db_manager.execute_insert(
            """INSERT INTO strategy_configs (strategy_name, strategy_class, config_data, description) 
               VALUES (%s, %s, %s, %s)""",
            ('ArbitrageStrategy', 'ArbitrageStrategy', json.dumps(strategy_config), '套利策略 - 基于价差的套利交易')
        )
        
        logger.info("✅ 示例数据初始化完成")
        return True
        
    except Exception as e:
        logger.error(f"初始化示例数据失败: {e}")
        return False

async def main():
    """主函数"""
    logger.info("="*60)
    logger.info("🗄️  ARBIG数据库初始化")
    logger.info("="*60)
    
    # 数据库配置
    mysql_config = {
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': 'arbig123',
        'database': 'arbig_trading',
        'charset': 'utf8mb4'
    }
    
    redis_config = {
        'host': 'localhost',
        'port': 6379,
        'db': 0,
        'password': None
    }
    
    try:
        # 初始化数据库连接
        logger.info("初始化数据库连接...")
        success = await init_database(mysql_config, redis_config)
        if not success:
            logger.error("❌ 数据库连接初始化失败")
            return False
        
        # 创建数据库表结构
        success = await create_database_schema()
        if not success:
            logger.error("❌ 数据库表结构创建失败")
            return False
        
        # 验证数据库表结构
        success = await verify_database_schema()
        if not success:
            logger.error("❌ 数据库表结构验证失败")
            return False
        
        # 初始化示例数据
        success = await init_sample_data()
        if not success:
            logger.error("❌ 示例数据初始化失败")
            return False
        
        logger.info("="*60)
        logger.info("🎉 数据库初始化完成！")
        logger.info("="*60)
        logger.info("📊 数据库: arbig_trading")
        logger.info("📋 表数量: 7个核心表 + 3个视图")
        logger.info("💾 示例数据: 已初始化")
        logger.info("="*60)
        
        return True
        
    except Exception as e:
        logger.error(f"数据库初始化异常: {e}")
        return False
    finally:
        # 关闭数据库连接
        await get_db_manager().close()

if __name__ == "__main__":
    # 运行初始化
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
