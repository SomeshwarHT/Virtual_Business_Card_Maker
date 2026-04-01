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

    views = db.Column(db.Integer, default=0)

    # ───────── PRINTABLE CARD CUSTOMIZATION ─────────
    print_show_phone = db.Column(db.Boolean, default=True)
    print_show_email = db.Column(db.Boolean, default=True)
    print_show_address = db.Column(db.Boolean, default=False)
    print_show_website = db.Column(db.Boolean, default=True)
    print_show_social = db.Column(db.Boolean, default=False)
    print_custom_text = db.Column(db.String(200))
    print_template = db.Column(db.String(20), default='classic')
    print_color = db.Column(db.String(20), default='black')
    print_background_color = db.Column(db.String(30), default='matte_black')
    print_layout_json = db.Column(db.Text)
    print_bg_template = db.Column(db.String(100), nullable=True)
    # ───────── BACKGROUND IMAGE (NEW) ─────────
    print_bg_image = db.Column(db.LargeBinary)  # Store image binary data
    print_bg_image_mime = db.Column(db.String(50))  # Store MIME type (image/png, image/jpeg)
    
    # ───────── FONT COLORS (NEW) ─────────
    print_font_colors_json = db.Column(db.Text)  # Store font colors as JSON (e.g., {"name": "#ffffff", "phone": "#000000"})

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
    def font_colors(self):
        """Return dict of font colors from print_font_colors_json, or empty dict."""
        if self.print_font_colors_json:
            try:
                return json.loads(self.print_font_colors_json)
            except Exception:
                pass
        return {}

    @property
    def social(self):
        return self
    
# ───────── CARD VIEW MODEL ─────────
class CardView(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    card_id = db.Column(db.Integer, db.ForeignKey('card.id'), nullable=False)

    # Either viewer_id OR session_id will be used
    viewer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    session_id = db.Column(db.String(100), nullable=True)

    viewed_at = db.Column(db.DateTime, default=datetime.utcnow)