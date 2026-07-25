from fastapi import APIRouter
router = APIRouter()

@router.get("/users")
def list_users(): return []

@router.get("/users/{id}")
def get_users(id: int): return {"id": id}

@router.post("/users")
def create_users(payload: dict): return payload

# TODO: add pagination
# FIXME: N+1 query in list_users
