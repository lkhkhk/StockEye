#!/bin/bash
# PostgreSQL 컨테이너 DB 백업/복구 스크립트
# 사용법:
#   ./backup_restore.sh backup   # 백업 (백업파일: db_backup_YYYYMMDD.sql)
#   ./backup_restore.sh restore db_backup_YYYYMMDD.sql  # 복구

CONTAINER=postgres_db
USER=postgres
DB=service_db

if [ "$1" == "backup" ]; then
    FILE=db_backup_$(date +%Y%m%d).sql
    docker exec -t $CONTAINER pg_dump -U $USER $DB > $FILE
    echo "백업 완료: $FILE"
elif [ "$1" == "restore" ] && [ -n "$2" ]; then
    cat $2 | docker exec -i $CONTAINER psql -U $USER -d $DB
    echo "복구 완료: $2"
else
    echo "사용법: $0 backup | restore <백업파일명>"
    exit 1
fi 