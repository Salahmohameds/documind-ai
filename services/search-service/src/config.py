import os


class Config:
    EMBEDDING_BACKEND = os.getenv("EMBEDDING_BACKEND", "mock")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "384"))

   
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))       
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))  

    VECTOR_STORE_BACKEND = os.getenv("VECTOR_STORE_BACKEND", "memory")

  
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "5432"))
    DB_NAME = os.getenv("DB_NAME", "documind")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres") 

    
    TOP_K = int(os.getenv("TOP_K", "5"))

    
    LOCAL_STORE_PATH = os.getenv("LOCAL_STORE_PATH", "./local_vector_store.json")

    PORT = int(os.getenv("PORT", "8080"))

    
    JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    DISABLE_AUTH = os.getenv("DISABLE_AUTH", "false").lower() == "true"
