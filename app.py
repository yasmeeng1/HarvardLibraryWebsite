import os
import datetime
import sqlite3

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for, jsonify
from functools import wraps
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__)
app.secret_key = "secret_key"

# Set up the database connection
db = SQL("sqlite:///bookings.db")

# Define the rooms list globally so it's accessible in all routes
rooms = [
    {"id": 1, "name": "Cabot LL10", "description": "Group Study Room -- Lower Level",
        "image": "https://library.harvard.edu/sites/default/files/spacefinder/rooms/2018-04/LL10%20Cabot%20Inside%20view.jpg"},
    {"id": 2, "name": "Cabot L212", "description": "Group Study Room -- Second Floor.",
        "image": "https://library.harvard.edu/sites/default/files/spacefinder/rooms/2018-04/Cabot%20L205%20-%20Inside%20View.jpg"},
    {"id": 3, "name": "Cabot L107", "description": "Video Conference Room -- Main Level.",
        "image": "https://library.harvard.edu/sites/default/files/spacefinder/rooms/2018-03/Cabot-L107-VideoConference-01.jpg"},
    {"id": 4, "name": "Cabot L214", "description": "Group Study Room -- Second Floor",
        "image": "https://library.harvard.edu/sites/default/files/spacefinder/rooms/2018-04/Cabot%20L214%20-%20Inside%20View%201.jpg"},
    {"id": 5, "name": "Cabot LL06", "description": "Group Study Room -- Lower Level",
        "image": "https://library.harvard.edu/sites/default/files/spacefinder/rooms/2018-04/L006%20inside.jpg"},
    {"id": 6, "name": "Cabot L210", "description": "Group Study Room -- Second Floor",
        "image": "https://library.harvard.edu/sites/default/files/spacefinder/rooms/2018-04/Cabot%20L210%20-%20Outside%20View.jpg"},
]

# Define the friend study location spaces globally so they are easilly accessible
study_locations_list = ["Colorful Couches", "Dinosaur Eggs",
                        "Lower Study Room", "Main Study Room", "Table Nooks", "Little Nooks"]


@app.route("/")
def index():
    if not session.get("user_id"):
        return redirect("/login")
    return render_template("home.html")


def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """Helper function to escape special characters for HTML display."""
        for old, new in [(";", "&semi;"), ("<", "&lt;"), (">", "&gt;"), ("&", "&amp;")]:
            s = s.replace(old, new)
        return s

    # Escape the message
    message = escape(message)

    # Render the template with the error message
    return render_template("apology.html", top=code, bottom=message), code

# make it clear for when logins are needed


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            flash("You must be logged in to access this page.", "danger")
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

# clear sessions so users can logout


@app.route("/logout")
def logout():
    """Log user out"""
    session.clear()
    flash("You have been logged out.", "info")
    return redirect("/")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    # Handle GET requests
    if request.method == "GET":
        return render_template("register.html")
    else:
        # handle POST requests
        username = request.form.get("username")
        if not username:
            return apology("Need to provide a username!!")

        password = request.form.get("password")
        if not password:
            return apology("Need to provide a password!!")

        confirmation = request.form.get("confirmation")
        if not confirmation:
            return apology("Need to provide a confirmation!!")

        name = request.form.get("name")
        if not name:
            return apology("Need to provide a name!!")

        if password != confirmation:
            return apology("Your password and confirmation don't match")

        # generat ea hashed password if users properly follwo the registration processs
        # finance pset was referenced frequently for this
        hashed_password = generate_password_hash(password)

        try:
            db.execute("INSERT INTO users (username, hash, name) VALUES (:username, :hash, :name)",
                       username=username, hash=hashed_password, name=name)
        except ValueError:
            return apology("That username already exists :( )")
        return redirect("/")

# return the stuyd page


@app.route("/music")
def music():
    return render_template("study.html")

# returnt he roombook page


@app.route("/roombook")
@login_required
def roombook():
    return render_template("roombook.html", rooms=rooms)

# Reserving rooms


@app.route('/reserve')
@login_required
def reserve():
    # Confirm the room exists
    room_id = request.args.get('room_id', type=int)
    room = next((room for room in rooms if room["id"] == room_id), None)
    if room is None:
        return "Room not found", 404

    # Get current date and time for comparison
    current_time = datetime.datetime.now()
    return render_template('reserve.html', room=room, current_time=current_time)

# Check that a room is actually available


def check_room_availability(room_id, booking_date, start_time, end_time):
    try:
        # Query existing bookings for this room on the specified date
        overlapping_bookings = db.execute("""
            SELECT COUNT(*) as count
            FROM bookings
            WHERE room_id = ?
            AND booking_date = ?
            AND (
                (start_time <= ? AND end_time > ?) OR
                (start_time < ? AND end_time >= ?) OR
                (? <= start_time AND ? >= end_time)
            )
        """,
                                          # 3 cases (existing booking overlaps start, overlaps end, or its existing compelteely)
                                          room_id,
                                          booking_date,
                                          end_time, start_time,
                                          end_time, end_time,
                                          start_time, end_time
                                          )

        # Room is available if there are no overlapping bookings
        return overlapping_bookings[0]["count"] == 0

    except Exception as e:
        print(f"Error checking availability: {e}")
        return False

# Filter through rooms to see if user input aligns with rooms that are alr eadytaken


@app.route("/filter", methods=["GET"])
def filter_rooms():
    test_bookings = db.execute("SELECT * FROM bookings")
    print("All bookings in database:", test_bookings)
    filter_date = request.args.get("filter_date")
    filter_start_time = request.args.get("filter_start_time")
    filter_end_time = request.args.get("filter_end_time")

    print(f"Filtering for date: {filter_date}, start: {filter_start_time}, end: {filter_end_time}")

    if not all([filter_date, filter_start_time, filter_end_time]):
        return render_template("roombook.html", rooms=rooms)

    # First check which rooms have bookings that overlap with the requested time
    booked_rooms = db.execute("""
        SELECT DISTINCT room_id
        FROM bookings
        WHERE booking_date = ?
        AND NOT (
            end_time <= ? OR  /* Existing booking ends before requested start */
            start_time >= ?   /* Existing booking starts after requested end */
        )
    """, filter_date, filter_start_time, filter_end_time)

    print("Database query results:", booked_rooms)  # Debug print

    # Convert to set of room IDs that are booked
    booked_room_ids = {booking['room_id'] for booking in booked_rooms}
    print(f"Booked room IDs: {booked_room_ids}")

    # Filter out the booked rooms
    available_rooms = [room for room in rooms if room['id'] not in booked_room_ids]
    print(f"Available rooms: {[room['name'] for room in available_rooms]}")

    # Return only the available rooms to the template via the avialbale_rooms variable
    return render_template("roombook.html", available_rooms=available_rooms)


@app.route("/leaderboard")
def leaderboard():
    # Get the leaderboard data from database
    leaderboard_data = db.execute("""
        SELECT name, SUM(assignments) AS assignments, SUM(time) AS time
        FROM study_sessions
        GROUP BY name
        ORDER BY assignments DESC, time DESC
    """)
    return render_template("leaderboard.html", leaderboard=leaderboard_data)


# Allow users to submit how much work they ve done to the leaderboard
@app.route("/submit-progress", methods=["POST"])
def submit_progress():
    name = request.form.get("name")
    assignments = request.form.get("assignments", type=int)
    time = request.form.get("time", type=int)

    if not name or not assignments or not time:
        flash("All fields are required.", "danger")
        return redirect("/leaderboard")

    # Insert progress into the database
    db.execute("""
        INSERT INTO study_sessions (name, assignments, time)
        VALUES (:name, :assignments, :time)
    """, name=name, assignments=assignments, time=time)

    flash("Progress submitted successfully!", "success")
    return redirect("/leaderboard")


# Database initialization
def init_db():
    # Make a table to keep track of the diff bookings
    db.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            room_id INTEGER NOT NULL,
            booking_date DATE NOT NULL,
            start_time TIME NOT NULL,
            end_time TIME NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # make a table of users
    db.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # make a table to keep track of the studying
    db.execute('''
        CREATE TABLE IF NOT EXISTS study_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            assignments INTEGER NOT NULL,
            time INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')


# Initialize the database when the app starts
init_db()


def get_db():
    conn = sqlite3.connect('bookings.db')
    conn.row_factory = sqlite3.Row  # This enables name-based access to columns
    return conn

# Tell users if their room was actually succesffult booked


@app.route("/reserve", methods=["GET"])
def reserve_room():
    room_id = request.args.get("room_id")

    # Implement room reservation logic (pseudo-code)
    reserve_success = reserve_room_by_id(room_id)

    if reserve_success:
        flash("Room reserved successfully!", "success")
    else:
        flash("Failed to reserve room. Please try again.", "danger")

    return redirect(url_for("index"))


@app.route('/room/<int:room_id>')
def room_detail(room_id):
    conn = get_db()
    c = conn.cursor()

    # Get room details usung the room id
    c.execute('SELECT * FROM rooms WHERE id = ?', (room_id,))
    room = c.fetchone()
    conn.close()

    # make sure the room is found
    if room is None:
        return "Room not found", 404

    # get the current date and time
    current_time = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    return render_template('reserve_room.html',
                           room={'id': room['id'],
                                 'name': room['name'],
                                 'description': room['description'],
                                 'image': room['image']},
                           current_time=current_time)


@app.route('/book', methods=['POST'])
def book_room():
    # book.a room basedo n the rpovided bookign details
    try:
        room_id = request.form.get('room_id')
        booking_date = request.form.get('booking_date')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')

        # Input validation
        if not all([room_id, booking_date, start_time, end_time]):
            return jsonify({'success': False, 'message': 'All fields are required'})

        conn = get_db()
        c = conn.cursor()

        # Check for booking conflicts
        c.execute('''
            SELECT * FROM bookings
            WHERE room_id = ?
            AND booking_date = ?
            AND (
                (start_time <= ? AND end_time > ?) OR
                (start_time < ? AND end_time >= ?) OR
                (start_time >= ? AND end_time <= ?)
            )
        ''', (room_id, booking_date, start_time, start_time,
              end_time, end_time, start_time, end_time))

        if c.fetchone() is not None:
            conn.close()
            return jsonify({'success': False, 'message': 'Time slot already booked'})

        # Insert new booking intot he bookings database
        c.execute('''
            INSERT INTO bookings (room_id, booking_date, start_time, end_time)
            VALUES (?, ?, ?, ?)
        ''', (room_id, booking_date, start_time, end_time))

        booking_id = c.lastrowid
        conn.commit()

        # Get the inserted booking
        c.execute('SELECT * FROM bookings WHERE id = ?', (booking_id,))
        booking = c.fetchone()
        conn.close()

        # return the booking details as JSON
        return jsonify({
            'success': True,
            'booking': {
                'id': booking['id'],
                'room_id': booking['room_id'],
                'booking_date': booking['booking_date'],
                'start_time': booking['start_time'],
                'end_time': booking['end_time']
            }
        })

    except Exception as e:
        if 'conn' in locals():
            conn.close()
        return jsonify({'success': False, 'message': str(e)})


@app.route('/room/<int:room_id>/bookings')
def room_bookings(room_id):
    # get all the bookings for a specific froom
    conn = get_db()
    c = conn.cursor()

    c.execute('''
        SELECT * FROM bookings
        WHERE room_id = ?
        ORDER BY booking_date, start_time
    ''', (room_id,))

    bookings = c.fetchall()
    conn.close()

    # reurn the bookings as json
    return jsonify({
        'bookings': [{
            'id': booking['id'],
            'booking_date': booking['booking_date'],
            'start_time': booking['start_time'],
            'end_time': booking['end_time']
        } for booking in bookings]
    })


if __name__ == '__main__':
    app.run(debug=True)


@app.route("/friendtracker", methods=["GET", "POST"])
@login_required
def friend_tracker():
    if request.method == "POST":
        location = request.form.get("study_locations")
        locked_in = request.form.get("locked_in_levels")
        duration = request.form.get("time_studying")

        # Current datetime
        current_time = datetime.datetime.now()
        time_to_add = datetime.timedelta(hours=int(duration[:2]), minutes=int(duration[-2:]))
        end_time = current_time + time_to_add

        # get the current user's name
        name = db.execute(
            "SELECT name FROM users WHERE id = ?", session["user_id"]
        )[0]["name"]

        # Save the user's study location
        try:
            # Delete existing entries for the user_id
            try:
                db.execute(
                    "DELETE FROM friends WHERE user_id = :user_id",
                    user_id=session["user_id"]
                )
            except:
                pass

            # Insert the user's study location into the database
            db.execute("""
                INSERT INTO friends (user_id, location, end_time, locked_in, name)
                VALUES (:user_id, :location, :end_time, :locked_in, :name)
                """, user_id=session["user_id"], location=str(location), end_time=str(end_time), locked_in=str(locked_in), name=str(name))

            flash("Study location saved successfully!", "success")
        except Exception as e:
            flash("An error occurred while saving your location. Please try again.", "danger")

        return redirect("/friendtracker")

    # if the user used the "GET" method
    else:
        friends = []

        for location in study_locations_list:
            location_friends = db.execute(
                "SELECT * FROM friends WHERE location = ?", location
            )
            # Filter friends and retain only "name" and "locked_in"
            filtered_friends = []
            for friend in location_friends:
                # Keep only friends whose study time hasn't ended
                if datetime.datetime.strptime(friend["end_time"], "%Y-%m-%d %H:%M:%S.%f") >= datetime.datetime.now():
                    filtered_friends.append(
                        {"name": friend["name"], "locked_in": friend["locked_in"]})
                else:
                    try:
                        # delete any friend study records that are timed out
                        db.execute(
                            "DELETE FROM friends WHERE id = :friend_id",
                            friend_id=friend["id"]
                        )
                    except Exception as e:
                        pass
            friends.append(filtered_friends)

        return render_template("friendtracker.html", study_locations_list=study_locations_list, location_friends=friends)


@app.route("/foodspots", methods=["GET"])
@login_required
def food_spots():
    all_restaurants = db.execute("SELECT * FROM restaurants")
    restaurants = []

    # Render the results
    return render_template("foodspots.html", all_restaurants=all_restaurants, restaurants=restaurants)


@app.route("/search", methods=["GET"])
@login_required
def search():
    # Get the search query from the form
    all_restaurants = []

    search = request.args.get("query")
    if not search:
        flash("Please enter a search term.", "danger")
        return redirect("/foodspots")

    # Query the database to find matching restaurants
    restaurants = db.execute("""
        SELECT *
        FROM restaurants
        WHERE name LIKE :search OR food_options LIKE :search
    """, search=f"%{search}%")

    # Check if any restaurants were found
    if not restaurants and search:
        flash("No matching restaurants found.", "danger")

    # Render the template with the search results
    return render_template("foodspots.html", all_restaurants=all_restaurants, restaurants=restaurants)


if __name__ == "__main__":
    app.run(debug=True)
