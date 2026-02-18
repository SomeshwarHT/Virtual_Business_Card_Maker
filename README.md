# vCard Flask Application

A Flask-based virtual business card web application with:

- Google OAuth Login
- Card creation form
- Unique shareable card URLs
- SQLite database
- Flask-Login authentication

## Tech Stack

- Python
- Flask
- Flask-Login
- Authlib (Google OAuth)
- Flask-SQLAlchemy
- SQLite

## Setup Instructions

1. Clone the repository
2. Create virtual environment
3. Install dependencies:

pip install -r requirements.txt

4. Create .env file with:

SECRET_KEY=your_secret
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret

5. Run:

python app.py

6. Open:

http://127.0.0.1:5000
