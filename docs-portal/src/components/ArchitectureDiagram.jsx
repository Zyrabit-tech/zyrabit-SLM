import React from 'react';
import BrowserOnly from '@docusaurus/BrowserOnly';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  useNodesState,
  useEdgesState,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

/* 
 * Mermaid Fallback for AI Consumability
 * 
 * flowchart TD
 *   A[Primary Adapters] --> B[Security Pipeline]
 *   B --> C[Domain Layer]
 *   C --> D[Port Contracts]
 *   D --> E[Inference Adapters]
 *   D --> F[Retrieval Adapters]
 *   E --> G[Hardware Layer]
 *   F --> G
 */

const baseNodeStyle = {
  background: 'var(--zyrabit-surface-glass)',
  backdropFilter: 'blur(12px)',
  borderRadius: '12px',
  overflow: 'hidden',
  width: '250px',
  boxShadow: '0 8px 32px rgba(0,0,0,0.05)',
};

const Header = ({ title, color }) => (
  <div style={{ background: color, padding: '8px 12px', color: '#fff', fontWeight: 'bold', fontSize: '14px', textAlign: 'center' }}>
    {title}
  </div>
);

const Content = ({ items, borderColor }) => (
  <div style={{ padding: '12px', border: `1px solid ${borderColor}`, borderTop: 'none', borderBottomLeftRadius: '12px', borderBottomRightRadius: '12px', background: 'var(--zyrabit-bg)', color: 'var(--zyrabit-text)' }}>
    <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '12px', lineHeight: '1.6' }}>
      {items.map((item, i) => <li key={i}>{item}</li>)}
    </ul>
  </div>
);

const PrimaryAdapterNode = ({ data }) => (
  <div style={baseNodeStyle}>
    <Header title="Primary Adapters (Driving)" color="#4ecdc4" />
    <Content items={['REST API (FastAPI)', 'Socket.IO', 'MCP Endpoints', 'AG-UI']} borderColor="#4ecdc4" />
    <Handle type="source" position={Position.Bottom} />
  </div>
);

const SecurityNode = ({ data }) => (
  <div style={baseNodeStyle}>
    <Handle type="target" position={Position.Top} />
    <Header title="Security Pipeline" color="#f39c12" />
    <Content items={['PII Pipeline', 'Anonymization']} borderColor="#f39c12" />
    <Handle type="source" position={Position.Bottom} />
  </div>
);

const DomainNode = ({ data }) => (
  <div style={baseNodeStyle}>
    <Handle type="target" position={Position.Top} />
    <Header title="Domain Layer (Core)" color="#3f5a6d" />
    <Content items={['ChatUseCase', 'IngestUseCase', 'Gatekeeper', 'HybridRetriever']} borderColor="#3f5a6d" />
    <Handle type="source" position={Position.Bottom} />
  </div>
);

const PortNode = ({ data }) => (
  <div style={{ ...baseNodeStyle, border: '2px dashed #2ba89e', background: 'transparent', boxShadow: 'none' }}>
    <Handle type="target" position={Position.Top} />
    <Header title="Port Contracts" color="#2ba89e" />
    <Content items={['InferencePort', 'VectorStorePort', 'StatePort', 'AutomationPort', 'McpClientPort']} borderColor="transparent" />
    <Handle type="source" position={Position.Bottom} />
  </div>
);

const AdapterNode = ({ data }) => (
  <div style={baseNodeStyle}>
    <Handle type="target" position={Position.Top} />
    <Header title={data.title} color="#9b59b6" />
    <div style={{ padding: '12px', border: '1px solid #9b59b6', borderTop: 'none', borderBottomLeftRadius: '12px', borderBottomRightRadius: '12px', background: 'var(--zyrabit-bg)' }}>
      <select style={{ width: '100%', padding: '4px', borderRadius: '4px', border: '1px solid var(--zyrabit-border)', fontSize: '12px', background: 'var(--zyrabit-surface)' }}>
        {data.options.map(opt => <option key={opt}>{opt}</option>)}
      </select>
    </div>
    <Handle type="source" position={Position.Bottom} />
  </div>
);

const HardwareNode = ({ data }) => (
  <div style={baseNodeStyle}>
    <Handle type="target" position={Position.Top} />
    <Header title="Hardware Layer" color="#e67e22" />
    <Content items={['Metal (Apple Silicon)', 'CUDA (NVIDIA)', 'CPU / AVX2', 'Tenstorrent P150A']} borderColor="#e67e22" />
  </div>
);

const nodeTypes = {
  primary: PrimaryAdapterNode,
  security: SecurityNode,
  domain: DomainNode,
  port: PortNode,
  adapter: AdapterNode,
  hardware: HardwareNode,
};

const initialNodes = [
  { id: '1', type: 'primary', position: { x: 300, y: 50 }, data: {} },
  { id: '2', type: 'security', position: { x: 300, y: 200 }, data: {} },
  { id: '3', type: 'domain', position: { x: 300, y: 350 }, data: {} },
  { id: '4', type: 'port', position: { x: 300, y: 500 }, data: {} },
  { id: '5a', type: 'adapter', position: { x: 150, y: 680 }, data: { title: 'Inference Adapters', options: ['Ollama (Default)', 'MLX', 'OpenAI-compatible'] } },
  { id: '5b', type: 'adapter', position: { x: 450, y: 680 }, data: { title: 'Retrieval Adapters', options: ['ChromaDB (Default)', 'PostgreSQL pgvector'] } },
  { id: '6', type: 'hardware', position: { x: 300, y: 850 }, data: {} },
];

const initialEdges = [
  { id: 'e1-2', source: '1', target: '2', animated: true },
  { id: 'e2-3', source: '2', target: '3', animated: true },
  { id: 'e3-4', source: '3', target: '4', animated: true },
  { id: 'e4-5a', source: '4', target: '5a', animated: true },
  { id: 'e4-5b', source: '4', target: '5b', animated: true },
  { id: 'e5a-6', source: '5a', target: '6', animated: true },
  { id: 'e5b-6', source: '5b', target: '6', animated: true },
];

function Flow() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  return (
    <div className="diagram-container" style={{ height: '700px', width: '100%' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.1 }}
      >
        <Background color="var(--zyrabit-muted)" gap={16} />
        <Controls />
        <MiniMap nodeStrokeColor={(n) => {
          if (n.type === 'primary') return '#4ecdc4';
          if (n.type === 'security') return '#f39c12';
          if (n.type === 'domain') return '#3f5a6d';
          return '#eee';
        }} nodeColor={(n) => 'var(--zyrabit-surface)'} />
      </ReactFlow>
    </div>
  );
}

export default function ArchitectureDiagram() {
  return (
    <BrowserOnly fallback={<div>Loading diagram...</div>}>
      {() => <Flow />}
    </BrowserOnly>
  );
}
