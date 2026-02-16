from flask import Flask, render_template, request , redirect, url_for, session, flash, jsonify, stream_with_context, Response
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from mysql.connector.errors import IntegrityError
import requests
import json

app = Flask(__name__)

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "phi3:mini"

app.secret_key = "YOUR_SECRET_KEY" 

mydb = mysql.connector.connect(
        host = "localhost",
        user = "root",
        password = "YOUR_MYSQL_PASSWORD_HERE",
        database = "Hamza_BD"
)


def warmup_ollama():
    try:
        payload = {
            "model": "phi3:mini",
            "prompt": "Say ready",
            "stream": False
        }
        requests.post(OLLAMA_URL, json=payload, timeout=20)
        print("✅ Ollama model warmed up")
    except Exception as e:
        print("⚠️ Ollama warmup failed:", e)

warmup_ollama()

cursor = mydb.cursor(dictionary=True)

# routes
#  SEARCH ROUTE
@app.route("/search")
def search():
    query = request.args.get("q", "").strip().lower()

    # User pressed search without typing anything
    if query == "":
        return render_template("search_results.html", query=query, page=None)

    # Simple keyword to page mapping
    pages = {
        "home": "home",
        "homepage": "home",
        "vision": "vision",
        "our vision": "vision",
        "camp": "camp",
        "blood camp": "camp",
        "donor": "donor_login",
        "patient": "patient_login",
        "admin": "admin_login",
        "about": "about",
        "contact": "contact",
        "bloodbot": "bloodbot",
        "chatbot": "bloodbot"
    }

    # Check if query matches any known keyword
    for key, page in pages.items():
        if key in query:
            return render_template("search_results.html", query=query, page=page)

    #  NO MATCH FOUND = show message
    return render_template("search_results.html", query=query, page=None)
#------
#home
#------
@app.route("/")
def home():
    return render_template("home.html")
#-----------
#our vision
#-----------
@app.route("/vision")
def vision():
    return render_template("vision.html")
#-----------
#live camps
#-----------
@app.route("/camp")
def camp():
    cursor = mydb.cursor(dictionary=True)
    cursor.execute("SELECT * FROM camps ORDER BY start_date ASC")
    camps = cursor.fetchall()
    return render_template("camp.html", camps=camps)

#-------------    
#donor section
#-------------

@app.route("/donor/login", methods=["GET", "POST"])
def donor_login():
    if "donor_id" in session:
        return redirect(url_for("donor_dashboard"))

    if request.method == "POST":

        email = request.form.get("email")
        password = request.form.get("password")

        cursor = mydb.cursor(dictionary=True)
        cursor.execute("SELECT * FROM donors WHERE email=%s", (email,))
        donor = cursor.fetchone()

        # Donor not found OR deleted OR rejected
        if not donor or donor["status"] == "Rejected" or donor["is_active"] == 0:
            flash("Your profile does not exist or it may be rejected or deleted.", "error")
            return redirect(url_for("donor_login"))

        #  Incorrect Password
        if not check_password_hash(donor["password_hash"], password):
            flash("Incorrect credentials!", "error")
            return redirect(url_for("donor_login"))

        #  Pending Status
        if donor["status"] == "Pending":
            flash("Your profile is under review by our team.", "error")
            return redirect(url_for("donor_login"))

        #  Approved Donor — Login Successful
        if donor["status"] == "Approved":
            session["donor_logged_in"] = True
            session["donor_id"] = donor["donor_id"]
            session["donor_name"] = donor["full_name"]
            return redirect(url_for("donor_dashboard"))

    return render_template("donor_login.html")

#donor registeration form
@app.route("/donor/register", methods=["GET", "POST"])
def donor_register():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        gender = request.form.get("gender")
        blood_group = request.form.get("blood_group")
        weight_kg = request.form.get("weight_kg")
        age = request.form.get("age")
        phone = request.form.get("phone")
        address = request.form.get("address", "").strip()

        donated_before = request.form.get("donated_before")
        last_donation_date = request.form.get("last_donation_date") or None

        any_disease = request.form.get("any_disease")
        bleeding_disorder = request.form.get("bleeding_disorder")
        diabetic = request.form.get("diabetic")

        email = request.form.get("email", "").strip()
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        consent = request.form.get("consent")  # "on" if checked else None

       

        # 1) last donation date only if 'Yes'
        if donated_before == "Yes" and not last_donation_date:
            return render_template("donor_registration.html",
                                   error="Please enter the last date of blood donation.")
        # 2) email already exists?
        cursor = mydb.cursor(dictionary=True)
        cursor.execute("SELECT donor_id FROM donors WHERE email = %s", (email,))
        existing = cursor.fetchone()
        if existing:
            cursor.close()
            return render_template("donor_registration.html",
                                   error="An account with this email already exists.")
        # 3) passwords must match
        if password != confirm_password:
            return render_template("donor_registration.html",
                                   error="Passwords do not match.")

        # 4) consent must be ticked
        if not consent:
            return render_template("donor_registration.html",
                                   error="You must accept the consent to register.")

         # 5) basic required field check
        required_ok = all([
            full_name, gender, blood_group, weight_kg, age, phone,
            address, donated_before, any_disease, bleeding_disorder,
            diabetic, email, password, confirm_password
        ])
        if not required_ok:
            return render_template("donor_registration.html",
                                   error="Please fill in all required fields.")

        # 6) insert into DB
        password_hash = generate_password_hash(password)

        insert_sql = """
            INSERT INTO donors
            (full_name, gender, blood_group, weight_kg, age, phone, address,
             donated_before, last_donation_date, any_disease, bleeding_disorder,
             diabetic, email, password_hash, consent_given, status)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """
        values = (
            full_name,
            gender,
            blood_group,
            weight_kg,
            age,
            phone,
            address,
            donated_before,
            last_donation_date,
            any_disease,
            bleeding_disorder,
            diabetic,
            email,
            password_hash,
            1,           
            "Pending"    
        )

        cursor.execute(insert_sql, values)
        mydb.commit()
        cursor.close()

        # Redirect-after-POST -> no double submit on back
        return redirect(url_for("donor_register_success"))

    # GET request
    return render_template("donor_registration.html", error=None)


#donor registeration successful page
@app.route("/donor/register/success")
def donor_register_success():
    return render_template("donor_submit_success.html")

#Donor dashboard
@app.route("/donor/dashboard")
def donor_dashboard():
    # Check logged in user
    donor_id = session.get("donor_id")
    if not donor_id:
        return redirect(url_for("donor_login"))

    cursor = mydb.cursor(dictionary=True)
    cursor.execute("SELECT full_name FROM donors WHERE donor_id = %s", (donor_id,))
    donor = cursor.fetchone()
    cursor.close()

    if not donor:
        return redirect(url_for("donor_login"))

    return render_template("donor_dashboard.html", donor_name=donor["full_name"])

#donor manage account   
@app.route("/donor/manage-account")
def donor_manage_account():

    # donor must be logged in
    if "donor_id" not in session:
        return redirect(url_for("donor_login"))

    return render_template("donor_manage_account.html")

# Donor view profile
@app.route("/donor/manage/view")
def donor_view_profile():
    # Check login
    if "donor_logged_in" not in session:
        return redirect(url_for("donor_login"))

    donor_id = session["donor_id"]

    cursor = mydb.cursor(dictionary=True)
    cursor.execute("SELECT * FROM donors WHERE donor_id = %s", (donor_id,))
    donor = cursor.fetchone()
    cursor.close()

    if not donor:
        return "Donor not found!", 404

    return render_template("donor_view_profile.html", donor=donor)


#donor edit profile 
@app.route("/donor/manage/edit", methods=["GET", "POST"])
def donor_edit_profile():
    if "donor_logged_in" not in session:
        return redirect(url_for("donor_login"))

    donor_id = session["donor_id"]

    def get_donor():
        c = mydb.cursor(dictionary=True)
        c.execute("SELECT * FROM donors WHERE donor_id = %s", (donor_id,))
        data = c.fetchone()
        c.close()
        return data

    # GET request → show form
    if request.method == "GET":
        donor = get_donor()
        return render_template("donor_edit.html", donor=donor, error=None)

    # POST request → update logic
    name = request.form.get("name", "").strip()
    weight = request.form.get("weight")
    age = request.form.get("age")
    phone = request.form.get("phone")
    address = request.form.get("address", "").strip()

    donated_before = request.form.get("donated_before")
    last_donation_date = request.form.get("last_donation_date") or None

    any_disease = request.form.get("any_disease")
    bleeding_disorder = request.form.get("bleeding_disorder")
    diabetic = request.form.get("diabetic")

    email = request.form.get("email", "").strip()
    password = request.form.get("password") or ""
    confirm_password = request.form.get("confirm_password") or ""

    def error(msg):
        donor = get_donor()
        return render_template("donor_edit.html", donor=donor, error=msg)

    # validations
    if not all([name, weight, age, phone, address,
                donated_before, any_disease, bleeding_disorder,
                diabetic, email]):
        return error("Please fill in all required fields.")

    if donated_before == "Yes" and not last_donation_date:
        return error("Please enter the last donation date.")

    if (password or confirm_password) and password != confirm_password:
        return error("Passwords do not match.")

    # email unique (except self)
    c = mydb.cursor(dictionary=True)
    c.execute("SELECT donor_id FROM donors WHERE email=%s AND donor_id!=%s", (email, donor_id))
    if c.fetchone():
        c.close()
        return error("This email is already used by another donor.")
    c.close()

    # update
    update_sql = """
        UPDATE donors SET 
            full_name=%s, weight_kg=%s, age=%s, phone=%s, address=%s,
            donated_before=%s, last_donation_date=%s,
            any_disease=%s, bleeding_disorder=%s, diabetic=%s,
            email=%s
    """
    values = [name, weight, age, phone, address,
              donated_before, last_donation_date,
              any_disease, bleeding_disorder, diabetic,
              email]

    if password:
        update_sql += ", password_hash=%s"
        values.append(generate_password_hash(password))

    update_sql += " WHERE donor_id=%s"
    values.append(donor_id)

    c = mydb.cursor()
    c.execute(update_sql, tuple(values))
    mydb.commit()
    c.close()

    session["donor_name"] = name

    return redirect(url_for("donor_manage_account"))

#delete donor account
@app.route("/donor/manage/delete", methods=["GET", "POST"])
def donor_delete_account():
    if "donor_logged_in" not in session:
        return redirect(url_for("donor_login"))

    donor_id = session["donor_id"]

    # --- GET → show form ---
    if request.method == "GET":
        return render_template("donor_delete_account.html", error=None)

    # --- POST → start validation ---
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")
    reason = request.form.get("reason", "")

    cursor = mydb.cursor(dictionary=True)

    # Load donor
    cursor.execute("SELECT * FROM donors WHERE donor_id=%s", (donor_id,))
    donor = cursor.fetchone()

    if not donor:
        cursor.close()
        return render_template("donor_delete_account.html", error="Donor not found.")

    # 1) Check email
    if email != donor["email"]:
        cursor.close()
        return render_template("donor_delete_account.html", error="Incorrect email address.")

    # 2) Check passwords match
    if password != confirm_password:
        cursor.close()
        return render_template("donor_delete_account.html", error="Passwords do not match.")

    # 3) Verify password hash
    if not check_password_hash(donor["password_hash"], password):
        cursor.close()
        return render_template("donor_delete_account.html", error="Incorrect password.")

    # 4) Reason required
    if not reason:
        cursor.close()
        return render_template("donor_delete_account.html", error="Please select a reason.")

    # 5) Delete account
    cursor.execute("DELETE FROM donors WHERE donor_id=%s", (donor_id,))
    mydb.commit()
    cursor.close()

    # 6) Logout user
    session.clear()

    return redirect(url_for("donor_login"))

#donor request board
@app.route("/donor/request-board")
def donor_request_board():

    if "donor_id" not in session:
        return redirect(url_for("donor_login"))

    donor_id = session["donor_id"]
    cursor = mydb.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            dr.request_id,
            dr.request_date,
            p.patient_id,
            p.name AS patient_name,
            p.blood_group
        FROM donation_requests dr
        JOIN patients p ON p.patient_id = dr.patient_id
        WHERE dr.donor_id = %s
          AND dr.status = 'Pending'
    """, (donor_id,))

    requests = cursor.fetchall()
    cursor.close()

    return render_template(
        "donor_request_board.html",
        requests=requests
    )

#accept request of patient
@app.route("/donor/request/accept/<int:request_id>", methods=["POST"])
def donor_accept_request(request_id):

    if "donor_id" not in session:
        return redirect(url_for("donor_login"))

    donor_id = session["donor_id"]
    cursor = mydb.cursor(dictionary=True)

    # Fetch request + patient data
    cursor.execute("""
        SELECT
            dr.patient_id,
            p.reason,
            p.hospital_name
        FROM donation_requests dr
        JOIN patients p ON p.patient_id = dr.patient_id
        WHERE dr.request_id = %s
          AND dr.donor_id = %s
    """, (request_id, donor_id))

    data = cursor.fetchone()
    if not data:
        cursor.close()
        return "Invalid request", 400

    # INSERT INTO donations
    cursor.execute("""
        INSERT INTO donations
        (donor_id, patient_id, request_date, last_updated,
         status, reason, hospital_name)
        VALUES (%s, %s, CURDATE(), CURDATE(),
                'Active', %s, %s)
    """, (
        donor_id,
        data["patient_id"],
        data["reason"],
        data["hospital_name"]
    ))

    # DELETE request
    cursor.execute("""
        DELETE FROM donation_requests
        WHERE request_id = %s
    """, (request_id,))

    mydb.commit()
    cursor.close()

    return redirect(url_for("donor_request_board"))


#reject request of patient
@app.route("/donor/request/reject/<int:request_id>", methods=["POST"])
def donor_reject_request(request_id):

    if "donor_id" not in session:
        return redirect(url_for("donor_login"))

    donor_id = session["donor_id"]
    cursor = mydb.cursor()

    cursor.execute("""
        DELETE FROM donation_requests
        WHERE request_id = %s
          AND donor_id = %s
    """, (request_id, donor_id))

    mydb.commit()
    cursor.close()

    return redirect(url_for("donor_request_board"))


# VIEW PATIENT DETAILS (HIDDEN)
@app.route("/donor/request/details/<int:request_id>")
def donor_view_patient_details_hidden(request_id):
    if "donor_id" not in session:
        return redirect(url_for("donor_login"))

    donor_id = session["donor_id"]
    cursor = mydb.cursor(dictionary=True)

    # Fetch patient + request data
    cursor.execute("""
        SELECT 
            dr.request_id,
            dr.request_date,
            p.patient_id,
            p.name AS name,
            p.gender,
            p.blood_group,
            p.weight,
            p.age,
            p.phone,
            p.address,
            p.reason,
            p.hospital_name,
            p.email
        FROM donation_requests dr
        JOIN patients p ON p.patient_id = dr.patient_id
        WHERE dr.request_id = %s AND dr.donor_id = %s
    """, (request_id, donor_id))

    donation_request = cursor.fetchone()
    cursor.close()

    if not donation_request:
        flash("No such request found or unauthorized access", "error")
        return redirect(url_for("donor_request_board"))

    # Mask phone & email
    phone = donation_request["phone"]
    masked_phone = phone[:2] + "******" + phone[-2:]

    email = donation_request["email"]
    masked_email = email[:3] + "******@" + email.split("@")[1]

    return render_template(
        "donorside_patient_details_hidden.html",
        patient=donation_request,
        donation_request=donation_request,
        masked_phone=masked_phone,
        masked_email=masked_email
    )

#accept from details page
@app.route("/donor/request/accept/from-details/<int:request_id>", methods=["POST"])
def donor_accept_from_details(request_id):
    if "donor_id" not in session:
        return redirect(url_for("donor_login"))

    donor_id = session["donor_id"]
    cursor = mydb.cursor(dictionary=True)

    # Fetch patient info from request
    cursor.execute("""
        SELECT dr.patient_id, p.reason, p.hospital_name
        FROM donation_requests dr
        JOIN patients p ON p.patient_id = dr.patient_id
        WHERE dr.request_id = %s AND dr.donor_id = %s
    """, (request_id, donor_id))
    data = cursor.fetchone()

    if not data:
        cursor.close()
        flash("Request not found.", "error")
        return redirect(url_for("donor_request_board"))

    # Create donation entry
    cursor.execute("""
        INSERT INTO donations
        (donor_id, patient_id, request_date, last_updated,
         status, reason, hospital_name)
        VALUES (%s, %s, CURDATE(), CURDATE(),
                'Active', %s, %s)
    """, (
        donor_id,
        data["patient_id"],
        data["reason"],
        data["hospital_name"]
    ))

    # Delete request from donation_requests
    cursor.execute("DELETE FROM donation_requests WHERE request_id = %s", (request_id,))
    mydb.commit()
    cursor.close()

    return redirect(url_for("donor_request_board"))

#reject from details page
@app.route("/donor/request/reject/from-details/<int:request_id>", methods=["POST"])
def donor_reject_from_details(request_id):
    if "donor_id" not in session:
        return redirect(url_for("donor_login"))

    donor_id = session["donor_id"]
    cursor = mydb.cursor()

    cursor.execute("""
        DELETE FROM donation_requests
        WHERE request_id = %s AND donor_id = %s
    """, (request_id, donor_id))

    mydb.commit()
    cursor.close()

    return redirect(url_for("donor_request_board"))

#my donation page of donor
@app.route("/donor/my-donations")
def donor_my_donations():

    if "donor_id" not in session:
        return redirect(url_for("donor_login"))

    return render_template("donorside_my_donations.html")

#active donation section of donor
@app.route("/donor/active-donations")
def donor_active_donations():

    if "donor_id" not in session:
        return redirect(url_for("donor_login"))

    donor_id = session["donor_id"]
    cursor = mydb.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            d.donation_id,
            d.request_date,
            d.donor_confirmed,
            d.patient_confirmed,
            p.name AS patient_name,
            p.blood_group
        FROM donations d
        JOIN patients p ON p.patient_id = d.patient_id
        WHERE d.donor_id = %s
          AND d.status IN ('Active', 'Pending Patient Approval','Pending Donor Approval')
    """, (donor_id,))

    donations = cursor.fetchall()
    cursor.close()

    return render_template(
        "donor_active_donations.html",
        donations=donations
    )

#donation confirming logic
@app.route("/donor/confirm-donation/<int:donation_id>", methods=["POST"])
def donor_confirm_donation(donation_id):

    if "donor_id" not in session:
        return redirect(url_for("donor_login"))

    cursor = mydb.cursor()

    # mark donor confirmed
    cursor.execute("""
        UPDATE donations
        SET donor_confirmed = 'Yes',
            last_updated = CURDATE()
        WHERE donation_id = %s
    """, (donation_id,))

    # check if patient also confirmed
    cursor.execute("""
        SELECT patient_confirmed
        FROM donations
        WHERE donation_id = %s
    """, (donation_id,))
    patient_confirmed = cursor.fetchone()[0]

    # if both confirmed → move to completed
    if patient_confirmed == 'Yes':
        cursor.execute("""
            UPDATE donations
            SET status = 'Completed',
                completion_date = CURDATE()
            WHERE donation_id = %s
        """, (donation_id,))

    mydb.commit()
    cursor.close()

    return redirect(url_for("donor_active_donations"))

# open details of patient after accepting request
@app.route("/donor/active-donation/details/<int:donation_id>")
def donor_active_donation_details(donation_id):

    if "donor_id" not in session:
        return redirect(url_for("donor_login"))

    donor_id = session["donor_id"]
    cursor = mydb.cursor(dictionary=True)

    # 1️ Fetch donation (ensure it belongs to logged-in donor)
    cursor.execute("""
        SELECT *
        FROM donations
        WHERE donation_id = %s
          AND donor_id = %s
    """, (donation_id, donor_id))
    donation = cursor.fetchone()

    if not donation:
        cursor.close()
        return redirect(url_for("donor_active_donations"))

    # 2️ Fetch patient
    cursor.execute("""
        SELECT *
        FROM patients
        WHERE patient_id = %s
    """, (donation["patient_id"],))
    patient = cursor.fetchone()

    cursor.close()

    if not patient:
        return redirect(url_for("donor_active_donations"))

    return render_template(
        "donorside_patient_details_open.html",

        patient_name = patient["name"],
        gender       = patient["gender"],
        blood_group  = patient["blood_group"],
        weight       = patient["weight"],
        age          = patient["age"],

        request_date = donation["request_date"].strftime("%d/%m/%Y"),

        phone_number = patient["phone"],
        city         = patient["address"],
        reason       = donation["reason"],
        hospital     = donation["hospital_name"],
        email        = patient["email"]
    )

#donorside donation history
@app.route("/donor/donation-history")
def donor_donation_history():

    if "donor_id" not in session:
        return redirect(url_for("donor_login"))

    donor_id = session["donor_id"]
    cursor = mydb.cursor(dictionary=True)

    cursor.execute("""
    SELECT
        d.donation_id,
        d.completion_date,
        p.name AS patient_name,
        p.blood_group
    FROM donations d
    JOIN patients p ON d.patient_id = p.patient_id
    WHERE d.donor_id = %s
      AND d.status = 'Completed'
      AND d.completion_date IS NOT NULL
    ORDER BY d.completion_date DESC
 """, (donor_id,))
 

    donations = cursor.fetchall()
    cursor.close()

    return render_template(
        "donorside_donation_history.html",
        donations=donations
    )

# Donor Logout    
@app.route("/donor/logout")
def donor_logout():
    session.pop("donor_id", None)
    return redirect(url_for("home"))


#----------------
#patient section
#----------------

#patient login
@app.route("/patient/login", methods=["GET", "POST"])
def patient_login():
    if "patient_id" in session:
        return redirect(url_for("patient_dashboard"))

    if request.method == "POST":

        email = request.form.get("email")
        password = request.form.get("password")

        cursor = mydb.cursor(dictionary=True)
        cursor.execute("SELECT * FROM patients WHERE email=%s", (email,))
        patient = cursor.fetchone()

        #  Patient not found OR deleted OR rejected
        if not patient :
            flash("Your profile does not exist or it may be rejected or deleted.", "error")
            return redirect(url_for("patient_login"))

        #  Incorrect Password
        if not check_password_hash(patient["password_hash"], password):
            flash("Incorrect credentials!", "error")
            return redirect(url_for("patient_login"))

        #  Pending Status
        if patient["status"] == "pending":
            flash("Your profile is under review by our team.", "error")
            return redirect(url_for("patient_login"))

        #  Approved Patient — Login Successful
        if patient["status"] == "approved":
            session["patient_logged_in"] = True
            session["patient_id"] = patient["patient_id"]
            session["patient_name"] = patient["name"]
            return redirect(url_for("patient_dashboard"))

    return render_template("patient_login.html")

#patient registration form
@app.route("/patient/register" , methods=["GET", "POST"])
def patient_register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        gender = request.form.get("gender")
        blood_group = request.form.get("blood_group")
        weight = request.form.get("weight")
        age = request.form.get("age")
        phone = request.form.get("phone")
        address = request.form.get("address", "").strip()

        reason = request.form.get("reason").strip()
        hospital_name = request.form.get("hospital_name").strip()

        email = request.form.get("email", "").strip()
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        consent = request.form.get("consent")  # "on" if checked else None

    
        # 1) email already exists?
        cursor = mydb.cursor(dictionary=True)
        cursor.execute("SELECT patient_id FROM patients WHERE email = %s", (email,))
        existing = cursor.fetchone()
        if existing:
            cursor.close()
            return render_template("patient_registration.html",
                                   error="An account with this email already exists.")
        # 2) passwords must match
        if password != confirm_password:
            return render_template("patient_registration.html",
                                   error="Passwords do not match.")

        # 3) consent must be ticked
        if not consent:
            return render_template("patient_registration.html",
                                   error="You must accept the consent to register.")

       
         # 4) basic required field check
        required_ok = all([
            name, gender, blood_group, weight, age, phone,
            address, reason, hospital_name, email, password, confirm_password
        ])
        if not required_ok:
            return render_template("patient_registration.html",
                                   error="Please fill in all required fields.")

        # 5) insert into DB
        password_hash = generate_password_hash(password)

        insert_sql = """
            INSERT INTO patients
            (name, gender, blood_group, weight, age, phone, address,
             reason, hospital_name,  email, password_hash, status, consent_accepted)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """
        values = (
            name,
            gender,
            blood_group,
            weight,
            age,
            phone,
            address,
            reason,
            hospital_name,
            email,
            password_hash,
            "pending",  
            1,          
              
        )

        cursor.execute(insert_sql, values)
        mydb.commit()
        cursor.close()

        # Redirect-after-POST -> no double submit on back
        return redirect(url_for("patient_register_success"))

    # GET request
    return render_template("patient_registration.html")
#patient registeration successful page
@app.route("/patient/register/success")
def patient_register_success():
    return render_template("patient_submit_success.html")

#patient dashboard
@app.route("/patient/dashboard")
def patient_dashboard():

    # Check logged in user
    patient_id = session.get("patient_id")
    if not patient_id:
        return redirect(url_for("patient_login"))

    cursor = mydb.cursor(dictionary=True)
    cursor.execute("SELECT name FROM patients WHERE patient_id = %s", (patient_id,))
    patient = cursor.fetchone()
    cursor.close()

    if not patient:
        return redirect(url_for("patient_login"))

    return render_template("patient_dashboard.html", patient_name=patient["name"])
#manage patient
@app.route("/patient/manage-account")
def patient_manage_account():
     # patient must be logged in
    if "patient_id" not in session:
        return redirect(url_for("patient_login"))

    return render_template("patient_manage_account.html")
#Patient view profile
@app.route("/patient/manage/view")
def patient_view_profile():
    if "patient_logged_in" not in session:
        return redirect(url_for("patient_login"))

    patient_id = session["patient_id"]
    cursor = mydb.cursor(dictionary=True)
    cursor.execute("SELECT * FROM patients WHERE patient_id = %s", (patient_id,))
    patient = cursor.fetchone()
    cursor.close()

    if not patient:
        return "Patient not found!", 404

    return render_template("patient_view_profile.html", patient=patient)

#edit patient account    
@app.route("/patient/manage/edit", methods=["GET","POST"])
def patient_edit_profile():
    if "patient_logged_in" not in session:
        return redirect(url_for("patient_login"))

    patient_id = session["patient_id"]

    def get_patient():
        c = mydb.cursor(dictionary=True)
        c.execute("SELECT * FROM patients WHERE patient_id = %s", (patient_id,))
        data = c.fetchone()
        c.close()
        return data

    # GET request → show form
    if request.method == "GET":
        patient = get_patient()
        return render_template("patient_edit_profile.html", patient=patient, error=None)

    # POST request → update logic
    name = request.form.get("name", "").strip()
    weight = request.form.get("weight")
    age = request.form.get("age")
    phone = request.form.get("phone")
    address = request.form.get("address", "").strip()

    reason = request.form.get("reason", "").strip()
    hospital = request.form.get("hospital", "").strip()


    email = request.form.get("email", "").strip()
    new_password = request.form.get("new_password") or ""
    confirm_password = request.form.get("confirm_password") or ""

    def error(msg):
        patient = get_patient()
        return render_template("patient_edit_profile.html", patient=patient, error=msg)

    # validations
    if not all([name, weight, age, phone, address,
                reason,hospital, email]):
        return error("Please fill in all required fields.")

    if (new_password or confirm_password) and new_password != confirm_password:
        return error("Passwords do not match.")

    # email unique (except self)
    c = mydb.cursor(dictionary=True)
    c.execute("SELECT patient_id FROM patients WHERE email=%s AND patient_id!=%s", (email, patient_id))
    if c.fetchone():
        c.close()
        return error("This email is already used by another patient.")
    c.close()

    # update
    update_sql = """
        UPDATE patients SET 
            name=%s, weight=%s, age=%s, phone=%s, address=%s,
            reason=%s, hospital_name=%s,email=%s
    """
    values = [name, weight, age, phone, address,reason,hospital,
              email]

    if new_password:
        update_sql += ", password_hash=%s"
        values.append(generate_password_hash(new_password))

    update_sql += " WHERE patient_id=%s"
    values.append(patient_id)

    c = mydb.cursor()
    c.execute(update_sql, tuple(values))
    mydb.commit()
    c.close()

    session["patient_name"] = name

    return redirect(url_for("patient_manage_account"))

@app.route("/patient/manage/delete", methods=["GET", "POST"])
def patient_delete_account():
    if "patient_logged_in" not in session:
        return redirect(url_for("patient_login"))

    patient_id = session["patient_id"]

    # --- GET → show form ---
    if request.method == "GET":
        return render_template("patient_delete_account.html", error=None)

    # --- POST → start validation ---
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")
    reason = request.form.get("reason", "")

    cursor = mydb.cursor(dictionary=True)

    # Load patient
    cursor.execute("SELECT * FROM patients WHERE patient_id=%s", (patient_id,))
    patient = cursor.fetchone()

    if not patient:
        cursor.close()
        return render_template("patient_delete_account.html", error="Patient not found.")

    # 1) Check email
    if email != patient["email"]:
        cursor.close()
        return render_template("patient_delete_account.html", error="Incorrect email address.")

    # 2) Check passwords match
    if password != confirm_password:
        cursor.close()
        return render_template("patient_delete_account.html", error="Passwords do not match.")

    # 3) Verify password hash
    if not check_password_hash(patient["password_hash"], password):
        cursor.close()
        return render_template("patient_delete_account.html", error="Incorrect password.")

    # 4) Reason required
    if not reason:
        cursor.close()
        return render_template("patient_delete_account.html", error="Please select a reason.")

    # 5) Delete account
    cursor.execute("DELETE FROM patients WHERE patient_id=%s", (patient_id,))
    mydb.commit()
    cursor.close()

    # 6) Logout user
    session.clear()

    return redirect(url_for("patient_login"))
    
#matching donors at patient side
@app.route("/patient/matching-donors")
def matching_donors():
    if "patient_id" not in session:
        return redirect(url_for("patient_login"))

    patient_id = session["patient_id"]
    cursor = mydb.cursor(dictionary=True)

    # Patient blood group
    cursor.execute(
        "SELECT blood_group FROM patients WHERE patient_id = %s",
        (patient_id,)
    )
    patient = cursor.fetchone()

    if not patient:
        cursor.close()
        return redirect(url_for("patient_login"))

    blood_group = patient["blood_group"]

    #  CORE LOGIC: exclude donors with ACTIVE donation with this patient
    cursor.execute("""
        SELECT d.donor_id, d.full_name, d.blood_group,
        EXISTS (
            SELECT 1 FROM donation_requests r
            WHERE r.donor_id = d.donor_id
              AND r.patient_id = %s
              AND r.status = 'Pending'
        ) AS requested
        FROM donors d
        WHERE d.blood_group = %s
          AND d.status = 'Approved'
          AND d.is_active = 1
          AND d.donor_id NOT IN (
              SELECT donor_id FROM donations
              WHERE patient_id = %s
                AND status != 'Completed'
          )
    """, (patient_id, blood_group, patient_id))

    donors = cursor.fetchall()
    cursor.close()

    return render_template("matching_donors.html", donors=donors)


#send request from patient to donor
@app.route("/patient/send-request/<int:donor_id>", methods=["POST"])
def patient_send_request(donor_id):

    if "patient_id" not in session:
        return redirect(url_for("patient_login"))

    patient_id = session["patient_id"]
    cursor = mydb.cursor()

    try:
        cursor.execute("""
            INSERT INTO donation_requests
            (donor_id, patient_id, request_date, last_updated, status)
            VALUES (%s, %s, CURDATE(), CURDATE(), 'Pending')
        """, (donor_id, patient_id))

        mydb.commit()

    except IntegrityError:
        # request already exists → ignore silently
        mydb.rollback()

    finally:
        cursor.close()

    return redirect(url_for("matching_donors"))

#cancel sent request
@app.route("/patient/cancel-request/<int:donor_id>", methods=["POST"])
def patient_cancel_request(donor_id):

    if "patient_id" not in session:
        return redirect(url_for("patient_login"))

    patient_id = session["patient_id"]
    cursor = mydb.cursor()

    cursor.execute("""
        DELETE FROM donation_requests
        WHERE donor_id = %s
          AND patient_id = %s
          AND status = 'Pending'
    """, (donor_id, patient_id))

    mydb.commit()
    cursor.close()

    return redirect(url_for("matching_donors"))

#hidden donor details
@app.route("/patient/donor/<int:donor_id>", methods=["GET", "POST"])
def patient_view_donor_details_hidden(donor_id):

    if "patient_id" not in session:
        return redirect(url_for("patient_login"))

    patient_id = session["patient_id"]
    cursor = mydb.cursor(dictionary=True)

    # 1️ Fetch donor (must be available)
    cursor.execute("""
        SELECT *
        FROM donors
        WHERE donor_id = %s
          AND status = 'Approved'
          AND is_active = 1
    """, (donor_id,))
    donor = cursor.fetchone()

    if not donor:
        cursor.close()
        return redirect(url_for("matching_donors"))

    # 2️ Check existing request
    cursor.execute("""
        SELECT request_id, status
        FROM donation_requests
        WHERE donor_id = %s
          AND patient_id = %s
    """, (donor_id, patient_id))
    request_row = cursor.fetchone()

    # 3️ POST logic (Send / Cancel)
    if request.method == "POST":

        if request_row:
            # Cancel request (only Pending will exist here)
            cursor.execute("""
                DELETE FROM donation_requests
                WHERE request_id = %s
            """, (request_row["request_id"],))
            mydb.commit()

        else:
            #  Send new request
            cursor.execute("""
                INSERT INTO donation_requests
                (donor_id, patient_id, request_date, last_updated, status)
                VALUES (%s, %s, CURDATE(), CURDATE(), 'Pending')
            """, (donor_id, patient_id))
            mydb.commit()

        cursor.close()
        return redirect(
            url_for("patient_view_donor_details_hidden", donor_id=donor_id)
        )

    cursor.close()

    # 4️ Masking (VIEW ONLY)
    phone = donor["phone"]
    masked_phone = phone[:2] + "******" + phone[-2:]

    email = donor["email"]
    masked_email = email[:3] + "******@" + email.split("@")[1]

    # 5️ Button text
    request_status = "Requested" if request_row else "Send Request"

    return render_template(
        "patientside_donor_detail_hidden.html",
        donor=donor,
        masked_phone=masked_phone,
        masked_email=masked_email,
        request_status=request_status
    )

#my requests pge of patient
@app.route("/patient/my-requests")
def patient_my_requests():
    if "patient_id" not in session:
        return redirect(url_for("patient_login"))

    return render_template("patientside_my_requests.html")

#active requests of patient
@app.route("/patient/active-requests")
def patient_active_requests():

    if "patient_id" not in session:
        return redirect(url_for("patient_login"))

    patient_id = session["patient_id"]
    cursor = mydb.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            d.donation_id,
            d.request_date,
            d.donor_confirmed,
            d.patient_confirmed,

            dn.full_name AS donor_name,
            dn.blood_group

        FROM donations d
        JOIN donors dn ON dn.donor_id = d.donor_id

        WHERE d.patient_id = %s
          AND d.status IN ('Active', 'Pending Donor Approval','Pending Patient Approval')
    """, (patient_id,))

    donations = cursor.fetchall()
    cursor.close()

    return render_template(
        "patientside_active_requests.html",
        donations=donations
    )


#confirm donation from patientside
@app.route("/patient/confirm-donation/<int:donation_id>", methods=["POST"])
def patient_confirm_donation(donation_id):

    if "patient_id" not in session:
        return redirect(url_for("patient_login"))

    patient_id = session["patient_id"]
    cursor = mydb.cursor(dictionary=True)

    # Fetch donation
    cursor.execute("""
        SELECT *
        FROM donations
        WHERE donation_id = %s
          AND patient_id = %s
    """, (donation_id, patient_id))
    donation = cursor.fetchone()

    if not donation or donation["patient_confirmed"] == "Yes":
        cursor.close()
        return redirect(url_for("patient_active_requests"))

    # Update patient confirmation
    if donation["donor_confirmed"] == "Yes":
        cursor.execute("""
            UPDATE donations
            SET patient_confirmed='Yes',
                status='Completed',
                completion_date=CURDATE(),
                last_updated=CURDATE()
            WHERE donation_id=%s
        """, (donation_id,))
    else:
        cursor.execute("""
            UPDATE donations
            SET patient_confirmed='Yes',
                status='Pending Donor Approval',
                last_updated=CURDATE()
            WHERE donation_id=%s
        """, (donation_id,))

    mydb.commit()
    cursor.close()

    return redirect(url_for("patient_active_requests"))

#donor details at patientside not hidden
@app.route("/patient/active-donation/details/<int:donation_id>")
def patient_active_donation_details(donation_id):

    if "patient_id" not in session:
        return redirect(url_for("patient_login"))

    patient_id = session["patient_id"]
    cursor = mydb.cursor(dictionary=True)

    # Fetch donation (security check)
    cursor.execute("""
        SELECT *
        FROM donations
        WHERE donation_id = %s
          AND patient_id = %s
          AND status IN ('Active', 'Pending Donor Approval', 'Pending Patient Approval')
    """, (donation_id, patient_id))

    donation = cursor.fetchone()

    if not donation:
        cursor.close()
        return redirect(url_for("patient_active_requests"))

    # Fetch donor details
    cursor.execute("""
        SELECT *
        FROM donors
        WHERE donor_id = %s
    """, (donation["donor_id"],))

    donor = cursor.fetchone()
    cursor.close()

    return render_template(
        "patientside_donor_detail_open.html",
        donor=donor
    )


@app.route("/patient/donation-history")
def patient_donation_history():

    if "patient_id" not in session:
        return redirect(url_for("patient_login"))

    patient_id = session["patient_id"]
    cursor = mydb.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            d.donation_id,
            d.completion_date,
            dn.full_name AS donor_name,
            dn.blood_group
        FROM donations d
        JOIN donors dn ON d.donor_id = dn.donor_id
        WHERE d.patient_id = %s
          AND d.status = 'Completed'
        ORDER BY d.completion_date DESC
    """, (patient_id,))

    donations = cursor.fetchall()
    cursor.close()

    return render_template(
        "patientside_request_history.html",
        donations=donations
    )

#logout Patient
@app.route("/patient/logout")
def patient_logout():
    session.pop("patient_id", None)
    return redirect(url_for("home"))

#------------------------------
#        about page
#-------------------------------

#about
@app.route("/about")
def about():
    return render_template("about.html")
#contact
@app.route("/contact")
def contact():
    return render_template("contact.html")

#--------------
#admin section
#--------------

#creating admin credentials
def create_default_admin():
    cursor = mydb.cursor()

    # Check if admin exists
    cursor.execute("SELECT * FROM admin")
    result = cursor.fetchone()

    # If NOT exists → create new
    if not result:
        username = "admin"
        password = generate_password_hash("test123")  # HASHED PASSWORD

        cursor.execute(
            "INSERT INTO admin (username, password) VALUES (%s, %s)",
            (username, password)
        )
        mydb.commit()
        print(" Default Admin Created: username=admin | password=test123")

create_default_admin()

def admin_required(f):
    def wrap(*args, **kwargs):
        if "admin_logged_in" not in session:
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap


#admin login
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if "admin_logged_in" in session:
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        cursor = mydb.cursor(dictionary=True)
        cursor.execute("SELECT * FROM admin WHERE username = %s", (username,))
        admin = cursor.fetchone()

        if admin and check_password_hash(admin["password"], password):
            session["admin_logged_in"] = True
            session["admin_username"] = admin["username"]
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid username or password!", "error")

    return render_template("admin_login.html")

#admin dashboard
@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():

    cursor = mydb.cursor()

    # Total donors
    cursor.execute("SELECT COUNT(*) FROM donors WHERE status = 'Approved'")
    total_donors = cursor.fetchone()[0]

    # Total patients
    cursor.execute("SELECT COUNT(*) FROM patients WHERE status = 'approved'")
    total_patients = cursor.fetchone()[0]

    # Total camps
    cursor.execute("SELECT COUNT(*) FROM camps")
    total_camps = cursor.fetchone()[0]

    # Pending donor + patient requests
    cursor.execute("SELECT COUNT(*) FROM donors WHERE status='Pending'")
    pending_donors = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM patients WHERE status='pending'")
    pending_patients = cursor.fetchone()[0]

    pending_requests = pending_donors + pending_patients

    # Active donations
    cursor.execute("SELECT COUNT(*) FROM donations WHERE status='Active'")
    active_donations = cursor.fetchone()[0]

    # Completed donations
    cursor.execute("SELECT COUNT(*) FROM donations WHERE status='Completed'")
    completed_donations = cursor.fetchone()[0]

    session["last_admin_page"] = url_for("admin_dashboard")

    return render_template("admin_dashboard.html",
                           total_donors=total_donors,
                           total_patients=total_patients,
                           total_camps=total_camps,
                           pending_requests=pending_requests,
                           active_donations=active_donations,
                           completed_donations=completed_donations)

#change admin password
@app.route("/admin/change_password", methods=["GET", "POST"])
def admin_change_password():

    if "admin_logged_in" not in session:
        return redirect(url_for("admin_login"))

    message = None

    if request.method == "POST":

        username = request.form.get("username")
        old_password = request.form.get("old_password")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        # 1️ EMPTY FIELD CHECK
        if not username or not old_password or not new_password or not confirm_password:
            message = "All fields are required!"
            return render_template("admin_change_password.html", message=message)

        # 2️ USERNAME VERIFY
        cursor.execute("SELECT * FROM admin WHERE username=%s", (username,))
        admin = cursor.fetchone()

        if not admin:
            message = "Incorrect username!"
            return render_template("admin_change_password.html", message=message)

        # 3️ OLD PASSWORD VERIFY
        if not check_password_hash(admin["password"], old_password):
            message = "Existing password is incorrect!"
            return render_template("admin_change_password.html", message=message)

        # 4️ NEW PASSWORD MATCH CHECK
        if new_password != confirm_password:
            message = "New password and confirm password do not match!"
            return render_template("admin_change_password.html", message=message)

        # 5️ UPDATE PASSWORD (HASHED!)
        hashed_new_pass = generate_password_hash(new_password)

        cursor.execute("UPDATE admin SET password=%s WHERE admin_id=%s",
                       (hashed_new_pass, admin["admin_id"]))
        mydb.commit()

        # 6️ LOGOUT ADMIN AFTER PASSWORD CHANGE
        session.pop("admin_logged_in", None)

        return redirect(url_for("admin_login"))

    return render_template("admin_change_password.html", message=message)

# admin side camp page
@app.route("/admin/camps")
@admin_required

def admin_camps():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    cursor = mydb.cursor(dictionary=True)
    cursor.execute("SELECT * FROM camps ORDER BY start_date ASC")
    camps = cursor.fetchall()
    cursor.close()

    return render_template("admin_camps.html", camps=camps)

#add camp at admin side
@app.route("/admin/add-camp", methods=["GET", "POST"])
@admin_required

def admin_add_camp():
    if "admin_logged_in" not in session:
        return redirect(url_for("admin_login"))

    if request.method == "POST":
        hospital_name = request.form["hospital_name"]
        address = request.form["address"]
        camp_name = request.form["camp_name"]
        start_date = request.form["start_date"]
        end_date = request.form["end_date"]

        cursor = mydb.cursor()

        sql = """
            INSERT INTO camps (hospital_name, address, camp_name, start_date, end_date)
            VALUES (%s, %s, %s, %s, %s)
        """
        values = (hospital_name, address, camp_name, start_date, end_date)

        cursor.execute(sql, values)
        mydb.commit()
        return redirect(url_for("admin_camps"))

    return render_template("admin_add_camp.html")
    
# delete a camp
@app.route("/admin/delete_camp/<int:camp_id>")
@admin_required
def admin_delete_camp(camp_id):
    # login check
    if "admin_logged_in" not in session:
        return redirect(url_for("admin_login"))

    cursor = mydb.cursor()

    # DELETE query
    sql = "DELETE FROM camps WHERE id = %s"
    cursor.execute(sql, (camp_id,))
    mydb.commit()

    cursor.close()

    # After delete, redirect back to camps page
    return redirect(url_for("admin_camps"))

# camp editing logic
@app.route("/admin/edit_camp/<int:camp_id>", methods=["GET", "POST"])
@admin_required
def admin_edit_camp(camp_id):
    if "admin_logged_in" not in session:
        return redirect(url_for("admin_login"))

    cursor = mydb.cursor(dictionary=True)

    # If POST → Update camp
    if request.method == "POST":
        hospital_name = request.form["hospital_name"]
        address = request.form["address"]
        camp_name = request.form["camp_name"]
        start_date = request.form["start_date"]
        end_date = request.form["end_date"]

        sql = """
            UPDATE camps 
            SET hospital_name=%s, address=%s, camp_name=%s, start_date=%s, end_date=%s
            WHERE id=%s
        """
        values = (hospital_name, address, camp_name, start_date, end_date, camp_id)

        cursor.execute(sql, values)
        mydb.commit()
        cursor.close()

        return redirect(url_for("admin_camps"))

    # If GET → Show form with existing data
    cursor.execute("SELECT * FROM camps WHERE id=%s", (camp_id,))
    camp = cursor.fetchone()
    cursor.close()

    return render_template("admin_edit_camp.html", camp=camp)

#pending donor page
@app.route("/admin/pending_donor")
@admin_required
def admin_pending_donor():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    cursor = mydb.cursor(dictionary=True)
    cursor.execute("SELECT * FROM donors WHERE status = 'Pending'")
    donors = cursor.fetchall()

    return render_template("admin_pending_donor.html", donors=donors)

#approving donor

@app.route("/admin/approve_donor/<int:donor_id>")
@admin_required
def admin_approve_donor(donor_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    cursor = mydb.cursor()
    cursor.execute("UPDATE donors SET status = 'Approved' WHERE donor_id = %s", (donor_id,))
    mydb.commit()
    return redirect(url_for("admin_pending_donor"))

#rejecting donor
@app.route("/admin/reject_donor/<int:donor_id>")
@admin_required
def admin_reject_donor(donor_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    cursor = mydb.cursor()
    cursor.execute("DELETE FROM donors WHERE donor_id = %s", (donor_id,))
    mydb.commit()
    return redirect(url_for("admin_pending_donor"))

#viewing pending donor details
@app.route("/admin/pending_donor/details/<int:donor_id>")
@admin_required
def admin_pending_donor_details(donor_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    cursor = mydb.cursor(dictionary=True)
    cursor.execute("SELECT * FROM donors WHERE donor_id = %s", (donor_id,))
    donor = cursor.fetchone()

    if not donor:
        flash("Donor not found!", "error")
        return redirect(url_for("admin_pending_donor"))

    return render_template("admin_pending_donor_details.html", donor=donor)

#approved donor list page
@app.route("/admin/donors")
@admin_required
def admin_donor_list():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    cursor = mydb.cursor(dictionary=True)
    cursor.execute("SELECT * FROM donors WHERE status = 'Approved'")
    donors = cursor.fetchall()

    return render_template("admin_donor_list.html", donors=donors)

# deleting donor from admin side
@app.route("/admin/donor/delete/<int:donor_id>")
@admin_required
def admin_delete_donor(donor_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    cursor = mydb.cursor()
    cursor.execute("DELETE FROM donors WHERE donor_id = %s", (donor_id,))
    mydb.commit()
    return redirect(url_for("admin_donor_list"))

#approved donor details at admin side
@app.route("/admin/donor/details/<int:donor_id>")
@admin_required
def admin_approved_donor_details(donor_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    cursor = mydb.cursor(dictionary=True)
    cursor.execute("SELECT * FROM donors WHERE donor_id = %s AND status = 'Approved'", (donor_id,))
    donor = cursor.fetchone()

    if not donor:
        return "Invalid Donor ID or donor is not approved."

    return render_template("admin_approved_donor_details.html", donor=donor)

#pending patients at admin side
@app.route("/admin/pending_patient")
@admin_required
def admin_pending_patient():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    cursor = mydb.cursor(dictionary=True)
    cursor.execute("SELECT * FROM patients WHERE status = 'pending'")
    patients = cursor.fetchall()

    return render_template("admin_pending_patient.html", patients=patients)

#approving patient request
@app.route("/admin/approve_patient/<int:patient_id>")
@admin_required
def admin_approve_patient(patient_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    cursor = mydb.cursor()
    cursor.execute("UPDATE patients SET status = 'approved' WHERE patient_id = %s", (patient_id,))
    mydb.commit()

    return redirect(url_for("admin_pending_patient"))

# rejecting patient from admin side
@app.route("/admin/reject_patient/<int:patient_id>")
@admin_required 
def admin_reject_patient(patient_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    cursor = mydb.cursor()
    cursor.execute("DELETE FROM patients WHERE patient_id = %s", (patient_id,))
    mydb.commit()

    return redirect(url_for("admin_pending_patient"))

#pending patients details
@app.route("/admin/pending_patient/details/<int:patient_id>")
@admin_required
def admin_pending_patient_details(patient_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    cursor = mydb.cursor(dictionary=True)
    cursor.execute("SELECT * FROM patients WHERE patient_id = %s", (patient_id,))
    patient = cursor.fetchone()

    if not patient:
        flash("patient not found!", "error")
        return redirect(url_for("admin_pending_patient"))

    return render_template("admin_pending_patient_details.html", patient=patient)

#approved patient list page
@app.route("/admin/patients")
@admin_required
def admin_patient_list():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    cursor = mydb.cursor(dictionary=True)
    cursor.execute("SELECT * FROM patients WHERE status = 'approved'")
    patients = cursor.fetchall()

    return render_template("admin_patient_list.html", patients=patients)

# deleting patient from admin side
@app.route("/admin/patient/delete/<int:patient_id>")
@admin_required
def admin_delete_patient(patient_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    cursor = mydb.cursor()
    cursor.execute("DELETE FROM patients WHERE patient_id = %s", (patient_id,))
    mydb.commit()

    return redirect(url_for("admin_patient_list"))

#approved patient details at admin side
@app.route("/admin/patient/details/<int:patient_id>")
@admin_required
def admin_approved_patient_details(patient_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    cursor = mydb.cursor(dictionary=True)
    cursor.execute("SELECT * FROM patients WHERE patient_id = %s AND status = 'approved'", (patient_id,))
    patient = cursor.fetchone()

    if not patient:
        return "Invalid Patient ID or patient is not approved."

    return render_template("admin_approved_patient_details.html", patient=patient)

#active donations at admin side    
@app.route("/admin/active-donations")
@admin_required
def admin_active_donations():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    cursor = mydb.cursor(dictionary=True)

    # Get all active donations
    cursor.execute("""
        SELECT donation_id, donor_confirmed, patient_confirmed,
               status, request_date, last_updated
        FROM donations
        WHERE status = 'Active'
        ORDER BY donation_id DESC
    """)
    donations = cursor.fetchall()
    cursor.close()

    return render_template("admin_active_donations.html", donations=donations)
    
#active donation details page
@app.route("/admin/active-donations/details/<int:donation_id>")
@admin_required
def admin_active_donation_details(donation_id):

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    cursor = mydb.cursor(dictionary=True)

    # Get donation data
    cursor.execute("SELECT * FROM donations WHERE donation_id = %s", (donation_id,))
    donation = cursor.fetchone()

    if not donation:
        cursor.close()
        flash("Donation record not found!", "error")
        return redirect(url_for("admin_active_donations"))

    # Get donor details
    cursor.execute("SELECT * FROM donors WHERE donor_id = %s", (donation["donor_id"],))
    donor = cursor.fetchone()

    # Get patient details
    cursor.execute("SELECT * FROM patients WHERE patient_id = %s", (donation["patient_id"],))
    patient = cursor.fetchone()

    cursor.close()

    return render_template(
        "admin_active_donation_details.html",
        donation=donation,
        donor=donor,
        patient=patient
    )


#completed donations at admin side
@app.route("/admin/completed-donations")
@admin_required

def admin_completed_donations():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    cursor = mydb.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            donation_id,
            request_date,
            last_updated
        FROM donations
        WHERE status = 'Completed'
        ORDER BY completion_date DESC
    """)

    donations = cursor.fetchall()
    cursor.close()

    return render_template(
        "admin_completed_donations.html",
        donations=donations
    )

@app.route("/admin/completed-donation/details/<int:donation_id>")
@admin_required
def admin_completed_donation_details(donation_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    
    cursor = mydb.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            d.donation_id,
            d.donor_id,
            d.patient_id,
            d.request_date,
            d.last_updated,
            d.reason,
            d.hospital_name,

            dn.full_name AS donor_name,
            dn.blood_group AS blood_group,

            p.name AS patient_name

        FROM donations d
        JOIN donors dn ON d.donor_id = dn.donor_id
        JOIN patients p ON d.patient_id = p.patient_id

        WHERE d.donation_id = %s
          AND d.status = 'Completed'
    """, (donation_id,))

    donation = cursor.fetchone()
    cursor.close()

    if not donation:
        return "<h3>Invalid or non-completed donation</h3>"

    return render_template(
        "admin_completed_donation_details.html",
        donation=donation
    )

# admin logout logic
@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    session.pop("admin_username", None)
    return redirect(url_for("admin_login"))


@app.route("/bloodbot")
def bloodbot():
    return render_template("chatbot.html")
    


@app.route("/chatbot/ask", methods=["POST"])
def chatbot_ask():
    data = request.get_json()
    user_msg = data.get("message", "").strip()

    if not user_msg:
        return "Please ask something 🙂"

    payload = {
        "model": "phi3:mini",
        "prompt": f"You are BloodBot. Answer briefly.\nQuestion: {user_msg}",
        "stream": False
    }

    r = requests.post(OLLAMA_URL, json=payload, timeout=60)
    out = r.json()

    return out.get("response", "").strip()

@app.route("/chatbot/ask_stream", methods=["POST"])
def chatbot_ask_stream():
    data = request.get_json()
    user_msg = data.get("message", "").strip()

    if not user_msg:
        return Response("Please ask something 🙂", mimetype="text/plain")

    prompt = f"""
You are BloodBot, an assistant focused on blood donation and blood-related health.

IMPORTANT:
- NEVER mention rules or instructions in your answer.
- NEVER say things like "To respond following your rules".

RULES FOR RESPONSE LENGTH:

1. Greetings (hi, hello, hey) → reply in ONLY ONE SHORT LINE.

2. Normal questions → clear SHORT answer (max 4–5 lines).

3. Detailed answers ONLY if user asks using words:
"explain", "detail", "why", "how", "in depth", "full explanation".

4. Do NOT stop answer midway. Always complete your sentence.

5. If unrelated question:
"I mainly help with blood donation and blood-related health topics."

Question: {user_msg}
"""

    payload = {
        "model": "phi3:mini",
        "prompt": prompt,
        "stream": True
    }

    def generate():
        try:
            with requests.post(
                OLLAMA_URL,
                json=payload,
                stream=True,
                timeout=60
            ) as r:

                for line in r.iter_lines():
                    if not line:
                        continue

                    try:
                        obj = json.loads(line.decode("utf-8"))
                    except:
                        continue

                    if "response" in obj:
                        text = obj["response"]

                        # 🔴 CLEAN MODEL INTERNAL TEXT
                        junk = [
                            "To respond following your rules:",
                            "According to your rules:",
                            "Following your instructions:",
                        ]

                        for j in junk:
                            text = text.replace(j, "")

                        yield text

        except Exception as e:
            print("STREAM ERROR:", e)
            yield "⚠️ BloodBot unavailable."

    return Response(
        stream_with_context(generate()),
        mimetype="text/plain"
    )


if __name__ == "__main__":
    app.run(debug=True)