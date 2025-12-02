#!/bin/bash
# PostgreSQL DB 백업/복구 스크립트
# 사용법:
#   ./backup_restore.sh backup                          # 백업
#   ./backup_restore.sh restore <백업파일명>            # 복구

CONTAINER=stockeye-db
USER=postgres
DB=stocks_db
BACKUP_DIR=./db/backups

# 백업 디렉토리 생성
mkdir -p $BACKUP_DIR

if [ "$1" == "backup" ]; then
    FILE=$BACKUP_DIR/stocks_db_$(date +%Y-%m-%d_%H-%M-%S).sql.gz
    echo "백업 시작: $DB → $FILE"
    docker exec -t $CONTAINER pg_dump -U $USER $DB | gzip > $FILE
    if [ $? -eq 0 ]; then
        SIZE=$(du -h $FILE | cut -f1)
        echo "✅ 백업 완료: $FILE ($SIZE)"
    else
        echo "❌ 백업 실패"
        exit 1
    fi
elif [ "$1" == "restore" ] && [ -n "$2" ]; then
    if [ ! -f "$2" ]; then
        echo "❌ 백업 파일을 찾을 수 없습니다: $2"
        exit 1
    fi
    echo "복구 시작: $2 → $DB"
    echo "⚠️  경고: 기존 데이터가 모두 삭제됩니다!"
    read -p "정말 진행하시겠습니까? (y/N): " confirm
    if [[ "$confirm" == [yY] || "$confirm" == [yY][eE][sS] ]]; then
        gunzip < $2 | docker exec -i $CONTAINER psql -U $USER -d $DB
        if [ $? -eq 0 ]; then
            echo "✅ 복구 완료: $2"
        else
            echo "❌ 복구 실패"
            exit 1
        fi
    else
        echo "복구 취소됨"
        exit 0
    fi
else
    echo "사용법: $0 backup | restore <백업파일명>"
    echo ""
    echo "예시:"
    echo "  $0 backup"
    echo "  $0 restore db/backups/stocks_db_2025-12-03_00-00-00.sql.gz"
    exit 1
fi