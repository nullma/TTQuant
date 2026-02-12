"""
ML Strategy - 机器学习策略示例

使用 ML 因子进行交易决策
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, Optional
import logging

from strategy.base_strategy import BaseStrategy, Signal
from strategy.factors.ml_factor import MLFactor
from strategy.factors.feature_engineering import FeatureEngineering
from proto.market_data_pb2 import MarketData
from proto.trade_pb2 import Trade

logger = logging.getLogger(__name__)


class MLStrategy(BaseStrategy):
    """
    机器学习策略

    使用训练好的 ML 模型预测市场方向并生成交易信号
    """

    def __init__(self, strategy_id: str, config: Dict):
        super().__init__(strategy_id, config)

        # 特征工程
        lookback_period = config.get('lookback_period', 50)
        self.feature_eng = FeatureEngineering(lookback_period=lookback_period)

        # ML 因子
        ml_config = {
            'model_type': config.get('model_type', 'random_forest'),
            'feature_names': config.get('feature_names', [
                'returns', 'volatility', 'rsi_14', 'macd',
                'bb_position', 'volume_ratio'
            ]),
            'prediction_horizon': config.get('prediction_horizon', 1),
            'model_dir': config.get('model_dir', 'models'),
            'load_model': True  # 加载已训练的模型
        }
        self.ml_factor = MLFactor(
            factor_id=f"{strategy_id}_ml_factor",
            config=ml_config
        )

        # 交易参数
        self.symbol = config.get('symbol', 'BTCUSDT')
        self.position_size = config.get('position_size', 0.1)
        self.confidence_threshold = config.get('confidence_threshold', 0.6)
        self.stop_loss_pct = config.get('stop_loss_pct', 0.02)
        self.take_profit_pct = config.get('take_profit_pct', 0.04)

        # 状态
        self.last_price = 0.0
        self.entry_price = 0.0

        logger.info(f"MLStrategy initialized: {strategy_id}")
        logger.info(f"  Symbol: {self.symbol}")
        logger.info(f"  Confidence threshold: {self.confidence_threshold}")

    def on_market_data(self, md: MarketData) -> Optional[Signal]:
        """
        处理市场数据

        Args:
            md: 市场数据

        Returns:
            交易信号（如果有）
        """
        if md.symbol != self.symbol:
            return None

        # 更新特征
        self.feature_eng.update(md.symbol, md.last_price, md.volume)
        self.last_price = md.last_price

        # 提取特征
        features = self.feature_eng.extract_features(md.symbol)
        if not features:
            return None

        # 计算 ML 因子
        factor_value = self.ml_factor.calculate(features)

        # 检查置信度
        if factor_value.confidence < self.confidence_threshold:
            logger.debug(f"Low confidence: {factor_value.confidence:.4f}")
            return None

        # 获取当前持仓
        current_position = self.portfolio.get_position(md.symbol)

        # 生成交易信号
        signal = None

        if factor_value.value > 0:  # 预测上涨
            if current_position <= 0:
                # 开多仓
                signal = Signal(
                    symbol=md.symbol,
                    side='BUY',
                    price=md.last_price,
                    volume=self.position_size,
                    reason=f"ML prediction: UP (confidence={factor_value.confidence:.4f})"
                )
                self.entry_price = md.last_price

        elif factor_value.value < 0:  # 预测下跌
            if current_position >= 0:
                # 开空仓或平多仓
                signal = Signal(
                    symbol=md.symbol,
                    side='SELL',
                    price=md.last_price,
                    volume=abs(current_position) if current_position > 0 else self.position_size,
                    reason=f"ML prediction: DOWN (confidence={factor_value.confidence:.4f})"
                )
                self.entry_price = md.last_price

        # 止损止盈检查
        if current_position != 0 and self.entry_price > 0:
            pnl_pct = (md.last_price - self.entry_price) / self.entry_price
            if current_position > 0:
                pnl_pct = pnl_pct
            else:
                pnl_pct = -pnl_pct

            # 止损
            if pnl_pct < -self.stop_loss_pct:
                signal = Signal(
                    symbol=md.symbol,
                    side='SELL' if current_position > 0 else 'BUY',
                    price=md.last_price,
                    volume=abs(current_position),
                    reason=f"Stop loss triggered: {pnl_pct:.2%}"
                )

            # 止盈
            elif pnl_pct > self.take_profit_pct:
                signal = Signal(
                    symbol=md.symbol,
                    side='SELL' if current_position > 0 else 'BUY',
                    price=md.last_price,
                    volume=abs(current_position),
                    reason=f"Take profit triggered: {pnl_pct:.2%}"
                )

        if signal:
            logger.info(f"Signal generated: {signal.side} {signal.volume} @ {signal.price:.2f} - {signal.reason}")

        return signal

    def on_trade(self, trade: Trade):
        """
        处理成交回报

        Args:
            trade: 成交回报
        """
        super().on_trade(trade)

        if trade.status == "FILLED":
            logger.info(f"Trade filled: {trade.side} {trade.filled_volume} @ {trade.filled_price:.2f}")

            # 更新入场价格
            if trade.side == "BUY":
                self.entry_price = trade.filled_price
            elif trade.side == "SELL":
                self.entry_price = 0.0
