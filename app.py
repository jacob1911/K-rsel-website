# from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, render_template, request, redirect, url_for, flash, session,jsonify, send_file
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests
import os
import secrets
import pythonextensions.send_email as SMTP
import pythonextensions.blackjack as bj
import pythonextensions.pathfinder as pf
from pythonextensions.models import db, ClubLoginToken, Club, Race, Carpool, Reservation, Comment
from PIL import Image
from io import BytesIO

# import send_email_2 as SMTP2

load_dotenv('environ.env')
app = Flask(__name__)
CORS(app, resources={r"/beregn_ruter/*": {"origins": "https://steinthal.dk"}})
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///carpool.db'
# app.run(host="0.0.0.0", port=5000, debug=True)
token_cleanup_counter = 0
PASSWORD_ADMIN = os.getenv("PASSWORD_ADMIN")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")
GMAIL = os.getenv("GMAIL")
db.init_app(app)

app.secret_key = "your_secret_key_here123"  # Needed for flash messages and session

with app.app_context():
   
    db.create_all()
    
    


def generate_token(club_id, hours_valid=24):
    token = secrets.token_urlsafe(32)  # cryptographically secure random token
    expires_at = datetime.utcnow() + timedelta(hours=hours_valid)
    new_token = ClubLoginToken(token=token, club_id=club_id, expires_at=expires_at)
    db.session.add(new_token)
    db.session.commit()
    return token

# Homepage: List all available carpools
@app.route('/')
def home():
    session.pop("admin_login", None) 
    session.pop("club_id", None)  # Clear any previous club session
    session.pop("club_name", None)  # Clear any previous club session
    # Default coordinates (center of map)
    latitude = 55.6761  # Default latitude for Denmark
    longitude = 12.5683  # Default longitude for Denmark

    club_name = request.args.get('club', None)
    is_club_page = True if club_name else False

    

    if club_name:
        active_carpools = Carpool.query.join(Club).filter(Club.name == club_name, Carpool.departure_time >= datetime.utcnow()).all()
    else:
        active_carpools = Carpool.query.filter(Carpool.departure_time >= datetime.utcnow(), Carpool.club_level==0).all()

    # Get all clubs for the dropdown
    clubs = Club.query.all()

    return render_template('home.html', carpools=active_carpools, clubs=clubs, latitude=latitude, longitude=longitude, selected_club=club_name, is_club_page=is_club_page)


# Route to show login page
@app.route("/club-login", methods=["GET", "POST"])
def club_login():
    clubs = Club.query.all()  # Get all clubs for the dropdown

    if request.method == "POST":
        club_id = request.form.get("club_id")
        password = request.form.get("password")

        club = Club.query.filter_by(id=club_id).first()
        if club and club.password == password:
            # Save logged-in club in session
            session["club_id"] = club.id
            session["club_name"] = club.name
            flash(f"Welcome, {club.name}!", "success")
            print("Logged in")
            return redirect(url_for("club_dashboard", club_name=club.name))  # Replace with your club page
        else:
            flash("Invalid club or password.", "danger")
            print("Invalid ")
            return redirect(url_for("club_login"))

    return render_template("club_login.html", clubs=clubs)

@app.route("/generate-token", methods=["POST"])
def generate_token_route():
    race_id = request.form.get("race_id")  # e.g. /?race_id=14 or any path you want
    print("got:", race_id)

    if "club_id" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("club_login"))

    # Generate a token valid for 24 hours
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=24)

    new_token = ClubLoginToken(
        token=token,
        club_id=session["club_id"],
        expires_at=expires_at
    )
    db.session.add(new_token)
    
    # Cleanup
    global token_cleanup_counter
    token_cleanup_counter +=1 
    if (token_cleanup_counter % 10 == 0):
        expired = ClubLoginToken.query.filter(ClubLoginToken.expires_at < datetime.utcnow()).all()
        print(f"Found {len(expired)} expired tokens")
        for token in expired:
            db.session.delete(token)
        print(f"----Deleted {len(expired)} expired tokens----")

    db.session.commit()

    # Build the shareable link
    link = url_for("club_login_token", token=token, _external=True)

    if race_id:
        flash(f"{link}?race_id={race_id}", "success")
        return redirect(url_for("club_dashboard", club_name=session["club_name"], race_id=race_id))
    else:
        redirect(url_for("club_dashboard", club_name=session["club_name"]))

@app.route("/club-login-token/<token>")
def club_login_token(token):
    # Parse query parameters from URL
    race_id = request.args.get("race_id")  # e.g. /?race_id=14 or any path you want
    extra_param = request.args.get("extra")  # optional, just an example

    login_token = ClubLoginToken.query.filter_by(token=token, used=False).first()

    if not login_token:
        flash("Invalid or already used token.", "danger")
        return redirect(url_for("home"))

    if login_token.expires_at < datetime.utcnow():
        flash("This token has expired.", "danger")
        return redirect(url_for("home"))

    # Optionally mark token as used
    # login_token.used = True
    # db.session.commit()

    # Log the user into the club session
    club = login_token.club
    session["club_id"] = club.id
    session["club_name"] = club.name
    flash(f"Welcome, {club.name}!", "success")

    # Redirect to next page if provided, otherwise to club dashboard
    if race_id:
        return redirect(url_for("club_dashboard", club_name=club.name, race_id=race_id))
    else:
        return redirect(url_for("club_dashboard", club_name=club.name))

# Example route for logged-in club page
@app.route("/club-dashboard")
def club_dashboard():
    if "club_id" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("club_login"))

    club = Club.query.get(session["club_id"])
    club_clicked = request.args.get('club_name')
    print("club_clicked", club_clicked)
    print("session club_name:", club.name)
    if club_clicked != club.name:
        print("ny klub valgt")
        session.pop("club_id")
        session.pop("club_name")
        return redirect(url_for("club_login"))

    print ("klubbens id er", session["club_name"])
    
    # Filter carpools for this club only
    active_carpools = Carpool.query.filter(
        Carpool.club_id == club.id,
        Carpool.departure_time >= datetime.utcnow()
    ).all()

    # Default map coordinates (optional: center on first carpool if exists)
    if active_carpools:
        latitude = active_carpools[0].latitude
        longitude = active_carpools[0].longitude
    else:
        latitude = 55.6761
        longitude = 12.5683

    # Get all clubs for dropdown (optional, could hide in dashboard)
    clubs = Club.query.all()


  

    return render_template(
        "home.html",
        carpools=active_carpools,
        clubs=clubs,
        latitude=latitude,
        longitude=longitude,
        selected_club=club.name,
        is_club_page=True,  # flag so template knows it's a club dashboard
        club=club  # pass the club object for extra info if needed
    )





@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'admin_login' not in session: 
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        # Check if this is a "delete" request
        club_id_to_delete = request.form.get("delete_club_id")
        race_id_to_delete = request.form.get("delete_race_id")
        if club_id_to_delete:
            club_id_to_delete = int(club_id_to_delete)
            
            # Delete the club and related data
            club = Club.query.get_or_404(club_id_to_delete)
            # Delete related races, carpools, comments, reservations
            delete_races = Race.query.filter_by(club_id=club.id).all()
            for race in delete_races:
                delete_carpools = Carpool.query.filter_by(race_id=race.id).all()
                count = len(delete_carpools)
                for carpool in delete_carpools:
                    delete_comments = Comment.query.filter_by(carpool_id=carpool.id).all()
                    delete_reservations = Reservation.query.filter_by(carpool_id=carpool.id).all()
                    for comment in delete_comments:
                        db.session.delete(comment)
                    for reservation in delete_reservations:
                        db.session.delete(reservation)
                    db.session.delete(carpool)
                db.session.delete(race)
            db.session.delete(club)
            db.session.commit()
            print(f":::Deleted this many carpools:::{count}")
        elif race_id_to_delete:

            race_id_to_delete = int(race_id_to_delete)
            delete_races = Race.query.filter_by(id=race_id_to_delete).all()
            for race in delete_races:
                delete_carpools = Carpool.query.filter_by(race_id=race.id).all()
                count = len(delete_carpools)
                for carpool in delete_carpools:
                    delete_comments = Comment.query.filter_by(carpool_id=carpool.id).all()
                    delete_reservations = Reservation.query.filter_by(carpool_id=carpool.id).all()
                    for comment in delete_comments:
                        db.session.delete(comment)
                    for reservation in delete_reservations:
                        db.session.delete(reservation)
                    db.session.delete(carpool)
                db.session.delete(race)
            db.session.commit()

        else:
            # Otherwise, it's an "add club" request
            club_name = request.form.get("name")
            password = request.form.get("password")
            description = request.form.get("description")
            new_club = Club(name=club_name, password=password, description=description)
            db.session.add(new_club)
            db.session.commit()
    
    # Finally, render the admin page
    Clubs = Club.query.all()
    Races = Race.query.all()
    Carpools = Carpool.query.all()
    races_by_club = {}
    carpools_by_races = {}
    for race in Races:
        races_by_club.setdefault(race.club_id, []).append(race)

    for carpool in Carpools:
        carpools_by_races.setdefault(carpool.race_id, []).append(carpool)

    clubs_dict = {club.id: club for club in Clubs}
    Carpools = Carpool.query.all()
    return render_template("admin.html", clubs=Clubs, races=Races, carpool=Carpools, clubs_dict = clubs_dict, races_by_club=races_by_club, carpools_by_races=carpools_by_races )

    
@app.route("/admin/login", methods=['GET', 'POST'])
def admin_login():
    if request.method == "POST":
        
        password = request.form.get("password")
        global PASSWORD_ADMIN
        if password == PASSWORD_ADMIN:
        
            session["admin_login"] = "PASS"
            flash(f"Welcome,!", "success")
            print("Logged in")
            return redirect(url_for("admin"))  # Replace with your club page
        else:
            flash("Invalid club or password.", "danger")
            print("Invalid ")
            return redirect(url_for("admin_login"))
    return render_template('admin_login.html')

    
@app.route('/for-klubber')
def home_klubber():

    

    # Default coordinates (center of map)
    latitude = 55.6761  # Default latitude for Denmark
    longitude = 12.5683  # Default longitude for Denmark

    club_name = request.args.get('club', None)

    if club_name:
        active_carpools = Carpool.query.join(Club).filter(Club.name == club_name, Carpool.departure_time >= datetime.utcnow()).all(),Carpool.club_level == 1
    else:
        active_carpools = Carpool.query.filter(Carpool.departure_time >= datetime.utcnow(),Carpool.club_level==1).all()

    # Get all clubs for the dropdown
    clubs = Club.query.all()

    return render_template('home.html', carpools=active_carpools, clubs=clubs, latitude=latitude, longitude=longitude, selected_club=club_name, is_club_page=True)


# API endpoint to get carpool locations as JSON for the map
@app.route('/api/carpool-locations')
def carpool_locations():
    club_name = request.args.get('club', None)
    race_id = request.args.get('race_id', type=int)  # optional race filter

    query = Carpool.query.filter(Carpool.departure_time >= datetime.utcnow())

    if club_name:
        query = query.filter(Club.name == club_name)
    if race_id:
        query = query.filter(Carpool.race_id == race_id)

    carpools = query.all()

    locations = []
    for carpool in carpools:
        locations.append({
            'id': carpool.id,
            'club_level' : carpool.club_level,
            'event': carpool.event,
            'owner': carpool.owner,
            'departure_place': carpool.departure_place,
            'departure_time': carpool.departure_time.strftime('%Y-%m-%d %H:%M'),
            'vacant_seats': carpool.vacant_seats,
            'latitude': carpool.latitude,
            'longitude': carpool.longitude,
            'race_id': carpool.race_id  # <-- include race_id
        })

    return jsonify(locations)


# API endpoint to get race details
@app.route('/api/race-details')
def race_details():

    query = Race.query.filter(Race.date >= datetime.utcnow())

    races = query.all()
    race_list = []
    for race in races:
        race_list.append({
            'id': race.id,
            'club_level' : race.club_level,
            'name': race.name,
            'description': race.description,
            'date': race.date.strftime('%Y-%m-%d %H:%M'),
            'latitude': race.latitude,
            'longitude': race.longitude,
            'club_id': race.club_id,
            # 👇 include carpools backref
            'carpools': [
                {
                    'id': carpool.id,
                    'owner': carpool.owner,
                    'vacant_seats': carpool.vacant_seats,
                    'departure_place': carpool.departure_place
                }
                for carpool in race.carpools
            ]
        })
    return jsonify({"races": race_list,
                   "session_club_id": session.get("club_id"),
                   "session_club_name": session.get("club_name")})


@app.route('/api/carpool/<int:carpool_id>/comments', methods=['POST'])
def add_carpool_comment(carpool_id):  # renamed function
    data = request.json
    comment = Comment(
        carpool_id=carpool_id,
        author=data['author'],
        text=data['text'],
        timestamp=datetime.utcnow()
    )
    db.session.add(comment)
    db.session.commit()
    return jsonify({
        'author': comment.author,
        'text': comment.text,
        'timestamp': comment.timestamp.strftime('%Y-%m-%d %H:%M')
    })


@app.route('/carpool/<club_name>')
def show_carpools(club_name):
    # Query carpools that belong to the specified club
    club_carpools = Carpool.query.filter(Carpool.club == club_name).all()

    return render_template('home.html', carpools=club_carpools, club_name=club_name)

@app.route('/create_race', methods=['GET', 'POST'])
def create_race():
    

    if request.method == 'POST':
        race_name = request.form['race_name']
        club_level = request.form['club_level']
        if club_level == "true":
            club_level = True
        else:
            club_level = False
        club_id = request.form['club_id']  # Get club_id from the form
        description = request.form['description']
        date = request.form['date']
        latitude = request.form['latitude']
        longitude = request.form['longitude']


        # Create a new Race object
        new_race = Race(name=race_name,club_id=club_id, club_level=club_level,description=description, date=datetime.strptime(date, '%Y-%m-%dT%H:%M'), latitude=latitude, longitude=longitude)
        db.session.add(new_race)
        db.session.commit()

        if club_level:
            return redirect(url_for('club_dashboard', club_name = session.get('club_name')))  # Redirect to club-specific homepage
        else:
            return redirect(url_for('home'))

    return render_template('create_race.html')
# handle comments
@app.route('/add_comment/<int:carpool_id>', methods=['POST'])
def add_comment(carpool_id):
    author = request.form.get('author')
    text = request.form.get('text')

    if not author or not text:
        return "Error: Missing name or comment", 400

    new_comment = Comment(author=author, text=text, carpool_id=carpool_id)
    db.session.add(new_comment)
    db.session.commit()

    return redirect(url_for('home'))

# Create a new carpool
@app.route('/create', methods=['GET', 'POST'])
def create_carpool():
    if request.method == 'POST':
        event = request.form['event']
        is_club = request.form.get('club_level') == "true"
        race_id = request.form.get('race_id')  # get race_id from the form
        owner = request.form['owner']
        owner_email = request.form['owner_email']
        description = request.form['description']
        vacant_seats = int(request.form['vacant_seats'])
        departure_time = request.form['departure_time']
        departure_place = request.form['departure_place']
        club_id = int(request.form['club_id'])
        latitude = float(request.form['latitude'])
        longitude = float(request.form['longitude'])
        
        departure_time = datetime.strptime(departure_time, '%Y-%m-%dT%H:%M')

        # existing_club = Club.query.filter_by(name=club_name).first()
        # if not existing_club:
        #     new_club = Club(name=club_name)
        #     db.session.add(new_club)
        # else:
        #     new_club = existing_club
        # db.session.commit()
       
    #    if club_name > 1:

        print("her printes id", club_id)

        new_carpool = Carpool(
            event=event,
            club_level=is_club,
            race_id=race_id,
            owner=owner,
            description = description,
            owner_email=owner_email,
            vacant_seats=vacant_seats,
            departure_time=departure_time,
            departure_place=departure_place,
            club_id=club_id,
            latitude=latitude,
            longitude=longitude
        )
        
        db.session.add(new_carpool)
        db.session.commit()
        if is_club:
            return redirect(url_for('club_dashboard', club_name=session.get('club_name')))  # Redirect to club-specific homepage
        else:
            return redirect(url_for('home'))

    # GET request: prefill event and race_id if given in query string
    event_name = request.args.get("event", "")
    race_id = request.args.get("race_id", "")
    return render_template('create_carpool.html', event_name=event_name, race_id=race_id)



# Reserve a spot in a carpool
@app.route('/reserve/<int:carpool_id>', methods=['GET', 'POST'])
def reserve_spot(carpool_id):
    carpool = Carpool.query.get_or_404(carpool_id)
    


    if request.method == 'POST':
        passenger_name = request.form['passenger_name']
        passenger_phone = request.form['passenger_phone']
        passenger_email = request.form['passenger_email']
        
        # Check if there are vacant seats
        if carpool.vacant_seats > 0:
            # Create a new reservation
            reservation = Reservation(carpool_id=carpool.id, passenger_name=passenger_name, passenger_phone = passenger_phone, passenger_email=passenger_email)
            
            # Save it to the database
            db.session.add(reservation)
            db.session.commit()

            # Update the vacant seats for the carpool
            carpool.vacant_seats -= 1
            db.session.commit()
            msg = f"Hej {carpool.owner},\n\n{passenger_name} har reserveret en plads hos dig til '{carpool.event}' med afgang:\n {carpool.departure_time.strftime('%Y-%m-%d %H:%M')}.\n\nBedste hilsner,\nKørselsservice"
            mime_msg = SMTP.message_to_email(msg, carpool.owner_email, GMAIL)
            if ('@' in carpool.owner_email):
                SMTP.send_mail(mime_msg,GMAIL,GMAIL_PASSWORD)
            else:
                print("no email found")
            
            if session.get('club_id'):
                return redirect(url_for('club_dashboard', club_name=session.get('club_name')))
            else:
                return redirect(url_for('home'))  # Redirect back to the homepage

        return "No available seats"

    return render_template('reserve_spot.html', carpool=carpool)

@app.route('/get_comments/<int:carpool_id>')
def get_comments(carpool_id):
    comments = Comment.query.filter_by(carpool_id=carpool_id).order_by(Comment.timestamp.desc()).all()
    comments_data = []
    
    for comment in comments:
        comments_data.append({
            'id': comment.id,
            'author': comment.author,
            'text': comment.text,
            'timestamp': comment.timestamp.strftime('%Y-%m-%d %H:%M')
        })
    
    return jsonify(comments_data)

# ----------------------------- ANDRE FEDE FEATURES -----------------------------
@app.route("/playblackjack", methods=["GET"])
def play_blackjack():
    if request.method == "GET":
        initial_bakroll = int(request.args.get("initial_bankroll"))
        hands = int(request.args.get("hands"))
        bj.main(initial_bakroll, hands)
        return redirect("./static/plot.png")
        

@app.route("/beregn_ruter", methods = ["GET"])
def get_routes():
    
    img_url = request.args.get("url")
    start = request.args.get("start")
    goal = request.args.get("goal")

    if not img_url or not start or not goal:
        return "Missing parameters", 400

    start = tuple(map(int, start.split(",")))
    goal = tuple(map(int, goal.split(",")))

    # Fetch external image
    response = requests.get(img_url)
    im = Image.open(BytesIO(response.content))
    im.save("./pythonextensions/static/map.png")
    # Process the image (your function)
    pf.main("./pythonextensions/static/map.png", start=start, goal=goal)  # modify pf.main to accept PIL image
    # or save to BytesIO if pf.main returns nothing
    processed_im = "./static/path_result.png"
    
    # Return image directly
    return send_file(processed_im, mimetype="image/png")
        
if __name__ == '__main__':
    app.run(debug=True)