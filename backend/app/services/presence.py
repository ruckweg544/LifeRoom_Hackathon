from app.websocket.connection_manager import manager


def online_member_ids(household_id: str) -> set[str]:
    return manager.room_member_ids(household_id)


def online_count(household_id: str) -> int:
    return len(online_member_ids(household_id))
