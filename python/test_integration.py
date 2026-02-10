#!/usr/bin/env python3
"""
TTQuant 数据持久化集成测试

这个脚本会：
1. 启动必要的服务
2. 等待数据收集
3. 验证数据写入
4. 生成测试报告
"""

import subprocess
import time
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

# 配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'ttquant_trading',
    'user': 'ttquant',
    'password': 'changeme'
}

DOCKER_COMPOSE_FILE = '../docker/docker-compose.yml'
WAIT_TIME = 60  # 等待数据收集的时间（秒）


def run_command(cmd, check=True):
    """运行 shell 命令"""
    print(f"执行: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"错误: {result.stderr}")
        return False
    return True


def check_docker():
    """检查 Docker 是否可用"""
    print("\n=== 检查 Docker ===")
    if not run_command("docker --version"):
        print("✗ Docker 未安装或未运行")
        return False
    print("✓ Docker 可用")
    return True


def start_services():
    """启动服务"""
    print("\n=== 启动服务 ===")

    # 启动 TimescaleDB
    print("启动 TimescaleDB...")
    if not run_command(f"docker compose -f {DOCKER_COMPOSE_FILE} up -d timescaledb"):
        return False

    # 等待数据库启动
    print("等待数据库启动...")
    time.sleep(15)

    # 检查数据库健康状态
    for i in range(10):
        result = subprocess.run(
            f"docker compose -f {DOCKER_COMPOSE_FILE} ps timescaledb",
            shell=True,
            capture_output=True,
            text=True
        )
        if "healthy" in result.stdout or "Up" in result.stdout:
            print("✓ TimescaleDB 已启动")
            break
        time.sleep(2)
    else:
        print("✗ TimescaleDB 启动超时")
        return False

    # 启动 Market Data 服务
    print("启动 Market Data 服务...")
    if not run_command(f"docker compose -f {DOCKER_COMPOSE_FILE} up -d md-binance"):
        return False

    # 启动 Gateway 服务
    print("启动 Gateway 服务...")
    if not run_command(f"docker compose -f {DOCKER_COMPOSE_FILE} up -d gateway-binance"):
        return False

    print("✓ 所有服务已启动")
    return True


def wait_for_data():
    """等待数据收集"""
    print(f"\n=== 等待数据收集 ({WAIT_TIME} 秒) ===")
    for i in range(WAIT_TIME):
        remaining = WAIT_TIME - i
        print(f"\r剩余时间: {remaining} 秒", end='', flush=True)
        time.sleep(1)
    print("\n✓ 等待完成")


def connect_db():
    """连接数据库"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"✗ 数据库连接失败: {e}")
        return None


def verify_market_data(conn):
    """验证行情数据"""
    print("\n=== 验证行情数据 ===")

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # 检查是否有数据
        cur.execute("SELECT COUNT(*) as count FROM market_data")
        count = cur.fetchone()['count']

        if count == 0:
            print("✗ 未找到行情数据")
            return False

        print(f"✓ 找到 {count} 条行情数据")

        # 检查最新数据
        cur.execute("""
            SELECT symbol, last_price, volume, exchange, time
            FROM market_data
            ORDER BY time DESC
            LIMIT 5
        """)

        rows = cur.fetchall()
        print("\n最新行情:")
        for row in rows:
            print(f"  {row['symbol']:10s} | {row['last_price']:12.2f} | "
                  f"{row['volume']:10.4f} | {row['exchange']:8s}")

        # 检查数据时效性（最新数据应该在最近 1 分钟内）
        cur.execute("""
            SELECT MAX(time) as latest_time FROM market_data
        """)
        latest_time = cur.fetchone()['latest_time']
        age_seconds = (datetime.now(latest_time.tzinfo) - latest_time).total_seconds()

        if age_seconds > 60:
            print(f"⚠ 最新数据已过时 ({age_seconds:.0f} 秒前)")
        else:
            print(f"✓ 数据实时性良好 ({age_seconds:.0f} 秒前)")

        return True


def verify_database_structure(conn):
    """验证数据库结构"""
    print("\n=== 验证数据库结构 ===")

    expected_tables = [
        'market_data',
        'orders',
        'trades',
        'positions',
        'account_balance',
        'metrics',
        'klines'
    ]

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
        """)

        tables = [row['tablename'] for row in cur.fetchall()]

        missing_tables = set(expected_tables) - set(tables)
        if missing_tables:
            print(f"✗ 缺少表: {', '.join(missing_tables)}")
            return False

        print(f"✓ 所有必需的表都存在")

        # 检查 hypertables
        cur.execute("""
            SELECT hypertable_name
            FROM timescaledb_information.hypertables
        """)

        hypertables = [row['hypertable_name'] for row in cur.fetchall()]
        print(f"✓ TimescaleDB hypertables: {', '.join(hypertables)}")

        return True


def generate_report(conn):
    """生成测试报告"""
    print("\n" + "=" * 60)
    print("测试报告")
    print("=" * 60)

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # 行情数据统计
        cur.execute("""
            SELECT
                symbol,
                exchange,
                COUNT(*) as count,
                MIN(time) as first_time,
                MAX(time) as last_time
            FROM market_data
            GROUP BY symbol, exchange
        """)

        print("\n行情数据统计:")
        for row in cur.fetchall():
            duration = row['last_time'] - row['first_time']
            print(f"  {row['symbol']:10s} ({row['exchange']:8s}): "
                  f"{row['count']:6d} 条, 时间跨度: {duration}")

        # 数据库大小
        cur.execute("""
            SELECT
                hypertable_name,
                pg_size_pretty(hypertable_size(format('%I.%I', hypertable_schema, hypertable_name)::regclass)) AS size
            FROM timescaledb_information.hypertables
        """)

        print("\n数据库大小:")
        for row in cur.fetchall():
            print(f"  {row['hypertable_name']:20s}: {row['size']}")

        # 写入速率
        cur.execute("""
            SELECT
                time_bucket('1 minute', time) AS bucket,
                COUNT(*) as records_per_minute
            FROM market_data
            WHERE time > NOW() - INTERVAL '10 minutes'
            GROUP BY bucket
            ORDER BY bucket DESC
            LIMIT 5
        """)

        print("\n最近写入速率 (每分钟):")
        for row in cur.fetchall():
            print(f"  {row['bucket']}: {row['records_per_minute']} 条/分钟")


def cleanup():
    """清理（可选）"""
    print("\n=== 清理 ===")
    response = input("是否停止服务? (y/N): ")
    if response.lower() == 'y':
        run_command(f"docker compose -f {DOCKER_COMPOSE_FILE} down", check=False)
        print("✓ 服务已停止")


def main():
    """主函数"""
    print("=" * 60)
    print("TTQuant 数据持久化集成测试")
    print("=" * 60)

    # 检查 Docker
    if not check_docker():
        sys.exit(1)

    # 启动服务
    if not start_services():
        print("\n✗ 服务启动失败")
        sys.exit(1)

    # 等待数据收集
    wait_for_data()

    # 连接数据库
    conn = connect_db()
    if not conn:
        sys.exit(1)

    try:
        # 验证数据库结构
        if not verify_database_structure(conn):
            print("\n✗ 数据库结构验证失败")
            sys.exit(1)

        # 验证行情数据
        if not verify_market_data(conn):
            print("\n✗ 行情数据验证失败")
            sys.exit(1)

        # 生成报告
        generate_report(conn)

        print("\n" + "=" * 60)
        print("✓ 所有测试通过！")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()

    # 清理
    cleanup()


if __name__ == "__main__":
    main()
