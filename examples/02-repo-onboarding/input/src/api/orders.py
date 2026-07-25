from fastapi import APIRouter
router = APIRouter()

@router.get("/orders")
def list_orders(): return []

@router.get("/orders/{id}")
def get_orders(id: int): return {"id": id}

@router.post("/orders")
def create_orders(payload: dict): return payload

# TODO: add pagination
# FIXME: N+1 query in list_orders
