import React from 'react';
import Layout from '@theme/Layout';
import Link from '@docusaurus/Link';
import BrowserOnly from '@docusaurus/BrowserOnly';

function HeroSceneWrapper() {
  return (
    <BrowserOnly fallback={<div className="hero-3d-fallback">Loading 3D Engine...</div>}>
      {() => {
        const HeroScene = require('../components/HeroScene').default;
        return <HeroScene />;
      }}
    </BrowserOnly>
  );
}

const FEATURES = [
  {
    title: '🏗️ Hexagonal Architecture',
    description: 'Swap any component without touching core logic. Clean separation of concerns.',
    delay: 1,
  },
  {
    title: '🔒 100% Offline',
    description: 'Air-gapped capable, zero external dependencies. Your data never leaves the device.',
    delay: 2,
  },
  {
    title: '🧠 Multi-Model',
    description: 'Text, audio, vision, embeddings — all running locally via optimized runtimes.',
    delay: 3,
  },
  {
    title: '⚡ Hardware-Aware',
    description: 'Auto-detects Metal, CUDA, AVX2, Tenstorrent to maximize hardware utilization.',
    delay: 4,
  },
  {
    title: '📡 Multiple Protocols',
    description: 'REST, Socket.IO, MCP, AG-UI — seamless integration into any ecosystem.',
    delay: 5,
  },
  {
    title: '🔌 Pluggable Storage',
    description: 'Chroma, PostgreSQL, SQLite — your choice of vector and relational stores.',
    delay: 6,
  },
];

export default function Home() {
  return (
    <Layout
      title="Sovereign AI, Locally"
      description="Deploy, extend, and run a fully private AI stack on your own hardware.">
      
      <header className="landing-hero">
        <h1 className="landing-title">Sovereign AI, Locally</h1>
        <p className="landing-subtitle">
          Deploy, extend, and run a fully private AI stack on your own hardware. No cloud. No external APIs. Complete data sovereignty.
        </p>
        
        <div style={{ display: 'flex', gap: '16px', marginBottom: '40px', zIndex: 10 }}>
          <Link
            className="landing-cta"
            to="/docs/getting-started/fundamentals">
            Get Started →
          </Link>
          <Link
            className="landing-cta"
            style={{ background: 'var(--zyrabit-surface-glass)', color: 'var(--zyrabit-text)', border: '1px solid var(--zyrabit-border)' }}
            to="https://assets.zyrabit.com/streaming/zyrabit_ocrtex_bot.mp4">
            Watch Demo
          </Link>
        </div>

        <div style={{ width: '100%', maxWidth: '900px', margin: '0 auto', zIndex: 5 }}>
          <HeroSceneWrapper />
        </div>
      </header>

      <main>
        <section className="landing-features">
          {FEATURES.map((feature, idx) => (
            <div key={idx} className={`feature-card animate-fade-in-up animate-delay-${feature.delay}`}>
              <h3>{feature.title}</h3>
              <p>{feature.description}</p>
            </div>
          ))}
        </section>

        <section className="demo-video-section">
          <div className="demo-video-card">
            <video 
              controls 
              poster="https://assets.zyrabit.com/streaming/poster.jpg"
              preload="none"
              style={{ width: '100%', aspectRatio: '16/9', backgroundColor: '#000' }}
            >
              <source src="https://assets.zyrabit.com/streaming/zyrabit_ocrtex_bot.mp4" type="video/mp4" />
              Your browser does not support the video tag.
            </video>
            <div className="demo-video-info">
              <h3>Zyrabit SLM Demo</h3>
              <p>See how Zyrabit orchestrates local models entirely offline.</p>
            </div>
          </div>
        </section>
      </main>
      
    </Layout>
  );
}
