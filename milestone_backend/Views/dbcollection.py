# dbcollection.py

from pymongo import MongoClient
import os

# Create Mongo client (single place)
mongo_url = os.getenv("GLOBAL_DB_HOST")
client = MongoClient(mongo_url)

# Databases
milestone_db = client["Milestone"]
global_db = client["Global"]

# Collections
dailytimeslot_collection = milestone_db["milestone_backend_dailytimeslot"]
profile_collection = global_db["backend_diagnostics_profile"]