from sqlalchemy.orm import Session

from app.models.activity import Activity, ActivityType


def log_activity(db: Session, household_id: str, activity_type: ActivityType, actor_name: str, message: str) -> Activity:
    activity = Activity(
        household_id=household_id,
        type=activity_type,
        actor_name=actor_name,
        message=message,
    )
    db.add(activity)
    db.flush()
    return activity
