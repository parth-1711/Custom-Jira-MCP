import json
import re
import httpx
from .utils import (
    ATLASSIAN_INSTANCE_URL,
    get_auth,
    get_headers
)

def register_confluence_tools(mcp):
    """Register all Confluence tools with the MCP server"""
    
    @mcp.tool()
    async def get_jira_issue_confluence_content(issue_key: str) -> str:
        """Get Confluence page content from links attached to a Jira issue"""
        async with httpx.AsyncClient() as client:
            # Get issue with remote links
            url = f"{ATLASSIAN_INSTANCE_URL}/rest/api/3/issue/{issue_key}"
            response = await client.get(
                url,
                auth=get_auth(),
                headers=get_headers(),
                params={"fields": "summary"}
            )
            response.raise_for_status()
            issue_data = response.json()
            
            # Get remote links
            links_url = f"{ATLASSIAN_INSTANCE_URL}/rest/api/3/issue/{issue_key}/remotelink"
            links_response = await client.get(
                links_url,
                auth=get_auth(),
                headers=get_headers()
            )
            links_response.raise_for_status()
            links_data = links_response.json()
            
            def extract_page_id(confluence_url: str) -> str:
                """Extract page ID from Confluence URL"""
                m = re.search(r"[?&]pageId=(\d+)", confluence_url)
                if m:
                    return m.group(1)
                m2 = re.search(r"/spaces/[^/]+/pages/(\d+)", confluence_url)
                return m2.group(1) if m2 else None
            
            # Process Confluence links
            confluence_pages = []
            for link in links_data:
                obj = link.get('object', {})
                url_str = obj.get('url', '')
                
                if '/wiki/' in url_str or 'confluence' in url_str.lower():
                    page_id = extract_page_id(url_str)
                    
                    if page_id:
                        try:
                            page_url = f"{ATLASSIAN_INSTANCE_URL}/wiki/rest/api/content/{page_id}"
                            page_response = await client.get(
                                page_url,
                                auth=get_auth(),
                                headers=get_headers(),
                                params={"expand": "body.storage,body.view,version,space"}
                            )
                            page_response.raise_for_status()
                            page_data = page_response.json()
                            
                            confluence_pages.append({
                                "link_id": link.get('id'),
                                "page_id": page_id,
                                "title": page_data.get('title', obj.get('title', 'Untitled')),
                                "url": url_str,
                                "space": page_data.get('space', {}).get('name', 'Unknown'),
                                "space_key": page_data.get('space', {}).get('key', ''),
                                "version": page_data.get('version', {}).get('number', 1),
                                "last_modified": page_data.get('version', {}).get('when', ''),
                                "last_modified_by": page_data.get('version', {}).get('by', {}).get('displayName', ''),
                                "content_html": page_data.get('body', {}).get('view', {}).get('value', ''),
                                "content_storage": page_data.get('body', {}).get('storage', {}).get('value', '')
                            })
                        except Exception as e:
                            confluence_pages.append({
                                "link_id": link.get('id'),
                                "page_id": page_id,
                                "title": obj.get('title', 'Untitled'),
                                "url": url_str,
                                "error": f"Failed to fetch content: {str(e)}"
                            })
            
            result = {
                "issue_key": issue_key,
                "issue_summary": issue_data.get('fields', {}).get('summary', ''),
                "confluence_pages_count": len(confluence_pages),
                "confluence_pages": confluence_pages
            }
            
            return json.dumps(result, indent=2)
    
    @mcp.tool()
    async def get_jira_issue_confluence_content(issue_key: str) -> str:
        """Get Confluence page content from links attached to a Jira issue
        
        Args:
            issue_key: Jira issue key (e.g., SCRUM-2)
        
        Returns:
            All Confluence pages linked to the issue with their full content
        """
        async with httpx.AsyncClient() as client:
            # Get issue with remote links
            url = f"{ATLASSIAN_INSTANCE_URL}/rest/api/3/issue/{issue_key}"
            response = await client.get(
                url,
                auth=get_auth(),
                headers=get_headers(),
                params={"fields": "summary"}
            )
            response.raise_for_status()
            issue_data = response.json()
            
            # Get remote links (which includes Confluence links)
            links_url = f"{ATLASSIAN_INSTANCE_URL}/rest/api/3/issue/{issue_key}/remotelink"
            links_response = await client.get(
                links_url,
                auth=get_auth(),
                headers=get_headers()
            )
            links_response.raise_for_status()
            links_data = links_response.json()
            
            # Helper function to extract page ID from Confluence URL
            def extract_page_id(confluence_url: str) -> str:
                """Extract page ID from Confluence URL using regex"""
                # Check for ?pageId=<ID> or &pageId=<ID>
                m = re.search(r"[?&]pageId=(\d+)", confluence_url)
                if m:
                    return m.group(1)
                # Check for /spaces/<SPACE>/pages/<ID>/...
                m2 = re.search(r"/spaces/[^/]+/pages/(\d+)", confluence_url)
                return m2.group(1) if m2 else None
            
            # Process Confluence links and fetch their content
            confluence_pages = []
            for link in links_data:
                obj = link.get('object', {})
                url_str = obj.get('url', '')
                
                # Check if it's a Confluence link
                if '/wiki/' in url_str or 'confluence' in url_str.lower():
                    # Extract page ID from URL using improved logic
                    page_id = extract_page_id(url_str)
                    
                    if page_id:
                        # Fetch the Confluence page content
                        try:
                            page_url = f"{ATLASSIAN_INSTANCE_URL}/wiki/rest/api/content/{page_id}"
                            page_response = await client.get(
                                page_url,
                                auth=get_auth(),
                                headers=get_headers(),
                                params={"expand": "body.storage,body.view,version,space"}
                            )
                            page_response.raise_for_status()
                            page_data = page_response.json()
                            
                            confluence_pages.append({
                                "link_id": link.get('id'),
                                "page_id": page_id,
                                "title": page_data.get('title', obj.get('title', 'Untitled')),
                                "url": url_str,
                                "space": page_data.get('space', {}).get('name', 'Unknown'),
                                "space_key": page_data.get('space', {}).get('key', ''),
                                "version": page_data.get('version', {}).get('number', 1),
                                "last_modified": page_data.get('version', {}).get('when', ''),
                                "last_modified_by": page_data.get('version', {}).get('by', {}).get('displayName', ''),
                                "content_html": page_data.get('body', {}).get('view', {}).get('value', ''),
                                "content_storage": page_data.get('body', {}).get('storage', {}).get('value', '')
                            })
                        except Exception as e:
                            confluence_pages.append({
                                "link_id": link.get('id'),
                                "page_id": page_id,
                                "title": obj.get('title', 'Untitled'),
                                "url": url_str,
                                "error": f"Failed to fetch content: {str(e)}"
                            })
                    else:
                        # If we can't extract page ID, just include the link info
                        confluence_pages.append({
                            "link_id": link.get('id'),
                            "title": obj.get('title', 'Untitled'),
                            "url": url_str,
                            "error": "Could not extract page ID from URL"
                        })
            
            result = {
                "issue_key": issue_key,
                "issue_summary": issue_data.get('fields', {}).get('summary', ''),
                "confluence_pages_count": len(confluence_pages),
                "confluence_pages": confluence_pages
            }
            
            return json.dumps(result, indent=2)

    @mcp.tool()
    async def get_confluence_spaces(limit: int = 25) -> str:
        """Get list of Confluence spaces
        
        Args:
            limit: Maximum number of spaces to return (default: 25)
        """
        async with httpx.AsyncClient() as client:
            url = f"{ATLASSIAN_INSTANCE_URL}/wiki/rest/api/space"
            response = await client.get(
                url,
                auth=get_auth(),
                headers=get_headers(),
                params={"limit": limit}
            )
            response.raise_for_status()
            data = response.json()
            return json.dumps(data, indent=2)

    @mcp.tool()
    async def get_confluence_pages(space_key: str, limit: int = 25) -> str:
        """Get pages in a Confluence space
        
        Args:
            space_key: Space key
            limit: Maximum number of pages to return (default: 25)
        """
        async with httpx.AsyncClient() as client:
            url = f"{ATLASSIAN_INSTANCE_URL}/wiki/rest/api/space/{space_key}/content/page"
            response = await client.get(
                url,
                auth=get_auth(),
                headers=get_headers(),
                params={"limit": limit, "expand": "version,body.storage"}
            )
            response.raise_for_status()
            data = response.json()
            return json.dumps(data, indent=2)

    @mcp.tool()
    async def get_confluence_page(page_id: str) -> str:
        """Get content of a Confluence page
        
        Args:
            page_id: Page ID
        """
        async with httpx.AsyncClient() as client:
            url = f"{ATLASSIAN_INSTANCE_URL}/wiki/rest/api/content/{page_id}"
            response = await client.get(
                url,
                auth=get_auth(),
                headers=get_headers(),
                params={"expand": "body.storage,version,space"}
            )
            response.raise_for_status()
            data = response.json()
            return json.dumps(data, indent=2)

    @mcp.tool()
    async def create_confluence_page(space_key: str, title: str, content: str, parent_id: str = None) -> str:
        """Create a new Confluence page
        
        Args:
            space_key: Space key
            title: Page title
            content: Page content
            parent_id: Parent page ID (optional)
        """
        async with httpx.AsyncClient() as client:
            url = f"{ATLASSIAN_INSTANCE_URL}/wiki/rest/api/content"
            
            page_data = {
                "type": "page",
                "title": title,
                "space": {"key": space_key},
                "body": {
                    "storage": {
                        "value": content,
                        "representation": "storage"
                    }
                }
            }
            
            if parent_id:
                page_data["ancestors"] = [{"id": parent_id}]
            
            response = await client.post(
                url,
                auth=get_auth(),
                headers=get_headers(),
                json=page_data
            )
            response.raise_for_status()
            data = response.json()
            return f"Created page: {data['id']}\n{json.dumps(data, indent=2)}"

    @mcp.tool()
    async def update_confluence_page(page_id: str, title: str, content: str, version: int) -> str:
        """Update an existing Confluence page
        
        Args:
            page_id: Page ID
            title: Page title
            content: Page content
            version: Current version number
        """
        async with httpx.AsyncClient() as client:
            url = f"{ATLASSIAN_INSTANCE_URL}/wiki/rest/api/content/{page_id}"
            response = await client.put(
                url,
                auth=get_auth(),
                headers=get_headers(),
                json={
                    "version": {"number": version + 1},
                    "title": title,
                    "type": "page",
                    "body": {
                        "storage": {
                            "value": content,
                            "representation": "storage"
                        }
                    }
                }
            )
            response.raise_for_status()
            data = response.json()
            return f"Updated page {page_id}\n{json.dumps(data, indent=2)}"
