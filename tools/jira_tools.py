import json
import httpx
from .utils import (
    ATLASSIAN_INSTANCE_URL,
    get_auth,
    get_headers,
    extract_text_from_adf
)

def register_jira_tools(mcp):
    """Register all Jira tools with the MCP server"""
    
    @mcp.tool()
    async def get_jira_issue(issue_key: str) -> str:
        """Get details of a Jira issue by key or ID with comments, history and subtasks"""
        async with httpx.AsyncClient() as client:
            # Get the main issue with changelog
            url = f"{ATLASSIAN_INSTANCE_URL}/rest/api/3/issue/{issue_key}"
            response = await client.get(
                url,
                auth=get_auth(),
                headers=get_headers(),
                params={"expand": "changelog,renderedFields", "fields": "summary,description,status,comment,subtasks,issuetype"}
            )
            response.raise_for_status()
            issue_data = response.json()
            
            # Extract description
            description = extract_text_from_adf(issue_data.get('fields', {}).get('description', ''))
            issuetype = issue_data.get('fields', {}).get('issuetype', {}).get('name', '')
            
            # Extract comments
            comments = []
            comment_data = issue_data.get('fields', {}).get('comment', {}).get('comments', [])
            for c in comment_data:
                author_name = c.get('author', {}).get('displayName', 'Unknown')
                body = extract_text_from_adf(c.get('body', ''))
                comments.append({
                    "author": author_name,
                    "body": body
                })
            
            # Extract history (changelog)
            history_entries = []
            changelog = issue_data.get('changelog', {})
            if changelog:
                for h in changelog.get('histories', []):
                    author_name = h.get('author', {}).get('displayName', 'Unknown')
                    history_entries.append({
                        "author": author_name,
                        "created": h.get('created', ''),
                        "items": [{
                            "field": i.get('field', ''),
                            "from": i.get('fromString', ''),
                            "to": i.get('toString', '')
                        } for i in h.get('items', [])]
                    })
            
            # Extract subtasks with their comments and history
            subtasks_payload = []
            subtasks = issue_data.get('fields', {}).get('subtasks', [])
            
            for sub in subtasks:
                sub_key = sub.get('key')
                if not sub_key:
                    continue
                
                # Fetch full subtask details with changelog
                sub_url = f"{ATLASSIAN_INSTANCE_URL}/rest/api/3/issue/{sub_key}"
                sub_response = await client.get(
                    sub_url,
                    auth=get_auth(),
                    headers=get_headers(),
                    params={"expand": "changelog", "fields": "summary,description,status,comment"}
                )
                sub_response.raise_for_status()
                sub_data = sub_response.json()
                
                # Extract subtask description
                sub_description = extract_text_from_adf(sub_data.get('fields', {}).get('description', ''))
                
                # Extract subtask comments
                sub_comments = []
                sub_comment_data = sub_data.get('fields', {}).get('comment', {}).get('comments', [])
                for c in sub_comment_data:
                    author_name = c.get('author', {}).get('displayName', 'Unknown')
                    body = extract_text_from_adf(c.get('body', ''))
                    sub_comments.append({
                        "author": author_name,
                        "body": body
                    })
                
                # Extract subtask history
                sub_history = []
                sub_changelog = sub_data.get('changelog', {})
                if sub_changelog:
                    for h in sub_changelog.get('histories', []):
                        author_name = h.get('author', {}).get('displayName', 'Unknown')
                        sub_history.append({
                            "author": author_name,
                            "created": h.get('created', ''),
                            "items": [{
                                "field": i.get('field', ''),
                                "from": i.get('fromString', ''),
                                "to": i.get('toString', '')
                            } for i in h.get('items', [])]
                        })
                
                subtasks_payload.append({
                    "key": sub_data.get('key', ''),
                    "summary": sub_data.get('fields', {}).get('summary', ''),
                    "description": sub_description,
                    "status": sub_data.get('fields', {}).get('status', {}).get('name', ''),
                    "comments": sub_comments,
                    "history": sub_history
                })
            
            # Build the final payload
            result = {
                "key": issue_data.get('key', ''),
                "issuetype": issuetype,
                "summary": issue_data.get('fields', {}).get('summary', ''),
                "description": description,
                "status": issue_data.get('fields', {}).get('status', {}).get('name', ''),
                "comments": comments,
                "history": history_entries,
                "subtasks": subtasks_payload
            }
            
            return json.dumps(result, indent=2)
    
    # Add all other Jira tools here following the same pattern...
    # For brevity, I'll show a few more examples:
    
    @mcp.tool()
    async def get_jira_issue_type(issue_key: str) -> str:
        """Get the issue type of a Jira issue"""
        async with httpx.AsyncClient() as client:
            url = f"{ATLASSIAN_INSTANCE_URL}/rest/api/3/issue/{issue_key}"
            response = await client.get(
                url,
                auth=get_auth(),
                headers=get_headers(),
                params={"fields": "issuetype,key,summary"}
            )
            response.raise_for_status()
            issue_data = response.json()
            
            result = {
                "key": issue_data.get('key', ''),
                "issue_type": issue_data.get('fields', {}).get('issuetype', {}).get('name', ''),
                "issue_type_id": issue_data.get('fields', {}).get('issuetype', {}).get('id', ''),
                "is_subtask": issue_data.get('fields', {}).get('issuetype', {}).get('subtask', False)
            }
            
            return json.dumps(result, indent=2)
    
    @mcp.tool()
    async def create_jira_issue(project_key: str, summary: str, description: str = "", issue_type: str = "Task") -> str:
        """Create a new Jira issue
        
        Args:
            project_key: Project key
            summary: Issue summary
            description: Issue description (optional)
            issue_type: Issue type (default: Task)
        """
        async with httpx.AsyncClient() as client:
            url = f"{ATLASSIAN_INSTANCE_URL}/rest/api/3/issue"
            response = await client.post(
                url,
                auth=get_auth(),
                headers=get_headers(),
                json={
                    "fields": {
                        "project": {"key": project_key},
                        "summary": summary,
                        "description": {
                            "type": "doc",
                            "version": 1,
                            "content": [{
                                "type": "paragraph",
                                "content": [{"type": "text", "text": description}]
                            }]
                        },
                        "issuetype": {"name": issue_type}
                    }
                }
            )
            response.raise_for_status()
            data = response.json()
            return f"Created issue: {data['key']}\n{json.dumps(data, indent=2)}"

    @mcp.tool()
    async def update_jira_issue(issue_key: str, fields: dict) -> str:
        """Update a Jira issue
        
        Args:
            issue_key: Issue key
            fields: Fields to update
        """
        async with httpx.AsyncClient() as client:
            url = f"{ATLASSIAN_INSTANCE_URL}/rest/api/3/issue/{issue_key}"
            response = await client.put(
                url,
                auth=get_auth(),
                headers=get_headers(),
                json={"fields": fields}
            )
            response.raise_for_status()
            return f"Updated issue {issue_key}"

    @mcp.tool()
    async def add_jira_comment(issue_key: str, comment: str) -> str:
        """Add a comment to a Jira issue
        
        Args:
            issue_key: Issue key
            comment: Comment text
        """
        async with httpx.AsyncClient() as client:
            url = f"{ATLASSIAN_INSTANCE_URL}/rest/api/3/issue/{issue_key}/comment"
            response = await client.post(
                url,
                auth=get_auth(),
                headers=get_headers(),
                json={
                    "body": {
                        "type": "doc",
                        "version": 1,
                        "content": [{
                            "type": "paragraph",
                            "content": [{"type": "text", "text": comment}]
                        }]
                    }
                }
            )
            response.raise_for_status()
            data = response.json()
            return f"Added comment to {issue_key}\n{json.dumps(data, indent=2)}"

    @mcp.tool()
    async def get_jira_transitions(issue_key: str) -> str:
        """Get available transitions for a Jira issue
        
        Args:
            issue_key: Issue key
        """
        async with httpx.AsyncClient() as client:
            url = f"{ATLASSIAN_INSTANCE_URL}/rest/api/3/issue/{issue_key}/transitions"
            response = await client.get(
                url,
                auth=get_auth(),
                headers=get_headers()
            )
            response.raise_for_status()
            data = response.json()
            return json.dumps(data, indent=2)

    @mcp.tool()
    async def transition_jira_issue(issue_key: str, transition_id: str) -> str:
        """Transition a Jira issue to a new status
        
        Args:
            issue_key: Issue key
            transition_id: Transition ID
        """
        async with httpx.AsyncClient() as client:
            url = f"{ATLASSIAN_INSTANCE_URL}/rest/api/3/issue/{issue_key}/transitions"
            response = await client.post(
                url,
                auth=get_auth(),
                headers=get_headers(),
                json={"transition": {"id": transition_id}}
            )
            response.raise_for_status()
            return f"Transitioned issue {issue_key}"

    @mcp.tool()
    async def get_board_sprints(board_id: str, state: str = "active") -> str:
        """Get sprints for a board filtered by state
        
        Args:
            board_id: Board ID
            state: Sprint state (active, closed, future) (default: active)
        """
        async with httpx.AsyncClient() as client:
            url = f"{ATLASSIAN_INSTANCE_URL}/rest/agile/1.0/board/{board_id}/sprint"
            response = await client.get(
                url,
                auth=get_auth(),
                headers=get_headers(),
                params={"state": state}
            )
            response.raise_for_status()
            data = response.json()
            return json.dumps(data, indent=2)

    @mcp.tool()
    async def find_sprint_ID_by_name(board_id: str, sprint_name: str) -> str:
        """Find a sprint ID by its name
        
        Args:
            board_id: Board ID (use get_all_boards to find this)
            sprint_name: Sprint name to search for (e.g., "SCRUM Sprint 0")
        
        Returns:
            Sprint details including the numeric ID needed for get_sprint_issues
        """
        async with httpx.AsyncClient() as client:
            # Search in all sprint states
            for state in ["active", "closed", "future"]:
                url = f"{ATLASSIAN_INSTANCE_URL}/rest/agile/1.0/board/{board_id}/sprint"
                response = await client.get(
                    url,
                    auth=get_auth(),
                    headers=get_headers(),
                    params={"state": state}
                )
                response.raise_for_status()
                data = response.json()
                
                # Search for sprint by name
                for sprint in data.get('values', []):
                    if sprint.get('name', '').lower() == sprint_name.lower():
                        return json.dumps({
                            "found": True,
                            "sprint_id": sprint.get('id'),
                            "sprint_name": sprint.get('name'),
                            "state": sprint.get('state'),
                            "start_date": sprint.get('startDate'),
                            "end_date": sprint.get('endDate'),
                            "complete_date": sprint.get('completeDate'),
                            "goal": sprint.get('goal')
                        }, indent=2)
            
            return json.dumps({"found": False, "message": f"Sprint '{sprint_name}' not found"}, indent=2)

    @mcp.tool()
    async def get_sprint_issues_by_name(sprint_name: str, max_results: int = 100) -> str:
        """Get all issues in a sprint using only the sprint name (searches all boards)
        
        Args:
            sprint_name: Sprint name (e.g., "SCRUM Sprint 0")
            max_results: Maximum number of issues to return (default: 100)
        
        Returns:
            All issues in the sprint with sprint and board information
        """
        async with httpx.AsyncClient() as client:
            # First, get all boards
            boards_url = f"{ATLASSIAN_INSTANCE_URL}/rest/agile/1.0/board"
            boards_response = await client.get(
                boards_url,
                auth=get_auth(),
                headers=get_headers(),
                params={"maxResults": 100}
            )
            boards_response.raise_for_status()
            boards_data = boards_response.json()
            
            # Search for the sprint in each board
            for board in boards_data.get('values', []):
                board_id = board.get('id')
                
                for state in ["active", "closed", "future"]:
                    sprints_url = f"{ATLASSIAN_INSTANCE_URL}/rest/agile/1.0/board/{board_id}/sprint"
                    sprints_response = await client.get(
                        sprints_url,
                        auth=get_auth(),
                        headers=get_headers(),
                        params={"state": state}
                    )
                    sprints_response.raise_for_status()
                    sprints_data = sprints_response.json()
                    
                    # Search for sprint by name
                    for sprint in sprints_data.get('values', []):
                        if sprint.get('name', '').lower() == sprint_name.lower():
                            sprint_id = sprint.get('id')
                            
                            # Found the sprint! Now get the issues
                            issues_url = f"{ATLASSIAN_INSTANCE_URL}/rest/agile/1.0/sprint/{sprint_id}/issue"
                            issues_response = await client.get(
                                issues_url,
                                auth=get_auth(),
                                headers=get_headers(),
                                params={
                                    "maxResults": max_results,
                                    "startAt": 0,
                                    "fields": "summary,status,assignee,priority,issuetype,created,updated,timetracking,progress,customfield_10016"
                                }
                            )
                            issues_response.raise_for_status()
                            issues_data = issues_response.json()
                            
                            # Return with complete information
                            result = {
                                "board_info": {
                                    "board_id": board_id,
                                    "board_name": board.get('name'),
                                    "board_type": board.get('type')
                                },
                                "sprint_info": {
                                    "sprint_id": sprint_id,
                                    "sprint_name": sprint.get('name'),
                                    "state": sprint.get('state'),
                                    "start_date": sprint.get('startDate'),
                                    "end_date": sprint.get('endDate'),
                                    "goal": sprint.get('goal')
                                },
                                "total_issues": issues_data.get('total', 0),
                                "returned_issues": len(issues_data.get('issues', [])),
                                "issues": issues_data.get('issues', [])
                            }
                            
                            return json.dumps(result, indent=2)
            
            return json.dumps({"error": f"Sprint '{sprint_name}' not found in any board"}, indent=2)

    @mcp.tool()
    async def get_epic_issues(epic_key: str, max_results: int = 100, start_at: int = 0) -> str:
        """Get all issues in an epic
        
        Args:
            epic_key: Epic issue key (e.g., SCRUM-1)
            max_results: Maximum number of issues to return (default: 100)
            start_at: Starting index for pagination (default: 0)
        
        Returns:
            All issues belonging to the epic with epic information
        """
        async with httpx.AsyncClient() as client:
            # First, get the epic details
            epic_url = f"{ATLASSIAN_INSTANCE_URL}/rest/api/3/issue/{epic_key}"
            epic_response = await client.get(
                epic_url,
                auth=get_auth(),
                headers=get_headers(),
                params={"fields": "summary,status,project,created,updated,assignee"}
            )
            epic_response.raise_for_status()
            epic_data = epic_response.json()
            
            # Use the new JQL search endpoint
            jql = f'parent = {epic_key} OR "Epic Link" = {epic_key}'
            
            search_url = f"{ATLASSIAN_INSTANCE_URL}/rest/api/3/search/jql"
            try:
                search_response = await client.get(
                    search_url,
                    auth=get_auth(),
                    headers={"Accept": "application/json"},
                    params={
                        "jql": jql,
                        "maxResults": max_results,
                        "startAt": start_at,
                        "fields": "summary,status,assignee,priority,issuetype,created,updated,parent,timetracking,progress"
                    }
                )
                search_response.raise_for_status()
                issues_data = search_response.json()
            except httpx.HTTPStatusError as e:
                # Fallback: Try with epic's internal ID
                epic_id = epic_data.get('id')
                jql_with_id = f'parent = {epic_id}'
                search_response = await client.get(
                    search_url,
                    auth=get_auth(),
                    headers={"Accept": "application/json"},
                    params={
                        "jql": jql_with_id,
                        "maxResults": max_results,
                        "startAt": start_at,
                        "fields": "summary,status,assignee,priority,issuetype,created,updated,parent,timetracking,progress"
                    }
                )
                search_response.raise_for_status()
                issues_data = search_response.json()
            
            result = {
                "epic_info": {
                    "epic_key": epic_key,
                    "epic_id": epic_data.get('id'),
                    "epic_summary": epic_data.get('fields', {}).get('summary', ''),
                    "epic_assignee": epic_data.get('fields', {}).get('assignee', {}).get('displayName', ''),
                    "epic_status": epic_data.get('fields', {}).get('status', {}).get('name', ''),
                    "project": epic_data.get('fields', {}).get('project', {}).get('name', ''),
                    "created": epic_data.get('fields', {}).get('created', ''),
                    "updated": epic_data.get('fields', {}).get('updated', '')
                },
                "total_issues": issues_data.get('total', 0),
                "returned_issues": len(issues_data.get('issues', [])),
                "start_at": start_at,
                "max_results": max_results,
                "issues": issues_data.get('issues', [])
            }
            
            return json.dumps(result, indent=2)

    @mcp.tool()
    async def get_epic_issues_by_board(board_id: str, epic_key: str, max_results: int = 100) -> str:
        """Get all issues in an epic using Agile API (board-specific)
        
        Args:
            board_id: Board ID
            epic_key: Epic issue key (e.g., SCRUM-1)
            max_results: Maximum number of issues to return (default: 100)
        
        Returns:
            All issues in the epic from the specified board
        """
        async with httpx.AsyncClient() as client:
            # Get epic details first
            epic_url = f"{ATLASSIAN_INSTANCE_URL}/rest/api/3/issue/{epic_key}"
            epic_response = await client.get(
                epic_url,
                auth=get_auth(),
                headers=get_headers(),
                params={"fields": "summary,status"}
            )
            epic_response.raise_for_status()
            epic_data = epic_response.json()
            
            # Get issues for the epic from the board
            issues_url = f"{ATLASSIAN_INSTANCE_URL}/rest/agile/1.0/board/{board_id}/epic/{epic_key}/issue"
            issues_response = await client.get(
                issues_url,
                auth=get_auth(),
                headers=get_headers(),
                params={
                    "maxResults": max_results,
                    "startAt": 0,
                    "fields": "summary,status,assignee,priority,issuetype,created,updated,timetracking,progress"
                }
            )
            issues_response.raise_for_status()
            issues_data = issues_response.json()
            
            result = {
                "board_id": board_id,
                "epic_info": {
                    "epic_key": epic_key,
                    "epic_summary": epic_data.get('fields', {}).get('summary', ''),
                    "epic_status": epic_data.get('fields', {}).get('status', {}).get('name', '')
                },
                "total_issues": issues_data.get('total', 0),
                "returned_issues": len(issues_data.get('issues', [])),
                "issues": issues_data.get('issues', [])
            }
            
            return json.dumps(result, indent=2)

    @mcp.tool()
    async def get_issues_by_assignee(assignee_email: str, max_results: int = 50, start_at: int = 0) -> str:
        """Get all Jira issues assigned to a specific user with full details
        
        Args:
            assignee_email: Email address of the assignee
            max_results: Maximum number of issues to return (default: 50)
            start_at: Starting index for pagination (default: 0)
        
        Returns:
            All issues assigned to the user with description, comments, history, and subtasks
        """
        async with httpx.AsyncClient() as client:
            # Build JQL query to find issues by assignee
            jql = f'assignee = "{assignee_email}" ORDER BY updated DESC'
            
            url = f"{ATLASSIAN_INSTANCE_URL}/rest/api/3/search/jql"
            response = await client.get(
                url,
                auth=get_auth(),
                headers={"Accept": "application/json"},
                params={
                    "jql": jql,
                    "maxResults": max_results,
                    "startAt": start_at,
                    "fields": "summary,description,status,comment,subtasks,created,updated,priority,issuetype,project"
                }
            )
            response.raise_for_status()
            data = response.json()
            
            if not data:
                return json.dumps({"error": "No data returned from API"}, indent=2)
            
            # Process each issue to get full details
            formatted_issues = []
            for issue_summary in data.get('issues', []):
                try:
                    issue_key = issue_summary.get('key')
                    if not issue_key:
                        continue
                    
                    # Fetch full issue details with changelog
                    issue_url = f"{ATLASSIAN_INSTANCE_URL}/rest/api/3/issue/{issue_key}"
                    issue_response = await client.get(
                        issue_url,
                        auth=get_auth(),
                        headers=get_headers(),
                        params={"expand": "changelog", "fields": "summary,description,status,comment,subtasks,created,updated,priority,issuetype,project"}
                    )
                    issue_response.raise_for_status()
                    issue_data = issue_response.json()
                    
                    if not issue_data:
                        continue
                    
                    fields = issue_data.get('fields', {})
                    if not fields:
                        continue
                    
                    # Extract description
                    description = extract_text_from_adf(fields.get('description', ''))
                    
                    # Extract comments
                    comments = []
                    comment_obj = fields.get('comment', {})
                    if comment_obj:
                        comment_data = comment_obj.get('comments', [])
                        for c in comment_data:
                            if not c:
                                continue
                            author = c.get('author', {})
                            author_name = author.get('displayName', 'Unknown') if author else 'Unknown'
                            body = extract_text_from_adf(c.get('body', ''))
                            comments.append({
                                "author": author_name,
                                "body": body
                            })
                    
                    # Extract history (changelog)
                    history_entries = []
                    changelog = issue_data.get('changelog', {})
                    if changelog:
                        for h in changelog.get('histories', []):
                            if not h:
                                continue
                            author = h.get('author', {})
                            author_name = author.get('displayName', 'Unknown') if author else 'Unknown'
                            history_entries.append({
                                "author": author_name,
                                "created": h.get('created', ''),
                                "items": [{
                                    "field": i.get('field', ''),
                                    "from": i.get('fromString', ''),
                                    "to": i.get('toString', '')
                                } for i in h.get('items', []) if i]
                            })
                    
                    # Extract subtasks with their comments and history
                    subtasks_payload = []
                    subtasks = fields.get('subtasks', [])
                    
                    for sub in subtasks:
                        if not sub:
                            continue
                        
                        sub_key = sub.get('key')
                        if not sub_key:
                            continue
                        
                        try:
                            # Fetch full subtask details with changelog
                            sub_url = f"{ATLASSIAN_INSTANCE_URL}/rest/api/3/issue/{sub_key}"
                            sub_response = await client.get(
                                sub_url,
                                auth=get_auth(),
                                headers=get_headers(),
                                params={"expand": "changelog", "fields": "summary,description,status,comment"}
                            )
                            sub_response.raise_for_status()
                            sub_data = sub_response.json()
                            
                            if not sub_data:
                                continue
                            
                            sub_fields = sub_data.get('fields', {})
                            if not sub_fields:
                                continue
                            
                            # Extract subtask description
                            sub_description = extract_text_from_adf(sub_fields.get('description', ''))
                            
                            # Extract subtask comments
                            sub_comments = []
                            sub_comment_obj = sub_fields.get('comment', {})
                            if sub_comment_obj:
                                sub_comment_data = sub_comment_obj.get('comments', [])
                                for c in sub_comment_data:
                                    if not c:
                                        continue
                                    author = c.get('author', {})
                                    author_name = author.get('displayName', 'Unknown') if author else 'Unknown'
                                    body = extract_text_from_adf(c.get('body', ''))
                                    sub_comments.append({
                                        "author": author_name,
                                        "body": body
                                    })
                            
                            # Extract subtask history
                            sub_history = []
                            sub_changelog = sub_data.get('changelog', {})
                            if sub_changelog:
                                for h in sub_changelog.get('histories', []):
                                    if not h:
                                        continue
                                    author = h.get('author', {})
                                    author_name = author.get('displayName', 'Unknown') if author else 'Unknown'
                                    sub_history.append({
                                        "author": author_name,
                                        "created": h.get('created', ''),
                                        "items": [{
                                            "field": i.get('field', ''),
                                            "from": i.get('fromString', ''),
                                            "to": i.get('toString', '')
                                        } for i in h.get('items', []) if i]
                                    })
                            
                            status = sub_fields.get('status', {})
                            subtasks_payload.append({
                                "key": sub_data.get('key', ''),
                                "summary": sub_fields.get('summary', ''),
                                "description": sub_description,
                                "status": status.get('name', '') if status else '',
                                "comments": sub_comments,
                                "history": sub_history
                            })
                        except Exception as e:
                            # Skip this subtask if there's an error
                            continue
                    
                    # Build formatted issue
                    priority = fields.get('priority', {})
                    issuetype = fields.get('issuetype', {})
                    project = fields.get('project', {})
                    status = fields.get('status', {})
                    
                    formatted_issue = {
                        "key": issue_data.get('key', ''),
                        "summary": fields.get('summary', ''),
                        "description": description,
                        "status": status.get('name', '') if status else '',
                        "priority": priority.get('name', '') if priority else '',
                        "issue_type": issuetype.get('name', '') if issuetype else '',
                        "project": project.get('name', '') if project else '',
                        "created": fields.get('created', ''),
                        "updated": fields.get('updated', ''),
                        "comments": comments,
                        "history": history_entries,
                        "subtasks": subtasks_payload
                    }
                    
                    formatted_issues.append(formatted_issue)
                except Exception as e:
                    # Skip this issue if there's an error
                    continue
            
            result = {
                "assignee": assignee_email,
                "total_issues": data.get('total', 0),
                "returned_issues": len(formatted_issues),
                "start_at": start_at,
                "max_results": max_results,
                "issues": formatted_issues
            }
            
            return json.dumps(result, indent=2)
        
    @mcp.tool()
    async def get_all_boards(start_at: int = 0, max_results: int = 50) -> str:
        """Get all Jira boards
        
        Args:
            start_at: Starting index for pagination (default: 0)
            max_results: Maximum number of boards to return (default: 50)
        """
        async with httpx.AsyncClient() as client:
            url = f"{ATLASSIAN_INSTANCE_URL}/rest/agile/1.0/board"
            response = await client.get(
                url,
                auth=get_auth(),
                headers=get_headers(),
                params={
                    "startAt": start_at,
                    "maxResults": max_results
                }
            )
            response.raise_for_status()
            data = response.json()
            return json.dumps(data, indent=2)
    
    @mcp.tool()
    async def get_active_sprints(board_id: str) -> str:
        """Get active sprints for a board
        
        Args:
            board_id: Board ID
        """
        async with httpx.AsyncClient() as client:
            url = f"{ATLASSIAN_INSTANCE_URL}/rest/agile/1.0/board/{board_id}/sprint"
            response = await client.get(
                url,
                auth=get_auth(),
                headers=get_headers(),
                params={"state": "active"}
            )
            response.raise_for_status()
            data = response.json()
            return json.dumps(data, indent=2)

    @mcp.tool()
    async def get_board_sprints(board_id: str, state: str = "active") -> str:
        """Get sprints for a board filtered by state
        
        Args:
            board_id: Board ID
            state: Sprint state (active, closed, future) (default: active)
        """
        async with httpx.AsyncClient() as client:
            url = f"{ATLASSIAN_INSTANCE_URL}/rest/agile/1.0/board/{board_id}/sprint"
            response = await client.get(
                url,
                auth=get_auth(),
                headers=get_headers(),
                params={"state": state}
            )
            response.raise_for_status()
            data = response.json()
            return json.dumps(data, indent=2)


    @mcp.tool()
    async def get_all_issues_in_project(project_key: str, max_results: int = 100, start_at: int = 0) -> str:
        """Get all issues in a project
        
        Args:
            project_key: Project key (e.g., "SCRUM")
            max_results: Maximum number of issues to return (default: 100)
            start_at: Starting index for pagination (default: 0)
        
        Returns:
            List of all issues in the project with their details
        """
        async with httpx.AsyncClient() as client:
            # Build JQL query
            jql = f'project = {project_key} ORDER BY created DESC'
            
            url = f"{ATLASSIAN_INSTANCE_URL}/rest/api/3/search/jql"
            response = await client.get(
                url,
                auth=get_auth(),
                headers={"Accept": "application/json"},
                params={
                    "jql": jql,
                    "maxResults": max_results,
                    "startAt": start_at,
                    "fields": "summary,status,assignee,priority,issuetype,created,updated,description,parent,labels"
                }
            )
            response.raise_for_status()
            data = response.json()
            
            # Format the issues
            issues = []
            for issue in data.get('issues', []):
                fields = issue.get('fields', {})
                assignee = fields.get('assignee', {})
                priority = fields.get('priority', {})
                issuetype = fields.get('issuetype', {})
                status_obj = fields.get('status', {})
                parent = fields.get('parent', {})
                
                issues.append({
                    "key": issue.get('key', ''),
                    "summary": fields.get('summary', ''),
                    "issue_type": issuetype.get('name', '') if issuetype else '',
                    "status": status_obj.get('name', '') if status_obj else '',
                    "assignee": assignee.get('displayName', '') if assignee else 'Unassigned',
                    "priority": priority.get('name', '') if priority else '',
                    "parent_key": parent.get('key', '') if parent else None,
                    "parent_summary": parent.get('fields', {}).get('summary', '') if parent else None,
                    "labels": fields.get('labels', []),
                    "created": fields.get('created', ''),
                    "updated": fields.get('updated', '')
                })
            
            result = {
                "project_key": project_key,
                "total_issues": data.get('total', 0),
                "returned_issues": len(issues),
                "start_at": start_at,
                "max_results": max_results,
                "issues": issues
            }
            
            return json.dumps(result, indent=2)

    @mcp.tool()
    async def get_all_epics(project_key: str = None, max_results: int = 100, start_at: int = 0) -> str:
        """Get all epics, optionally filtered by project
        
        Args:
            project_key: Project key to filter epics (optional, e.g., "SCRUM")
            max_results: Maximum number of epics to return (default: 100)
            start_at: Starting index for pagination (default: 0)
        
        Returns:
            List of all epics with their details
        """
        async with httpx.AsyncClient() as client:
            # Build JQL query to find all epics
            if project_key:
                jql = f'project = {project_key} AND type = Epic ORDER BY created DESC'
            else:
                jql = 'type = Epic ORDER BY created DESC'
            
            url = f"{ATLASSIAN_INSTANCE_URL}/rest/api/3/search/jql"
            response = await client.get(
                url,
                auth=get_auth(),
                headers={"Accept": "application/json"},
                params={
                    "jql": jql,
                    "maxResults": max_results,
                    "startAt": start_at,
                    "fields": "summary,status,project,created,updated,description,assignee,priority"
                }
            )
            response.raise_for_status()
            data = response.json()
            
            # Format the epics
            epics = []
            for epic in data.get('issues', []):
                fields = epic.get('fields', {})
                assignee = fields.get('assignee', {})
                priority = fields.get('priority', {})
                project = fields.get('project', {})
                status = fields.get('status', {})
                
                epics.append({
                    "key": epic.get('key', ''),
                    "summary": fields.get('summary', ''),
                    "status": status.get('name', '') if status else '',
                    "project": project.get('name', '') if project else '',
                    "project_key": project.get('key', '') if project else '',
                    "assignee": assignee.get('displayName', '') if assignee else 'Unassigned',
                    "priority": priority.get('name', '') if priority else '',
                    "created": fields.get('created', ''),
                    "updated": fields.get('updated', '')
                })
            
            result = {
                "total_epics": data.get('total', 0),
                "returned_epics": len(epics),
                "start_at": start_at,
                "max_results": max_results,
                "project_filter": project_key if project_key else "All projects",
                "epics": epics
            }
            
            return json.dumps(result, indent=2)
        
