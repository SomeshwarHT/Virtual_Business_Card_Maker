import os
import json
from flask import Flask, render_template, request, redirect, url_for, Response, jsonify
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
from authlib.integrations.flask_client import OAuth
from werkzeug.utils import secure_filename
from config import Config
from models import db, User, Card

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

# ───────── ROUTES ─────────

@app.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("form"))
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
            name=user_info["name"],
            email=user_info["email"],
            profile_pic=user_info["picture"]
        )
        db.session.add(user)
        db.session.commit()

    login_user(user)
    return redirect(url_for("form"))

@app.route("/form")
@login_required
def form():
    user_cards = Card.query.filter_by(user_id=current_user.id).order_by(Card.created_at.desc()).all()
    return render_template("form.html", edit_card=None, user_cards=user_cards)

@app.route("/form/edit/<int:card_id>")
@login_required
def edit_card(card_id):
    card = Card.query.get_or_404(card_id)
    if card.user_id != current_user.id:
        return redirect(url_for("form"))
    user_cards = Card.query.filter_by(user_id=current_user.id).order_by(Card.created_at.desc()).all()
    return render_template("form.html", edit_card=card, user_cards=user_cards)

@app.route("/save_card", methods=["POST"])
@login_required
def save_card():
    data = request.form
    card_id = data.get("card_id")

    # Handle profile picture upload
    profile_pic_filename = save_upload(
        request.files.get('profile_pic'),
        f"{current_user.id}_profile"
    )

    # Handle banner picture upload
    banner_pic_filename = save_upload(
        request.files.get('banner_pic'),
        f"{current_user.id}_banner"
    )

    # Handle multi-role data (arrays from form)
    designations = request.form.getlist('designation[]')
    companies    = request.form.getlist('company[]')
    bios         = request.form.getlist('bio[]')

    roles = []
    for i in range(max(len(designations), len(companies), len(bios))):
        d = designations[i].strip() if i < len(designations) else ''
        c = companies[i].strip()    if i < len(companies)    else ''
        b = bios[i].strip()         if i < len(bios)         else ''
        if d or c or b:
            roles.append({'designation': d, 'company': c, 'bio': b})

    roles = roles[:8]
    first_role = roles[0] if roles else {}

    # Card label — validate uniqueness among this user's cards
    card_label = (data.get("card_label") or "").strip() or None

    if card_id:
        card = Card.query.get(int(card_id))
        if card and card.user_id == current_user.id:
            card.card_label    = card_label
            card.name          = data.get("name") or ""
            card.title         = first_role.get('designation', '')
            card.designation   = first_role.get('designation', '')
            card.company       = first_role.get('company', '')
            card.bio           = first_role.get('bio', '')
            card.roles_json    = json.dumps(roles) if roles else None
            card.phone         = data.get("phone")
            card.email         = data.get("email")
            card.address       = data.get("address")
            card.website       = data.get("website")
            card.upi           = data.get("upi")
            if profile_pic_filename:
                card.profile_pic = profile_pic_filename
            if banner_pic_filename:
                card.banner_pic  = banner_pic_filename
            card.pic_shape     = data.get("pic_shape", card.pic_shape or "round")
            card.pic_position  = data.get("pic_position", card.pic_position or "center")
            card.identity_align= data.get("identity_align", card.identity_align or "center")
            card.theme         = data.get("theme", card.theme or "midnight")
            card.instagram     = data.get("instagram")
            card.linkedin      = data.get("linkedin")
            card.twitter       = data.get("twitter")
            card.facebook      = data.get("facebook")
            card.youtube       = data.get("youtube")
            card.whatsapp      = data.get("whatsapp")
            db.session.commit()
            return redirect(url_for("view_card", card_id=card.id))

    new_card = Card(
        user_id=current_user.id,
        card_label=card_label,
        name=data.get("name") or "",
        title=first_role.get('designation', ''),
        designation=first_role.get('designation', ''),
        company=first_role.get('company', ''),
        bio=first_role.get('bio', ''),
        roles_json=json.dumps(roles) if roles else None,
        phone=data.get("phone"),
        email=data.get("email"),
        address=data.get("address"),
        website=data.get("website"),
        upi=data.get("upi"),
        profile_pic=profile_pic_filename,
        banner_pic=banner_pic_filename,
        pic_shape=data.get("pic_shape", "round"),
        pic_position=data.get("pic_position", "center"),
        identity_align=data.get("identity_align", "center"),
        theme=data.get("theme", "midnight"),
        instagram=data.get("instagram"),
        linkedin=data.get("linkedin"),
        twitter=data.get("twitter"),
        facebook=data.get("facebook"),
        youtube=data.get("youtube"),
        whatsapp=data.get("whatsapp"),
    )

    db.session.add(new_card)
    db.session.commit()

    return redirect(url_for("view_card", card_id=new_card.id))

@app.route("/card/<int:card_id>")
def view_card(card_id):
    card = Card.query.get_or_404(card_id)
    return render_template("card.html", card=card)

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
    label = (request.form.get("card_label") or "").strip() or None
    card.card_label = label
    db.session.commit()
    return jsonify({'success': True})

@app.route("/card/<int:card_id>/update_image", methods=["POST"])
@login_required
def update_card_image(card_id):
    """Update only profile pic or banner from the card view page."""
    card = Card.query.get_or_404(card_id)
    if card.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    image_type = request.form.get("image_type")

    if image_type == 'profile':
        filename = save_upload(request.files.get('image'), f"{current_user.id}_profile")
        if filename:
            card.profile_pic = filename
            db.session.commit()
            return jsonify({'success': True, 'url': url_for('static', filename=f'uploads/{filename}')})
    elif image_type == 'banner':
        filename = save_upload(request.files.get('image'), f"{current_user.id}_banner")
        if filename:
            card.banner_pic = filename
            db.session.commit()
            return jsonify({'success': True, 'url': url_for('static', filename=f'uploads/{filename}')})

    return jsonify({'error': 'No valid file uploaded'}), 400

@app.route("/download_contact/<int:card_id>")
def download_contact(card_id):
    card = Card.query.get_or_404(card_id)

    lines = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"FN:{card.name or ''}",
        f"ORG:{card.company or ''}",
    ]

    roles = card.roles
    first_desig = ''
    if roles:
        first_desig = roles[0].get('designation', '') or ''
    if not first_desig:
        first_desig = (card.designation or card.title or '').strip().splitlines()[0] if (card.designation or card.title) else ''

    if first_desig:
        lines.append(f"TITLE:{first_desig}")

    if card.phone:
        lines.append(f"TEL;TYPE=CELL,VOICE:{card.phone.replace(' ', '')}")
    if card.email:
        lines.append(f"EMAIL;TYPE=WORK:{card.email}")
    if card.address:
        lines.append(f"ADR;TYPE=WORK:;;{card.address};;;;")
    if card.website:
        lines.append(f"URL:{card.website}")
    if card.instagram:
        lines.append(f"X-SOCIALPROFILE;type=instagram:{card.instagram}")
    if card.linkedin:
        lines.append(f"X-SOCIALPROFILE;type=linkedin:{card.linkedin}")
    if card.twitter:
        lines.append(f"X-SOCIALPROFILE;type=twitter:{card.twitter}")

    lines.append("END:VCARD")

    vcf_content = "\r\n".join(lines)
    safe_name = (card.name or "contact").replace(" ", "_")

    return Response(
        vcf_content,
        mimetype="text/vcard",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}.vcf"'
        }
    )

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)