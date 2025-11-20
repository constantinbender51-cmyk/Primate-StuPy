import base64
import requests
from config import Config

class GitHubAPI:
    def __init__(self):
        self.token = Config.GITHUB_TOKEN
        self.username = Config.GITHUB_USERNAME
        self.repo = Config.GITHUB_REPO
        self.api_url = Config.GITHUB_API_URL
        self.headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json'
        }
    
    def get_entire_codebase(self) -> str:
        """Get all files and their contents from the repository"""
        url = f"{self.api_url}/repos/{self.username}/{self.repo}/contents/"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code != 200:
            return "Empty repository or cannot access files"
        
        codebase = []
        items = response.json()
        
        for item in items:
            if item['type'] == 'file':
                file_url = item['url']
                file_response = requests.get(file_url, headers=self.headers)
                
                if file_response.status_code == 200:
                    file_data = file_response.json()
                    if file_data.get('encoding') == 'base64':
                        content = base64.b64decode(file_data['content']).decode('utf-8')
                        codebase.append(f"--- {item['path']} ---\n{content}\n")
        
        return "\n".join(codebase) if codebase else "Empty repository"
    
    def get_file_content(self, filename: str) -> tuple:
        """Get current file content and SHA from GitHub"""
        url = f"{self.api_url}/repos/{self.username}/{self.repo}/contents/{filename}"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            file_data = response.json()
            content = base64.b64decode(file_data['content']).decode('utf-8')
            return content, file_data['sha']
        return None, None
    
    def apply_instruction(self, instruction: dict) -> bool:
        """Apply a single file operation to GitHub"""
        op = instruction['operation']
        file = instruction['file']
        url = f"{self.api_url}/repos/{self.username}/{self.repo}/contents/{file}"

        if op == 'write':
            payload = {
                'message': f'Write {file}',
                'content': base64.b64encode(instruction['content'].encode('utf-8')).decode('utf-8')
            }
            response = requests.put(url, headers=self.headers, json=payload)
            return response.status_code in [200, 201]

        elif op == 'delete':
            current_content, sha = self.get_file_content(file)
            if not sha:
                return False
            
            payload = {
                'message': f'Delete {file}',
                'sha': sha
            }
            response = requests.delete(url, headers=self.headers, json=payload)
            return response.status_code in [200, 204]

        elif op == 'insert':
            line = instruction['line']
            content_to_insert = instruction['content']
            
            current_content, sha = self.get_file_content(file)
            if current_content is None:
                payload = {
                    'message': f'Create {file} with insert at line {line}',
                    'content': base64.b64encode(content_to_insert.encode('utf-8')).decode('utf-8')
                }
                response = requests.put(url, headers=self.headers, json=payload)
                return response.status_code in [200, 201]
            
            lines = current_content.split('\n')
            if line < 1 or line > len(lines) + 1:
                return False
            
            lines.insert(line - 1, content_to_insert)
            new_content = '\n'.join(lines)
            
            payload = {
                'message': f'Insert at line {line} in {file}',
                'content': base64.b64encode(new_content.encode('utf-8')).decode('utf-8'),
                'sha': sha
            }
            response = requests.put(url, headers=self.headers, json=payload)
            return response.status_code in [200, 201]

        elif op == 'delete_from':
            line = instruction['line']
            content_to_delete = instruction['content']
            
            current_content, sha = self.get_file_content(file)
            if not current_content:
                return False
            
            lines = current_content.split('\n')
            if line < 1 or line > len(lines):
                return False
            
            target_line_content = lines[line - 1] if line - 1 < len(lines) else ""
            if content_to_delete in target_line_content:
                del lines[line - 1]
                new_content = '\n'.join(lines)
                
                payload = {
                    'message': f'Delete content from line {line} in {file}',
                    'content': base64.b64encode(new_content.encode('utf-8')).decode('utf-8'),
                    'sha': sha
                }
                response = requests.put(url, headers=self.headers, json=payload)
                return response.status_code in [200, 201]
            else:
                return False

        return False
    
    def apply_instructions(self, instructions: list) -> list:
        """Apply all instructions to GitHub and return results"""
        results = []
        for instruction in instructions:
            success = self.apply_instruction(instruction)
            op = instruction['operation']
            file = instruction['file']
            if success:
                results.append(f"✅ {op} {file}")
            else:
                results.append(f"❌ {op} {file}")
        return results
