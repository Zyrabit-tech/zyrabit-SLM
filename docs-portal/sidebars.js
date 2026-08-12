module.exports = {
  mainSidebar: [
    {
      type: "doc",
      id: "intro",
      label: "📖 Introduction",
    },

    {
      type: "category",
      label: "🚀 Getting Started",
      collapsed: false,
      items: [
        "getting-started/fundamentals",
        "first-rag",
        "installation",
        {
          type: "category",
          label: "Hardware Guides",
          items: ["getting-started/ubuntu-tenstorrent"],
        },
      ],
    },

    {
      type: "category",
      label: "🏗️ Architecture",
      collapsed: false,
      items: [
        "architecture/hexagonal",
        "agent-architecture",
        "core-architecture/pluggability",
        "architecture-mermaid",
        "core-v2",
        "frontend-architecture",
      ],
    },

    {
      type: "category",
      label: "🔧 Guides",
      items: [
        "guides/swap-database",
        "guides/swap-models",
        "guides/swap-hardware",
        "models",
        "telegram-bridge",
        "erp-connection",
      ],
    },

    {
      type: "category",
      label: "📡 API & Integrations",
      items: ["api-reference", "integration-playbook"],
    },

    {
      type: "category",
      label: "🛡️ Operations",
      items: [
        "production-hardening",
        "data-portability",
        "compliance-report",
        "benchmarks",
      ],
    },

    {
      type: "category",
      label: "📐 Design System",
      items: ["zds-manifesto", "zds-style-guide"],
    },

    {
      type: "doc",
      id: "ai-context",
      label: "🤖 AI Context",
    },
  ],
};
