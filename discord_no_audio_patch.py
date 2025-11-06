import sys
import types

# Create a dummy audioop module so discord.py can import it
sys.modules["audioop"] = types.ModuleType("audioop")
