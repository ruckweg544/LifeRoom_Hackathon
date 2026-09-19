from app.websocket.connection_manager import manager
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_member
from app.database.session import get_db
from app.models.activity import ActivityType
from app.models.grocery import GroceryItem
from app.models.member import Member
from app.schemas.grocery import CreateGroceryRequest, GroceryOut, UpdateGroceryRequest
from app.services.activity_service import log_activity

router = APIRouter(prefix="/api/groceries", tags=["groceries"])


def _to_out(item: GroceryItem, db: Session) -> GroceryOut:
    added_by = db.query(Member).filter(Member.id == item.added_by_id).first()
    out = GroceryOut.model_validate(item)
    out.added_by_name = added_by.display_name if added_by else None
    return out


def _get_household_item(db: Session, item_id: str, household_id: str) -> GroceryItem:
    item = db.query(GroceryItem).filter(GroceryItem.id == item_id, GroceryItem.household_id == household_id).first()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grocery item not found")
    return item


@router.get("", response_model=list[GroceryOut])
def list_groceries(current_member: Member = Depends(get_current_member), db: Session = Depends(get_db)):
    items = (
        db.query(GroceryItem)
        .filter(GroceryItem.household_id == current_member.household_id)
        .order_by(GroceryItem.purchased.asc(), GroceryItem.created_at.desc())
        .all()
    )
    return [_to_out(i, db) for i in items]


@router.post("", response_model=GroceryOut, status_code=status.HTTP_201_CREATED)
async def create_grocery(
    payload: CreateGroceryRequest,
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db),
):
    item = GroceryItem(
        household_id=current_member.household_id,
        name=payload.name,
        quantity=payload.quantity,
        added_by_id=current_member.id,
    )
    db.add(item)
    db.flush()

    log_activity(
        db,
        current_member.household_id,
        ActivityType.grocery_added,
        current_member.display_name,
        f"{current_member.display_name} added {item.name} to groceries",
    )

    db.commit()
    await manager.broadcast(current_member.household_id, {"type": "household.changed"})
    db.refresh(item)
    return _to_out(item, db)


@router.patch("/{item_id}", response_model=GroceryOut)
async def update_grocery(
    item_id: str,
    payload: UpdateGroceryRequest,
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db),
):
    item = _get_household_item(db, item_id, current_member.household_id)
    was_purchased = item.purchased

    data = payload.model_dump(exclude_unset=True)
    for field in ("name", "quantity", "purchased"):
        if field in data:
            setattr(item, field, data[field])

    db.flush()

    if item.purchased and not was_purchased:
        log_activity(
            db,
            current_member.household_id,
            ActivityType.grocery_purchased,
            current_member.display_name,
            f"{current_member.display_name} marked {item.name} as purchased",
        )

    db.commit()
    await manager.broadcast(current_member.household_id, {"type": "household.changed"})
    db.refresh(item)
    return _to_out(item, db)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_grocery(
    item_id: str,
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db),
):
    item = _get_household_item(db, item_id, current_member.household_id)
    db.delete(item)
    db.commit()
    await manager.broadcast(current_member.household_id, {"type": "household.changed"})
