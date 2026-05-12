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


### The .env file

about ROOT_PATH variable:

When nginx receives https://46.224.199.1/botox/docs, it strips /botox/ and forwards   
  just /docs to FastAPI (because of the trailing slash in proxy_pass).                
                                                                                        
  FastAPI receives /docs and renders Swagger — but Swagger then tries to fetch the API  
  definition at /openapi.json (absolute path, no /botox/ prefix). That request hits     
  nginx, which doesn't match any location block → 404.                                  
                  
  root_path tells FastAPI "you're mounted under /botox", so Swagger requests            
  /botox/openapi.json instead → nginx forwards it correctly → works.
                                                                                        
  Browser → https://46.224.199.1/botox/docs                                             
  nginx   → strips /botox/ → forwards /docs to FastAPI :8001                            
  FastAPI → renders Swagger, but Swagger fetches /openapi.json  ← wrong, 404            
                                                                                        
  With root_path=/botox:                                                                
  FastAPI → renders Swagger, Swagger fetches /botox/openapi.json ← correct, 200    


### About Heztner server:

The server run Nginx reverse proxy and white list my IP address to access the app

Connect to server with `ssh botserver` @seealso ssh config for details

#### Local Forward DB ports 

docker-compose file on server side should contain: 
``` 
ports:
- "5432:5432" # "host_port:container_port"
```

SSH config on local
```
Host botserver
HostName <your-server-ip>
User <your-user>
LocalForward 5434 localhost:5432
```
pgAdmin should be set to **localhost:5434.**

