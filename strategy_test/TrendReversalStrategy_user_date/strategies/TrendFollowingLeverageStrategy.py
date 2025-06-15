from functools import reduce
from pandas import DataFrame
from freqtrade.strategy import IStrategy
from freqtrade.strategy import DecimalParameter

import talib.abstract as ta

from freqtrade.strategy.interface import IStrategy

class TrendFollowingLeverageStrategy(IStrategy):

    INTERFACE_VERSION: int = 3
    # short
    can_short = True

    # ROI table:
    minimal_roi = {"0": 0.15, "30": 0.1, "60": 0.05}
    # minimal_roi = {"0": 1}

    # Stoploss:
    stoploss = -0.265

    # Trailing stop:
    trailing_stop = True
    trailing_stop_positive = 0.05
    trailing_stop_positive_offset = 0.1
    trailing_only_offset_is_reached = False

    timeframe = "5m"

class TrendFollowingLeverageStrategy(IStrategy):
    INTERFACE_VERSION = 3
    can_short = True

    # 参数化 ATR 阈值，用于 Hyperopt
    atr_threshold_low = DecimalParameter(0.001, 0.01, default=0.0025, space='buy')
    atr_threshold_high = DecimalParameter(0.005, 0.03, default=0.01, space='buy')

    def leverage(self, pair: str, current_time: 'datetime', current_rate: float,
                 proposed_leverage: float, max_leverage: float, side: str,
                 **kwargs) -> float:
        """
        动态根据标准化波动率（ATR/价格）调整杠杆，做空更保守。
        """

        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe is None or len(dataframe) < 20:
            return 2.0  # 安全默认值

        close = dataframe['close'].iloc[-1]
        atr = ta.ATR(dataframe, timeperiod=14).iloc[-1]
        normalized_atr = atr / close if close > 0 else 0

        # 杠杆逻辑（低波动高杠杆）
        if normalized_atr < self.atr_threshold_low.value:
            lev = 4.0
        elif normalized_atr < self.atr_threshold_high.value:
            lev = 2.5
        else:
            lev = 1.5

        # 做空时进一步降低杠杆
        if side == 'short':
            lev = min(lev, 2.0)

        return min(lev, max_leverage)            

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Calculate OBV
        dataframe['obv'] = ta.OBV(dataframe['close'], dataframe['volume'])
        
        # Add your trend following indicators here
        dataframe['trend'] = dataframe['close'].ewm(span=20, adjust=False).mean()
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Add your trend following buy signals here
        dataframe.loc[
            (dataframe['close'] > dataframe['trend']) & 
            (dataframe['close'].shift(1) <= dataframe['trend'].shift(1)) &
            (dataframe['obv'] > dataframe['obv'].shift(1)), 
            'enter_long'] = 1
        
        # Add your trend following sell signals here
        dataframe.loc[
            (dataframe['close'] < dataframe['trend']) & 
            (dataframe['close'].shift(1) >= dataframe['trend'].shift(1)) &
            (dataframe['obv'] < dataframe['obv'].shift(1)), 
            'enter_short'] = 1
        
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Add your trend following exit signals for long positions here
        dataframe.loc[
            (dataframe['close'] < dataframe['trend']) & 
            (dataframe['close'].shift(1) >= dataframe['trend'].shift(1)) &
            (dataframe['obv'] > dataframe['obv'].shift(1)), 
            'exit_long'] = 1
        
        # Add your trend following exit signals for short positions here
        dataframe.loc[
            (dataframe['close'] > dataframe['trend']) & 
            (dataframe['close'].shift(1) <= dataframe['trend'].shift(1)) &
            (dataframe['obv'] < dataframe['obv'].shift(1)), 
            'exit_short'] = 1
        
        return dataframe



