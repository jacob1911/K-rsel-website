from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///carpool.db'
db = SQLAlchemy(app)

class Carpool(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event = db.Column(db.String(100), nullable=False)
    owner = db.Column(db.String(100), nullable=False)
    club_name = db.Column(db.String(100), nullable=False)
    vacant_seats = db.Column(db.Integer, nullable=False)
    departure_time = db.Column(db.DateTime, nullable=False)  # Could be a datetime type
    departure_place = db.Column(db.String(100), nullable=False)
    
    # Relationship: One carpool can have many reservations
    reservations = db.relationship('Reservation', backref='carpool', lazy="joined")

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    carpool_id = db.Column(db.Integer, db.ForeignKey('carpool.id'), nullable=False)
    passenger_name = db.Column(db.String(100), nullable=False)



with app.app_context():
    db.create_all()

from flask import render_template, request, redirect, url_for

# Homepage: List all available carpools
@app.route('/')
def home():

    active_carpools = Carpool.query.filter(Carpool.departure_time >= datetime.utcnow()).all()
    return render_template('home.html', carpools=active_carpools)

@app.route('/carpool/<club_name>')
def show_carpools(club_name):
    # Query carpools that belong to the specified club
    club_carpools = Carpool.query.filter(Carpool.club_name == club_name).all()

    return render_template('home.html', carpools=club_carpools, club_name=club_name)




# Create a new carpool
@app.route('/create', methods=['GET', 'POST'])
def create_carpool():
    if request.method == 'POST':
        event = request.form['event']
        owner = request.form['owner']
        vacant_seats = int(request.form['vacant_seats'])
        departure_time = request.form['departure_time']
        departure_place = request.form['departure_place']
        club_name = request.form['club_name']


        departure_time = datetime.strptime(departure_time, '%Y-%m-%dT%H:%M') # Convert to datetime object

        # Create a new Carpool object
        new_carpool = Carpool(event=event, owner=owner, vacant_seats=vacant_seats, departure_time=departure_time, departure_place=departure_place, club_name=club_name)
        
        # Save it to the database
        db.session.add(new_carpool)
        db.session.commit()
        
        return redirect(url_for('home'))  # Redirect back to the homepage

    return render_template('create_carpool.html')

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

if __name__ == '__main__':
    app.run(debug=True)
