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
 *   Primary[Primary Adapters] --> Security[Security Pipeline]
 *   Security --> Core[Core Domain]
 *   Core --> InfPort[InferencePort] --> InfAdap[Inference Adapters]
 *   Core --> RetPort[VectorStorePort] --> RetAdap[Retrieval Adapters]
 *   Core --> StatePort[StatePort] --> StateAdap[State Adapter]
 *   Core --> AutPort[AutomationPort] --> AutAdap[Automation Adapters]
 *   InfAdap --> Hardware[Hardware Layer]
 *   RetAdap --> Hardware
 */

const baseNodeStyle = {
  background: 'var(--zyrabit-surface-glass)',
  backdropFilter: 'blur(12px)',
  borderRadius: '12px',
  overflow: 'hidden',
  width: '180px',
  boxShadow: '0 8px 32px rgba(0,0,0,0.05)',
  border: '1px solid var(--zyrabit-border)',
};

const Header = ({ title, color }) => (
  <div style={{ background: color, padding: '6px 10px', color: '#fff', fontWeight: 'bold', fontSize: '12px', textAlign: 'center' }}>
    {title}
  </div>
);

const Content = ({ items, borderColor }) => (
  <div style={{ padding: '8px 10px', border: `1px solid ${borderColor}`, borderTop: 'none', borderBottomLeftRadius: '12px', borderBottomRightRadius: '12px', background: 'var(--zyrabit-bg)', color: 'var(--zyrabit-text)' }}>
    <ul style={{ margin: 0, paddingLeft: '15px', fontSize: '10.5px', lineHeight: '1.4', listStyleType: 'square' }}>
      {items.map((item, i) => <li key={i}>{item}</li>)}
    </ul>
  </div>
);

// ── CUSTOM NODES ──

const PrimaryAdapterNode = () => (
  <div style={baseNodeStyle}>
    <Header title="Primary Adapters" color="#4ecdc4" />
    <Content items={['REST API (FastAPI)', 'Socket.IO', 'MCP RPC', 'AG-UI']} borderColor="#4ecdc4" />
    <Handle type="source" position={Position.Bottom} id="out" />
  </div>
);

const SecurityNode = () => (
  <div style={baseNodeStyle}>
    <Handle type="target" position={Position.Top} id="in" />
    <Header title="Security Pipeline" color="#f39c12" />
    <Content items={['PII Shield', 'Anonymize', 'De-anonymize']} borderColor="#f39c12" />
    <Handle type="source" position={Position.Bottom} id="out" />
  </div>
);

const DomainNode = () => (
  <div style={{ ...baseNodeStyle, width: '200px', border: '2px solid #3f5a6d' }}>
    <Handle type="target" position={Position.Top} id="in" />
    <Header title="Core Domain" color="#3f5a6d" />
    <Content items={['ChatUseCase', 'IngestUseCase', 'Gatekeeper', 'HybridRetrieverService']} borderColor="#3f5a6d" />
    {/* Radial Handles for Hexagonal Ports */}
    <Handle type="source" position={Position.Left} id="left-out" />
    <Handle type="source" position={Position.Right} id="right-out" />
    <Handle type="source" position={Position.Bottom} id="bottom-out" />
  </div>
);

const PortNode = ({ data }) => (
  <div style={{ 
    ...baseNodeStyle, 
    width: '130px', 
    border: '1.5px dashed #2ba89e', 
    background: 'rgba(78, 205, 196, 0.05)',
    boxShadow: 'none' 
  }}>
    <Handle type="target" position={data.targetPos || Position.Top} id="in" />
    <div style={{ padding: '6px', textAlign: 'center', fontSize: '11px', fontWeight: 'bold', color: '#2ba89e' }}>
      {data.title}
    </div>
    <Handle type="source" position={data.sourcePos || Position.Bottom} id="out" />
  </div>
);

const AdapterNode = ({ data }) => (
  <div style={{ ...baseNodeStyle, width: '170px' }}>
    <Handle type="target" position={data.targetPos || Position.Top} id="in" />
    <Header title={data.title} color="#9b59b6" />
    <div style={{ padding: '8px', border: '1px solid #9b59b6', borderTop: 'none', borderBottomLeftRadius: '12px', borderBottomRightRadius: '12px', background: 'var(--zyrabit-bg)' }}>
      <select style={{ width: '100%', padding: '3px', borderRadius: '4px', border: '1px solid var(--zyrabit-border)', fontSize: '11px', background: 'var(--zyrabit-surface)', color: 'var(--zyrabit-text)' }}>
        {data.options.map(opt => <option key={opt}>{opt}</option>)}
      </select>
    </div>
    <Handle type="source" position={data.sourcePos || Position.Bottom} id="out" />
  </div>
);

const HardwareNode = () => (
  <div style={baseNodeStyle}>
    <Handle type="target" position={Position.Top} id="in" />
    <Header title="Hardware Layer" color="#e67e22" />
    <Content items={['Metal (Apple Silicon)', 'CUDA (NVIDIA GPU)', 'CPU / AVX2', 'Tenstorrent Wormhole']} borderColor="#e67e22" />
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

// Radial Hexagonal coordinates centering around Core Domain at (350, 350)
const initialNodes = [
  // ── Driving Side (Top center)
  { id: 'primary', type: 'primary', position: { x: 360, y: 20 }, data: {} },
  { id: 'security', type: 'security', position: { x: 360, y: 150 }, data: {} },
  
  // ── Core Domain (Center)
  { id: 'domain', type: 'domain', position: { x: 350, y: 320 }, data: {} },
  
  // ── Inference Sector (Right side)
  { id: 'port-inf', type: 'port', position: { x: 600, y: 270 }, data: { title: 'InferencePort', targetPos: Position.Left, sourcePos: Position.Right } },
  { id: 'adapter-inf', type: 'adapter', position: { x: 780, y: 255 }, data: { title: 'Inference Adapters', options: ['Ollama (Default)', 'MLX (Apple Silicon)', 'OpenAI-compatible'], targetPos: Position.Left, sourcePos: Position.Bottom } },
  
  // ── Retrieval Sector (Bottom Right)
  { id: 'port-ret', type: 'port', position: { x: 560, y: 470 }, data: { title: 'VectorStorePort', targetPos: Position.Top, sourcePos: Position.Bottom } },
  { id: 'adapter-ret', type: 'adapter', position: { x: 540, y: 560 }, data: { title: 'Retrieval Adapters', options: ['ChromaDB (Default)', 'PostgreSQL pgvector'], targetPos: Position.Top, sourcePos: Position.Bottom } },

  // ── State Sector (Bottom Left)
  { id: 'port-state', type: 'port', position: { x: 200, y: 470 }, data: { title: 'StatePort', targetPos: Position.Top, sourcePos: Position.Bottom } },
  { id: 'adapter-state', type: 'adapter', position: { x: 180, y: 560 }, data: { title: 'State Adapters', options: ['SQLite WAL (Default)'], targetPos: Position.Top } },

  // ── Automation & MCP Sector (Left side)
  { id: 'port-aut', type: 'port', position: { x: 170, y: 270 }, data: { title: 'AutomationPort', targetPos: Position.Right, sourcePos: Position.Left } },
  { id: 'adapter-aut', type: 'adapter', position: { x: -40, y: 255 }, data: { title: 'Automation Adapters', options: ['n8n Webhook Adapter', 'MCP Client Bridge'], targetPos: Position.Right } },

  // ── Hardware layer (Unified bottom)
  { id: 'hardware', type: 'hardware', position: { x: 360, y: 730 }, data: {} },
];

const initialEdges = [
  // Primary flow to Core Domain
  { id: 'e-prim-sec', source: 'primary', sourceHandle: 'out', target: 'security', targetHandle: 'in', animated: true },
  { id: 'e-sec-dom', source: 'security', sourceHandle: 'out', target: 'domain', targetHandle: 'in', animated: true },

  // Inference connections (Right)
  { id: 'e-dom-portinf', source: 'domain', sourceHandle: 'right-out', target: 'port-inf', targetHandle: 'in', animated: true },
  { id: 'e-portinf-adapinf', source: 'port-inf', sourceHandle: 'out', target: 'adapter-inf', targetHandle: 'in', animated: true },

  // Retrieval connections (Bottom Right)
  { id: 'e-dom-portret', source: 'domain', sourceHandle: 'bottom-out', target: 'port-ret', targetHandle: 'in', animated: true },
  { id: 'e-portret-adapret', source: 'port-ret', sourceHandle: 'out', target: 'adapter-ret', targetHandle: 'in', animated: true },

  // State connections (Bottom Left)
  { id: 'e-dom-portstate', source: 'domain', sourceHandle: 'bottom-out', target: 'port-state', targetHandle: 'in', animated: true },
  { id: 'e-portstate-adapstate', source: 'port-state', sourceHandle: 'out', target: 'adapter-state', targetHandle: 'in', animated: true },

  // Automation connections (Left)
  { id: 'e-dom-portaut', source: 'domain', sourceHandle: 'left-out', target: 'port-aut', targetHandle: 'in', animated: true },
  { id: 'e-portaut-adapaut', source: 'port-aut', sourceHandle: 'out', target: 'adapter-aut', targetHandle: 'in', animated: true },

  // Hardware connections from main operational adapters
  { id: 'e-adapinf-hw', source: 'adapter-inf', sourceHandle: 'out', target: 'hardware', targetHandle: 'in', animated: true },
  { id: 'e-adapret-hw', source: 'adapter-ret', sourceHandle: 'out', target: 'hardware', targetHandle: 'in', animated: true },
];

function Flow() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  return (
    <div className="diagram-container" style={{ height: '720px', width: '100%' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.12 }}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="var(--zyrabit-muted)" gap={16} />
        <Controls />
        <MiniMap nodeStrokeColor={(n) => {
          if (n.type === 'primary') return '#4ecdc4';
          if (n.type === 'security') return '#f39c12';
          if (n.type === 'domain') return '#3f5a6d';
          return '#eee';
        }} nodeColor={() => 'var(--zyrabit-surface)'} />
      </ReactFlow>
    </div>
  );
}

export default function ArchitectureDiagram() {
  return (
    <BrowserOnly fallback={<div style={{ padding: '20px', textAlign: 'center', color: 'var(--zyrabit-muted)' }}>Loading architecture diagram...</div>}>
      {() => <Flow />}
    </BrowserOnly>
  );
}
