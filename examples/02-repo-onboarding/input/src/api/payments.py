from fastapi import APIRouter
router = APIRouter()

@router.get("/payments")
def list_payments(): return []

@router.get("/payments/{id}")
def get_payments(id: int): return {"id": id}

@router.post("/payments")
def create_payments(payload: dict): return payload

# TODO: add pagination
# FIXME: N+1 query in list_payments
