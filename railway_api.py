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
        self.api_url = Config.RAILWAY_API_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }
        logger.info(f"🚂 Railway API initialized for project: {self.project_id[:8]}...")
        logger.debug(f"API URL: {self.api_url}")
    
    def get_latest_deployment(self) -> dict:
        """Get the latest deployment for the project using proper GraphQL variables"""
        logger.debug("🔍 Fetching latest deployment...")
        
        query = """
        query GetDeployments($projectId: String!) {
          deployments(input: {projectId: $projectId}, first: 1) {
            edges {
              node {
                id
                status
                createdAt
              }
            }
          }
        }
        """
        
        variables = {
            "projectId": self.project_id
        }

        try:
            response = requests.post(
                self.api_url, 
                json={"query": query, "variables": variables}, 
                headers=self.headers
            )
            
            logger.debug(f"Railway API response status: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"❌ Railway API request failed: {response.status_code}")
                logger.debug(f"Response body: {response.text[:500]}")
                return None
                
            data = response.json()
            logger.debug(f"Response data keys: {data.keys()}")
            
            # Check for errors in response
            if 'errors' in data:
                logger.error(f"❌ GraphQL errors: {data['errors']}")
                return None
            
            # Check if data structure is valid and has deployments
            if ('data' not in data or 
                'deployments' not in data['data'] or 
                'edges' not in data['data']['deployments']):
                logger.error("❌ Invalid response structure from Railway API")
                logger.debug(f"Response structure: {data}")
                return None
            
            edges = data['data']['deployments']['edges']
            
            # Check if there are any deployments
            if not edges or len(edges) == 0:
                logger.warning("📭 No deployments found for this project")
                return None
            
            # Safe access to deployment data
            deployment = edges[0]['node']
            result = {
                'id': deployment['id'],
                'status': deployment['status'],
                'createdAt': deployment['createdAt']
            }
            
            logger.info(f"✅ Latest deployment: {result['id'][:12]}... Status: {result['status']}")
            logger.debug(f"Created at: {result['createdAt']}")
            
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Network error fetching deployment: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error fetching deployment: {str(e)}")
            return None
    
    def get_deployment_logs(self, deployment_id: str) -> str:
        """Get deployment logs for a specific deployment using proper GraphQL variables"""
        if not deployment_id:
            logger.warning("⚠️  No deployment ID provided for logs")
            return "No deployment ID provided"
        
        logger.debug(f"📜 Fetching deployment logs for: {deployment_id[:12]}...")
        
        query = """
        query GetDeploymentLogs($deploymentId: String!, $limit: Int) {
          deploymentLogs(deploymentId: $deploymentId, limit: $limit) {
            message
            severity
            timestamp
          }
        }
        """
        
        variables = {
            "deploymentId": deployment_id,
            "limit": 500
        }

        try:
            response = requests.post(
                self.api_url, 
                json={"query": query, "variables": variables}, 
                headers=self.headers
            )
            
            if response.status_code != 200:
                error_msg = f"Failed to fetch deployment logs: {response.status_code}"
                logger.error(f"❌ {error_msg}")
                return error_msg
                
            data = response.json()
            
            if 'errors' in data:
                logger.error(f"❌ GraphQL errors in deployment logs: {data['errors']}")
                return f"GraphQL errors: {data['errors']}"
            
            if 'data' in data and data['data']['deploymentLogs']:
                logs = data['data']['deploymentLogs']
                logger.info(f"✅ Retrieved {len(logs)} deployment log entries")
                
                formatted_logs = []
                for log in sorted(logs, key=lambda x: x["timestamp"]):
                    formatted_logs.append(f"{log['timestamp']} [{log['severity']}] {log['message']}")
                
                return "\n".join(formatted_logs)
            
            logger.warning("⚠️  No deployment logs available")
            return "No deployment logs available"
            
        except Exception as e:
            logger.error(f"❌ Error fetching deployment logs: {str(e)}")
            return f"Error: {str(e)}"
    
    def get_build_logs(self, deployment_id: str) -> str:
        """Get build logs for a specific deployment using proper GraphQL variables"""
        if not deployment_id:
            logger.warning("⚠️  No deployment ID provided for build logs")
            return "No deployment ID provided"
        
        logger.debug(f"🔨 Fetching build logs for: {deployment_id[:12]}...")
        
        query = """
        query GetBuildLogs($deploymentId: String!, $limit: Int) {
          buildLogs(deploymentId: $deploymentId, limit: $limit) {
            message
            severity
            timestamp
          }
        }
        """
        
        variables = {
            "deploymentId": deployment_id,
            "limit": 500
        }

        try:
            response = requests.post(
                self.api_url, 
                json={"query": query, "variables": variables}, 
                headers=self.headers
            )
            
            if response.status_code != 200:
                error_msg = f"Failed to fetch build logs: {response.status_code}"
                logger.error(f"❌ {error_msg}")
                return error_msg
                
            data = response.json()
            
            if 'errors' in data:
                logger.error(f"❌ GraphQL errors in build logs: {data['errors']}")
                return f"GraphQL errors: {data['errors']}"
            
            if 'data' in data and data['data']['buildLogs']:
                logs = data['data']['buildLogs']
                logger.info(f"✅ Retrieved {len(logs)} build log entries")
                
                formatted_logs = []
                for log in sorted(logs, key=lambda x: x["timestamp"]):
                    formatted_logs.append(f"{log['timestamp']} [{log['severity']}] {log['message']}")
                
                return "\n".join(formatted_logs)
            
            logger.warning("⚠️  No build logs available")
            return "No build logs available"
            
        except Exception as e:
            logger.error(f"❌ Error fetching build logs: {str(e)}")
            return f"Error: {str(e)}"
    
    def wait_for_deployment_completion(self, timeout: int = None) -> dict:
        """Wait for the current deployment to complete"""
        if timeout is None:
            timeout = Config.MAX_DEPLOYMENT_WAIT
        
        logger.info(f"⏱️  Starting deployment monitor (timeout: {timeout}s)")
        start_time = time.time()
        
        print("🚀 Checking for deployments...")
        last_deployment = self.get_latest_deployment()
        
        if not last_deployment:
            logger.warning("📭 No existing deployments found, waiting for first deployment...")
            print("📭 No existing deployments found. Waiting for first deployment...")
            
            # Wait for initial deployment to appear
            check_count = 0
            while time.time() - start_time < timeout:
                check_count += 1
                elapsed = int(time.time() - start_time)
                logger.debug(f"Check #{check_count} (elapsed: {elapsed}s) - Looking for new deployment...")
                
                current_deployment = self.get_latest_deployment()
                if current_deployment:
                    logger.info(f"🎯 Found new deployment: {current_deployment['id'][:12]}...")
                    print(f"🎯 Found new deployment: {current_deployment['id']}")
                    last_deployment = current_deployment
                    break
                
                time.sleep(Config.DEPLOYMENT_CHECK_INTERVAL)
            
            if not last_deployment:
                logger.error("❌ No deployment started within timeout period")
                return {
                    'status': 'TIMEOUT',
                    'deployment_logs': 'No deployment started within timeout period',
                    'build_logs': 'No build logs available'
                }
        
        logger.info(f"📊 Monitoring deployment: {last_deployment['id'][:12]}...")
        print(f"📊 Monitoring deployment: {last_deployment['id']}")
        print(f"📈 Initial status: {last_deployment['status']}")
        
        check_count = 0
        while time.time() - start_time < timeout:
            check_count += 1
            elapsed = int(time.time() - start_time)
            
            current_deployment = self.get_latest_deployment()
            
            if current_deployment and current_deployment['id'] == last_deployment['id']:
                status = current_deployment['status']
                logger.debug(f"Check #{check_count} (elapsed: {elapsed}s) - Status: {status}")
                
                if status in ['SUCCESS', 'FAILED', 'CRASHED', 'NONE']:
                    logger.info(f"🏁 Deployment completed with status: {status}")
                    print(f"📊 Deployment completed with status: {status}")
                    
                    # Get logs
                    logger.debug("Fetching deployment and build logs...")
                    deployment_logs = self.get_deployment_logs(current_deployment['id'])
                    build_logs = self.get_build_logs(current_deployment['id'])
                    
                    result = {
                        'id': current_deployment['id'],
                        'status': status,
                        'deployment_logs': deployment_logs,
                        'build_logs': build_logs
                    }
                    
                    logger.info(f"✅ Deployment monitoring complete")
                    logger.debug(f"Deployment logs: {len(deployment_logs)} chars")
                    logger.debug(f"Build logs: {len(build_logs)} chars")
                    
                    return result
                else:
                    if check_count % 5 == 0:  # Log every 5th check
                        logger.info(f"⏳ Still deploying... Status: {status} (elapsed: {elapsed}s)")
            
            time.sleep(Config.DEPLOYMENT_CHECK_INTERVAL)
        
        elapsed = int(time.time() - start_time)
        logger.warning(f"⏰ Deployment monitoring timeout reached after {elapsed}s")
        print("⏰ Deployment monitoring timeout reached")
        
        return {
            'status': 'TIMEOUT',
            'deployment_logs': 'Deployment monitoring timeout',
            'build_logs': 'No build logs available'
        }
