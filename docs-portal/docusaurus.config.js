const config = {
  title: "Zyrabit Docs",
  tagline: "Local sovereign AI, production-ready",
  favicon: "https://assets.zyrabit.com/logos/favicon.png",
  url: "https://docs.zyrabit.com",
  baseUrl: "/",
  onBrokenLinks: "throw",
  i18n: {
    defaultLocale: "en",
    locales: ["en"]
  },
  themes: ["@docusaurus/theme-mermaid"],
  markdown: {
    mermaid: true,
    hooks: {
      onBrokenMarkdownLinks: "warn"
    }
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
      title: "Docs",
      logo: {
        alt: "Zyrabit Logo",
        src: "https://assets.zyrabit.com/logos/zyrabit_black.png",
        srcDark: "https://assets.zyrabit.com/logos/zyrabit_white.png",
      },
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
