#!/bin/bash
# 통합 서비스 운영 자동화 스크립트
# 사용법:
#   ./service_control.sh start|stop|restart|status|logs

case "$1" in
  start)
    docker compose up -d
    ;;
  stop)
    docker compose down
    ;;
  restart)
    docker compose down && docker compose up -d
    ;;
  status)
    docker compose ps
    ;;
  logs)
    docker compose logs --tail=100 -f
    ;;
  *)
    echo "사용법: $0 start|stop|restart|status|logs"
    exit 1
    ;;
esac 