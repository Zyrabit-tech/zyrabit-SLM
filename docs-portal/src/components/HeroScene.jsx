import React, { useRef, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Html, Float } from '@react-three/drei';

const PILLARS = [
  { id: 1, label: 'Inference', color: '#4ecdc4' },
  { id: 2, label: 'Retrieval', color: '#6090b4' },
  { id: 3, label: 'State', color: '#3f5a6d' },
  { id: 4, label: 'Security', color: '#4ecdc4' },
  { id: 5, label: 'Transport', color: '#6090b4' },
  { id: 6, label: 'Automation', color: '#3f5a6d' },
];

function PillarFace({ angle, radius, label, color, index }) {
  const [hovered, setHovered] = useState(false);
  const meshRef = useRef();

  const x = Math.cos(angle) * radius;
  const z = Math.sin(angle) * radius;
  
  // Angle for rotation so the face faces outward
  // If x = cos, z = sin, the normal vector is (cos, 0, sin)
  // We want the plane to face outward. A plane faces +Z by default.
  // We need to rotate it around Y axis by -angle (with offset for orientation).
  const rotationY = -angle + Math.PI / 2;

  return (
    <group position={[x, 0, z]} rotation={[0, rotationY, 0]}>
      <mesh
        ref={meshRef}
        onPointerOver={(e) => {
          e.stopPropagation();
          setHovered(true);
        }}
        onPointerOut={(e) => {
          e.stopPropagation();
          setHovered(false);
        }}
      >
        <planeGeometry args={[1.5, 2]} />
        <meshStandardMaterial
          color={hovered ? color : '#3f5a6d'}
          emissive={hovered ? color : '#000000'}
          emissiveIntensity={hovered ? 0.5 : 0}
          transparent
          opacity={0.9}
          roughness={0.2}
          metalness={0.8}
        />
        <lineSegments>
          <edgesGeometry args={[new (require('three').PlaneGeometry)(1.5, 2)]} />
          <lineBasicMaterial color={color} linewidth={2} />
        </lineSegments>
      </mesh>
      {hovered && (
        <Html center position={[0, 0, 0.1]} distanceFactor={8} zIndexRange={[100, 0]}>
          <div style={{
            background: 'rgba(22, 27, 34, 0.8)',
            padding: '8px 16px',
            borderRadius: '8px',
            color: '#fff',
            fontFamily: 'var(--ifm-font-family-base)',
            fontWeight: 'bold',
            border: `1px solid ${color}`,
            backdropFilter: 'blur(4px)',
            pointerEvents: 'none',
            whiteSpace: 'nowrap'
          }}>
            {label}
          </div>
        </Html>
      )}
    </group>
  );
}

function HexagonCore() {
  const groupRef = useRef();

  useFrame((state) => {
    if (groupRef.current) {
      groupRef.current.rotation.y = state.clock.elapsedTime * 0.2;
    }
  });

  const radius = 1.3;

  return (
    <Float speed={2} rotationIntensity={0.2} floatIntensity={0.5}>
      <group ref={groupRef}>
        {/* Core center to make it look solid */}
        <mesh>
          <cylinderGeometry args={[radius - 0.1, radius - 0.1, 1.9, 6]} />
          <meshStandardMaterial color="#1a1d23" roughness={0.8} metalness={0.5} />
        </mesh>
        
        {PILLARS.map((pillar, i) => {
          const angle = (i / 6) * Math.PI * 2;
          return (
            <PillarFace
              key={pillar.id}
              angle={angle}
              radius={radius}
              label={pillar.label}
              color={pillar.color}
              index={i}
            />
          );
        })}
      </group>
    </Float>
  );
}

export default function HeroScene() {
  return (
    <div className="hero-3d-container">
      <Canvas frameloop="demand" camera={{ position: [0, 2, 5], fov: 50 }}>
        <ambientLight intensity={0.6} />
        <directionalLight position={[10, 10, 5]} intensity={1} color="#ffffff" />
        <directionalLight position={[-10, -10, -5]} intensity={0.5} color="#4ecdc4" />
        
        <HexagonCore />
        
        <OrbitControls 
          enableZoom={true} 
          minDistance={3} 
          maxDistance={8}
          enablePan={false}
          minPolarAngle={Math.PI / 4}
          maxPolarAngle={Math.PI / 1.5}
          autoRotate
          autoRotateSpeed={0.5}
        />
      </Canvas>
    </div>
  );
}
