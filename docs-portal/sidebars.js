module.exports = {
  tutorialSidebar: [
    {
      type: "doc",
      id: "intro",
      label: "Introduction",
    },
    {
      type: "category",
      label: "Getting Started",
      collapsed: false,
      items: [
        "getting-started/macos-quickstart",
        "getting-started/fundamentals",
        "getting-started/bare-metal-setup",
      ],
    },
    {
      type: "category",
      label: "Core Platform",
      items: [
        "models",
        "agents-and-personality",
        "mcp-server",
        "n8n-automation",
        "telegram-bridge",
      ],
    },
    {
      type: "category",
      label: "Architecture",
      items: [
        "architecture-mermaid",
        "core-v2",
        "data-portability",
        "core-architecture/pluggability",
        "frontend-architecture",
      ],
    },
    {
      type: "category",
      label: "API & Integrations",
      items: [
        "api-reference",
        "integration-playbook",
        "erp-connection",
        "first-rag",
      ],
    },
    {
      type: "category",
      label: "Production & Compliance",
      items: [
        "production-hardening",
        "compliance-report",
        "zds-manifesto",
        "zds-style-guide",
      ],
    },
  ],
};
