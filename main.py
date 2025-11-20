#!/usr/bin/env python3
"""
DeepSeek Coding Agent with Railway Deployment Integration
Main execution file that orchestrates the entire pipeline
"""

import time
import sys
import logging
from config import Config
from deepseek_api import DeepSeekAPI
from github_api import GitHubAPI
from railway_api import RailwayAPI

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

class CodingAgent:
    def __init__(self):
        logger.info("🚀 Initializing Coding Agent...")
        
        try:
            Config.validate()
            logger.info("✅ Configuration validated")
        except ValueError as e:
            logger.error(f"❌ Configuration validation failed: {str(e)}")
            raise
        
        self.deepseek = DeepSeekAPI()
        self.github = GitHubAPI()
        self.railway = RailwayAPI()
        
        logger.info("✅ All services initialized successfully")
    
    def run(self, user_instruction: str):
        """Main execution flow with deployment integration"""
        logger.info("=" * 80)
        logger.info(f"🎯 STARTING CODING AGENT")
        logger.info(f"📝 User instruction: {user_instruction}")
        logger.info("=" * 80)
        
        print(f"🎯 Starting coding agent with instruction: {user_instruction}")
        print("=" * 60)
        
        iteration = 1
        revision_instructions = []
        
        while iteration <= Config.MAX_ITERATIONS:
            logger.info("=" * 60)
            logger.info(f"🔄 ITERATION {iteration}/{Config.MAX_ITERATIONS}")
            logger.info("=" * 60)
            
            print(f"\n🔄 Iteration {iteration}/{Config.MAX_ITERATIONS}")
            print("-" * 40)
            
            # Get current codebase
            logger.info("Step 1: Fetching current codebase")
            print("📁 Fetching current codebase...")
            
            try:
                codebase = self.github.get_entire_codebase()
                logger.info(f"✅ Codebase fetched: {len(codebase)} characters")
            except Exception as e:
                logger.error(f"❌ Failed to fetch codebase: {str(e)}")
                print(f"❌ Failed to fetch codebase: {str(e)}")
                break
            
            # Generate or apply instructions
            if iteration == 1:
                # First iteration: generate initial code
                logger.info("Step 2: Generating initial code implementation")
                print("🤖 Generating initial code implementation...")
                
                try:
                    instructions = self.deepseek.generate_initial_code(user_instruction, codebase)
                    logger.info(f"✅ Generated {len(instructions)} file operations")
                except Exception as e:
                    logger.error(f"❌ Failed to generate code: {str(e)}")
                    print(f"❌ Failed to generate code: {str(e)}")
                    break
            else:
                # Subsequent iterations: apply revisions from deployment review
                logger.info("Step 2: Applying revision instructions from previous review")
                print("🔄 Applying revision instructions...")
                instructions = revision_instructions
                logger.info(f"📝 Applying {len(instructions)} revision operations")
            
            # Apply code changes to GitHub
            if instructions:
                logger.info(f"Step 3: Applying {len(instructions)} file operations to GitHub")
                print(f"📦 Applying {len(instructions)} file operations...")
                
                try:
                    results = self.github.apply_instructions(instructions)
                    for result in results:
                        print(f"  {result}")
                        logger.debug(f"Operation result: {result}")
                    
                    success_count = sum(1 for r in results if r.startswith('✅'))
                    logger.info(f"✅ Applied operations: {success_count}/{len(instructions)} successful")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to apply instructions: {str(e)}")
                    print(f"❌ Failed to apply instructions: {str(e)}")
                    break
            else:
                logger.warning("⚠️  No operations to apply")
                print("⚠️  No operations to apply")
                break
            
            # Wait for GitHub sync and trigger deployment
            logger.info("Step 4: Waiting for GitHub sync and deployment trigger")
            print("⏳ Waiting for GitHub sync and deployment trigger...")
            sync_wait = 10
            logger.debug(f"Sleeping for {sync_wait} seconds to allow GitHub webhook to trigger Railway")
            time.sleep(sync_wait)
            
            # Monitor deployment
            logger.info("Step 5: Monitoring Railway deployment")
            print("🚀 Monitoring Railway deployment...")
            
            try:
                deployment_result = self.railway.wait_for_deployment_completion()
                
                if not deployment_result:
                    logger.error("❌ Failed to get deployment results")
                    print("❌ Failed to get deployment results")
                    break
                
                logger.info(f"✅ Deployment monitoring complete: {deployment_result.get('status')}")
                logger.debug(f"Deployment ID: {deployment_result.get('id', 'N/A')}")
                
            except Exception as e:
                logger.error(f"❌ Deployment monitoring failed: {str(e)}")
                print(f"❌ Deployment monitoring failed: {str(e)}")
                break
            
            # Review deployment with DeepSeek
            logger.info("Step 6: Requesting deployment review from DeepSeek")
            print("🔍 Requesting deployment review from DeepSeek...")
            
            try:
                # Get fresh codebase for review
                fresh_codebase = self.github.get_entire_codebase()
                
                review = self.deepseek.review_deployment(
                    instruction=user_instruction,
                    codebase=fresh_codebase,
                    deployment_logs=deployment_result['deployment_logs'],
                    build_logs=deployment_result['build_logs'],
                    deployment_status=deployment_result['status']
                )
                
                status = review.get('status', 'unknown')
                reason = review.get('reason', 'No reason provided')
                
                logger.info(f"📋 Review result: {status}")
                logger.info(f"💡 Reason: {reason}")
                
                print(f"📋 Review result: {status}")
                print(f"💡 Reason: {reason}")
                
            except Exception as e:
                logger.error(f"❌ Deployment review failed: {str(e)}")
                print(f"❌ Deployment review failed: {str(e)}")
                break
            
            # Handle review decision
            logger.info("Step 7: Processing review decision")
            
            if review.get('status') == 'approved':
                logger.info("🎉 DEPLOYMENT APPROVED - Process complete!")
                print("\n🎉 DEPLOYMENT APPROVED!")
                print("✅ Code successfully implemented and deployed")
                print(f"📝 Final implementation meets: {user_instruction}")
                logger.info(f"✅ Total iterations: {iteration}")
                logger.info("=" * 80)
                break
                
            elif review.get('status') == 'revise':
                revision_instructions = review.get('instructions', [])
                
                if revision_instructions:
                    logger.info(f"📝 Revision needed: {len(revision_instructions)} changes")
                    print(f"📝 Revision needed: {len(revision_instructions)} changes")
                    
                    # Log revision details
                    for i, inst in enumerate(revision_instructions, 1):
                        logger.debug(f"  Revision {i}: {inst.get('operation')} - {inst.get('file')}")
                    
                    iteration += 1
                    logger.info(f"🔄 Moving to iteration {iteration}")
                else:
                    logger.warning("⚠️  Revision requested but no instructions provided")
                    print("⚠️  Revision requested but no instructions provided")
                    break
            else:
                logger.error(f"❓ Unknown review status: {status}")
                print("❓ Unknown review status, stopping")
                break
        
        if iteration > Config.MAX_ITERATIONS:
            logger.warning(f"🛑 Maximum iterations ({Config.MAX_ITERATIONS}) reached")
            print(f"\n🛑 Maximum iterations ({Config.MAX_ITERATIONS}) reached")
            print("💡 The system may need manual intervention")
        
        logger.info("=" * 80)
        logger.info("🏁 PROCESS COMPLETED")
        logger.info("=" * 80)
        print("\n🏁 Process completed")

def main():
    logger.info("=" * 80)
    logger.info("🚀 DEEPSEEK CODING AGENT - STARTUP")
    logger.info("=" * 80)
    
    if len(sys.argv) > 1:
        user_instruction = " ".join(sys.argv[1:])
        logger.info(f"📝 Instruction from command line: {user_instruction}")
    else:
        # Default instruction for testing
        user_instruction = "Create a simple Python web server that returns 'Hello World'"
        logger.info(f"📝 Using default instruction: {user_instruction}")
    
    try:
        agent = CodingAgent()
        agent.run(user_instruction)
    except Exception as e:
        logger.error(f"❌ Fatal error: {str(e)}", exc_info=True)
        print(f"\n❌ Fatal error: {str(e)}")
        sys.exit(1)
    
    logger.info("👋 Agent shutdown complete")

if __name__ == "__main__":
    main()
