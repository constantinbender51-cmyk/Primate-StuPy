import base64
import requests
import logging
from config import Config

logger = logging.getLogger(__name__)

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
        logger.info(f"🐙 GitHub API initialized for {self.username}/{self.repo}")
    
    def get_entire_codebase(self) -> str:
        """Get all files and their contents from the repository"""
        logger.info("📁 Fetching entire codebase from GitHub...")
        url = f"{self.api_url}/repos/{self.username}/{self.repo}/contents/"
        logger.debug(f"Request URL: {url}")
        
        try:
            response = requests.get(url, headers=self.headers)
            logger.debug(f"Response status: {response.status_code}")
            
            if response.status_code != 200:
                logger.warning(f"⚠️  Cannot access repository contents: {response.status_code}")
                return "Empty repository or cannot access files"
            
            codebase = []
            items = response.json()
            logger.info(f"📊 Found {len(items)} items in repository")
            
            for item in items:
                if item['type'] == 'file':
                    file_name = item['path']
                    logger.debug(f"📄 Reading file: {file_name}")
                    
                    file_url = item['url']
                    file_response = requests.get(file_url, headers=self.headers)
                    
                    if file_response.status_code == 200:
                        file_data = file_response.json()
                        if file_data.get('encoding') == 'base64':
                            content = base64.b64decode(file_data['content']).decode('utf-8')
                            content_lines = len(content.split('\n'))
                            logger.debug(f"  ✓ {file_name}: {content_lines} lines, {len(content)} bytes")
                            codebase.append(f"--- {item['path']} ---\n{content}\n")
                    else:
                        logger.warning(f"  ✗ Failed to read {file_name}: {file_response.status_code}")
            
            result = "\n".join(codebase) if codebase else "Empty repository"
            logger.info(f"✅ Codebase fetched: {len(codebase)} files, {len(result)} total chars")
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch codebase: {str(e)}")
            raise
    
    def get_file_content(self, filename: str) -> tuple:
        """Get current file content and SHA from GitHub"""
        logger.debug(f"📖 Getting content for: {filename}")
        url = f"{self.api_url}/repos/{self.username}/{self.repo}/contents/{filename}"
        
        try:
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                file_data = response.json()
                content = base64.b64decode(file_data['content']).decode('utf-8')
                sha = file_data['sha']
                logger.debug(f"  ✓ Retrieved {filename}: {len(content)} bytes, SHA: {sha[:8]}...")
                return content, sha
            else:
                logger.debug(f"  ✗ File not found: {filename} (status: {response.status_code})")
                return None, None
                
        except Exception as e:
            logger.error(f"❌ Error getting file content for {filename}: {str(e)}")
            return None, None
    
    def apply_instruction(self, instruction: dict) -> bool:
        """Apply a single file operation to GitHub"""
        op = instruction['operation']
        file = instruction['file']
        
        logger.info(f"🔧 Applying operation: {op} on {file}")
        logger.debug(f"Full instruction: {instruction}")
        
        url = f"{self.api_url}/repos/{self.username}/{self.repo}/contents/{file}"

        try:
            if op == 'write':
                content = instruction['content']
                logger.debug(f"Writing {len(content)} bytes to {file}")
                
                payload = {
                    'message': f'Write {file}',
                    'content': base64.b64encode(content.encode('utf-8')).decode('utf-8')
                }
                
                response = requests.put(url, headers=self.headers, json=payload)
                success = response.status_code in [200, 201]
                
                if success:
                    logger.info(f"✅ Successfully wrote {file}")
                else:
                    logger.error(f"❌ Failed to write {file}: {response.status_code}")
                    logger.debug(f"Response: {response.text[:200]}")
                
                return success

            elif op == 'delete':
                current_content, sha = self.get_file_content(file)
                if not sha:
                    logger.warning(f"⚠️  Cannot delete {file}: file not found")
                    return False
                
                logger.debug(f"Deleting {file} with SHA: {sha[:8]}...")
                payload = {
                    'message': f'Delete {file}',
                    'sha': sha
                }
                
                response = requests.delete(url, headers=self.headers, json=payload)
                success = response.status_code in [200, 204]
                
                if success:
                    logger.info(f"✅ Successfully deleted {file}")
                else:
                    logger.error(f"❌ Failed to delete {file}: {response.status_code}")
                
                return success

            elif op == 'insert':
                line = instruction['line']
                content_to_insert = instruction['content']
                
                logger.debug(f"Inserting content at line {line} in {file}")
                current_content, sha = self.get_file_content(file)
                
                if current_content is None:
                    logger.debug(f"File {file} doesn't exist, creating new file")
                    payload = {
                        'message': f'Create {file} with insert at line {line}',
                        'content': base64.b64encode(content_to_insert.encode('utf-8')).decode('utf-8')
                    }
                    response = requests.put(url, headers=self.headers, json=payload)
                    success = response.status_code in [200, 201]
                    
                    if success:
                        logger.info(f"✅ Created {file} with inserted content")
                    else:
                        logger.error(f"❌ Failed to create {file}: {response.status_code}")
                    
                    return success
                
                lines = current_content.split('\n')
                total_lines = len(lines)
                logger.debug(f"Current file has {total_lines} lines")
                
                if line < 1 or line > total_lines + 1:
                    logger.error(f"❌ Invalid line number {line} for file with {total_lines} lines")
                    return False
                
                lines.insert(line - 1, content_to_insert)
                new_content = '\n'.join(lines)
                
                payload = {
                    'message': f'Insert at line {line} in {file}',
                    'content': base64.b64encode(new_content.encode('utf-8')).decode('utf-8'),
                    'sha': sha
                }
                
                response = requests.put(url, headers=self.headers, json=payload)
                success = response.status_code in [200, 201]
                
                if success:
                    logger.info(f"✅ Successfully inserted content at line {line} in {file}")
                else:
                    logger.error(f"❌ Failed to insert in {file}: {response.status_code}")
                
                return success

            elif op == 'delete_from':
                line = instruction['line']
                content_to_delete = instruction['content']
                
                logger.debug(f"Deleting content from line {line} in {file}")
                current_content, sha = self.get_file_content(file)
                
                if not current_content:
                    logger.warning(f"⚠️  Cannot delete from {file}: file not found")
                    return False
                
                lines = current_content.split('\n')
                if line < 1 or line > len(lines):
                    logger.error(f"❌ Invalid line number {line} for file with {len(lines)} lines")
                    return False
                
                target_line_content = lines[line - 1] if line - 1 < len(lines) else ""
                
                if content_to_delete in target_line_content:
                    logger.debug(f"Found matching content at line {line}, deleting...")
                    del lines[line - 1]
                    new_content = '\n'.join(lines)
                    
                    payload = {
                        'message': f'Delete content from line {line} in {file}',
                        'content': base64.b64encode(new_content.encode('utf-8')).decode('utf-8'),
                        'sha': sha
                    }
                    
                    response = requests.put(url, headers=self.headers, json=payload)
                    success = response.status_code in [200, 201]
                    
                    if success:
                        logger.info(f"✅ Successfully deleted line {line} from {file}")
                    else:
                        logger.error(f"❌ Failed to delete from {file}: {response.status_code}")
                    
                    return success
                else:
                    logger.warning(f"⚠️  Content '{content_to_delete}' not found at line {line}")
                    return False
            
            else:
                logger.error(f"❌ Unknown operation: {op}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Exception during {op} on {file}: {str(e)}")
            return False
    
    def apply_instructions(self, instructions: list) -> list:
        """Apply all instructions to GitHub and return results"""
        logger.info(f"📦 Applying {len(instructions)} instructions to GitHub...")
        
        results = []
        for i, instruction in enumerate(instructions, 1):
            logger.debug(f"Processing instruction {i}/{len(instructions)}")
            
            success = self.apply_instruction(instruction)
            op = instruction['operation']
            file = instruction['file']
            
            if success:
                results.append(f"✅ {op} {file}")
            else:
                results.append(f"❌ {op} {file}")
        
        success_count = sum(1 for r in results if r.startswith('✅'))
        logger.info(f"📊 Results: {success_count}/{len(instructions)} operations successful")
        
        return results
