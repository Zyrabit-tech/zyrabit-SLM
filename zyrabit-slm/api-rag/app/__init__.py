"""Application package.

Importing ``app`` must not start optional integrations. Composition happens in
``app.main`` so tests and local utilities can use the Node domain in isolation.
"""
