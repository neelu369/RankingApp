import pymongo
from pymongo import MongoClient

# Test with pymongo (simpler, synchronous)
uri = "mongodb+srv://rankinguser:Hq2otsnjOJTO8Ezj@instantai.sff1nma.mongodb.net/?retryWrites=true&w=majority"

try:
    print("Connecting with pymongo...")
    client = MongoClient(uri, serverSelectionTimeoutMS=10000)
    
    # Test the connection
    client.admin.command('ping')
    print("✓ Connected successfully!")
    
    # List databases
    print(f"✓ Databases: {client.list_database_names()}")
    
except Exception as e:
    print(f"✗ Failed: {e}")
finally:
    client.close()