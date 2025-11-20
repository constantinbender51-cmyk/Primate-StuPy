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

    def get_file_content_and_sha(self, filename: str) -> tuple:
        """Get current file content and SHA from GitHub"""
        logger.debug(f"📖 Getting content and SHA for: {filename}")
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

    def process_file_operations(self, instructions: list) -> dict:
        """Process all file operations locally and return final file contents"""
        logger.info(f"🔄 Processing {len(instructions)} operations locally...")
        
        # Group operations by file
        file_operations = {}
        for instruction in instructions:
            file = instruction['file']
            if file not in file_operations:
                file_operations[file] = []
            file_operations[file].append(instruction)
        
        final_files = {}
        
        for file, operations in file_operations.items():
            logger.info(f"📄 Processing file: {file} ({len(operations)} operations)")
            
            # Get current file content from GitHub
            current_content, sha = self.get_file_content_and_sha(file)
            if current_content is None:
                current_content = ""  # New file
                logger.debug(f"  Creating new file: {file}")
            else:
                logger.debug(f"  Loaded existing file: {file} ({len(current_content)} bytes)")
            
            # Apply operations in correct order
            final_content = self._apply_operations_to_file(file, current_content, operations)
            final_files[file] = {
                'content': final_content,
                'sha': sha,  # Will be None for new files
                'operations': operations
            }
            
            logger.info(f"  ✅ Processed {file}: {len(current_content)} → {len(final_content)} bytes")
        
        return final_files

    def _apply_operations_to_file(self, filename: str, content: str, operations: list) -> str:
        """Apply all operations to a file content and return final version"""
        lines = content.split('\n') if content else []
        
        # Separate operation types
        write_ops = [op for op in operations if op['operation'] == 'write']
        delete_ops = [op for op in operations if op['operation'] == 'delete']
        write_at_line_ops = [op for op in operations if op['operation'] == 'write_at_line']
        delete_at_line_ops = [op for op in operations if op['operation'] == 'delete_at_line']
        
        # Apply operations in correct order
        
        # 1. Handle write operations (complete file overwrite)
        if write_ops:
            if len(write_ops) > 1:
                logger.warning(f"⚠️  Multiple write operations for {filename}, using the last one")
            final_op = write_ops[-1]
            logger.debug(f"  Applying write operation to {filename}")
            return final_op['content']
        
        # 2. Handle delete operations
        if delete_ops:
            logger.debug(f"  Applying delete operation to {filename}")
            return ""  # File deleted
        
        # 3. Apply line-level operations from bottom to top to avoid shifting
        all_line_ops = write_at_line_ops + delete_at_line_ops
        
        # Sort by line number descending (process from bottom up)
        all_line_ops.sort(key=lambda x: x.get('line', 0), reverse=True)
        
        for operation in all_line_ops:
            op_type = operation['operation']
            line_num = operation['line']
            op_content = operation['content']
            
            if op_type == 'write_at_line':
                lines = self._apply_write_at_line(lines, line_num, op_content, filename)
            elif op_type == 'delete_at_line':
                lines = self._apply_delete_at_line(lines, line_num, op_content, filename)
        
        return '\n'.join(lines)

    def _apply_write_at_line(self, lines: list, line_num: int, content: str, filename: str) -> list:
        """Insert content at specific line number"""
        logger.debug(f"    Inserting at line {line_num} in {filename}")
        
        if line_num < 1 or line_num > len(lines) + 1:
            logger.error(f"    ❌ Invalid line number {line_num} for file with {len(lines)} lines")
            return lines
        
        # Split content into lines to insert
        content_lines = content.split('\n')
        
        # Insert the content
        lines[line_num-1:line_num-1] = content_lines
        logger.debug(f"    ✅ Inserted {len(content_lines)} lines at line {line_num}")
        
        return lines

    def _apply_delete_at_line(self, lines: list, line_num: int, content: str, filename: str) -> list:
        """Delete specific consecutive lines where content matches exactly"""
        logger.debug(f"    Checking deletion at line {line_num} in {filename}")
        
        if line_num < 1 or line_num > len(lines):
            logger.error(f"    ❌ Invalid line number {line_num} for file with {len(lines)} lines")
            return lines
        
        # Calculate the range to check (content might span multiple lines)
        content_lines = content.split('\n')
        end_line = line_num - 1 + len(content_lines)
        
        if end_line > len(lines):
            logger.error(f"    ❌ Delete range {line_num}-{end_line} exceeds file length {len(lines)}")
            return lines
        
        # Check if content matches exactly
        actual_content = '\n'.join(lines[line_num-1:end_line])
        if actual_content == content:
            # Delete the matching lines
            del lines[line_num-1:end_line]
            logger.debug(f"    ✅ Deleted {len(content_lines)} lines starting at line {line_num}")
        else:
            logger.warning(f"    ⚠️  Content mismatch at line {line_num}, skipping deletion")
            logger.debug(f"      Expected: {content[:100]}...")
            logger.debug(f"      Actual: {actual_content[:100]}...")
        
        return lines

    def upload_final_files(self, final_files: dict) -> list:
        """Upload final processed files to GitHub"""
        logger.info(f"📤 Uploading {len(final_files)} files to GitHub...")
        
        results = []
        
        for filename, file_data in final_files.items():
            content = file_data['content']
            sha = file_data['sha']
            operations = file_data['operations']
            
            url = f"{self.api_url}/repos/{self.username}/{self.repo}/contents/{filename}"
            
            # Determine if this is create, update, or delete
            if content == "":  # File deletion
                if sha:  # Only delete if file exists
                    payload = {
                        'message': f'Delete {filename}',
                        'sha': sha
                    }
                    response = requests.delete(url, headers=self.headers, json=payload)
                    success = response.status_code in [200, 204]
                    op_desc = "delete"
                else:
                    logger.warning(f"⚠️  Cannot delete non-existent file: {filename}")
                    success = False
                    op_desc = "delete (skip)"
            else:  # File create or update
                payload = {
                    'message': f'Update {filename}',
                    'content': base64.b64encode(content.encode('utf-8')).decode('utf-8')
                }
                if sha:  # Update existing file
                    payload['sha'] = sha
                    op_desc = "update"
                else:  # Create new file
                    op_desc = "create"
                
                response = requests.put(url, headers=self.headers, json=payload)
                success = response.status_code in [200, 201]
            
            if success:
                results.append(f"✅ {op_desc} {filename}")
                logger.info(f"  ✅ {op_desc} {filename}")
            else:
                results.append(f"❌ {op_desc} {filename}")
                logger.error(f"  ❌ Failed to {op_desc} {filename}: {response.status_code if 'response' in locals() else 'N/A'}")
                if 'response' in locals():
                    logger.debug(f"    Response: {response.text[:200]}")
        
        success_count = sum(1 for r in results if r.startswith('✅'))
        logger.info(f"📊 Upload results: {success_count}/{len(final_files)} files successful")
        
        return results

    def apply_instructions(self, instructions: list) -> list:
        """Main method: process all instructions and upload to GitHub"""
        logger.info(f"🚀 Applying {len(instructions)} instructions...")
        
        if not instructions:
            logger.warning("⚠️  No instructions to apply")
            return ["⚠️  No operations to apply"]
        
        # Process all operations locally
        final_files = self.process_file_operations(instructions)
        
        # Upload final files to GitHub
        results = self.upload_final_files(final_files)
        
        return results

    def clear_repository(self):
        """Delete all files from the repository"""
        logger.info("🗑️ Clearing entire repository...")
        
        try:
            # Get all files in the repository
            url = f"{self.api_url}/repos/{self.username}/{self.repo}/contents/"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code != 200:
                logger.error(f"❌ Failed to list repository contents: {response.status_code}")
                return False, [f"Failed to list repository contents: {response.status_code}"]
            
            items = response.json()
            delete_results = []
            
            for item in items:
                if item['type'] == 'file':
                    logger.debug(f"🗑️ Deleting file: {item['path']}")
                    
                    delete_url = f"{self.api_url}/repos/{self.username}/{self.repo}/contents/{item['path']}"
                    delete_payload = {
                        'message': f'Clear repository: delete {item["path"]}',
                        'sha': item['sha']
                    }
                    
                    delete_response = requests.delete(delete_url, headers=self.headers, json=delete_payload)
                    
                    if delete_response.status_code in [200, 204]:
                        delete_results.append(f"✅ Deleted {item['path']}")
                        logger.info(f"✅ Deleted {item['path']}")
                    else:
                        delete_results.append(f"❌ Failed to delete {item['path']}: {delete_response.status_code}")
                        logger.error(f"❌ Failed to delete {item['path']}: {delete_response.status_code}")
            
            logger.info(f"✅ Repository cleared: {len(delete_results)} files processed")
            return True, delete_results
            
        except Exception as e:
            logger.error(f"❌ Error clearing repository: {str(e)}")
            return False, [f"Error: {str(e)}"]

    def get_repository_info(self):
        """Get basic repository information"""
        logger.debug("📊 Getting repository information...")
        url = f"{self.api_url}/repos/{self.username}/{self.repo}"
        
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                repo_data = response.json()
                return {
                    'name': repo_data['name'],
                    'full_name': repo_data['full_name'],
                    'description': repo_data.get('description', ''),
                    'html_url': repo_data['html_url'],
                    'default_branch': repo_data['default_branch'],
                    'size': repo_data['size'],
                    'updated_at': repo_data['updated_at']
                }
            else:
                logger.error(f"❌ Failed to get repository info: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"❌ Error getting repository info: {str(e)}")
            return None

    def list_files(self, path: str = ""):
        """List files and directories in the repository"""
        logger.debug(f"📁 Listing files in: {path or 'root'}")
        url = f"{self.api_url}/repos/{self.username}/{self.repo}/contents/{path}"
        
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                items = response.json()
                files = []
                directories = []
                
                for item in items:
                    if item['type'] == 'file':
                        files.append({
                            'name': item['name'],
                            'path': item['path'],
                            'size': item['size'],
                            'sha': item['sha']
                        })
                    elif item['type'] == 'dir':
                        directories.append({
                            'name': item['name'],
                            'path': item['path']
                        })
                
                return {
                    'files': files,
                    'directories': directories
                }
            else:
                logger.error(f"❌ Failed to list files: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"❌ Error listing files: {str(e)}")
            return None

    def get_file_history(self, filename: str):
        """Get commit history for a specific file"""
        logger.debug(f"📜 Getting file history for: {filename}")
        url = f"{self.api_url}/repos/{self.username}/{self.repo}/commits"
        params = {'path': filename}
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            if response.status_code == 200:
                commits = response.json()
                return [{
                    'sha': commit['sha'],
                    'message': commit['commit']['message'],
                    'author': commit['commit']['author']['name'],
                    'date': commit['commit']['author']['date']
                } for commit in commits]
            else:
                logger.error(f"❌ Failed to get file history: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"❌ Error getting file history: {str(e)}")
            return None
