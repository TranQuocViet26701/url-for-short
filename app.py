import os
from flask import Flask, render_template, request, redirect, abort
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from form import GeneratorForm
from utils import generate_unique_key

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
Bootstrap(app)

# configure the SQLite database
db = SQLAlchemy()
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("SQLALCHEMY_DATABASE_URI", "sqlite:///urlshortener.db")
db.init_app(app)


class Url(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shorten_key = db.Column(db.String, unique=True, nullable=False)
    original_url = db.Column(db.String, unique=True, nullable=False)


with app.app_context():
    db.create_all()


@app.route('/', methods=["GET", "POST"])
def home():
    shorten_url = None
    form = GeneratorForm()
    if form.validate_on_submit():
        original_url = form.url.data
        record_by_original_url = db.session.query(Url).filter_by(original_url=original_url).first()

        # original_url already existed
        if record_by_original_url:
            shorten_url = f"{request.base_url}{record_by_original_url.shorten_key}"
            return render_template("index.html", form=form, shorten_url=shorten_url)

        # regenerate if shorten_key already existed
        unique_key = generate_unique_key()
        while db.session.query(Url).filter_by(shorten_key=unique_key).first():
            unique_key = generate_unique_key()

        # add new record url
        new_record = Url(original_url=original_url, shorten_key=unique_key)
        db.session.add(new_record)
        db.session.commit()

        shorten_url = f"{request.base_url}{unique_key}"
    return render_template("index.html", form=form, shorten_url=shorten_url)


@app.route("/<string:shorten_key>")
def redirect_shorten_url(shorten_key: str):
    record = db.session.query(Url).filter_by(shorten_key=shorten_key).first()

    if not record:
        abort(400, "URL Not Found")

    return redirect(record.original_url)


if __name__ == '__main__':
    app.run(debug=True)
