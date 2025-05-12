from fastapi import FastAPI
# Import logger first to ensure it's configured
from allin_app.core.logging_config import logger
# Import routers
from allin_app.api.endpoints import websocket, root, chat #, admin, health

logger.info("Starting Allin AI Assistant application...")

app = FastAPI(
    title="Allin AI Assistant", 
    version="0.1.0",
    description="AI assistant for new software engineers by Team 8."
)

@app.get("/", tags=["Root"])
async def read_root():
    logger.debug("Root endpoint '/' accessed.")
    return {"message": "Welcome to Allin AI Assistant by Team 8"}

# Placeholder for health check endpoint (Phase 4)
@app.get("/health", tags=["Health"])
async def health_check():
    logger.debug("Health check endpoint '/health' accessed.")
    # TODO: Add more comprehensive health checks later
    return {"status": "ok"}

# Include routers
app.include_router(websocket.router)
app.include_router(root.router)
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"]) # Added prefix and tag
# app.include_router(admin.router)   # To be added in Phase 4

logger.info("FastAPI application configured and routers included.")

if __name__ == "__main__":
    import uvicorn
    logger.info("Running Uvicorn directly (for debugging/testing)...")
    # Recommended way to run for development is: uvicorn main:app --reload
    # Get host/port from environment or use defaults
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    log_level = os.getenv("UVICORN_LOG_LEVEL", "info")

    uvicorn.run(app, host=host, port=port, log_level=log_level)
