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
        self.api_url = "https://backboard.railway.app/graphql/v2"
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }
        logger.info(f"🚂 Railway API initialized for project: {self.project_id[:8]}...")
    
    def _make_graphql_request(self, query: str) -> dict:
        """Make GraphQL request using string formatting (like your working script)"""
        try:
            logger.debug(f"📡 Making GraphQL request: {query[:100]}...")
            response = requests.post(
                self.api_url,
                json={"query": query},
                headers=self.headers,
                timeout=30
            )
            
            logger.debug(f"Railway API response status: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"❌ Railway API request failed: {response.status_code}")
                logger.debug(f"Response: {response.text[:200]}")
                return None
                
            data = response.json()
            
            if 'errors' in data:
                error_messages = [err.get('message', 'Unknown error') for err in data['errors']]
                logger.error(f"❌ GraphQL errors: {error_messages}")
                return None
            
            return data
            
        except requests.exceptions.Timeout:
            logger.error("❌ Railway API: Request timeout")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Railway API network error: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error: {str(e)}")
            return None
    
    def get_latest_deployment(self) -> dict:
        """Get the latest deployment for the project - USING WORKING FORMAT"""
        logger.debug("🔍 Fetching latest deployment...")
        
        query = """
        {
          deployments(input: {projectId: "%s"}, first: 1) {
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
        """ % self.project_id
        
        data = self._make_graphql_request(query)
        
        if not data:
            return None
        
        try:
            deployments = data['data']['deployments']['edges']
            
            if not deployments:
                logger.warning("📭 No deployments found for this project")
                return None
            
            deployment_node = deployments[0]['node']
            deployment_data = {
                'id': deployment_node['id'],
                'status': deployment_node['status'],
                'createdAt': deployment_node['createdAt'],
                'environment': deployment_node.get('environment', {}).get('name', 'unknown')
            }
            
            logger.info(f"✅ Latest deployment: {deployment_data['id'][:12]}... Status: {deployment_data['status']}")
            return deployment_data
            
        except Exception as e:
            logger.error(f"❌ Error parsing deployment data: {str(e)}")
            return None
    
    def get_deployment_logs(self, deployment_id: str) -> str:
        """Get deployment logs for a specific deployment - USING WORKING FORMAT"""
        if not deployment_id:
            return "No deployment ID provided"
        
        logger.debug(f"📜 Fetching deployment logs for: {deployment_id[:12]}...")
        
        query = """
        {
          deploymentLogs(deploymentId: "%s", limit: 500) {
            message
            severity
            timestamp
          }
        }
        """ % deployment_id
        
        data = self._make_graphql_request(query)
        
        if not data:
            return "Error fetching deployment logs"
        
        try:
            logs = data['data']['deploymentLogs']
            if logs:
                formatted_logs = []
                for log in sorted(logs, key=lambda x: x["timestamp"]):
                    formatted_logs.append(f"{log['timestamp']} [{log['severity']}] {log['message']}")
                
                log_output = "\n".join(formatted_logs)
                logger.info(f"✅ Retrieved {len(logs)} deployment log entries")
                return log_output
            else:
                return "No deployment logs available"
                
        except Exception as e:
            return f"Error parsing deployment logs: {str(e)}"
    
    def get_build_logs(self, deployment_id: str) -> str:
        """Get build logs for a specific deployment - USING WORKING FORMAT"""
        if not deployment_id:
            return "No deployment ID provided"
        
        logger.debug(f"🔨 Fetching build logs for: {deployment_id[:12]}...")
        
        query = """
        {
          buildLogs(deploymentId: "%s", limit: 500) {
            message
            severity
            timestamp
          }
        }
        """ % deployment_id
        
        data = self._make_graphql_request(query)
        
        if not data:
            return "Error fetching build logs"
        
        try:
            logs = data['data']['buildLogs']
            if logs:
                formatted_logs = []
                for log in sorted(logs, key=lambda x: x["timestamp"]):
                    formatted_logs.append(f"{log['timestamp']} [{log['severity']}] {log['message']}")
                
                log_output = "\n".join(formatted_logs)
                logger.info(f"✅ Retrieved {len(logs)} build log entries")
                return log_output
            else:
                return "No build logs available"
                
        except Exception as e:
            return f"Error parsing build logs: {str(e)}"
    
    def wait_for_deployment_completion(self, timeout: int = None) -> dict:
        """Wait for deployment completion"""
        if timeout is None:
            timeout = Config.MAX_DEPLOYMENT_WAIT
        
        logger.info(f"⏱️  Starting deployment monitor (timeout: {timeout}s)")
        
        # Get current deployment
        deployment = self.get_latest_deployment()
        
        if not deployment:
            logger.warning("❌ Cannot access deployment information")
            return {
                'status': 'API_ERROR',
                'deployment_logs': 'Cannot access deployment information',
                'build_logs': 'Cannot access build logs'
            }
        
        # Monitor deployment
        start_time = time.time()
        last_status = deployment['status']
        
        logger.info(f"📊 Monitoring deployment: {deployment['id']}, current status: {last_status}")
        
        while time.time() - start_time < timeout:
            current_deployment = self.get_latest_deployment()
            
            if current_deployment and current_deployment['id'] == deployment['id']:
                current_status = current_deployment['status']
                
                if current_status != last_status:
                    logger.info(f"📈 Status changed: {last_status} → {current_status}")
                    last_status = current_status
                
                if current_status in ['SUCCESS', 'FAILED', 'CRASHED', 'NONE']:
                    # Get final logs
                    deployment_logs = self.get_deployment_logs(current_deployment['id'])
                    build_logs = self.get_build_logs(current_deployment['id'])
                    
                    return {
                        'id': current_deployment['id'],
                        'status': current_status,
                        'deployment_logs': deployment_logs,
                        'build_logs': build_logs
                    }
            
            elapsed = int(time.time() - start_time)
            if elapsed % 30 == 0:  # Log every 30 seconds
                logger.info(f"⏳ Still deploying... Status: {last_status} (elapsed: {elapsed}s)")
            
            time.sleep(Config.DEPLOYMENT_CHECK_INTERVAL)
        
        # Timeout reached
        deployment_logs = self.get_deployment_logs(deployment['id'])
        build_logs = self.get_build_logs(deployment['id'])
        
        return {
            'status': 'TIMEOUT',
            'deployment_logs': deployment_logs,
            'build_logs': build_logs,
            'message': f'Deployment monitoring timed out. Last status: {last_status}'
        }
