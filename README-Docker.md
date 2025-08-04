# Backend Docker Development Setup

## 🚀 Quick Start

### Development Mode
```bash
# Start backend development server
docker-compose up backend-dev

# Access: http://localhost:8000
# Admin: http://localhost:8000/admin (admin/admin123)
```

## 🛠️ Available Commands

### Docker Commands
```bash
# Development
docker-compose up backend-dev

# Build image
docker build -t feedback-backend-dev .

# Clean up
docker-compose down
```

### Django Commands (trong container)
```bash
# Django shell
docker-compose exec backend-dev python manage.py shell

# Migrations
docker-compose exec backend-dev python manage.py migrate
docker-compose exec backend-dev python manage.py makemigrations

# Create superuser
docker-compose exec backend-dev python manage.py createsuperuser

# Show logs
docker-compose logs -f backend-dev
```


## 📋 Setup Checklist

1. ✅ Copy `.env.example` to `.env`
2. ✅ Update `.env` with your Supabase credentials
3. ✅ Run `docker-compose up backend-dev`
4. ✅ Access http://localhost:8000