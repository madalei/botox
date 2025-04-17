# Botox


## 🚀 How to run project

Botox is a FastAPI (web framework for APIs) Application running on a async-friendly Uvicorn server

Botox use Poetry: a Python dependency management and packaging tool 

`poetry install` to install dependencies

`poetry add somepackage` to add a lib


### Run the app

`poetry run python -m uvicorn main:app --reload`

Server should run at `http://127.0.0.1:8000/`

Interactive doc `http://127.0.0.1:8000/docs` 


### Start the Database

Botox use a PosgreSQL database

How to have a postgresql db?

``brew install postgresql``

``brew services start postgresql``

Access the PostgreSQL command-line interface: 
``psql postgres`` or `psql -U your_user -d postgres`
