import os
import hashlib

import joblib
import pandas as pd


# ============================================================
# PROJECT DIRECTORY
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)


# ============================================================
# MODEL PATHS
# ============================================================

MODEL_PATH = os.path.join(
    BASE_DIR,
    "models",
    "fraud_model.pkl"
)

SCALER_PATH = os.path.join(
    BASE_DIR,
    "models",
    "scaler.pkl"
)

FEATURE_PATH = os.path.join(
    BASE_DIR,
    "models",
    "feature_columns.pkl"
)


# ============================================================
# LOAD MODEL
# ============================================================

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(
        f"Model not found: {MODEL_PATH}"
    )

if not os.path.exists(SCALER_PATH):
    raise FileNotFoundError(
        f"Scaler not found: {SCALER_PATH}"
    )

if not os.path.exists(FEATURE_PATH):
    raise FileNotFoundError(
        f"Feature columns not found: {FEATURE_PATH}"
    )


model = joblib.load(MODEL_PATH)
scaler = joblib.load(SCALER_PATH)
feature_columns = joblib.load(FEATURE_PATH)


print()
print("=" * 70)
print("PREDICTION MODEL LOADED")
print("=" * 70)

print("Model:", MODEL_PATH)
print("Scaler:", SCALER_PATH)
print("Feature file:", FEATURE_PATH)
print("Number of model features:", len(feature_columns))
print("Features:", feature_columns)

print("=" * 70)


# ============================================================
# EXPECTED FEATURES
# ============================================================

EXPECTED_FEATURES = [
    "Time",

    "V1",
    "V2",
    "V3",
    "V4",
    "V5",
    "V6",
    "V7",
    "V8",
    "V9",
    "V10",
    "V11",
    "V12",
    "V13",
    "V14",
    "V15",
    "V16",
    "V17",
    "V18",
    "V19",
    "V20",
    "V21",
    "V22",
    "V23",
    "V24",
    "V25",
    "V26",
    "V27",
    "V28",

    "Amount"
]


# ============================================================
# CHECK MODEL STRUCTURE
# ============================================================

if list(feature_columns) != EXPECTED_FEATURES:

    print()
    print("WARNING:")
    print(
        "The saved feature_columns.pkl does not exactly "
        "match the expected Credit Card Fraud feature order."
    )

    print("Saved features:", feature_columns)
    print()


# ============================================================
# FIND COLUMN
# ============================================================

def find_column(df, possible_names):

    lookup = {
        str(column).strip().lower(): column
        for column in df.columns
    }

    for name in possible_names:

        key = str(name).strip().lower()

        if key in lookup:
            return lookup[key]

    return None


# ============================================================
# NUMERIC VALUE
# ============================================================

def numeric_value(value, default=0.0):

    try:

        if pd.isna(value):
            return default

        text = str(value).strip()

        if not text:
            return default

        text = text.replace(",", "")
        text = text.replace("₹", "")
        text = text.replace("$", "")

        return float(text)

    except (
        ValueError,
        TypeError
    ):

        return default


# ============================================================
# DETERMINISTIC TEXT NUMBER
# ============================================================

def text_to_number(value):

    text = str(value).strip().lower()

    if not text:
        return 0.0

    digest = hashlib.md5(
        text.encode("utf-8")
    ).hexdigest()

    integer_value = int(
        digest[:12],
        16
    )

    return (
        (integer_value % 2000000)
        / 1000000.0
    ) - 1.0


# ============================================================
# CREATE MODEL INPUT
# ============================================================

def create_model_input(df):

    """
    Creates ONLY the features required by the trained model.

    IMPORTANT:
    The original CSV dataframe is never modified or discarded.
    """

    model_df = pd.DataFrame(
        index=df.index
    )

    # --------------------------------------------------------
    # IMPORTANT COLUMNS
    # --------------------------------------------------------

    time_column = find_column(
        df,
        [
            "Time",
            "Timestamp",
            "Date",
            "Datetime",
            "DateTime"
        ]
    )

    amount_column = find_column(
        df,
        [
            "Amount",
            "Amount_INR",
            "Transaction_Amount",
            "Transaction Amount",
            "amount",
            "value"
        ]
    )

    if amount_column is None:

        raise ValueError(
            "CSV must contain an Amount or Amount_INR column."
        )

    customer_column = find_column(
        df,
        [
            "Customer",
            "Customer_Name",
            "CustomerName",
            "Customer Name",
            "Name",
            "Customer ID",
            "Customer_ID"
        ]
    )

    merchant_column = find_column(
        df,
        [
            "Merchant",
            "Merchant_Name",
            "MerchantName",
            "Merchant Name",
            "App"
        ]
    )

    type_column = find_column(
        df,
        [
            "Type",
            "TransactionType",
            "Transaction_Type",
            "Transaction Type"
        ]
    )

    location_column = find_column(
        df,
        [
            "Location",
            "City",
            "Country"
        ]
    )

    channel_column = find_column(
        df,
        [
            "Channel",
            "AppChannel",
            "App_Channel",
            "Payment_Method",
            "Payment Method"
        ]
    )

    # --------------------------------------------------------
    # TIME
    # --------------------------------------------------------

    if time_column is not None:

        time_series = df[time_column]

        numeric_time = pd.to_numeric(
            time_series,
            errors="coerce"
        )

        if numeric_time.notna().all():

            model_df["Time"] = numeric_time

        else:

            parsed_time = pd.to_datetime(
                time_series,
                errors="coerce"
            )

            if parsed_time.notna().sum() > 0:

                first_time = (
                    parsed_time
                    .dropna()
                    .iloc[0]
                )

                seconds = (
                    parsed_time - first_time
                ).dt.total_seconds()

                model_df["Time"] = (
                    seconds.fillna(0)
                )

            else:

                model_df["Time"] = range(
                    len(df)
                )

    else:

        model_df["Time"] = range(
            len(df)
        )

    # --------------------------------------------------------
    # AMOUNT
    # --------------------------------------------------------

    amount = pd.to_numeric(
        df[amount_column],
        errors="coerce"
    ).fillna(0)

    model_df["Amount"] = amount

    # --------------------------------------------------------
    # NORMALIZED AMOUNT
    # --------------------------------------------------------

    amount_mean = amount.mean()
    amount_std = amount.std()

    if (
        pd.isna(amount_std)
        or amount_std == 0
    ):

        amount_std = 1.0

    amount_normalized = (
        (amount - amount_mean)
        / amount_std
    )

    amount_normalized = (
        amount_normalized
        .replace(
            [
                float("inf"),
                float("-inf")
            ],
            0
        )
        .fillna(0)
    )

    # --------------------------------------------------------
    # REAL V1-V28
    # --------------------------------------------------------

    real_v_columns = {}

    for number in range(1, 29):

        feature_name = f"V{number}"

        actual_column = find_column(
            df,
            [feature_name]
        )

        if actual_column is not None:

            model_df[feature_name] = (
                pd.to_numeric(
                    df[actual_column],
                    errors="coerce"
                ).fillna(0)
            )

            real_v_columns[feature_name] = True

        else:

            real_v_columns[feature_name] = False

    # --------------------------------------------------------
    # BANKING SIGNATURE
    # --------------------------------------------------------

    signature_parts = []

    signature_parts.append(
        amount.astype(str)
    )

    if customer_column is not None:

        signature_parts.append(
            df[customer_column]
            .fillna("")
            .astype(str)
        )

    if merchant_column is not None:

        signature_parts.append(
            df[merchant_column]
            .fillna("")
            .astype(str)
        )

    if type_column is not None:

        signature_parts.append(
            df[type_column]
            .fillna("")
            .astype(str)
        )

    if location_column is not None:

        signature_parts.append(
            df[location_column]
            .fillna("")
            .astype(str)
        )

    if channel_column is not None:

        signature_parts.append(
            df[channel_column]
            .fillna("")
            .astype(str)
        )

    base_signature = signature_parts[0]

    for part in signature_parts[1:]:

        base_signature = (
            base_signature
            + "|"
            + part
        )

    # --------------------------------------------------------
    # GENERATE MISSING V FEATURES
    # --------------------------------------------------------

    for number in range(1, 29):

        feature_name = f"V{number}"

        if real_v_columns[feature_name]:
            continue

        feature_signature = (
            base_signature
            + "|"
            + str(number)
        )

        hashed_values = (
            feature_signature.map(
                text_to_number
            )
        )

        model_df[feature_name] = (
            hashed_values * 0.7
            + amount_normalized * 0.3
        )

    # --------------------------------------------------------
    # CHECK REQUIRED FEATURES
    # --------------------------------------------------------

    missing_features = [
        feature
        for feature in feature_columns
        if feature not in model_df.columns
    ]

    if missing_features:

        raise ValueError(
            "Unable to create required model features: "
            + ", ".join(missing_features)
        )

    # --------------------------------------------------------
    # EXACT MODEL FEATURE ORDER
    # --------------------------------------------------------

    model_df = model_df[
        feature_columns
    ].copy()

    # --------------------------------------------------------
    # CLEAN MODEL INPUT
    # --------------------------------------------------------

    for column in feature_columns:

        model_df[column] = pd.to_numeric(
            model_df[column],
            errors="coerce"
        )

    model_df = model_df.fillna(0)

    return model_df


# ============================================================
# MAIN PREDICTION FUNCTION
# ============================================================

def predict_transaction(filepath):

    print()
    print("=" * 70)
    print("PREDICT TRANSACTION")
    print("=" * 70)

    if not os.path.exists(filepath):

        raise FileNotFoundError(
            f"CSV file not found: {filepath}"
        )

    # --------------------------------------------------------
    # READ CSV
    # --------------------------------------------------------

    print("Input CSV:", filepath)

    df = pd.read_csv(filepath)

    if df.empty:

        raise ValueError(
            "CSV file is empty."
        )

    original_row_count = len(df)

    original_columns = list(df.columns)

    print(
        "CSV rows:",
        original_row_count
    )

    print(
        "CSV columns:",
        len(original_columns)
    )

    print(
        "Original columns:",
        original_columns
    )

    # --------------------------------------------------------
    # CREATE MODEL INPUT
    # --------------------------------------------------------

    print()
    print("Preparing AI model features...")

    model_input = create_model_input(df)

    print(
        "Model input shape:",
        model_input.shape
    )

    if len(model_input) != original_row_count:

        raise ValueError(
            "Model input row count mismatch."
        )

    # --------------------------------------------------------
    # SCALE AMOUNT
    # --------------------------------------------------------

    print()
    print("Scaling Amount...")

    model_input["Amount"] = scaler.transform(
        model_input[["Amount"]]
    ).ravel()

    # --------------------------------------------------------
    # VERIFY FEATURES
    # --------------------------------------------------------

    if list(model_input.columns) != list(
        feature_columns
    ):

        raise ValueError(
            "Model feature order mismatch."
        )

    print(
        "Feature verification: PASSED"
    )

    # --------------------------------------------------------
    # MODEL PREDICTION
    # --------------------------------------------------------

    print()
    print("Running Random Forest prediction...")

    predictions = model.predict(
        model_input
    )

    # --------------------------------------------------------
    # PROBABILITIES
    # --------------------------------------------------------

    probabilities = None

    if hasattr(model, "predict_proba"):

        probabilities = model.predict_proba(
            model_input
        )

    # --------------------------------------------------------
    # FIND FRAUD CLASS
    # --------------------------------------------------------

    fraud_class_index = None

    if probabilities is not None:

        classes = list(
            model.classes_
        )

        possible_fraud_classes = [
            1,
            "1",
            True,
            "Fraud",
            "fraud"
        ]

        for possible_class in possible_fraud_classes:

            if possible_class in classes:

                fraud_class_index = (
                    classes.index(
                        possible_class
                    )
                )

                break

        if fraud_class_index is None:

            fraud_class_index = (
                len(classes) - 1
            )

    # --------------------------------------------------------
    # AMOUNT COLUMN
    # --------------------------------------------------------

    amount_column = find_column(
        df,
        [
            "Amount",
            "Amount_INR",
            "Transaction_Amount",
            "Transaction Amount",
            "amount",
            "value"
        ]
    )

    original_amount = pd.to_numeric(
        df[amount_column],
        errors="coerce"
    ).fillna(0)

    # --------------------------------------------------------
    # HIGH VALUE THRESHOLD
    # --------------------------------------------------------

    if len(original_amount) >= 10:

        high_value_threshold = float(
            original_amount.quantile(0.90)
        )

    else:

        high_value_threshold = 50000.0

    if high_value_threshold <= 0:

        high_value_threshold = 50000.0

    # --------------------------------------------------------
    # FIND STANDARD COLUMNS
    # --------------------------------------------------------

    id_column = find_column(
        df,
        [
            "TransactionID",
            "Transaction_ID",
            "Transaction Id",
            "Transaction ID",
            "transaction_id",
            "transactionId",
            "ID",
            "Id"
        ]
    )

    customer_column = find_column(
        df,
        [
            "Customer",
            "Customer_Name",
            "CustomerName",
            "Customer Name",
            "Name",
            "Customer ID",
            "Customer_ID"
        ]
    )

    merchant_column = find_column(
        df,
        [
            "Merchant",
            "Merchant_Name",
            "MerchantName",
            "Merchant Name",
            "App"
        ]
    )

    time_column = find_column(
        df,
        [
            "Time",
            "Timestamp",
            "Date",
            "Datetime",
            "DateTime",
            "TransactionDate",
            "Transaction_Date"
        ]
    )

    type_column = find_column(
        df,
        [
            "Type",
            "TransactionType",
            "Transaction_Type",
            "Transaction Type"
        ]
    )

    account_number_column = find_column(
        df,
        [
            "AccountNumber",
            "Account_Number",
            "Account Number",
            "Account No",
            "AccountNo",
            "Account"
        ]
    )

    bank_column = find_column(
        df,
        [
            "Bank",
            "BankName",
            "Bank_Name",
            "Bank Name"
        ]
    )

    account_type_column = find_column(
        df,
        [
            "AccountType",
            "Account_Type",
            "Account Type"
        ]
    )

    payment_method_column = find_column(
        df,
        [
            "PaymentMethod",
            "Payment_Method",
            "Payment Method"
        ]
    )

    channel_column = find_column(
        df,
        [
            "Channel",
            "AppChannel",
            "App_Channel",
            "App Channel"
        ]
    )

    location_column = find_column(
        df,
        [
            "Location",
            "City",
            "Country"
        ]
    )

    device_column = find_column(
        df,
        [
            "Device",
            "DeviceType",
            "Device_Type",
            "Device Type"
        ]
    )

    ip_column = find_column(
        df,
        [
            "IP",
            "IPAddress",
            "IP_Address",
            "IP Address"
        ]
    )

    previous_amount_column = find_column(
        df,
        [
            "PreviousAmount",
            "Previous_Amount",
            "Previous Amount",
            "previous_amount"
        ]
    )

    last_24h_column = find_column(
        df,
        [
            "TransactionsLast24Hours",
            "Transactions_Last_24h",
            "Transactions Last 24h",
            "transactions_last_24h"
        ]
    )

    unusual_location_column = find_column(
        df,
        [
            "UnusualLocation",
            "Unusual_Location",
            "Unusual Location",
            "unusual_location"
        ]
    )

    # --------------------------------------------------------
    # BUILD TRANSACTIONS
    # --------------------------------------------------------

    transactions = []

    safe_count = 0
    risky_count = 0
    fraud_count = 0

    for position in range(
        original_row_count
    ):

        row = df.iloc[position]

        # ----------------------------------------------------
        # TRANSACTION ID
        # ----------------------------------------------------

        if id_column is not None:

            transaction_id = row[id_column]

        else:

            transaction_id = (
                f"TXN-{position + 1:06d}"
            )

        if pd.isna(transaction_id):

            transaction_id = (
                f"TXN-{position + 1:06d}"
            )

        transaction_id = str(
            transaction_id
        )

        # ----------------------------------------------------
        # BASIC VALUES
        # ----------------------------------------------------

        customer = (
            row[customer_column]
            if customer_column is not None
            else "-"
        )

        merchant = (
            row[merchant_column]
            if merchant_column is not None
            else "-"
        )

        transaction_time = (
            row[time_column]
            if time_column is not None
            else "-"
        )

        transaction_type = (
            row[type_column]
            if type_column is not None
            else "-"
        )

        amount = numeric_value(
            row[amount_column],
            0
        )

        # ----------------------------------------------------
        # MODEL RESULT
        # ----------------------------------------------------

        model_prediction = predictions[
            position
        ]

        if (
            probabilities is not None
            and fraud_class_index is not None
        ):

            fraud_probability = float(
                probabilities[position][
                    fraud_class_index
                ]
            )

        else:

            fraud_probability = (
                1.0
                if str(
                    model_prediction
                ).strip() == "1"
                else 0.0
            )

        # ----------------------------------------------------
        # FRAUD DECISION
        # ----------------------------------------------------

        model_says_fraud = (

            str(
                model_prediction
            ).strip().lower()

            in [
                "1",
                "true",
                "fraud"
            ]

            or

            fraud_probability >= 0.70
        )

        # ----------------------------------------------------
        # CLASSIFICATION
        # ----------------------------------------------------

        if model_says_fraud:

            prediction_label = "Fraud"
            risk_level = "High Risk"
            status = "Fraud Detected"

            details = (
                "AI model detected a high-risk "
                "transaction requiring attention."
            )

            fraud_count += 1

        elif amount >= high_value_threshold:

            prediction_label = "Risky"
            risk_level = "Medium Risk"
            status = "Requires Attention"

            details = (
                "Transaction was not classified "
                "as fraud by the AI model, but "
                "its value is unusually high "
                "compared with this dataset."
            )

            risky_count += 1

        else:

            prediction_label = "Safe"
            risk_level = "Low Risk"
            status = "Normal"

            details = (
                "Transaction appears legitimate "
                "and has a normal transaction value."
            )

            safe_count += 1

        # ====================================================
        # MOST IMPORTANT PART
        # ====================================================
        #
        # COPY THE COMPLETE ORIGINAL CSV ROW.
        #
        # This means EVERY CSV column is preserved.
        #
        # ====================================================

        transaction = {}

        for column in original_columns:

            value = row[column]

            if pd.isna(value):

                value = "-"

            transaction[column] = value

        # ----------------------------------------------------
        # STANDARDIZED FIELDS
        # ----------------------------------------------------

        transaction["id"] = transaction_id

        transaction["transaction_id"] = transaction_id

        transaction["customer"] = str(
            customer
        )

        transaction["customer_name"] = str(
            customer
        )

        transaction["amount"] = amount

        transaction["merchant"] = str(
            merchant
        )

        transaction["time"] = str(
            transaction_time
        )

        transaction["type"] = str(
            transaction_type
        )

        # ----------------------------------------------------
        # AI FIELDS
        # ----------------------------------------------------

        transaction["prediction"] = (
            prediction_label
        )

        transaction["risk_level"] = (
            risk_level
        )

        transaction["status"] = status

        transaction["fraud_probability"] = round(
            fraud_probability,
            4
        )

        transaction[
            "fraud_probability_percent"
        ] = round(
            fraud_probability * 100,
            2
        )

        transaction["details"] = details

        # ----------------------------------------------------
        # STANDARDIZED BANKING FIELDS
        # ----------------------------------------------------

        transaction["account_number"] = (

            str(
                row[account_number_column]
            )

            if account_number_column is not None

            else "-"
        )

        transaction["bank_name"] = (

            str(
                row[bank_column]
            )

            if bank_column is not None

            else "-"
        )

        transaction["account_type"] = (

            str(
                row[account_type_column]
            )

            if account_type_column is not None

            else "-"
        )

        transaction["payment_method"] = (

            str(
                row[payment_method_column]
            )

            if payment_method_column is not None

            else "-"
        )

        transaction["app_channel"] = (

            str(
                row[channel_column]
            )

            if channel_column is not None

            else "-"
        )

        transaction["location"] = (

            str(
                row[location_column]
            )

            if location_column is not None

            else "-"
        )

        transaction["device_type"] = (

            str(
                row[device_column]
            )

            if device_column is not None

            else "-"
        )

        transaction["ip_address"] = (

            str(
                row[ip_column]
            )

            if ip_column is not None

            else "-"
        )

        transaction["previous_amount"] = (

            str(
                row[previous_amount_column]
            )

            if previous_amount_column is not None

            else "-"
        )

        transaction[
            "transactions_last_24h"
        ] = (

            str(
                row[last_24h_column]
            )

            if last_24h_column is not None

            else "-"
        )

        transaction["unusual_location"] = (

            str(
                row[unusual_location_column]
            )

            if unusual_location_column is not None

            else "-"
        )

        transactions.append(
            transaction
        )

    # ========================================================
    # VERIFICATION
    # ========================================================

    total = len(transactions)

    if total != original_row_count:

        raise ValueError(
            "TRANSACTION COUNT MISMATCH! "
            f"Uploaded CSV contains "
            f"{original_row_count} rows, "
            f"but only {total} transactions "
            f"were processed."
        )

    verification_total = (
        safe_count
        + risky_count
        + fraud_count
    )

    if verification_total != total:

        raise ValueError(
            "Statistics mismatch: "
            f"{safe_count} + "
            f"{risky_count} + "
            f"{fraud_count} != "
            f"{total}"
        )

    print()
    print("=" * 70)
    print("AI FRAUD ANALYSIS COMPLETED")
    print("=" * 70)

    print(
        "Uploaded rows:",
        original_row_count
    )

    print(
        "Processed rows:",
        total
    )

    print(
        "Safe:",
        safe_count
    )

    print(
        "Risky:",
        risky_count
    )

    print(
        "Fraud:",
        fraud_count
    )

    print(
        "Original CSV fields preserved:",
        len(original_columns)
    )

    print(
        "Verification:",
        verification_total,
        "/",
        original_row_count
    )

    print("=" * 70)

    return {
        "transactions": transactions,
        "total": total,
        "safe": safe_count,
        "risky": risky_count,
        "fraud": fraud_count
    }