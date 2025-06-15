from functools import reduce
from pandas import DataFrame
from freqtrade.strategy.interface import IStrategy
from freqtrade.strategy import IntParameter, DecimalParameter
import talib.abstract as ta
import technical.indicators as ftt


def EWO(dataframe: DataFrame, ema1=50, ema2=200):
    ema_short = ta.EMA(dataframe, timeperiod=ema1)
    ema_long = ta.EMA(dataframe, timeperiod=ema2)
    return (ema_short - ema_long) / dataframe['close'] * 100


class SMAOffsetProtectV3(IStrategy):
    """
    更新语法结构的 SMA Offset 策略
    """

    INTERFACE_VERSION = 3
    can_short = False  # 当前版本不做空

    timeframe = "5m"
    startup_candle_count = 200

    minimal_roi = {
        "0": 0.028,
        "10": 0.018,
        "30": 0.010,
        "40": 0.005
    }

    stoploss = -0.5
    trailing_stop = False

    # 参数化设置
    base_nb_candles_buy = IntParameter(5, 80, default=16, space="buy", optimize=True)
    base_nb_candles_sell = IntParameter(5, 80, default=20, space="sell", optimize=True)
    low_offset = DecimalParameter(0.9, 0.99, default=0.973, space="buy", optimize=True)
    high_offset = DecimalParameter(0.99, 1.1, default=1.010, space="sell", optimize=True)

    ewo_low = DecimalParameter(-20.0, -8.0, default=-19.931, space="buy", optimize=True)
    ewo_high = DecimalParameter(2.0, 12.0, default=5.672, space="buy", optimize=True)
    rsi_buy = IntParameter(30, 70, default=59, space="buy", optimize=True)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['EWO'] = EWO(dataframe, 50, 200)
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['ema_buy'] = ta.EMA(dataframe, timeperiod=self.base_nb_candles_buy.value)
        dataframe['ema_sell'] = ta.EMA(dataframe, timeperiod=self.base_nb_candles_sell.value)

        # Pump strength using ZEMA (or fallback to DEMA if zema deprecated)
        dataframe['zema_30'] = ftt.DEMA(dataframe, period=30)
        dataframe['zema_200'] = ftt.DEMA(dataframe, period=200)
        dataframe['pump_strength'] = (dataframe['zema_30'] - dataframe['zema_200']) / dataframe['zema_30']

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = []

        # 第一类买入条件（EWO 高 + RSI 低）
        conditions.append(
            (dataframe['close'] < dataframe['ema_buy'] * self.low_offset.value) &
            (dataframe['EWO'] > self.ewo_high.value) &
            (dataframe['rsi'] < self.rsi_buy.value) &
            (dataframe['volume'] > 0)
        )

        # 第二类买入条件（EWO 低）
        conditions.append(
            (dataframe['close'] < dataframe['ema_buy'] * self.low_offset.value) &
            (dataframe['EWO'] < self.ewo_low.value) &
            (dataframe['volume'] > 0)
        )

        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x | y, conditions),
                'enter_long'
            ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe['close'] > dataframe['ema_sell'] * self.high_offset.value) &
            (dataframe['volume'] > 0),
            'exit_long'
        ] = 1
        return dataframe
