from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

# ───────── USER MODEL ─────────
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(100), unique=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(150), unique=True)
    profile_pic = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ───────── CARD MODEL ─────────
class Card(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    name = db.Column(db.String(100))
    title = db.Column(db.String(100))
    company = db.Column(db.String(150))
    bio = db.Column(db.Text)

    phone = db.Column(db.String(20))
    email = db.Column(db.String(150))
    address = db.Column(db.String(200))
    website = db.Column(db.String(200))
    upi = db.Column(db.String(100))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
