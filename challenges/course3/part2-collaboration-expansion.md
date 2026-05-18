# Challenge 3 Part 2: Technical Design Document - Collaboration Expansion

**Student Name**: [Your Name]
**Submission Date**: [Date]
**Challenge**: TeamFlow Team Collaboration Platform - Part 2 Collaboration Expansion

---

## Context - what happened

Your Part 1 platform launched and grew into tens of thousands of teams. Customers stopped describing TeamFlow as a chat app and started calling it their collaboration platform. The new requests are not about more messaging - they are about everything that surrounds messaging.

Teams want to share files in conversations with inline previews. They want to edit documents together inside a channel without leaving for another tool. They want to find old messages by keyword, not just scroll. And legal wants retention policies that move old content out of the hot path.

This document is your **evolution** of the Part 1 design, not a redesign. Part 2 should clearly build on the architecture you submitted for Part 1, adding components and modifying connections to address four new requirements. The Part 1 messaging core stays intact.

## IMPORTANT: Technology-Agnostic Design Required

Use building block names, not technologies. See the Part 1 template for the full list. Full-text indexes, inverted indexes, snapshots, soft-delete, archive tiers, and CRDT or operational transformation as concepts are all **techniques and patterns** - they describe what happens inside building blocks, not new primitives.

---

## Part 1 Architecture Recap

[Briefly summarize your Part 1 architecture in 2-3 sentences. Name the major components: Message Service, fanout Queue, Relational Database for the message log, Key-Value Store for presence and conversation lists, notification Queue + Worker, External Service for push gateway. This sets the baseline for what you are evolving.]

---

## Requirement 6: File Sharing with Inline Previews

*Users drag files into a conversation. Images, PDFs, and short clips appear inline with a generated preview. Uploading must not block the user's send, and previews can appear a moment after the file lands.*

### User Flow Design

```
Example formats:
Upload: User → Upload Service → File Store
File metadata: Upload Service → Relational Database (uploader, conversation, MIME type, size, storage key)
Preview job: Upload Service → Queue (preview job)
Preview render: Queue → Preview Worker → File Store (thumbnail or preview asset)
```

**Your file-sharing flows:**
[Write 3-5 specific flows for the upload path, the metadata write, the async preview pipeline, and how the inline preview gets back to the conversation when it is ready]

### Building Blocks Added

- **[File Store]**: [Stores the uploaded bytes. Why a File Store rather than the Relational Database?]
- **[Upload Service]**: [Owns the upload endpoint. Coordinates the File Store write and the metadata row.]
- **[Preview Queue + Preview Worker]**: [Async preview generation. Why async rather than blocking the upload?]

### Architecture Decisions & Trade-offs

- **[Decision 1]**: [Why File Store for bytes plus Relational Database for metadata, instead of BLOBs in the Relational Database?]
- **[Decision 2]**: [How does the conversation get notified that the preview is ready? Does the Message Service fanout an "attachment updated" event?]
- **[Decision 3]**: [What happens when preview generation fails? Does the file still show up as a generic attachment?]

---

## Requirement 7: Collaborative Document Editing

*Inside any channel, users can open a shared document and edit it together. Multiple people can type at once. Edits propagate to everyone with the doc open within a heartbeat. The doc has a durable version that survives every editor disconnecting.*

### User Flow Design

```
Example formats:
Open document: User → Document Service → Relational Database (current doc state)
Live edit: User → Document Service → Edit Queue → Document Worker → Relational Database + broadcast
Broadcast: Document Service → Queue → other Document Services → other Users
Snapshot: Document Worker → File Store (periodic snapshot)
```

**Your collaborative-editing flows:**
[Write 3-5 specific flows showing how a user opens a doc, how concurrent edits get serialized, how edits broadcast to other open editors, and how the durable state is kept up to date]

### Building Blocks Added

- **[Document Service]**: [Holds the live edit connection. Owns the per-document session state.]
- **[Edit Queue + Document Worker]**: [Serializes concurrent operations into a single ordered stream applied to durable storage.]
- **[Relational Database for document state]**: [Why the same primitive as messages? What does the row shape look like?]
- **[Optional File Store for snapshots]**: [If you snapshot the document periodically, where does the snapshot live and why?]

### Architecture Decisions & Trade-offs

- **[Decision 1]**: [Operational transformation or CRDT at the concept level - which? Or do you use a simpler "last-write-wins per region" rule with a vector clock? Justify.]
- **[Decision 2]**: [Why a Queue between the Document Service and durable storage rather than direct writes?]
- **[Decision 3]**: [How does a user joining mid-session catch up to the current state without replaying every operation?]

---

## Requirement 8: Full-Text Search Across Message History

*Users search messages by keyword and get sub-second results across years of history. The search index must stay current as new messages arrive, without slowing the live send path.*

### User Flow Design

```
Example formats:
Index new message: Message Service → Indexing Queue → Indexing Worker → Key-Value Store (inverted index)
Search query: User → Search Service → Key-Value Store (inverted index) → Relational Database (rehydrate matches)
Update on edit: Message edit → Indexing Queue → Indexing Worker → Key-Value Store
```

**Your search flows:**
[Write 3-5 specific flows for both the indexing path and the query path. Include what happens on a message edit and how the index stays consistent with the durable message log.]

### Building Blocks Added

- **[Search Service]**: [The query entry point. Why a dedicated Service rather than overloading the Message Service?]
- **[Indexing Queue + Indexing Worker]**: [Builds the index offline. Why not index at query time?]
- **[Key-Value Store as inverted index]**: [Or a Relational Database full-text index used through the Search Service. Whichever you choose, name the building block.]

### Architecture Decisions & Trade-offs

- **[Decision 1]**: [Inverted index in a Key-Value Store, or a Relational Database full-text index accessed through the Search Service? Trade-offs of each.]
- **[Decision 2]**: [How fresh is the index? Sub-second behind the live message? A few seconds? How does that staleness window get communicated to the user, if at all?]
- **[Decision 3]**: [How does the Search Service rehydrate from inverted-index hits to actual message rows? Where do permissions get checked?]

---

## Requirement 9: Time-Based Retention and Archive Policies

*Teams configure retention windows. After the configured window, messages and files move to a cold archive or get deleted, depending on team policy. Retention runs continuously without operator intervention.*

### User Flow Design

```
Example formats:
Scheduled trigger: Time → Retention Service → Retention Queue (per-team jobs)
Retention job: Queue → Retention Worker → Relational Database (read policy) → Relational Database (delete) + File Store (archive)
Archive read: User → Search Service → File Store (cold tier) when needed
```

**Your retention flows:**
[Write 3-5 specific flows showing how Time triggers the work, how retention jobs are enqueued per team, and how the Worker reads the policy and moves or deletes data]

### Building Blocks Added

- **[Time external entity]**: [The trigger for retention sweeps. How often does it fire?]
- **[Retention Service]**: [Owns the policy reads and the scheduling of retention jobs.]
- **[Retention Queue + Retention Worker]**: [Does the actual delete or archive work, off the live path.]
- **[File Store cold tier]**: [Where archived content lands. Why a separate logical tier of the File Store?]

### Architecture Decisions & Trade-offs

- **[Decision 1]**: [Why Time as the trigger rather than checking on every message write?]
- **[Decision 2]**: [Why a Queue plus Worker instead of having the Retention Service do the deletes directly?]
- **[Decision 3]**: [Soft-delete first then hard-delete after a grace window, or hard-delete on first sweep? What happens when a user searches for content that has been archived?]

---

## Foundation Preserved

Walk through the Part 1 paths and confirm they are intact. The grader looks for the Part 1 messaging core surviving under the Part 2 additions.

- **Messaging core**: [Message Service + fanout Queue + recipient Services still in place?]
- **Presence**: [Still in Key-Value Store?]
- **Conversation list cache**: [Still routed through a Service?]
- **Notification path**: [Notification Queue + Worker + External Service push gateway still wired up?]

---

## Cross-Cutting Trade-offs

A strong Part 2 names where the new requirements collide with the Part 1 design.

### Index freshness vs send latency

[Indexing on the live send path slows sends. Indexing offline introduces a staleness window. Where do you land, and why?]

### Preview generation lag

[Previews are async. What does the user experience while a preview is rendering? How long is acceptable?]

### Edit convergence vs broadcast latency

[Serializing every edit through a Queue introduces a small delay. Skipping the Queue would risk divergent state. How do you balance?]

### Retention window vs storage cost

[Longer retention costs more storage. Shorter retention loses institutional memory. How does the architecture make this a team-by-team choice rather than a platform-wide one?]

---

## Failure Mode Analysis

Name what still breaks and how the system degrades:

- **If the Indexing Queue backs up**: [What happens to search freshness? Does the live send path notice?]
- **If the File Store is unavailable**: [Can users still send text-only messages? Do existing previews still load?]
- **If the Document Worker crashes mid-edit**: [What state does the document end up in? How does the next start-up recover?]
- **If a Retention Worker deletes data mid-search**: [Race conditions between retention and queries - how does the architecture avoid surfacing broken result rows?]

---

## Trade-offs Explicitly Accepted

- **[Trade-off 1]**: [What you gave up to add these capabilities]
- **[Trade-off 2]**: [What you gave up to add these capabilities]
- **[Trade-off 3]**: [What you gave up to add these capabilities]

---

## What This Evolution Intentionally Does NOT Address

[Anything you are deferring to Part 3 - explicitly. Examples: semantic search across messages and documents, AI assistant inside channels, video calls with recording and transcription. The grader rewards designs that know their boundaries.]

---

## Self-Graded Rubric (A / A- / B+)

**My grade**: [A / A- / B+]

**Why I assigned this grade**: [Apply the same rubric from Lesson 2. A means all four new requirements covered + optimal patterns + trade-offs named + Part 1 preserved. A- means strong with one precision gap. B+ means solid but missing a domain-specific pattern. Be honest.]

---

## Submission

Save this document as markdown and paste the full content into the **Challenge Part 2** submission form at [systemthinkinglab.ai](https://systemthinkinglab.ai/protected/course3/challenge2.html). Part 1 must be graded before Part 2 can be submitted.
