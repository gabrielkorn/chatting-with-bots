from flask import Flask, render_template, request, redirect, url_for
from flask_htmx import HTMX

app = Flask(__name__)
htmx = HTMX(app)

@app.route("/")
def index():
    return render_template("index.html")

