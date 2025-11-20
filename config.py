import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

class Config:
    """Configuration management for all services"""
    
    # DeepSeek API
    DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
    DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
    
    # GitHub API
    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
    GITHUB_USERNAME = os.getenv('GITHUB_USERNAME')
    GITHUB_REPO = os.getenv('GITHUB_REPO')
    GITHUB_API_URL = "https://api.github.com"
    
    # Railway API - for the TARGET project
    RAILWAY_API_TOKEN = os.getenv('RAILWAY_API_TOKEN')
    RAILWAY_TARGET_PROJECT_ID = os.getenv('RAILWAY_TARGET_PROJECT_ID')
    RAILWAY_API_URL = "https://backboard.railway.app/graphql/v2"
    
    # Deployment monitoring
    DEPLOYMENT_CHECK_INTERVAL = 30  # seconds
    MAX_DEPLOYMENT_WAIT = 600  # 10 minutes
    MAX_ITERATIONS = 10
    
    @classmethod
    def validate(cls):
        """Validate all required environment variables are set"""
        logger.info("🔍 Validating configuration...")
        
        required_vars = {
            'DEEPSEEK_API_KEY': cls.DEEPSEEK_API_KEY,
            'GITHUB_TOKEN': cls.GITHUB_TOKEN,
            'GITHUB_USERNAME': cls.GITHUB_USERNAME,
            'GITHUB_REPO': cls.GITHUB_REPO,
            'RAILWAY_API_TOKEN': cls.RAILWAY_API_TOKEN,
            'RAILWAY_TARGET_PROJECT_ID': cls.RAILWAY_TARGET_PROJECT_ID
        }
        
        # Log which variables are set (without revealing values)
        for var_name, value in required_vars.items():
            if value:
                masked_value = value[:4] + '...' if len(value) > 4 else '***'
                logger.debug(f"✓ {var_name}: {masked_value}")
            else:
                logger.error(f"✗ {var_name}: NOT SET")
        
        missing = [var for var, value in required_vars.items() if not value]
        
        if missing:
            error_msg = f"Missing environment variables: {', '.join(missing)}"
            logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg)
        
        logger.info("✅ Configuration validation successful")
        logger.debug(f"📊 Config: GitHub={cls.GITHUB_USERNAME}/{cls.GITHUB_REPO}, Project={cls.RAILWAY_TARGET_PROJECT_ID[:8]}...")
