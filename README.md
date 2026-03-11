# Botox


## 🚀 How to run project

Botox is a FastAPI (web framework for APIs) Application running on a async-friendly Uvicorn server

To install dependencies

Python 3.12 is required, not more for pytest at the moment

``python -m venv venv``

``source .venv/bin/activate``

``pip install --upgrade pip``

``pip install -r requirements.txt``


### Run the backend app

``cd backend``

``source venv/bin/activate``

``uvicorn app.main:app --reload``

Server should run at `http://127.0.0.1:8000/`

Interactive doc `http://127.0.0.1:8000/docs` 


### Start the Database

Botox use a PosgreSQL database

How to have a postgresql db?

``brew install postgresql@14``

``brew services start postgresql@14``
`` psql --version ``

#### Access the PostgreSQL command-line interface: 
``psql postgres`` or `psql -U your_user -d postgres`

#### when running from docker

 Dumps will appear in ./backups/botox_2026-03-11.sql.gz on the host, rotated daily at 02:00 UTC, kept for 30 days.                         
                                                                                                                                            
 To restore a dump manually:                                                                                                               
  `gunzip -c backups/botox_2026-03-11.sql.gz | docker compose exec -T db psql -U botox_user -d botox`        
