# test_railway.py
import os
from railway_api import RailwayAPI
from config import Config

def test_railway_connection():
    print("🔍 Testing Railway API connection...")
    
    # Validate config first
    try:
        Config.validate()
        print("✅ Configuration validated")
    except Exception as e:
        print(f"❌ Config error: {e}")
        return
    
    # Test API
    railway = RailwayAPI()
    
    print("📡 Testing deployment access...")
    deployment = railway.get_latest_deployment()
    
    if deployment:
        print(f"✅ Success! Deployment: {deployment['id']}")
        print(f"📊 Status: {deployment['status']}")
    else:
        print("❌ Failed to access deployments")
        print("💡 Check your RAILWAY_API_TOKEN permissions")

if __name__ == "__main__":
    test_railway_connection()
