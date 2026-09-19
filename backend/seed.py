"""
Seeds the local database with a demo household so LifeRoom looks alive
immediately, without hand-typing data through the UI before a demo.

Usage:
    cd backend
    python seed.py

Safe to re-run: leaves an existing demo household and its data untouched.
"""
from datetime import datetime, timedelta, timezone

from app.core.security import generate_session_token, hash_token
from app.database.session import SessionLocal, init_db
from app.models.activity import Activity, ActivityType
from app.models.bill import Bill, BillParticipant
from app.models.chore import Chore, Priority
from app.models.grocery import GroceryItem
from app.models.household import Household
from app.models.member import Member
from app.models.message import Message

DEMO_ROOM_CODE = "FRX482"


def run() -> None:
    init_db()
    db = SessionLocal()
    try:
        existing = db.query(Household).filter(Household.room_code == DEMO_ROOM_CODE).first()
        if existing:
            print("Demo household already exists; leaving its data unchanged.")
            return

        household = Household(name="Foxridge House", room_code=DEMO_ROOM_CODE, password_hash=None)
        db.add(household)
        db.flush()

        names = ["Seongjin", "Alex", "Jamie", "Chris"]
        members: dict[str, Member] = {}
        for i, name in enumerate(names):
            member = Member(
                household_id=household.id,
                display_name=name,
                session_token=hash_token(generate_session_token()),
                is_owner=(i == 0),
            )
            db.add(member)
            db.flush()
            members[name] = member

        household.created_by_member_id = members["Seongjin"].id

        now = datetime.now(timezone.utc)

        chores = [
            Chore(
                household_id=household.id,
                title="Take out trash",
                assigned_to_id=members["Seongjin"].id,
                created_by_id=members["Alex"].id,
                due_date=now.replace(hour=20, minute=0, second=0, microsecond=0),
                priority=Priority.high,
            ),
            Chore(
                household_id=household.id,
                title="Clean kitchen",
                assigned_to_id=members["Alex"].id,
                created_by_id=members["Seongjin"].id,
                due_date=now + timedelta(days=1),
                priority=Priority.medium,
            ),
            Chore(
                household_id=household.id,
                title="Vacuum living room",
                assigned_to_id=members["Jamie"].id,
                created_by_id=members["Jamie"].id,
                due_date=now + timedelta(days=2),
                priority=Priority.low,
            ),
        ]
        db.add_all(chores)

        internet = Bill(
            household_id=household.id,
            title="Internet",
            amount_cents=9000,
            paid_by_id=members["Alex"].id,
            created_by_id=members["Alex"].id,
        )
        db.add(internet)
        db.flush()
        for name in ["Alex", "Seongjin", "Jamie", "Chris"]:
            db.add(
                BillParticipant(
                    bill_id=internet.id,
                    member_id=members[name].id,
                    share_cents=2250,
                    settled=(name == "Alex"),
                )
            )

        electricity = Bill(
            household_id=household.id,
            title="Electricity",
            amount_cents=6000,
            paid_by_id=members["Chris"].id,
            created_by_id=members["Chris"].id,
        )
        db.add(electricity)
        db.flush()
        for name in ["Chris", "Seongjin", "Alex"]:
            db.add(
                BillParticipant(
                    bill_id=electricity.id,
                    member_id=members[name].id,
                    share_cents=2000,
                    settled=(name == "Chris"),
                )
            )

        groceries = [
            GroceryItem(household_id=household.id, name="Milk", quantity=1, added_by_id=members["Jamie"].id),
            GroceryItem(household_id=household.id, name="Eggs", quantity=12, added_by_id=members["Seongjin"].id),
            GroceryItem(household_id=household.id, name="Rice", quantity=1, added_by_id=members["Chris"].id),
            GroceryItem(household_id=household.id, name="Chicken", quantity=2, added_by_id=members["Alex"].id),
        ]
        db.add_all(groceries)

        messages = [
            Message(household_id=household.id, member_id=members["Alex"].id, sender_name="Alex", content="Anyone going grocery shopping today?"),
            Message(household_id=household.id, member_id=members["Jamie"].id, sender_name="Jamie", content="I can go after class."),
        ]
        db.add_all(messages)

        activities = [
            Activity(household_id=household.id, type=ActivityType.member_joined, actor_name="Alex", message="Alex joined the household"),
            Activity(household_id=household.id, type=ActivityType.chore_created, actor_name="Alex", message='Alex added "Take out trash"'),
            Activity(household_id=household.id, type=ActivityType.grocery_added, actor_name="Jamie", message="Jamie added Milk to groceries"),
            Activity(household_id=household.id, type=ActivityType.bill_created, actor_name="Chris", message='Chris added "Electricity" ($60.00)'),
        ]
        db.add_all(activities)

        db.commit()

        print("Seeded demo household successfully.\n")
        print(f"  Household : {household.name}")
        print(f"  Room code : {household.room_code}")
        print("  Members   : " + ", ".join(names))
        print("Join with a new display name using the room code above.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
