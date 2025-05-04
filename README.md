# Allin - AI Assistant for New Software Engineers

This project implements "Allin," an AI-powered assistant designed by Team 8 to help new software engineers.

## Features

*   Real-time guidance (voice and text)
*   Knowledge base interaction via RAG (PDFs, images)
*   Conversational context management
*   Code execution capabilities
*   FastAPI backend

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd allin-assistant
    ```

2.  **Create Conda Environment:**
    ```powershell
    conda create --name allin_env python=3.10 -y
    conda activate allin_env
    ```

3.  **Install Dependencies:**
    ```powershell
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    *   Copy `.env.example` to `.env` (or create `.env`)
    *   Fill in the required API keys and settings in `.env`:
        ```env
        GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY"
        # Add other configuration variables as needed
        ```

5.  **Run the Application:**
    ```powershell
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
    ```

## Project Structure

(See proposed structure in initial setup steps)

## API Endpoints

(Details to be added as developed)

*   `/ws`: WebSocket connection
*   `/health`: Health check
*   ... (other REST endpoints)
