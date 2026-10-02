import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

load_dotenv()

app = Flask(__name__)

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

FEES = {
    "hdb": 1999,
    "condo": 4999,
    "landed": 9999,
}

@app.get("/")
def home():
    return render_template("index.html", fees=FEES)

@app.post("/api/estimate")
def estimate():
    payload = request.get_json(silent=True) or request.form
    property_type = str(payload.get("property_type", "hdb")).lower()
    try:
        price = float(str(payload.get("price", "0")).replace(",", ""))
    except ValueError:
        return jsonify({"error": "Enter a valid selling price."}), 400

    if property_type not in FEES or price <= 0:
        return jsonify({"error": "Choose a property type and enter a selling price."}), 400

    traditional_fee = round(price * 0.02)
    flat_fee = FEES[property_type]
    return jsonify({
        "traditional_fee": traditional_fee,
        "flat_fee": flat_fee,
        "savings": max(traditional_fee - flat_fee, 0),
        "property_type": property_type,
    })

@app.post("/api/lead")
def lead():
    print("LEAD FORM RECEIVED")

    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip()
    property_type = request.form.get("property_type", "").strip()

    if not name or not phone or not email or not property_type:
        return jsonify({"error": "Please complete all required fields."}), 400

    try:
        message = EmailMessage()
        message["Subject"] = "New Homewise Free Call Request"
        message["From"] = EMAIL_ADDRESS
        message["To"] = EMAIL_ADDRESS

        message.set_content(
            f"""New free call request received.

Name: {name}
Phone: {phone}
Email: {email}
Property type: {property_type}
"""
        )

        with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(message)

        return jsonify({
            "message": "Thanks. We will be in touch within one business day."
        })

    except Exception as error:
        app.logger.error("Email failed: %s", error)
        return jsonify({
            "error": "We could not send your request. Please try again."
        }), 500

if __name__ == "__main__":
    app.run(debug=True)
