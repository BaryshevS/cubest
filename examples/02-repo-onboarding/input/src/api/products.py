from fastapi import APIRouter
router = APIRouter()

@router.get("/products")
def list_products(): return []

@router.get("/products/{id}")
def get_products(id: int): return {"id": id}

@router.post("/products")
def create_products(payload: dict): return payload

# TODO: add pagination
# FIXME: N+1 query in list_products
