import os
from dotenv import load_dotenv

load_dotenv()

# Atlassian API configuration
ATLASSIAN_INSTANCE_URL = os.getenv("ATLASSIAN_INSTANCE_URL")
ATLASSIAN_EMAIL = os.getenv("ATLASSIAN_EMAIL")
ATLASSIAN_API_TOKEN = os.getenv("ATLASSIAN_API_TOKEN")

def get_auth():
    """Get authentication tuple for Atlassian API"""
    return (ATLASSIAN_EMAIL, ATLASSIAN_API_TOKEN)

def get_headers():
    """Get headers for Atlassian API"""
    return {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

def extract_text_from_adf(adf_content):
    """Extract plain text from Atlassian Document Format (ADF)"""
    if not adf_content:
        return ""
    
    if isinstance(adf_content, str):
        return adf_content
    
    if not isinstance(adf_content, dict):
        return ""
    
    text_parts = []
    
    def extract_from_content(content_list):
        for item in content_list:
            if item.get('type') == 'text':
                text_parts.append(item.get('text', ''))
            elif item.get('type') in ['paragraph', 'listItem', 'tableCell', 'tableHeader']:
                if 'content' in item:
                    extract_from_content(item['content'])
                text_parts.append('\n')
            elif item.get('type') in ['bulletList', 'orderedList']:
                if 'content' in item:
                    extract_from_content(item['content'])
            elif item.get('type') == 'hardBreak':
                text_parts.append('\n')
            elif 'content' in item:
                extract_from_content(item['content'])
    
    if 'content' in adf_content:
        extract_from_content(adf_content['content'])
    
    return ''.join(text_parts).strip()