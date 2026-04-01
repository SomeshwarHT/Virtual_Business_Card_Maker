import os
import json
import io
import base64
from flask import Flask, render_template, request, redirect, url_for, Response, jsonify
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
from authlib.integrations.flask_client import OAuth
from werkzeug.utils import secure_filename
from config import Config
from models import db, User, Card, CardView
from flask import session
import uuid
import qrcode

app = Flask(__name__)
app.config.from_object(Config)

# Upload folder config
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_upload(file, prefix):
    """Save an uploaded file with a unique prefix and return the filename, or None."""
    if file and file.filename and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filename = f"{prefix}_{filename}"
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        return filename
    return None

def generate_qr_base64(data):
    """Generate QR code and return as base64 string."""
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode()

# Initialize DB
db.init_app(app)

# Login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "home"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# OAuth
oauth = OAuth(app)

google = oauth.register(
    name='google',
    client_id=app.config["GOOGLE_CLIENT_ID"],
    client_secret=app.config["GOOGLE_CLIENT_SECRET"],
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# Create DB
with app.app_context():
    db.create_all()

# ───────── TEMPLATE PRESETS ─────────
TEMPLATE_PRESETS = {
    'modern': {
        'positions': {
            'name': {'x': 26, 'y': 26, 'scale': 1},
            'designation': {'x': 26, 'y': 55, 'scale': 1},
            'company': {'x': 26, 'y': 73, 'scale': 1},
            'phone': {'x': 26, 'y': 105, 'scale': 1},
            'email': {'x': 26, 'y': 125, 'scale': 1},
            'website': {'x': 26, 'y': 145, 'scale': 1},
            'qr': {'x': 494, 'y': 125, 'scale': 1}
        },
        'background': 'matte_navy',
        'accent': 'orange',
        'preset': 'modern',
        'bg_template_filename': 'template_modern.png'
    },
    'minimal': {
        'positions': {
            'name': {'x': 265, 'y': 70, 'scale': 1},
            'designation': {'x': 265, 'y': 98, 'scale': 1},
            'company': {'x': 265, 'y': 118, 'scale': 1},
            'phone': {'x': 265, 'y': 155, 'scale': 1},
            'email': {'x': 265, 'y': 175, 'scale': 1},
            'website': {'x': 265, 'y': 195, 'scale': 1},
            'qr': {'x': 273, 'y': 235, 'scale': 0.9}
        },
        'background': 'matte_beige',
        'accent': 'blue',
        'preset': 'minimal',
        'bg_template_filename': 'template_minimal.png'
    },
    'bold': {
        'positions': {
            'name': {'x': 26, 'y': 35, 'scale': 1.3},
            'designation': {'x': 26, 'y': 75, 'scale': 1.1},
            'company': {'x': 26, 'y': 98, 'scale': 1},
            'phone': {'x': 26, 'y': 135, 'scale': 1},
            'email': {'x': 26, 'y': 155, 'scale': 1},
            'website': {'x': 26, 'y': 175, 'scale': 1},
            'qr': {'x': 485, 'y': 215, 'scale': 1.1}
        },
        'background': 'matte_black',
        'accent': 'orange',
        'preset': 'bold',
        'bg_template_filename': 'template_bold.png'
    },
    'elegant': {
        'positions': {
            'name': {'x': 260, 'y': 55, 'scale': 1.1},
            'designation': {'x': 260, 'y': 88, 'scale': 1},
            'company': {'x': 260, 'y': 108, 'scale': 1},
            'phone': {'x': 260, 'y': 145, 'scale': 1},
            'email': {'x': 260, 'y': 165, 'scale': 1},
            'website': {'x': 260, 'y': 185, 'scale': 1},
            'qr': {'x': 268, 'y': 230, 'scale': 1}
        },
        'background': 'matte_beige',
        'accent': 'gold',
        'preset': 'elegant',
        'bg_template_filename': 'template_elegant.png'
    }
}

# ───────── ROUTES ─────────

@app.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return render_template("home.html")


@app.route("/login")
def login():
    redirect_uri = url_for("auth_callback", _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route("/auth/callback")
def auth_callback():
    token = google.authorize_access_token()

    resp = google.get("https://openidconnect.googleapis.com/v1/userinfo")
    user_info = resp.json()

    google_id = user_info["sub"]

    user = User.query.filter_by(google_id=google_id).first()

    if not user:
        user = User(
            google_id=google_id,
            name=user_info.get("name"),
            email=user_info.get("email"),
            profile_pic=user_info.get("picture")
        )
        db.session.add(user)
        db.session.commit()

    login_user(user)
    return redirect(url_for("dashboard"))

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))

@app.route("/dashboard")
@login_required
def dashboard():
    user_cards = Card.query.filter_by(user_id=current_user.id).order_by(Card.created_at.desc()).all()
    return render_template("dashboard.html", user_cards=user_cards)

@app.route("/form")
@login_required
def form():
    return render_template("form.html", card=None)

@app.route('/edit_card/<int:card_id>', methods=['GET', 'POST'])
@login_required
def edit_card(card_id):
    card = Card.query.get_or_404(card_id)

    if request.method == 'POST':
        card.name = request.form.get('name')
        card.phone = request.form.get('phone')
        card.email = request.form.get('email')
        card.address = request.form.get('address')
        # add other fields

        db.session.commit()
        return redirect(url_for('dashboard'))

    return render_template('form.html', card=card, edit_card=True)

@app.route("/save_card", methods=["POST"])
@login_required
def save_card():
    card_id = request.form.get("card_id")

    if card_id:
        card = Card.query.get_or_404(int(card_id))
        if card.user_id != current_user.id:
            return redirect(url_for("dashboard"))
    else:
        card = Card(user_id=current_user.id)
        db.session.add(card)

    card.card_label = request.form.get("card_label", "").strip() or None
    card.name = request.form.get("name")
    card.title = request.form.get("title")
    card.designation = request.form.get("designation")
    card.company = request.form.get("company")
    card.bio = request.form.get("bio")
    card.phone = request.form.get("phone")
    card.email = request.form.get("email")
    card.address = request.form.get("address")
    card.website = request.form.get("website")
    card.upi = request.form.get("upi")

    card.pic_shape = request.form.get("pic_shape", "round")
    card.pic_position = request.form.get("pic_position", "center")
    card.identity_align = request.form.get("identity_align", "center")
    card.theme = request.form.get("theme", "midnight")

    card.instagram = request.form.get("instagram")
    card.linkedin = request.form.get("linkedin")
    card.twitter = request.form.get("twitter")
    card.facebook = request.form.get("facebook")
    card.youtube = request.form.get("youtube")
    card.whatsapp = request.form.get("whatsapp")

    profile_file = request.files.get("profile_pic")
    if profile_file and profile_file.filename:
        uploaded = save_upload(profile_file, f"profile_{card.id or 'new'}")
        if uploaded:
            card.profile_pic = uploaded

    banner_file = request.files.get("banner_pic")
    if banner_file and banner_file.filename:
        uploaded = save_upload(banner_file, f"banner_{card.id or 'new'}")
        if uploaded:
            card.banner_pic = uploaded

    db.session.commit()

    return redirect(url_for("view_card", card_id=card.id))

@app.route("/card/<int:card_id>")
def view_card(card_id):
    card = Card.query.get_or_404(card_id)

    if "anon_id" not in session:
        session["anon_id"] = str(uuid.uuid4())

    if current_user.is_authenticated:
        if current_user.id != card.user_id:
            existing_view = CardView.query.filter_by(
                card_id=card.id,
                viewer_id=current_user.id
            ).first()

            if not existing_view:
                new_view = CardView(
                    card_id=card.id,
                    viewer_id=current_user.id
                )
                db.session.add(new_view)
                card.views += 1
                db.session.commit()
    else:
        existing_view = CardView.query.filter_by(
            card_id=card.id,
            session_id=session["anon_id"]
        ).first()

        if not existing_view:
            new_view = CardView(
                card_id=card.id,
                session_id=session["anon_id"]
            )
            db.session.add(new_view)
            card.views += 1
            db.session.commit()

    return render_template("card.html", card=card)

# ───────── TEMPLATE SELECTION ROUTE (NEW) ─────────

@app.route("/card/<int:card_id>/templates")
@login_required
def card_templates(card_id):
    card = Card.query.get_or_404(card_id)
    if card.user_id != current_user.id:
        return redirect(url_for("dashboard"))
    # Pass a stripped-down metadata dict (no position data needed in the template)
    templates_meta = {
        key: {
            'bg_template_filename': val.get('bg_template_filename'),
            'background': val['background'],
            'accent': val['accent'],
        }
        for key, val in TEMPLATE_PRESETS.items()
    }
    return render_template(
        "templates.html",
        card=card,
        templates_meta=templates_meta,
        current_template=card.print_bg_template,
    )

@app.route("/card/<int:card_id>/select_template", methods=["POST"])
@login_required
def select_template(card_id):
    card = Card.query.get_or_404(card_id)
    if card.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    template_name = data.get('template')
    
    if template_name not in TEMPLATE_PRESETS:
        return jsonify({'error': 'Invalid template'}), 400
    
    # Apply template preset to card
    template_config = TEMPLATE_PRESETS[template_name]

    # Persist the template background filename directly on the card model
    # so it can be retrieved without parsing the layout JSON.
    card.print_bg_template = template_config.get('bg_template_filename')

    # Store full layout in print_layout_json (single source of truth for the designer)
    card.print_layout_json = json.dumps({
        'positions': template_config['positions'],
        'background': template_config['background'],
        'accent': template_config['accent'],
        'preset': template_config['preset'],
        'bg_template_filename': template_config.get('bg_template_filename'),
        'show_phone': True,
        'show_email': True,
        'show_website': True,
        'show_address': False,
        'custom_text': ''
    })
    
    db.session.commit()
    
    return jsonify({'success': True})

# ───────── DESIGNER & PRINT ROUTES ─────────

@app.route("/card/<int:card_id>/designer")
@login_required
def card_designer(card_id):
    card = Card.query.get_or_404(card_id)
    if card.user_id != current_user.id:
        return redirect(url_for("dashboard"))
    
    # Parse layout JSON in Python — never in templates
    layout = {}
    if card.print_layout_json:
        try:
            layout = json.loads(card.print_layout_json)
        except (ValueError, TypeError):
            layout = {}

    positions    = layout.get('positions', {})
    sizes        = layout.get('sizes', {})
    saved_bg     = layout.get('background', 'matte_black')
    saved_accent = layout.get('accent', 'orange')
    custom_text  = layout.get('custom_text', '')
    show_phone   = layout.get('show_phone', True)
    show_email   = layout.get('show_email', True)
    show_website = layout.get('show_website', True)
    show_address = layout.get('show_address', False)
    font_colors  = layout.get('font_colors', {})

    # Background image priority:
    # 1. User-uploaded binary image (card.print_bg_image) — served via /get_bg_image
    # 2. Template default static image (card.print_bg_template filename)
    # 3. Fallback to background colour class
    has_user_bg = bool(card.print_bg_image)

    bg_template_filename = card.print_bg_template or layout.get('bg_template_filename') or ''
    template_bg_url = (
        url_for('static', filename=f'templates/bg/{bg_template_filename}')
        if bg_template_filename else ''
    )

    # Generate QR code for designer preview
    card_url = url_for("view_card", card_id=card.id, _external=True)
    qr_base64 = generate_qr_base64(card_url)

    return render_template("designer.html",
        card=card,
        qr_base64=qr_base64,
        positions=positions,
        sizes=sizes,
        saved_bg=saved_bg,
        saved_accent=saved_accent,
        custom_text=custom_text,
        show_phone=show_phone,
        show_email=show_email,
        show_website=show_website,
        show_address=show_address,
        has_user_bg=has_user_bg,
        template_bg_url=template_bg_url,
        font_colors=font_colors,
    )

@app.route("/card/<int:card_id>/save_layout", methods=["POST"])
@login_required
def save_layout(card_id):
    card = Card.query.get_or_404(card_id)
    if card.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    layout_data = request.get_json()
    if not layout_data:
        return jsonify({'error': 'No data'}), 400

    # If the designer sends a bg_template_filename, mirror it onto the model field
    # so print_card can read it without re-parsing the JSON every time.
    if 'bg_template_filename' in layout_data:
        card.print_bg_template = layout_data['bg_template_filename'] or None

    # Store everything in print_layout_json — single source of truth
    card.print_layout_json = json.dumps(layout_data)
    db.session.commit()

    return jsonify({'success': True})

@app.route("/card/<int:card_id>/print")
@login_required
def print_card(card_id):
    card = Card.query.get_or_404(card_id)
    if card.user_id != current_user.id:
        return redirect(url_for("dashboard"))

    # Determine whether a user-uploaded background image exists
    has_bg_image = card.print_bg_image is not None

    # Parse layout JSON in Python — never in templates
    layout = {}
    if card.print_layout_json:
        try:
            layout = json.loads(card.print_layout_json)
        except (ValueError, TypeError):
            layout = {}

    positions    = layout.get('positions', {})
    sizes        = layout.get('sizes', {})
    bg           = layout.get('background', 'matte_black')
    accent       = layout.get('accent', 'orange')
    custom_text  = layout.get('custom_text', '')
    show_phone   = layout.get('show_phone', True)
    show_email   = layout.get('show_email', True)
    show_website = layout.get('show_website', True)
    show_address = layout.get('show_address', False)
    font_colors  = layout.get('font_colors', {})

    # Resolve the template background filename:
    # prefer the value stored on the card model; fall back to what's in layout JSON.
    bg_template_filename = card.print_bg_template or layout.get('bg_template_filename')

    # Generate QR code
    card_url = url_for("view_card", card_id=card.id, _external=True)
    qr_base64 = generate_qr_base64(card_url)

    return render_template("print_card.html",
        card=card,
        has_bg_image=has_bg_image,
        bg_template_filename=bg_template_filename,
        qr_base64=qr_base64,
        positions=positions,
        sizes=sizes,
        bg=bg,
        accent=accent,
        custom_text=custom_text,
        show_phone=show_phone,
        show_email=show_email,
        show_website=show_website,
        show_address=show_address,
        font_colors=font_colors,
    )

@app.route("/card/<int:card_id>/delete", methods=["POST"])
@login_required
def delete_card(card_id):
    card = Card.query.get_or_404(card_id)
    if card.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    db.session.delete(card)
    db.session.commit()
    return jsonify({'success': True})

@app.route("/card/<int:card_id>/update_label", methods=["POST"])
@login_required
def update_card_label(card_id):
    card = Card.query.get_or_404(card_id)
    if card.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    new_label = data.get('label', '').strip() or None
    card.card_label = new_label
    db.session.commit()
    
    return jsonify({'success': True})

@app.route("/card/<int:card_id>/download")
def download_contact(card_id):
    card = Card.query.get_or_404(card_id)

    vcard = f"""BEGIN:VCARD
VERSION:3.0
FN:{card.name}
ORG:{card.company}
TITLE:{card.designation}
TEL:{card.phone}
EMAIL:{card.email}
URL:{card.website}
END:VCARD
"""

    return Response(
        vcard,
        mimetype="text/vcard",
        headers={"Content-Disposition": f"attachment;filename={card.name}.vcf"}
    )

@app.route("/card/<int:card_id>/upload_bg_image", methods=["POST"])
@login_required
def upload_bg_image(card_id):
    """Upload background image for printable card"""
    card = Card.query.get_or_404(card_id)
    if card.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    if 'bg_image' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['bg_image']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Validate file type
    allowed_types = {'image/png', 'image/jpeg', 'image/jpg'}
    if file.content_type not in allowed_types:
        return jsonify({'error': 'Invalid file type. Use PNG or JPG'}), 400
    
    # Read and store binary data
    image_data = file.read()
    
    # Store in database
    card.print_bg_image = image_data
    card.print_bg_image_mime = file.content_type
    db.session.commit()
    
    return jsonify({'success': True})

@app.route("/card/<int:card_id>/get_bg_image")
@login_required
def get_bg_image(card_id):
    """Retrieve background image for printable card"""
    card = Card.query.get_or_404(card_id)
    if card.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    if not card.print_bg_image:
        return jsonify({'error': 'No background image'}), 404
    
    return Response(card.print_bg_image, mimetype=card.print_bg_image_mime)

@app.route("/card/<int:card_id>/delete_bg_image", methods=["POST"])
@login_required
def delete_bg_image(card_id):
    """Delete user-uploaded background image. Template default BG is preserved."""
    card = Card.query.get_or_404(card_id)
    if card.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    card.print_bg_image = None
    card.print_bg_image_mime = None
    db.session.commit()

    # Tell the designer what (if any) template BG should now show instead
    bg_template_filename = card.print_bg_template or ''
    template_bg_url = (
        url_for('static', filename=f'templates/bg/{bg_template_filename}',
                _external=False)
        if bg_template_filename else ''
    )
    return jsonify({'success': True, 'template_bg_url': template_bg_url})

if __name__ == "__main__":
    app.run(debug=True)