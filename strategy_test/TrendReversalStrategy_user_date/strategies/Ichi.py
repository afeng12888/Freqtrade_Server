from freqtrade.strategy import IStrategy
from pandas import DataFrame
from technical.indicators import ichimoku
import talib.abstract as ta
import logging
from datetime import datetime
import os

logger = logging.getLogger(__name__)

# Setup logging to file
LOG_FILENAME = datetime.now().strftime('ichimoku_%d%m%Y.log')
if os.path.exists(LOG_FILENAME):
    os.remove(LOG_FILENAME)


for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.basicConfig(filename=LOG_FILENAME, level=logging.DEBUG, format='%(asctime)s :: %(message)s')
logging.info("Ichimoku strategy initialized.")


class IchiV3(IStrategy):
    """
    Ichimoku + EMA 策略（兼容 Freqtrade v2024+）
    """

    INTERFACE_VERSION = 3
    can_short = False

    timeframe = '15m'
    stoploss = -0.20

    order_types = {
        'buy': 'limit',
        'sell': 'limit',
        'stoploss': 'limit',
        'stoploss_on_exchange': True
    }

    minimal_roi = {
        "60": 0,
        "45": 0.0025 / 2,
        "30": 0.003 / 2,
        "15": 0.005 / 2,
        "10": 0.0075 / 2,
        "5": 0.01 / 2,
        "0": 0.02 / 2,
    }

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        ichi = ichimoku(dataframe)
        dataframe['tenkan'] = ichi['tenkan_sen']
        dataframe['kijun'] = ichi['kijun_sen']
        dataframe['senkou_a'] = ichi['senkou_span_a']
        dataframe['senkou_b'] = ichi['senkou_span_b']
        dataframe['cloud_green'] = ichi['cloud_green']
        dataframe['cloud_red'] = ichi['cloud_red']
        dataframe['chikou'] = ichi['chikou_span']

        dataframe['ema8'] = ta.EMA(dataframe, timeperiod=8)
        dataframe['ema13'] = ta.EMA(dataframe, timeperiod=13)
        dataframe['ema21'] = ta.EMA(dataframe, timeperiod=21)
        dataframe['ema55'] = ta.EMA(dataframe, timeperiod=55)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['open'].shift(1) < dataframe['senkou_b'].shift(1)) &
                (dataframe['close'].shift(1) > dataframe['senkou_b'].shift(1)) &
                (dataframe['open'] > dataframe['senkou_b']) &
                (dataframe['close'] > dataframe['senkou_b']) &
                (dataframe['cloud_green'] == True) &
                (dataframe['tenkan'] > dataframe['kijun']) &
                (dataframe['tenkan'].shift(1) < dataframe['kijun'].shift(1)) &
                (dataframe['close'].shift(-26) > dataframe['close'].shift(26)) &
                (dataframe['ema21'] > dataframe['ema55']) &
                (dataframe['ema13'] > dataframe['ema21']) &
                (dataframe['ema8'] > dataframe['ema13'])
            ),
            'enter_long'
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe['close'].shift(-26) <= dataframe['close'].shift(26)),
            'exit_long'
        ] = 1

        return dataframe
