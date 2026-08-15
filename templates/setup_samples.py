import os
import csv
import random
from datetime import datetime, timedelta

# ============================================================
# CONFIGURATION
# ============================================================

OUTPUT_FOLDER = os.path.join("static", "sample")

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Sample sizes
DATASET_SIZES = [
    500,
    1000,
    5000,
    10000,
    25000,
    50000
]

# ============================================================
# BANKING DATA
# ============================================================

customers = [
    "Rahul Sharma",
    "Amit Kumar",
    "Priya Singh",
    "Neha Gupta",
    "Rohit Verma",
    "Vikas Malhotra",
    "Anjali Mehta",
    "Karan Patel",
    "Sneha Agarwal",
    "Arjun Singh",
    "Pooja Sharma",
    "Aditya Kumar",
    "Riya Gupta",
    "Nikhil Verma",
    "Simran Kaur"
]

safe_merchants = [
    "Amazon",
    "Flipkart",
    "Walmart",
    "Reliance Digital",
    "Swiggy",
    "Zomato",
    "Uber",
    "IRCTC",
    "Myntra",
    "BigBasket",
    "BookMyShow",
    "Netflix",
    "Airtel",
    "Jio",
    "DMart"
]

risky_merchants = [
    "Unknown Merchant",
    "International Store",
    "Unverified Seller",
    "Crypto Exchange",
    "Foreign Merchant",
    "Unknown Online Shop",
    "High Risk Merchant"
]

safe_locations = [
    "Delhi",
    "Mumbai",
    "Bangalore",
    "Pune",
    "Hyderabad",
    "Chennai",
    "Kolkata",
    "Noida",
    "Gurgaon",
    "Lucknow"
]

risky_locations = [
    "Unknown Location",
    "International",
    "Foreign Country",
    "Unverified Location",
    "High Risk Region"
]

payment_types = [
    "UPI",
    "Card",
    "Net Banking",
    "Wallet"
]

# ============================================================
# CSV COLUMNS
# ============================================================

columns = [
    "Transaction_ID",
    "Customer",
    "Age",
    "Amount_INR",
    "Previous_Amount_INR",
    "Merchant",
    "Location",
    "Payment_Type",
    "Date_Time",
    "Risk_Score",
    "Risk_Level",
    "Actual_Label"
]

# ============================================================
# GENERATE ONE TRANSACTION
# ============================================================

def generate_transaction(transaction_number):

    transaction_id = f"TXN{transaction_number:06d}"

    customer = random.choice(customers)

    age = random.randint(18, 75)

    # --------------------------------------------------------
    # Decide transaction type
    #
    # 90% Safe
    # 6% Suspicious
    # 4% Fraud
    # --------------------------------------------------------

    probability = random.random()

    if probability < 0.04:

        transaction_status = "fraud"

    elif probability < 0.10:

        transaction_status = "risky"

    else:

        transaction_status = "safe"

    # ========================================================
    # SAFE TRANSACTION
    # ========================================================

    if transaction_status == "safe":

        amount = round(
            random.uniform(200, 15000),
            2
        )

        previous_amount = round(
            random.uniform(
                amount * 0.5,
                amount * 1.3
            ),
            2
        )

        merchant = random.choice(
            safe_merchants
        )

        location = random.choice(
            safe_locations
        )

        payment = random.choice(
            payment_types
        )

        risk_score = round(
            random.uniform(2, 30),
            2
        )

        risk_level = "Low"

        actual_label = "Risky"

    # ========================================================
    # RISKY TRANSACTION
    # ========================================================

    elif transaction_status == "risky":

        amount = round(
            random.uniform(15000, 75000),
            2
        )

        # Large jump from previous transaction
        previous_amount = round(
            random.uniform(
                500,
                amount * 0.25
            ),
            2
        )

        merchant = random.choice(
            risky_merchants
        )

        location = random.choice(
            risky_locations
        )

        payment = random.choice(
            payment_types
        )

        risk_score = round(
            random.uniform(55, 84),
            2
        )

        risk_level = "Medium"

        # Keep as Safe ground truth so AI can classify
        # suspicious behavior separately if required.
        actual_label = "Risky"

    # ========================================================
    # FRAUD TRANSACTION
    # ========================================================

    else:

        amount = round(
            random.uniform(50000, 250000),
            2
        )

        # Extremely unusual previous amount
        previous_amount = round(
            random.uniform(
                100,
                5000
            ),
            2
        )

        merchant = random.choice(
            risky_merchants
        )

        location = random.choice(
            risky_locations
        )

        payment = random.choice(
            payment_types
        )

        risk_score = round(
            random.uniform(85, 99.9),
            2
        )

        risk_level = "High"

        actual_label = "Fraud"

    # ========================================================
    # DATE / TIME
    # ========================================================

    base_date = datetime.now()

    transaction_date = base_date - timedelta(
        days=random.randint(0, 180),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59)
    )

    date_time = transaction_date.strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    # ========================================================
    # RETURN TRANSACTION
    # ========================================================

    return [
        transaction_id,
        customer,
        age,
        amount,
        previous_amount,
        merchant,
        location,
        payment,
        date_time,
        risk_score,
        risk_level,
        actual_label
    ]


# ============================================================
# CREATE DATASET
# ============================================================

def create_dataset(number_of_transactions):

    filename = os.path.join(
        OUTPUT_FOLDER,
        f"banking_transactions_{number_of_transactions}.csv"
    )

    safe_count = 0
    risky_count = 0
    fraud_count = 0

    with open(
        filename,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        writer.writerow(columns)

        for i in range(
            1,
            number_of_transactions + 1
        ):

            row = generate_transaction(i)

            writer.writerow(row)

            label = row[-1]
            risk_level = row[-2]

            if label == "Fraud":

                fraud_count += 1

            elif risk_level == "Medium":

                risky_count += 1

            else:

                safe_count += 1

    print(
        f"Created: {filename}"
    )

    print(
        f"   Safe:  {safe_count}"
    )

    print(
        f"   Risky: {risky_count}"
    )

    print(
        f"   Fraud: {fraud_count}"
    )

    print()


# ============================================================
# CREATE ALL DATASETS
# ============================================================

print()
print("=" * 55)
print("AI FRAUD DETECTION - BANKING SAMPLE GENERATOR")
print("=" * 55)
print()

for size in DATASET_SIZES:

    create_dataset(size)

print("=" * 55)
print("ALL BANKING SAMPLE DATASETS CREATED SUCCESSFULLY!")
print("=" * 55)
print()