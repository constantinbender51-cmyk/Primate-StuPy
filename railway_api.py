import os
import requests
import time
from config import Config

class RailwayAPI:
    def __init__(self):
        self.api_token = Config.RAILWAY_API_TOKEN
        self.project_id = Config.RAILWAY_TARGET_PROJECT_ID
        self.api_url = Config.RAILWAY_API_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }
    
    def get_latest_deployment(self) -> dict:
        """Get the latest deployment for the project"""
        query = """
        {
          deployments(input: {projectId: "%s"}, first: 1) {
            edges {
              node {
                id
                status
                createdAt
              }
            }
          }
        }
        """ % self.project_id

        response = requests.post(self.api_url, json={"query": query}, headers=self.headers)
        
        # Check if request was successful
        if response.status_code != 200:
            print(f"❌ Railway API request failed: {response.status_code}")
            return None
            
        data = response.json()
        
        # Check if data structure is valid and has deployments
        if ('data' not in data or 
            'deployments' not in data['data'] or 
            'edges' not in data['data']['deployments']):
            print("❌ Invalid response structure from Railway API")
            return None
        
        edges = data['data']['deployments']['edges']
        
        # Check if there are any deployments
        if not edges or len(edges) == 0:
            print("📭 No deployments found for this project")
            return None
        
        # Safe access to deployment data
        deployment = edges[0]['node']
        return {
            'id': deployment['id'],
            'status': deployment['status'],
            'createdAt': deployment['createdAt']
        }
    
    def get_deployment_logs(self, deployment_id: str) -> str:
        """Get deployment logs for a specific deployment"""
        if not deployment_id:
            return "No deployment ID provided"
            
        query = """
        {
          deploymentLogs(deploymentId: "%s", limit: 500) {
            message
            severity
            timestamp
          }
        }
        """ % deployment_id

        response = requests.post(self.api_url, json={"query": query}, headers=self.headers)
        
        if response.status_code != 200:
            return f"Failed to fetch deployment logs: {response.status_code}"
            
        data = response.json()
        
        if 'data' in data and data['data']['deploymentLogs']:
            logs = data['data']['deploymentLogs']
            formatted_logs = []
            for log in sorted(logs, key=lambda x: x["timestamp"]):
                formatted_logs.append(f"{log['timestamp']} [{log['severity']}] {log['message']}")
            return "\n".join(formatted_logs)
        return "No deployment logs available"
    
    def get_build_logs(self, deployment_id: str) -> str:
        """Get build logs for a specific deployment"""
        if not deployment_id:
            return "No deployment ID provided"
            
        query = """
        {
          buildLogs(deploymentId: "%s", limit: 500) {
            message
            severity
            timestamp
          }
        }
        """ % deployment_id

        response = requests.post(self.api_url, json={"query": query}, headers=self.headers)
        
        if response.status_code != 200:
            return f"Failed to fetch build logs: {response.status_code}"
            
        data = response.json()
        
        if 'data' in data and data['data']['buildLogs']:
            logs = data['data']['buildLogs']
            formatted_logs = []
            for log in sorted(logs, key=lambda x: x["timestamp"]):
                formatted_logs.append(f"{log['timestamp']} [{log['severity']}] {log['message']}")
            return "\n".join(formatted_logs)
        return "No build logs available"
    
    def wait_for_deployment_completion(self, timeout: int = None) -> dict:
        """Wait for the current deployment to complete"""
        if timeout is None:
            timeout = Config.MAX_DEPLOYMENT_WAIT
        
        start_time = time.time()
        
        print("🚀 Checking for deployments...")
        last_deployment = self.get_latest_deployment()
        
        if not last_deployment:
            print("📭 No existing deployments found. Waiting for first deployment...")
            # Wait for initial deployment to appear
            while time.time() - start_time < timeout:
                current_deployment = self.get_latest_deployment()
                if current_deployment:
                    print(f"🎯 Found new deployment: {current_deployment['id']}")
                    last_deployment = current_deployment
                    break
                time.sleep(Config.DEPLOYMENT_CHECK_INTERVAL)
            
            if not last_deployment:
                return {
                    'status': 'TIMEOUT',
                    'deployment_logs': 'No deployment started within timeout period',
                    'build_logs': 'No build logs available'
                }
        
        print(f"📊 Monitoring deployment: {last_deployment['id']}")
        print(f"📈 Initial status: {last_deployment['status']}")
        
        while time.time() - start_time < timeout:
            current_deployment = self.get_latest_deployment()
            
            if current_deployment and current_deployment['id'] == last_deployment['id']:
                status = current_deployment['status']
                
                if status in ['SUCCESS', 'FAILED', 'CRASHED', 'NONE']:
                    print(f"📊 Deployment completed with status: {status}")
                    
                    # Get logs
                    deployment_logs = self.get_deployment_logs(current_deployment['id'])
                    build_logs = self.get_build_logs(current_deployment['id'])
                    
                    return {
                        'id': current_deployment['id'],
                        'status': status,
                        'deployment_logs': deployment_logs,
                        'build_logs': build_logs
                    }
            
            time.sleep(Config.DEPLOYMENT_CHECK_INTERVAL)
        
        print("⏰ Deployment monitoring timeout reached")
        return {
            'status': 'TIMEOUT',
            'deployment_logs': 'Deployment monitoring timeout',
            'build_logs': 'No build logs available'
        }
