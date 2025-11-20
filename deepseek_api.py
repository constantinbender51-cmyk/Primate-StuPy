import json
import requests
import logging
from config import Config

logger = logging.getLogger(__name__)

class DeepSeekAPI:
    def __init__(self):
        self.api_key = Config.DEEPSEEK_API_KEY
        self.api_url = Config.DEEPSEEK_API_URL
        logger.info("🤖 DeepSeek API initialized")
        logger.debug(f"API URL: {self.api_url}")
    
    def call_api(self, prompt: str, system_message: str = None) -> str:
        """Call DeepSeek API with given prompt"""
        logger.info("📡 Calling DeepSeek API...")
        logger.debug(f"System message length: {len(system_message) if system_message else 0} chars")
        logger.debug(f"Prompt length: {len(prompt)} chars")
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        messages = []
        if system_message:
            messages.append({'role': 'system', 'content': system_message})
        
        messages.append({'role': 'user', 'content': prompt})
        
        payload = {
            'model': 'deepseek-coder',
            'messages': messages,
            'temperature': 0.1,
            'max_tokens': 4000
        }
        
        logger.debug(f"Request payload: model={payload['model']}, temp={payload['temperature']}, max_tokens={payload['max_tokens']}")
        
        try:
            response = requests.post(self.api_url, headers=headers, json=payload)
            logger.debug(f"API response status: {response.status_code}")
            
            response.raise_for_status()
            result = response.json()
            
            response_content = result['choices'][0]['message']['content']
            logger.info(f"✅ DeepSeek API call successful (response length: {len(response_content)} chars)")
            logger.debug(f"Response preview: {response_content[:200]}...")
            
            return response_content
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ DeepSeek API request failed: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text[:500]}")
            raise
    
    def generate_initial_code(self, instruction: str, codebase: str) -> list:
        """Generate initial code implementation based on user instruction"""
        logger.info("🎨 Generating initial code implementation...")
        logger.debug(f"User instruction: {instruction}")
        logger.debug(f"Codebase length: {len(codebase)} chars")
        
        prompt = f"""
        USER INSTRUCTION: {instruction}
        
        CURRENT CODEBASE:
        {codebase}
        
        Implement this instruction by providing file operations in JSON format:
        
        Available operations:
        - write: Create or overwrite entire file
        - write_at_line: Insert content at specific line number
        - delete: Delete entire file  
        - delete_at_line: Delete specific consecutive lines where content exactly matches
        
        Return JSON array of operations. Example:
        [
            {{"operation": "write", "file": "hello.py", "content": "print('Hello World!')"}},
            {{"operation": "write_at_line", "file": "hello.py", "line": 2, "content": "print('Second line')"}},
            {{"operation": "delete_at_line", "file": "hello.py", "line": 1, "content": "print('Hello World!')"}}
        ]
        
        Only respond with valid JSON array.
        """
        
        try:
            response = self.call_api(prompt, "You are a coding assistant. Create file operations to implement user requirements.")
            instructions = self._parse_instructions(response)
            
            logger.info(f"✅ Generated {len(instructions)} file operations")
            for i, inst in enumerate(instructions, 1):
                logger.debug(f"  Operation {i}: {inst.get('operation')} - {inst.get('file')}")
            
            return instructions
            
        except Exception as e:
            logger.error(f"❌ Failed to generate initial code: {str(e)}")
            raise
    
    def review_deployment(self, instruction: str, codebase: str, deployment_logs: str, build_logs: str, deployment_status: str) -> dict:
        """Review deployment results and decide on approval or revisions"""
        logger.info("🔍 Reviewing deployment results...")
        logger.debug(f"Deployment status: {deployment_status}")
        logger.debug(f"Build logs length: {len(build_logs)} chars")
        logger.debug(f"Deployment logs length: {len(deployment_logs)} chars")
        
        prompt = f"""
        ORIGINAL USER INSTRUCTION: {instruction}
        
        DEPLOYMENT STATUS: {deployment_status}
        
        BUILD LOGS:
        {build_logs}
        
        DEPLOYMENT LOGS:
        {deployment_logs}

        Railway may need language specific files to install dependencies, libraries or packages and to know what file to execute after deployment.
        For python deployments you msy need a requirements.txt and a Procfile.
        
        CURRENT CODEBASE:
        {codebase}
        
        Analyze the deployment results and respond with one of two options:
        
        OPTION 1 - APPROVE: If the deployment was successful and the code correctly implements the instruction, respond with:
        {{"status": "approved", "reason": "Brief explanation of why it's approved"}}
        
        OPTION 2 - REVISE: If deployment failed or code needs improvements, respond with file operations:
        {{
            "status": "revise",
            "reason": "Explanation of what needs fixing",
            "instructions": [
                {{"operation": "write", "file": "filename", "content": "content"}},
                {{"operation": "write_at_line", "file": "filename", "line": 5, "content": "code"}},
                {{"operation": "delete_at_line", "file": "filename", "line": 10, "content": "lines\\nto\\ndelete"}}
            ]
        }}
        
        Only respond with valid JSON, no other text.
        """
        
        system_msg = "You are a deployment reviewer. Analyze deployment logs and code to determine if changes are needed."
        
        try:
            response = self.call_api(prompt, system_msg)
            review_result = json.loads(response.strip())
            
            status = review_result.get('status', 'unknown')
            reason = review_result.get('reason', 'No reason provided')
            
            logger.info(f"📋 Review decision: {status.upper()}")
            logger.info(f"💡 Reason: {reason}")
            
            if status == 'revise':
                revision_count = len(review_result.get('instructions', []))
                logger.info(f"📝 Revision instructions: {revision_count} operations")
                for i, inst in enumerate(review_result.get('instructions', []), 1):
                    logger.debug(f"  Revision {i}: {inst.get('operation')} - {inst.get('file')}")
            
            return review_result
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse review response as JSON: {str(e)}")
            logger.debug(f"Raw response: {response[:500]}")
            return {"status": "revise", "reason": "Failed to parse response", "instructions": []}
        except Exception as e:
            logger.error(f"❌ Deployment review failed: {str(e)}")
            raise
    
    def _parse_instructions(self, response: str) -> list:
        """Parse JSON instructions from DeepSeek response"""
        logger.debug("🔄 Parsing instructions from response...")
        
        cleaned = response.strip()
        if '```json' in cleaned:
            logger.debug("Found ```json code block, extracting...")
            cleaned = cleaned.split('```json')[1].split('```')[0]
        elif '```' in cleaned:
            logger.debug("Found ``` code block, extracting...")
            cleaned = cleaned.split('```')[1].split('```')[0]
        
        try:
            instructions = json.loads(cleaned.strip())
            logger.debug(f"✅ Successfully parsed {len(instructions)} instructions")
            return instructions
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse instructions: {str(e)}")
            logger.debug(f"Attempted to parse: {cleaned[:200]}...")
            return []
