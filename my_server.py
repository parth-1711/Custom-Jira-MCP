import os
from fastmcp import FastMCP
from tools import register_jira_tools, register_confluence_tools
from dotenv import load_dotenv

load_dotenv()



mcp = FastMCP("atlassian-custom-tools")

register_jira_tools(mcp)
register_confluence_tools(mcp)

if __name__ == "__main__":
    # mcp.run()
    environment=os.getenv("environment")
    host=""
    if environment == "dev":
        host="127.0.0.1"
    else: host = "0.0.0.0"
    mcp.run(transport="sse", host=host, port=8080)

