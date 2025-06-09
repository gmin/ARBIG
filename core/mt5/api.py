"""
MT5 FIX API 实现
使用 quickfix 库实现 FIX 协议
"""

import time
from datetime import datetime
from typing import Dict, Optional, Callable

import quickfix as fix
from quickfix import (
    SessionID, Message, FieldNotFound, IncorrectDataFormat,
    IncorrectTagValue, UnsupportedMessageType
)

from ..utils.logger import get_logger
from .utils import load_config

logger = get_logger(__name__)

class MT5FIXApplication(fix.Application):
    """
    MT5 FIX 应用程序
    处理 FIX 消息的接收和发送
    """
    
    def __init__(self, config: Dict):
        """
        初始化 FIX 应用程序
        
        Args:
            config: FIX 配置信息
        """
        super().__init__()
        self.config = config
        self.connected = False
        self.session_id: Optional[SessionID] = None
        self.on_tick: Optional[Callable] = None
        
    def onCreate(self, sessionID: SessionID):
        """
        会话创建时的回调
        
        Args:
            sessionID: 会话ID
        """
        logger.info(f"FIX会话创建: {sessionID}")
        
    def onLogon(self, sessionID: SessionID):
        """
        登录成功时的回调
        
        Args:
            sessionID: 会话ID
        """
        logger.info(f"FIX登录成功: {sessionID}")
        self.connected = True
        self.session_id = sessionID
        
    def onLogout(self, sessionID: SessionID):
        """
        登出时的回调
        
        Args:
            sessionID: 会话ID
        """
        logger.info(f"FIX登出: {sessionID}")
        self.connected = False
        self.session_id = None
        
    def fromAdmin(self, message: Message, sessionID: SessionID):
        """
        处理管理消息
        
        Args:
            message: FIX消息
            sessionID: 会话ID
        """
        try:
            msg_type = message.getHeader().getField(fix.MsgType())
            logger.debug(f"收到管理消息: {msg_type}")
            
        except (FieldNotFound, IncorrectDataFormat, IncorrectTagValue) as e:
            logger.error(f"处理管理消息失败: {str(e)}")
            
    def toAdmin(self, message: Message, sessionID: SessionID):
        """
        发送管理消息前的处理
        
        Args:
            message: FIX消息
            sessionID: 会话ID
        """
        try:
            msg_type = message.getHeader().getField(fix.MsgType())
            if msg_type == fix.MsgType_Logon:
                # 设置登录信息
                message.setField(fix.Username(self.config["fix"]["username"]))
                message.setField(fix.Password(self.config["fix"]["password"]))
                
        except (FieldNotFound, IncorrectDataFormat, IncorrectTagValue) as e:
            logger.error(f"处理管理消息失败: {str(e)}")
            
    def fromApp(self, message: Message, sessionID: SessionID):
        """
        处理应用消息
        
        Args:
            message: FIX消息
            sessionID: 会话ID
        """
        try:
            msg_type = message.getHeader().getField(fix.MsgType())
            
            if msg_type == fix.MsgType_MarketDataSnapshotFullRefresh:
                self._handle_market_data(message)
            else:
                logger.warning(f"未知的消息类型: {msg_type}")
                
        except (FieldNotFound, IncorrectDataFormat, IncorrectTagValue, UnsupportedMessageType) as e:
            logger.error(f"处理应用消息失败: {str(e)}")
            
    def toApp(self, message: Message, sessionID: SessionID):
        """
        发送应用消息前的处理
        
        Args:
            message: FIX消息
            sessionID: 会话ID
        """
        pass
        
    def _handle_market_data(self, message: Message):
        """
        处理市场数据消息
        
        Args:
            message: FIX消息
        """
        try:
            # 获取合约信息
            symbol = message.getField(fix.Symbol())
            
            # 获取价格信息
            no_md_entries = message.getField(fix.NoMDEntries())
            
            for i in range(int(no_md_entries)):
                message.setGroup(i + 1)
                
                entry_type = message.getField(fix.MDEntryType())
                price = message.getField(fix.MDEntryPx())
                size = message.getField(fix.MDEntrySize())
                
                # 转换为Tick数据
                if self.on_tick:
                    tick_data = {
                        "symbol": symbol,
                        "last_price": price,
                        "volume": size,
                        "datetime": datetime.now()
                    }
                    self.on_tick(tick_data)
                    
        except (FieldNotFound, IncorrectDataFormat, IncorrectTagValue) as e:
            logger.error(f"处理市场数据失败: {str(e)}")
            
    def subscribe_market_data(self, symbol: str):
        """
        订阅市场数据
        
        Args:
            symbol: 合约代码
        """
        try:
            if not self.connected or not self.session_id:
                logger.error("FIX未连接")
                return False
                
            # 创建市场数据请求消息
            message = fix.Message()
            message.getHeader().setField(fix.MsgType(fix.MsgType_MarketDataRequest))
            message.setField(fix.MDReqID("1"))
            message.setField(fix.SubscriptionRequestType(fix.SubscriptionRequestType_SNAPSHOT_PLUS_UPDATES))
            message.setField(fix.MarketDepth(1))
            message.setField(fix.MDUpdateType(fix.MDUpdateType_FULL_REFRESH))
            
            # 添加合约信息
            message.setField(fix.NoRelatedSym(1))
            message.setField(fix.Symbol(symbol))
            
            # 发送请求
            fix.Session.sendToTarget(message, self.session_id)
            logger.info(f"订阅市场数据成功: {symbol}")
            return True
            
        except Exception as e:
            logger.error(f"订阅市场数据失败: {str(e)}")
            return False
