import psycopg2
# use PGADMIN-SOFTWARE for simplicity 
# Run the Schema.sql as it is firstly in ur database(using Query Tool) -> then use the same database for DB_CONFIGURATION
PG_HOST = "localhost"       
PG_PORT = 5432
PG_DB   = "YOUR_DATABASE_NAME"
PG_USER = "YOUR_DATABASE_USER_NAME"    
PG_PASS = "YOUR_DATABSE_PASSWORD"   

def create_connection():
    conn = psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASS
    )
    return conn
