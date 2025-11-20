#!/usr/bin/env python3
"""
Simple Web Service for Coding Agent
Uses Flask to serve a website and handle user instructions
"""

from flask import Flask, request, jsonify, render_template_string, Response
import threading
from main import CodingAgent
import json
import time
import logging
from io import StringIO
import sys
from github_api import GitHubAPI

app = Flask(__name__)

# Store job statuses and log handlers
jobs = {}
log_handlers = {}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>AI Coding Agent</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 1000px; margin: 0 auto; padding: 20px; }
        .container { background: #f5f5f5; padding: 20px; border-radius: 10px; }
        textarea { width: 100%; height: 100px; margin: 10px 0; padding: 10px; }
        button { background: #007cba; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
        button:hover { background: #005a87; }
        button:disabled { background: #cccccc; cursor: not-allowed; }
        .job { background: white; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 5px solid #007cba; }
        .status-completed { color: green; border-left-color: green; }
        .status-processing { color: orange; border-left-color: orange; }
        .status-error { color: red; border-left-color: red; }
        .status-cleaning { color: blue; border-left-color: blue; }
        .log-container { background: #1e1e1e; color: #fff; padding: 15px; border-radius: 5px; font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace; 
                        white-space: pre-wrap; max-height: 400px; overflow-y: auto; font-size: 12px; line-height: 1.4; }
        .log-entry { margin: 2px 0; }
        .log-debug { color: #888; }
        .log-info { color: #fff; }
        .log-warning { color: #ffa500; }
        .log-error { color: #ff4444; }
        .timestamp { color: #6a9955; }
        .clear-repo { background: #dc3545; margin-left: 10px; }
        .clear-repo:hover { background: #c82333; }
        .controls { display: flex; justify-content: space-between; align-items: center; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 AI Coding Agent</h1>
        <p>Describe what you want to build, and the AI will code and deploy it automatically!</p>
        
        <form id="instructionForm">
            <textarea name="instruction" placeholder="Example: Create a Python web server that returns 'Hello World' and has a /health endpoint" required></textarea>
            <br>
            <div class="controls">
                <button type="submit" id="submitBtn">Start Coding & Deployment</button>
                <button type="button" id="clearRepoBtn" class="clear-repo">Clear Repository First</button>
            </div>
            <div>
                <input type="checkbox" id="clearRepoCheckbox" checked>
                <label for="clearRepoCheckbox">Clear repository before starting (recommended)</label>
            </div>
        </form>
        
        <div id="results">
            <h2>Active Jobs</h2>
            <div id="jobList"></div>
        </div>
    </div>

    <script>
        let eventSource = null;
        let currentJobId = null;
        
        document.getElementById('instructionForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            const instruction = formData.get('instruction');
            const clearRepo = document.getElementById('clearRepoCheckbox').checked;
            
            // Disable button during processing
            document.getElementById('submitBtn').disabled = true;
            document.getElementById('clearRepoBtn').disabled = true;
            
            const response = await fetch('/implement', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    instruction: instruction,
                    clear_repo: clearRepo
                })
            });
            
            const result = await response.json();
            if (result.job_id) {
                currentJobId = result.job_id;
                startMonitoring(result.job_id);
            } else {
                // Re-enable buttons on error
                document.getElementById('submitBtn').disabled = false;
                document.getElementById('clearRepoBtn').disabled = false;
            }
        });
        
        document.getElementById('clearRepoBtn').addEventListener('click', async function() {
            if (!confirm('Are you sure you want to clear the entire repository? This will delete all files.')) {
                return;
            }
            
            this.disabled = true;
            document.getElementById('submitBtn').disabled = true;
            
            const response = await fetch('/clear-repository', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            const result = await response.json();
            alert(result.message);
            
            this.disabled = false;
            document.getElementById('submitBtn').disabled = false;
        });
        
        function startMonitoring(jobId) {
            if (eventSource) {
                eventSource.close();
            }
            
            eventSource = new EventSource(`/stream/${jobId}`);
            
            eventSource.onmessage = function(event) {
                const data = JSON.parse(event.data);
                updateJobStatus(jobId, data);
                
                // Re-enable buttons when job is complete
                if (data.status === 'completed' || data.status === 'error') {
                    document.getElementById('submitBtn').disabled = false;
                    document.getElementById('clearRepoBtn').disabled = false;
                }
            };
            
            eventSource.onerror = function(event) {
                console.error('EventSource failed:', event);
                document.getElementById('submitBtn').disabled = false;
                document.getElementById('clearRepoBtn').disabled = false;
            };
        }
        
        function updateJobStatus(jobId, data) {
            let jobList = document.getElementById('jobList');
            let existingJob = document.getElementById(`job-${jobId}`);
            
            if (!existingJob) {
                existingJob = document.createElement('div');
                existingJob.id = `job-${jobId}`;
                existingJob.className = 'job';
                jobList.prepend(existingJob); // Add new jobs at the top
            }
            
            // Update class based on status
            existingJob.className = `job status-${data.status}`;
            
            const logsHtml = data.logs ? data.logs.split('\n').map(line => {
                let cssClass = 'log-entry';
                if (line.includes('DEBUG]')) cssClass += ' log-debug';
                else if (line.includes('INFO]')) cssClass += ' log-info';
                else if (line.includes('WARNING]')) cssClass += ' log-warning';
                else if (line.includes('ERROR]')) cssClass += ' log-error';
                return `<div class="${cssClass}">${line}</div>`;
            }).join('') : '';
            
            existingJob.innerHTML = `
                <h3>Job: ${jobId}</h3>
                <p><strong>Instruction:</strong> ${data.instruction || 'N/A'}</p>
                <p><strong>Status:</strong> ${data.status}</p>
                <p><strong>Message:</strong> ${data.message || 'Processing...'}</p>
                ${logsHtml ? `<div class="log-container">${logsHtml}</div>` : '<div class="log-container">Waiting for logs...</div>'}
                ${data.status === 'completed' ? '<p style="color: green;">🎉 Deployment completed successfully!</p>' : ''}
                ${data.status === 'error' ? '<p style="color: red;">❌ An error occurred during processing.</p>' : ''}
            `;
            
            // Auto-scroll to bottom of log container
            const logContainer = existingJob.querySelector('.log-container');
            if (logContainer) {
                logContainer.scrollTop = logContainer.scrollHeight;
            }
        }
        
        // Clean up EventSource when leaving page
        window.addEventListener('beforeunload', function() {
            if (eventSource) {
                eventSource.close();
            }
        });
    </script>
</body>
</html>
"""

class LogCaptureHandler(logging.Handler):
    """Custom logging handler to capture logs in real-time"""
    
    def __init__(self, job_id):
        super().__init__()
        self.job_id = job_id
        self.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
    
    def emit(self, record):
        log_entry = self.format(record)
        if self.job_id in jobs:
            if 'logs' not in jobs[self.job_id]:
                jobs[self.job_id]['logs'] = ''
            jobs[self.job_id]['logs'] += log_entry + '\n'

def clear_repository():
    """Clear all files from the repository"""
    github = GitHubAPI()
    try:
        # Get all files in the repository
        url = f"{github.api_url}/repos/{github.username}/{github.repo}/contents/"
        response = requests.get(url, headers=github.headers)
        
        if response.status_code == 200:
            items = response.json()
            delete_results = []
            
            for item in items:
                if item['type'] == 'file':
                    delete_url = f"{github.api_url}/repos/{github.username}/{github.repo}/contents/{item['path']}"
                    delete_payload = {
                        'message': f'Clear repository: delete {item["path"]}',
                        'sha': item['sha']
                    }
                    delete_response = requests.delete(delete_url, headers=github.headers, json=delete_payload)
                    
                    if delete_response.status_code in [200, 204]:
                        delete_results.append(f"✅ Deleted {item['path']}")
                    else:
                        delete_results.append(f"❌ Failed to delete {item['path']}: {delete_response.status_code}")
            
            return True, delete_results
        else:
            return False, [f"Failed to list repository contents: {response.status_code}"]
            
    except Exception as e:
        return False, [f"Error clearing repository: {str(e)}"]

def run_agent_job(job_id, instruction, clear_repo=False):
    """Run the coding agent in a separate thread"""
    try:
        # Set up log capture
        log_handler = LogCaptureHandler(job_id)
        root_logger = logging.getLogger()
        root_logger.addHandler(log_handler)
        
        jobs[job_id] = {
            'status': 'cleaning' if clear_repo else 'processing', 
            'instruction': instruction,
            'message': 'Cleaning repository...' if clear_repo else 'Starting coding agent...',
            'logs': ''
        }
        
        # Clear repository if requested
        if clear_repo:
            success, results = clear_repository()
            for result in results:
                logging.info(result)
            
            if not success:
                jobs[job_id].update({
                    'status': 'error',
                    'message': 'Failed to clear repository'
                })
                root_logger.removeHandler(log_handler)
                return
        
        jobs[job_id].update({
            'status': 'processing',
            'message': 'Running coding agent...'
        })
        
        # Initialize and run the agent
        agent = CodingAgent()
        agent.run(instruction)
        
        jobs[job_id].update({
            'status': 'completed',
            'message': 'Code implemented and deployed successfully'
        })
        
        # Clean up log handler
        root_logger.removeHandler(log_handler)
        
    except Exception as e:
        error_msg = f"Error in job execution: {str(e)}"
        logging.error(error_msg)
        jobs[job_id].update({
            'status': 'error',
            'message': error_msg
        })
        
        # Clean up log handler in case of error
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            if isinstance(handler, LogCaptureHandler) and handler.job_id == job_id:
                root_logger.removeHandler(handler)

@app.route('/')
def index():
    """Serve the main website"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/implement', methods=['POST'])
def implement_code():
    """Handle user instruction and start coding process"""
    data = request.get_json()
    user_instruction = data.get('instruction', '').strip()
    clear_repo = data.get('clear_repo', False)
    
    if not user_instruction:
        return jsonify({"error": "No instruction provided"}), 400
    
    # Generate job ID
    job_id = f"job_{int(time.time())}"
    
    # Start processing in background thread
    thread = threading.Thread(
        target=run_agent_job, 
        args=(job_id, user_instruction, clear_repo)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "job_id": job_id,
        "status": "started",
        "message": "Coding agent started processing your request",
        "instruction": user_instruction,
        "clear_repo": clear_repo
    })

@app.route('/clear-repository', methods=['POST'])
def clear_repo_endpoint():
    """Clear the entire repository"""
    try:
        success, results = clear_repository()
        return jsonify({
            "success": success,
            "message": "Repository cleared successfully" if success else "Failed to clear repository",
            "results": results
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error clearing repository: {str(e)}"
        }), 500

@app.route('/status/<job_id>')
def get_status(job_id):
    """Get current status of a job"""
    job = jobs.get(job_id, {'status': 'unknown'})
    return jsonify(job)

@app.route('/stream/<job_id>')
def stream_status(job_id):
    """Server-sent events for real-time status updates"""
    def generate():
        last_log_length = 0
        while True:
            job = jobs.get(job_id, {})
            
            # Only send updates if there are new logs
            current_logs = job.get('logs', '')
            current_log_length = len(current_logs)
            
            if current_log_length > last_log_length:
                # Only send the new portion of logs to reduce bandwidth
                job['logs'] = current_logs  # Send full logs for simplicity
                last_log_length = current_log_length
            
            yield f"data: {json.dumps(job)}\n\n"
            
            if job.get('status') in ['completed', 'error']:
                # Send a few more updates after completion to ensure client gets final logs
                for _ in range(3):
                    time.sleep(1)
                    job = jobs.get(job_id, {})
                    yield f"data: {json.dumps(job)}\n\n"
                break
            
            time.sleep(1)  # Update every second
    
    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*'
        }
    )

@app.route('/jobs')
def list_jobs():
    """List all jobs"""
    return jsonify(jobs)

@app.route('/jobs/<job_id>', methods=['DELETE'])
def delete_job(job_id):
    """Delete a specific job"""
    if job_id in jobs:
        del jobs[job_id]
        return jsonify({"message": f"Job {job_id} deleted"})
    else:
        return jsonify({"error": "Job not found"}), 404

if __name__ == '__main__':
    print("🚀 Starting AI Coding Agent Web Service...")
    print("📝 Open http://localhost:5000 in your browser")
    print("💡 Enter your coding instruction and watch the AI build and deploy!")
    app.run(host='0.0.0.0', port=5000, debug=True)
