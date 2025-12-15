from fastmcp import FastMCP
from tools import register_jira_tools, register_confluence_tools



mcp = FastMCP("atlassian-custom-tools")

register_jira_tools(mcp)
register_confluence_tools(mcp)

if __name__ == "__main__":
    # mcp.run()
    mcp.run(transport="sse", host="127.0.0.1", port=8080)