"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from pathlib import Path
from sqlalchemy.orm import Session

from .db import SessionLocal, init_db, Activity, Participant

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Initialize DB and seed data if empty
def seed_default_activities(db: Session):
    existing = db.query(Activity).count()
    if existing > 0:
        return

    default_activities = {
        "Chess Club": {
            "description": "Learn strategies and compete in chess tournaments",
            "schedule": "Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 12,
            "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
        },
        "Programming Class": {
            "description": "Learn programming fundamentals and build software projects",
            "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
            "max_participants": 20,
            "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
        },
        "Gym Class": {
            "description": "Physical education and sports activities",
            "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
            "max_participants": 30,
            "participants": ["john@mergington.edu", "olivia@mergington.edu"]
        }
    }

    for name, data in default_activities.items():
        activity = Activity(
            name=name,
            description=data["description"],
            schedule=data["schedule"],
            max_participants=data["max_participants"],
        )
        for email in data.get("participants", []):
            participant = db.query(Participant).filter_by(email=email).first()
            if not participant:
                participant = Participant(email=email)
            activity.participants.append(participant)
        db.add(activity)
    db.commit()


# Run DB init at startup
init_db()
with SessionLocal() as db:
    seed_default_activities(db)


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities(db: Session = Depends(get_db)):
    activities = db.query(Activity).all()
    return {a.name: a.to_dict() for a in activities}


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str, db: Session = Depends(get_db)):
    """Sign up a student for an activity"""
    # Validate activity exists
    activity = db.query(Activity).filter_by(name=activity_name).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Validate student is not already signed up
    participant = db.query(Participant).filter_by(email=email).first()
    if participant and participant in activity.participants:
        raise HTTPException(status_code=400, detail="Student is already signed up")

    if not participant:
        participant = Participant(email=email)
    activity.participants.append(participant)
    db.add(activity)
    db.commit()
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str, db: Session = Depends(get_db)):
    """Unregister a student from an activity"""
    activity = db.query(Activity).filter_by(name=activity_name).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    participant = db.query(Participant).filter_by(email=email).first()
    if not participant or participant not in activity.participants:
        raise HTTPException(status_code=400, detail="Student is not signed up for this activity")

    activity.participants.remove(participant)
    db.add(activity)
    db.commit()
    return {"message": f"Unregistered {email} from {activity_name}"}
