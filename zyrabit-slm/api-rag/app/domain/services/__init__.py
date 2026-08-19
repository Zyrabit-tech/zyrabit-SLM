"""Domain services are imported explicitly by their consumers.

This prevents optional MCP/Docker/Obsidian integration setup as a side effect
of importing a document-operation service.
"""
