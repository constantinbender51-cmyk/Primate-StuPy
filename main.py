#!/usr/bin/env python3
"""
DeepSeek Coding Agent with Railway Deployment Integration
Main execution file that orchestrates the entire pipeline
"""

import time
import sys
from config import Config
from deepseek_api import DeepSeekAPI
from github_api import GitHubAPI
from railway_api import RailwayAPI

class CodingAgent:
    def __init__(self):
        Config.validate()
        self.deepseek = DeepSeekAPI()
        self.github = GitHubAPI()
        self.railway = RailwayAPI()
    
    def run(self, user_instruction: str):
        """Main execution flow with deployment integration"""
        print(f"🎯 Starting coding agent with instruction: {user_instruction}")
        print("=" * 60)
        
        iteration = 1
        
        while iteration <= Config.MAX_ITERATIONS:
            print(f"\n🔄 Iteration {iteration}/{Config.MAX_ITERATIONS}")
            print("-" * 40)
            
            # Get current codebase
            print("📁 Fetching current codebase...")
            codebase = self.github.get_entire_codebase()
            
            if iteration == 1:
                # First iteration: generate initial code
                print("🤖 Generating initial code implementation...")
                instructions = self.deepseek.generate_initial_code(user_instruction, codebase)
            else:
                # Subsequent iterations: apply revisions from deployment review
                print("🔄 Applying revision instructions...")
                instructions = revision_instructions
            
            # Apply code changes to GitHub
            if instructions:
                print(f"📦 Applying {len(instructions)} file operations...")
                results = self.github.apply_instructions(instructions)
                for result in results:
                    print(f"  {result}")
            else:
                print("⚠️  No operations to apply")
                break
            
            # Wait for GitHub sync and trigger deployment
            print("⏳ Waiting for GitHub sync and deployment trigger...")
            time.sleep(10)  # Allow time for GitHub webhook to trigger Railway deployment
            
            # Monitor deployment
            print("🚀 Monitoring Railway deployment...")
            deployment_result = self.railway.wait_for_deployment_completion()
            
            if not deployment_result:
                print("❌ Failed to get deployment results")
                break
            
            # Review deployment with DeepSeek
            print("🔍 Requesting deployment review from DeepSeek...")
            review = self.deepseek.review_deployment(
                instruction=user_instruction,
                codebase=self.github.get_entire_codebase(),
                deployment_logs=deployment_result['deployment_logs'],
                build_logs=deployment_result['build_logs'],
                deployment_status=deployment_result['status']
            )
            
            print(f"📋 Review result: {review.get('status', 'unknown')}")
            print(f"💡 Reason: {review.get('reason', 'No reason provided')}")
            
            # Handle review decision
            if review.get('status') == 'approved':
                print("\n🎉 DEPLOYMENT APPROVED!")
                print("✅ Code successfully implemented and deployed")
                print(f"📝 Final implementation meets: {user_instruction}")
                break
            elif review.get('status') == 'revise':
                revision_instructions = review.get('instructions', [])
                if revision_instructions:
                    print(f"📝 Revision needed: {len(revision_instructions)} changes")
                    iteration += 1
                else:
                    print("⚠️  Revision requested but no instructions provided")
                    break
            else:
                print("❓ Unknown review status, stopping")
                break
        
        if iteration > Config.MAX_ITERATIONS:
            print(f"\n🛑 Maximum iterations ({Config.MAX_ITERATIONS}) reached")
            print("💡 The system may need manual intervention")
        
        print("\n🏁 Process completed")

def main():
    if len(sys.argv) > 1:
        user_instruction = " ".join(sys.argv[1:])
    else:
        # Default instruction for testing
        user_instruction = "Create a simple Python web server that returns 'Hello World'"
    
    agent = CodingAgent()
    agent.run(user_instruction)

if __name__ == "__main__":
    main()
