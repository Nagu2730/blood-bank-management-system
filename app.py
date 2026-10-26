from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
import os
import heapq
from datetime import datetime, timedelta
from collections import deque


app = Flask(__name__)
app.secret_key = "secret123"


# ============================================================
# ADVANCED DATA STRUCTURES USED IN THIS PROJECT
# ============================================================
# Min-Heap / Priority Queue : emergency blood request processing
# Hash Table               : O(1)-average donor lookup
# Graph + BFS/DFS          : blood compatibility traversal
# Deque                    : recent request event history
# Linked List              : donation history

# ============================================================
# PRIORITY QUEUE - ADVANCED DATA STRUCTURE
# ============================================================

# Critical -> 1
# High     -> 2
# Normal   -> 3

blood_request_queue = []


# ============================================================
# ADVANCED DATA STRUCTURES - COMPLETE IMPLEMENTATION
# ============================================================
# 1. Min-Heap / Priority Queue -> blood request priority
# 2. Hash Table -> fast donor lookup by phone and blood group
# 3. Graph + BFS/DFS -> blood-group compatibility traversal
# 4. Deque -> recent request event history
# 5. Linked List -> donor donation history


# ---------------- HASH TABLE ----------------
# Phone number -> donor record
# Blood group -> {phone -> donor record}
donor_hash = {}
donor_group_hash = {}


def refresh_donor_hash():
    """Rebuild donor indexes from the database."""
    donor_hash.clear()
    donor_group_hash.clear()

    conn = sqlite3.connect("database/database.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            name,
            email,
            phone,
            address,
            blood_group,
            availability,
            last_donation,
            health_status
        FROM donors
    """)

    rows = cursor.fetchall()
    conn.close()

    for row in rows:
        (
            name,
            email,
            phone,
            address,
            blood_group,
            availability,
            last_donation,
            health_status
        ) = row

        donor = {
            "name": name or "",
            "email": email or "",
            "phone": phone or "",
            "address": address or "",
            "blood_group": blood_group or "",
            "availability": availability or "Unavailable",
            "last_donation": last_donation,
            "health_status": health_status or "Pending"
        }

        if phone:
            donor_hash[phone] = donor

        group = (blood_group or "").upper()
        if group:
            donor_group_hash.setdefault(group, {})[phone] = donor


def get_donor_by_phone(phone):
    """O(1) average-time donor lookup using the hash table."""
    return donor_hash.get(phone)


def get_donors_by_blood_group(blood_group):
    """O(1) average-time access to donors indexed by blood group."""
    return list(
        donor_group_hash.get(
            (blood_group or "").upper(),
            {}
        ).values()
    )


# ---------------- GRAPH + BFS/DFS ----------------
# Recipient blood group -> compatible donor blood groups.
# This graph is used by the donor matching algorithm.
blood_compatibility_graph = {
    "O-": ["O-"],
    "O+": ["O+", "O-"],
    "A-": ["A-", "O-"],
    "A+": ["A+", "A-", "O+", "O-"],
    "B-": ["B-", "O-"],
    "B+": ["B+", "B-", "O+", "O-"],
    "AB-": ["AB-", "A-", "B-", "O-"],
    "AB+": ["AB+", "AB-", "A+", "A-", "B+", "B-", "O+", "O-"]
}


def bfs_compatible_blood_groups(start_group):
    """Breadth-First Search over the blood compatibility graph."""
    start_group = (start_group or "").upper()
    if start_group not in blood_compatibility_graph:
        return []

    queue = deque([start_group])
    visited = {start_group}
    order = []

    while queue:
        current = queue.popleft()
        order.append(current)

        for neighbour in blood_compatibility_graph.get(current, []):
            if neighbour not in visited:
                visited.add(neighbour)
                queue.append(neighbour)

    return order


def dfs_compatible_blood_groups(start_group):
    """Depth-First Search over the blood compatibility graph."""
    start_group = (start_group or "").upper()
    if start_group not in blood_compatibility_graph:
        return []

    visited = set()
    order = []

    def dfs(node):
        visited.add(node)
        order.append(node)
        for neighbour in blood_compatibility_graph.get(node, []):
            if neighbour not in visited:
                dfs(neighbour)

    dfs(start_group)
    return order


# ---------------- DEQUE / REQUEST HISTORY ----------------
request_history = deque(maxlen=50)


def record_request_event(request_id, event, patient_name="", status=""):
    """Persist and maintain the most recent 50 request events in a deque."""
    event_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        conn = sqlite3.connect("database/database.db")
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO request_events(
                request_id,
                event,
                patient_name,
                status,
                event_time
            )
            VALUES(?, ?, ?, ?, ?)
        """, (
            request_id,
            event,
            patient_name or "",
            status or "",
            event_time
        ))

        event_id = cursor.lastrowid

        conn.commit()
        conn.close()

        request_history.append({
            "event_id": event_id,
            "request_id": request_id,
            "event": event,
            "patient_name": patient_name or "",
            "status": status or "",
            "time": event_time
        })

    except Exception:
        pass


def load_request_history():
    """Rebuild the deque from the latest persisted request events."""
    request_history.clear()

    conn = sqlite3.connect("database/database.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            request_id,
            event,
            patient_name,
            status,
            event_time
        FROM request_events
        ORDER BY id DESC
        LIMIT 50
    """)

    rows = cursor.fetchall()
    conn.close()

    for row in reversed(rows):
        request_history.append({
            "event_id": row[0],
            "request_id": row[1],
            "event": row[2],
            "patient_name": row[3],
            "status": row[4],
            "time": row[5]
        })


def delete_request_event(event_id):
    """Delete one persisted Deque history event by its event-row id."""
    conn = sqlite3.connect("database/database.db")
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM request_events
        WHERE id=?
    """, (event_id,))

    changed = cursor.rowcount
    conn.commit()
    conn.close()

    load_request_history()
    return changed




# ---------------- LINKED LIST / DONATION HISTORY ----------------


# ---------------- LINKED LIST / DONATION HISTORY ----------------
class DonationNode:
    def __init__(self, donation_id, donor_name, date, status):
        self.donation_id = donation_id
        self.donor_name = donor_name
        self.date = date
        self.status = status
        self.next = None


class DonationLinkedList:
    def __init__(self):
        self.head = None
        self.tail = None
        self.size = 0

    def append(self, donation_id, donor_name, date, status):
        node = DonationNode(
            donation_id,
            donor_name,
            date,
            status
        )

        if self.head is None:
            self.head = node
            self.tail = node
        else:
            self.tail.next = node
            self.tail = node

        self.size += 1

    def to_list(self):
        result = []
        current = self.head

        while current is not None:
            result.append({
                "id": current.donation_id,
                "donor_name": current.donor_name,
                "date": current.date,
                "status": current.status
            })
            current = current.next

        return result

    def find_by_donor_name(self, donor_name):
        result = []
        current = self.head

        while current is not None:
            if (
                (current.donor_name or "").strip().lower()
                == (donor_name or "").strip().lower()
            ):
                result.append({
                    "id": current.donation_id,
                    "donor_name": current.donor_name,
                    "date": current.date,
                    "status": current.status
                })
            current = current.next

        return result


donation_linked_list = DonationLinkedList()


def load_donation_linked_list():
    """Load existing donation records into the linked list."""
    global donation_linked_list

    donation_linked_list = DonationLinkedList()

    conn = sqlite3.connect("database/database.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, donor_name, date, status
        FROM donations
        ORDER BY id ASC
    """)

    rows = cursor.fetchall()
    conn.close()

    for row in rows:
        donation_linked_list.append(
            row[0],
            row[1],
            row[2],
            row[3]
        )




def add_blood_request(request_id, patient_name, blood_group, priority):

    priority_value = {
        "Critical": 1,
        "High": 2,
        "Normal": 3
    }

    heapq.heappush(
        blood_request_queue,
        (
            priority_value.get(priority, 3),
            request_id,
            patient_name,
            blood_group,
            priority
        )
    )


def get_next_blood_request():

    if blood_request_queue:
        return heapq.heappop(blood_request_queue)

    return None


def load_pending_requests_into_queue():

    blood_request_queue.clear()

    conn = sqlite3.connect("database/database.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, patient_name, blood_group, priority
        FROM blood_requests
        WHERE status='Pending'
    """)

    requests = cursor.fetchall()

    conn.close()

    for request_id, patient_name, blood_group, priority in requests:

        add_blood_request(
            request_id,
            patient_name,
            blood_group,
            priority
        )


# ============================================================
# DATABASE
# ============================================================

if not os.path.exists("database"):
    os.makedirs("database")


conn = sqlite3.connect("database/database.db")
cursor = conn.cursor()


# ============================================================
# DONOR TABLE
# ============================================================

cursor.execute("""
CREATE TABLE IF NOT EXISTS donors(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT,
    phone TEXT,
    address TEXT,
    blood_group TEXT,
    availability TEXT,
    password TEXT,
    coins INTEGER DEFAULT 0,
    last_donation TEXT,
    report TEXT
)
""")


# ============================================================
# FEEDBACK TABLE
# ============================================================

cursor.execute("""
CREATE TABLE IF NOT EXISTS feedback(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_email TEXT,
    message TEXT,
    image TEXT,
    date TEXT
)
""")


# ============================================================
# DONATION HISTORY
# ============================================================

cursor.execute("""
CREATE TABLE IF NOT EXISTS donations(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    donor_name TEXT,
    date TEXT,
    status TEXT
)
""")


# ============================================================
# ADMIN TABLE
# ============================================================

cursor.execute("""
CREATE TABLE IF NOT EXISTS admin(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    password TEXT
)
""")


# Create default admin if it does not exist
cursor.execute("""
    INSERT OR IGNORE INTO admin(id, username, password)
    VALUES(1, 'admin', 'admin123')
""")


# ============================================================
# SYSTEM SETTINGS
# ============================================================

cursor.execute("""
CREATE TABLE IF NOT EXISTS system_settings(
    id INTEGER PRIMARY KEY,
    coin_per_donation INTEGER,
    interval_days INTEGER
)
""")


cursor.execute("""
    INSERT OR IGNORE INTO system_settings
    (id, coin_per_donation, interval_days)
    VALUES(1, 200, 90)
""")


# ============================================================
# HEALTH REPORTS
# ============================================================

cursor.execute("""
CREATE TABLE IF NOT EXISTS health_reports(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    donor_name TEXT,
    hemoglobin REAL,
    report_date TEXT,
    status TEXT
)
""")


# ============================================================
# BLOOD REQUESTS
# ============================================================

cursor.execute("""
CREATE TABLE IF NOT EXISTS blood_requests(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_name TEXT,
    blood_group TEXT,
    priority TEXT,
    request_date TEXT,
    status TEXT,
    location TEXT
)
""")


# ============================================================
# REQUEST EVENT HISTORY TABLE - supports Deque persistence
# ============================================================
cursor.execute("""
CREATE TABLE IF NOT EXISTS request_events(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id INTEGER,
    event TEXT,
    patient_name TEXT,
    status TEXT,
    event_time TEXT
)
""")


conn.commit()
conn.close()


# ============================================================
# DATABASE UPGRADE
# ============================================================

conn = sqlite3.connect("database/database.db")
cursor = conn.cursor()

try:
    cursor.execute(
        "ALTER TABLE donors ADD COLUMN custom_interval INTEGER DEFAULT 0"
    )
except:
    pass

try:
    cursor.execute(
        "ALTER TABLE donors ADD COLUMN health_status TEXT DEFAULT 'Pending'"
    )
except:
    pass

try:
    cursor.execute(
        "ALTER TABLE donors ADD COLUMN next_eligible TEXT"
    )
except:
    pass

try:
    cursor.execute(
        "ALTER TABLE blood_requests ADD COLUMN location TEXT"
    )
except:
    pass

conn.commit()
conn.close()


# Build in-memory Advanced Data Structures from persisted data
refresh_donor_hash()
load_request_history()
load_donation_linked_list()


# ============================================================
# HELPER
# ============================================================

def get_settings():

    conn = sqlite3.connect("database/database.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT coin_per_donation, interval_days
        FROM system_settings
        WHERE id=1
    """)

    data = cursor.fetchone()

    conn.close()

    return data


# ============================================================
# ELIGIBILITY
# ============================================================

def is_eligible(last_donation, email=None):

    settings = get_settings()

    if not settings:
        return True

    coin_value, default_interval = settings

    conn = sqlite3.connect("database/database.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT custom_interval, next_eligible
        FROM donors
        WHERE email=?
    """, (email,))

    row = cursor.fetchone()

    conn.close()

    custom_interval = row[0] if row else 0
    next_eligible = row[1] if row else None

    # Admin controlled next eligible date
    if next_eligible:

        try:
            next_date = datetime.strptime(
                next_eligible,
                "%Y-%m-%d"
            )

            return datetime.now() >= next_date

        except:
            pass

    interval = (
        custom_interval
        if custom_interval and custom_interval > 0
        else default_interval
    )

    if not last_donation:
        return True

    try:

        last = datetime.strptime(
            last_donation,
            "%Y-%m-%d"
        )

        return datetime.now() >= last + timedelta(days=interval)

    except:

        return True


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():
    return render_template("home.html")


# ============================================================
# ABOUT
# ============================================================

@app.route("/about")
def about():
    return render_template("about.html")


# ============================================================
# ADMIN HOME
# ============================================================

@app.route("/admin_home")
def admin_home():

    if "admin" not in session:
        return redirect("/admin_login")

    return render_template("admin_home.html")


# ============================================================
# ADMIN LOGIN - FIXED
# ============================================================

@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        ).strip()

        # ====================================================
        # DEFAULT ADMIN LOGIN
        # ====================================================

        if (
            username.lower() == "admin"
            and password == "admin123"
        ):

            conn = sqlite3.connect(
                "database/database.db"
            )

            cursor = conn.cursor()

            # Make sure admin table exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS admin(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT,
                    password TEXT
                )
            """)

            # Check first admin
            cursor.execute("""
                SELECT id
                FROM admin
                ORDER BY id
                LIMIT 1
            """)

            existing_admin = cursor.fetchone()

            if existing_admin:

                cursor.execute("""
                    UPDATE admin
                    SET username=?,
                        password=?
                    WHERE id=?
                """, (
                    "admin",
                    "admin123",
                    existing_admin[0]
                ))

            else:

                cursor.execute("""
                    INSERT INTO admin
                    (username, password)
                    VALUES (?, ?)
                """, (
                    "admin",
                    "admin123"
                ))

            conn.commit()
            conn.close()

            # Create fresh admin session
            session.clear()
            session["admin"] = "admin"

            return redirect("/admin_home")


        # ====================================================
        # DATABASE ADMIN LOGIN
        # ====================================================

        conn = sqlite3.connect(
            "database/database.db"
        )

        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, username, password
            FROM admin
            WHERE LOWER(TRIM(username)) = LOWER(?)
            AND CAST(password AS TEXT) = ?
            LIMIT 1
        """, (
            username,
            password
        ))

        admin = cursor.fetchone()

        conn.close()

        if admin:

            session.clear()
            session["admin"] = admin[1]

            return redirect("/admin_home")


        # ====================================================
        # INVALID LOGIN
        # ====================================================

        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Invalid Admin Login</title>
            <style>

                body {
                    font-family: Arial, sans-serif;
                    background: #f8fafc;
                    text-align: center;
                    padding-top: 80px;
                }

                .box {
                    width: 420px;
                    max-width: 90%;
                    margin: auto;
                    background: white;
                    padding: 30px;
                    border-radius: 15px;
                    box-shadow: 0 8px 25px rgba(0,0,0,0.10);
                }

                h2 {
                    color: #dc3545;
                }

                a {
                    display: inline-block;
                    margin-top: 20px;
                    background: #2563eb;
                    color: white;
                    text-decoration: none;
                    padding: 10px 20px;
                    border-radius: 8px;
                }

            </style>
        </head>

        <body>

            <div class="box">

                <h2>
                    Invalid Admin Login ❌
                </h2>

                <p>
                    Please use:
                </p>

                <p>
                    <strong>Username:</strong> admin
                </p>

                <p>
                    <strong>Password:</strong> admin123
                </p>

                <a href="/admin_login">
                    Back to Login
                </a>

            </div>

        </body>
        </html>
        """

    return render_template("admin_login.html")


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@app.route("/admin_dashboard")
def admin_dashboard():

    if "admin" not in session:
        return redirect("/admin_login")

    search = request.args.get(
        "search",
        ""
    ).strip()

    conn = sqlite3.connect(
        "database/database.db"
    )

    cursor = conn.cursor()

    if search:

        cursor.execute("""
            SELECT
                name,
                phone,
                blood_group,
                coins,
                last_donation,
                health_status
            FROM donors
            WHERE name LIKE ?
            ORDER BY
                LOWER(name) ASC,
                id ASC
        """, (
            "%" + search + "%",
        ))

    else:

        cursor.execute("""
            SELECT
                name,
                phone,
                blood_group,
                coins,
                last_donation,
                health_status
            FROM donors
            ORDER BY
                LOWER(name) ASC,
                id ASC
        """)

    donors = cursor.fetchall()

    cursor.execute("""
        SELECT
            coin_per_donation,
            interval_days
        FROM system_settings
        WHERE id=1
    """)

    settings = cursor.fetchone()

    conn.close()

    return render_template(
        "admin_dashboard.html",
        donors=donors,
        settings=settings,
        search=search
    )


# ============================================================
# UPDATE SETTINGS
# ============================================================

@app.route("/update_settings", methods=["POST"])
def update_settings():

    coins = request.form.get(
        "coins",
        "200"
    )

    interval = request.form.get(
        "interval",
        "90"
    )

    conn = sqlite3.connect(
        "database/database.db"
    )

    cursor = conn.cursor()

    cursor.execute("""
        UPDATE system_settings
        SET coin_per_donation=?,
            interval_days=?
        WHERE id=1
    """, (
        coins,
        interval
    ))

    conn.commit()
    conn.close()

    flash(
        "Settings updated successfully!",
        "success"
    )

    return redirect(
        "/admin_dashboard"
    )


# ============================================================
# ADMIN VERIFY
# ============================================================

@app.route(
    "/admin_verify/<phone>",
    methods=["POST"]
)
def admin_verify(phone):

    today = datetime.now().strftime(
        "%Y-%m-%d"
    )

    conn = sqlite3.connect(
        "database/database.db"
    )

    cursor = conn.cursor()

    cursor.execute("""
        SELECT coin_per_donation
        FROM system_settings
        WHERE id=1
    """)

    result = cursor.fetchone()
    coins = result[0] if result else 200

    settings = get_settings()

    interval_days = (
        settings[1]
        if settings
        else 90
    )

    next_date = (
        datetime.now()
        + timedelta(days=interval_days)
    )

    cursor.execute("""
        SELECT name
        FROM donors
        WHERE phone=?
    """, (phone,))

    donor_row = cursor.fetchone()
    donor_name = donor_row[0] if donor_row else "Unknown Donor"

    cursor.execute("""
        UPDATE donors
        SET coins = coins + ?,
            last_donation = ?,
            availability = 'Unavailable',
            next_eligible = ?
        WHERE phone = ?
    """, (
        coins,
        today,
        next_date.strftime("%Y-%m-%d"),
        phone
    ))

    changed = cursor.rowcount
    donation_id = None
    donation_status = "Verified"

    # Store donation only when a real donor was verified.
    if changed:
        cursor.execute("""
            INSERT INTO donations(
                donor_name,
                date,
                status
            )
            VALUES(?, ?, ?)
        """, (
            donor_name,
            today,
            donation_status
        ))

        donation_id = cursor.lastrowid

    conn.commit()
    conn.close()

    if donation_id is not None:
        donation_linked_list.append(
            donation_id,
            donor_name,
            today,
            donation_status
        )

    refresh_donor_hash()

    return redirect(
        "/admin_dashboard"
    )


# ============================================================
# HEALTH DASHBOARD
# ============================================================

@app.route("/health_dashboard")
def health_dashboard():

    if "admin" not in session:
        return redirect("/admin_login")

    conn = sqlite3.connect(
        "database/database.db"
    )

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            name,
            phone,
            health_status,
            report
        FROM donors
        ORDER BY LOWER(name) ASC, id ASC
    """)

    donors = cursor.fetchall()

    cursor.execute("""
        SELECT
            id,
            donor_name,
            hemoglobin,
            report_date,
            status
        FROM health_reports
        ORDER BY id DESC
    """)

    health_reports = cursor.fetchall()

    conn.close()

    return render_template(
        "health_dashboard.html",
        donors=donors,
        health_reports=health_reports,
        settings=None
    )


# ============================================================
# COIN CONTROL
# ============================================================

@app.route(
    "/update_coins/<donor_phone>",
    methods=["POST"]
)
def update_coins(donor_phone):

    action = request.form.get(
        "action",
        "add"
    )

    try:

        amount = int(
            request.form.get(
                "amount",
                0
            )
        )

    except:

        amount = 0

    conn = sqlite3.connect(
        "database/database.db"
    )

    cursor = conn.cursor()

    if action == "add":

        cursor.execute("""
            UPDATE donors
            SET coins = coins + ?
            WHERE phone=?
        """, (
            amount,
            donor_phone
        ))

    else:

        cursor.execute("""
            UPDATE donors
            SET coins = coins - ?
            WHERE phone=?
        """, (
            amount,
            donor_phone
        ))

    conn.commit()
    conn.close()

    return redirect(
        "/admin_dashboard"
    )


# ============================================================
# INTERVAL CONTROL
# ============================================================

@app.route(
    "/update_interval/<donor_phone>",
    methods=["POST"]
)
def update_interval(donor_phone):

    try:

        days = int(
            request.form.get(
                "days",
                0
            )
        )

    except:

        days = 0

    conn = sqlite3.connect(
        "database/database.db"
    )

    cursor = conn.cursor()

    cursor.execute("""
        UPDATE donors
        SET custom_interval=?
        WHERE phone=?
    """, (
        days,
        donor_phone
    ))

    conn.commit()
    conn.close()

    return redirect(
        "/admin_dashboard"
    )


# ============================================================
# ADMIN NEXT DATE CONTROL
# ============================================================

@app.route(
    "/set_next_date/<phone>",
    methods=["POST"]
)
def set_next_date(phone):

    date = request.form.get(
        "next_date"
    )

    conn = sqlite3.connect(
        "database/database.db"
    )

    cursor = conn.cursor()

    cursor.execute("""
        UPDATE donors
        SET next_eligible=?
        WHERE phone=?
    """, (
        date,
        phone
    ))

    conn.commit()
    conn.close()

    return redirect(
        "/admin_dashboard"
    )


# ============================================================
# SIGNUP
# ============================================================

@app.route("/signup")
def signup():

    return render_template(
        "signup.html"
    )


# ============================================================
# REGISTER
# ============================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "GET":
        return render_template(
            "signup.html"
        )

    data = request.form

    name = data.get(
        "name",
        ""
    ).strip()

    email = data.get(
        "email",
        ""
    ).strip()

    phone = data.get(
        "phone",
        ""
    ).strip()

    address = data.get(
        "address",
        ""
    ).strip()

    blood_group = data.get(
        "blood_group"
    )

    password = data.get(
        "password",
        ""
    )

    confirm_password = data.get(
        "confirm_password",
        ""
    )

    try:

        age = int(
            data.get(
                "age",
                0
            )
        )

    except:

        age = 0

    try:

        weight = int(
            data.get(
                "weight",
                0
            )
        )

    except:

        weight = 0

    gender = data.get(
        "gender"
    )

    report_date = data.get(
        "report_date"
    )

    report = request.files.get(
        "report"
    )


    valid_blood_groups = [
        "A+",
        "A-",
        "B+",
        "B-",
        "AB+",
        "AB-",
        "O+",
        "O-"
    ]


    if len(name) < 3:

        flash(
            "Name must contain at least 3 characters"
        )

        return redirect(
            "/register"
        )


    if len(phone) != 10 or not phone.isdigit():

        flash(
            "Phone number must contain 10 digits"
        )

        return redirect(
            "/register"
        )


    if age < 18 or age > 60:

        flash(
            "Donor age must be between 18 and 60 years"
        )

        return redirect(
            "/register"
        )


    if gender not in [
        "Male",
        "Female",
        "Other"
    ]:

        flash(
            "Please select valid gender"
        )

        return redirect(
            "/register"
        )


    if weight < 50:

        flash(
            "Weight must be at least 50 kg"
        )

        return redirect(
            "/register"
        )


    if len(password) < 6:

        flash(
            "Password must contain at least 6 characters"
        )

        return redirect(
            "/register"
        )


    # Require at least one non-alphanumeric, non-space character.
    if not any(
        not character.isalnum() and not character.isspace()
        for character in password
    ):

        flash(
            "Password must include at least one special character, e.g. @, #, $, or !"
        )

        return redirect(
            "/register"
        )


    if password != confirm_password:

        flash(
            "Passwords do not match"
        )

        return redirect(
            "/register"
        )


    if blood_group not in valid_blood_groups:

        flash(
            "Invalid blood group selected"
        )

        return redirect(
            "/register"
        )


    if not report or report.filename == "":

        flash(
            "Please upload blood report"
        )

        return redirect(
            "/register"
        )


    if not report_date:

        flash(
            "Please select report date"
        )

        return redirect(
            "/register"
        )


    try:

        today = datetime.today()

        report_date_obj = datetime.strptime(
            report_date,
            "%Y-%m-%d"
        )

        difference = (
            today - report_date_obj
        ).days

    except:

        flash(
            "Invalid report date"
        )

        return redirect(
            "/register"
        )


    if difference < 0:

        flash(
            "Blood report date cannot be in the future"
        )

        return redirect(
            "/register"
        )


    if difference > 10:

        flash(
            "Blood report must be within 10 days"
        )

        return redirect(
            "/register"
        )


    allowed_extensions = [
        ".png",
        ".jpg",
        ".jpeg",
        ".pdf"
    ]


    file_ext = os.path.splitext(
        report.filename
    )[1].lower()


    if file_ext not in allowed_extensions:

        flash(
            "Only PNG, JPG, JPEG and PDF files allowed"
        )

        return redirect(
            "/register"
        )


    if not os.path.exists(
        "static/uploads"
    ):

        os.makedirs(
            "static/uploads"
        )


    filename = report.filename

    report.save(
        os.path.join(
            "static/uploads",
            filename
        )
    )


    conn = sqlite3.connect(
        "database/database.db"
    )

    cursor = conn.cursor()


    cursor.execute("""
        SELECT *
        FROM donors
        WHERE email=?
    """, (
        email,
    ))

    existing_email = cursor.fetchone()


    if existing_email:

        conn.close()

        flash(
            "Email already registered"
        )

        return redirect(
            "/register"
        )


    cursor.execute("""
        SELECT *
        FROM donors
        WHERE phone=?
    """, (
        phone,
    ))

    existing_phone = cursor.fetchone()


    if existing_phone:

        conn.close()

        flash(
            "Phone number already registered"
        )

        return redirect(
            "/register"
        )


    cursor.execute("""
        INSERT INTO donors(
            name,
            email,
            phone,
            address,
            blood_group,
            availability,
            password,
            coins,
            report,
            health_status
        )
        VALUES(
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?
        )
    """, (
        name,
        email,
        phone,
        address,
        blood_group,
        "Unavailable",
        password,
        0,
        filename,
        "Pending"
    ))


    conn.commit()
    conn.close()

    # Update Hash Table immediately after adding a new donor.
    refresh_donor_hash()


    flash(
        "Registration successful. Waiting for admin verification"
    )


    return redirect(
        "/login"
    )


# ============================================================
# DONOR LOGIN
# ============================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        conn = sqlite3.connect(
            "database/database.db"
        )

        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM donors
            WHERE email=?
            AND password=?
        """, (
            email,
            password
        ))

        user = cursor.fetchone()

        conn.close()


        if user:

            session.clear()
            session["user"] = email

            return redirect(
                "/dashboard"
            )


        flash(
            "Invalid email or password"
        )


    return render_template(
        "login.html"
    )


# ============================================================
# DONOR DASHBOARD
# ============================================================

@app.route("/dashboard")
def dashboard():

    if "user" not in session:

        return redirect(
            "/login"
        )


    conn = sqlite3.connect(
        "database/database.db"
    )

    cursor = conn.cursor()


    cursor.execute("""
        SELECT
            name,
            availability,
            coins,
            last_donation,
            next_eligible,
            health_status
        FROM donors
        WHERE email=?
    """, (
        session["user"],
    ))


    user = cursor.fetchone()

    conn.close()


    if not user:

        session.clear()

        return redirect(
            "/login"
        )


    eligible = is_eligible(
        user[3],
        session["user"]
    )


    if eligible:

        if user[1] == "Available":

            status = "Available"

        else:

            status = "Eligible"

    else:

        status = "Not Eligible"


    return render_template(
        "dashboard.html",
        name=user[0],
        availability=status,
        coins=user[2],
        health_status=user[5]
    )


# ============================================================
# TOGGLE STATUS
# ============================================================

@app.route(
    "/toggle_status",
    methods=["POST"]
)
def toggle_status():

    if "user" not in session:

        return redirect(
            "/login"
        )


    conn = sqlite3.connect(
        "database/database.db"
    )

    cursor = conn.cursor()


    cursor.execute("""
        SELECT
            availability,
            last_donation,
            next_eligible
        FROM donors
        WHERE email=?
    """, (
        session["user"],
    ))


    data = cursor.fetchone()


    if not data:

        conn.close()

        return redirect(
            "/login"
        )


    if not is_eligible(
        data[1],
        session["user"]
    ):

        conn.close()

        flash(
            "You are not eligible to donate yet."
        )

        return redirect(
            "/dashboard"
        )


    new = (
        "Unavailable"
        if data[0] == "Available"
        else "Available"
    )


    cursor.execute("""
        UPDATE donors
        SET availability=?
        WHERE email=?
    """, (
        new,
        session["user"]
    ))


    conn.commit()
    conn.close()


    return redirect(
        "/dashboard"
    )


# ============================================================
# MATCH DONORS - HASH TABLE + GRAPH/BFS
# ============================================================

@app.route(
    "/submit_request",
    methods=["POST"]
)
def submit_request():

    blood = request.form.get(
        "blood_group",
        ""
    ).strip().upper()

    location_raw = request.form.get(
        "location",
        ""
    ).strip()

    location = location_raw.lower()

    req_type = request.form.get(
        "type",
        ""
    )

    # Graph/BFS determines the compatible donor blood-group order.
    compatible_groups = bfs_compatible_blood_groups(blood)
    if not compatible_groups:
        compatible_groups = [blood]

    valid = []
    seen_phones = set()

    # Hash Table provides fast access to donors by blood group.
    for group_rank, donor_group in enumerate(compatible_groups):

        for donor in get_donors_by_blood_group(donor_group):

            phone = donor.get("phone", "")

            if phone in seen_phones:
                continue

            seen_phones.add(phone)

            if donor.get("availability") != "Available":
                continue

            if not is_eligible(
                donor.get("last_donation"),
                donor.get("email")
            ):
                continue

            donor_address = (
                donor.get("address") or ""
            ).lower()

            # Location match score: exact/contained address gets priority.
            location_score = 0

            if location:
                if location in donor_address or donor_address in location:
                    location_score = 2
                else:
                    # Compare individual location words for a softer match.
                    request_words = {
                        word for word in location.split()
                        if len(word) > 2
                    }
                    donor_words = {
                        word for word in donor_address.split()
                        if len(word) > 2
                    }
                    if request_words.intersection(donor_words):
                        location_score = 1

            valid.append({
                "record": (
                    donor.get("name", ""),
                    donor.get("blood_group", ""),
                    donor.get("phone", ""),
                    donor.get("address", ""),
                    donor.get("availability", "Unavailable"),
                    donor.get("last_donation")
                ),
                "group_rank": group_rank,
                "location_score": location_score
            })

    # First: location relevance, then BFS compatibility rank.
    valid.sort(
        key=lambda item: (
            -item["location_score"],
            item["group_rank"]
        )
    )

    donors = [item["record"] for item in valid]

    return render_template(
        "matched_donors.html",
        donors=donors,
        blood_group=blood,
        type=req_type,
        compatible_groups=compatible_groups
    )


# ============================================================
# ADD BLOOD REQUEST
# ============================================================

@app.route(
    "/add_blood_request",
    methods=["POST"]
)
def create_blood_request():

    # Both donors and admins can create a blood request.
    # Admin access is useful for demonstration/testing of the
    # Priority Queue and Deque without requiring a donor login.
    if "user" not in session and "admin" not in session:
        return redirect(
            "/login"
        )

    patient_name = request.form.get(
        "patient_name",
        ""
    ).strip()

    blood_group = request.form.get(
        "blood_group",
        ""
    ).strip()

    priority = request.form.get(
        "priority",
        "Normal"
    )

    # Patient location is saved for the Admin Location button.
    location = request.form.get(
        "location",
        ""
    ).strip()

    valid_blood_groups = [
        "A+",
        "A-",
        "B+",
        "B-",
        "AB+",
        "AB-",
        "O+",
        "O-"
    ]

    valid_priorities = [
        "Critical",
        "High",
        "Normal"
    ]

    if (
        not patient_name
        or blood_group not in valid_blood_groups
        or priority not in valid_priorities
    ):
        flash(
            "Please enter valid patient, blood group and priority."
        )
        return redirect(
            "/request"
        )

    request_date = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    conn = sqlite3.connect(
        "database/database.db"
    )

    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO blood_requests(
            patient_name,
            blood_group,
            priority,
            request_date,
            status,
            location
        )
        VALUES(
            ?, ?, ?, ?, ?, ?
        )
    """, (
        patient_name,
        blood_group,
        priority,
        request_date,
        "Pending",
        location
    ))

    request_id = cursor.lastrowid

    conn.commit()
    conn.close()

    # Min-Heap / Priority Queue insertion.
    add_blood_request(
        request_id,
        patient_name,
        blood_group,
        priority
    )

    # Deque event history insertion.
    record_request_event(
        request_id,
        "Created",
        patient_name,
        "Pending"
    )

    # After an admin creates a request, show the admin queue directly.
    if "admin" in session:
        return redirect("/blood_requests")

    return redirect(
        "/request"
    )


# ============================================================
# VIEW BLOOD REQUESTS
# ============================================================

@app.route(
    "/blood_requests"
)
def blood_requests():

    if "admin" not in session:
        return redirect(
            "/admin_login"
        )

    load_pending_requests_into_queue()

    conn = sqlite3.connect(
        "database/database.db"
    )

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            patient_name,
            blood_group,
            priority,
            request_date,
            status,
            location
        FROM blood_requests
        ORDER BY
            CASE priority
                WHEN 'Critical' THEN 1
                WHEN 'High' THEN 2
                ELSE 3
            END,
            id DESC
    """)

    requests_data = cursor.fetchall()
    conn.close()

    return render_template(
        "blood_requests.html",
        requests=requests_data,
        queue_size=len(
            blood_request_queue
        ),
        request_history=list(request_history)[::-1]
    )


# ============================================================
# PROCESS NEXT BLOOD REQUEST
# ============================================================

@app.route(
    "/process_next_blood_request",
    methods=["POST"]
)
def process_next_blood_request():

    if "admin" not in session:
        return redirect(
            "/admin_login"
        )

    load_pending_requests_into_queue()
    next_request = get_next_blood_request()

    if next_request:
        (
            priority_number,
            request_id,
            patient_name,
            blood_group,
            priority
        ) = next_request

        conn = sqlite3.connect(
            "database/database.db"
        )

        cursor = conn.cursor()

        cursor.execute("""
            UPDATE blood_requests
            SET status='Processing'
            WHERE id=?
            AND status='Pending'
        """, (
            request_id,
        ))

        changed = cursor.rowcount
        conn.commit()
        conn.close()

        if changed:
            record_request_event(
                request_id,
                "Processing",
                patient_name,
                "Processing"
            )

    return redirect(
        "/blood_requests"
    )


# ============================================================
# COMPLETE BLOOD REQUEST
# ============================================================

@app.route(
    "/complete_blood_request/<int:request_id>",
    methods=["POST"]
)
def complete_blood_request(request_id):

    if "admin" not in session:
        return redirect(
            "/admin_login"
        )

    conn = sqlite3.connect(
        "database/database.db"
    )

    cursor = conn.cursor()

    cursor.execute("""
        SELECT patient_name
        FROM blood_requests
        WHERE id=?
    """, (
        request_id,
    ))

    row = cursor.fetchone()
    patient_name = row[0] if row else ""

    cursor.execute("""
        UPDATE blood_requests
        SET status='Completed'
        WHERE id=?
    """, (
        request_id,
    ))

    changed = cursor.rowcount
    conn.commit()
    conn.close()

    if changed:
        record_request_event(
            request_id,
            "Completed",
            patient_name,
            "Completed"
        )

    return redirect(
        "/blood_requests"
    )


# ============================================================
# DELETE BLOOD REQUEST
# ============================================================

@app.route(
    "/delete_blood_request/<int:request_id>",
    methods=["POST"]
)
def delete_blood_request(request_id):

    if "admin" not in session:
        return redirect(
            "/admin_login"
        )

    conn = sqlite3.connect(
        "database/database.db"
    )

    cursor = conn.cursor()

    cursor.execute("""
        SELECT patient_name, status
        FROM blood_requests
        WHERE id=?
    """, (
        request_id,
    ))

    row = cursor.fetchone()
    patient_name = row[0] if row else ""
    old_status = row[1] if row else "Deleted"

    cursor.execute("""
        DELETE FROM blood_requests
        WHERE id=?
    """, (
        request_id,
    ))

    changed = cursor.rowcount
    conn.commit()
    conn.close()

    if changed:
        record_request_event(
            request_id,
            "Deleted",
            patient_name,
            old_status
        )

    return redirect(
        "/blood_requests"
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        "/login"
    )


# ============================================================
# PROFILE
# ============================================================

@app.route("/profile")
def profile():

    if "user" not in session:

        return redirect(
            "/login"
        )


    conn = sqlite3.connect(
        "database/database.db"
    )

    cursor = conn.cursor()


    cursor.execute("""
        SELECT
            name,
            email,
            phone,
            address,
            blood_group,
            availability,
            coins,
            last_donation
        FROM donors
        WHERE email=?
    """, (
        session["user"],
    ))


    user = cursor.fetchone()

    conn.close()


    if not user:

        session.clear()

        return redirect(
            "/login"
        )


    conn = sqlite3.connect(
        "database/database.db"
    )

    cursor = conn.cursor()


    cursor.execute("""
        SELECT
            next_eligible
        FROM donors
        WHERE email=?
    """, (
        session["user"],
    ))


    data = cursor.fetchone()

    conn.close()


    next_date = (
        data[0]
        if data
        else None
    )


    days_left = None


    if next_date:

        try:

            next_obj = datetime.strptime(
                next_date,
                "%Y-%m-%d"
            )

            days_left = (
                next_obj - datetime.now()
            ).days


            if days_left < 0:

                days_left = 0

        except:

            days_left = None


    donation_history = donation_linked_list.find_by_donor_name(
        user[0]
    )

    return render_template(
        "profile.html",
        user=user,
        next_date=next_date,
        days_left=days_left,
        donation_history=donation_history
    )


# ============================================================
# DONORS - HASH TABLE LOOKUP
# ============================================================

@app.route("/donors")
def donors():

    # Hash Table provides fast in-memory donor retrieval.
    data = []

    for donor in donor_hash.values():
        data.append((
            donor.get("name", ""),
            donor.get("blood_group", ""),
            donor.get("phone", ""),
            donor.get("address", ""),
            donor.get("availability", "Unavailable")
        ))

    # Keep the page resilient if the in-memory index is empty.
    if not data:
        refresh_donor_hash()
        for donor in donor_hash.values():
            data.append((
                donor.get("name", ""),
                donor.get("blood_group", ""),
                donor.get("phone", ""),
                donor.get("address", ""),
                donor.get("availability", "Unavailable")
            ))

    return render_template(
        "donors.html",
        donors=data
    )


# ============================================================
# REQUEST
# ============================================================

@app.route("/request")
def request_page():

    return render_template(
        "request.html"
    )


# ============================================================
# EMERGENCY
# ============================================================

@app.route("/emergency")
def emergency():

    # A self-contained emergency request form.
    # This avoids depending on the existing emergency.html template
    # and makes the ADS Priority Queue demo easy to test.

    is_admin = "admin" in session
    is_user = "user" in session

    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">

        <title>Emergency Blood Request</title>

        <style>

            * {
                box-sizing: border-box;
            }

            body {
                margin: 0;
                font-family: Arial, sans-serif;
                background: #f3f6fb;
                color: #222;
            }

            .navbar {
                background: #dc3545;
                color: white;
                padding: 16px 24px;
                font-size: 21px;
                font-weight: bold;
            }

            .container {
                width: 92%;
                max-width: 680px;
                margin: 45px auto;
            }

            .card {
                background: white;
                padding: 30px;
                border-radius: 18px;
                box-shadow: 0 8px 25px rgba(0,0,0,0.10);
            }

            h1 {
                margin-top: 0;
                text-align: center;
                color: #dc3545;
            }

            .note {
                background: #fff3cd;
                color: #664d03;
                padding: 12px;
                border-radius: 10px;
                margin-bottom: 22px;
            }

            label {
                display: block;
                margin-top: 16px;
                margin-bottom: 7px;
                font-weight: bold;
            }

            input,
            select {
                width: 100%;
                padding: 12px;
                border: 1px solid #cfd4da;
                border-radius: 9px;
                font-size: 15px;
            }

            button {
                width: 100%;
                margin-top: 25px;
                padding: 13px;
                border: 0;
                border-radius: 9px;
                background: #dc3545;
                color: white;
                font-size: 17px;
                font-weight: bold;
                cursor: pointer;
            }

            button:hover {
                background: #b02a37;
            }

            .links {
                display: flex;
                gap: 10px;
                flex-wrap: wrap;
                margin-top: 20px;
            }

            .links a {
                flex: 1;
                min-width: 180px;
                text-align: center;
                text-decoration: none;
                background: #212529;
                color: white;
                padding: 11px;
                border-radius: 8px;
            }

            .maps-btn {
                display: inline-block;
                margin-top: 10px;
                background: #0d6efd;
                color: white;
                padding: 9px 12px;
                border-radius: 8px;
                text-decoration: none;
                font-size: 14px;
            }

            .small {
                font-size: 13px;
                color: #666;
                margin-top: 6px;
            }

        </style>
    </head>

    <body>

        <div class="navbar">
            🩸 Blood Bank Management System
        </div>

        <div class="container">

            <div class="card">

                <h1>🚨 Emergency Blood Request</h1>

                <div class="note">
                    Emergency requests are inserted into the
                    <strong>Min-Heap / Priority Queue</strong>
                    and recorded in the <strong>Deque</strong>.
                </div>

                <form action="/add_blood_request" method="POST">

                    <label>Patient Name</label>

                    <input
                        type="text"
                        name="patient_name"
                        placeholder="Enter patient name"
                        required
                    >

                    <label>Blood Group</label>

                    <select name="blood_group" required>

                        <option value="">Select Blood Group</option>

                        <option value="A+">A+</option>
                        <option value="A-">A-</option>
                        <option value="B+">B+</option>
                        <option value="B-">B-</option>
                        <option value="AB+">AB+</option>
                        <option value="AB-">AB-</option>
                        <option value="O+">O+</option>
                        <option value="O-">O-</option>

                    </select>

                    <label>Priority</label>

                    <select name="priority" required>

                        <option value="Critical">Critical</option>
                        <option value="High">High</option>
                        <option value="Normal">Normal</option>

                    </select>

                    <label>Patient Location</label>

                    <input
                        type="text"
                        name="location"
                        id="patientLocation"
                        placeholder="Example: Tanuku"
                    >

                    <div class="small">
                        Location is stored with the blood request for Admin tracking.
                    </div>

                    <a
                        class="maps-btn"
                        id="mapsLink"
                        href="#"
                        target="_blank"
                        rel="noopener noreferrer"
                        style="display:none;"
                    >
                        🗺️ Open Location in Google Maps
                    </a>

                    <button type="submit">
                        🚨 Submit Emergency Blood Request
                    </button>

                </form>

                <div class="links">
                    <a href="/ads_dashboard">ADS Dashboard</a>
                    <a href="/blood_requests">Blood Requests</a>
                    <a href="/admin_home">Admin Home</a>
                </div>

            </div>

        </div>

        <script>
            const locationInput = document.getElementById("patientLocation");
            const mapsLink = document.getElementById("mapsLink");

            locationInput.addEventListener("input", function () {

                const value = locationInput.value.trim();

                if (!value) {
                    mapsLink.style.display = "none";
                    return;
                }

                mapsLink.href =
                    "https://www.google.com/maps/search/?api=1&query="
                    + encodeURIComponent(value);

                mapsLink.style.display = "inline-block";
            });
        </script>

    </body>
    </html>
    """


# ============================================================
# REGULAR
# ============================================================

@app.route("/regular")
def regular():

    return render_template(
        "regular.html"
    )


# ============================================================
# FEEDBACK
# ============================================================

@app.route("/feedback")
def feedback():

    return render_template(
        "feedback.html"
    )


# ============================================================
# SUBMIT FEEDBACK
# ============================================================

@app.route(
    "/submit_feedback",
    methods=["POST"]
)
def submit_feedback():

    if "user" not in session:

        return redirect(
            "/login"
        )


    message = request.form.get(
        "message",
        ""
    )


    image = request.files.get(
        "image"
    )


    filename = ""


    if image and image.filename:

        if not os.path.exists(
            "static/uploads"
        ):

            os.makedirs(
                "static/uploads"
            )


        filename = image.filename


        image.save(
            os.path.join(
                "static/uploads",
                filename
            )
        )


    today = datetime.now().strftime(
        "%Y-%m-%d"
    )


    conn = sqlite3.connect(
        "database/database.db"
    )

    cursor = conn.cursor()


    cursor.execute("""
        INSERT INTO feedback(
            user_email,
            message,
            image,
            date
        )
        VALUES(?, ?, ?, ?)
    """, (
        session["user"],
        message,
        filename,
        today
    ))


    conn.commit()
    conn.close()


    return redirect(
        "/feedback"
    )


# ============================================================
# TEMP DB FIX
# ============================================================

@app.route("/fix_db")
def fix_db():

    conn = sqlite3.connect(
        "database/database.db"
    )

    cursor = conn.cursor()


    try:

        cursor.execute(
            "ALTER TABLE donors ADD COLUMN next_eligible TEXT"
        )

        msg = (
            "Column added successfully ✅"
        )

    except Exception as e:

        msg = (
            f"Already exists or error: {e}"
        )


    conn.commit()
    conn.close()


    return msg


# ============================================================
# ADD REPORT COLUMN
# ============================================================

@app.route("/add_report_column")
def add_report_column():

    conn = sqlite3.connect(
        "database/database.db"
    )

    cursor = conn.cursor()


    try:

        cursor.execute(
            "ALTER TABLE donors ADD COLUMN report TEXT"
        )

        msg = (
            "Report column added successfully"
        )

    except Exception as e:

        msg = str(e)


    conn.commit()
    conn.close()


    return msg


# ============================================================
# ADMIN FEEDBACK PAGE
# ============================================================

@app.route("/admin_feedback")
def admin_feedback():

    if "admin" not in session:

        return redirect(
            "/admin_login"
        )


    conn = sqlite3.connect(
        "database/database.db"
    )

    cursor = conn.cursor()


    cursor.execute("""
        SELECT
            id,
            user_email,
            message,
            image,
            date
        FROM feedback
        ORDER BY id DESC
    """)


    feedbacks = cursor.fetchall()

    conn.close()


    return render_template(
        "admin_feedback.html",
        feedbacks=feedbacks
    )


# ============================================================
# DELETE FEEDBACK
# ============================================================

@app.route(
    "/delete_feedback/<int:feedback_id>",
    methods=["POST"]
)
def delete_feedback(feedback_id):

    if "admin" not in session:

        return redirect(
            "/admin_login"
        )


    conn = sqlite3.connect(
        "database/database.db"
    )

    cursor = conn.cursor()


    cursor.execute("""
        DELETE FROM feedback
        WHERE id=?
    """, (
        feedback_id,
    ))


    conn.commit()
    conn.close()


    return redirect(
        "/admin_feedback"
    )


# ============================================================
# RESET FEEDBACK TABLE
# ============================================================

@app.route(
    "/reset_feedback_table"
)
def reset_feedback_table():

    conn = sqlite3.connect(
        "database/database.db"
    )

    cursor = conn.cursor()


    cursor.execute(
        "DROP TABLE IF EXISTS feedback"
    )


    cursor.execute("""
        CREATE TABLE feedback(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT,
            message TEXT,
            image TEXT,
            date TEXT
        )
    """)


    conn.commit()
    conn.close()


    return (
        "Feedback table recreated successfully"
    )


# ============================================================
# ADMIN LOGOUT
# ============================================================

@app.route("/admin_logout")
def admin_logout():

    session.clear()

    return redirect("/")


# ============================================================
# ADD HEALTH REPORT
# ============================================================

@app.route(
    "/add_health_report",
    methods=["POST"]
)
def add_health_report():

    if "admin" not in session:

        return redirect(
            "/admin_login"
        )


    donor_name = request.form.get(
        "donor_name",
        ""
    ).strip()


    hemoglobin = request.form.get(
        "hemoglobin",
        ""
    ).strip()


    status = request.form.get(
        "status",
        "Pending"
    )


    if not donor_name or not hemoglobin:

        return redirect(
            "/admin_dashboard"
        )


    report_date = datetime.now().strftime(
        "%Y-%m-%d"
    )


    conn = sqlite3.connect(
        "database/database.db"
    )

    cursor = conn.cursor()


    cursor.execute("""
        SELECT phone
        FROM donors
        WHERE LOWER(name)=LOWER(?)
        LIMIT 1
    """, (
        donor_name,
    ))


    existing_donor = cursor.fetchone()


    if status == "Healthy":

        health_status = "Fit"

    elif status == "Not Eligible":

        health_status = "Unfit"

    else:

        health_status = "Pending"


    if existing_donor:

        donor_phone = existing_donor[0]


        cursor.execute("""
            UPDATE donors
            SET health_status=?,
                report=?
            WHERE phone=?
        """, (
            health_status,
            "Hemoglobin: "
            + hemoglobin
            + " g/dL",
            donor_phone
        ))


    else:

        new_phone = (
            "HEALTH-"
            + datetime.now().strftime(
                "%Y%m%d%H%M%S"
            )
        )


        cursor.execute("""
            INSERT INTO donors(
                name,
                phone,
                address,
                blood_group,
                availability,
                coins,
                health_status,
                report
            )
            VALUES(
                ?, ?, ?, ?, ?, ?, ?, ?
            )
        """, (
            donor_name,
            new_phone,
            "Not Provided",
            "Unknown",
            "Unavailable",
            0,
            health_status,
            "Hemoglobin: "
            + hemoglobin
            + " g/dL"
        ))


    cursor.execute("""
        INSERT INTO health_reports(
            donor_name,
            hemoglobin,
            report_date,
            status
        )
        VALUES(?, ?, ?, ?)
    """, (
        donor_name,
        hemoglobin,
        report_date,
        status
    ))


    conn.commit()
    conn.close()

    refresh_donor_hash()


    return redirect(
        "/health_dashboard"
    )


# ============================================================
# DELETE HEALTH REPORT
# ============================================================

@app.route(
    "/delete_health_report/<int:report_id>",
    methods=["POST"]
)
def delete_health_report(report_id):

    if "admin" not in session:

        return redirect(
            "/admin_login"
        )


    conn = sqlite3.connect(
        "database/database.db"
    )

    cursor = conn.cursor()


    cursor.execute("""
        DELETE FROM health_reports
        WHERE id=?
    """, (
        report_id,
    ))


    conn.commit()
    conn.close()


    return redirect(
        "/health_dashboard"
    )


# ============================================================
# VERIFY DONOR HEALTH
# ============================================================

@app.route(
    "/verify_health/<phone>/<status>",
    methods=["POST"]
)
def verify_health(phone, status):

    if "admin" not in session:

        return redirect(
            "/admin_login"
        )


    if status not in [
        "Fit",
        "Unfit"
    ]:

        return redirect(
            "/health_dashboard"
        )


    conn = sqlite3.connect(
        "database/database.db"
    )

    cursor = conn.cursor()


    cursor.execute("""
        UPDATE donors
        SET health_status=?
        WHERE phone=?
    """, (
        status,
        phone
    ))


    conn.commit()
    conn.close()

    refresh_donor_hash()


    return redirect(
        "/health_dashboard"
    )


# ============================================================
# DELETE DONOR
# ============================================================

@app.route(
    "/delete_donor/<phone>",
    methods=["POST"]
)
def delete_donor(phone):

    if "admin" not in session:

        return redirect(
            "/admin_login"
        )


    conn = sqlite3.connect(
        "database/database.db"
    )

    cursor = conn.cursor()


    cursor.execute("""
        DELETE FROM donors
        WHERE phone=?
    """, (
        phone,
    ))


    conn.commit()
    conn.close()

    refresh_donor_hash()


    return redirect(
        "/admin_dashboard"
    )


# ============================================================
# ADVANCED DATA STRUCTURES DEMO DASHBOARD
# ============================================================

def _admin_required():
    if "admin" not in session:
        return redirect("/admin_login")
    return None


def _normalized_hash_buckets():
    """Return clean blood-group bucket counts for the Hash Table pages."""
    blood_group_aliases = {
        "A+VE": "A+",
        "A-NEG": "A-",
        "B+VE": "B+",
        "B-NEG": "B-",
        "O+VE": "O+",
        "O-NEG": "O-",
        "AB+VE": "AB+",
        "AB-NEG": "AB-",
    }

    normalized = {}
    for group, records in donor_group_hash.items():
        raw_group = (group or "UNKNOWN").upper().strip()
        clean_group = blood_group_aliases.get(raw_group, raw_group)
        normalized[clean_group] = normalized.get(clean_group, 0) + len(records)

    display_order = ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"]
    result = {group: normalized.get(group, 0) for group in display_order}
    other_count = sum(
        count for group, count in normalized.items()
        if group not in display_order
    )
    if other_count:
        result["Other"] = other_count
    return result


def _page_shell(title, body_html):
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title}</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family:Arial,sans-serif; background:#f5f7fb; margin:0; color:#1f2937; }}
            .wrap {{ max-width:1100px; margin:30px auto; padding:20px; }}
            .card {{ background:white; border-radius:16px; padding:24px; margin-bottom:18px; box-shadow:0 4px 18px rgba(0,0,0,.08); }}
            h1 {{ color:#c62828; margin-top:0; }}
            h2 {{ margin-top:0; color:#111827; }}
            p {{ line-height:1.6; }}
            .value {{ font-size:30px; font-weight:700; color:#c62828; }}
            table {{ width:100%; border-collapse:collapse; }}
            th {{ background:#c62828; color:white; padding:12px; text-align:left; }}
            td {{ padding:12px; border-bottom:1px solid #e5e7eb; }}
            .actions {{ display:flex; gap:10px; flex-wrap:wrap; margin-top:18px; }}
            .btn {{ display:inline-block; text-decoration:none; color:white; background:#c62828; padding:10px 15px; border-radius:8px; font-weight:600; }}
            .btn.secondary {{ background:#475569; }}
            .btn.purple {{ background:#7c3aed; }}
            .btn.blue {{ background:#2563eb; }}
            .btn.green {{ background:#15803d; }}
            .btn.orange {{ background:#ea580c; }}
            pre {{ background:#f0f2f5; padding:14px; border-radius:10px; overflow:auto; }}
            .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:15px; }}
            .mini {{ cursor:default; transition:.2s; }}
            @media(max-width:700px) {{ .wrap{{padding:10px;}} }}
        </style>
    </head>
    <body>
    <div class="wrap">
        {body_html}
    </div>
    </body>
    </html>
    """


@app.route("/ads_dashboard")
def ads_dashboard():
    blocked = _admin_required()
    if blocked:
        return blocked

    refresh_donor_hash()
    load_request_history()
    load_donation_linked_list()
    load_pending_requests_into_queue()

    donation_count = donation_linked_list.size
    donor_count = len(donor_hash)
    buckets = _normalized_hash_buckets()
    bfs_demo = bfs_compatible_blood_groups("AB+")
    dfs_demo = dfs_compatible_blood_groups("AB+")

    cards = [
        ("Min-Heap / Priority Queue", str(len(blood_request_queue)),
         "Pending blood requests ordered by Critical → High → Normal.",
         "/ads/minheap", "blue"),
        ("Hash Table", str(donor_count),
         "Donors indexed for fast lookup by phone and blood group.",
         "/ads/hash", "green"),
        ("Deque", str(len(request_history)),
         "Latest request events retained in a fixed-size deque.",
         "/ads/deque", "orange"),
        ("Linked List", str(donation_count),
         "Donation history maintained as linked-list nodes.",
         "/ads/linkedlist", "purple"),
        ("Graph + BFS", "BFS", "Breadth-first compatibility traversal.",
         "/ads/bfs", "blue"),
        ("Graph + DFS", "DFS", "Depth-first compatibility traversal.",
         "/ads/dfs", "green"),
    ]

    card_html = []
    for title, value, desc, href, color in cards:
        card_html.append(f"""
        <a href="{href}" style="text-decoration:none;color:inherit;">
            <div class="card mini" style="border-left:6px solid #c62828;">
                <h2>{title}</h2>
                <div class="value">{value}</div>
                <p>{desc}</p>
                <strong style="color:#c62828;">Click to open →</strong>
            </div>
        </a>
        """)

    bucket_rows = "".join(
        f"<tr><td>{group}</td><td>{count}</td></tr>"
        for group, count in buckets.items()
    )

    body = f"""
        <h1>🩸 Advanced Data Structures Dashboard</h1>
        <p>Click any card below to open its dedicated ADS page.</p>

        <div class="grid">
            {''.join(card_html)}
        </div>

        <div class="card">
            <h2>Hash Table Bucket Summary</h2>
            <table>
                <tr><th>Blood Group</th><th>Donor Count</th></tr>
                {bucket_rows}
            </table>
        </div>

        <div class="actions">
            <a class="btn" href="/emergency">🚨 Create Emergency Request</a>
            <a class="btn secondary" href="/admin_dashboard">Admin Dashboard</a>
            <a class="btn secondary" href="/admin_home">Admin Home</a>
        </div>
    """
    return _page_shell("ADS Dashboard - Blood Bank", body)


@app.route("/ads/minheap")
def ads_minheap():
    blocked = _admin_required()
    if blocked:
        return blocked

    load_pending_requests_into_queue()
    items = sorted(blood_request_queue)
    rows = "".join(
        f"<tr><td>{idx}</td><td>{item[1]}</td><td>{item[2]}</td><td>{item[3]}</td><td>{item[4]}</td></tr>"
        for idx, item in enumerate(items, 1)
    )
    if not rows:
        rows = "<tr><td colspan='5'>No pending requests.</td></tr>"

    body = f"""
        <h1>⛓️ Min-Heap / Priority Queue</h1>
        <div class="card">
            <div class="value">{len(items)}</div>
            <p>Pending requests are ordered by priority: Critical → High → Normal.</p>
            <table>
                <tr><th>S.No</th><th>Request ID</th><th>Patient</th><th>Blood Group</th><th>Priority</th></tr>
                {rows}
            </table>
        </div>
        <div class="actions">
            <a class="btn" href="/blood_requests">Open Blood Requests</a>
            <a class="btn secondary" href="/ads_dashboard">Back to ADS Dashboard</a>
        </div>
    """
    return _page_shell("Min-Heap - ADS", body)


@app.route("/ads/hash")
def ads_hash():
    blocked = _admin_required()
    if blocked:
        return blocked

    refresh_donor_hash()
    buckets = _normalized_hash_buckets()

    rows = "".join(
        f"<tr><td>{group}</td><td>{count}</td></tr>"
        for group, count in buckets.items()
    )

    lookup_examples = "".join(
        f"<li><strong>{phone}</strong> → {donor.get('name','')} ({donor.get('blood_group','')})</li>"
        for phone, donor in list(donor_hash.items())[:10]
    )
    if not lookup_examples:
        lookup_examples = "<li>No donor records indexed.</li>"

    body = f"""
        <h1>🔑 Hash Table</h1>
        <div class="card">
            <div class="value">{len(donor_hash)}</div>
            <p>Donors are indexed by phone number for average O(1) lookup. A second hash index groups donors by blood group.</p>
        </div>
        <div class="card">
            <h2>Blood Group Buckets</h2>
            <table><tr><th>Blood Group</th><th>Donor Count</th></tr>{rows}</table>
        </div>
        <div class="card">
            <h2>Sample Phone → Donor Index</h2>
            <ul>{lookup_examples}</ul>
        </div>
        <div class="actions">
            <a class="btn green" href="/donors">Open Donors</a>
            <a class="btn secondary" href="/ads_dashboard">Back to ADS Dashboard</a>
        </div>
    """
    return _page_shell("Hash Table - ADS", body)


@app.route("/ads/deque")
def ads_deque():
    blocked = _admin_required()
    if blocked:
        return blocked

    load_request_history()

    # The Deque remains the underlying ADS structure.
    # For a cleaner admin view, rows are sorted by patient name A-Z.
    events = list(request_history)

    events.sort(
        key=lambda item: (
            (item.get("patient_name") or "").strip().lower(),
            -(item.get("request_id") or 0),
            item.get("time") or ""
        )
    )

    rows = ""

    for serial_no, item in enumerate(events, 1):

        event_id = item.get("event_id", "")
        request_id = item.get("request_id", "")
        event = item.get("event", "")
        patient_name = item.get("patient_name", "")
        status = item.get("status", "")
        event_time = item.get("time", "")

        rows += f"""
        <tr>
            <td class="serial">{serial_no}</td>
            <td>{request_id}</td>
            <td class="patient-name">{patient_name}</td>
            <td>{event}</td>
            <td>{status}</td>
            <td>{event_time}</td>
            <td>
                <form method="POST"
                      action="/ads/deque/delete/{event_id}"
                      onsubmit="return confirm('Delete this request history event?');"
                      style="margin:0;">
                    <button type="submit" class="delete-btn">
                        🗑️ Delete
                    </button>
                </form>
            </td>
        </tr>
        """

    if not rows:
        rows = """
        <tr>
            <td colspan="7" class="empty">
                No request events yet.
            </td>
        </tr>
        """

    body = f"""
        <h1>↔️ Deque - Request History</h1>

        <div class="card">

            <div class="top-info">

                <div>
                    <div class="value">{len(events)}</div>
                    <p>
                        Latest 50 request events are maintained
                        using a fixed-size Deque.
                    </p>
                </div>

                <div class="sort-info">
                    🔤 Sorted by Patient Name (A → Z)
                </div>

            </div>

            <div class="table-wrap">

                <table>

                    <thead>

                        <tr>
                            <th>S.No</th>
                            <th>Request ID</th>
                            <th>Patient Name</th>
                            <th>Event</th>
                            <th>Status</th>
                            <th>Time</th>
                            <th>Action</th>
                        </tr>

                    </thead>

                    <tbody>
                        {rows}
                    </tbody>

                </table>

            </div>

        </div>


        <div class="actions">

            <a class="btn orange"
               href="/blood_requests">
                Open Blood Requests
            </a>

            <a class="btn secondary"
               href="/ads_dashboard">
                Back to ADS Dashboard
            </a>

            <a class="btn blue"
               href="/admin_dashboard">
                Admin Dashboard
            </a>

        </div>


        <style>

            .top-info {{
                display:flex;
                justify-content:space-between;
                align-items:center;
                gap:20px;
                flex-wrap:wrap;
                margin-bottom:20px;
            }}

            .sort-info {{
                background:#eff6ff;
                color:#1d4ed8;
                border:1px solid #bfdbfe;
                padding:10px 15px;
                border-radius:10px;
                font-weight:700;
            }}

            .table-wrap {{
                overflow-x:auto;
            }}

            table {{
                width:100%;
                border-collapse:collapse;
                min-width:980px;
            }}

            th {{
                background:#c62828;
                color:white;
                padding:13px;
                text-align:center;
                white-space:nowrap;
            }}

            td {{
                padding:12px;
                border-bottom:1px solid #e5e7eb;
                text-align:left;
            }}

            tbody tr:hover {{
                background:#fff7f7;
            }}

            .serial {{
                text-align:center;
                font-weight:700;
                color:#111827;
                width:70px;
            }}

            .patient-name {{
                font-weight:700;
                color:#111827;
                min-width:160px;
            }}

            .delete-btn {{
                background:#dc2626;
                color:white;
                border:none;
                border-radius:8px;
                padding:8px 12px;
                font-weight:700;
                cursor:pointer;
            }}

            .delete-btn:hover {{
                background:#b91c1c;
            }}

            .empty {{
                text-align:center;
                color:#64748b;
                padding:25px;
            }}

        </style>
    """

    return _page_shell("Deque - ADS", body)


@app.route("/ads/deque/delete/<int:event_id>", methods=["POST"])
def ads_deque_delete_event(event_id):
    blocked = _admin_required()
    if blocked:
        return blocked

    delete_request_event(event_id)

    return redirect("/ads/deque")
@app.route("/ads/linkedlist")
def ads_linkedlist():
    blocked = _admin_required()
    if blocked:
        return blocked

    load_donation_linked_list()
    records = list(reversed(donation_linked_list.to_list()))
    rows = "".join(
        f"<tr><td>{serial_no}</td><td>{item['donor_name']}</td><td>{item['date']}</td><td>{item['status']}</td></tr>"
        for serial_no, item in enumerate(records, 1)
    )
    if not rows:
        rows = "<tr><td colspan='4'>No donation records yet.</td></tr>"

    body = f"""
        <h1>🔗 Linked List - Donation History</h1>
        <div class="card">
            <div class="value">{donation_linked_list.size}</div>
            <p>Each donation record is stored as a node linked to the next donation record.</p>
            <table>
                <tr><th>S.No</th><th>Donor</th><th>Date</th><th>Status</th></tr>
                {rows}
            </table>
        </div>
        <div class="actions">
            <a class="btn purple" href="/donation_history">Open Donation History</a>
            <a class="btn secondary" href="/ads_dashboard">Back to ADS Dashboard</a>
        </div>
    """
    return _page_shell("Linked List - ADS", body)


@app.route("/ads/bfs")
def ads_bfs():
    blocked = _admin_required()
    if blocked:
        return blocked

    traversal = bfs_compatible_blood_groups("AB+")
    body = f"""
        <h1>🌐 Graph + BFS</h1>
        <div class="card">
            <h2>Breadth-First Search</h2>
            <p>BFS starts from <strong>AB+</strong> and visits reachable compatible blood groups level by level.</p>
            <pre>{' → '.join(traversal)}</pre>
        </div>
        <div class="card">
            <h2>Algorithm</h2>
            <p>Queue is used to visit the current node first, then its adjacent compatibility nodes.</p>
        </div>
        <div class="actions">
            <a class="btn blue" href="/ads/dfs">Open DFS</a>
            <a class="btn secondary" href="/ads_dashboard">Back to ADS Dashboard</a>
        </div>
    """
    return _page_shell("BFS - ADS", body)


@app.route("/ads/dfs")
def ads_dfs():
    blocked = _admin_required()
    if blocked:
        return blocked

    traversal = dfs_compatible_blood_groups("AB+")
    body = f"""
        <h1>🌐 Graph + DFS</h1>
        <div class="card">
            <h2>Depth-First Search</h2>
            <p>DFS starts from <strong>AB+</strong> and explores one compatibility path deeply before backtracking.</p>
            <pre>{' → '.join(traversal)}</pre>
        </div>
        <div class="card">
            <h2>Algorithm</h2>
            <p>DFS uses recursive traversal to explore neighbouring blood-group nodes before backtracking.</p>
        </div>
        <div class="actions">
            <a class="btn green" href="/ads/bfs">Open BFS</a>
            <a class="btn secondary" href="/ads_dashboard">Back to ADS Dashboard</a>
        </div>
    """
    return _page_shell("DFS - ADS", body)


# ============================================================
# DONATION HISTORY - LINKED LIST VIEW
# ============================================================

# S.No values are generated from the displayed order; database IDs are not used as serial numbers.
@app.route("/donation_history")
def donation_history():

    if "admin" not in session:
        return redirect(
            "/admin_login"
        )

    load_donation_linked_list()
    records = donation_linked_list.to_list()

    rows = []
    for serial_no, item in enumerate(reversed(records), 1):
        rows.append(
            f"<tr><td>{serial_no}</td><td>{item['donor_name']}</td>"
            f"<td>{item['date']}</td><td>{item['status']}</td></tr>"
        )

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Donation History</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family:Arial,sans-serif; background:#f7f7f7; padding:25px; }
            .box { max-width:950px; margin:auto; background:white; padding:25px; border-radius:14px; box-shadow:0 4px 15px rgba(0,0,0,.08); }
            table { width:100%; border-collapse:collapse; }
            th,td { padding:10px; border-bottom:1px solid #ddd; text-align:left; }
            th { background:#c62828; color:white; }
            a { text-decoration:none; color:#fff; background:#c62828; padding:10px 15px; border-radius:8px; }
        </style>
    </head>
    <body>
        <div class="box">
            <h2>🩸 Donation History (Linked List)</h2>
            <table>
                <tr><th>S.No</th><th>Donor</th><th>Date</th><th>Status</th></tr>
                __ROWS__
            </table>
            <p style="margin-top:20px;"><a href="/ads/linkedlist">← Back to Linked List</a></p>
        </div>
    </body>
    </html>
    """

    html = html.replace("__ROWS__", "".join(rows))
    return html


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    # Rebuild all in-memory ADS structures before starting Flask.
    refresh_donor_hash()
    load_request_history()
    load_donation_linked_list()
    load_pending_requests_into_queue()

    app.run(
        host="0.0.0.0",
        port=5000
    )