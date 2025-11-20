#!/usr/bin/env python3
"""
Simple Web Service for Coding Agent
Uses Flask to serve a website and handle user instructions
"""

from flask import Flask, request, jsonify, render_template_string
import threading
from main import CodingAgent
import json
import time

app = Flask(__name__)
agent = CodingAgent()

# Store job statuses
jobs = {}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>AI Coding Agent</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .container { background: #f5f5f5; padding: 20px; border-radius: 10px; }
        textarea { width: 100%; height: 100px; margin: 10px 0; padding: 10px; }
        button { background: #007cba; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
        button:hover { background: #005a87; }
        .job { background: white; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .status-completed { color: green; }
        .status-processing { color: orange; }
        .status-error { color: red; }
        .log { background: #333; color: #fff; padding: 10px; border-radius: 5px; font-family: monospace; white-space: pre-wrap; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 AI Coding Agent</h1>
        <p>Describe what you want to build, and the AI will code and deploy it automatically!</p>
        
        <form id="instructionForm">
            <textarea name="instruction" placeholder="Example: Create a Python web server that returns 'Hello World' and has a /health endpoint" required></textarea>
            <br>
            <button type="submit">Start Coding & Deployment</button>
        </form>
        
        <div id="results">
            <h2>Active Jobs</h2>
            <div id="jobList"></div>
        </div>
    </div>

    <script>
        let eventSource = null;
        
        document.getElementById('instructionForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            const instruction = formData.get('instruction');
            
            const response = await fetch('/implement', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ instruction: instruction })
            });
            
            const result = await response.json();
            if (result.job_id) {
                startMonitoring(result.job_id);
            }
        });
        
        function startMonitoring(jobId) {
            if (eventSource) {
                eventSource.close();
            }
            
            eventSource = new EventSource(`/stream/${jobId}`);
            
            eventSource.onmessage = function(event) {
                const data = JSON.parse(event.data);
                updateJobStatus(jobId, data);
            };
            
            eventSource.onerror = function(event) {
                console.error('EventSource failed:', event);
            };
        }
        
        function updateJobStatus(jobId, data) {
            let jobList = document.getElementById('jobList');
            let existingJob = document.getElementById(`job-${jobId}`);
            
            if (!existingJob) {
                existingJob = document.createElement('div');
                existingJob.id = `job-${jobId}`;
                existingJob.className = 'job';
                jobList.appendChild(existingJob);
            }
            
            existingJob.innerHTML = `
                <h3>Job: ${jobId}</h3>
                <p><strong>Instruction:</strong> ${data.instruction || 'N/A'}</p>
                <p><strong>Status:</strong> <span class="status-${data.status}">${data.status}</span></p>
                <p><strong>Message:</strong> ${data.message || 'Processing...'}</p>
                ${data.logs ? `<div class="log">${data.logs}</div>` : ''}
                ${data.status === 'completed' ? '<p>🎉 Deployment completed successfully!</p>' : ''}
                ${data.status === 'error' ? '<p>❌ An error occurred during processing.</p>' : ''}
            `;
            
            if (data.status === 'completed' || data.status === 'error') {
                if (eventSource) {
                    eventSource.close();
                }
            }
        }
    </script>
</body>
</html>
"""

def run_agent_job(job_id, instruction):
    """Run the coding agent in a separate thread"""
    try:
        jobs[job_id] = {'status': 'processing', 'instruction': instruction}
        
        # Capture print statements
        import io
        import sys
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            agent.run(instruction)
        
        logs = f.getvalue()
        jobs[job_id] = {
            'status': 'completed', 
            'instruction': instruction,
            'message': 'Code implemented and deployed successfully',
            'logs': logs
        }
        
    except Exception as e:
        jobs[job_id] = {
            'status': 'error',
            'instruction': instruction, 
            'message': str(e),
            'logs': f"Error: {str(e)}"
        }

@app.route('/')
def index():
    """Serve the main website"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/implement', methods=['POST'])
def implement_code():
    """Handle user instruction and start coding process"""
    data = request.get_json()
    user_instruction = data.get('instruction', '').strip()
    
    if not user_instruction:
        return jsonify({"error": "No instruction provided"}), 400
    
    # Generate job ID
    job_id = f"job_{int(time.time())}"
    
    # Start processing in background thread
    thread = threading.Thread(target=run_agent_job, args=(job_id, user_instruction))
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "job_id": job_id,
        "status": "started",
        "message": "Coding agent started processing your request",
        "instruction": user_instruction
    })

@app.route('/status/<job_id>')
def get_status(job_id):
    """Get current status of a job"""
    job = jobs.get(job_id, {'status': 'unknown'})
    return jsonify(job)

@app.route('/stream/<job_id>')
def stream_status(job_id):
    """Server-sent events for real-time status updates"""
    def generate():
        while True:
            job = jobs.get(job_id, {})
            yield f"data: {json.dumps(job)}\n\n"
            
            if job.get('status') in ['completed', 'error']:
                break
            time.sleep(2)
    
    return generate(), {'Content-Type': 'text/event-stream'}

@app.route('/jobs')
def list_jobs():
    """List all jobs"""
    return jsonify(jobs)

if __name__ == '__main__':
    print("🚀 Starting AI Coding Agent Web Service...")
    print("📝 Open http://localhost:5000 in your browser")
    print("💡 Enter your coding instruction and watch the AI build and deploy!")
    app.run(host='0.0.0.0', port=5000, debug=True)
