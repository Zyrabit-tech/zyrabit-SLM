import React, { useState } from 'react';
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
    tag: 'ARCHITECTURE',
    title: 'Pluggable Hexagonal Core',
    description: 'De-coupled ports & adapters. Swap out vector DBs, LLM inference backends, or parsers without changing business logic.',
  },
  {
    tag: 'SECURITY',
    title: '100% Sovereign & Offline',
    description: 'Air-gapped by default. Zero phone-home calls or external API keys required. Your enterprise data never leaves your metal.',
  },
  {
    tag: 'RUNTIME',
    title: 'Multi-Model Execution',
    description: 'Simultaneously serve local text LLMs, embeddings (BGE/nomic), audio transcription (Whisper), and OCR document engines.',
  },
  {
    tag: 'HARDWARE',
    title: 'Hardware Acceleration',
    description: 'Auto-detects and maximizes Metal (Apple Silicon), CUDA (NVIDIA), CPU AVX512, and Tenstorrent Blackhole p150 silicon.',
  },
  {
    tag: 'INTERFACES',
    title: 'Universal Connectivity',
    description: 'Native REST endpoints, Socket.IO real-time streams, MCP RPC tools, and automated n8n webhook triggers.',
  },
  {
    tag: 'STORAGE',
    title: 'Hybrid Durable Storage',
    description: 'SQLite WAL state manager paired with ChromaDB vector store and BM25 lexical retriever for exact cited evidence.',
  },
];

export default function Home() {
  const [copied, setCopied] = useState(false);

  const handleCopyCommand = () => {
    navigator.clipboard.writeText('./zyra.sh install');
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Layout
      title="Sovereign Local AI Infrastructure"
      description="Deploy, extend, and run a fully private AI stack on your own hardware.">
      
      <header className="landing-hero">
        <div className="hero-pill-badge">
          <span className="hero-pill-dot"></span>
          Zyrabit SLM v0.1.0 • Pluggable Hexagonal Architecture
        </div>

        <h1 className="landing-title">
          Sovereign Local AI Infrastructure
        </h1>
        
        <p className="landing-subtitle">
          Run private inference, multi-modal document RAG, and automated MCP tool workflows 100% on your own hardware. No cloud. No tracking. Complete data sovereignty.
        </p>

        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', justifyContent: 'center', zIndex: 10, marginBottom: '20px' }}>
          <Link
            className="landing-cta-primary"
            to="/docs/getting-started/fundamentals">
            Get Started →
          </Link>
          <Link
            className="landing-cta-secondary"
            to="/docs/architecture/hexagonal">
            Architecture Blueprint
          </Link>
          <Link
            className="landing-cta-secondary"
            to="https://assets.zyrabit.com/streaming/zyrabit_ocrtex_bot.mp4">
            Watch Demo ▶
          </Link>
        </div>

        <div className="hero-cli-bar">
          <code>$ ./zyra.sh install</code>
          <button className="hero-cli-btn" onClick={handleCopyCommand} title="Copy install command">
            {copied ? '✓ Copied' : '📋 Copy'}
          </button>
        </div>

        <div style={{ width: '100%', maxWidth: '940px', margin: '3.5rem auto 0 auto', zIndex: 5 }}>
          <HeroSceneWrapper />
        </div>
      </header>

      <main>
        <section className="landing-features-section">
          <div className="section-header">
            <h2 className="section-title">Built for Enterprise Data Sovereignty</h2>
            <p className="section-subtitle">Everything you need to orchestrate local SLMs without cloud dependencies.</p>
          </div>

          <div className="landing-features-grid">
            {FEATURES.map((feature, idx) => (
              <div key={idx} className="feature-card">
                <div>
                  <span className="feature-tag">{feature.tag}</span>
                  <h3>{feature.title}</h3>
                  <p>{feature.description}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="demo-video-section">
          <div className="demo-video-card">
            <video 
              controls 
              poster="https://assets.zyrabit.com/streaming/poster.jpg"
              preload="none"
              style={{ width: '100%', aspectRatio: '16/9', backgroundColor: '#090d16' }}
            >
              <source src="https://assets.zyrabit.com/streaming/zyrabit_ocrtex_bot.mp4" type="video/mp4" />
              Your browser does not support the video tag.
            </video>
            <div className="demo-video-info">
              <h3>Zyrabit SLM — Production Document Node Demo</h3>
              <p>Observe fully local document ingestion, evidence unit extraction, PII protection, and offline inference in real time.</p>
            </div>
          </div>
        </section>
      </main>
      
    </Layout>
  );
}
