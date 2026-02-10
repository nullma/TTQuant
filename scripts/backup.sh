#!/bin/bash
# =========================================================
# TTQuant 数据库备份脚本
# 用法: bash scripts/backup.sh
# 建议: 通过 crontab 每天凌晨 3 点执行
#   0 3 * * * cd /root/TTQuant && bash scripts/backup.sh
# =========================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

BACKUP_DIR="$SCRIPT_DIR/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/ttquant_backup_${DATE}.sql.gz"
MAX_BACKUPS=7

echo "[$(date)] TTQuant 数据库备份开始"

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 执行 pg_dump 并压缩
echo "  导出数据库..."
docker exec ttquant-timescaledb pg_dump \
    -U ttquant \
    -d ttquant_trading \
    --no-owner \
    --no-privileges \
    2>/dev/null | gzip > "$BACKUP_FILE"

# 检查备份文件
if [ -s "$BACKUP_FILE" ]; then
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "  ✓ 备份成功: $BACKUP_FILE ($SIZE)"
else
    echo "  ✗ 备份失败: 文件为空"
    rm -f "$BACKUP_FILE"
    exit 1
fi

# 清理旧备份（保留最近 N 份）
BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/ttquant_backup_*.sql.gz 2>/dev/null | wc -l)
if [ "$BACKUP_COUNT" -gt "$MAX_BACKUPS" ]; then
    DELETE_COUNT=$((BACKUP_COUNT - MAX_BACKUPS))
    echo "  清理旧备份 ($DELETE_COUNT 份)..."
    ls -1t "$BACKUP_DIR"/ttquant_backup_*.sql.gz | tail -n "$DELETE_COUNT" | xargs rm -f
fi

echo "[$(date)] 备份完成 (保留 $MAX_BACKUPS 份)"

# 列出当前备份
echo ""
echo "当前备份列表:"
ls -lh "$BACKUP_DIR"/ttquant_backup_*.sql.gz 2>/dev/null | awk '{print "  " $NF " (" $5 ")"}'
