# Challenge 3 Part 1: Technical Design Document - MVP Foundation

**Student Name**: [Your Name]
**Submission Date**: [Date]
**Challenge**: TeamFlow Team Collaboration Platform - Part 1 MVP Foundation

---

## IMPORTANT: Technology-Agnostic Design Required

This technical design document must focus on **building blocks and architectural patterns**, not specific technologies.

**Use:**
- Building block names: Service, Worker, Queue, Key-Value Store, File Store, Relational Database, Vector Database
- External entities: User, External Service, Time
- Technology-agnostic terms: cache, fanout, sequence number, acknowledgement, presence state, push gateway

**Do NOT use:**
- Specific technologies: Redis, Memcached, Kafka, RabbitMQ, NATS, PostgreSQL, MongoDB, DynamoDB, Pusher, Ably
- Vendor names: AWS, Google Cloud, Azure, Firebase, Twilio, SendGrid, APNs as a branded product
- Programming languages or frameworks: Node.js, Express, Django, Socket.io, SignalR, Phoenix Channels

The grader will look for pattern recognition and clear reasoning, not technology brand-recall. Senior engineers think in patterns that transcend specific technologies.

## Recommended approach

1. **Draw your architecture diagram** using the 7 building blocks + 3 external entities. Use [this Google Drawing template](https://docs.google.com/drawings/d/1hbx9r8NCBNjMDZv9tAXzfvLR3-XPsOgHm9zrX0h_cO8/edit?usp=sharing) to get started.
2. **Use your diagram as reference** while writing your user flows and technical explanations.
3. **Ensure consistency** between what you draw and what you write.

---

## Scenario

TeamFlow is a new team collaboration platform launching its MVP. Teams need to message each other in direct conversations and group channels, see who is online, get notified of messages they missed, and trust that messages arrive in the right order. You are designing the MVP architecture that has to support real-time messaging without breaking when a user has a flaky connection or has the app closed on their phone.

---

## Architecture Overview

**High-Level Description**:
[Provide a 2-3 sentence overview of your overall architecture approach for the MVP. Name the live messaging path, the storage shape, and how missed-message notifications get out without slowing the live send.]

**Core Building Blocks Used** (check all that apply):
- [ ] Service (Blue Rectangle)
- [ ] Worker (Blue Trapezoid)
- [ ] Key-Value Store (Pink Diamond)
- [ ] File Store (Pink Pentagon)
- [ ] Queue (Pink Stacked Rectangles)
- [ ] Relational Database (Pink Cylinder)
- [ ] Vector Database (Pink Cube)
- [ ] User (Green Smiley)
- [ ] External Service (Green Cloud)
- [ ] Time (Green Hourglass)

---

## Requirement 1: Direct and Group Messaging with Low Latency

*Users send direct messages and post in group channels. Messages must arrive at every active recipient within a perceptible heartbeat, with no full page reload, no manual refresh.*

### User Flow Design

**Building block requirements:**
- Use EXACT building block names
- Use `+` for combinations (e.g., Queue + Worker)
- The User always connects to a Service first, never directly to storage

```
Example formats:
Send direct message: User → Message Service → Queue → recipient Message Services → recipient Users
Send group message: User → Channel Service → Queue → recipient Channel Services → recipient Users
Persist message: Message Service → Relational Database
```

**Your messaging flows:**
[Write 3-5 specific flows for direct messages, group messages, and how a recipient who is online receives a message in real time]

### Architecture Decisions & Trade-offs

**Key architectural decisions:**
- **[Decision 1]**: [Why a Queue between sender Service and recipient Services rather than direct Service-to-Service calls?]
- **[Decision 2]**: [How does the sender's Service know which recipient Services to fan out to for a group channel?]
- **[Decision 3]**: [Does the message hit the Relational Database before or after fanout, and why?]

### Technical Implementation Details

**Live connection ownership**: [Which Service holds the user's open connection? What happens when a user moves between two app instances?]

**Fanout pattern**: [How does one send become N delivered messages? Where does the work happen?]

**Persistence boundary**: [At what point in the flow is the message durably stored? What happens if the Queue is full or a recipient Service is down?]

---

## Requirement 2: Message Ordering and Delivery Confirmation

*Inside a conversation, messages must appear in the order they were sent, on every device. Senders need to see when their message was delivered to the recipient's app.*

### User Flow Design

```
Example formats:
Ordered send: Message Service → assigns per-conversation sequence number → Queue → recipient Services
Delivery ack: Recipient Message Service → ack → Message Service → Relational Database (delivery state)
Read receipt cache: Message Service → Key-Value Store (per-conversation last-read marker)
```

**Your ordering and confirmation flows:**
[Write 2-4 specific flows showing how a message gets a sequence number, how ordering is preserved through the Queue, and how acknowledgements travel back]

### Architecture Decisions & Trade-offs

**Key architectural decisions:**
- **[Decision 1]**: [Where do sequence numbers come from? A monotonic counter per conversation in the Relational Database? Per-partition ordering on the Queue? Something else?]
- **[Decision 2]**: [Why store delivery confirmation? Where does it live: Relational Database for the durable record, Key-Value Store for fast per-conversation state, or both?]
- **[Decision 3]**: [What happens to ordering when the recipient is offline and the message is queued for later delivery?]

### Technical Implementation Details

**Ordering mechanism**: [Name the concrete pattern - sequence numbers, monotonic IDs, per-conversation queue partitions]

**Acknowledgement flow**: [What does an ack look like end-to-end? Sender Service → Queue → Recipient Service → ack back. Where is the ack persisted?]

**Out-of-order handling**: [What does the client do if two messages arrive in the wrong sequence?]

---

## Requirement 3: Presence Indicators Across Devices

*Users see whether their teammates are online, offline, or actively typing. A user signed in on their laptop and phone counts as online if either device is connected.*

### User Flow Design

```
Example formats:
Connection event: User connects → Message Service → Key-Value Store (per-device presence entry)
Presence read: User → Presence Service → Key-Value Store
Typing indicator: User types → Message Service → Key-Value Store (typing-state TTL) → Queue → recipient Services
```

**Your presence flows:**
[Write 2-4 specific flows for connection events, presence queries, and the typing indicator across multiple devices]

### Architecture Decisions & Trade-offs

**Key architectural decisions:**
- **[Decision 1]**: [Why a Key-Value Store for presence rather than the Relational Database? What pattern does presence fit: high-write, fast-read, ephemeral?]
- **[Decision 2]**: [How is multi-device presence aggregated? Per-device entries under a user key? An "any device online" rule? Something else?]
- **[Decision 3]**: [How does typing state expire so a user does not appear to be typing forever after they close the tab?]

### Technical Implementation Details

**Presence key shape**: [What does a presence entry look like? `presence:user_id:device_id` → status + last-seen?]

**Multi-device aggregation**: [How do reads combine multiple device entries into a single "Alex is online" answer?]

**Typing-state TTL**: [How short is the TTL? What refreshes it while the user keeps typing?]

---

## Requirement 4: Cache Active Conversation Lists

*Every time a user opens the app, the home screen shows their list of active conversations with last-message previews and unread counts. This list is hit on every app open. Hitting the Relational Database every time would not survive even moderate growth.*

### User Flow Design

```
Example formats:
Cache hit: User → Conversation Service → Key-Value Store
Cache miss: User → Conversation Service → Key-Value Store → Relational Database → (populate cache) → respond
Invalidation: New message → Message Service → Key-Value Store (update conversation list cache)
```

**Your conversation-list flows:**
[Write 2-4 specific flows showing both the hit and miss paths, plus the invalidation path when a new message arrives]

### Architecture Decisions & Trade-offs

**Key architectural decisions:**
- **[Decision 1]**: [Cache-aside, write-through, or write-behind? Why?]
- **[Decision 2]**: [TTL with refresh, write-through invalidation on every message, or both?]
- **[Decision 3]**: [What is in the cached value? A list of conversation IDs? Full preview snippets? Unread counts?]

### Technical Implementation Details

**Cache keys and values**: [What is the key? What is the shape of the value? How big is the value per user?]

**Invalidation strategy**: [When does the cache get updated? On every send? Only when the conversation list itself changes? Both?]

**Cold-start cost**: [What does the first read after a cache miss look like in terms of Relational Database load?]

---

## Requirement 5: Notification Delivery for Missed Messages

*If the recipient is offline, asleep, or has the app closed, they need a push notification on their phone within seconds of the message being sent. The notification path must not block the live send path: a slow push gateway must not slow down delivery to online recipients.*

### User Flow Design

```
Example formats:
Detect offline recipient: Message Service → Key-Value Store (presence check) → Queue (notification job)
Notification delivery: Queue → Notification Worker → External Service (push gateway) → user device
Retry on failure: Notification Worker → backoff → retry → External Service
```

**Your notification flows:**
[Write 2-4 specific flows showing how an offline recipient gets detected, how the notification job is queued, and how the Worker calls the push gateway]

### Architecture Decisions & Trade-offs

**Key architectural decisions:**
- **[Decision 1]**: [Why fire-and-forget to a Queue rather than a synchronous call to the push gateway from the Message Service?]
- **[Decision 2]**: [How do you detect "this recipient was offline" at send time - presence Key-Value Store lookup? An ack-timeout reaper? A delivery-state row in the Relational Database that a Worker watches?]
- **[Decision 3]**: [What happens when the External Service push gateway is rate-limiting you or returning errors? How does the Worker retry without losing notifications?]

### Technical Implementation Details

**Detection trigger**: [What signal tells the system "this needs a push notification"?]

**Worker behavior**: [How many notification Workers? How do they share work? What is the retry and backoff policy?]

**External Service**: [The push gateway is an External Service. What does the contract look like? Token in, delivery acknowledgement out?]

---

## Overall Architecture Analysis

### Key design decisions (whole-system level)

1. **[Decision 1]**: [Rationale]
2. **[Decision 2]**: [Rationale]
3. **[Decision 3]**: [Rationale]

### Building block combinations used

- **[Pattern 1]**: [Which building blocks combined, where, and why. Example: Queue + Worker + External Service for async push notifications.]
- **[Pattern 2]**: [Which building blocks combined, where, and why. Example: Key-Value Store + Relational Database for cache-aside on conversation lists.]
- **[Pattern 3]**: [Which building blocks combined, where, and why. Example: Service + Queue + Service for message fanout.]

### Trade-offs explicitly accepted

- **[Trade-off 1]**: [What you gave up and what you gained. Example: eventual consistency on the conversation list cache in exchange for sub-millisecond reads.]
- **[Trade-off 2]**: [What you gave up and what you gained.]

### What this MVP intentionally does NOT address

[Anything you are deferring to Part 2 or Part 3 - be explicit about what is out of scope. Examples: file sharing, collaborative document editing, full-text search across history, retention policies, semantic search, AI features, video calls. The grader rewards designs that know their boundaries.]

### Self-graded rubric (A / A- / B+)

**My grade**: [A / A- / B+]

**Why I assigned this grade**: [One paragraph using the rubric from Lesson 2 - A means all requirements + optimal blocks + trade-offs acknowledged, A- means strong with one precision gap, B+ means solid with one domain-specific gap]

---

## Submission

Save this document as markdown and paste the full content into the **Challenge Part 1** submission form at [systemthinkinglab.ai](https://systemthinkinglab.ai/protected/course3/challenge1.html). You will receive AI-graded feedback within 24 hours.
