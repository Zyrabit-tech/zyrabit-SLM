const config = {
  title: "Zyrabit Docs",
  tagline: "Local sovereign AI, production-ready",
  favicon: "https://assets.zyrabit.com/logos/favicon.png",
  url: "https://docs.zyrabit.com",
  baseUrl: "/",
  onBrokenLinks: "warn",

  i18n: {
    defaultLocale: "en",
    locales: ["en"],
  },

  themes: ["@docusaurus/theme-mermaid"],
  markdown: {
    mermaid: true,
  },

  plugins: [
    [
      require.resolve("@easyops-cn/docusaurus-search-local"),
      {
        hashed: true,
        language: ["en"],
        highlightSearchTermsOnTargetPage: true,
        explicitSearchResultPath: true,
      },
    ],
  ],

  presets: [
    [
      "classic",
      {
        docs: {
          sidebarPath: require.resolve("./sidebars.js"),
          editUrl:
            "https://github.com/Zyrabit-tech/zyrabit-SLM/edit/main/docs-portal/",
        },
        blog: false,
        theme: {
          customCss: require.resolve("./src/custom.css"),
        },
      },
    ],
  ],

  themeConfig: {
    metadata: [
      {
        name: "description",
        content:
          "Zyrabit SLM — Production-grade local AI orchestration with pluggable hexagonal architecture. Run sovereign inference, RAG, and document analysis 100% offline.",
      },
      {
        name: "keywords",
        content:
          "zyrabit, SLM, local AI, sovereign AI, RAG, hexagonal architecture, ollama, chroma, on-premise AI",
      },
      { property: "og:title", content: "Zyrabit SLM Documentation" },
      {
        property: "og:description",
        content:
          "Deploy, configure, and extend a fully local AI stack with pluggable components.",
      },
      { property: "og:type", content: "website" },
    ],

    colorMode: {
      defaultMode: "dark",
      disableSwitch: false,
      respectPrefersColorScheme: true,
    },

    navbar: {
      logo: {
        alt: "Zyrabit Logo",
        src: "https://assets.zyrabit.com/logos/zyrabit_black.png",
        srcDark: "https://assets.zyrabit.com/logos/zyrabit_white.png",
      },
      items: [
        {
          type: "docSidebar",
          sidebarId: "mainSidebar",
          position: "left",
          label: "Docs",
        },
        {
          to: "/docs/architecture/hexagonal",
          label: "Architecture",
          position: "left",
        },
        {
          to: "/docs/api-reference",
          label: "API",
          position: "left",
        },
        {
          href: "https://github.com/Zyrabit-tech/zyrabit-SLM",
          label: "GitHub",
          position: "right",
        },
      ],
    },

    footer: {
      style: "dark",
      links: [
        {
          title: "Docs",
          items: [
            { label: "Getting Started", to: "/docs/getting-started/fundamentals" },
            { label: "Architecture", to: "/docs/architecture/hexagonal" },
            { label: "API Reference", to: "/docs/api-reference" },
          ],
        },
        {
          title: "Community",
          items: [
            {
              label: "GitHub Discussions",
              href: "https://github.com/Zyrabit-tech/zyrabit-SLM/discussions",
            },
            {
              label: "GitHub Issues",
              href: "https://github.com/Zyrabit-tech/zyrabit-SLM/issues",
            },
          ],
        },
        {
          title: "More",
          items: [
            { label: "Changelog", href: "https://github.com/Zyrabit-tech/zyrabit-SLM/blob/main/CHANGELOG.md" },
            { label: "License (MIT)", href: "https://github.com/Zyrabit-tech/zyrabit-SLM/blob/main/LICENSE" },
          ],
        },
      ],
      copyright: `© ${new Date().getFullYear()} Zyrabit. Sovereign AI, locally.`,
    },

    prism: {
      theme: require("prism-react-renderer").themes.github,
      darkTheme: require("prism-react-renderer").themes.dracula,
      additionalLanguages: ["bash", "python", "json", "yaml", "docker"],
    },
  },
};

module.exports = config;
