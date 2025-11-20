import os
import requests
import time
import logging
from config import Config

logger = logging.getLogger(__name__)

class RailwayAPI:
    def __init__(self):
        self.api_token = Config.RAILWAY_API_TOKEN
        self.project_id = Config.RAILWAY_TARGET_PROJECT_ID
        self.rest_api_url = "https://api.railway.app/graphql/v2"  # Keep GraphQL endpoint
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }
        logger.info(f"🚂 Railway API initialized for project: {self.project_id[:8]}...")
    
    def get_latest_deployment(self) -> dict:
        """Get the latest deployment using REST API approach"""
        logger.debug("🔍 Fetching latest deployment via REST API...")
        
        query = """
        query GetDeployments($projectId: String!) {
          deployments(input: {projectId: $projectId}, first: 1) {
            edges {
              node {
                id
                status
                createdAt
                environment {
                  name
                }
              }
            }
          }
        }
        """
        
        variables = {"projectId": self.project_id}

        try:
            response = requests.post(
                self.rest_api_url,
                json={"query": query, "variables": variables},
                headers=self.headers,
                timeout=30
            )
            
            logger.debug(f"Railway API response status: {response.status_code}")
            
            if response.status_code == 401:
                logger.error("❌ Railway API: Unauthorized - Check your API token permissions")
                return None
            elif response.status_code == 403:
                logger.error("❌ Railway API: Forbidden - Token lacks required permissions")
                return None
            elif response.status_code != 200:
                logger.error(f"❌ Railway API request failed: {response.status_code}")
                return None
                
            data = response.json()
            
            # Check for GraphQL errors
            if 'errors' in data:
                for error in data['errors']:
                    if 'Not Authorized' in error.get('message', ''):
                        logger.error("❌ Railway API: Not Authorized - Token needs project read permissions")
                    else:
                        logger.error(f"❌ Railway API GraphQL error: {error.get('message')}")
                return None
            
            # Extract deployment data
            deployments = data.get('data', {}).get('deployments', {}).get('edges', [])
            
            if not deployments:
                logger.warning("📭 No deployments found for this project")
                return None
            
            deployment_node = deployments[0]['node']
            result = {
                'id': deployment_node['id'],
                'status': deployment_node['status'],
                'createdAt': deployment_node['createdAt']
            }
            
            logger.info(f"✅ Latest deployment: {result['id'][:12]}... Status: {result['status']}")
            return result
            
        except requests.exceptions.Timeout:
            logger.error("❌ Railway API: Request timeout")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Railway API network error: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error fetching deployment: {str(e)}")
            return None
    
    def get_deployment_logs(self, deployment_id: str) -> str:
        """Get deployment logs with better error handling"""
        if not deployment_id:
            return "No deployment ID provided"
        
        logger.debug(f"📜 Fetching deployment logs for: {deployment_id[:12]}...")
        
        query = """
        query GetDeploymentLogs($deploymentId: String!) {
          deploymentLogs(deploymentId: $deploymentId) {
            message
            severity
            timestamp
          }
        }
        """
        
        variables = {"deploymentId": deployment_id}

        try:
            response = requests.post(
                self.rest_api_url,
                json={"query": query, "variables": variables},
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code != 200:
                return f"Failed to fetch logs: {response.status_code}"
                
            data = response.json()
            
            if 'errors' in data:
                return f"GraphQL errors: {data['errors']}"
            
            logs = data.get('data', {}).get('deploymentLogs', [])
            if logs:
                formatted_logs = []
                for log in sorted(logs, key=lambda x: x["timestamp"]):
                    formatted_logs.append(f"{log['timestamp']} [{log['severity']}] {log['message']}")
                return "\n".join(formatted_logs[:50])  # Limit to first 50 lines
            
            return "No deployment logs available"
            
        except Exception as e:
            return f"Error fetching logs: {str(e)}"
    
    def get_build_logs(self, deployment_id: str) -> str:
        """Get build logs with better error handling"""
        if not deployment_id:
            return "No deployment ID provided"
        
        logger.debug(f"🔨 Fetching build logs for: {deployment_id[:12]}...")
        
        query = """
        query GetBuildLogs($deploymentId: String!) {
          buildLogs(deploymentId: $deploymentId) {
            message
            severity
            timestamp
          }
        }
        """
        
        variables = {"deploymentId": deployment_id}

        try:
            response = requests.post(
                self.rest_api_url,
                json={"query": query, "variables": variables},
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code != 200:
                return f"Failed to fetch build logs: {response.status_code}"
                
            data = response.json()
            
            if 'errors' in data:
                return f"GraphQL errors: {data['errors']}"
            
            logs = data.get('data', {}).get('buildLogs', [])
            if logs:
                formatted_logs = []
                for log in sorted(logs, key=lambda x: x["timestamp"]):
                    formatted_logs.append(f"{log['timestamp']} [{log['severity']}] {log['message']}")
                return "\n".join(formatted_logs[:50])  # Limit to first 50 lines
            
            return "No build logs available"
            
        except Exception as e:
            return f"Error fetching build logs: {str(e)}"
    
    def wait_for_deployment_completion(self, timeout: int = None) -> dict:
        """Wait for deployment completion with fallback options"""
        if timeout is None:
            timeout = Config.MAX_DEPLOYMENT_WAIT
        
        logger.info(f"⏱️  Starting deployment monitor (timeout: {timeout}s)")
        
        # Try to get current deployment
        deployment = self.get_latest_deployment()
        
        if not deployment:
            logger.warning("❌ Cannot access deployment information")
            return {
                'status': 'API_ERROR',
                'deployment_logs': 'Cannot access Railway API - check token permissions',
                'build_logs': 'Cannot access build logs - check token permissions'
            }
        
        # Monitor deployment
        start_time = time.time()
        check_count = 0
        
        logger.info(f"📊 Monitoring deployment: {deployment['id']}")
        
        while time.time() - start_time < timeout:
            check_count += 1
            elapsed = int(time.time() - start_time)
            
            current_deployment = self.get_latest_deployment()
            
            if current_deployment and current_deployment['id'] == deployment['id']:
                status = current_deployment['status']
                
                if status in ['SUCCESS', 'FAILED', 'CRASHED', 'NONE']:
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
        
        # Timeout reached
        return {
            'status': 'TIMEOUT',
            'deployment_logs': 'Deployment monitoring timeout',
            'build_logs': 'Build logs unavailable due to timeout'
        }
