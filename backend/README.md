# QuantNest Backend

This is the backend for the QuantNest project, built with Django and Django REST Framework.

## Features
- Custom user model with email authentication
- JWT authentication with cookies
- User profile API
- Email confirmation and password reset
- Dockerized for easy deployment
- Cloudinary for media storage

## Requirements
- Python 3.10+
- PostgreSQL
- Cloudinary account (for media)

## Setup
1. Clone the repository:
   ```sh
   git clone <repo-url>
   cd backend
   ```
2. Create a virtual environment and activate it:
   ```sh
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
4. Copy the example environment file and set your variables:
   ```sh
   cp .env.example .env
   # Edit .env with your secrets and config
   ```
5. Run migrations and create a superuser:
   ```sh
   python manage.py migrate
   python manage.py createsuperuser
   ```
6. Run the development server:
   ```sh
   python manage.py runserver
   ```

## Running with Docker
```sh
docker build -t quantnest-backend .
docker run --env-file .env -p 8000:8000 quantnest-backend
```

## Testing
```sh
python manage.py test
```

## API Documentation
- API endpoints are versioned under `/api/v1/`
- Auth endpoints provided by dj-rest-auth and allauth

## Static & Media
- Static files are served from `/static/`
- Media files are stored on Cloudinary

## Health Check
- `/health/` endpoint for monitoring

## License
MIT 