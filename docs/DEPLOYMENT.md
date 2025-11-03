# Standalone Node Architecture

## Two Deployment Options

You can deploy FALM in two ways:

### Option 1: Federated Mesh (Current)
- All nodes run in one process
- Shared orchestrator coordinates
- Easier for single-machine deployment
- **Good for**: Development, small deployments

### Option 2: Standalone Nodes (Microservices)
- Each node runs independently
- Can be on different servers/containers
- Nodes communicate via HTTP/SIMP
- **Good for**: Production, scaling, distributed systems

## Standalone Node Structure

Each node would be a complete microservice:

```
UK_IUK_Node/
├─ node_api.py          ← FastAPI server for this node only
├─ node_config.py       ← IUK-specific configuration
├─ scraper.py           ← IUK-specific scraping logic
├─ scheduler.py         ← IUK-specific scheduling
├─ requirements.txt     ← Dependencies
├─ Dockerfile           ← Container definition
├─ .env                 ← IUK node config
└─ data/
    ├─ chroma_db/       ← IUK vector database
    ├─ cache/           ← IUK cache
    └─ logs/            ← IUK logs
```

## What Needs to Be Shared vs Isolated?

### Must Be Shared (Minimal):
1. **SIMP Protocol Spec** - So nodes can communicate
2. **Data Models** - Grant structure (can be versioned)
3. **Orchestrator** (Optional - can be separate service)

### Can Be Fully Isolated Per Node:
1. ✅ **Database** - Each node has own ChromaDB
2. ✅ **Scraping Engine** - Custom per funding body
3. ✅ **Scheduler** - Independent scheduling
4. ✅ **API Server** - Each node can have own API
5. ✅ **Dependencies** - Each node picks its own versions
6. ✅ **Configuration** - Completely independent

## Deployment Patterns

### Pattern A: All-in-One (Current)
```
Single Server
└─ FALM Federated API
    ├─ IUK Node
    ├─ NIHR Node
    └─ Wellcome Node
```

**Pros**: Simple, fast communication
**Cons**: Single point of failure, hard to scale

### Pattern B: Microservices
```
Load Balancer
├─ Orchestrator Service (port 8000)
├─ IUK Node Service (port 8001)
├─ NIHR Node Service (port 8002)
└─ Wellcome Node Service (port 8003)
```

**Pros**: Independent scaling, fault isolation
**Cons**: Network latency, more complex

### Pattern C: Docker Compose
```yaml
services:
  orchestrator:
    build: ./orchestrator
    ports: ["8000:8000"]

  iuk-node:
    build: ./nodes/UK_IUK
    volumes: ["./data/nodes/UK_IUK:/app/data"]

  nihr-node:
    build: ./nodes/UK_NIHR
    volumes: ["./data/nodes/UK_NIHR:/app/data"]
```

**Pros**: Easy deployment, portable
**Cons**: Docker overhead

### Pattern D: Kubernetes
```
Kubernetes Cluster
├─ Orchestrator Pod (replicas: 2)
├─ IUK Node Pod (replicas: 3)
├─ NIHR Node Pod (replicas: 2)
└─ Wellcome Node Pod (replicas: 1)
```

**Pros**: Auto-scaling, high availability
**Cons**: Complex setup

## Recommended Approach

### For You Right Now:
**Use Option 1 (Federated Mesh)** - All nodes in one process

Why?
- ✅ Easier to develop and test
- ✅ Faster (no network calls between nodes)
- ✅ Simpler deployment
- ✅ Lower resource usage

Each node is still **logically isolated**:
- Own database directory
- Own configuration
- Own specialized logic
- Own scheduler

### Later (When Scaling):
Move to **Option 2 (Microservices)**

When?
- Need to scale specific nodes independently
- Want fault isolation (one node crash doesn't affect others)
- Deploying across multiple servers
- Different nodes need different resources

## Making Current Nodes Truly Standalone

If you want to run each node independently NOW, I can create:

1. **Standalone Node Template**
```python
# UK_IUK/node_server.py
from fastapi import FastAPI

app = FastAPI(title="IUK Node")

# This node runs completely independently
# Has its own database, scheduler, everything
# Communicates with orchestrator via HTTP

@app.get("/")
async def root():
    return {"node": "IUK", "status": "active"}

@app.post("/search")
async def search(query: str):
    # Search only IUK data
    pass

@app.post("/ingest")
async def ingest(url: str):
    # Scrape and ingest IUK grants
    pass
```

2. **Docker Containers**
```dockerfile
# UK_IUK/Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "node_server.py"]
```

3. **Docker Compose**
```yaml
# docker-compose.yml
version: '3.8'

services:
  iuk-node:
    build: ./nodes/UK_IUK
    ports: ["8001:8001"]
    volumes:
      - ./data/nodes/UK_IUK:/app/data
    environment:
      - NODE_CODE=IUK
      - SILO=UK

  nihr-node:
    build: ./nodes/UK_NIHR
    ports: ["8002:8002"]
    volumes:
      - ./data/nodes/UK_NIHR:/app/data
```

## Current vs Standalone Comparison

### Current (Federated Mesh):
```
One Python Process
  ├─ mesh.add_node(IUKNode())      ← In-process
  ├─ mesh.add_node(NIHRNode())     ← In-process
  └─ mesh.add_node(WellcomeNode()) ← In-process

Communication: Direct function calls
Storage: data/nodes/{node}/
```

### Standalone (Microservices):
```
Orchestrator Process (port 8000)
  ↓ HTTP/SIMP
IUK Node Process (port 8001)
  ↓ HTTP/SIMP
NIHR Node Process (port 8002)
  ↓ HTTP/SIMP
Wellcome Node Process (port 8003)

Communication: HTTP requests
Storage: data/nodes/{node}/ (same)
```

## What I Recommend

**Keep the current federated mesh approach for now** because:

1. **Nodes are already isolated** where it matters:
   - Separate databases
   - Separate config
   - Separate logic
   - Can be extracted later

2. **You get the benefits**:
   - Modular (easy to add funding bodies)
   - Specialized (each node is an expert)
   - Independent scheduling
   - SIMP communication

3. **Easy to convert later**:
   - Each node is already a class
   - Just wrap in FastAPI server
   - Deploy as containers

Want me to create the **fully standalone microservice version** so you can deploy each node independently? Or are you happy with the current federated approach where they're logically isolated but run in one process?