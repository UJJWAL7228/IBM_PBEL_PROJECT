import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
REPORT_FOLDER = os.path.join(BASE_DIR, "reports")
MODEL_FOLDER = os.path.join(BASE_DIR, "models")

SECRET_KEY = "ibm_pbel_fraud_detection_secret"

MAX_CONTENT_LENGTH = 16 * 1024 * 1024
# Gmail OTP Settings
MAIL_SERVER = "smtp.gmail.com"
MAIL_PORT = 587
MAIL_USERNAME = "ujjwalkumarujjain7228@gmail.com"
MAIL_PASSWORD = "tfrs rpbu slfa zmku"