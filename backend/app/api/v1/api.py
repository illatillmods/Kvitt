from fastapi import APIRouter

from app.api.v1.endpoints import access, health, receipts, products, insights

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(access.router, prefix="/access", tags=["access"])
api_router.include_router(receipts.router, prefix="/receipts", tags=["receipts"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(insights.router, prefix="/insights", tags=["insights"])
