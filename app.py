import json
import os
import smtplib
from urllib import error, request as urlrequest
from email.message import EmailMessage

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

FEES = {
    "hdb": 1999,
    "condo": 4999,
    "landed": 9999,
}


def send_whatsapp_booking(name, phone, email, property_type, booking_date, booking_time):
    access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
    phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
    recipient_phone = os.getenv("WHATSAPP_RECIPIENT_PHONE")

    if not access_token or not phone_number_id or not recipient_phone:
        app.logger.warning("WhatsApp is not configured; booking was logged only.")
        return False

    message = (
        "New AIHome strategy call request\n"
        f"Name: {name}\n"
        f"Phone: {phone}\n"
        f"Email: {email}\n"
        f"Property: {property_type}\n"
        f"Preferred date: {booking_date or 'Not specified'}\n"
        f"Preferred time: {booking_time or 'Not specified'}"
    )
    payload = json.dumps({
        "messaging_product": "whatsapp",
        "to": recipient_phone,
        "type": "text",
        "text": {"body": message},
    }).encode("utf-8")
    api_version = os.getenv("WHATSAPP_API_VERSION", "v22.0")
    endpoint = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"
    http_request = urlrequest.Request(
        endpoint,
        data=payload,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlrequest.urlopen(http_request, timeout=10) as response:
            if 200 <= response.status < 300:
                app.logger.info("WhatsApp booking notification sent.")
                return True
            app.logger.error("WhatsApp API returned status %s.", response.status)
    except error.HTTPError as exc:
        app.logger.error("WhatsApp API returned status %s.", exc.code)
    except error.URLError:
        app.logger.exception("Could not connect to WhatsApp API.")
    return False


def booking_details(name, phone, email, property_type, booking_date, booking_time):
    return {
        "name": name,
        "phone": phone,
        "email": email,
        "property_type": property_type,
        "booking_date": booking_date,
        "booking_time": booking_time,
    }


def save_booking(details):
    database_config = {
        "host": os.getenv("MYSQL_HOST"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER"),
        "password": os.getenv("MYSQL_PASSWORD"),
        "database": os.getenv("MYSQL_DATABASE"),
    }
    if not all(database_config.values()):
        app.logger.warning("MySQL is not configured; booking was logged only.")
        return False

    try:
        import mysql.connector

        connection = mysql.connector.connect(**database_config)
        cursor = connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(120) NOT NULL,
                phone VARCHAR(40) NOT NULL,
                email VARCHAR(255) NOT NULL,
                property_type VARCHAR(40) NOT NULL,
                booking_date VARCHAR(80),
                booking_time VARCHAR(80),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            INSERT INTO bookings
                (name, phone, email, property_type, booking_date, booking_time)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            details["name"], details["phone"], details["email"],
            details["property_type"], details["booking_date"], details["booking_time"],
        ))
        connection.commit()
        booking_id = cursor.lastrowid
        cursor.close()
        connection.close()
        app.logger.info("Booking saved to MySQL with id %s.", booking_id)
        return True
    except ImportError:
        app.logger.exception("mysql-connector-python is not installed.")
    except Exception:
        app.logger.exception("Could not save booking to MySQL.")
    return False


def send_email_booking(details):
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    email_from = os.getenv("BOOKING_EMAIL_FROM", smtp_username or "")
    email_to = os.getenv("BOOKING_EMAIL_TO")

    if not all((smtp_host, smtp_username, smtp_password, email_from, email_to)):
        app.logger.warning("Email notifications are not configured; booking was logged only.")
        return False

    message = EmailMessage()
    message["Subject"] = f"New AIHome booking: {details['name']}"
    message["From"] = email_from
    message["To"] = email_to
    message.set_content("New AIHome strategy call request\n\n" + "\n".join(
        f"{key.replace('_', ' ').title()}: {value or 'Not specified'}"
        for key, value in details.items()
    ))

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as smtp:
            smtp.starttls()
            smtp.login(smtp_username, smtp_password)
            smtp.send_message(message)
        app.logger.info("Email booking notification sent.")
        return True
    except (OSError, smtplib.SMTPException):
        app.logger.exception("Could not send email booking notification.")
        return False


def send_crm_booking(details):
    crm_webhook_url = os.getenv("CRM_WEBHOOK_URL")
    if not crm_webhook_url:
        app.logger.warning("CRM webhook is not configured; booking was logged only.")
        return False

    payload = json.dumps({"event": "new_booking", "lead": details}).encode("utf-8")
    http_request = urlrequest.Request(
        crm_webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlrequest.urlopen(http_request, timeout=10) as response:
            if 200 <= response.status < 300:
                app.logger.info("CRM booking notification sent.")
                return True
            app.logger.error("CRM webhook returned status %s.", response.status)
    except error.HTTPError as exc:
        app.logger.error("CRM webhook returned status %s.", exc.code)
    except error.URLError:
        app.logger.exception("Could not connect to CRM webhook.")
    return False

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
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip()
    property_type = request.form.get("property_type", "").strip()
    booking_date = request.form.get("booking_date", "").strip()
    booking_time = request.form.get("booking_time", "").strip()

    if not name or not phone or not email or not property_type:
        return jsonify({"error": "Please complete all required fields."}), 400

    # Keep the starter deployment database-free; connect this endpoint to email/CRM in production.
    app.logger.info("Strategy call request: %s, %s, %s, %s, %s, %s", name, phone, email, property_type, booking_date, booking_time)
    details = booking_details(name, phone, email, property_type, booking_date, booking_time)
    save_booking(details)
    send_whatsapp_booking(name, phone, email, property_type, booking_date, booking_time)
    send_email_booking(details)
    send_crm_booking(details)
    confirmation = "Thanks. We will be in touch within one business day."
    if booking_date and booking_time:
        confirmation = "Thanks. Your preferred time has been shared with our team."
    return jsonify({"message": confirmation})

if __name__ == "__main__":
    app.run(debug=True)
