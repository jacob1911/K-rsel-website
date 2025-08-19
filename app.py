from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///carpool.db'
db = SQLAlchemy(app)

class Club(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)

    # One club can have many carpools
    carpools = db.relationship('Carpool', backref='club', lazy="joined")


class Race(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    date = db.Column(db.DateTime, nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    # One race can have many carpools
    carpools = db.relationship('Carpool', backref='race', lazy="joined")


class Carpool(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event = db.Column(db.String(100), nullable=False)
    owner = db.Column(db.String(100), nullable=False)
    club_id = db.Column(db.Integer, db.ForeignKey('club.id'), nullable=False)
    race_id = db.Column(db.Integer, db.ForeignKey('race.id'), nullable=False)
    vacant_seats = db.Column(db.Integer, nullable=False)
    departure_time = db.Column(db.DateTime, nullable=False)
    departure_place = db.Column(db.String(100), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)  # Fixed spelling from longtitude to longitude


    reservations = db.relationship('Reservation', backref='carpool', lazy="joined")
    # club attribute is available via backref from Club


class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    carpool_id = db.Column(db.Integer, db.ForeignKey('carpool.id'), nullable=False)
    passenger_name = db.Column(db.String(100), nullable=False)


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    carpool_id = db.Column(db.Integer, db.ForeignKey('carpool.id'), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    carpool = db.relationship('Carpool', backref=db.backref('comments', lazy=True))


with app.app_context():
    db.create_all()

from flask import render_template, request, redirect, url_for, jsonify

# Homepage: List all available carpools
@app.route('/')
def home():
    # Default coordinates (center of map)
    latitude = 55.6761  # Default latitude for Denmark
    longitude = 12.5683  # Default longitude for Denmark

    club_name = request.args.get('club', None)

    if club_name:
        active_carpools = Carpool.query.join(Club).filter(Club.name == club_name, Carpool.departure_time >= datetime.utcnow()).all()
    else:
        active_carpools = Carpool.query.filter(Carpool.departure_time >= datetime.utcnow()).all()

    # Get all clubs for the dropdown
    clubs = Club.query.all()

    return render_template('home.html', carpools=active_carpools, clubs=clubs, latitude=latitude, longitude=longitude, selected_club=club_name)

# API endpoint to get carpool locations as JSON for the map
@app.route('/api/carpool-locations')
def carpool_locations():
    club_name = request.args.get('club', None)
    race_id = request.args.get('race_id', type=int)  # optional race filter

    query = Carpool.query.join(Club).filter(Carpool.departure_time >= datetime.utcnow())

    if club_name:
        query = query.filter(Club.name == club_name)
    if race_id:
        query = query.filter(Carpool.race_id == race_id)

    carpools = query.all()

    locations = []
    for carpool in carpools:
        locations.append({
            'id': carpool.id,
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
    races = Race.query.all()
    race_list = []
    for race in races:
        race_list.append({
            'id': race.id,
            'name': race.name,
            'description': race.description,
            'date': race.date.strftime('%Y-%m-%d %H:%M'),
            'latitude': race.latitude,
            'longitude': race.longitude,
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
    return jsonify(race_list)


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
        description = request.form['description']
        date = request.form['date']
        latitude = request.form['latitude']
        longitude = request.form['longitude']

        # Create a new Race object
        new_race = Race(name=race_name, description=description, date=datetime.strptime(date, '%Y-%m-%dT%H:%M'), latitude=latitude, longitude=longitude)
        db.session.add(new_race)
        db.session.commit()

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
        race_id = request.form.get('race_id')  # get race_id from the form
        owner = request.form['owner']
        vacant_seats = int(request.form['vacant_seats'])
        departure_time = request.form['departure_time']
        departure_place = request.form['departure_place']
        club_name = request.form['club_name']
        latitude = float(request.form['latitude'])
        longitude = float(request.form['longitude'])
        
        departure_time = datetime.strptime(departure_time, '%Y-%m-%dT%H:%M')

        existing_club = Club.query.filter_by(name=club_name).first()
        if not existing_club:
            new_club = Club(name=club_name)
            db.session.add(new_club)
        else:
            new_club = existing_club
        db.session.commit()

        new_carpool = Carpool(
            event=event,
            race_id=race_id,
            owner=owner,
            vacant_seats=vacant_seats,
            departure_time=departure_time,
            departure_place=departure_place,
            club_id=new_club.id,
            latitude=latitude,
            longitude=longitude
        )
        
        db.session.add(new_carpool)
        db.session.commit()
        
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
        
        # Check if there are vacant seats
        if carpool.vacant_seats > 0:
            # Create a new reservation
            reservation = Reservation(carpool_id=carpool.id, passenger_name=passenger_name)
            
            # Save it to the database
            db.session.add(reservation)
            db.session.commit()

            # Update the vacant seats for the carpool
            carpool.vacant_seats -= 1
            db.session.commit()
            
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


if __name__ == '__main__':
    app.run(debug=True)