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
        data = response.json()
        
        if 'data' in data and data['data']['deployments']['edges']:
            deployment = data['data']['deployments']['edges'][0]['node']
            return {
                'id': deployment['id'],
                'status': deployment['status'],
                'createdAt': deployment['createdAt']
            }
        return None
    
    def get_deployment_logs(self, deployment_id: str) -> str:
        """Get deployment logs for a specific deployment"""
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
        data = response.json()
        
        if 'data' in data:
            logs = data['data']['deploymentLogs']
            formatted_logs = []
            for log in sorted(logs, key=lambda x: x["timestamp"]):
                formatted_logs.append(f"{log['timestamp']} [{log['severity']}] {log['message']}")
            return "\n".join(formatted_logs)
        return "No deployment logs available"
    
    def get_build_logs(self, deployment_id: str) -> str:
        """Get build logs for a specific deployment"""
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
        data = response.json()
        
        if 'data' in data:
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
        last_deployment = self.get_latest_deployment()
        
        if not last_deployment:
            return None
        
        print(f"🚀 Monitoring deployment: {last_deployment['id']}")
        print(f"📊 Initial status: {last_deployment['status']}")
        
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
        return None
