#!/bin/bash

# StockEye 개발/테스트/운영 스크립트

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 프로젝트 루트 디렉토리 (스크립트가 어디서 실행되든 항상 프로젝트 루트로 이동)
SCRIPT_DIR=$(dirname "$(realpath "$0")")
PROJECT_ROOT="$SCRIPT_DIR"

# 함수 정의

# Get 프로젝트명
get_project_name() {
    local script_name="$0"
    local file_name=$(basename "$script_name")
    local name_without_extension="${file_name%.*}"
    echo ${name_without_extension}
}

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
    local env=${1:-development} # 기본값 development
    local test_type=${2:-all} # 기본값 all (unit, integration, e2e, all)
    
    echo -e "${YELLOW}>>> API 서비스 테스트 실행 (환경: $env, 타입: $test_type)...${NC}"
    cd "$PROJECT_ROOT" || exit 1
    
    case "$test_type" in
        unit)
            APP_ENV=$env docker compose exec api pytest src/api/tests/unit
            ;;
        integration)
            APP_ENV=$env docker compose exec api pytest src/api/tests/integration
            ;;
        e2e)
            APP_ENV=$env docker compose exec api pytest src/api/tests/e2e
            ;;
        all|*)
            APP_ENV=$env docker compose exec api pytest src/api/tests/
            ;;
    esac
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}>>> API 서비스 테스트 통과.${NC}"
    else
        echo -e "${RED}>>> API 서비스 테스트 실패.${NC}"
        exit 1
    fi
}

# Bot 서비스 테스트 실행
run_bot_tests() {
    local env=${1:-development} # 기본값 development
    echo -e "${YELLOW}>>> Bot 서비스 테스트 실행 (환경: $env)...${NC}"
    cd "$PROJECT_ROOT" || exit 1
    APP_ENV=$env docker compose exec bot pytest src/bot/tests/unit
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}>>> Bot 서비스 테스트 통과.${NC}"
    else
        echo -e "${RED}>>> Bot 서비스 테스트 실패.${NC}"
        exit 1
    fi
}

# Worker 서비스 테스트 실행
run_worker_tests() {
    local env=${1:-development} # 기본값 development
    echo -e "${YELLOW}>>> Worker 서비스 테스트 실행 (환경: $env)...${NC}"
    cd "$PROJECT_ROOT" || exit 1
    APP_ENV=$env docker compose exec worker pytest src/worker/tests/unit
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}>>> Worker 서비스 테스트 통과.${NC}"
    else
        echo -e "${RED}>>> Worker 서비스 테스트 실패.${NC}"
        exit 1
    fi
}

# Common 공통 모듈 테스트 실행
run_common_tests() {
    local env=${1:-development} # 기본값 development
    echo -e "${YELLOW}>>> Common 공통 모듈 테스트 실행 (환경: $env)...${NC}"
    cd "$PROJECT_ROOT" || exit 1
    docker build -t stockeye-common-tester -f src/common/Dockerfile.test . && docker run --rm stockeye-common-tester
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}>>> Common 공통 모듈 테스트 통과.${NC}"
    else
        echo -e "${RED}>>> Common 공통 모듈 테스트 실패.${NC}"
        exit 1
    fi
}

# 모든 테스트 실행
run_all_tests() {
    echo -e "${YELLOW}>>> 모든 서비스 테스트 실행...${NC}"
    run_common_tests "$@"
    run_worker_tests "$@"
    run_api_tests "$@"
    run_bot_tests "$@"
    echo -e "${GREEN}>>> 모든 서비스 테스트 완료.${NC}"
}

# 특정 서비스 빌드 및 재시작
build_and_restart_service() {
    local service_name=${1:-api} # 기본값 api
    local env=${2:-development} # 기본값 development
    echo -e "${YELLOW}>>> 서비스 '${service_name}' 빌드 및 재시작 (환경: $env)...${NC}"
    cd "$PROJECT_ROOT" || exit 1
    APP_ENV=$env docker compose up -d --build "stockeye-${service_name}"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}>>> 서비스 빌드 및 재시작 완료.${NC}"
    else
        echo -e "${RED}>>> 서비스 빌드 및 재시작 실패.${NC}"
        exit 1
    fi
}

# 서비스 상태 확인
show_status() {
    echo -e "${BLUE}>>> Docker Compose 서비스 상태 확인...${NC}"
    cd "$PROJECT_ROOT" || exit 1
    docker compose ps
}

# 서비스 로그 확인
show_logs() {
    local service_name=${1:-all}
    local lines=${2:-50}
    
    cd "$PROJECT_ROOT" || exit 1
    
    if [ "$service_name" == "all" ]; then
        echo -e "${BLUE}>>> 모든 서비스 로그 확인 (최근 $lines 줄)...${NC}"
        docker compose logs --tail=$lines
    else
        echo -e "${BLUE}>>> 서비스 '${service_name}' 로그 확인 (최근 $lines 줄)...${NC}"
        docker compose logs --tail=$lines "stockeye-${service_name}"
    fi
}

# 서비스 재시작 (빌드 없이)
restart_service() {
    local service_name=${1:-all}
    
    cd "$PROJECT_ROOT" || exit 1
    
    if [ "$service_name" == "all" ]; then
        echo -e "${YELLOW}>>> 모든 서비스 재시작...${NC}"
        docker compose restart
    else
        echo -e "${YELLOW}>>> 서비스 '${service_name}' 재시작...${NC}"
        docker compose restart "stockeye-${service_name}"
    fi
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}>>> 재시작 완료.${NC}"
    else
        echo -e "${RED}>>> 재시작 실패.${NC}"
        exit 1
    fi
}

# Docker 환경 정리
clean_env() {
    local is_clear_db=${1:-N} # 기본값 N
    local env=${2:-development} # 기본값 development
    
    echo -e "${RED}>>> 경고: 이 작업은 모든 Docker 컨테이너, 네트워크, 볼륨을 영구적으로 삭제합니다. (환경: $env)${NC}"
    if [[ "$is_clear_db" == [yY] ]]; then
        echo -e "${RED}>>> 데이터베이스 데이터도 삭제되므로 주의하십시오.${NC}"
    fi
    
    read -p "정말 진행하시겠습니까? (y/N): " confirm
    if [[ "$confirm" == [yY] || "$confirm" == [yY][eE][sS] ]]; then
        echo -e "${YELLOW}>>> Docker 환경 정리 중 (환경: $env)...${NC}"
        cd "$PROJECT_ROOT" || exit 1
        APP_ENV=$env docker compose down --volumes --remove-orphans
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}>>> Docker 환경 정리 완료.${NC}"
            if [[ "$is_clear_db" == [yY] ]]; then
                sudo rm -rf ./db/* ./logs/*
                echo -e "${GREEN}>>> DB files, logs 삭제 완료.${NC}"
            else
                sudo rm -rf ./logs/*
                echo -e "${GREEN}>>> logs 삭제 완료.${NC}"
            fi
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
    echo "사용법: ./stockeye.sh [명령어] [옵션]"
    echo ""
    echo "=== 서비스 관리 ==="
    echo "  build [env]              : Docker Compose 서비스를 빌드하고 재시작합니다."
    echo "  rebuild [service] [env]  : 특정 서비스를 빌드하고 재시작합니다."
    echo "  restart [service]        : 서비스를 재시작합니다 (빌드 없이)."
    echo "  status                   : 모든 서비스의 상태를 확인합니다."
    echo "  logs [service] [lines]   : 서비스 로그를 확인합니다."
    echo "  clean [Y/N] [env]        : Docker 환경을 정리합니다."
    echo ""
    echo "=== 테스트 실행 ==="
    echo "  all-test [env]           : 모든 서비스의 테스트를 실행합니다."
    echo "  api-test [env] [type]    : API 서비스 테스트를 실행합니다."
    echo "                             type: unit, integration, e2e, all (기본값: all)"
    echo "  bot-test [env]           : Bot 서비스 테스트를 실행합니다."
    echo "  worker-test [env]        : Worker 서비스 테스트를 실행합니다."
    echo "  common-test [env]        : Common 모듈 테스트를 실행합니다."
    echo ""
    echo "=== 기타 ==="
    echo "  help                     : 이 도움말 메시지를 표시합니다."
    echo ""
    echo "환경 (env): development (기본값), production"
    echo "서비스: api, bot, worker, db, redis, all"
    echo ""
    echo "예시:"
    echo "  ./stockeye.sh build"
    echo "  ./stockeye.sh build production"
    echo "  ./stockeye.sh rebuild api"
    echo "  ./stockeye.sh restart bot"
    echo "  ./stockeye.sh status"
    echo "  ./stockeye.sh logs api 100"
    echo "  ./stockeye.sh api-test development unit"
    echo "  ./stockeye.sh all-test"
    echo "  ./stockeye.sh clean"
    echo "  ./stockeye.sh clean Y development"
}

# 메인 로직
main() {
    case "$1" in
        build)
            shift
            build_and_restart "$@"
            ;;
        rebuild)
            shift
            build_and_restart_service "$@"
            ;;
        restart)
            shift
            restart_service "$@"
            ;;
        status)
            show_status
            ;;
        logs)
            shift
            show_logs "$@"
            ;;
        all-test)
            shift
            run_all_tests "$@"
            ;;
        api-test)
            shift
            run_api_tests "$@"
            ;;
        bot-test)
            shift
            run_bot_tests "$@"
            ;;
        worker-test)
            shift
            run_worker_tests "$@"
            ;;
        common-test)
            shift
            run_common_tests "$@"
            ;;
        clean)
            shift
            clean_env "$@"
            ;;
        help|--help|-h)
            show_help
            ;;
        "")
            echo -e "${RED}오류: 명령어를 입력하세요.${NC}"
            show_help
            exit 1
            ;;
        *)
            echo -e "${RED}오류: 알 수 없는 명령어입니다: $1${NC}"
            show_help
            exit 1
            ;;
    esac
}

# 메인 함수 호출
main "$@"
