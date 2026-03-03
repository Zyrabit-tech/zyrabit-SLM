const config = {
  title: "Zyrabit Docs",
  tagline: "Local sovereign AI, production-ready",
  favicon: "img/favicon.ico",
  url: "https://localhost",
  baseUrl: "/",
  onBrokenLinks: "throw",
  onBrokenMarkdownLinks: "warn",
  i18n: {
    defaultLocale: "en",
    locales: ["en"]
  },
  themes: ["@docusaurus/theme-mermaid"],
  markdown: {
    mermaid: true
  },
  presets: [
    [
      "classic",
      {
        docs: {
          sidebarPath: require.resolve("./sidebars.js")
        },
        blog: false,
        theme: {
          customCss: require.resolve("./src/custom.css")
        }
      }
    ]
  ],
  themeConfig: {
    navbar: {
      title: "Zyrabit Docs",
      items: [
        {
          to: "/docs/intro",
          position: "left",
          label: "Docs"
        }
      ]
    }
  }
};

module.exports = config;
