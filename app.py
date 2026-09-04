from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

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
    confirmation = "Thanks. We will be in touch within one business day."
    if booking_date and booking_time:
        confirmation = "Thanks. Your preferred time has been shared with our team."
    return jsonify({"message": confirmation})

if __name__ == "__main__":
    app.run(debug=True)
