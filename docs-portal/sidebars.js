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
      items: [
        "getting-started/fundamentals",
        "first-rag",
        "installation",
      ],
    },
    {
      type: "category",
      label: "Core Architecture",
      items: [
        "architecture-mermaid",
        "models",
        "data-portability",
        "core-architecture/pluggability",
      ],
    },
    {
      type: "category",
      label: "API & Integrations",
      items: [
        "api-reference",
        "integration-playbook",
        "erp-connection",
      ],
    },
    {
      type: "category",
      label: "Production & Compliance",
      items: [
        "production-hardening",
        "compliance-report",
      ],
    },
  ],
};
