from fastapi import APIRouter
router = APIRouter()

@router.get("/shipping")
def list_shipping(): return []

@router.get("/shipping/{id}")
def get_shipping(id: int): return {"id": id}

@router.post("/shipping")
def create_shipping(payload: dict): return payload

# TODO: add pagination
# FIXME: N+1 query in list_shipping
