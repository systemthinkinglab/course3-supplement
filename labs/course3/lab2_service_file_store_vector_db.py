#!/usr/bin/env python3
# =============================================================================
# Systems Thinking in the AI Era
# https://systemthinkinglab.ai
#
# This code is part of the "Systems Thinking in the AI Era" course series.
# For more information, educational content, and courses, visit:
# https://systemthinkinglab.ai
# =============================================================================

"""
Systems Thinking in the AI Era III: Real-Time & Communication Systems
Lesson 9: Service + File Store + Vector Database Discovery Lab
Interactive Python Application

Three progressive experiments that build deep intuition for semantic
understanding in communication systems:
1. Keyword search vs semantic (vector) search on chat history
2. Embedding pipeline patterns: inline vs queue-then-worker
3. Real-time AI assist: inline LLM, async stream, precompute + retrieve

The Vector Database in this lab uses simulated, deterministic embeddings
(bag-of-words + topic features) so the lab runs offline with zero API
dependencies. The same patterns apply when you swap in a real embedding
model behind the same Building Block interface.
"""

import os
import sys
import time
import math
import random
import hashlib
import argparse
import threading
from typing import Optional, List, Dict, Tuple

# Dual-mode import so this file works in both layouts:
#   1. Monorepo / standalone: building_blocks.py sits next to this file
#   2. course3-supplement repo: building_blocks/ is a top-level package
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)
sys.path.insert(0, os.path.dirname(os.path.dirname(script_dir)))

try:
    # Sibling import - works when building_blocks.py is next to this file
    from building_blocks import Service, Worker, FileStore, Queue, RelationalDB, VectorDB
except ImportError:
    try:
        # Package import - works when building_blocks/ is a top-level package
        from building_blocks.building_blocks import (
            Service, Worker, FileStore, Queue, RelationalDB, VectorDB
        )
    except ImportError:
        print("Error: Could not import building_blocks module.")
        print("Expected building_blocks.py next to this file, OR building_blocks/ package at repo root.")
        sys.exit(1)


# Constants - tuned so the user can feel timing differences without long waits
SIMULATED_LLM_LATENCY_S = 0.8      # 800ms for a "real" LLM call
SIMULATED_EMBEDDING_LATENCY_S = 0.15  # 150ms to compute an embedding
SIMULATED_DB_LATENCY_S = 0.02      # 20ms per relational DB read
EMBEDDING_DIMENSION = 64           # small enough to be fast, large enough to be interesting


# =============================================================================
# Simulated embedding function
# =============================================================================
#
# Real systems call out to an embedding API (OpenAI, Cohere, HuggingFace).
# For an offline lab we need something deterministic that nonetheless gives
# semantically related sentences higher cosine similarity than unrelated ones.
#
# Strategy:
#   - Maintain a small lexicon of "topic seed" words (schedule, location,
#     food, project, greeting). Each seed maps to a specific dimension cluster.
#   - For each word in the input, hash it to a base index and add a unit
#     contribution. Then add topic boosts for any topic seed words detected
#     by simple synonym lookup.
#   - The result is a deterministic, low-dim semantic vector where related
#     phrases land in similar regions of the space.
#
# This is not a real embedding model. It is a teaching simulation. The lab
# never claims otherwise; the building block interface is what matters.

TOPIC_LEXICON = {
    # schedule / timing
    "schedule": ["schedule", "meeting", "pushed", "delayed", "rescheduled", "moved",
                 "postponed", "time", "calendar", "later", "earlier", "tomorrow",
                 "monday", "tuesday", "wednesday", "thursday", "friday"],
    # location / where
    "location": ["where", "location", "room", "office", "building", "floor",
                 "address", "place", "venue", "here", "there"],
    # food / lunch
    "food": ["lunch", "dinner", "food", "eat", "restaurant", "menu", "coffee",
             "breakfast", "snack", "meal"],
    # project / deliverable
    "project": ["deck", "slides", "presentation", "doc", "document", "draft",
                "report", "spec", "design", "deliverable", "project", "ticket"],
    # status / blocker
    "status": ["status", "blocked", "stuck", "done", "finished", "complete",
               "shipped", "ready", "waiting", "progress"],
    # greeting / social
    "greeting": ["hello", "hi", "hey", "morning", "afternoon", "evening",
                 "thanks", "thank", "welcome"],
}

TOPIC_NAMES = list(TOPIC_LEXICON.keys())


def _word_index(word: str, dim: int) -> int:
    """Deterministic hash to a stable dimension index."""
    h = hashlib.sha256(word.lower().encode("utf-8")).digest()
    return int.from_bytes(h[:4], "big") % dim


def simulate_embedding(text: str, dim: int = EMBEDDING_DIMENSION) -> List[float]:
    """
    Deterministic simulated embedding.

    The first len(TOPIC_NAMES) dimensions are reserved as "topic channels."
    The remaining dimensions absorb per-word noise so unrelated text doesn't
    accidentally collide on the topic channels.
    """
    vec = [0.0] * dim
    words = [w.strip(".,!?;:\"'()").lower() for w in text.split() if w.strip()]
    if not words:
        return vec

    # Topic channels: boost the slot for any topic seed we recognize
    for i, topic in enumerate(TOPIC_NAMES):
        seeds = TOPIC_LEXICON[topic]
        topic_score = 0.0
        for w in words:
            if w in seeds:
                topic_score += 1.0
        vec[i] = topic_score

    # Word channels: add small contributions in the remainder of the vector
    word_channel_start = len(TOPIC_NAMES)
    word_channel_size = dim - word_channel_start
    for w in words:
        idx = word_channel_start + (_word_index(w, word_channel_size))
        vec[idx] += 0.4  # smaller magnitude than topic boost

    # Normalize so cosine similarity behaves nicely
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        vec = [x / norm for x in vec]
    return vec


def keyword_overlap_score(query: str, doc: str) -> float:
    """Naive keyword match: fraction of query tokens that appear in doc."""
    q_tokens = {w.strip(".,!?;:\"'()").lower() for w in query.split() if w.strip()}
    d_tokens = {w.strip(".,!?;:\"'()").lower() for w in doc.split() if w.strip()}
    if not q_tokens:
        return 0.0
    shared = q_tokens & d_tokens
    return len(shared) / len(q_tokens)


# =============================================================================
# LabExperience
# =============================================================================

class LabExperience:
    """Interactive lab experience for Lesson 9: Service + File Store + Vector DB"""

    def __init__(self, student_name: str = "Student"):
        self.student_name = student_name
        self.experiment_times = {}

        self.separator = "=" * 80
        self.mini_separator = "-" * 40

        self.typewriter_speed = 0.03
        self.fast_typewriter_speed = 0.01
        self.instant_print = False
        self.skip_typewriter = False
        self.non_interactive = False

        self.print_lock = threading.Lock()

    # -----------------------------------------------------------------------
    # Print helpers
    # -----------------------------------------------------------------------

    def typewriter_print(self, text: str, speed: Optional[float] = None, end: str = "\n"):
        if self.instant_print or self.skip_typewriter:
            print(text, end=end)
            return
        if speed is None:
            speed = self.typewriter_speed
        for char in text:
            print(char, end='', flush=True)
            if char not in [' ', '\n', '\t']:
                time.sleep(speed)
        print(end=end)

    def direct_print(self, text: str, end: str = "\n"):
        with self.print_lock:
            print(text, end=end)

    def print_header(self, text: str, style: str = "main"):
        if style == "main":
            print(f"\n{self.separator}")
            print(f"  {text.upper()}")
            print(self.separator)
        elif style == "sub":
            print(f"\n{self.mini_separator}")
            print(f"  {text}")
            print(self.mini_separator)
        elif style == "experiment":
            print(f"\n{'#' * 60}")
            print(f"  EXPERIMENT: {text}")
            print('#' * 60)

    def print_experiment(self, text: str):
        self.print_header(text, style="experiment")

    def print_info(self, text: str, indent: int = 0):
        prefix = "  " * indent
        for line in text.strip().split('\n'):
            self.typewriter_print(f"{prefix}{line}")

    def print_result(self, text: str):
        self.typewriter_print(f"[RESULT] {text}")

    def print_warning(self, text: str):
        self.typewriter_print(f"[NOTE]   {text}")

    def wait_for_enter(self, prompt: str = "Press ENTER to continue..."):
        if self.non_interactive:
            return
        input(f"\n>> {prompt}")

    def ask_yes_no(self, question: str) -> bool:
        if self.non_interactive:
            return True
        while True:
            response = input(f"\n?? {question} (yes/no): ").lower().strip()
            if response in ['yes', 'y']:
                return True
            elif response in ['no', 'n']:
                return False
            print("Please answer 'yes' or 'no'")

    def ask_multiple_choice(self, question: str, choices: list, responses: list) -> str:
        print(f"\nREFLECTION QUESTION:")
        print(f"   {question}\n")
        for i, choice in enumerate(choices, 1):
            print(f"   {i}. {choice}")
        if self.non_interactive:
            # In non-interactive mode, just print the first response so the
            # full lab content gets exercised end to end.
            print(f"\n[non-interactive] auto-selecting choice 1")
            print(f"\n>>", end=' ')
            self.typewriter_print(responses[0])
            return choices[0]
        while True:
            try:
                choice_num = int(input(f"\n?? Enter your choice (1-{len(choices)}): ").strip())
                if 1 <= choice_num <= len(choices):
                    break
                print(f"Please enter a number between 1 and {len(choices)}")
            except ValueError:
                print(f"Please enter a valid number between 1 and {len(choices)}")
        selected_choice = choices[choice_num - 1]
        educational_response = responses[choice_num - 1]
        print(f"\nYou selected: {selected_choice}")
        print(f"\n>>", end=' ')
        self.typewriter_print(educational_response)
        self.wait_for_enter()
        return selected_choice

    # -----------------------------------------------------------------------
    # Welcome
    # -----------------------------------------------------------------------

    def run_welcome(self):
        self.print_header("WELCOME TO SYSTEMS THINKING IN THE AI ERA")
        print("\nSystems Thinking in the AI Era III: Real-Time & Communication Systems")
        print("Lesson 9: Service + File Store + Vector Database Discovery Lab\n")

        self.typewriter_print(
            "Transform from a code writer who thinks of search as 'finding the right keywords'"
        )
        self.typewriter_print(
            "to a system thinker who knows when meaning has to win over wording."
        )

        if not self.non_interactive:
            entered = input("\n\nWhat's your name? ").strip()
            if entered:
                self.student_name = entered
        self.typewriter_print(
            f"\nWelcome, {self.student_name}. Today we discover semantic search the same "
            f"way we discover anything important in this course: by feeling it."
        )

        self.print_info("""
You're about to build intuition for the patterns that make modern AI-powered
communication tools possible. Slack message search, chatbot memory, AI smart
reply, semantic FAQ retrieval. All of them share the same skeleton.

You'll run three experiments:
1. Keyword vs semantic search: feel meaning win over wording
2. Embedding pipeline: feel why we move embedding off the write path
3. Real-time AI assist: feel the latency, cost, and freshness tradeoffs

After each experiment, three multiple-choice reflection questions with
immediate educational feedback.
""")
        self.wait_for_enter("Ready to discover? Press ENTER to begin.")

    # =======================================================================
    # EXPERIMENT 1 - Keyword vs Semantic Search
    # =======================================================================

    def experiment_1_keyword_vs_semantic(self):
        self.print_experiment("1 - KEYWORD SEARCH vs SEMANTIC SEARCH")

        self.print_info("""
A small team has been chatting all morning. Your job is to build the search
box that lets them find old messages.

Approach A (keyword search): look for shared words between the query and the
message body. Fast, easy to explain. Works fine when the user happens to
type the same words that were used in the message.

Approach B (semantic search): represent each message as a vector and store
it in a Vector Database. At query time, embed the query the same way and
return the nearest neighbors. The match is on meaning, not wording.

You'll search the same chat history with both approaches and compare what
each one finds.
""")
        self.wait_for_enter()

        # Sample chat history. Notice these messages do NOT share keywords
        # with the queries we're going to run; that's the whole point.
        chat_messages = [
            ("alice",  "the 10am meeting got pushed to 2pm"),
            ("bob",    "lunch is delayed by half an hour"),
            ("carol",  "where is the deck for the review?"),
            ("dave",   "I'm blocked on the API spec from product"),
            ("alice",  "hey team, morning! coffee anyone?"),
            ("bob",    "the demo room moved to floor 4"),
            ("carol",  "I'll have the draft slides ready tomorrow"),
            ("dave",   "sushi place on 3rd street has a 30 minute wait today"),
            ("alice",  "kickoff tuesday is rescheduled to thursday"),
            ("bob",    "anyone seen the project doc from last week?"),
        ]

        # Set up Vector DB and index every message
        self.typewriter_print("\nIndexing 10 chat messages into the Vector Database...")
        vector_db = VectorDB("chat_history", dimension=EMBEDDING_DIMENSION)
        for i, (author, text) in enumerate(chat_messages):
            embedding = simulate_embedding(text)
            vector_db.store_vector(
                f"msg_{i}",
                embedding,
                metadata={"author": author, "text": text}
            )
        self.print_result(f"Indexed {len(chat_messages)} messages.")

        # Wrap both search approaches behind a Service so the user sees the
        # building-block-on-building-block composition explicitly.
        search_service = Service("chat_search")

        @search_service.route("/keyword")
        def keyword_handler(data):
            query = data["query"]
            scored = []
            for i, (author, text) in enumerate(chat_messages):
                score = keyword_overlap_score(query, text)
                if score > 0:
                    scored.append({"id": f"msg_{i}", "score": score,
                                   "author": author, "text": text})
            scored.sort(key=lambda x: x["score"], reverse=True)
            return scored[:3]

        @search_service.route("/semantic")
        def semantic_handler(data):
            query = data["query"]
            query_vec = simulate_embedding(query)
            hits = vector_db.similarity_search(query_vec, top_k=3)
            return [
                {"id": h["id"], "score": round(h["similarity"], 3),
                 "author": h["metadata"]["author"], "text": h["metadata"]["text"]}
                for h in hits
            ]

        # Run both approaches against the same queries
        queries = [
            "schedule changes",
            "presentation location",
            "food plans",
        ]

        start_time = time.time()
        for q in queries:
            self.print_header(f"Query: \"{q}\"", style="sub")

            self.typewriter_print("\nApproach A - keyword search:", speed=self.fast_typewriter_speed)
            kw_resp = search_service.handle_request("/keyword", data={"query": q})
            kw_hits = kw_resp["data"]
            if not kw_hits:
                self.print_warning("No matches. Keyword search found zero results.")
            else:
                for h in kw_hits:
                    self.direct_print(f"   [{h['score']:.2f}] {h['author']}: {h['text']}")

            self.typewriter_print("\nApproach B - semantic search:", speed=self.fast_typewriter_speed)
            sem_resp = search_service.handle_request("/semantic", data={"query": q})
            sem_hits = sem_resp["data"]
            for h in sem_hits:
                self.direct_print(f"   [{h['score']:.2f}] {h['author']}: {h['text']}")

        self.experiment_times['experiment_1'] = time.time() - start_time

        self.print_info("""
What you just saw: every query was written in language that shares almost
no words with the relevant chat messages. "schedule changes" found "the
10am meeting got pushed" and "kickoff tuesday is rescheduled". Keyword
search missed those entirely because there's no overlap on the literal
words.

That's the whole story of vector search: meaning wins over wording.
""")

        self.print_header("EXPERIMENT 1 REFLECTIONS", style="sub")

        self.ask_multiple_choice(
            "Why did keyword search miss messages that semantic search found?",
            [
                "The query and the message describe the same idea but use different words, so there's no token overlap for keyword search to match on",
                "Keyword search was misconfigured in this lab",
                "Semantic search is just lucky with these particular messages",
            ],
            [
                "Right. Users describe what they remember, not what was literally typed. They search 'schedule changes' when the original message said 'pushed to 2pm'. Keyword search has no way to bridge that gap. Semantic search puts both phrases near the 'schedule/timing' region of the vector space, so they land close to each other regardless of wording.",
                "Keyword search is doing exactly what it's designed to do: find shared tokens. The limitation isn't a bug, it's the fundamental ceiling of the approach. No amount of configuration tuning lets it match words that aren't there.",
                "It's not luck. Both 'pushed' and 'rescheduled' boosted the schedule channel in the simulated embedding. The query 'schedule changes' also boosted that channel. They landed near each other in the vector space by design, not by accident. Real embedding models do the same thing at much higher fidelity.",
            ],
        )

        self.ask_multiple_choice(
            "What does it mean that a Vector Database stores 'meaning' instead of 'words'?",
            [
                "Each piece of text is represented as a high-dimensional vector where nearby vectors correspond to similar ideas; the actual words are not directly stored as match keys",
                "Vector databases internally translate every sentence into a canonical English phrase",
                "Vector databases compress text smaller so search is faster",
            ],
            [
                "Right. The vector is a coordinate in 'idea space'. Two sentences that mean similar things land near each other even if they share no words. Two sentences that share words but mean different things land far apart. That property is what makes vector search so different from keyword search.",
                "There's no canonical English phrase. The whole point of the vector representation is that meaning is expressed numerically, not linguistically. The embedding model decides what counts as 'close' based on what it learned from training data.",
                "Compression is a side effect at best. The actual value of vector search is the geometric property: similar ideas cluster together. A compressed string search would still match on words, not on meaning.",
            ],
        )

        self.ask_multiple_choice(
            "When would keyword search still be the right choice?",
            [
                "When exact term matching matters: code search, log search, regulatory filings, anything where 'mentions of class X' must be precise",
                "Never. Vector search is strictly better.",
                "Only for very small datasets where vectors are too expensive",
            ],
            [
                "Right. Keyword search is exact and explainable. If a compliance officer searches for 'GDPR' they want every document that literally says GDPR, not documents about 'European privacy regulations'. Code search has the same property: you want exact symbol matches. Production systems often combine both approaches and let the user pick.",
                "Vector search is not strictly better; it's different. It trades precision for recall and exact match for semantic match. For some use cases (exact symbol lookup, legal compliance, audit trails), that trade is wrong. The systems thinker's job is to know which mode each use case needs.",
                "Cost is real but it's not the main constraint. Even on small datasets, keyword search is the right choice for exact-match use cases. Conversely, on huge datasets, vector search is fine if the index is built well. Size doesn't determine the right approach; the question type does.",
            ],
        )

        if self.ask_yes_no("Ready to feel why we move embedding off the write path?"):
            self.experiment_2_embedding_pipeline()

    # =======================================================================
    # EXPERIMENT 2 - Embedding pipeline patterns
    # =======================================================================

    def experiment_2_embedding_pipeline(self):
        self.print_experiment("2 - EMBEDDING PIPELINE: INLINE vs QUEUE-THEN-WORKER")

        self.print_info("""
Now your chat app needs to index new messages as they arrive, so that
semantic search stays current.

Computing an embedding takes real time. In this lab we simulate 150ms per
embedding, which is roughly what a small API call costs in production.

Two patterns to compare:

Pattern A (inline / block-and-embed):
   Service receives message -> compute embedding -> write to DB and
   Vector DB -> return to user.
   Latency for the user = full DB write + full embedding call.

Pattern B (pipelined / queue-then-worker):
   Service receives message -> write to Relational DB -> enqueue
   embed job -> return to user immediately.
   A separate Worker reads the queue and writes to the Vector DB later.
   Latency for the user = only the DB write.

The trade is freshness of the index vs latency of the user-facing path.
""")
        self.wait_for_enter()

        # Shared dataset: a stream of incoming messages
        incoming_messages = [
            "the standup is moved to 11am",
            "lunch order is delayed",
            "where is the demo room today?",
            "draft slides for tomorrow are in the shared folder",
            "kickoff thursday postponed to next monday",
            "coffee run, anyone want anything?",
            "design review needs the latest deck",
            "ticket queue is empty, shipping the build",
        ]

        # ------------------------------------------------------------------
        # Pattern A: inline
        # ------------------------------------------------------------------
        self.print_header("Pattern A: inline (block-and-embed)", style="sub")

        db_a = RelationalDB("chat_inline", db_path=":memory:")
        db_a.create_table("messages",
                          "id INTEGER PRIMARY KEY AUTOINCREMENT, author TEXT, body TEXT")
        vector_db_a = VectorDB("chat_inline_vectors", dimension=EMBEDDING_DIMENSION)

        service_a = Service("post_message_inline")

        @service_a.route("/post")
        def handle_inline(data):
            # 1. Persist the message
            time.sleep(SIMULATED_DB_LATENCY_S)
            row_id = db_a.insert("messages",
                                 {"author": data["author"], "body": data["body"]})
            # 2. Compute embedding inline (slow)
            time.sleep(SIMULATED_EMBEDDING_LATENCY_S)
            vec = simulate_embedding(data["body"])
            # 3. Write to Vector DB
            vector_db_a.store_vector(f"msg_{row_id}", vec,
                                     metadata={"author": data["author"],
                                               "body": data["body"]})
            return {"id": row_id, "indexed": True}

        latencies_a = []
        self.typewriter_print(
            f"\nPosting {len(incoming_messages)} messages, one at a time...\n",
            speed=self.fast_typewriter_speed,
        )
        start_a = time.time()
        for i, body in enumerate(incoming_messages):
            t0 = time.time()
            service_a.handle_request("/post",
                                     data={"author": f"user{i % 3}", "body": body})
            dt = time.time() - t0
            latencies_a.append(dt)
            self.direct_print(f"   posted msg {i+1}/{len(incoming_messages)} - "
                              f"user-facing latency: {dt*1000:.0f}ms")
        elapsed_a = time.time() - start_a
        avg_a = sum(latencies_a) / len(latencies_a) * 1000

        print(f"\nPattern A statistics:")
        print(f"   Total elapsed: {elapsed_a:.2f}s")
        print(f"   Average user-facing latency: {avg_a:.0f}ms")
        print(f"   Vector DB size: {vector_db_a.get_stats()['vector_count']}")
        self.print_warning(
            f"Every user wait includes the full embedding call. "
            f"In production with a real model, that's often 200ms-1s per post."
        )

        # ------------------------------------------------------------------
        # Pattern B: queue-then-worker
        # ------------------------------------------------------------------
        self.print_header("Pattern B: queue-then-worker (pipelined)", style="sub")

        db_b = RelationalDB("chat_pipelined", db_path=":memory:")
        db_b.create_table("messages",
                          "id INTEGER PRIMARY KEY AUTOINCREMENT, author TEXT, body TEXT")
        vector_db_b = VectorDB("chat_pipelined_vectors", dimension=EMBEDDING_DIMENSION)
        embed_queue = Queue("embed_jobs", max_size=200)

        worker_done = threading.Event()
        worker_count = {"processed": 0, "target": len(incoming_messages)}

        @embed_queue.subscriber("embed")
        def embed_subscriber(job):
            """Worker side. Compute embedding, write to Vector DB."""
            time.sleep(SIMULATED_EMBEDDING_LATENCY_S)
            vec = simulate_embedding(job["body"])
            vector_db_b.store_vector(
                f"msg_{job['row_id']}",
                vec,
                metadata={"author": job["author"], "body": job["body"]}
            )
            worker_count["processed"] += 1
            if worker_count["processed"] >= worker_count["target"]:
                worker_done.set()

        service_b = Service("post_message_pipelined")

        @service_b.route("/post")
        def handle_pipelined(data):
            # 1. Persist the message
            time.sleep(SIMULATED_DB_LATENCY_S)
            row_id = db_b.insert("messages",
                                 {"author": data["author"], "body": data["body"]})
            # 2. Enqueue embed job and return immediately
            embed_queue.enqueue(
                {"row_id": row_id, "author": data["author"], "body": data["body"]},
                message_type="embed",
            )
            return {"id": row_id, "indexed": False, "queued": True}

        latencies_b = []
        self.typewriter_print(
            f"\nPosting {len(incoming_messages)} messages, one at a time...\n",
            speed=self.fast_typewriter_speed,
        )
        start_b = time.time()
        for i, body in enumerate(incoming_messages):
            t0 = time.time()
            service_b.handle_request("/post",
                                     data={"author": f"user{i % 3}", "body": body})
            dt = time.time() - t0
            latencies_b.append(dt)
            self.direct_print(f"   posted msg {i+1}/{len(incoming_messages)} - "
                              f"user-facing latency: {dt*1000:.0f}ms")
        user_elapsed_b = time.time() - start_b
        avg_b = sum(latencies_b) / len(latencies_b) * 1000

        # Wait for worker to drain
        self.typewriter_print(
            "\nUser path returned. Now waiting for the worker to finish indexing in the background...",
            speed=self.fast_typewriter_speed,
        )
        worker_done.wait(timeout=10.0)
        total_elapsed_b = time.time() - start_b
        embed_queue.stop()

        print(f"\nPattern B statistics:")
        print(f"   User-facing total elapsed: {user_elapsed_b:.2f}s")
        print(f"   Average user-facing latency: {avg_b:.0f}ms")
        print(f"   Background indexing total elapsed: {total_elapsed_b:.2f}s")
        print(f"   Vector DB size after worker drained: "
              f"{vector_db_b.get_stats()['vector_count']}")
        self.print_result(
            f"Users got responses {avg_a / max(avg_b, 0.001):.1f}x faster. "
            f"The indexing work still happened. It just didn't block the user."
        )

        self.experiment_times['experiment_2'] = elapsed_a + total_elapsed_b

        self.print_header("EXPERIMENT 2 REFLECTIONS", style="sub")

        self.ask_multiple_choice(
            "Why did the user-facing latency drop so dramatically in Pattern B?",
            [
                "Because the embedding work moved off the user's request path; the Service only writes to the DB and enqueues a job, then returns",
                "Because the Queue is faster than the Vector DB",
                "Because the Worker computes embeddings faster than the Service does",
            ],
            [
                "Right. The work itself didn't get faster. We just moved it off the user's critical path. The user pays for the DB write and an enqueue (microseconds). The 150ms embedding call happens after the user has already moved on. This pattern is everywhere: image processing pipelines, video transcoding, full-text indexing.",
                "Queues and Vector DBs aren't really comparable; one is a transport, the other is a storage system. The Queue isn't doing the embedding work; it's just deferring it. The user benefits because they don't wait for the work, not because the work got faster.",
                "Both the inline Service and the Worker call the exact same simulate_embedding function. There's no speed difference per embedding. The win comes from moving the work off the user's request path, not from running it faster.",
            ],
        )

        self.ask_multiple_choice(
            "What is the cost of Pattern B (the queue-then-worker pattern)?",
            [
                "The index is briefly out of date; a message posted right now will not appear in semantic search until the Worker finishes processing it (eventual consistency)",
                "The Queue can lose messages randomly",
                "The Worker uses more memory than an inline Service",
            ],
            [
                "Right. This is the classic eventual consistency trade. The message is durably saved to the Relational DB before the user gets their response, so nothing is lost. But the Vector DB lags by however long the Worker takes to drain its queue. For most use cases that lag is acceptable (a few seconds), and the latency win is worth it. For use cases where the new message MUST be searchable immediately, you might keep the inline pattern or use a hybrid.",
                "Queues don't randomly lose messages; production queues (SQS, RabbitMQ, Kafka) have strong durability guarantees. The cost is timing, not data loss. The lag between write and index is the actual trade.",
                "Memory usage isn't really the issue. Workers and Services run similar code paths. The architectural cost of Pattern B is the eventual consistency window: between the write and the embed completing, the new message exists in the DB but isn't yet in the index.",
            ],
        )

        self.ask_multiple_choice(
            "When should you reach for Pattern A (inline) instead of Pattern B?",
            [
                "When the use case absolutely requires the data to be searchable the instant the write returns, even at the cost of user latency",
                "When you don't have a Queue building block available in your stack",
                "Always - simpler code is always better",
            ],
            [
                "Right. Some workflows have hard read-your-writes requirements on the search path. An AI agent that posts a message and then searches for it 50ms later. A document editor that re-runs RAG after every edit. For those, the eventual consistency window is unacceptable and you pay the latency cost. The systems thinker's job is to recognize which it is.",
                "Most modern stacks have a queue available (Redis Streams, SQS, RabbitMQ, even an in-process channel). The decision isn't 'do I have a queue', it's 'does my use case tolerate eventual consistency in the index'. Don't let tooling availability override the correctness requirement.",
                "Simpler isn't always better. Pattern A is simpler but pushes the latency cost onto every user. Pattern B is more moving parts but gives every user a faster experience. The simpler choice is often wrong at scale. Make the trade explicitly.",
            ],
        )

        if self.ask_yes_no("Ready to face real-time AI assist?"):
            self.experiment_3_realtime_ai_assist()

    # =======================================================================
    # EXPERIMENT 3 - Real-time AI assist (inline LLM, async stream, retrieve)
    # =======================================================================

    def experiment_3_realtime_ai_assist(self):
        self.print_experiment("3 - REAL-TIME AI ASSIST: THREE PATTERNS")

        self.print_info("""
A user types a question into your chatbot. You have to send back an
answer. You have three patterns available and they trade off latency,
cost, and freshness differently.

Pattern A - inline LLM call:
   Service blocks on the External Service (LLM API), waits for the full
   answer, returns it to the user. Simple. Slow. Pays for every call.

Pattern B - async streaming:
   Service starts the LLM call, then streams tokens back to the user as
   they arrive. Time-to-first-token is much lower. User perceives a
   responsive chatbot even though the total wall time is similar.

Pattern C - precompute + retrieve from Vector DB:
   For FAQ-style questions, the answers are already written and indexed
   as vectors. The Service embeds the question, hits the Vector DB,
   returns the nearest precomputed answer. No LLM call at all. Near-zero
   latency. Near-zero cost. Stale if the answer changes.

We'll run the same user question through all three.
""")
        self.wait_for_enter()

        # Build the precomputed FAQ store - Vector DB indexed with canned answers
        faq_entries = [
            ("How do I reset my password?",
             "Click 'Forgot password' on the login screen. We send a reset link to your email."),
            ("What are your business hours?",
             "Support is available Monday through Friday, 9am to 6pm Pacific time."),
            ("How do I export my data?",
             "Go to Settings > Account > Export. We email you a downloadable archive within 24 hours."),
            ("Can I cancel my subscription anytime?",
             "Yes, cancel anytime from Settings > Billing. Access continues until the end of your billing cycle."),
            ("How do I invite a teammate?",
             "Settings > Team > Invite. Enter their email and pick a role. They get an invite link by email."),
        ]
        faq_vector_db = VectorDB("faq_vectors", dimension=EMBEDDING_DIMENSION)
        for i, (q, a) in enumerate(faq_entries):
            faq_vector_db.store_vector(f"faq_{i}", simulate_embedding(q),
                                       metadata={"question": q, "answer": a})

        # Simulated External Service - the LLM
        def simulated_llm_full_response(prompt: str) -> str:
            """Block for the full latency, then return a complete response."""
            time.sleep(SIMULATED_LLM_LATENCY_S)
            return (f"Based on what you asked ('{prompt[:40]}...'), here is a "
                    f"thoughtful multi-sentence answer the model generated.")

        def simulated_llm_stream(prompt: str):
            """Yield tokens one at a time over the same total latency."""
            tokens = (
                f"Based on what you asked, here is a thoughtful multi-sentence "
                f"answer the model generated."
            ).split()
            per_token_delay = SIMULATED_LLM_LATENCY_S / max(len(tokens), 1)
            # A small initial setup delay so time-to-first-token is realistic
            time.sleep(per_token_delay * 2)
            for tok in tokens:
                yield tok
                time.sleep(per_token_delay)

        # ------------------------------------------------------------------
        # Build a Service that hosts all three handlers
        # ------------------------------------------------------------------
        chat_service = Service("ai_chat")

        @chat_service.route("/inline")
        def handle_inline(data):
            return simulated_llm_full_response(data["question"])

        @chat_service.route("/retrieve")
        def handle_retrieve(data):
            q_vec = simulate_embedding(data["question"])
            hits = faq_vector_db.similarity_search(q_vec, top_k=1)
            if not hits:
                return None
            top = hits[0]
            return {
                "answer": top["metadata"]["answer"],
                "matched_question": top["metadata"]["question"],
                "similarity": round(top["similarity"], 3),
            }

        # Streaming gets its own helper - Service handles streaming a bit
        # differently from a request/response handler. We measure
        # time-to-first-token explicitly.
        def streamed_call(question: str) -> Tuple[float, float, str]:
            t0 = time.time()
            t_first = None
            tokens = []
            for tok in simulated_llm_stream(question):
                if t_first is None:
                    t_first = time.time() - t0
                tokens.append(tok)
            total = time.time() - t0
            return (t_first or 0.0), total, " ".join(tokens)

        # ------------------------------------------------------------------
        # Run all three for a question that IS in the FAQ
        # ------------------------------------------------------------------
        faq_question = "I need to change my password, how?"
        self.print_header(f"FAQ-style question: \"{faq_question}\"", style="sub")

        # Pattern A
        self.typewriter_print("\nPattern A - inline LLM call:", speed=self.fast_typewriter_speed)
        t0 = time.time()
        resp_a = chat_service.handle_request("/inline", data={"question": faq_question})
        dt_a = time.time() - t0
        self.direct_print(f"   total latency: {dt_a*1000:.0f}ms")
        self.direct_print(f"   answer: {str(resp_a['data'])[:80]}...")

        # Pattern B
        self.typewriter_print("\nPattern B - streaming LLM:", speed=self.fast_typewriter_speed)
        t_first_b, t_total_b, streamed_text = streamed_call(faq_question)
        self.direct_print(f"   time to first token: {t_first_b*1000:.0f}ms")
        self.direct_print(f"   total latency: {t_total_b*1000:.0f}ms")
        self.direct_print(f"   answer: {streamed_text[:80]}...")

        # Pattern C
        self.typewriter_print(
            "\nPattern C - retrieve from Vector DB (no LLM call):",
            speed=self.fast_typewriter_speed,
        )
        t0 = time.time()
        resp_c = chat_service.handle_request("/retrieve", data={"question": faq_question})
        dt_c = time.time() - t0
        retrieved = resp_c["data"]
        self.direct_print(f"   total latency: {dt_c*1000:.0f}ms")
        self.direct_print(f"   matched FAQ: \"{retrieved['matched_question']}\" "
                          f"(similarity {retrieved['similarity']})")
        self.direct_print(f"   answer: {retrieved['answer']}")

        # ------------------------------------------------------------------
        # Run the same patterns for a question that is NOT in the FAQ
        # ------------------------------------------------------------------
        novel_question = "Can your chatbot help me draft a sales email to a customer in Tokyo?"
        self.print_header(f"Novel question (not in FAQ): \"{novel_question}\"", style="sub")

        self.typewriter_print("\nPattern C - retrieve attempt:", speed=self.fast_typewriter_speed)
        resp_c2 = chat_service.handle_request("/retrieve", data={"question": novel_question})
        retr2 = resp_c2["data"]
        self.direct_print(f"   best FAQ similarity: {retr2['similarity']}")
        if retr2["similarity"] < 0.5:
            self.print_warning(
                "Best FAQ match is below confidence threshold. "
                "This question needs an LLM call. Production systems gate "
                "retrieval behind a confidence threshold and fall back to "
                "Pattern A or B for low-confidence matches."
            )
        else:
            self.direct_print(f"   would return: {retr2['answer']}")

        self.typewriter_print(
            "\nPattern A - inline LLM (the only honest answer for a novel question):",
            speed=self.fast_typewriter_speed,
        )
        t0 = time.time()
        resp_a2 = chat_service.handle_request("/inline", data={"question": novel_question})
        dt_a2 = time.time() - t0
        self.direct_print(f"   total latency: {dt_a2*1000:.0f}ms")

        # ------------------------------------------------------------------
        # Comparison table
        # ------------------------------------------------------------------
        print(f"\nPattern comparison (FAQ question):")
        print(f"   {'Pattern':<35} {'Latency':>12} {'LLM call':>10} {'Cost':>8}")
        print(f"   {'-'*35} {'-'*12} {'-'*10} {'-'*8}")
        print(f"   {'A: inline LLM':<35} {dt_a*1000:>9.0f}ms {'yes':>10} {'$$':>8}")
        print(f"   {'B: streaming LLM':<35} "
              f"{t_first_b*1000:>9.0f}ms* {'yes':>10} {'$$':>8}")
        print(f"   {'C: precompute + retrieve':<35} "
              f"{dt_c*1000:>9.0f}ms {'no':>10} {'~$0':>8}")
        print(f"   * = time to first token (perceived latency)")

        self.experiment_times['experiment_3'] = dt_a + t_total_b + dt_c + dt_a2

        self.print_header("EXPERIMENT 3 REFLECTIONS", style="sub")

        self.ask_multiple_choice(
            "Why is streaming (Pattern B) usually better UX than inline (Pattern A) even though total time is similar?",
            [
                "Perceived latency is dominated by time-to-first-token; once the user sees text appearing they feel the system is working, even if the full answer takes the same total time",
                "Streaming is technically faster in total elapsed time",
                "Streaming uses less server CPU than inline calls",
            ],
            [
                "Right. Humans tolerate long total wait times much better when they get feedback that the system is alive. ChatGPT, Claude, every modern AI chat product streams for exactly this reason. Total wall time is roughly the same as an inline call, but the user gets the first token in a fraction of the time and feels engaged the whole way through.",
                "Streaming doesn't make the model faster. The model generates tokens at the same rate either way. Streaming just exposes them as they're produced instead of buffering until the end.",
                "Streaming vs inline doesn't meaningfully change server CPU. The model burns the same compute either way. The difference is purely in how bytes flow back to the client.",
            ],
        )

        self.ask_multiple_choice(
            "Why is Pattern C (precompute + retrieve) often cheaper than Pattern A by an order of magnitude?",
            [
                "Pattern C doesn't call the LLM at runtime; it returns a precomputed answer from a Vector DB lookup. LLM tokens cost real money; vector lookups are essentially free",
                "Pattern C is just a faster version of the same LLM call",
                "Pattern C uses a smaller, cheaper LLM behind the scenes",
            ],
            [
                "Right. Every LLM call has a per-token cost that adds up fast at scale. A high-volume FAQ chatbot answering 10,000 questions a day pays significant money to a model provider. If 80% of those questions match a precomputed answer in the Vector DB, you eliminate 80% of the model spend. This is one of the most concrete RAG vs raw-LLM economic arguments.",
                "Pattern C isn't a faster LLM, it's no LLM. The cost difference comes from skipping the model call entirely, not from running it faster.",
                "Pattern C doesn't involve any LLM at all at query time. The savings aren't from a smaller model, they're from avoiding the call altogether. The LLM may have been used offline to write the canned answers, but the runtime path doesn't touch it.",
            ],
        )

        self.ask_multiple_choice(
            "When does Pattern C break, and what do you do about it?",
            [
                "When the user's question isn't close enough to any precomputed entry; production systems set a similarity threshold and fall back to an LLM call (Pattern A or B) when no FAQ matches confidently",
                "When the Vector DB is too small; you should always have at least 100,000 entries",
                "Pattern C never breaks; LLMs are obsolete now",
            ],
            [
                "Right. This is the standard RAG gating pattern. If the top vector similarity is above a confidence threshold (say 0.75), return the precomputed answer. If not, fall back to an LLM call. You get the cost win on the common questions and the flexibility of an LLM on the unusual ones. Best of both worlds, at the price of one extra branch in your Service.",
                "Vector DB size doesn't determine when Pattern C breaks. What matters is whether the user's question semantically matches an indexed answer. A 100-entry FAQ that covers 90% of user questions is more valuable than a 100,000-entry FAQ that covers 30%. Coverage and similarity threshold matter, not raw count.",
                "LLMs are not obsolete. They handle the novel, the creative, the personalized. The systems thinker's move is to combine: cheap retrieval for the common questions, LLM for everything else. Pattern C and Pattern A are partners, not competitors.",
            ],
        )

        if self.ask_yes_no("Ready to see your discovery summary?"):
            self.show_summary()

    # =======================================================================
    # Summary
    # =======================================================================

    def show_summary(self):
        self.print_header("DISCOVERY SUMMARY")
        self.print_info("""
You've now experienced the three patterns that make AI-enhanced
communication systems possible.

What you discovered:

1. Semantic search vs keyword search:
   Keyword search matches tokens. Semantic search matches meaning.
   When users describe what they remember (not what was typed), only
   semantic search finds it. The Vector Database is the building block
   that makes this possible.

2. Embedding pipeline:
   Embedding is slow. Block-and-embed forces every user to wait for it.
   Queue-then-worker moves the embedding off the user's request path and
   trades latency for eventual consistency in the index. Almost always
   the right trade for chat-style apps.

3. Real-time AI assist - three patterns, one decision framework:
   Inline LLM: simple, slow, expensive. Use when streaming isn't supported.
   Streaming LLM: same total time, much lower perceived latency. Default
   for modern chat UX.
   Precompute + retrieve: near-zero latency, near-zero cost, stale if
   the source answer changes. Use for FAQ-style traffic, gated by a
   similarity threshold with LLM fallback.

Pattern recognition over technology trivia. The same skeleton (Service
delegates the hard work to a specialized building block; freshness,
latency, and cost are the three axes you trade against) shows up in
every AI-enhanced product, from Slack's smart replies to ChatGPT's
plugins to Notion's AI features.
""")
        print(f"\nTime spent per experiment:")
        for name, t in self.experiment_times.items():
            print(f"   {name}: {t:.1f}s")

        self.print_info("""
The next case study (Lessons 10-11, AI Chatbots) takes the patterns you
just felt and assembles them into a complete AI-powered communication
product. You'll recognize every piece because you built each one by
hand here.

You're ready.
""")

    # =======================================================================
    # Entry points
    # =======================================================================

    def run_full(self):
        self.run_welcome()
        self.experiment_1_keyword_vs_semantic()
        self.experiment_2_embedding_pipeline()
        self.experiment_3_realtime_ai_assist()
        self.show_summary()

    def run_one(self, experiment_num: int):
        mapping = {
            1: self.experiment_1_keyword_vs_semantic,
            2: self.experiment_2_embedding_pipeline,
            3: self.experiment_3_realtime_ai_assist,
        }
        fn = mapping.get(experiment_num)
        if fn is None:
            print(f"Unknown experiment: {experiment_num}. Choose 1-3.")
            return
        print(f"\nRunning Experiment {experiment_num} directly...\n")
        fn()


def main():
    parser = argparse.ArgumentParser(
        description="Course 3 Lab 2: Service + File Store + Vector Database Discovery"
    )
    parser.add_argument("experiment", nargs="?", type=int,
                        help="Optional experiment number (1-3) to run directly")
    parser.add_argument("--instant", action="store_true",
                        help="Disable typewriter effect (faster output)")
    parser.add_argument("--skip-typewriter", action="store_true",
                        help="Alias for --instant; disables typewriter effect")
    parser.add_argument("--no-interactive", action="store_true",
                        help="Run end-to-end without prompts (auto-selects first MC choice)")
    args = parser.parse_args()

    lab = LabExperience()
    if args.instant or args.skip_typewriter:
        lab.instant_print = True
        lab.skip_typewriter = True
    if args.no_interactive:
        lab.non_interactive = True
        lab.instant_print = True
        lab.skip_typewriter = True

    if args.experiment is None:
        lab.run_full()
    else:
        lab.run_one(args.experiment)


if __name__ == "__main__":
    main()
