
import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# Tell the MCP client how to launch our server.
server_params = StdioServerParameters(
    command="uv",
    args=["run", "python", "server.py"],
)


async def main():
    # Launch the server and establish stdio communication.
    async with stdio_client(server_params) as (read_stream, write_stream):

        # Create a session for MCP communication.
        async with ClientSession(read_stream, write_stream) as session:

            # Initialize the MCP connection.
            await session.initialize()
            print("Connected to Expense MCP Server!\n")

            # Discover tools exposed by the server.
            tools_result = await session.list_tools()

            print("Available tools:")
            for tool in tools_result.tools:
                print(f"- {tool.name}: {tool.description}")

            # Call the summary tool through MCP.
            print("\nCurrent expense summary:")

            result = await session.call_tool(
                "summarize_transactions",
                arguments={
                    "start_date": "",
                    "end_date": "",
                },
            )

            for content in result.content:
                if hasattr(content, "text"):
                    print(content.text)


if __name__ == "__main__":
    asyncio.run(main())
