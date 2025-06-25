import numpy as np
import talib

# 创建一些测试数据
close_prices = np.array([10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0])

# 计算5日简单移动平均线
ma5 = talib.SMA(close_prices, timeperiod=5)

print("收盘价:", close_prices)
print("5日移动平均线:", ma5)

print(talib.__version__)