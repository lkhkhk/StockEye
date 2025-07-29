#!/bin/bash

# StocksEye 개발/테스트/운영 스크립트

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 프로젝트 루트 디렉토리 (스크립트가 어디서 실행되든 항상 프로젝트 루트로 이동)
SCRIPT_DIR=$(dirname "$(realpath "$0")")
PROJECT_ROOT="$SCRIPT_DIR"

# 함수 정의

# 서비스 빌드 및 재시작
build_and_restart() {
    local env=${1:-development} # 기본값 development
    echo -e "${YELLOW}>>> Docker Compose 서비스 빌드 및 재시작 (환경: $env)...${NC}"
    cd "$PROJECT_ROOT" || exit 1
    APP_ENV=$env docker compose up -d --build
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}>>> 서비스 빌드 및 재시작 완료.${NC}"
    else
        echo -e "${RED}>>> 서비스 빌드 및 재시작 실패.${NC}"
        exit 1
    fi
}

# API 서비스 테스트 실행
run_api_tests() {
    echo -e "${YELLOW}>>> API 서비스 테스트 실행...${NC}"
    cd "$PROJECT_ROOT" || exit 1
    # API 컨테이너의 작업 디렉토리가 /app/src/api 이므로, tests/ 로 경로 지정
    docker compose exec api pytest tests/
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}>>> API 서비스 테스트 통과.${NC}"
    else
        echo -e "${RED}>>> API 서비스 테스트 실패.${NC}"
        exit 1
    fi
}

# Bot 서비스 테스트 실행
run_bot_tests() {
    echo -e "${YELLOW}>>> Bot 서비스 테스트 실행...${NC}"
    cd "$PROJECT_ROOT" || exit 1
    # Bot 컨테이너의 작업 디렉토리가 /app 이므로, src/bot/tests/ 로 경로 지정
    docker compose exec bot pytest src/bot/tests/
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}>>> Bot 서비스 테스트 통과.${NC}"
    else
        echo -e "${RED}>>> Bot 서비스 테스트 실패.${NC}"
        exit 1
    fi
}

# 모든 테스트 실행
run_all_tests() {
    echo -e "${YELLOW}>>> 모든 서비스 테스트 실행...${NC}"
    run_api_tests
    run_bot_tests
    echo -e "${GREEN}>>> 모든 서비스 테스트 완료.${NC}"
}

# Docker 환경 정리
clean_env() {
    echo -e "${RED}>>> 경고: 이 작업은 모든 Docker 컨테이너, 네트워크, 볼륨을 영구적으로 삭제합니다.${NC}"
    echo -e "${RED}>>> 데이터베이스 데이터도 삭제되므로 주의하십시오.${NC}"
    read -p "정말 진행하시겠습니까? (y/N): " confirm
    if [[ "$confirm" == [yY] || "$confirm" == [yY][eE][sS] ]]; then
        echo -e "${YELLOW}>>> Docker 환경 정리 중...${NC}"
        cd "$PROJECT_ROOT" || exit 1
        docker compose down --volumes --remove-orphans
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}>>> Docker 환경 정리 완료.${NC}"
        else
            echo -e "${RED}>>> Docker 환경 정리 실패.${NC}"
            exit 1
        fi
    else
        echo -e "${YELLOW}>>> Docker 환경 정리 취소.${NC}"
    fi
}

# 도움말 표시
show_help() {
    echo "사용법: ./dev_ops.sh [명령어]"
    echo ""
    echo "명령어:"
    echo "  build       : Docker Compose 서비스를 빌드하고 재시작합니다."
    echo "  api-test    : API 서비스의 pytest를 실행합니다."
    echo "  bot-test    : Bot 서비스의 pytest를 실행합니다."
    echo "  all-test    : API 및 Bot 서비스의 모든 pytest를 실행합니다."
    echo "  clean       : 모든 Docker 컨테이너, 네트워크, 볼륨을 삭제합니다. (경고: 데이터 손실 가능)"
    echo "  help        : 이 도움말 메시지를 표시합니다."
    echo ""
    echo "예시:"
    echo "  ./dev_ops.sh build"
    echo "  ./dev_ops.sh all-test"
    echo "  ./dev_ops.sh clean"
}

# 메인 로직
case "$1" in
    build)
        build_and_restart "$2" # 환경 인자 전달
        ;;
    api-test)
        run_api_tests
        ;;
    bot-test)
        run_bot_tests
        ;;
    all-test)
        run_all_tests
        ;;
    clean)
        clean_env
        ;;
    help)
        show_help
        ;;
    *)
        echo -e "${RED}오류: 알 수 없는 명령어입니다. 'help'를 입력하여 사용법을 확인하세요.${NC}"
        show_help
        exit 1
        ;;
esac
