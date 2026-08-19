import React from 'react';
import BrowserOnly from '@docusaurus/BrowserOnly';
import {
  ReactFlow,
  Background,
  Controls,
  Handle,
  Position,
  useNodesState,
  useEdgesState,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

/* 
 * Mermaid Fallback for AI Consumability
 * 
 * flowchart LR
 *   Client --> FastAPI
 *   FastAPI --> PII[PII Pipeline]
 *   PII --> Gatekeeper
 *   Gatekeeper -->|rag| RAG[RAG Branch]
 *   Gatekeeper -->|direct| Direct[Direct Branch]
 *   RAG --> Inference
 *   Direct --> Inference
 *   Inference --> Cache
 *   Cache --> Response
 */

const baseNodeStyle = {
  padding: '12px 16px',
  borderRadius: '12px',
  background: 'var(--zyrabit-surface-glass)',
  backdropFilter: 'blur(12px)',
  border: '1px solid var(--zyrabit-border)',
  fontSize: '14px',
  fontWeight: '600',
  color: 'var(--zyrabit-text)',
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  minWidth: '150px',
  boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
};

const StepNode = ({ data }) => (
  <div style={{ ...baseNodeStyle, borderLeft: `4px solid ${data.color || 'var(--zyrabit-primary)'}` }}>
    <Handle type="target" position={Position.Left} />
    <span style={{ fontSize: '1.2rem' }}>{data.icon}</span>
    <div>
      <div style={{ fontWeight: '700' }}>{data.label}</div>
      <div style={{ fontSize: '11px', color: 'var(--zyrabit-subtext)', fontWeight: 'normal' }}>{data.desc}</div>
    </div>
    <Handle type="source" position={Position.Right} />
  </div>
);

const nodeTypes = {
  step: StepNode,
};

const initialNodes = [
  { id: '1', type: 'step', position: { x: 50, y: 150 }, data: { label: 'Client Request', icon: '👤', desc: 'POST /v1/chat', color: '#6090b4' } },
  { id: '2', type: 'step', position: { x: 280, y: 150 }, data: { label: 'FastAPI', icon: '⚡', desc: 'Primary Adapter', color: '#4ecdc4' } },
  { id: '3', type: 'step', position: { x: 520, y: 150 }, data: { label: 'PII Pipeline', icon: '🛡️', desc: 'Mask sensitive data', color: '#ff6b6b' } },
  { id: '4', type: 'step', position: { x: 760, y: 150 }, data: { label: 'Gatekeeper', icon: '🚦', desc: 'Routing decision', color: '#3f5a6d' } },
  { id: '5a', type: 'step', position: { x: 1000, y: 80 }, data: { label: 'RAG Branch', icon: '📚', desc: 'Hybrid retrieval', color: '#6090b4' } },
  { id: '5b', type: 'step', position: { x: 1000, y: 220 }, data: { label: 'Direct Branch', icon: '🎯', desc: 'Bypass retrieval', color: '#6090b4' } },
  { id: '6', type: 'step', position: { x: 1250, y: 150 }, data: { label: 'Inference', icon: '🧠', desc: 'LLM Generation', color: '#9b59b6' } },
  { id: '7', type: 'step', position: { x: 1480, y: 150 }, data: { label: 'Cache & De-mask', icon: '💾', desc: 'Store & Restore PII', color: '#f39c12' } },
  { id: '8', type: 'step', position: { x: 1720, y: 150 }, data: { label: 'Response', icon: '✉️', desc: 'To Client', color: '#2ecc71' } },
];

const initialEdges = [
  { id: 'e1-2', source: '1', target: '2', animated: true },
  { id: 'e2-3', source: '2', target: '3', animated: true },
  { id: 'e3-4', source: '3', target: '4', animated: true },
  { id: 'e4-5a', source: '4', target: '5a', animated: true, label: '"rag"' },
  { id: 'e4-5b', source: '4', target: '5b', animated: true, label: '"direct"' },
  { id: 'e5a-6', source: '5a', target: '6', animated: true },
  { id: 'e5b-6', source: '5b', target: '6', animated: true },
  { id: 'e6-7', source: '6', target: '7', animated: true },
  { id: 'e7-8', source: '7', target: '8', animated: true },
];

function Flow() {
  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  return (
    <div className="diagram-container" style={{ height: '400px', width: '100%' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.2}
      >
        <Background color="var(--zyrabit-muted)" gap={16} />
        <Controls />
      </ReactFlow>
    </div>
  );
}

export default function DataFlowDiagram() {
  return (
    <BrowserOnly fallback={<div>Loading diagram...</div>}>
      {() => <Flow />}
    </BrowserOnly>
  );
}
