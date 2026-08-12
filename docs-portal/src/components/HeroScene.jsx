import React, { useRef, useState, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Html, Float } from '@react-three/drei';
import * as THREE from 'three';

// ── ARCHITECTURAL LAYERS SPECIFICATION ──
const ARCHITECTURE_LAYERS = [
  {
    id: 'layer-4',
    level: 4,
    y: 1.8,
    name: 'Edge Transport & Agent Control',
    subtitle: 'Layer 4 • Public Interface & Gateway',
    color: '#38bdf8',
    emissive: '#0284c7',
    tag: 'NETWORKING & AGENTS',
    nodes: [
      { name: 'MCP RPC Bridge', detail: 'JSON-RPC 2.0 • 12 Pluggable Tools' },
      { name: 'Socket.IO Stream', detail: 'Real-time WebSocket event bus' },
      { name: 'REST OpenAPI', detail: '/v1/chat, /v1/sources/import' },
      { name: 'n8n Automation', detail: 'Signed webhook workflow triggers' }
    ],
    telemetry: {
      latency: '< 1ms dispatch',
      throughput: '10,000 req/min',
      protocols: 'MCP RPC, HTTP/2, WS',
      security: 'Bearer API Key & Scope Isolation'
    }
  },
  {
    id: 'layer-3',
    level: 3,
    y: 0.6,
    name: 'AI Agent & Security Harness',
    subtitle: 'Layer 3 • Sovereign Logic & Guardrails',
    color: '#34d399',
    emissive: '#059669',
    tag: 'REASONING & SAFETY',
    nodes: [
      { name: 'ReAct Agent Harness', detail: 'Lazy Tool Loader (0ms Intent Class)' },
      { name: 'PII Sandwich Shield', detail: 'Mask → Execute → Re-mask Pipeline' },
      { name: 'Token Budget Guard', detail: 'Emergency Context Compactor (70%)' },
      { name: 'Idempotency Tracker', detail: 'SQLite WAL Job Queue & Audit' }
    ],
    telemetry: {
      intent_classifier: '0ms Keyword Match',
      pii_overhead: '< 2ms Regex/NER',
      context_cap: '70% Token Budget',
      isolation: 'Strict Document Scope'
    }
  },
  {
    id: 'layer-2',
    level: 2,
    y: -0.6,
    name: 'Sovereign Storage & Retrieval',
    subtitle: 'Layer 2 • Hybrid RAG Engine',
    color: '#818cf8',
    emissive: '#4f46e5',
    tag: 'DATA & MEMORY',
    nodes: [
      { name: 'ChromaDB Vector Store', detail: 'Persistent collection embeddings' },
      { name: 'BM25 Lexical Search', detail: 'In-memory exact keyword retriever' },
      { name: 'SQLite WAL State', detail: 'SovereignStateManager & Memory' },
      { name: 'SHA-256 Storage', detail: 'Immutable source file vault' }
    ],
    telemetry: {
      embeddings: 'BAAI/bge-small-en-v1.5',
      hybrid_ratio: '50% Vector / 50% Lexical',
      chunk_size: '512 tokens (50 overlap)',
      persistence: 'Zero Ephemeral Fallback'
    }
  },
  {
    id: 'layer-1',
    level: 1,
    y: -1.8,
    name: 'Hardware Inference Acceleration',
    subtitle: 'Layer 1 • On-Prem Silicon Runtimes',
    color: '#fbbf24',
    emissive: '#d97706',
    tag: 'PHYSICAL SILICON',
    nodes: [
      { name: 'Tenstorrent p150', detail: 'Blackhole Silicon (vLLM-TT metal)' },
      { name: 'Apple Metal / MLX', detail: 'Unified RAM M-Series acceleration' },
      { name: 'CUDA / TensorRT', detail: 'NVIDIA vLLM & Ollama fallback' },
      { name: 'Embedded llama.cpp', detail: 'CPU AVX512 zero-dependency' }
    ],
    telemetry: {
      ttft: '~80-105 ms (TT p150)',
      tps: '21 tokens/sec (Qwen 2.5 3B)',
      airgap: '100% Offline (Internal Net)',
      quantization: 'bfloat16 / Q4_K_M'
    }
  }
];

// ── PARTICLES DATA STREAM ──
function DataStreamParticles({ count = 40 }) {
  const points = useMemo(() => {
    const p = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const angle = Math.random() * Math.PI * 2;
      const radius = 0.5 + Math.random() * 1.5;
      p[i * 3] = Math.cos(angle) * radius;
      p[i * 3 + 1] = -2.2 + Math.random() * 4.4;
      p[i * 3 + 2] = Math.sin(angle) * radius;
    }
    return p;
  }, [count]);

  const pointsRef = useRef();

  useFrame((_, delta) => {
    if (!pointsRef.current) return;
    const positions = pointsRef.current.geometry.attributes.position.array;
    for (let i = 0; i < count; i++) {
      positions[i * 3 + 1] += delta * 1.2;
      if (positions[i * 3 + 1] > 2.2) {
        positions[i * 3 + 1] = -2.2;
      }
    }
    pointsRef.current.geometry.attributes.position.needsUpdate = true;
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={count}
          array={points}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial
        size={0.06}
        color="#38bdf8"
        transparent
        opacity={0.7}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}

// ── HEXAGONAL GLASS PLATFORM MESH ──
function HexagonalLayerPlatform({ layer, isSelected, isHovered, onSelect, onHover }) {
  const meshRef = useRef();
  const wireRef = useRef();

  useFrame((state) => {
    if (!meshRef.current) return;
    // Gentle floating rotation
    const rotSpeed = state.clock.elapsedTime * 0.05;
    meshRef.current.rotation.y = rotSpeed;
    if (wireRef.current) wireRef.current.rotation.y = rotSpeed;
  });

  const isActive = isSelected || isHovered;

  return (
    <group position={[0, layer.y, 0]}>
      {/* Central Solid Metallic Glass Hexagon */}
      <mesh
        ref={meshRef}
        onClick={(e) => {
          e.stopPropagation();
          onSelect(layer.id);
        }}
        onPointerOver={(e) => {
          e.stopPropagation();
          onHover(layer.id);
        }}
        onPointerOut={(e) => {
          e.stopPropagation();
          onHover(null);
        }}
        scale={isActive ? [2.3, 0.18, 2.3] : [2.1, 0.15, 2.1]}
      >
        <cylinderGeometry args={[1, 1, 1, 6]} />
        <meshPhysicalMaterial
          color={isActive ? layer.color : '#1e293b'}
          emissive={isActive ? layer.emissive : '#090d16'}
          emissiveIntensity={isActive ? 0.6 : 0.1}
          metalness={0.8}
          roughness={0.2}
          transmission={0.5}
          thickness={1.2}
          transparent
          opacity={0.85}
        />
      </mesh>

      {/* Illuminated Edge Wireframe Ring */}
      <mesh ref={wireRef} scale={isActive ? [2.32, 0.19, 2.32] : [2.12, 0.16, 2.12]}>
        <cylinderGeometry args={[1, 1, 1, 6]} />
        <meshBasicMaterial
          color={isActive ? layer.color : '#475569'}
          wireframe
          transparent
          opacity={isActive ? 0.9 : 0.3}
        />
      </mesh>

      {/* Layer Label on 3D Space */}
      <Html position={[2.6, 0, 0]} distanceFactor={7} zIndexRange={[100, 0]}>
        <div
          onClick={() => onSelect(layer.id)}
          style={{
            background: isActive ? 'rgba(15, 23, 42, 0.92)' : 'rgba(15, 23, 42, 0.65)',
            border: `1.5px solid ${isActive ? layer.color : 'rgba(255,255,255,0.1)'}`,
            padding: '6px 14px',
            borderRadius: '10px',
            color: '#f8fafc',
            fontFamily: "'Plus Jakarta Sans', sans-serif",
            fontSize: '12px',
            fontWeight: '700',
            cursor: 'pointer',
            whiteSpace: 'nowrap',
            backdropFilter: 'blur(12px)',
            boxShadow: isActive ? `0 0 20px ${layer.color}40` : '0 4px 12px rgba(0,0,0,0.2)',
            transition: 'all 0.25s ease',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          <span
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: layer.color,
              boxShadow: `0 0 8px ${layer.color}`,
            }}
          />
          <span>{layer.name}</span>
        </div>
      </Html>
    </group>
  );
}

// ── 3D SCENE COMPONENT ──
function Architecture3DScene({ selectedLayerId, hoveredLayerId, onSelectLayer, onHoverLayer }) {
  return (
    <Float speed={1.2} rotationIntensity={0.08} floatIntensity={0.2}>
      <group>
        {/* Central Energy Core Beam */}
        <mesh position={[0, 0, 0]}>
          <cylinderGeometry args={[0.08, 0.08, 4.4, 16]} />
          <meshBasicMaterial color="#38bdf8" transparent opacity={0.4} />
        </mesh>

        {/* Data Stream Particles */}
        <DataStreamParticles count={50} />

        {/* Stacked Architecture Platforms */}
        {ARCHITECTURE_LAYERS.map((layer) => (
          <HexagonalLayerPlatform
            key={layer.id}
            layer={layer}
            isSelected={selectedLayerId === layer.id}
            isHovered={hoveredLayerId === layer.id}
            onSelect={onSelectLayer}
            onHover={onHoverLayer}
          />
        ))}
      </group>
    </Float>
  );
}

// ── MAIN HERO SCENE EXPORT ──
export default function HeroScene() {
  const [selectedLayerId, setSelectedLayerId] = useState('layer-4');
  const [hoveredLayerId, setHoveredLayerId] = useState(null);

  const activeLayerId = hoveredLayerId || selectedLayerId;
  const activeLayer = ARCHITECTURE_LAYERS.find((l) => l.id === activeLayerId) || ARCHITECTURE_LAYERS[0];

  return (
    <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      
      {/* 3D Canvas Canvas & Overlay Telemetry Card */}
      <div className="hero-3d-container" style={{ position: 'relative', height: '520px' }}>
        
        {/* Top Control Header Overlay inside 3D Canvas */}
        <div
          style={{
            position: 'absolute',
            top: '16px',
            left: '20px',
            zIndex: 10,
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            pointerEvents: 'none',
          }}
        >
          <div
            style={{
              padding: '6px 14px',
              borderRadius: '8px',
              background: 'rgba(9, 13, 22, 0.85)',
              border: '1px solid var(--zyrabit-border)',
              backdropFilter: 'blur(12px)',
              color: 'var(--zyrabit-text-main)',
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: '11px',
              fontWeight: '600',
            }}
          >
            ● INTERACTIVE ARCHITECTURE ENGINE
          </div>
        </div>

        {/* Floating Telemetry Inspector Card (Top Right) */}
        <div
          style={{
            position: 'absolute',
            top: '16px',
            right: '20px',
            zIndex: 10,
            width: '320px',
            background: 'rgba(15, 23, 42, 0.92)',
            border: `1.5px solid ${activeLayer.color}`,
            borderRadius: '14px',
            padding: '18px',
            backdropFilter: 'blur(16px)',
            boxShadow: `0 12px 40px rgba(0,0,0,0.4), 0 0 20px ${activeLayer.color}30`,
            transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
            color: '#f8fafc',
            fontFamily: "'Plus Jakarta Sans', sans-serif",
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span
              style={{
                fontSize: '10px',
                fontWeight: '800',
                letterSpacing: '0.08em',
                color: activeLayer.color,
                background: `${activeLayer.color}15`,
                padding: '3px 8px',
                borderRadius: '4px',
                border: `1px solid ${activeLayer.color}40`,
              }}
            >
              {activeLayer.tag}
            </span>
            <span style={{ fontSize: '11px', color: '#94a3b8', fontFamily: "'JetBrains Mono', monospace" }}>
              LAYER {activeLayer.level}/4
            </span>
          </div>

          <h4 style={{ margin: '0 0 4px 0', fontSize: '15px', fontWeight: '800', color: '#ffffff' }}>
            {activeLayer.name}
          </h4>
          <p style={{ margin: '0 0 14px 0', fontSize: '11px', color: '#94a3b8' }}>
            {activeLayer.subtitle}
          </p>

          {/* Subsystem Components List */}
          <div style={{ marginBottom: '14px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div style={{ fontSize: '10px', fontWeight: '700', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Core Subsystems:
            </div>
            {activeLayer.nodes.map((node, idx) => (
              <div
                key={idx}
                style={{
                  background: 'rgba(255, 255, 255, 0.04)',
                  border: '1px solid rgba(255, 255, 255, 0.06)',
                  padding: '6px 10px',
                  borderRadius: '6px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <span style={{ fontSize: '11px', fontWeight: '700', color: '#e2e8f0' }}>{node.name}</span>
                <span style={{ fontSize: '10px', color: '#94a3b8', fontFamily: "'JetBrains Mono', monospace" }}>
                  {node.detail.split('•')[0]}
                </span>
              </div>
            ))}
          </div>

          {/* Technical Telemetry Grid */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: '8px',
              paddingTop: '10px',
              borderTop: '1px solid rgba(255,255,255,0.08)',
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: '10px',
            }}
          >
            {Object.entries(activeLayer.telemetry).map(([key, value]) => (
              <div key={key}>
                <div style={{ color: '#64748b', textTransform: 'uppercase', fontSize: '9px' }}>{key.replace('_', ' ')}</div>
                <div style={{ color: activeLayer.color, fontWeight: '600' }}>{value}</div>
              </div>
            ))}
          </div>
        </div>

        {/* 3D Canvas Rendering Engine */}
        <Canvas frameloop="demand" camera={{ position: [4.2, 2.5, 6.5], fov: 42 }}>
          <ambientLight intensity={0.7} />
          <pointLight position={[10, 15, 10]} intensity={1.5} color="#ffffff" />
          <pointLight position={[-10, -10, -10]} intensity={0.8} color="#38bdf8" />
          <directionalLight position={[0, 8, 0]} intensity={1.0} />

          <Architecture3DScene
            selectedLayerId={selectedLayerId}
            hoveredLayerId={hoveredLayerId}
            onSelectLayer={setSelectedLayerId}
            onHoverLayer={setHoveredLayerId}
          />

          <OrbitControls
            enableZoom={true}
            minDistance={4.0}
            maxDistance={9.5}
            enablePan={false}
            minPolarAngle={Math.PI / 4}
            maxPolarAngle={Math.PI / 1.7}
            autoRotate={!hoveredLayerId}
            autoRotateSpeed={0.35}
          />
        </Canvas>
      </div>

      {/* Layer Selection Selector Bar Below Canvas */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '12px',
        }}
      >
        {ARCHITECTURE_LAYERS.map((layer) => {
          const isSelected = selectedLayerId === layer.id;
          return (
            <button
              key={layer.id}
              onClick={() => setSelectedLayerId(layer.id)}
              style={{
                background: isSelected ? 'var(--zyrabit-surface)' : 'var(--zyrabit-surface-glass)',
                border: `1.5px solid ${isSelected ? layer.color : 'var(--zyrabit-border)'}`,
                borderRadius: '12px',
                padding: '14px',
                textAlign: 'left',
                cursor: 'pointer',
                transition: 'all 0.25s ease',
                boxShadow: isSelected ? `0 4px 20px ${layer.color}25` : 'none',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                <span style={{ fontSize: '10px', fontWeight: '800', color: layer.color, fontFamily: "'JetBrains Mono', monospace" }}>
                  L{layer.level}
                </span>
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: layer.color }} />
              </div>
              <div style={{ fontSize: '12px', fontWeight: '700', color: 'var(--zyrabit-text-main)', marginBottom: '2px' }}>
                {layer.name}
              </div>
              <div style={{ fontSize: '10px', color: 'var(--zyrabit-text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {layer.nodes.map(n => n.name).join(' • ')}
              </div>
            </button>
          );
        })}
      </div>

    </div>
  );
}
