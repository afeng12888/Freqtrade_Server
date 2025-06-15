# 这个是一个垃圾策略，不好用

from functools import reduce
from pandas import DataFrame
from freqtrade.strategy import IStrategy

import talib.abstract as ta

from freqtrade.strategy.interface import IStrategy

class TrendReversalStrategy(IStrategy):

    INTERFACE_VERSION: int = 3
    # short
    can_short = True

    # ROI table:
    minimal_roi = {"0": 0.15, "30": 0.1, "60": 0.05}

    # Stoploss:
    stoploss = -0.265

    # Trailing stop:
    trailing_stop = True
    trailing_stop_positive = 0.05
    trailing_stop_positive_offset = 0.1
    trailing_only_offset_is_reached = False

    timeframe = "5m"
    
    def leverage(self, pair: str, current_time: 'datetime', current_rate: float,
                 proposed_leverage: float, max_leverage: float, side: str,
                 **kwargs) -> float:
        return 2.0

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['obv'] = ta.OBV(dataframe['close'], dataframe['volume'])
        dataframe['trend'] = dataframe['close'].ewm(span=20, adjust=False).mean()
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 做多（原做空）：价格下穿均线，OBV 下降（通常为下跌趋势）
        dataframe.loc[
            (dataframe['close'] < dataframe['trend']) &
            (dataframe['close'].shift(1) >= dataframe['trend'].shift(1)) &
            (dataframe['obv'] < dataframe['obv'].shift(1)),
            'enter_long'] = 1

        # 做空（原做多）：价格上穿均线，OBV 上升（通常为上涨趋势）
        dataframe.loc[
            (dataframe['close'] > dataframe['trend']) &
            (dataframe['close'].shift(1) <= dataframe['trend'].shift(1)) &
            (dataframe['obv'] > dataframe['obv'].shift(1)),
            'enter_short'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 平多（原平空）：价格上穿均线，OBV 下降（逆势）
        dataframe.loc[
            (dataframe['close'] > dataframe['trend']) &
            (dataframe['close'].shift(1) <= dataframe['trend'].shift(1)) &
            (dataframe['obv'] < dataframe['obv'].shift(1)),
            'exit_long'] = 1

        # 平空（原平多）：价格下穿均线，OBV 上升（逆势）
        dataframe.loc[
            (dataframe['close'] < dataframe['trend']) &
            (dataframe['close'].shift(1) >= dataframe['trend'].shift(1)) &
            (dataframe['obv'] > dataframe['obv'].shift(1)),
            'exit_short'] = 1

        return dataframe
