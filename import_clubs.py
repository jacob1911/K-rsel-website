from app import app, db, Club

clubs_data = [
    {"name": "Farum OK", "password": "secret123", "description": "Orienteering club in Farum"},
    {"name": "OK Pan", "password": "pass456", "description": "Club from Aarhus"},
    {"name": "Tisvilde Hegn OK", "password": "hunter789", "description": "Forest runners from Tisvilde"}
]

with app.app_context():  # must have app context
    for c in clubs_data:
        # check if club already exists
        if not Club.query.filter_by(name=c["name"]).first():
            db.session.add(Club(**c))
    db.session.commit()
    print("✅ Clubs added")
