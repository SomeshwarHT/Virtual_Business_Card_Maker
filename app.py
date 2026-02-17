from flask import Flask, render_template, request, redirect, url_for
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
from authlib.integrations.flask_client import OAuth
from config import Config
from models import db, User, Card

app = Flask(__name__)
app.config.from_object(Config)

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
    return render_template("form.html")

@app.route("/save_card", methods=["POST"])
@login_required
def save_card():
    data = request.form

    new_card = Card(
        user_id=current_user.id,
        name=data.get("name"),
        title=data.get("title"),
        company=data.get("company"),
        bio=data.get("bio"),
        phone=data.get("phone"),
        email=data.get("email"),
        address=data.get("address"),
        website=data.get("website"),
        upi=data.get("upi"),
    )

    db.session.add(new_card)
    db.session.commit()

    return redirect(url_for("view_card", card_id=new_card.id))

@app.route("/card/<int:card_id>")
def view_card(card_id):
    card = Card.query.get_or_404(card_id)
    return render_template("card.html", card=card)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True)
