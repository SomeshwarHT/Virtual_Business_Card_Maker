from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import json

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

    # Card label (user-defined unique name for the card)
    card_label = db.Column(db.String(80))

    name = db.Column(db.String(100))

    # Legacy single-role fields (backward compat)
    title = db.Column(db.String(100))
    designation = db.Column(db.Text)
    company = db.Column(db.String(150))
    bio = db.Column(db.Text)

    # Multi-role: stored as JSON array of {designation, company, bio}
    roles_json = db.Column(db.Text)

    phone = db.Column(db.String(20))
    email = db.Column(db.String(150))
    address = db.Column(db.String(200))
    website = db.Column(db.String(200))
    upi = db.Column(db.String(100))

    # Images
    profile_pic = db.Column(db.String(300))
    banner_pic = db.Column(db.String(300))

    # Display options
    pic_shape = db.Column(db.String(10), default='round')      # 'round' or 'square'
    pic_position = db.Column(db.String(10), default='center')  # 'left', 'center', 'right'
    identity_align = db.Column(db.String(10), default='center') # 'left', 'center', 'right'

    # Theme: stores a theme key string e.g. 'midnight', 'ocean', 'forest', etc.
    theme = db.Column(db.String(30), default='midnight')

    # Social media profiles
    instagram = db.Column(db.String(300))
    linkedin  = db.Column(db.String(300))
    twitter   = db.Column(db.String(300))
    facebook  = db.Column(db.String(300))
    youtube   = db.Column(db.String(300))
    whatsapp  = db.Column(db.String(50))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def roles(self):
        """Return list of role dicts from roles_json, or build from legacy fields."""
        if self.roles_json:
            try:
                return json.loads(self.roles_json)
            except Exception:
                pass
        # Fallback to legacy single role
        if self.designation or self.company or self.bio:
            return [{'designation': self.designation or '', 'company': self.company or '', 'bio': self.bio or ''}]
        return []

    @property
    def social(self):
        return self