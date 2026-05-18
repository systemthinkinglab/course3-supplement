# Challenge 3 Part 3: Technical Design Document - AI and Multimedia

**Student Name**: [Your Name]
**Submission Date**: [Date]
**Challenge**: TeamFlow Team Collaboration Platform - Part 3 AI and Multimedia

---

## Context - what users are asking for

Your Part 2 platform serves hundreds of thousands of teams. File sharing, collaborative documents, search, and retention are all in production. The next wave of requests is reshaping what a collaboration platform is:

> *"I need to find the message where we agreed on the launch date, but I do not remember the exact words."*
> *"Can you summarize what happened in this channel while I was on vacation?"*
> *"We do video calls in other tools and copy the notes back here - can we just stay in TeamFlow?"*

This document is the **final evolution** - layering AI capabilities and live video on top of your Part 2 architecture. The patterns from Parts 1 and 2 stay intact. AI is added, not bolted on.

## IMPORTANT: Building Block Classification Matters Here

Cloud LLMs (the ones that summarize, answer channel questions, extract action items) are **External Services**, not File Stores and not Services you own. A locally-run model is Service + File Store (for weights), but the typical case is a cloud API call through External Service. The grader will check this classification - it is part of the grade.

Vector embeddings live in a **Vector Database**, not in a Key-Value Store or a Relational Database. The Vector Database is the one new building block this challenge requires. By the end of Part 3, all seven building blocks and all three external entities should appear in the cumulative design.

The real-time media gateway for video calls is also an **External Service**. WebRTC is allowed as the name of the open protocol the gateway speaks - it is not a vendor name. WebRTC is not a building block. Do not name a Service "WebRTC", a Queue "WebRTC", or storage "WebRTC".

---

## Part 1 + Part 2 Architecture Recap

[Briefly summarize the architecture after Part 2 (2-3 sentences). Messaging core (Service + Queue fanout), presence in Key-Value Store, conversation-list cache, notification path with External Service push gateway, File Store for attachments, Document Service + Queue for collaborative editing, search indexing pipeline, Time-driven retention. This is the foundation that survives.]

---

## Requirement 10: Semantic Search Across Messages and Documents

*Users describe what they remember, not what was written. "The post about hiring the new designer" should find the message that announced the hire, even if it never said "designer". Documents are searchable the same way.*

### User Flow Design

```
Example formats:
Embedding pipeline: Message Service → Embedding Queue → Embedding Worker → External Service (embedding model) → Vector Database
Document embed: Document Service (on save) → Embedding Queue → Embedding Worker → External Service → Vector Database
Semantic query: User → Semantic Search Service → External Service (embedding model) → Vector Database → Relational Database (rehydrate matches) → User
Hybrid query: User → Semantic Search Service → keyword index (from Part 2) + Vector Database → merge results
```

**Your semantic search flows:**
[Write 3-5 specific flows showing the offline embedding pipeline for new messages and documents, the query path, and how semantic results combine with the keyword search from Part 2]

### Building Blocks Added

- **[Vector Database]**: [Stores embeddings for every message and document. Why a Vector Database and not the Relational Database?]
- **[Embedding Queue + Embedding Worker]**: [Why offline? Why not embed at query time, or at write time inside the Message Service?]
- **[External Service for embedding model]**: [Named explicitly. Why External Service rather than a Service you own?]
- **[Semantic Search Service]**: [The query entry point. Why a dedicated Service rather than overloading the Search Service from Part 2?]

### Architecture Decisions & Trade-offs

- **[Decision 1]**: [Why a managed embedding model behind an External Service rather than running your own?]
- **[Decision 2]**: [Hybrid search (keyword + vector) or pure semantic? Why?]
- **[Decision 3]**: [How does the Vector Database stay in sync with deletes from the Part 2 retention pipeline?]

---

## Requirement 11: AI Assistant in Every Channel

*Inside any channel, users can ask the assistant questions: "summarize today", "what action items came out of this thread", "what did we decide about the Q3 roadmap". The assistant grounds its answers in the actual channel content, not in generic web knowledge.*

### User Flow Design

```
Example formats:
Channel summary: User → Assistant Service → External Service (embedding) → Vector Database → context assembly → External Service (LLM) → User
Action items: User → Assistant Service → Relational Database (recent messages) → External Service (LLM) → User
Channel Q&A: User → Assistant Service → External Service (embedding) → Vector Database (top-k matches) → context assembly → External Service (LLM) → User
Response cache: Assistant Service → Key-Value Store (cached summary keyed by channel + time window)
```

**Your assistant flows:**
[Write 3-5 specific flows showing the retrieval-grounded response pattern. The shape required is: query → embedding → Vector Database → context → External Service (LLM) → response.]

### Building Blocks Added

- **[Assistant Service]**: [Owns the assistant endpoint inside each channel. Coordinates retrieval and the LLM call.]
- **[External Service - LLM]**: [The cloud language model. Named as an External Service entity.]
- **[External Service - embedding model]**: [Already added in R10. Reused here for query embedding.]
- **[Vector Database]**: [Already added in R10. Reused here for retrieval.]
- **[Optional Key-Value Store for response cache]**: [Why cache assistant responses at all? When is the cache safe to return?]

### Architecture Decisions & Trade-offs

- **[Decision 1]**: [Why retrieval-grounded rather than feeding the entire channel into the LLM context window?]
- **[Decision 2]**: [How does the system handle the LLM being unavailable or rate-limited? Does the channel degrade gracefully?]
- **[Decision 3]**: [Where do you check permissions? An assistant must not surface content from messages the asking user cannot see.]

---

## Requirement 12: Video Calls with Recording and Transcription

*Inside any channel, users start a video call. Calls can be recorded. Recordings are transcribed automatically so the spoken content is searchable like text messages. Transcripts are available to the assistant for channel summaries.*

### User Flow Design

```
Example formats:
Start call: User → Call Service → External Service (media gateway, speaks WebRTC) → other Users
Recording finishes: Call Service → File Store (raw recording) → Transcription Queue
Transcription: Transcription Queue → Transcription Worker → External Service (transcription model) → Relational Database (transcript) + File Store
Index transcript: Transcription Worker → Indexing Queue (from Part 2) + Embedding Queue (from Part 3)
Search transcript: User → Search Service or Semantic Search Service → matched transcript snippet → User
```

**Your video and transcription flows:**
[Write 3-5 specific flows showing how a call is set up, how the recording lands in File Store, how the transcription pipeline runs, and how the transcript becomes searchable]

### Building Blocks Added

- **[Call Service]**: [Holds call signaling state - who is in the call, who started it, who is the host. Does NOT carry the media.]
- **[External Service - media gateway]**: [Carries the actual audio and video. Speaks WebRTC as a protocol. This is the green cloud, not a Service you own.]
- **[File Store for recordings]**: [Raw recording bytes land here. Why File Store and not the Relational Database?]
- **[Transcription Queue + Transcription Worker]**: [Async transcription. Why async rather than blocking the end-of-call?]
- **[External Service - transcription model]**: [The cloud transcription provider. Named as an External Service entity.]

### Architecture Decisions & Trade-offs

- **[Decision 1]**: [Why an External Service for the media gateway rather than building real-time media inside the seven building blocks?]
- **[Decision 2]**: [Why does the recording have to land in File Store before transcription starts, rather than streaming the audio to the transcription provider live?]
- **[Decision 3]**: [Transcripts feed the existing search index AND the Vector Database. Why both?]

---

## The Three Classic Trade-offs

A strong Part 3 submission names these explicitly.

### Freshness vs Cost

[Each LLM call costs money and adds latency. A cached channel summary stays fresh enough for many minutes; a question about an active thread should not be cached at all. Where do you cache, what is the TTL, and what triggers an invalidation?]

### Retrieval Relevance vs Latency

[Deeper retrieval (more vectors searched, larger context windows assembled) produces better answers but adds latency. What is your top-k? Do you do reranking? What is the user's acceptable wait time before they think the assistant is broken?]

### Privacy and Permissions

[The assistant pulls context from messages the user can see. The retrieval step has to filter by membership and visibility. Where in the flow does that filter sit - at retrieval time, at context-assembly time, or at the LLM prompt level?]

---

## Graceful Degradation: Designing for AI Failure

AI and media services fail. The LLM provider has an outage. The embedding service rate-limits you. The media gateway is unreachable. TeamFlow cannot go down when AI does.

For each AI and video capability, define the fallback:

| Capability | Primary path | Fallback when External Service is unavailable |
|---|---|---|
| Semantic search | [Vector Database + embedding External Service] | [Keyword search from Part 2] |
| Channel summary | [External Service LLM + retrieval] | [Disable summary with a "summaries unavailable" banner; messages still flow] |
| Channel Q&A | [Retrieval + External Service LLM] | [Disable assistant; suggest search instead] |
| New message embedding | [External Service embedding model] | [Embedding Queue absorbs the lag; messages still searchable by keyword in the meantime] |
| Video call media | [External Service media gateway] | [Show "calls temporarily unavailable"; messaging still works] |
| Transcription | [Transcription Queue + Worker + External Service] | [Recording still saved; transcript fills in when service returns] |

**Architectural principle**: [State explicitly - the platform should still work when every AI and video External Service is down for an hour. AI enhances the product. AI is not load-bearing for messaging.]

---

## Foundation Preserved

Walk through the Parts 1 and 2 paths and confirm they survive:

- **Messaging core**: [Message Service + fanout Queue still in place?]
- **Presence**: [Still in Key-Value Store?]
- **Notification path**: [Notification Queue + Worker + External Service push gateway still wired up?]
- **File Store and search indexing**: [Both still present and feeding Part 3 additions?]
- **Time entity**: [Still triggering retention sweeps?]

---

## Complete End-to-End Architecture

Provide a complete architecture diagram (or detailed text description) showing:

1. All Part 1 components (still present)
2. All Part 2 additions (still present)
3. All Part 3 additions (new)
4. The connections between them

By the end, all seven building blocks (Service, Worker, Queue, Key-Value Store, File Store, Relational Database, Vector Database) and all three external entities (User, External Service, Time) should be visible in the design.

[Include diagram or detailed text walkthrough]

---

## Trade-offs Explicitly Accepted

- **[Trade-off 1]**: [What you gave up to add AI and video]
- **[Trade-off 2]**: [What you gave up to add AI and video]
- **[Trade-off 3]**: [What you gave up to add AI and video]

---

## What This Architecture Intentionally Does NOT Address

[Be honest about what is out of scope. Examples: real-time translation between languages, AI-generated documents inside channels, multi-tenant private model fine-tuning, on-device offline assistant. The grader rewards designs that know their boundaries.]

---

## Self-Graded Rubric (A / A- / B+)

**My grade**: [A / A- / B+]

**Why I assigned this grade**: [Apply the rubric from Lesson 2. Specifically check: did you classify the cloud LLM as External Service (not File Store, not Service alone)? Did you classify the media gateway as External Service? Did you keep WebRTC as a protocol name and not a building block? Did you reuse the Vector Database for both R10 and R11? Did you provide explicit fallbacks for every AI and video capability?]

---

## Submission

Save this document as markdown and paste the full content into the **Challenge Part 3** submission form at [systemthinkinglab.ai](https://systemthinkinglab.ai/protected/course3/challenge3.html). Parts 1 and 2 must be graded before Part 3 can be submitted. This is the capstone of Course 3 - make it count.
