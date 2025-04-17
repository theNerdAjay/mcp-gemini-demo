import os
import json
import asyncio
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

class MCPClient:
    def __init__(self):
        
        self.session : Optional[ClientSession] = None        
        self.exit_stack = AsyncExitStack()
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.types = types

    async def connect_to_server(self,server_path:str):
        """Connect to an MCP server
        Args:
            server_script_path: Path to the server script (.py or .js)
        """

        is_python = server_path.endswith(".py")   
        is_js = server_path.endswith(".js")   
        
        if not (is_python or is_js):
            raise ValueError("Server file must be .py or .js")
        
        command = "python" if is_python else "node"

        server_params = StdioServerParameters(
            command=command,
            args=[server_path],
            env=None
        )

        studio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.studio,self.write = studio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.studio,self.write))

        await self.session.initialize()

        response = await self.session.list_tools()

        tools = response.tools

        print(f"Connected to MCP server with tools : \n", [tool.name for tool in tools])

    async def process_query(self,query:str)-> str:
        """Process a query using Claude and available tools"""


        message = [
           self.types.Content(
               role="user",
               parts=[self.types.Part(text=query)]
           )
        ]
        
        mcp_response = await self.session.list_tools()

        available_tools = [
                self.types.Tool(
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
                for tool in mcp_response.tools
        ]

        response = self.client.models.generate_content(
            model="gemini-2.0-flash",
            contents=message,
            config=self.types.GenerateContentConfig(
                temperature=0,
                tools=available_tools
            )
        )

        final_text = []

        assistant_message_cotent = []

        for content in response.candidates[0].content.parts:
            if content.function_call:
                fc = content.function_call 

                
                print(f"Calling : {fc.name} with {fc.args}")

                result = await self.session.call_tool(fc.name,arguments=fc.args)
                # print("result : ",result.content[0].text)
                final_text.append(f"[Calling tool {fc.name} with args {fc.args}]")
                assistant_message_cotent.append({"function_response": {"name": fc.name, "content": result.content}})

                print(result.content)
              
                # func_part = self.types.Part.from_function_response(
                #     name=fc.name,
                #     response ={
                #         "content": result.content[0].text,
                #     }
                # )

                message.append(self.types.Content(role="model",  parts=self.types.Part(function_call=fc)))
                message.append(self.types.Content(role="user",   parts=[self.types.Part.from_function_response(name=fc.name,response={"content":result.content[0].text})]))

                # message.append({
                #     "role":"user",
                #     "parts": self.types
                # })

                response = self.client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=message,
                    config=self.types.GenerateContentConfig(
                    temperature=0,
                    tools=available_tools
                    )
                )

                final_text.append(response.text)

            elif content.text:
                final_text.append(content.text)

        return "\n".join(final_text)

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")

        while True:
            try:
                query = input("\nUser : ").strip()

                if query.lower() == "quit":
                    break

                response = await self.process_query(query)
                print("\nLLM :" + response)
            except Exception as e:
                print(f"\nError : {str(e)} ")

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)

    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    import sys
    asyncio.run(main())