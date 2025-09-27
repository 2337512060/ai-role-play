#!/bin/bash
# AI Paimon Backend 启动脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印彩色输出
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Docker是否安装
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
}

# 检查端口是否被占用
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_warning "Port $port is already in use"
        return 1
    fi
    return 0
}

# 显示帮助信息
show_help() {
    echo "AI Paimon Backend 启动脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  start         启动服务"
    echo "  stop          停止服务"
    echo "  restart       重启服务"
    echo "  logs          查看日志"
    echo "  status        查看服务状态"
    echo "  build         构建镜像"
    echo "  clean         清理容器和镜像"
    echo "  test          运行测试"
    echo "  dev           开发模式启动"
    echo "  prod          生产模式启动"
    echo "  with-nginx    启动时包含Nginx"
    echo "  with-db       启动时包含数据库"
    echo "  --help, -h    显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 start              # 启动基础服务"
    echo "  $0 dev                # 开发模式启动"
    echo "  $0 start with-nginx   # 启动服务并包含Nginx"
    echo "  $0 start with-db      # 启动服务并包含数据库"
}

# 构建镜像
build_image() {
    print_info "Building Docker image..."
    docker build -t ai-paimon-backend:latest .
    print_success "Docker image built successfully"
}

# 启动服务
start_services() {
    local profiles=""

    # 处理额外的profile参数
    for arg in "$@"; do
        case $arg in
            with-nginx)
                profiles="$profiles --profile with-nginx"
                ;;
            with-db)
                profiles="$profiles --profile with-db"
                ;;
            with-redis)
                profiles="$profiles --profile with-redis"
                ;;
        esac
    done

    print_info "Starting AI Paimon Backend services..."

    if command -v docker-compose &> /dev/null; then
        docker-compose up -d $profiles
    else
        docker compose up -d $profiles
    fi

    print_success "Services started successfully"
    print_info "API documentation: http://localhost:8000/docs"
    print_info "Health check: http://localhost:8000/health"
}

# 停止服务
stop_services() {
    print_info "Stopping services..."

    if command -v docker-compose &> /dev/null; then
        docker-compose down
    else
        docker compose down
    fi

    print_success "Services stopped"
}

# 重启服务
restart_services() {
    print_info "Restarting services..."
    stop_services
    sleep 2
    start_services "$@"
}

# 查看日志
show_logs() {
    if command -v docker-compose &> /dev/null; then
        docker-compose logs -f
    else
        docker compose logs -f
    fi
}

# 查看服务状态
show_status() {
    print_info "Service status:"

    if command -v docker-compose &> /dev/null; then
        docker-compose ps
    else
        docker compose ps
    fi

    echo ""
    print_info "Checking health endpoints..."

    # 检查API健康状态
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        print_success "API service is healthy"
    else
        print_error "API service is not responding"
    fi
}

# 清理
clean_all() {
    print_info "Cleaning up containers and images..."

    # 停止并删除容器
    if command -v docker-compose &> /dev/null; then
        docker-compose down -v --remove-orphans
    else
        docker compose down -v --remove-orphans
    fi

    # 删除镜像
    docker rmi ai-paimon-backend:latest 2>/dev/null || true

    # 清理未使用的资源
    docker system prune -f

    print_success "Cleanup completed"
}

# 运行测试
run_tests() {
    print_info "Running tests..."

    # 检查虚拟环境
    if [ ! -d "venv" ]; then
        print_info "Creating virtual environment..."
        python -m venv venv
    fi

    # 激活虚拟环境
    source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null

    # 安装依赖
    pip install -r requirements.txt -q

    # 运行测试
    python -m pytest tests/ -v

    print_success "Tests completed"
}

# 开发模式
dev_mode() {
    print_info "Starting in development mode..."

    # 检查端口
    if ! check_port 8000; then
        print_error "Port 8000 is in use. Please stop the running service first."
        exit 1
    fi

    # 检查虚拟环境
    if [ ! -d "venv" ]; then
        print_info "Creating virtual environment..."
        python -m venv venv
    fi

    # 激活虚拟环境
    source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null

    # 安装依赖
    pip install -r requirements.txt -q

    # 启动开发服务器
    print_info "Starting development server..."
    export ENVIRONMENT=development
    export LOG_LEVEL=DEBUG
    uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
}

# 生产模式
prod_mode() {
    print_info "Starting in production mode..."
    export ENVIRONMENT=production
    start_services "$@"
}

# 主函数
main() {
    # 检查Docker
    check_docker

    case "${1:-start}" in
        start)
            shift
            start_services "$@"
            ;;
        stop)
            stop_services
            ;;
        restart)
            shift
            restart_services "$@"
            ;;
        logs)
            show_logs
            ;;
        status)
            show_status
            ;;
        build)
            build_image
            ;;
        clean)
            clean_all
            ;;
        test)
            run_tests
            ;;
        dev)
            dev_mode
            ;;
        prod)
            shift
            prod_mode "$@"
            ;;
        --help|-h|help)
            show_help
            ;;
        *)
            print_error "Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"