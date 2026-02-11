"""
TTQuant Strategy Engine - 策略引擎主程序

从 strategies.toml 加载策略配置并运行
"""

import os
import sys
import logging
import toml
from typing import Dict, Any

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from strategy.engine import StrategyEngine
from strategy.strategies.ema_cross import EMACrossStrategy
from strategy.strategies.grid_trading import GridTradingStrategy
from strategy.strategies.momentum import MomentumStrategy

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('strategy_engine.log', mode='a')
    ]
)

logger = logging.getLogger(__name__)


# 策略类型映射
STRATEGY_CLASSES = {
    'ma_cross': EMACrossStrategy,
    'grid': GridTradingStrategy,
    'momentum': MomentumStrategy,
}


def load_config(config_path: str) -> Dict[str, Any]:
    """加载策略配置"""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, 'r', encoding='utf-8') as f:
        config = toml.load(f)

    return config


def create_strategy(strategy_config: Dict[str, Any]):
    """根据配置创建策略实例"""
    name = strategy_config['name']
    strategy_type = strategy_config['type']
    enabled = strategy_config.get('enabled', False)

    if not enabled:
        logger.info(f"Strategy {name} is disabled, skipping")
        return None

    if strategy_type not in STRATEGY_CLASSES:
        logger.warning(f"Unknown strategy type: {strategy_type}")
        return None

    # 合并参数
    params = strategy_config.get('parameters', {})
    params['symbol'] = strategy_config.get('symbol', 'BTCUSDT')
    params['exchange'] = strategy_config.get('exchange', 'okx')

    # 创建策略实例
    strategy_class = STRATEGY_CLASSES[strategy_type]
    strategy = strategy_class(name, params)

    logger.info(f"Created strategy: {name} ({strategy_type})")
    return strategy


def main():
    """主函数"""
    logger.info("=" * 80)
    logger.info("TTQuant Strategy Engine Starting")
    logger.info("=" * 80)

    # 加载配置
    config_path = os.getenv('STRATEGY_CONFIG', '/app/config/strategies.toml')
    logger.info(f"Loading config from: {config_path}")

    try:
        config = load_config(config_path)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        sys.exit(1)

    # 全局配置
    global_config = config.get('global', {})
    trading_mode = global_config.get('trading_mode', 'paper')
    log_level = global_config.get('log_level', 'info').upper()

    logger.info(f"Trading mode: {trading_mode}")
    logger.info(f"Log level: {log_level}")

    # 设置日志级别
    logging.getLogger().setLevel(getattr(logging, log_level))

    # 引擎配置
    # 根据环境变量决定连接哪个交易所
    exchange = os.getenv('EXCHANGE', 'okx')

    if exchange == 'okx':
        md_endpoints = [os.getenv('MD_ENDPOINT', 'tcp://md-okx:5558')]
        trade_endpoint = os.getenv('TRADE_ENDPOINT', 'tcp://gateway-okx:5560')
        order_endpoint = os.getenv('ORDER_ENDPOINT', 'tcp://gateway-okx:5559')
    else:  # binance
        md_endpoints = [os.getenv('MD_ENDPOINT', 'tcp://md-binance:5555')]
        trade_endpoint = os.getenv('TRADE_ENDPOINT', 'tcp://gateway-binance:5557')
        order_endpoint = os.getenv('ORDER_ENDPOINT', 'tcp://gateway-binance:5556')

    # 收集所有交易对
    symbols = set()
    for strategy_config in config.get('strategies', []):
        if strategy_config.get('enabled', False):
            symbols.add(strategy_config.get('symbol', 'BTCUSDT'))

    engine_config = {
        'md_endpoints': md_endpoints,
        'trade_endpoint': trade_endpoint,
        'order_endpoint': order_endpoint,
        'symbols': list(symbols),
        'use_protobuf': True,
        'risk_management': config.get('risk_management', {})
    }

    logger.info(f"Market data endpoints: {md_endpoints}")
    logger.info(f"Trade endpoint: {trade_endpoint}")
    logger.info(f"Order endpoint: {order_endpoint}")
    logger.info(f"Symbols: {list(symbols)}")

    # 创建引擎
    engine = StrategyEngine(engine_config)

    # 加载策略
    strategies_loaded = 0
    for strategy_config in config.get('strategies', []):
        strategy = create_strategy(strategy_config)
        if strategy:
            engine.add_strategy(strategy)
            strategies_loaded += 1

    if strategies_loaded == 0:
        logger.warning("No strategies loaded! Check your config file.")
        logger.info("Exiting...")
        sys.exit(0)

    logger.info(f"Loaded {strategies_loaded} strategies")
    logger.info("=" * 80)

    # 运行引擎
    try:
        engine.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Engine failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
