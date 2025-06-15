"""
优化版 TrendFollowingProStrategy 策略：

优化内容：
1. 多指标协同过滤：结合 EMA、RSI、MFI、OBV、布林带、动量判断趋势、超买超卖、量能和极端位置。
2. 动态杠杆机制：根据 ATR 波动性调整杠杆大小（波动小 => 杠杆高，波动大 => 杠杆低）。
3. 移动止盈机制：采用 trailing stop 捕捉更大收益，同时保护已得利润。
4. 条件丰富的入场信号：避免单一指标误导，减少震荡区误触发。
5. 精准出场：使用 RSI 和 EMA 结合动态判断是否退出持仓。
6. 支持做空交易。

策略规则说明：
- 买入条件（做多 enter_long）：
  - 收盘价高于 20 EMA，说明处于上升趋势中；
  - RSI < 35 且 MFI < 40，表明处于超卖状态，有反弹潜力；
  - 收盘价跌破布林带下轨，出现极端偏离；
  - OBV 上升，量能支撑上涨。

- 卖出条件（做空 enter_short）：
  - 收盘价低于 20 EMA，说明处于下降趋势中；
  - RSI > 65 且 MFI > 60，处于超买区域，有回调压力；
  - 收盘价突破布林带上轨，出现极端偏高；
  - OBV 下降，量能减弱。

- 止盈条件：
  - 启用 trailing stop：价格上涨一定幅度后，回撤超过 1.5% 即止盈；
  - trailing offset 为 3%，只有上涨超过这个幅度才激活 trailing stop。

- 止损条件：
  - 固定止损为 -20%，防止极端行情下爆仓；

- 杠杆规则：
  - ATR < 0.5：波动小，允许高杠杆，使用 4x；
  - 0.5 <= ATR < 1.0：使用 3x 杠杆；
  - ATR >= 1.0：波动大，风险高，保守使用 1.5x 杠杆。
"""

from functools import reduce
from pandas import DataFrame
from freqtrade.strategy import IStrategy
from freqtrade.persistence import Trade

import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib

class TrendFollowingProStrategy(IStrategy):

    INTERFACE_VERSION = 3
    can_short = True

    # ROI 目标
    minimal_roi = {
        "0": 0.1,
        "30": 0.05,
        "60": 0.02
    }

    # 动态止损
    stoploss = -0.20

    # 移动止盈
    trailing_stop = True
    trailing_stop_positive = 0.015
    trailing_stop_positive_offset = 0.03
    trailing_only_offset_is_reached = True

    # 时间周期
    timeframe = "5m"

    def leverage(self, pair: str, current_time: 'datetime', current_rate: float,
                 proposed_leverage: float, max_leverage: float, side: str,
                 **kwargs) -> float:
        # 根据波动性动态调整杠杆（ATR 越小，杠杆越高）
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe is None or len(dataframe) < 20:
            return 2.0  # 默认值

        atr = ta.ATR(dataframe, timeperiod=14).iloc[-1]
        if atr < 0.5:
            return min(max_leverage, 4.0)
        elif atr < 1.0:
            return min(max_leverage, 3.0)
        else:
            return min(max_leverage, 1.5)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['ema'] = ta.EMA(dataframe, timeperiod=20)
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['mfi'] = ta.MFI(dataframe)
        dataframe['obv'] = ta.OBV(dataframe['close'], dataframe['volume'])
        dataframe['bb_lower'], dataframe['bb_middle'], dataframe['bb_upper'] = ta.BBANDS(dataframe['close'], timeperiod=20)
        dataframe['mom'] = ta.MOM(dataframe['close'], timeperiod=10)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['close'] > dataframe['ema']) &
                (dataframe['rsi'] < 35) &
                (dataframe['mfi'] < 40) &
                (dataframe['close'] < dataframe['bb_lower']) &
                (dataframe['obv'] > dataframe['obv'].shift(1))
            ),
            'enter_long'
        ] = 1

        dataframe.loc[
            (
                (dataframe['close'] < dataframe['ema']) &
                (dataframe['rsi'] > 65) &
                (dataframe['mfi'] > 60) &
                (dataframe['close'] > dataframe['bb_upper']) &
                (dataframe['obv'] < dataframe['obv'].shift(1))
            ),
            'enter_short'
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe['rsi'] > 70) | (dataframe['close'] < dataframe['ema']),
            'exit_long'
        ] = 1

        dataframe.loc[
            (dataframe['rsi'] < 30) | (dataframe['close'] > dataframe['ema']),
            'exit_short'
        ] = 1

        return dataframe
