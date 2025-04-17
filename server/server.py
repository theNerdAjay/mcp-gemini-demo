from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Ajay MCP")

@mcp.tool()
def calculate_bmi(weight_kg : float, height_m : float):
    """Calculate the BMI given weight in kg and height in meters"""
    return weight_kg / (height_m**2)

@mcp.tool()
def calculate_area(width:float,height:float):
    """Calculate the area of rectangle of given width and height"""
    return width * height

@mcp.tool()
def secrect():
    """Returns the Secret to the User"""
    return "secret : thisisyoursecretyayelvishbhhhaaaai"

if __name__ == "__main__":
    mcp.run(transport='stdio')