"""
Flask web layer for the car rental system.

Run:   python app.py      then open  http://127.0.0.1:5000
Admin: /admin  (password: admin123, or set the ADMIN_PASSWORD environment variable)
"""
import os
import re
from datetime import date
from functools import wraps

from flask import (Flask, flash, g, jsonify, redirect, render_template,
                   request, session, url_for)

from models import CarFactory, CarRentalAgency, InvalidInputError, RentalError
from seed import build_demo_agency
from translations import Translator

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024        # photo uploads: 8 MB max
PHOTO_DIR = os.path.join(app.static_folder, "cars")
PHOTO_TYPES = ("jpg", "jpeg", "png", "webp")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

agency: CarRentalAgency = build_demo_agency()   # the whole "database": objects in memory
translator = Translator()


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #
def parse_date(value):
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


def car_slug(car):
    """'Toyota Land Cruiser' -> 'toyota-land-cruiser' (photo file name, no extension)."""
    return re.sub(r"[^a-z0-9]+", "-", car.name.lower()).strip("-")


def photo_url(car):
    """URL of the car's photo (static/cars/<slug>.<ext>) or None if there is none."""
    slug = car_slug(car)
    for ext in PHOTO_TYPES:
        path = os.path.join(PHOTO_DIR, f"{slug}.{ext}")
        if os.path.isfile(path):
            return url_for("static", filename=f"cars/{slug}.{ext}",
                           v=int(os.path.getmtime(path)))
    return None


def save_photo(car, file):
    """Store an uploaded photo for the car. Does nothing if no file was chosen."""
    if file is None or not file.filename:
        return False
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in PHOTO_TYPES:
        raise InvalidInputError(field="photo")
    os.makedirs(PHOTO_DIR, exist_ok=True)
    slug = car_slug(car)
    for old in PHOTO_TYPES:                       # one photo per car
        old_path = os.path.join(PHOTO_DIR, f"{slug}.{old}")
        if os.path.isfile(old_path):
            os.remove(old_path)
    file.save(os.path.join(PHOTO_DIR, f"{slug}.{ext}"))
    return True


def tr(key, params=None):
    return translator.t(key, g.lang, params)


def notify(kind, key, **params):
    flash((kind, tr(key, params)))


def notify_error(error: RentalError):
    params = dict(error.params)
    if "field" in params:                       # translate the field name too
        params["field"] = tr(params["field"])
    notify("error", "err_" + error.code, **params)


def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            notify("error", "err_login_required")
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapper


@app.before_request
def pick_language():
    lang = session.get("lang", Translator.DEFAULT)
    g.lang = lang if translator.is_supported(lang) else Translator.DEFAULT


@app.context_processor
def inject_globals():
    return {
        "t": tr,
        "photo_url": photo_url,
        "lang": g.lang,
        "dir": translator.direction(g.lang),
        "other_lang": "ku" if g.lang == "en" else "en",
        "agency": agency,
        "today": date.today().isoformat(),
        "categories": CarFactory.categories(),
    }


# --------------------------------------------------------------------------- #
#  Public pages
# --------------------------------------------------------------------------- #
@app.route("/lang/<code>")
def set_language(code):
    if translator.is_supported(code):
        session["lang"] = code
    return redirect(request.referrer or url_for("index"))


@app.route("/")
def index():
    category = request.args.get("category") or None
    max_price = request.args.get("max_price", type=float)
    start = parse_date(request.args.get("start"))
    end = parse_date(request.args.get("end"))
    try:
        cars = agency.search(category, max_price, start, end)
    except RentalError as error:
        notify_error(error)
        cars = agency.search(category, max_price)
    availability = {car.id: agency.is_available_today(car) for car in cars}
    return render_template("index.html", cars=cars, availability=availability,
                           start=request.args.get("start", ""),
                           end=request.args.get("end", ""),
                           category=category or "",
                           max_price=request.args.get("max_price", ""))


@app.route("/car/<int:car_id>")
def car_detail(car_id):
    try:
        car = agency.get_car(car_id)
    except RentalError as error:
        notify_error(error)
        return redirect(url_for("index"))
    return render_template("car.html", car=car,
                           start=request.args.get("start", ""),
                           end=request.args.get("end", ""))


@app.route("/car/<int:car_id>/book", methods=["POST"])
def book_car(car_id):
    form = request.form
    try:
        booking = agency.create_booking(
            car_id, form.get("name"), form.get("phone"),
            parse_date(form.get("start")), parse_date(form.get("end")))
    except RentalError as error:
        notify_error(error)
        return redirect(url_for("car_detail", car_id=car_id,
                                start=form.get("start", ""), end=form.get("end", "")))
    return redirect(url_for("booking_detail", booking_id=booking.id))


@app.route("/booking/<int:booking_id>")
def booking_detail(booking_id):
    try:
        booking = agency.get_booking(booking_id)
    except RentalError as error:
        notify_error(error)
        return redirect(url_for("index"))
    return render_template("booking.html", booking=booking)


@app.route("/booking/<int:booking_id>/cancel", methods=["POST"])
def cancel_booking(booking_id):
    try:
        booking = agency.cancel_booking(booking_id)
        notify("success", "msg_booking_cancelled")
    except RentalError as error:
        notify_error(error)
        return redirect(url_for("index"))
    return redirect(request.form.get("next") or url_for("booking_detail", booking_id=booking.id))


@app.route("/my-bookings")
def my_bookings():
    phone = request.args.get("phone", "").strip()
    bookings = agency.bookings_for_phone(phone) if phone else []
    return render_template("my_bookings.html", bookings=bookings, phone=phone)


@app.route("/api/quote")
def api_quote():
    """Used by the booking form to show the price live."""
    try:
        quote = agency.quote(request.args.get("car_id"),
                             parse_date(request.args.get("start")),
                             parse_date(request.args.get("end")))
        return jsonify(ok=True, **quote)
    except RentalError as error:
        params = dict(error.params)
        if "field" in params:
            params["field"] = tr(params["field"])
        return jsonify(ok=False, message=tr("err_" + error.code, params))


# --------------------------------------------------------------------------- #
#  Admin
# --------------------------------------------------------------------------- #
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["is_admin"] = True
            notify("success", "msg_logged_in")
            return redirect(url_for("admin"))
        notify("error", "err_bad_password")
    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    session.pop("is_admin", None)
    return redirect(url_for("index"))


@app.route("/admin")
@admin_required
def admin():
    return render_template("admin.html", cars=agency.list_cars(),
                           bookings=agency.list_bookings(),
                           transmissions=CarFactory._registry["economy"].TRANSMISSIONS,
                           fuels=CarFactory._registry["economy"].FUELS)


@app.route("/admin/cars/add", methods=["POST"])
@admin_required
def admin_add_car():
    f = request.form
    try:
        car = agency.add_car(
            f.get("category"), brand=f.get("brand"), model=f.get("model"),
            year=f.get("year"), seats=f.get("seats"),
            transmission=f.get("transmission"), fuel=f.get("fuel"),
            daily_rate=f.get("daily_rate"), color=f.get("color", "#2c3e50"))
        notify("success", "msg_car_added")
        save_photo(car, request.files.get("photo"))
    except RentalError as error:
        notify_error(error)
    return redirect(url_for("admin"))


@app.route("/admin/cars/<int:car_id>/photo", methods=["POST"])
@admin_required
def admin_car_photo(car_id):
    try:
        car = agency.get_car(car_id)
        if save_photo(car, request.files.get("photo")):
            notify("success", "msg_photo_saved")
    except RentalError as error:
        notify_error(error)
    return redirect(url_for("admin"))


@app.route("/admin/cars/<int:car_id>/remove", methods=["POST"])
@admin_required
def admin_remove_car(car_id):
    try:
        agency.remove_car(car_id)
        notify("success", "msg_car_removed")
    except RentalError as error:
        notify_error(error)
    return redirect(url_for("admin"))


if __name__ == "__main__":
    app.run(debug=True)
