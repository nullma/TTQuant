#!/usr/bin/env python3
"""
TTQuant 数据库测试脚本

测试数据持久化功能：
1. 连接数据库
2. 查询行情数据
3. 查询订单和成交记录
4. 查询持仓快照
5. 性能测试
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import time
from datetime import datetime, timedelta
import sys

# 数据库连接配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'ttquant_trading',
    'user': 'ttquant',
    'password': 'changeme'
}


def connect_db():
    """连接数据库"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("✓ 数据库连接成功")
        return conn
    except Exception as e:
        print(f"✗ 数据库连接失败: {e}")
        sys.exit(1)


def test_market_data(conn):
    """测试行情数据查询"""
    print("\n=== 测试行情数据 ===")

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # 查询最近的行情数据
        cur.execute("""
            SELECT symbol, last_price, volume, exchange, time
            FROM market_data
            ORDER BY time DESC
            LIMIT 10
        """)

        rows = cur.fetchall()

        if rows:
            print(f"✓ 查询到 {len(rows)} 条行情数据")
            print("\n最新行情:")
            for row in rows[:5]:
                print(f"  {row['symbol']:10s} | {row['last_price']:12.2f} | "
                      f"{row['volume']:10.4f} | {row['exchange']:8s} | {row['time']}")
        else:
            print("✗ 未查询到行情数据")

        # 统计行情数据量
        cur.execute("""
            SELECT
                symbol,
                exchange,
                COUNT(*) as count,
                MIN(time) as first_time,
                MAX(time) as last_time
            FROM market_data
            GROUP BY symbol, exchange
            ORDER BY count DESC
        """)

        stats = cur.fetchall()
        if stats:
            print("\n行情数据统计:")
            for stat in stats:
                duration = stat['last_time'] - stat['first_time']
                print(f"  {stat['symbol']:10s} ({stat['exchange']:8s}): "
                      f"{stat['count']:6d} 条, 时间范围: {duration}")


def test_orders(conn):
    """测试订单数据查询"""
    print("\n=== 测试订单数据 ===")

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # 查询最近的订单
        cur.execute("""
            SELECT order_id, strategy_id, symbol, side, price, volume, time
            FROM orders
            ORDER BY time DESC
            LIMIT 10
        """)

        rows = cur.fetchall()

        if rows:
            print(f"✓ 查询到 {len(rows)} 条订单记录")
            print("\n最新订单:")
            for row in rows[:5]:
                print(f"  {row['order_id']:20s} | {row['strategy_id']:15s} | "
                      f"{row['symbol']:10s} | {row['side']:4s} | "
                      f"{row['price']:10.2f} x {row['volume']:3d} | {row['time']}")
        else:
            print("✗ 未查询到订单数据")

        # 按策略统计订单
        cur.execute("""
            SELECT
                strategy_id,
                COUNT(*) as total_orders,
                SUM(CASE WHEN side = 'BUY' THEN 1 ELSE 0 END) as buy_orders,
                SUM(CASE WHEN side = 'SELL' THEN 1 ELSE 0 END) as sell_orders
            FROM orders
            GROUP BY strategy_id
            ORDER BY total_orders DESC
        """)

        stats = cur.fetchall()
        if stats:
            print("\n订单统计 (按策略):")
            for stat in stats:
                print(f"  {stat['strategy_id']:15s}: "
                      f"总计 {stat['total_orders']:4d} | "
                      f"买 {stat['buy_orders']:4d} | 卖 {stat['sell_orders']:4d}")


def test_trades(conn):
    """测试成交数据查询"""
    print("\n=== 测试成交数据 ===")

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # 查询最近的成交
        cur.execute("""
            SELECT trade_id, order_id, strategy_id, symbol, side,
                   filled_price, filled_volume, status, error_message, time
            FROM trades
            ORDER BY time DESC
            LIMIT 10
        """)

        rows = cur.fetchall()

        if rows:
            print(f"✓ 查询到 {len(rows)} 条成交记录")
            print("\n最新成交:")
            for row in rows[:5]:
                status_icon = "✓" if row['status'] == 'FILLED' else "✗"
                print(f"  {status_icon} {row['trade_id']:20s} | {row['strategy_id']:15s} | "
                      f"{row['symbol']:10s} | {row['side']:4s} | "
                      f"{row['filled_price']:10.2f} x {row['filled_volume']:3d} | "
                      f"{row['status']:8s}")
                if row['error_message']:
                    print(f"    错误: {row['error_message']}")
        else:
            print("✗ 未查询到成交数据")

        # 成交统计
        cur.execute("""
            SELECT
                strategy_id,
                COUNT(*) as total_trades,
                SUM(CASE WHEN status = 'FILLED' THEN 1 ELSE 0 END) as filled_trades,
                SUM(CASE WHEN status = 'REJECTED' THEN 1 ELSE 0 END) as rejected_trades,
                AVG(CASE WHEN status = 'FILLED' THEN filled_price ELSE NULL END) as avg_fill_price
            FROM trades
            GROUP BY strategy_id
            ORDER BY total_trades DESC
        """)

        stats = cur.fetchall()
        if stats:
            print("\n成交统计 (按策略):")
            for stat in stats:
                fill_rate = (stat['filled_trades'] / stat['total_trades'] * 100) if stat['total_trades'] > 0 else 0
                print(f"  {stat['strategy_id']:15s}: "
                      f"总计 {stat['total_trades']:4d} | "
                      f"成交 {stat['filled_trades']:4d} | "
                      f"拒绝 {stat['rejected_trades']:4d} | "
                      f"成交率 {fill_rate:5.1f}% | "
                      f"均价 {stat['avg_fill_price'] or 0:10.2f}")


def test_positions(conn):
    """测试持仓数据查询"""
    print("\n=== 测试持仓数据 ===")

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # 查询最新持仓
        cur.execute("""
            SELECT strategy_id, symbol, position, avg_price, unrealized_pnl, time
            FROM latest_positions
            ORDER BY time DESC
        """)

        rows = cur.fetchall()

        if rows:
            print(f"✓ 查询到 {len(rows)} 个持仓")
            print("\n当前持仓:")
            for row in rows:
                print(f"  {row['strategy_id']:15s} | {row['symbol']:10s} | "
                      f"仓位: {row['position']:6d} | 均价: {row['avg_price']:10.2f} | "
                      f"未实现盈亏: {row['unrealized_pnl']:10.2f}")
        else:
            print("✗ 未查询到持仓数据")


def test_performance(conn):
    """性能测试"""
    print("\n=== 性能测试 ===")

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # 测试查询速度
        start = time.time()
        cur.execute("""
            SELECT COUNT(*) as count FROM market_data
        """)
        total_count = cur.fetchone()['count']
        elapsed = time.time() - start
        print(f"✓ 行情数据总量查询: {total_count} 条, 耗时: {elapsed*1000:.2f}ms")

        # 测试时间范围查询
        start = time.time()
        cur.execute("""
            SELECT COUNT(*) as count
            FROM market_data
            WHERE time > NOW() - INTERVAL '1 hour'
        """)
        recent_count = cur.fetchone()['count']
        elapsed = time.time() - start
        print(f"✓ 最近1小时行情查询: {recent_count} 条, 耗时: {elapsed*1000:.2f}ms")

        # 测试聚合查询
        start = time.time()
        cur.execute("""
            SELECT
                symbol,
                COUNT(*) as tick_count,
                AVG(last_price) as avg_price,
                MIN(last_price) as min_price,
                MAX(last_price) as max_price
            FROM market_data
            WHERE time > NOW() - INTERVAL '1 hour'
            GROUP BY symbol
        """)
        agg_results = cur.fetchall()
        elapsed = time.time() - start
        print(f"✓ 聚合统计查询: {len(agg_results)} 个品种, 耗时: {elapsed*1000:.2f}ms")

        if agg_results:
            print("\n最近1小时统计:")
            for row in agg_results:
                print(f"  {row['symbol']:10s}: {row['tick_count']:6d} ticks | "
                      f"均价: {row['avg_price']:10.2f} | "
                      f"最低: {row['min_price']:10.2f} | 最高: {row['max_price']:10.2f}")


def test_data_integrity(conn):
    """测试数据完整性"""
    print("\n=== 数据完整性检查 ===")

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # 检查订单和成交的关联
        cur.execute("""
            SELECT
                COUNT(DISTINCT o.order_id) as total_orders,
                COUNT(DISTINCT t.order_id) as orders_with_trades
            FROM orders o
            LEFT JOIN trades t ON o.order_id = t.order_id
        """)

        result = cur.fetchone()
        if result:
            print(f"✓ 订单总数: {result['total_orders']}")
            print(f"✓ 有成交记录的订单: {result['orders_with_trades']}")

        # 检查是否有孤立的成交记录
        cur.execute("""
            SELECT COUNT(*) as orphan_trades
            FROM trades t
            LEFT JOIN orders o ON t.order_id = o.order_id
            WHERE o.order_id IS NULL
        """)

        orphan = cur.fetchone()['orphan_trades']
        if orphan > 0:
            print(f"⚠ 发现 {orphan} 条孤立的成交记录（无对应订单）")
        else:
            print("✓ 无孤立成交记录")


def main():
    """主函数"""
    print("=" * 60)
    print("TTQuant 数据库测试")
    print("=" * 60)

    # 连接数据库
    conn = connect_db()

    try:
        # 运行测试
        test_market_data(conn)
        test_orders(conn)
        test_trades(conn)
        test_positions(conn)
        test_data_integrity(conn)
        test_performance(conn)

        print("\n" + "=" * 60)
        print("测试完成")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
