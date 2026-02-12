from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

async def test():
    # Use the EXACT connection string from MongoDB Atlas
    uri = "mongodb+srv://rankinguser:18wtD7jU81Mwy0Pr@instantai.ammyleh.mongodb.net/?appName=InstantAI"
    
    try:
        print("Attempting connection to MongoDB Atlas...")
        client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=10000)
        
        # Test connection
        await client.admin.command('ping')
        print("✓ Successfully connected to MongoDB!")
        
        # List databases
        dbs = await client.list_database_names()
        print(f"✓ Available databases: {dbs}")
        
        # Try to access your database
        db = client['rankingdb']
        collections = await db.list_collection_names()
        print(f"✓ Collections in 'rankingdb': {collections if collections else 'None (new database)'}")
        
        print("\n✓✓✓ CONNECTION TEST PASSED! Your app should work now. ✓✓✓")
        
    except Exception as e:
        print(f"✗ Connection failed!")
        print(f"Error: {e}")
        print("\nMake sure:")
        print("1. Your IP is whitelisted and shows 'Active' in Network Access")
        print("2. You've waited 2-3 minutes after adding the IP")
        print("3. Try adding 0.0.0.0/0 to allow all IPs (for testing)")
        
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(test())