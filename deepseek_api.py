import json
import requests
from config import Config

class DeepSeekAPI:
    def __init__(self):
        self.api_key = Config.DEEPSEEK_API_KEY
        self.api_url = Config.DEEPSEEK_API_URL
    
    def call_api(self, prompt: str, system_message: str = None) -> str:
        """Call DeepSeek API with given prompt"""
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
        
        response = requests.post(self.api_url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    
    def generate_initial_code(self, instruction: str, codebase: str) -> list:
        """Generate initial code implementation based on user instruction"""
        prompt = f"""
        USER INSTRUCTION: {instruction}
        
        CURRENT CODEBASE:
        {codebase}
        
        Implement this instruction by providing file operations in JSON format:
        
        Available operations:
        - write: Create or overwrite file
        - delete: Delete file  
        - insert: Insert at line
        - delete_from: Delete content from line
        
        Return JSON array of operations. Example:
        [
            {{"operation": "write", "file": "hello.py", "content": "print('Hello World!')"}}
        ]
        
        Only respond with valid JSON array.
        """
        
        response = self.call_api(prompt, "You are a coding assistant. Create file operations to implement user requirements.")
        return self._parse_instructions(response)
    
    def review_deployment(self, instruction: str, codebase: str, deployment_logs: str, build_logs: str, deployment_status: str) -> dict:
        """Review deployment results and decide on approval or revisions"""
        prompt = f"""
        ORIGINAL USER INSTRUCTION: {instruction}
        
        DEPLOYMENT STATUS: {deployment_status}
        
        BUILD LOGS:
        {build_logs}
        
        DEPLOYMENT LOGS:
        {deployment_logs}
        
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
                {{"operation": "insert", "file": "filename", "line": 5, "content": "code"}}
            ]
        }}
        
        Only respond with valid JSON, no other text.
        """
        
        system_msg = "You are a deployment reviewer. Analyze deployment logs and code to determine if changes are needed."
        response = self.call_api(prompt, system_msg)
        
        try:
            return json.loads(response.strip())
        except json.JSONDecodeError:
            return {"status": "revise", "reason": "Failed to parse response", "instructions": []}
    
    def _parse_instructions(self, response: str) -> list:
        """Parse JSON instructions from DeepSeek response"""
        cleaned = response.strip()
        if '```json' in cleaned:
            cleaned = cleaned.split('```json')[1].split('```')[0]
        elif '```' in cleaned:
            cleaned = cleaned.split('```')[1].split('```')[0]
        
        try:
            return json.loads(cleaned.strip())
        except json.JSONDecodeError:
            return []
