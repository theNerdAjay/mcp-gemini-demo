import asyncio
import os
from datetime import datetime
from google import genai
from google.genai import types
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv

load_dotenv()


print("api-key : ",os.getenv("GEMINI_API_KEY"))

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
 # Create server parameters for stdio connection
# server_params = StdioServerParameters(
#     command="npx",  # Executable
#     args=["-y", "@philschmid/weather-mcp"],  # Weather MCP Server
#     env=None,  # Optional environment variables
# )

async def run(server_script_path:str):

    is_python = server_script_path.endswith('.py')
    is_js = server_script_path.endswith('.js')
    if not (is_python or is_js):
        raise ValueError("Server script must be a .py or .js file")

    command = "python" if is_python else "node"
    server_params = StdioServerParameters(
        command=command,
        args=[server_script_path],
        env=None
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Prompt to get the weather for the current day in London.
            prompt = f"what is the area of reactangle who width is 100 and height is 200?"
            # Initialize the connection between client and server
            await session.initialize()

            # Get tools from MCP session and convert to Gemini Tool objects
            mcp_tools = await session.list_tools()
            tools = [
                types.Tool(
                    function_declarations=[
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": {
                                k: v
                                for k, v in tool.inputSchema.items()
                                if k not in ["additionalProperties", "$schema"]
                            },
                        }
                    ]
                )
                for tool in mcp_tools.tools
            ]

            # Send request to the model with MCP function declarations
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0,
                    tools=tools,
                ),
            )

            # Check for a function call
            if response.candidates[0].content.parts[0].function_call:
                function_call = response.candidates[0].content.parts[0].function_call
                print(function_call)
                # Call the MCP server with the predicted tool
                result = await session.call_tool(
                    function_call.name, arguments=function_call.args
                )
                print(result.content[0].text)
                # Continue as shown in step 4 of "How Function Calling Works"
                # and create a user friendly response
            else:
                print("No function call found in the response.")
                print(response.text)

# Start the asyncio event loop and run the main function
import sys

if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)


asyncio.run(run(sys.argv[1]))