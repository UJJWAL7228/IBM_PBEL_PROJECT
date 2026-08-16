from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    send_from_directory,
    jsonify
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from werkzeug.utils import secure_filename

import os
import uuid
import threading
import time

from dotenv import load_dotenv

from predict import predict_transaction

from database import (
    get_connection,
    initialize_database
)

from vercel import blob


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# FLASK
# ============================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    "ibm_pbel_fraud_detection_secret"
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)


# ============================================================
# STORAGE
# ============================================================

if os.environ.get("VERCEL"):

    UPLOAD_FOLDER = None

else:

    UPLOAD_FOLDER = os.path.join(
        BASE_DIR,
        "uploads"
    )

    os.makedirs(
        UPLOAD_FOLDER,
        exist_ok=True
    )


SAMPLE_FOLDER = os.path.join(
    BASE_DIR,
    "static",
    "sample"
)


if not os.environ.get("VERCEL"):

    os.makedirs(
        SAMPLE_FOLDER,
        exist_ok=True
    )


app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

app.config["MAX_CONTENT_LENGTH"] = (
    100 * 1024 * 1024
)


# ============================================================
# CURRENT ANALYSIS
# ============================================================

current_transactions = []

current_stats = {

    "total": 0,

    "safe": 0,

    "risky": 0,

    "fraud": 0

}


# ============================================================
# BACKGROUND ANALYSIS JOBS
# ============================================================

analysis_jobs = {}

analysis_jobs_lock = threading.Lock()


# ============================================================
# CREATE ANALYSIS JOB
# ============================================================

def create_analysis_job():

    job_id = uuid.uuid4().hex

    with analysis_jobs_lock:

        analysis_jobs[job_id] = {

            "status": "queued",

            "progress": 0,

            "processed": 0,

            "total": 0,

            "stage": (
                "Preparing AI analysis..."
            ),

            "error": None,

            "started_at": time.time(),

            "finished_at": None

        }

    return job_id


# ============================================================
# UPDATE ANALYSIS JOB
# ============================================================

def update_analysis_job(

    job_id,

    progress=None,

    processed=None,

    total=None,

    stage=None,

    status=None,

    error=None

):

    with analysis_jobs_lock:

        job = analysis_jobs.get(
            job_id
        )

        if job is None:
            return

        if progress is not None:

            job["progress"] = max(

                0,

                min(
                    100,
                    int(progress)
                )

            )

        if processed is not None:

            job["processed"] = int(
                processed
            )

        if total is not None:

            job["total"] = int(
                total
            )

        if stage is not None:

            job["stage"] = str(
                stage
            )

        if status is not None:

            job["status"] = str(
                status
            )

        if error is not None:

            job["error"] = str(
                error
            )

        if status in {
            "completed",
            "error"
        }:

            job["finished_at"] = (
                time.time()
            )


# ============================================================
# GET ANALYSIS JOB
# ============================================================

def get_analysis_job(job_id):

    with analysis_jobs_lock:

        job = analysis_jobs.get(
            job_id
        )

        if job is None:
            return None

        return dict(
            job
        )


# ============================================================
# ANALYSIS PROGRESS CALLBACK
# ============================================================

def analysis_progress_callback(

    job_id,

    progress,

    processed,

    total,

    stage

):

    try:

        update_analysis_job(

            job_id,

            progress=progress,

            processed=processed,

            total=total,

            stage=stage,

            status="processing"

        )

    except Exception as error:

        print(
            "Progress update warning:",
            repr(error)
        )


# ============================================================
# BACKGROUND BULK ANALYSIS
# ============================================================

def run_bulk_analysis(

    job_id,

    filepath,

    original_filename

):

    global current_transactions
    global current_stats

    try:

        print()
        print("=" * 70)
        print("AI FRAUD ANALYSIS STARTED")
        print("=" * 70)

        print(
            "Original file:",
            original_filename
        )

        print(
            "Analysis file:",
            filepath
        )

        print("=" * 70)


        # ----------------------------------------------------
        # START
        # ----------------------------------------------------

        update_analysis_job(

            job_id,

            progress=2,

            processed=0,

            total=0,

            stage=(
                "Starting AI fraud analysis..."
            ),

            status="processing"

        )


        # ----------------------------------------------------
        # LOCAL CALLBACK
        # ----------------------------------------------------

        def progress_callback(

            progress,

            processed,

            total,

            stage

        ):

            analysis_progress_callback(

                job_id,

                progress,

                processed,

                total,

                stage

            )


        # ----------------------------------------------------
        # RUN PREDICTION
        # ----------------------------------------------------

        result = predict_transaction(

            filepath,

            progress_callback=(
                progress_callback
            )

        )


        # ----------------------------------------------------
        # EXTRACT TRANSACTIONS
        # ----------------------------------------------------

        if isinstance(
            result,
            dict
        ):

            analyzed_transactions = (
                result.get(
                    "transactions",
                    []
                )
            )

        elif isinstance(
            result,
            list
        ):

            analyzed_transactions = (
                result
            )

        else:

            analyzed_transactions = []


        # ----------------------------------------------------
        # EMPTY RESULT
        # ----------------------------------------------------

        if not analyzed_transactions:

            raise ValueError(

                "AI analysis returned no "
                "transaction records. "
                "Check predict.py and "
                "the uploaded CSV."

            )


        processed_row_count = len(
            analyzed_transactions
        )


        # ----------------------------------------------------
        # FINAL STATISTICS
        # ----------------------------------------------------

        update_analysis_job(

            job_id,

            progress=96,

            processed=(
                processed_row_count
            ),

            total=(
                processed_row_count
            ),

            stage=(
                "Calculating final "
                "transaction statistics..."
            ),

            status="processing"

        )


        # ----------------------------------------------------
        # STORE RESULTS
        # ----------------------------------------------------

        current_transactions = list(
            analyzed_transactions
        )


        # ----------------------------------------------------
        # CALCULATE STATS
        # ----------------------------------------------------

        current_stats = (
            calculate_transaction_stats(
                current_transactions
            )
        )


        # ----------------------------------------------------
        # VERIFY COUNTS
        # ----------------------------------------------------

        verification_total = (

            current_stats["safe"]

            + current_stats["risky"]

            + current_stats["fraud"]

        )


        if (
            verification_total
            != processed_row_count
        ):

            raise ValueError(

                "Statistics mismatch. "

                f"Safe + Risky + Fraud = "
                f"{verification_total}, "

                f"but processed transactions = "
                f"{processed_row_count}."

            )


        # ----------------------------------------------------
        # COMPLETE
        # ----------------------------------------------------

        update_analysis_job(

            job_id,

            progress=100,

            processed=(
                processed_row_count
            ),

            total=(
                processed_row_count
            ),

            stage=(
                "Analysis completed successfully."
            ),

            status="completed"

        )


        print()
        print("=" * 70)
        print("AI FRAUD ANALYSIS COMPLETED")
        print("=" * 70)

        print(
            "Total processed:",
            processed_row_count
        )

        print(
            "Safe:",
            current_stats["safe"]
        )

        print(
            "Risky:",
            current_stats["risky"]
        )

        print(
            "Fraud:",
            current_stats["fraud"]
        )

        print("=" * 70)


    except Exception as error:

        print()
        print("=" * 70)
        print("UPLOAD / ANALYSIS ERROR")
        print("=" * 70)

        print(
            repr(error)
        )

        print("=" * 70)


        update_analysis_job(

            job_id,

            progress=100,

            stage=(
                "Analysis failed."
            ),

            status="error",

            error=str(error)

        )


# ============================================================
# OFFICIAL SAMPLE FILES
# ============================================================

OFFICIAL_SAMPLE_FILES = [

    "sample_banking_transactions_500.csv",

    "sample_bank_transfers_25000.csv",

    "sample_digital_wallet_30000.csv",

    "sample_mixed_transactions_50000.csv",

    "sample_online_payments_10000.csv"

]


# ============================================================
# GET SAMPLE FILES
# ============================================================

def get_sample_files():

    available_files = []

    if not os.path.isdir(
        SAMPLE_FOLDER
    ):

        return available_files


    for filename in (
        OFFICIAL_SAMPLE_FILES
    ):

        full_path = os.path.join(

            SAMPLE_FOLDER,

            filename

        )


        if os.path.isfile(
            full_path
        ):

            available_files.append(
                filename
            )


    return available_files


# ============================================================
# SAFE FLOAT
# ============================================================

def safe_float(

    value,

    default=None

):

    try:

        if value is None:

            return default


        text = str(
            value
        ).strip()


        if text == "":

            return default


        text = (
            text
            .replace(",", "")
            .replace("%", "")
            .replace("₹", "")
        )


        return float(
            text
        )


    except (
        ValueError,
        TypeError
    ):

        return default


# ============================================================
# FRAUD PROBABILITY
# ============================================================

def get_fraud_probability(

    transaction

):

    possible_keys = [

        "fraud_probability",

        "fraudProbability",

        "probability",

        "fraud_prob",

        "risk_probability",

        "riskProbability",

        "Fraud_Probability",

        "Fraud Probability",

        "fraud_probability_percent"

    ]


    for key in possible_keys:

        if key not in transaction:

            continue


        value = safe_float(

            transaction.get(
                key
            )

        )


        if value is None:

            continue


        if value > 1:

            value = (
                value / 100
            )


        return max(

            0,

            min(
                1,
                value
            )

        )


    return None


# ============================================================
# CLASSIFICATION
#
# IMPORTANT:
# Canonical prediction is checked first.
# This prevents:
#
# Fraud prediction
#      ->
# "Transaction Appears Safe"
#
# ============================================================

def classify_transaction(transaction):

    prediction = str(

        transaction.get(

            "prediction",

            transaction.get(
                "Prediction",
                ""
            )

        )

    ).strip().lower()


    risk_level = str(

        transaction.get(

            "risk_level",

            transaction.get(
                "RiskLevel",
                ""
            )

        )

    ).strip().lower()


    status = str(

        transaction.get(

            "status",

            transaction.get(
                "Status",
                ""
            )

        )

    ).strip().lower()


    classification = str(

        transaction.get(

            "classification",

            transaction.get(
                "Classification",
                ""
            )

        )

    ).strip().lower()


    result = str(

        transaction.get(

            "result",

            transaction.get(
                "Result",
                ""
            )

        )

    ).strip().lower()


    # --------------------------------------------------------
    # FRAUD
    # --------------------------------------------------------

    fraud_values = {

        "fraud",

        "fraudulent",

        "fraud detected",

        "high fraud risk",

        "high-risk fraud",

        "high risk fraud"

    }


    if prediction in fraud_values:

        return "fraud"


    if risk_level in fraud_values:

        return "fraud"


    if classification in fraud_values:

        return "fraud"


    if "fraud" in prediction:

        return "fraud"


    if "fraud" in risk_level:

        return "fraud"


    if "fraud" in classification:

        return "fraud"


    if "fraud detected" in status:

        return "fraud"


    if "fraudulent" in status:

        return "fraud"


    # --------------------------------------------------------
    # RISKY
    # --------------------------------------------------------

    risky_values = {

        "risky",

        "risk",

        "medium",

        "moderate",

        "medium risk",

        "moderate risk",

        "suspicious",

        "warning",

        "requires attention"

    }


    if prediction in risky_values:

        return "risky"


    if risk_level in risky_values:

        return "risky"


    if classification in risky_values:

        return "risky"


    if status in {

        "requires attention",

        "warning",

        "suspicious",

        "risky"

    }:

        return "risky"


    if result in risky_values:

        return "risky"


    # --------------------------------------------------------
    # SAFE
    # --------------------------------------------------------

    safe_values = {

        "safe",

        "legitimate",

        "normal",

        "safe transaction",

        "legitimate transaction",

        "transaction appears safe",

        "low risk",

        "low-risk",

        "low"

    }


    if prediction in safe_values:

        return "safe"


    if risk_level in safe_values:

        return "safe"


    if classification in safe_values:

        return "safe"


    if status in {

        "legitimate",

        "safe",

        "transaction appears safe"

    }:

        return "safe"


    if result in safe_values:

        return "safe"


    # --------------------------------------------------------
    # NUMERIC PREDICTION
    # --------------------------------------------------------

    numeric_prediction = safe_float(
        prediction
    )


    if numeric_prediction is not None:

        if numeric_prediction == 1:

            return "fraud"


        if numeric_prediction == 0:

            return "safe"


    # --------------------------------------------------------
    # PROBABILITY FALLBACK
    # --------------------------------------------------------

    probability = (
        get_fraud_probability(
            transaction
        )
    )


    if probability is not None:

        if probability >= 0.70:

            return "fraud"


        if probability >= 0.40:

            return "risky"


        return "safe"


    # --------------------------------------------------------
    # TEXT FALLBACK
    # --------------------------------------------------------

    combined = " ".join([

        prediction,

        risk_level,

        status,

        result,

        classification

    ])


    if "fraud" in combined:

        return "fraud"


    if any(

        word in combined

        for word in [

            "risky",

            "suspicious",

            "warning",

            "attention",

            "moderate",

            "medium risk",

            "high risk"

        ]

    ):

        return "risky"


    if any(

        word in combined

        for word in [

            "safe",

            "legitimate",

            "normal",

            "low risk",

            "low-risk"

        ]

    ):

        return "safe"


    # --------------------------------------------------------
    # FINAL SAFE FALLBACK
    # --------------------------------------------------------

    return "safe"


# ============================================================
# STATISTICS
# ============================================================

def calculate_transaction_stats(

    transaction_list

):

    stats = {

        "total":
            len(transaction_list),

        "safe":
            0,

        "risky":
            0,

        "fraud":
            0

    }


    for transaction in (
        transaction_list
    ):

        category = (
            classify_transaction(
                transaction
            )
        )


        if category == "fraud":

            stats["fraud"] += 1


        elif category == "risky":

            stats["risky"] += 1


        else:

            stats["safe"] += 1


    return stats


# ============================================================
# DATABASE
# ============================================================

initialize_database()


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# ============================================================
# REGISTER
# ============================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()


        email = (

            request.form.get(
                "email",
                ""
            )
            .strip()
            .lower()

        )


        password = request.form.get(
            "password",
            ""
        )


        if (

            not username

            or not email

            or not password

        ):

            flash(
                "Please fill in all fields."
            )

            return redirect(
                url_for("register")
            )


        hashed_password = (
            generate_password_hash(
                password
            )
        )


        connection = (
            get_connection()
        )

        cursor = (
            connection.cursor()
        )


        try:

            cursor.execute(

                """

                INSERT INTO users
                (username, email, password)

                VALUES (?, ?, ?)

                """,

                (
                    username,
                    email,
                    hashed_password
                )

            )


            connection.commit()


            flash(
                "Registration successful. "
                "Please login."
            )


            return redirect(
                url_for("login")
            )


        except Exception as error:

            print(
                "Registration Error:",
                error
            )


            flash(
                f"Registration Error: {error}"
            )


        finally:

            connection.close()


    return render_template(
        "register.html"
    )


# ============================================================
# LOGIN
# ============================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        email = (

            request.form.get(
                "email",
                ""
            )
            .strip()
            .lower()

        )


        password = request.form.get(
            "password",
            ""
        )


        connection = (
            get_connection()
        )

        cursor = (
            connection.cursor()
        )


        cursor.execute(

            """

            SELECT *
            FROM users
            WHERE LOWER(email) = ?

            """,

            (
                email,
            )

        )


        user = cursor.fetchone()


        connection.close()


        if (

            user

            and check_password_hash(

                user["password"],

                password

            )

        ):

            session["user_id"] = (
                user["id"]
            )

            session["username"] = (
                user["username"]
            )


            return redirect(
                url_for("dashboard")
            )


        flash(
            "Invalid email or password."
        )


    return render_template(
        "login.html"
    )


# ============================================================
# FORGOT PASSWORD
# ============================================================

@app.route(
    "/forgot-password",
    methods=["GET", "POST"]
)
def forgot_password():

    if request.method == "POST":

        email = (

            request.form.get(
                "email",
                ""
            )
            .strip()
            .lower()

        )


        if not email:

            flash(
                "Please enter your registered "
                "email address."
            )


            return redirect(
                url_for(
                    "forgot_password"
                )
            )


        connection = (
            get_connection()
        )

        cursor = (
            connection.cursor()
        )


        cursor.execute(

            """

            SELECT id, email
            FROM users
            WHERE LOWER(email) = ?

            """,

            (
                email,
            )

        )


        user = cursor.fetchone()


        connection.close()


        if user is None:

            flash(

                "This email has not been registered. "
                "Please use your registered email address."

            )


            return redirect(

                url_for(
                    "forgot_password"
                )

            )


        session["reset_email"] = (
            email
        )


        return redirect(

            url_for(
                "reset_password"
            )

        )


    return render_template(
        "forgot_password.html"
    )


# ============================================================
# RESET PASSWORD
# ============================================================

@app.route(
    "/reset-password",
    methods=["GET", "POST"]
)
def reset_password():

    if "reset_email" not in session:

        return redirect(
            url_for("forgot_password")
        )


    if request.method == "POST":

        new_password = request.form.get(
            "password",
            ""
        )


        confirm_password = (
            request.form.get(
                "confirm_password",
                ""
            )
        )


        if (

            not new_password

            or not confirm_password

        ):

            flash(
                "Please fill in both password fields."
            )


            return redirect(
                url_for("reset_password")
            )


        if new_password != confirm_password:

            flash(
                "Passwords do not match."
            )


            return redirect(
                url_for("reset_password")
            )


        if len(new_password) < 6:

            flash(
                "Password must contain at least "
                "6 characters."
            )


            return redirect(
                url_for("reset_password")
            )


        hashed_password = (
            generate_password_hash(
                new_password
            )
        )


        connection = (
            get_connection()
        )

        cursor = (
            connection.cursor()
        )


        try:

            cursor.execute(

                """

                UPDATE users
                SET password = ?
                WHERE LOWER(email) = ?

                """,

                (

                    hashed_password,

                    session[
                        "reset_email"
                    ].lower()

                )

            )


            connection.commit()


        finally:

            connection.close()


        session.pop(
            "reset_email",
            None
        )


        flash(
            "Password reset successful. "
            "Please login."
        )


        return redirect(
            url_for("login")
        )


    return render_template(
        "reset_password.html"
    )


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    dashboard_transactions = list(
        current_transactions
    ) if current_transactions else []


    # --------------------------------------------------------
    # FALLBACK RECENT TRANSACTIONS
    # --------------------------------------------------------

    if not dashboard_transactions:

        dashboard_transactions = [

            {
                "display_id": "TXN-10001",
                "display_customer": "Customer 1001",
                "display_amount": 1250.00,
                "display_merchant": "Amazon",
                "display_type": "Purchase",
                "display_classification": "safe"
            },

            {
                "display_id": "TXN-10002",
                "display_customer": "Customer 1002",
                "display_amount": 8500.00,
                "display_merchant": "Flipkart",
                "display_type": "Purchase",
                "display_classification": "safe"
            },

            {
                "display_id": "TXN-10003",
                "display_customer": "Customer 1003",
                "display_amount": 45000.00,
                "display_merchant": "Electronics Store",
                "display_type": "Purchase",
                "display_classification": "risky"
            },

            {
                "display_id": "TXN-10004",
                "display_customer": "Customer 1004",
                "display_amount": 3200.00,
                "display_merchant": "Walmart",
                "display_type": "Purchase",
                "display_classification": "safe"
            },

            {
                "display_id": "TXN-10005",
                "display_customer": "Customer 1005",
                "display_amount": 75000.00,
                "display_merchant": "Online Transfer",
                "display_type": "Transfer",
                "display_classification": "fraud"
            },

            {
                "display_id": "TXN-10006",
                "display_customer": "Customer 1006",
                "display_amount": 1800.00,
                "display_merchant": "Grocery Store",
                "display_type": "Purchase",
                "display_classification": "safe"
            },

            {
                "display_id": "TXN-10007",
                "display_customer": "Customer 1007",
                "display_amount": 12500.00,
                "display_merchant": "Travel Booking",
                "display_type": "Purchase",
                "display_classification": "risky"
            },

            {
                "display_id": "TXN-10008",
                "display_customer": "Customer 1008",
                "display_amount": 950.00,
                "display_merchant": "Restaurant",
                "display_type": "Purchase",
                "display_classification": "safe"
            },

            {
                "display_id": "TXN-10009",
                "display_customer": "Customer 1009",
                "display_amount": 56000.00,
                "display_merchant": "International Transfer",
                "display_type": "Transfer",
                "display_classification": "fraud"
            },

            {
                "display_id": "TXN-10010",
                "display_customer": "Customer 1010",
                "display_amount": 2400.00,
                "display_merchant": "Supermarket",
                "display_type": "Purchase",
                "display_classification": "safe"
            }

        ]


    if current_transactions:

        stats = (
            calculate_transaction_stats(
                current_transactions
            )
        )

    else:

        stats = (
            calculate_transaction_stats(
                dashboard_transactions
            )
        )


    return render_template(

        "dashboard.html",

        username=session.get(
            "username",
            "User"
        ),

        transactions=(
            dashboard_transactions[-10:]
        ),

        total=stats["total"],

        safe=stats["safe"],

        risky=stats["risky"],

        fraud=stats["fraud"],

        has_analysis=bool(
            current_transactions
        )

    )


# ============================================================
# BULK ANALYSIS PAGE
# ============================================================

@app.route("/bulk-analysis")
def bulk_analysis():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    stats = (
        calculate_transaction_stats(
            current_transactions
        )
    )


    return render_template(

        "bulk_analysis.html",

        username=session.get(
            "username",
            "User"
        ),

        transactions=current_transactions,

        total=stats["total"],

        safe=stats["safe"],

        risky=stats["risky"],

        fraud=stats["fraud"],

        sample_files=(
            get_sample_files()
        )

    )


# ============================================================
# SAVE UPLOADED CSV
# ============================================================

def save_uploaded_csv(

    file,

    filename

):

    """
    LOCAL:
        Saves CSV to uploads/.

    VERCEL:
        Uploads CSV to Vercel Blob.
    """

    # --------------------------------------------------------
    # VERCEL BLOB
    # --------------------------------------------------------

    if os.environ.get("VERCEL"):

        token = os.environ.get(
            "BLOB_READ_WRITE_TOKEN"
        )


        if not token:

            raise RuntimeError(

                "BLOB_READ_WRITE_TOKEN is not "
                "configured in the Vercel environment."

            )


        file_data = file.read()


        if not file_data:

            raise ValueError(
                "Uploaded CSV file is empty."
            )


        blob_path = (

            "fraud-analysis/"

            f"{uuid.uuid4().hex}_"

            f"{filename}"

        )


        blob = put(

            blob_path,

            file_data,

            access="private",

            content_type="text/csv",

            token=token

        )


        print()
        print("=" * 70)
        print("VERCEL BLOB UPLOAD SUCCESS")
        print("=" * 70)

        print(
            "Blob pathname:",
            blob.pathname
        )

        print(
            "Blob URL:",
            blob.url
        )

        print("=" * 70)


        return blob.url


    # --------------------------------------------------------
    # LOCAL DEVELOPMENT
    # --------------------------------------------------------

    filepath = os.path.join(

        UPLOAD_FOLDER,

        filename

    )


    counter = 1


    base_name = os.path.splitext(
        filename
    )[0]


    extension = os.path.splitext(
        filename
    )[1]


    while os.path.exists(
        filepath
    ):

        filename = (

            f"{base_name}_"

            f"{counter}"

            f"{extension}"

        )


        filepath = os.path.join(

            UPLOAD_FOLDER,

            filename

        )


        counter += 1


    file.save(
        filepath
    )


    return filepath


# ============================================================
# PREPARE ANALYSIS FILE
# ============================================================

def prepare_analysis_file(

    storage_location,

    original_filename

):

    """
    LOCAL:
        Returns local CSV path.

    VERCEL:
        Downloads private Blob URL into /tmp.
    """

    # --------------------------------------------------------
    # LOCAL
    # --------------------------------------------------------

    if not os.environ.get("VERCEL"):

        return storage_location


    # --------------------------------------------------------
    # VERCEL
    # --------------------------------------------------------

    import requests


    temp_dir = "/tmp"


    temp_filename = (

        f"fraud_analysis_"

        f"{uuid.uuid4().hex}_"

        f"{secure_filename(original_filename)}"

    )


    temp_filepath = os.path.join(

        temp_dir,

        temp_filename

    )


    response = requests.get(

        storage_location,

        timeout=120

    )


    response.raise_for_status()


    with open(

        temp_filepath,

        "wb"

    ) as output_file:

        output_file.write(
            response.content
        )


    if not os.path.isfile(
        temp_filepath
    ):

        raise RuntimeError(

            "Unable to prepare Blob file "
            "for analysis."

        )


    print(
        "Temporary analysis file:",
        temp_filepath
    )


    return temp_filepath


# ============================================================
# UPLOAD CSV
#
# IMPORTANT:
# This route now uses save_uploaded_csv()
# instead of directly writing to UPLOAD_FOLDER.
#
# Therefore:
#
# LOCAL  -> uploads/
# VERCEL -> Vercel Blob
# ============================================================

@app.route(
    "/upload",
    methods=["POST"]
)
def upload():

    if "user_id" not in session:

        return jsonify({

            "success":
                False,

            "error":
                "Please login first."

        }), 401


    file = request.files.get(
        "file"
    )


    if (

        not file

        or file.filename == ""

    ):

        return jsonify({

            "success":
                False,

            "error":
                "Please select a CSV file."

        }), 400


    original_filename = (
        file.filename
    )


    if not original_filename.lower().endswith(
        ".csv"
    ):

        return jsonify({

            "success":
                False,

            "error":
                "Only CSV files are supported."

        }), 400


    filename = secure_filename(
        original_filename
    )


    if not filename:

        return jsonify({

            "success":
                False,

            "error":
                "Invalid file name."

        }), 400


    try:

        # ----------------------------------------------------
        # SAVE FILE
        #
        # LOCAL:
        #   returns local path
        #
        # VERCEL:
        #   returns Blob URL
        # ----------------------------------------------------

        storage_location = (
            save_uploaded_csv(
                file,
                filename
            )
        )


        # ----------------------------------------------------
        # PREPARE FILE FOR PREDICTION
        #
        # LOCAL:
        #   same local path
        #
        # VERCEL:
        #   downloads Blob to /tmp
        # ----------------------------------------------------

        analysis_filepath = (
            prepare_analysis_file(

                storage_location,

                original_filename

            )
        )


    except Exception as error:

        print(
            "Upload storage error:",
            repr(error)
        )


        return jsonify({

            "success":
                False,

            "error":
                (
                    "Unable to save uploaded CSV: "
                    f"{error}"
                )

        }), 500


    # --------------------------------------------------------
    # CREATE JOB
    # --------------------------------------------------------

    job_id = (
        create_analysis_job()
    )


    # --------------------------------------------------------
    # BACKGROUND WORKER
    # --------------------------------------------------------

    worker = threading.Thread(

        target=run_bulk_analysis,

        args=(

            job_id,

            analysis_filepath,

            original_filename

        ),

        daemon=True

    )


    worker.start()


    # --------------------------------------------------------
    # RETURN IMMEDIATELY
    # --------------------------------------------------------

    return jsonify({

        "success":
            True,

        "job_id":
            job_id,

        "message":
            "AI fraud analysis started."

    })


# ============================================================
# ANALYSIS STATUS
# ============================================================

@app.route(
    "/analysis-status/<job_id>"
)
def analysis_status(
    job_id
):

    if "user_id" not in session:

        return jsonify({

            "success":
                False,

            "error":
                "Please login first."

        }), 401


    job = get_analysis_job(
        job_id
    )


    if job is None:

        return jsonify({

            "success":
                False,

            "error":
                "Analysis job not found."

        }), 404


    return jsonify({

        "success":
            True,

        **job

    })


# ============================================================
# DOWNLOAD SAMPLE CSV
# ============================================================

@app.route(
    "/download-sample/<path:filename>"
)
def download_sample(
    filename
):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    filename = os.path.basename(
        filename
    )


    if filename not in (
        OFFICIAL_SAMPLE_FILES
    ):

        flash(
            "Invalid sample file."
        )


        return redirect(
            url_for("bulk_analysis")
        )


    full_path = os.path.join(

        SAMPLE_FOLDER,

        filename

    )


    if not os.path.isfile(
        full_path
    ):

        flash(
            "Sample file not found."
        )


        return redirect(
            url_for("bulk_analysis")
        )


    return send_from_directory(

        SAMPLE_FOLDER,

        filename,

        as_attachment=True

    )


# ============================================================
# ANALYTICS
# ============================================================

@app.route("/analytics")
def analytics():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    transactions = (
        current_transactions
    )


    stats = (
        calculate_transaction_stats(
            transactions
        )
    )


    total = stats["total"]

    safe_count = stats["safe"]

    risky_count = stats["risky"]

    fraud_count = stats["fraud"]


    if total > 0:

        fraud_percentage = round(

            (
                fraud_count
                / total
            ) * 100,

            1

        )

    else:

        fraud_percentage = 0


    high_value_transactions = []


    for transaction in (
        transactions
    ):

        amount = safe_float(

            transaction.get(

                "amount",

                transaction.get(

                    "Amount",

                    transaction.get(

                        "Amount_INR",

                        0

                    )

                )

            ),

            0

        )


        if (

            amount is not None

            and amount >= 50000

        ):

            high_value_transactions.append(
                transaction
            )


    return render_template(

        "analytics.html",

        username=session.get(
            "username",
            "User"
        ),

        transactions=transactions,

        total=total,

        fraud=fraud_count,

        safe=safe_count,

        risky=risky_count,

        fraud_percentage=(
            fraud_percentage
        ),

        high_value=(
            high_value_transactions
        )

    )


# ============================================================
# LIVE PREDICTION
# ============================================================

@app.route(
    "/live-prediction",
    methods=["GET", "POST"]
)
def live_prediction():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    prediction = None

    confidence = None


    if request.method == "POST":

        try:

            amount = float(

                request.form.get(

                    "amount",

                    0

                )

            )


            if amount <= 0:

                flash(
                    "Please enter a valid "
                    "transaction amount."
                )


            elif amount > 100000:

                prediction = (
                    "High Fraud Risk"
                )

                confidence = "96%"


            elif amount > 50000:

                prediction = (
                    "Risky Transaction"
                )

                confidence = "82%"


            else:

                prediction = (
                    "Safe Transaction"
                )

                confidence = "94%"


        except (

            ValueError,

            TypeError

        ):

            flash(
                "Please enter a valid "
                "transaction amount."
            )


    return render_template(

        "live_prediction.html",

        username=session.get(
            "username",
            "User"
        ),

        prediction=prediction,

        confidence=confidence

    )


# ============================================================
# TRANSACTION DETAILS
# ============================================================

@app.route(
    "/transaction/<transaction_id>"
)
def transaction_details(
    transaction_id
):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    transaction = None


    for item in (
        current_transactions
    ):

        item_id = (

            item.get("id")

            or item.get(
                "transaction_id"
            )

            or item.get(
                "TransactionID"
            )

            or item.get(
                "Transaction_ID"
            )

            or item.get(
                "Transaction Id"
            )

        )


        if str(item_id) == str(
            transaction_id
        ):

            transaction = dict(
                item
            )


            def get_value(

                *keys,

                default="-"

            ):

                for key in keys:

                    value = (
                        transaction.get(
                            key
                        )
                    )


                    if (

                        value is not None

                        and str(
                            value
                        ).strip()

                        not in [

                            "",

                            "nan",

                            "None"

                        ]

                    ):

                        return value


                return default


            transaction[
                "transaction_id"
            ] = get_value(

                "transaction_id",

                "TransactionID",

                "Transaction_ID",

                "Transaction Id",

                "id"

            )


            transaction[
                "amount"
            ] = get_value(

                "amount",

                "Amount",

                "TransactionAmount",

                "Transaction_Amount",

                default=0

            )


            transaction[
                "customer_name"
            ] = get_value(

                "customer_name",

                "CustomerName",

                "Customer_Name",

                "Customer",

                "customer"

            )


            transaction[
                "account_number"
            ] = get_value(

                "account_number",

                "AccountNumber",

                "Account_Number",

                "Account No"

            )


            transaction[
                "bank_name"
            ] = get_value(

                "bank_name",

                "BankName",

                "Bank_Name",

                "Bank"

            )


            transaction[
                "account_type"
            ] = get_value(

                "account_type",

                "AccountType",

                "Account_Type"

            )


            transaction[
                "payment_method"
            ] = get_value(

                "payment_method",

                "PaymentMethod",

                "Payment_Method"

            )


            transaction[
                "app_channel"
            ] = get_value(

                "app_channel",

                "AppChannel",

                "App_Channel",

                "Channel",

                "channel"

            )


            transaction[
                "merchant"
            ] = get_value(

                "merchant",

                "Merchant",

                "MerchantName",

                "Merchant_Name"

            )


            transaction[
                "type"
            ] = get_value(

                "type",

                "TransactionType",

                "Transaction_Type"

            )


            transaction[
                "location"
            ] = get_value(

                "location",

                "Location",

                "City",

                "city"

            )


            transaction[
                "device_type"
            ] = get_value(

                "device_type",

                "DeviceType",

                "Device_Type",

                "Device"

            )


            transaction[
                "ip_address"
            ] = get_value(

                "ip_address",

                "IPAddress",

                "IP_Address",

                "IP"

            )


            transaction[
                "time"
            ] = get_value(

                "time",

                "DateTime",

                "Date_Time",

                "Timestamp",

                "TransactionDate"

            )


            transaction[
                "previous_amount"
            ] = get_value(

                "previous_amount",

                "PreviousAmount",

                "Previous_Amount"

            )


            transaction[
                "transactions_last_24h"
            ] = get_value(

                "transactions_last_24h",

                "TransactionsLast24Hours",

                "Transactions_Last_24h"

            )


            transaction[
                "unusual_location"
            ] = get_value(

                "unusual_location",

                "UnusualLocation",

                "Unusual_Location"

            )


            break


    # --------------------------------------------------------
    # NOT FOUND
    # --------------------------------------------------------

    if transaction is None:

        flash(
            "Transaction not found."
        )


        return redirect(
            url_for("bulk_analysis")
        )


    return render_template(

        "transaction_details.html",

        username=session.get(
            "username",
            "User"
        ),

        transaction=transaction

    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("home")
    )


# ============================================================
# START APPLICATION
# ============================================================

if __name__ == "__main__":

    print()

    print("=" * 70)

    print(
        "AI FRAUD DETECTION SYSTEM"
    )

    print("=" * 70)


    print(
        "Project directory:",
        BASE_DIR
    )


    print(
        "Sample directory:",
        SAMPLE_FOLDER
    )


    detected_samples = (
        get_sample_files()
    )


    print(
        "Detected official sample CSV files:",
        detected_samples
    )


    print(
        "Number of official sample files:",
        len(detected_samples)
    )


    print(
        "Flask server starting..."
    )


    print(
        "Open: http://127.0.0.1:5000"
    )


    print("=" * 70)


    app.run(

        debug=True,

        use_reloader=False,

        threaded=True

    )