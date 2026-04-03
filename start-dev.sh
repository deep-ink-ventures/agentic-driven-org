#!/bin/bash
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

G='\033[0;32m'
Y='\033[0;33m'
R='\033[0;31m'
NC='\033[0m'

echo -e "${G}Starting Agentic Company dev environment...${NC}"

echo -e "${Y}Starting Docker services (Postgres + Redis)...${NC}"
docker compose -f docker-compose.dev.yml up -d

echo -n "Waiting for Postgres..."
until docker compose -f docker-compose.dev.yml exec -T postgres pg_isready -q 2>/dev/null; do
  echo -n "."
  sleep 1
done
echo -e " ${G}ready${NC}"

echo -e "${Y}Running configure...${NC}"
cd backend
./venv/bin/python manage.py configure
cd ..

echo -e "${Y}Starting Django backend (port 8000)...${NC}"
cd backend
./venv/bin/python manage.py runserver 8000 &
DJANGO_PID=$!
cd ..

echo -e "${Y}Starting Celery worker...${NC}"
cd backend
./venv/bin/celery -A config worker --loglevel=info &
CELERY_PID=$!
cd ..

echo -e "${Y}Starting Celery beat...${NC}"
cd backend
./venv/bin/celery -A config beat --loglevel=info &
BEAT_PID=$!
cd ..

echo ""
echo -e "${G}All services running:${NC}"
echo -e "  Backend:   http://localhost:8000"
echo -e "  Admin:     http://localhost:8000/admin/"
echo -e "  Postgres:  localhost:5434"
echo -e "  Redis:     localhost:6381"
echo ""
echo -e "${Y}Press Ctrl+C to stop all services${NC}"

cleanup() {
  echo ""
  echo -e "${R}Stopping all services...${NC}"
  kill $DJANGO_PID $CELERY_PID $BEAT_PID 2>/dev/null
  docker compose -f docker-compose.dev.yml stop
  echo -e "${G}Done.${NC}"
  exit 0
}

trap cleanup SIGINT SIGTERM
wait
