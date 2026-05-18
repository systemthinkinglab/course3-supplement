# Course 3 Supplement — Real-Time & Communication Systems

**Systems Thinking in the AI Era III**

This repository contains the discovery labs and challenge templates for [Course 3: Real-Time & Communication Systems](https://systemthinkinglab.ai/course-3).

## What's in here

```
course3-supplement/
├── building_blocks/        Shared building block reference implementations
│   ├── building_blocks.py  Service, Worker, FileStore, KeyValueStore, Queue,
│   │                       RelationalDB, VectorDB (the 7 universal building blocks)
│   └── external_entities.py  User, External Service, Time
│
├── labs/course3/           Hands-on discovery labs
│   ├── lab1_service_queue_messaging.py            Service + Queue — Real-Time Messaging
│   └── lab2_service_file_store_vector_db.py       Service + File Store + Vector DB —
│                                                  AI-Enhanced Communication
│
└── challenges/course3/     Technical Design Document templates (Phase 5)
```

## Quick start

You need Python 3.8 or higher. No third-party packages are required: the labs use only the standard library.

```bash
git clone https://github.com/systemthinkinglab/course3-supplement.git
cd course3-supplement
python3 labs/course3/lab1_service_queue_messaging.py
```

## Running the labs

Each lab is interactive and self-contained. You'll be guided through three progressive experiments with 3 multiple-choice questions and educational feedback after each one.

### Lab 1 — Service + Queue (Real-Time Messaging Discovery)

```bash
python3 labs/course3/lab1_service_queue_messaging.py
```

Three experiments build deep intuition for real-time message routing:

1. **Direct vs Queue-routed delivery** — feel the latency difference between point-to-point synchronous delivery and Queue-mediated asynchronous delivery. What happens when the recipient is briefly offline?
2. **Fanout to many subscribers** — measure cost growth for direct delivery (linear with subscriber count) vs Queue-mediated fanout (constant for the sender).
3. **Backpressure** — when consumers slow down, the Queue depth grows. Walk through bounded queues, ack patterns, dead-letter handling, and the lossy vs reliable trade-off.

```bash
# Run a single experiment
python3 labs/course3/lab1_service_queue_messaging.py 2

# Skip the typewriter effect (faster runs)
python3 labs/course3/lab1_service_queue_messaging.py --skip-typewriter

# Non-interactive mode (skips MC questions, runs the experiments end-to-end)
python3 labs/course3/lab1_service_queue_messaging.py --no-interactive
```

### Lab 2 — Service + File Store + Vector Database (AI-Enhanced Communication)

```bash
python3 labs/course3/lab2_service_file_store_vector_db.py
```

Three experiments build deep intuition for semantic understanding in communication systems:

1. **Keyword vs semantic search** — search chat history with keyword matching, then with vector similarity. Watch semantic search find messages keyword search can't.
2. **Embedding generation pipeline** — compare inline embedding (Service blocks on embed) vs Queue + Worker pipelined indexing (Service returns immediately, Worker indexes asynchronously). Measure user-facing latency.
3. **Real-time AI assist patterns** — three approaches to integrating an LLM External Service: inline blocking, streaming, and precompute-and-retrieve via Vector Database. Trade off latency vs cost vs freshness.

```bash
# Run a single experiment
python3 labs/course3/lab2_service_file_store_vector_db.py 3

# Skip the typewriter effect
python3 labs/course3/lab2_service_file_store_vector_db.py --skip-typewriter
```

## Challenge templates

Phase 5 of the course will publish three Technical Design Document templates here for the Course 3 Capstone Challenge: designing **TeamFlow**, a team collaboration platform.

- **Part 1: MVP Foundation** — real-time messaging with delivery confirmation, presence, and notifications
- **Part 2: Collaboration Expansion** — files, collaborative documents, search, retention
- **Part 3: AI + Multimedia** — semantic search, AI assistant in channels, video conferencing with recording

When the templates land, fill in each section using **building block names** (Service, Queue, Worker, Key-Value Store, File Store, Relational Database, Vector Database, External Service) and submit through the challenge form on the course site.

## Building block language

These labs and challenges teach you to think in **building blocks** rather than specific technologies. Use names like `Queue` instead of `RabbitMQ`, `Vector Database` instead of `Pinecone`, `External Service` instead of `OpenAI API`. The pattern is what matters; technology is implementation.

## Course site

Full course at [systemthinkinglab.ai/course-3](https://systemthinkinglab.ai/course-3).

## License

See [LICENSE](LICENSE).
