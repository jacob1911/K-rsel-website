from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# I can add a new collumn to a sqllite table by :
# ALTER [TABLE] passengers ADD COLUMN [COLNAME] [VARCHAR(100)];

class ClubLoginToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(64), unique=True, nullable=False)
    club_id = db.Column(db.Integer, db.ForeignKey('club.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)

    club = db.relationship('Club')

class Club(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    password = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)

    # One club can have many carpools
    carpools = db.relationship('Carpool', backref='club', lazy="joined")
    races = db.relationship('Race', backref='club', lazy="joined")


class Race(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    club_level = db.Column(db.Boolean, default=False) #indicates if it is a club level 
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    date = db.Column(db.DateTime, nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    # One race can have many carpools
    carpools = db.relationship('Carpool', backref='race', lazy="joined")

    # foreign key to Club
    club_id = db.Column(db.Integer, db.ForeignKey('club.id'), nullable=True)


class Carpool(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    club_level = db.Column(db.Boolean, default=False) 
    event = db.Column(db.String(100), nullable=False)
    owner = db.Column(db.String(100), nullable=False)
    owner_email = db.Column(db.String(100), nullable=False)
    club_id = db.Column(db.Integer, db.ForeignKey('club.id'), nullable=True)
    race_id = db.Column(db.Integer, db.ForeignKey('race.id'), nullable=False)
    description = db.Column(db.Text, nullable=False)
    vacant_seats = db.Column(db.Integer, nullable=False)
    departure_time = db.Column(db.DateTime, nullable=False)
    departure_place = db.Column(db.String(100), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)  # Fixed spelling from longtitude to longitude


    comments = db.relationship('Comment', backref='carpool', lazy="joined")

    reservations = db.relationship('Reservation', backref='carpool', lazy="joined")
    # club attribute is available via backref from Club


class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    carpool_id = db.Column(db.Integer, db.ForeignKey('carpool.id'), nullable=False)
    passenger_name = db.Column(db.String(100), nullable=False)
    passenger_phone = db.Column(db.String(100), nullable=False)
    passenger_email = db.Column(db.String(100), nullable=False)


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    carpool_id = db.Column(db.Integer, db.ForeignKey('carpool.id'), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    