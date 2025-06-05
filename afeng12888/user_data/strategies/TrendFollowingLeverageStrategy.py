from functools import reduce
from pandas import DataFrame
from freqtrade.strategy import IStrategy

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



