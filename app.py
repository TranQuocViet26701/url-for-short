import os
from botocore.exceptions import ClientError
from flask import Flask, render_template, request, redirect, abort
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
import qrcode
import boto3
from form import GeneratorForm
from utils import generate_unique_key

BUCKET_NAME = os.environ["BUCKET_NAME"]
REGION_NAME = os.environ["REGION_NAME"]
AWS_ACCESS_KEY_ID = os.environ["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = os.environ["AWS_SECRET_ACCESS_KEY"]


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
    qrcode_url = db.Column(db.String, unique=True)


with app.app_context():
    db.create_all()

# configure AWS S3
s3 = boto3.resource(service_name="s3",
                    region_name=REGION_NAME,
                    aws_access_key_id=AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=AWS_SECRET_ACCESS_KEY)


@app.route('/', methods=["GET", "POST"])
def home():
    shorten_url, qrcode_url = None, None
    form = GeneratorForm()
    if form.validate_on_submit():
        original_url = form.url.data
        record_by_original_url = db.session.query(Url).filter_by(original_url=original_url).first()

        # original_url already existed
        if record_by_original_url:
            shorten_url = f"{request.base_url}{record_by_original_url.shorten_key}"
            return render_template("index.html", form=form, shorten_url=shorten_url,
                                   qrcode_url=record_by_original_url.qrcode_url)

        # regenerate if shorten_key already existed
        unique_key = generate_unique_key()
        while db.session.query(Url).filter_by(shorten_key=unique_key).first():
            unique_key = generate_unique_key()

        # save and upload img qrcode to AWS S3
        img = qrcode.make(original_url)
        img.get_image()
        img.save(f"{unique_key}.png")
        try:
            s3.Bucket(BUCKET_NAME).upload_file(Filename=f"{unique_key}.png",
                                               Key=f"{unique_key}.png",
                                               ExtraArgs={"ContentType": "image/png",
                                                          "ContentDisposition": "attachment"})
            # remove img
            if os.path.exists(f"{unique_key}.png"):
                os.remove(f"{unique_key}.png")
        except ClientError as e:
            print(f"error: {e}")

        qrcode_url = f"https://{BUCKET_NAME}.s3.{REGION_NAME}.amazonaws.com/{unique_key}.png"

        # add new record url
        new_record = Url(original_url=original_url, shorten_key=unique_key, qrcode_url=qrcode_url)
        db.session.add(new_record)
        db.session.commit()

        shorten_url = f"{request.base_url}{unique_key}"
    return render_template("index.html", form=form, shorten_url=shorten_url, qrcode=qrcode_url)


@app.route("/<string:shorten_key>")
def redirect_shorten_url(shorten_key: str):
    record = db.session.query(Url).filter_by(shorten_key=shorten_key).first()

    if not record:
        abort(400, "URL Not Found")

    return redirect(record.original_url)


if __name__ == '__main__':
    app.run(debug=True)
