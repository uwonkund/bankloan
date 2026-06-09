# Bank Loan System - Deployment Guide

## Deployment to Render.com

### Prerequisites
1. GitHub repository: `https://github.com/uwonkund/bankloan.git`
2. Render.com account (free tier available)

### Steps to Deploy on Render

#### 1. Connect to GitHub
1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New +" and select "Web Service"
3. Connect to your GitHub repository: `uwonkund/bankloan`

#### 2. Configure Web Service
- **Name**: `bankloan-api`
- **Environment**: `Python`
- **Build Command**: `./build.sh`
- **Start Command**: `gunicorn bankloan.wsgi:application`
- **Plan**: `Free` (or choose based on your needs)

#### 3. Add Environment Variables
Add these variables in the Render dashboard:
- `SECRET_KEY`: [Generate a strong secret key]
- `DEBUG`: `False`
- `DATABASE_URL`: [Will be auto-provided when you create a PostgreSQL database]
- `EMAIL_HOST_USER`: [Your Gmail for sending emails]
- `EMAIL_HOST_PASSWORD`: [Gmail app password]
- `PYTHON_VERSION`: `3.11.0`

#### 4. Create PostgreSQL Database
1. In Render Dashboard, click "New +" → "PostgreSQL"
2. Name: `bankloan_db`
3. Database name: `bankloan`
4. User: `bankloan_user`
5. Connect it to your web service

#### 5. Deploy
Click "Create Web Service" and wait for deployment to complete.

### Admin Account Setup

After deployment:
1. SSH into the instance or use Render's console
2. Run: `python manage.py create_admin_user`

This will create the admin user:
- **Email**: `philos@gmail.com`
- **Password**: `philos@48`

### API Endpoints
- **Admin Dashboard**: `https://your-app.onrender.com/api/userapp/admin/dashboard/`
- **Login**: `https://your-app.onrender.com/api/userapp/login/`
- **API Documentation**: `https://your-app.onrender.com/api/schema/swagger-ui/`

### Testing Deployment
1. Visit your deployed URL: `https://your-app.onrender.com/api/userapp/login/`
2. Use admin credentials to login
3. Access admin dashboard

### Troubleshooting
- If database migrations fail, check PostgreSQL connection
- If static files aren't served, ensure `whitenoise` is configured
- Check Render logs for any build/deployment errors

### Important Notes
1. The free tier has limitations (sleeps after inactivity)
2. Consider upgrading for production use
3. Set up custom domain if needed
4. Monitor resource usage in Render dashboard