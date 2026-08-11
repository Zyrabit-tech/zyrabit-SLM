import React, { useRef, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Html, Float, Line } from '@react-three/drei';

const PILLARS = [
  { id: 1, label: 'Inference', color: '#4ecdc4', icon: '🧠', desc: 'Local LLM & SLM execution (Ollama, MLX, OpenAI)' },
  { id: 2, label: 'Retrieval', color: '#6090b4', icon: '🔍', desc: 'Hybrid search (BM25 + ChromaDB Vector Store)' },
  { id: 3, label: 'State', color: '#ff6b6b', icon: '💾', desc: 'SQLite WAL SovereignStateManager persistence' },
  { id: 4, label: 'Security', color: '#ffbe0b', icon: '🛡️', desc: 'PII anonymization & de-anonymization shield' },
  { id: 5, label: 'Transport', color: '#3a86c8', icon: '🌐', desc: 'REST API, Socket.IO, and MCP RPC routing' },
  { id: 6, label: 'Automation', color: '#a29bfe', icon: '⚙️', desc: 'n8n workflow triggers and custom webhook ports' },
];

function OrbitingNode({ angle, radius, pillar, index, activeHover, setActiveHover }) {
  const meshRef = useRef();
  const [hovered, setHovered] = useState(false);

  // Use state or props to track node position for line drawing
  const [pos, setPos] = useState([0, 0, 0]);

  useFrame((state) => {
    if (!meshRef.current) return;
    const time = state.clock.elapsedTime * 0.15;
    // Calculate orbital position with unique offset
    const currentAngle = angle + time;
    const x = Math.cos(currentAngle) * radius;
    const z = Math.sin(currentAngle) * radius;
    const y = Math.sin(state.clock.elapsedTime * 0.8 + index) * 0.15; // smooth bobbing
    
    meshRef.current.position.set(x, y, z);
    setPos([x, y, z]);
  });

  const isCurrentHovered = hovered || activeHover === pillar.id;

  return (
    <group>
      {/* Connector Line to Hexagon Center */}
      <Line
        points={[[0, 0, 0], pos]}
        color={isCurrentHovered ? pillar.color : '#3f5a6d'}
        lineWidth={isCurrentHovered ? 2.5 : 1}
        opacity={isCurrentHovered ? 0.9 : 0.4}
        transparent
      />

      {/* Orbiting Sphere Mesh */}
      <mesh
        ref={meshRef}
        onPointerOver={(e) => {
          e.stopPropagation();
          setHovered(true);
          setActiveHover(pillar.id);
        }}
        onPointerOut={(e) => {
          e.stopPropagation();
          setHovered(false);
          setActiveHover(null);
        }}
        scale={isCurrentHovered ? 1.3 : 1.0}
      >
        <icosahedronGeometry args={[0.22, 2]} />
        <meshStandardMaterial
          color={isCurrentHovered ? pillar.color : '#3f5a6d'}
          roughness={0.1}
          metalness={0.8}
          emissive={isCurrentHovered ? pillar.color : '#000000'}
          emissiveIntensity={isCurrentHovered ? 0.6 : 0}
        />

        {/* HTML Label display */}
        <Html center position={[0, 0.4, 0]} distanceFactor={8} zIndexRange={[100, 0]}>
          <div
            style={{
              background: 'var(--zyrabit-surface-glass)',
              backdropFilter: 'blur(16px)',
              WebkitBackdropFilter: 'blur(16px)',
              border: `1.5px solid ${isCurrentHovered ? pillar.color : 'var(--zyrabit-border)'}`,
              padding: '6px 12px',
              borderRadius: '10px',
              color: 'var(--zyrabit-text)',
              fontFamily: 'var(--ifm-font-family-base)',
              fontSize: '11px',
              fontWeight: '700',
              pointerEvents: 'none',
              whiteSpace: 'nowrap',
              boxShadow: isCurrentHovered ? `0 0 15px ${pillar.color}40` : 'none',
              transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
              transform: isCurrentHovered ? 'scale(1.08)' : 'scale(1)',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <span>{pillar.icon}</span>
            <span>{pillar.label}</span>
          </div>
        </Html>

        {/* Detailed Popover when Hovered */}
        {isCurrentHovered && (
          <Html center position={[0, -0.6, 0]} distanceFactor={6} zIndexRange={[100, 0]}>
            <div
              style={{
                background: 'rgba(13, 17, 23, 0.95)',
                border: `1px solid ${pillar.color}`,
                padding: '12px 16px',
                borderRadius: '12px',
                color: '#e6edf3',
                fontFamily: 'var(--ifm-font-family-base)',
                fontSize: '11px',
                pointerEvents: 'none',
                width: '180px',
                boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
                lineHeight: '1.4',
                animation: 'fadeInUp 0.2s ease forwards',
              }}
            >
              <div style={{ fontWeight: 'bold', color: pillar.color, marginBottom: '4px', fontSize: '12px' }}>
                {pillar.icon} {pillar.label} Layer
              </div>
              <div style={{ opacity: 0.85 }}>{pillar.desc}</div>
            </div>
          </Html>
        )}
      </mesh>
    </group>
  );
}

function HexagonCore({ activeHover, setActiveHover }) {
  const coreMeshRef = useRef();
  const wireMeshRef = useRef();

  useFrame((state) => {
    const rotSpeed = state.clock.elapsedTime * 0.1;
    if (coreMeshRef.current) coreMeshRef.current.rotation.y = rotSpeed;
    if (wireMeshRef.current) wireMeshRef.current.rotation.y = rotSpeed;
  });

  const activePillar = PILLARS.find(p => p.id === activeHover);
  const coreColor = activePillar ? activePillar.color : '#3f5a6d';

  return (
    <Float speed={1.5} rotationIntensity={0.15} floatIntensity={0.3}>
      <group>
        {/* Solid Glass Hexagonal Prism Core */}
        <mesh ref={coreMeshRef}>
          <cylinderGeometry args={[0.9, 0.9, 0.8, 6]} />
          <meshPhysicalMaterial
            color={coreColor}
            roughness={0.15}
            metalness={0.1}
            transmission={0.7}
            thickness={1.5}
            transparent
            opacity={0.8}
            emissive={coreColor}
            emissiveIntensity={activeHover ? 0.3 : 0.05}
          />
        </mesh>

        {/* Outer Hexagonal Wireframe Outline */}
        <mesh ref={wireMeshRef}>
          <cylinderGeometry args={[0.91, 0.91, 0.81, 6]} />
          <meshBasicMaterial
            color={coreColor}
            wireframe
            transparent
            opacity={0.5}
          />
        </mesh>

        {/* Orbiting Pillars */}
        {PILLARS.map((pillar, i) => {
          const angle = (i / 6) * Math.PI * 2;
          return (
            <OrbitingNode
              key={pillar.id}
              angle={angle}
              radius={2.1}
              pillar={pillar}
              index={i}
              activeHover={activeHover}
              setActiveHover={setActiveHover}
            />
          );
        })}
      </group>
    </Float>
  );
}

export default function HeroScene() {
  const [activeHover, setActiveHover] = useState(null);

  return (
    <div className="hero-3d-container">
      <Canvas frameloop="demand" camera={{ position: [0, 2.5, 4.8], fov: 45 }}>
        <ambientLight intensity={0.65} />
        {/* Colorful dynamic lighting */}
        <pointLight position={[10, 10, 10]} intensity={1.2} />
        <pointLight position={[-10, -10, -10]} intensity={0.5} color="#4ecdc4" />
        <directionalLight position={[0, 5, 0]} intensity={0.8} />

        <HexagonCore activeHover={activeHover} setActiveHover={setActiveHover} />

        <OrbitControls
          enableZoom={true}
          minDistance={2.5}
          maxDistance={6.5}
          enablePan={false}
          minPolarAngle={Math.PI / 4}
          maxPolarAngle={Math.PI / 1.8}
          autoRotate={!activeHover}
          autoRotateSpeed={0.3}
        />
      </Canvas>
    </div>
  );
}
