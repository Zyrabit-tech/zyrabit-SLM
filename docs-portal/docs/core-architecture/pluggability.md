---
sidebar_position: 2
title: 'Architecture & Component Swapping Manual'
description: 'Comprehensive technical guide for interchanging Frontends (Angular, Next.js), Backends (Node.js, Go), Databases (PostgreSQL + pgvector), and Integrations (Obsidian, n8n).'
---

# 🛠️ Comprehensive Architecture & Component Swapping Manual

Zyrabit SLM is built strictly on **Hexagonal Architecture (Ports & Adapters)**. The application core (`api-rag`) is completely decoupled from UI frameworks, persistence mechanisms, inference providers, and automation tools.

This manual explains step-by-step how to swap, extend, or connect any layer of the stack using production-grade configurations, terminal commands, and clear code examples.

---

## 🖼️ 1. Swapping the Frontend (BYOF: Bring Your Own Front)

The default UI (`zyrabit-web`) is a lightweight reference implementation in Vanilla JS. You can disconnect it and replace it with **Angular**, **Next.js / React**, or **Vue**.

```
┌─────────────────────────────────────────────────────────┐
│              FRONTEND ADAPTERS (Pick One)               │
│  ┌──────────────┐   ┌──────────────┐   ┌─────────────┐  │
│  │ Angular SPA  │   │ Next.js SSR  │   │  n8n UI     │  │
│  └──────┬───────┘   └──────┬───────┘   └──────┬──────┘  │
└─────────┼──────────────────┼──────────────────┼─────────┘
          │ (REST / Socket)  │ (HTTP / SSE)     │ (Webhook)
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────┐
│               ZYRABIT CORE API (:8082)                  │
└─────────────────────────────────────────────────────────┘
```

### Option A: Connecting an Angular Container

#### 1. Add Angular Docker Service (`docker-compose.local.yml`)

```yaml
  zyrabit-angular:
    build:
      context: ../my-angular-app
      dockerfile: Dockerfile
    container_name: zyrabit-angular
    ports:
      - "4200:80"
    environment:
      - ZYRABIT_API_URL=http://localhost:8082/v1
    networks:
      - backend-network
```

#### 2. Angular Socket.io & REST Integration Service (`zyrabit.service.ts`)

```typescript
import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { io, Socket } from 'socket.io-client';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class ZyrabitService {
  private apiUrl = 'http://localhost:8082/v1';
  private socket: Socket;

  constructor(private http: HttpClient) {
    // Socket.io connection for real-time RAG streaming
    this.socket = io('http://localhost:8082', {
      path: '/socket.io',
      transports: ['websocket']
    });
  }

  // REST Document Ingestion
  ingestDocument(file: File): Observable<any> {
    const formData = new FormData();
    formData.append('file', file);

    const headers = new HttpHeaders({
      'Authorization': 'Bearer zyrabit-local-token'
    });

    return this.http.post(`${this.apiUrl}/ingest`, formData, { headers });
  }

  // Socket.io Real-time Chat
  sendChatMessage(message: string): Observable<any> {
    return new Observable(observer => {
      this.socket.emit('chat_message', { text: message });
      this.socket.on('chat_response', (data) => {
        observer.next(data);
      });
    });
  }
}
```

---

### Option B: Connecting a Next.js / React Application

#### 1. Next.js API Route for Sovereign Proxy (`app/api/chat/route.ts`)

```typescript
import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  const body = await request.json();

  const response = await fetch('http://localhost:8082/v1/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${process.env.ZYRABIT_API_KEY_WEB || 'zyrabit-local-token'}`
    },
    body: JSON.stringify(body)
  });

  const data = await response.json();
  return NextResponse.json(data);
}
```

---

## 🗄️ 2. Swapping Vector Databases (ChromaDB → PostgreSQL + `pgvector`)

While ChromaDB is the default vector store, you can swap it for enterprise **PostgreSQL with the `pgvector` extension** without changing any domain logic.

```
┌──────────────────────────────────────────────────────────┐
│                   PERSISTENCE PORT                       │
│  ┌───────────────────────┐   ┌────────────────────────┐  │
│  │ ChromaAdapter         │   │ PostgresPgVectorAdapter│  │
│  │ (Default SQLite/File) │   │ (PostgreSQL 16 + HNSW) │  │
│  └───────────────────────┘   └────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

### 1. Add PostgreSQL + `pgvector` to `docker-compose.yml`

```yaml
  zyrabit-pgvector:
    image: pgvector/pgvector:pg16
    container_name: zyrabit-pgvector
    environment:
      POSTGRES_DB: zyrabit_sovereign
      POSTGRES_USER: zyrabit
      POSTGRES_PASSWORD: sovereign_secret_password
    ports:
      - "5432:5432"
    volumes:
      - pgvector-data:/var/lib/postgresql/data
    networks:
      - backend-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U zyrabit -d zyrabit_sovereign"]
      interval: 10s
      timeout: 5s
      retries: 5
```

### 2. Enable `pgvector` Extension & Table Schema (`init.sql`)

```sql
-- Enable vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create documents table with 1024-dimensional embeddings (mxbai-embed-large)
CREATE TABLE IF NOT EXISTS zyrabit_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    metadata JSONB,
    embedding vector(1024),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Build HNSW index for ultra-fast cosine similarity search
CREATE INDEX IF NOT EXISTS zyrabit_embeddings_hnsw_idx 
ON zyrabit_embeddings 
USING hnsw (embedding vector_cosine_ops);
```

### 3. Update `.env` for PostgreSQL

```env
# Vector Store Switching
VECTOR_STORE_PROVIDER=postgres
POSTGRES_HOST=zyrabit-pgvector
POSTGRES_PORT=5432
POSTGRES_DB=zyrabit_sovereign
POSTGRES_USER=zyrabit
POSTGRES_PASSWORD=sovereign_secret_password
```

---

## ⚡ 3. Swapping the Backend (FastAPI → Node.js / Go)

Because Zyrabit API exposes standard HTTP endpoints (`/v1/chat`, `/v1/ingest`, `/v1/health`) and Socket.io, you can rewrite or mirror the backend in **Node.js (TypeScript)** or **Go**.

### Option A: Node.js / Express Backend Adapter (`server.ts`)

```typescript
import express from 'express';
import { Server } from 'socket.io';
import http from 'http';
import axios from 'axios';

const app = express();
const server = http.createServer(app);
const io = new Server(server, { cors: { origin: '*' } });

app.use(express.json());

// Forward Inference to Local Ollama
app.post('/v1/chat', async (req, res) => {
  try {
    const { messages, model = 'qwen2.5:7b' } = req.body;
    const prompt = messages[messages.length - 1].content;

    const response = await axios.post('http://127.0.0.1:11434/api/generate', {
      model,
      prompt,
      stream: false
    });

    res.json({
      choices: [{ message: { role: 'assistant', content: response.data.response } }]
    });
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

server.listen(8082, () => {
  console.log('⚡ Node.js Zyrabit Core API listening on port 8082');
});
```

### Option B: Go High-Throughput Ingestion Backend (`main.go`)

```go
package main

import (
	"encoding/json"
	"fmt"
	"net/http"
)

type HealthResponse struct {
	Status  string `json:"status"`
	Engine  string `json:"engine"`
	Backend string `json:"backend"`
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	resp := HealthResponse{
		Status:  "OPERATIONAL",
		Engine:  "Go-Zyrabit-Native",
		Backend: "Sovereign Air-Gapped Core",
	}
	json.NewEncoder(w).Encode(resp)
}

func main() {
	http.HandleFunc("/v1/health", healthHandler)
	fmt.Println("🚀 Go Zyrabit Engine running on :8082...")
	http.ListenAndServe(":8082", nil)
}
```

---

## 📓 4. Integrating Obsidian Knowledge Base Container

You can mount your local **Obsidian Vault** into a dedicated container or directly into `zyrabit-api` to enable automated real-time background learning (`Obsidian AutoLearner`).

### 1. Add Obsidian Sync Service (`docker-compose.local.yml`)

```yaml
  zyrabit-obsidian:
    image: alpine:latest
    container_name: zyrabit-obsidian
    command: sh -c "while true; do sleep 3600; done"
    volumes:
      - ~/Documents/ObsidianVault:/vault:ro
      - ./document_source:/app/document_source
    networks:
      - backend-network
```

### 2. Trigger Automated Vault Ingestion

Run this command in terminal to sync all Markdown notes from your Obsidian Vault into Zyrabit's RAG Memory:

```bash
# Sync Obsidian .md notes into Zyrabit document source
rsync -av --include="*.md" --filter="+ */" --filter="- *" \
  ~/Documents/ObsidianVault/ zyrabit-slm/document_source/

# Trigger API Auto-Ingest
curl -X POST http://localhost:8082/v1/ingest \
  -H "Authorization: Bearer zyrabit-local-token" \
  -F "file=@zyrabit-slm/document_source/KnowledgeBase.md"
```

---

## 🔌 5. Network Ports, Sockets & CORS Reference

To connect external tools, desktop apps, or cross-domain frontends, ensure your firewall and CORS settings match this matrix:

| Component | Protocol | Container Port | Host Port | Purpose |
|---|---|---|---|---|
| **Web UI** | HTTP | `:80` | `:3000` | Browser Frontend |
| **Core API** | HTTP / WebSocket | `:8080` | `:8082` | REST (`/v1`) & Socket.io (`/socket.io`) |
| **ChromaDB** | HTTP | `:8000` | `:8000` | Vector persistence API |
| **MCP Server** | HTTP / JSON-RPC | `:8001` | `:8001` | Model Context Protocol bridge |
| **Ollama (Host)** | HTTP | `:11434` | `:11434` | Native Metal GPU Inference Engine |
| **n8n** | HTTP / Webhook | `:5678` | `:5678` | Workflow Automation (`--profile automation`) |
| **PostgreSQL** | TCP | `:5432` | `:5432` | Optional `pgvector` store |

### Configuring CORS in `.env` for Remote Frontends

```env
# Allow external domain/IP to connect via REST or WebSockets
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:4200,https://my-app.company.internal
```

---

## 📑 Quick Command Summary

```bash
# Start lightweight local stack (Web, API, ChromaDB)
./zyra-up.sh start

# Start with n8n automation suite
./zyra-up.sh start --profile automation

# Monitor live logs & health watchdog
./zyra-up.sh watch

# Verify network ports & container statuses
./zyra-up.sh verify
```
