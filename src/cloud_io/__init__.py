import pandas as pd
import pymongo
import certifi
import json
import os, sys
from dotenv import load_dotenv
from src.constants import *
from src.exception import CustomException

# Ensure .env is loaded (needed for Streamlit multipage apps)
load_dotenv()


class MongoIO:
    _client = None
    _db = None

    def __init__(self):
        if MongoIO._client is None:
            mongo_db_url = os.getenv(MONGODB_URL_KEY)
            if mongo_db_url is None:
                raise Exception(f"Environment key: {MONGODB_URL_KEY} is not set.")
            
            # Clean URL — strip quotes/spaces that may have been added accidentally
            mongo_db_url = mongo_db_url.strip().strip('"').strip("'")
            
            if not mongo_db_url.startswith(("mongodb://", "mongodb+srv://")):
                raise Exception(f"Invalid MongoDB URL. Must start with 'mongodb://' or 'mongodb+srv://'. Got: {mongo_db_url[:30]}...")
            
            # Connect with proper SSL certificates
            MongoIO._client = pymongo.MongoClient(
                mongo_db_url,
                tlsCAFile=certifi.where(),
                serverSelectionTimeoutMS=30000
            )
            MongoIO._db = MongoIO._client[MONGO_DATABASE_NAME]
            print(f"[INFO] Connected to MongoDB database: {MONGO_DATABASE_NAME}")
        
        self.db = MongoIO._db

    def store_reviews(self,
                      product_name: str, reviews: pd.DataFrame):
        try:
            collection_name = product_name.replace(" ", "_")
            collection = self.db[collection_name]
            
            # Convert DataFrame to list of dicts and insert
            data_json = json.loads(reviews.to_json(orient='records'))
            collection.insert_many(data_json)
            print(f"[INFO] Stored {len(data_json)} reviews in collection: {collection_name}")

        except Exception as e:
            raise CustomException(e, sys)

    def get_reviews(self,
                    product_name: str):
        try:
            collection_name = product_name.replace(" ", "_")
            collection = self.db[collection_name]
            
            cursor = collection.find()
            data = pd.DataFrame(list(cursor))

            return data

        except Exception as e:
            raise CustomException(e, sys)


