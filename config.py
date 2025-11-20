import os

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
    
    # Railway API
    RAILWAY_API_TOKEN = os.getenv('RAILWAY_API_TOKEN')
    RAILWAY_PROJECT_ID = os.getenv('RAILWAY_PROJECT_ID')
    RAILWAY_API_URL = "https://backboard.railway.app/graphql/v2"
    
    # Deployment monitoring
    DEPLOYMENT_CHECK_INTERVAL = 30  # seconds
    MAX_DEPLOYMENT_WAIT = 600  # 10 minutes
    MAX_ITERATIONS = 10
    
    @classmethod
    def validate(cls):
        """Validate all required environment variables are set"""
        required_vars = {
            'DEEPSEEK_API_KEY': cls.DEEPSEEK_API_KEY,
            'GITHUB_TOKEN': cls.GITHUB_TOKEN,
            'GITHUB_USERNAME': cls.GITHUB_USERNAME,
            'GITHUB_REPO': cls.GITHUB_REPO,
            'RAILWAY_API_TOKEN': cls.RAILWAY_API_TOKEN,
            'RAILWAY_PROJECT_ID': cls.RAILWAY_PROJECT_ID
        }
        
        missing = [var for var, value in required_vars.items() if not value]
        if missing:
            raise ValueError(f"Missing environment variables: {', '.join(missing)}")
