import React, { useState } from 'react';

export default function SwapGuide() {
  const [activeTab, setActiveTab] = useState('Database');

  const tabs = ['Database', 'Model', 'Hardware'];

  return (
    <div className="swap-guide glass-card" style={{ marginTop: '2rem' }}>
      <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem', borderBottom: '1px solid var(--zyrabit-border)', paddingBottom: '1rem' }}>
        {tabs.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '0.5rem 1.5rem',
              borderRadius: '8px',
              border: 'none',
              background: activeTab === tab ? 'var(--zyrabit-primary)' : 'transparent',
              color: activeTab === tab ? 'white' : 'var(--zyrabit-text)',
              cursor: 'pointer',
              fontWeight: activeTab === tab ? '700' : '500',
              transition: 'all 0.2s ease',
            }}
          >
            {tab}
          </button>
        ))}
      </div>

      <div className="tab-content" style={{ minHeight: '300px' }}>
        {activeTab === 'Database' && (
          <div className="animate-fade-in-up">
            <h3>Database Swap Guide</h3>
            <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
              <span className="badge badge--adapter">Default: ChromaDB</span>
              <span className="badge badge--new">Alternative: PostgreSQL + pgvector</span>
            </div>
            <p>Zyrabit uses ChromaDB as the default vector store for RAG. You can easily swap it for PostgreSQL + pgvector or any other database by implementing the <code>VectorStorePort</code>.</p>
            
            <h4>Step-by-Step Instructions</h4>
            <ol>
              <li>Create a new adapter class in <code>app/infrastructure/vectorstore/pgvector_adapter.py</code> that implements <code>VectorStorePort</code>.</li>
              <li>Register the new adapter in <code>app/wiring.py</code> (or wherever DI is configured).</li>
              <li>Update your <code>.env</code> file with the new credentials.</li>
            </ol>
            
            <h4>Code Snippet</h4>
            <pre><code>{`from app.ports.vector_store_port import VectorStorePort

class PgVectorAdapter(VectorStorePort):
    def similarity_search(self, query: str):
        # Implement pgvector search
        pass
        
    def add_texts(self, texts: list):
        # Implement insert
        pass`}</code></pre>
          </div>
        )}

        {activeTab === 'Model' && (
          <div className="animate-fade-in-up">
            <h3>Model Provider Swap Guide</h3>
            <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
              <span className="badge badge--adapter">Default: Ollama (Qwen 2.5)</span>
              <span className="badge badge--new">Alternatives: MLX, OpenAI, vLLM</span>
            </div>
            <p>Zyrabit's Hexagonal Architecture makes swapping LLM providers a breeze. The system interacts only with the <code>InferencePort</code>.</p>
            
            <h4>Step-by-Step Instructions</h4>
            <ol>
              <li>Create an adapter implementing <code>InferencePort</code> in <code>app/infrastructure/inference/</code>.</li>
              <li>Register it in <code>app/inference_factory.py</code>.</li>
              <li>Set <code>INFERENCE_PROVIDER</code> in your <code>.env</code> file.</li>
            </ol>
            
            <h4>Code Snippet</h4>
            <pre><code>{`from app.ports.inference_port import InferencePort

class VLLMAdapter(InferencePort):
    def generate(self, request):
        # Call vLLM API
        pass`}</code></pre>
            
            <h4>.env Configuration</h4>
            <pre><code>{`INFERENCE_PROVIDER=vllm
VLLM_ENDPOINT=http://localhost:8000/v1`}</code></pre>
          </div>
        )}

        {activeTab === 'Hardware' && (
          <div className="animate-fade-in-up">
            <h3>Hardware Target Swap Guide</h3>
            <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
              <span className="badge badge--adapter">Options: Apple Silicon, NVIDIA GPU, CPU, Tenstorrent</span>
            </div>
            <p>The <code>zyra.sh</code> launch script automatically detects your hardware and configures the correct optimizations.</p>
            
            <h4>Available Targets</h4>
            <ul>
              <li><strong>Apple Silicon:</strong> Uses MLX and Metal backend automatically.</li>
              <li><strong>NVIDIA GPU:</strong> Uses CUDA optimizations.</li>
              <li><strong>CPU:</strong> Falls back to AVX2 instructions.</li>
              <li><strong>Tenstorrent P150A:</strong> Experimental support via TT-Buda.</li>
            </ul>
            
            <h4>Relevant .env Variables</h4>
            <p>You can force a specific hardware target by overriding the auto-detection:</p>
            <pre><code>{`FORCE_DEVICE=cuda
TENSOR_PARALLEL_SIZE=2`}</code></pre>
          </div>
        )}
      </div>
    </div>
  );
}
