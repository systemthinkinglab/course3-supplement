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
Lesson 2: Service + Queue Real-Time Messaging Discovery Lab
Interactive Python Application

This application guides students through three progressive experiments that
build deep intuition for routing messages between Services. Same message,
different delivery shape, and you will feel why the choice matters.
"""

import os
import sys
import time
import random
import argparse
import threading
from typing import Optional

# Dual-mode import so this file works in both layouts:
#   1. Monorepo / standalone:  building_blocks.py sits next to this file (sibling import)
#   2. course3-supplement repo: building_blocks/ is a top-level package; we add the
#      repo root to sys.path and import from the package
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)
sys.path.insert(0, os.path.dirname(os.path.dirname(script_dir)))

try:
    # Sibling import: works when building_blocks.py is next to this file
    from building_blocks import Service, Worker, Queue, KeyValueStore
except ImportError:
    try:
        # Package import: works when building_blocks/ is a top-level package
        from building_blocks.building_blocks import Service, Worker, Queue, KeyValueStore
    except ImportError:
        print("Error: Could not import building_blocks module.")
        print("Expected building_blocks.py next to this file, OR building_blocks/ package at repo root.")
        sys.exit(1)


class LabExperience:
    """Interactive lab experience for Lesson 2: Service + Queue Discovery"""

    def __init__(self, student_name: str = "Student"):
        self.student_name = student_name
        self.experiment_times = {}
        self.correct_answers = 0
        self.total_questions = 0

        self.separator = "=" * 80
        self.mini_separator = "-" * 40

        self.typewriter_speed = 0.03
        self.fast_typewriter_speed = 0.01
        self.instant_print = False

        self.print_lock = threading.Lock()

    # -----------------------------------------------------------------------
    # Print helpers (typewriter, thread-safe direct, headers)
    # -----------------------------------------------------------------------

    def typewriter_print(self, text: str, speed: Optional[float] = None, end: str = "\n"):
        if self.instant_print:
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
            print(f"🎯 {text.upper()}")
            print(self.separator)
        elif style == "sub":
            print(f"\n{self.mini_separator}")
            print(f"▶️  {text}")
            print(self.mini_separator)
        elif style == "experiment":
            print(f"\n{'🧪' * 20}")
            print(f"🧪 EXPERIMENT: {text}")
            print('🧪' * 20)

    def print_experiment(self, text: str):
        self.print_header(text, style="experiment")

    def print_info(self, text: str, indent: int = 0):
        prefix = "  " * indent + "ℹ️ " if indent == 0 else "  " * indent
        for line in text.strip().split('\n'):
            self.typewriter_print(f"{prefix}{line}")

    def print_action(self, text: str):
        self.typewriter_print(f"⚡ {text}", speed=self.fast_typewriter_speed)

    def print_result(self, text: str):
        self.typewriter_print(f"✅ {text}")

    def print_warning(self, text: str):
        self.typewriter_print(f"⚠️  {text}")

    def wait_for_enter(self, prompt: str = "Press ENTER to continue..."):
        input(f"\n📍 {prompt}")

    def ask_yes_no(self, question: str) -> bool:
        while True:
            response = input(f"\n❓ {question} (yes/no): ").lower().strip()
            if response in ['yes', 'y']:
                return True
            elif response in ['no', 'n']:
                return False
            print("Please answer 'yes' or 'no'")

    def ask_multiple_choice(self, question: str, choices: list, responses: list,
                            correct_index: int = 0) -> str:
        """Ask a multiple choice question with educational feedback per option.

        correct_index is the 0-based index of the correct choice in `choices`.
        We track right/wrong stats for the final summary.
        """
        self.total_questions += 1

        print(f"\n💭 REFLECTION QUESTION:")
        print(f"   {question}\n")
        for i, choice in enumerate(choices, 1):
            print(f"   {i}. {choice}")

        while True:
            try:
                choice_input = input(f"\n❓ Enter your choice (1-{len(choices)}): ").strip()
                choice_num = int(choice_input)
                if 1 <= choice_num <= len(choices):
                    break
                print(f"Please enter a number between 1 and {len(choices)}")
            except ValueError:
                print(f"Please enter a valid number between 1 and {len(choices)}")

        selected_choice = choices[choice_num - 1]
        educational_response = responses[choice_num - 1]

        if choice_num - 1 == correct_index:
            self.correct_answers += 1
            print(f"\n✅ You selected: {selected_choice}")
        else:
            print(f"\n📘 You selected: {selected_choice}")

        print("\n🎯 ", end='')
        self.typewriter_print(educational_response)
        self.wait_for_enter()
        return selected_choice

    # -----------------------------------------------------------------------
    # Welcome
    # -----------------------------------------------------------------------

    def run_welcome(self):
        self.print_header("WELCOME TO SYSTEMS THINKING IN THE AI ERA")
        print("\n🎓 Systems Thinking in the AI Era III: Real-Time & Communication Systems")
        print("📚 Lesson 2: Service + Queue Real-Time Messaging Discovery Lab\n")

        self.typewriter_print("Transform from a code writer who hard-wires every sender")
        self.typewriter_print("to a system thinker who knows when a Queue belongs in between.")

        self.student_name = input("\n\n👤 What's your name? ").strip() or "Student"
        self.typewriter_print(f"\nWelcome, {self.student_name}! Let's discover the pattern together.")

        self.print_info("""
You're about to feel, not just read about, why every real-time messaging
platform sits a Queue between the sender and the receiver.

You'll run three experiments:
1. Direct delivery vs Queue-routed delivery: who waits for whom
2. Fanout: one writer, many subscribers, and where the cost lands
3. Backpressure: what happens when consumers cannot keep up

After each experiment you'll answer three reflection questions with
immediate educational feedback. Wrong answers teach as much as right ones.
""")
        self.wait_for_enter("Ready to discover? Press ENTER to begin!")

    # =======================================================================
    # EXPERIMENT 1: Direct connection vs Queue-routed delivery
    # =======================================================================

    def experiment_1_direct_vs_queue(self):
        self.print_experiment("1 - DIRECT DELIVERY vs QUEUE-ROUTED DELIVERY")

        self.print_info("""
Alice wants to send a message to Bob. The simplest shape is: Alice's
Service calls Bob's Service directly and waits for an acknowledgment.
That's a point-to-point synchronous call. It feels obvious, and it works
until Bob is slow, or Bob is offline, or Bob is one of a thousand Bobs.

You'll measure two things:
1. How long Alice's send call takes (her response time)
2. What happens to Alice when Bob's Service is briefly unavailable

Then you'll do the same workload, but with a Queue in between. Alice
writes the message to the Queue and returns. Bob's Service drains the
Queue at its own pace. Watch how Alice's experience changes.
""")
        self.wait_for_enter()

        # -------------------------------------------------------------------
        # PART A: Direct delivery (Alice's Service calls Bob's Service)
        # -------------------------------------------------------------------
        self.print_header("Part A: Direct Service-to-Service Delivery", style="sub")

        bob_service = Service("bob_service")
        bob_inbox = []  # what Bob has received
        bob_is_down = {"down": False}  # mutable flag we toggle mid-experiment

        @bob_service.route("/receive")
        def bob_receive(data):
            if bob_is_down["down"]:
                # Simulate Bob being offline: long timeout, then failure
                time.sleep(2.0)
                raise Exception("Bob's Service is unreachable")
            # Simulate normal processing time for Bob (network + work)
            time.sleep(0.05)
            bob_inbox.append(data["text"])
            return {"delivered": True}

        alice_service = Service("alice_service")

        @alice_service.route("/send_direct")
        def alice_send_direct(data):
            # Alice synchronously calls Bob. Alice cannot return until Bob does.
            response = bob_service.handle_request("/receive", data={"text": data["text"]})
            return {"alice_status": "done", "bob_response": response}

        self.typewriter_print("\n🚀 Sending 10 messages directly from Alice's Service to Bob's...\n")
        direct_send_times = []
        start_time = time.perf_counter()

        for i in range(10):
            t0 = time.perf_counter()
            alice_service.handle_request("/send_direct", data={"text": f"hello from Alice #{i+1}"})
            direct_send_times.append(time.perf_counter() - t0)

        avg_direct = (sum(direct_send_times) / len(direct_send_times)) * 1000
        self.typewriter_print(
            f"📊 Direct path: average Alice send latency = {avg_direct:.0f}ms per message",
            speed=self.fast_typewriter_speed,
        )
        self.typewriter_print(
            f"   Bob received {len(bob_inbox)}/10 messages.",
            speed=self.fast_typewriter_speed,
        )

        # Now Bob's Service goes down for a moment
        self.typewriter_print("\n💥 Simulating Bob's Service going offline for the next 3 sends...")
        bob_is_down["down"] = True

        direct_outage_times = []
        direct_failures = 0
        for i in range(3):
            t0 = time.perf_counter()
            response = alice_service.handle_request("/send_direct",
                                                   data={"text": f"during outage #{i+1}"})
            direct_outage_times.append(time.perf_counter() - t0)
            # alice_service.handle_request wraps the inner exception into a 500 response
            if response.get("status") != 200:
                direct_failures += 1

        bob_is_down["down"] = False
        avg_outage = (sum(direct_outage_times) / len(direct_outage_times)) * 1000
        self.typewriter_print(
            f"📊 During Bob's outage: Alice's send latency jumped to {avg_outage:.0f}ms "
            f"per message, and {direct_failures}/3 attempts failed.",
            speed=self.fast_typewriter_speed,
        )
        self.print_warning(
            "Alice is coupled to Bob's availability. When Bob is slow or down, "
            "Alice feels it directly."
        )

        # -------------------------------------------------------------------
        # PART B: Queue-routed delivery (Alice writes to Queue, Bob subscribes)
        # -------------------------------------------------------------------
        self.print_header("Part B: Queue-Routed Delivery", style="sub")

        bob_inbox_queued = []
        bob_is_down["down"] = False

        message_queue = Queue("alice_to_bob_queue")

        @message_queue.subscriber("chat_message")
        def bob_subscriber(message):
            # Bob's subscriber drains the Queue. If Bob is down, the message
            # stays in the Queue until Bob comes back online and the
            # subscriber resumes draining. Either way, Alice has already
            # walked away.
            if bob_is_down["down"]:
                raise Exception("Bob is offline, message stays in queue")
            time.sleep(0.05)
            bob_inbox_queued.append(message["text"])

        @alice_service.route("/send_via_queue")
        def alice_send_via_queue(data):
            # Alice writes once. She does not wait for Bob.
            message_queue.enqueue({"text": data["text"]}, message_type="chat_message")
            return {"alice_status": "done"}

        # Let the subscriber register cleanly before we start writing
        time.sleep(0.1)

        self.typewriter_print("\n🚀 Sending 10 messages via the Queue...\n")
        queued_send_times = []

        for i in range(10):
            t0 = time.perf_counter()
            alice_service.handle_request("/send_via_queue",
                                         data={"text": f"queued hello #{i+1}"})
            queued_send_times.append(time.perf_counter() - t0)

        avg_queued = (sum(queued_send_times) / len(queued_send_times)) * 1000

        # Wait briefly for the Queue's dispatcher to deliver the messages
        time.sleep(1.0)

        self.typewriter_print(
            f"📊 Queue path: average Alice send latency = {avg_queued:.1f}ms per message",
            speed=self.fast_typewriter_speed,
        )
        self.typewriter_print(
            f"   Bob received {len(bob_inbox_queued)}/10 messages (asynchronously).",
            speed=self.fast_typewriter_speed,
        )

        # Outage with the Queue in between
        self.typewriter_print("\n💥 Simulating Bob going offline for 3 more sends...")
        bob_is_down["down"] = True

        queue_outage_times = []
        for i in range(3):
            t0 = time.perf_counter()
            alice_service.handle_request("/send_via_queue",
                                         data={"text": f"queued during outage #{i+1}"})
            queue_outage_times.append(time.perf_counter() - t0)

        avg_queue_outage = (sum(queue_outage_times) / len(queue_outage_times)) * 1000
        self.typewriter_print(
            f"📊 During Bob's outage: Alice's send latency = {avg_queue_outage:.1f}ms "
            f"per message (unchanged). Messages are sitting in the Queue.",
            speed=self.fast_typewriter_speed,
        )

        # Bring Bob back; the Queue keeps trying to dispatch
        bob_is_down["down"] = False
        time.sleep(1.0)

        message_queue.stop()

        self.experiment_times['experiment_1'] = time.perf_counter() - start_time

        self.print_result(
            f"Direct send avg: {avg_direct:.0f}ms. Queued send avg: {avg_queued:.1f}ms. "
            f"Alice's return time dropped by roughly {avg_direct / max(avg_queued, 0.1):.0f}x "
            f"once the Queue absorbed Bob's processing time."
        )

        # -------------------------------------------------------------------
        # Reflection questions
        # -------------------------------------------------------------------
        self.print_header("EXPERIMENT 1 REFLECTIONS", style="sub")

        self.ask_multiple_choice(
            "Why did Alice's send latency drop so dramatically when you added the Queue?",
            [
                "Because Alice no longer waits for Bob's Service to finish processing. She just writes to the Queue and returns.",
                "Because the Queue made Bob's Service faster.",
                "Because the Queue compressed the messages so they sent quicker over the network.",
            ],
            [
                "Exactly right. The Queue decouples Alice from Bob in time. Alice's job ends the moment the message lands in the Queue. Bob's processing time stops counting toward Alice's response time, no matter how slow Bob is.",
                "Bob's Service is doing the same work either way. It still takes the same 50ms per message to handle the delivery. The Queue did not speed Bob up. It just stopped Alice from having to wait for him.",
                "There is no compression involved. The message bytes are identical. The win is purely structural: Alice writes once to a local Queue and returns, instead of holding open a connection to Bob while he works.",
            ],
            correct_index=0,
        )

        self.ask_multiple_choice(
            "When Bob's Service went offline, what happened to Alice in each delivery shape?",
            [
                "Direct: Alice's calls slowed and failed. Queued: Alice's calls stayed fast and the messages waited in the Queue for Bob.",
                "Direct and Queued both failed because if Bob is offline, no message gets through.",
                "Direct stayed fast because Alice gave up immediately. Queued got slow because the Queue had to retry.",
            ],
            [
                "Right. This is the second piece of decoupling: availability decoupling. With direct delivery, Bob being down is Alice's problem. With the Queue, Bob being down is the Queue's problem. Messages persist in the Queue until Bob recovers and his subscriber drains them.",
                "Queue-routed delivery does not lose messages when Bob is offline. The Queue holds them. That is the entire reason real chat apps survive when phones go through tunnels: the Queue keeps the message until the recipient comes back online.",
                "Direct delivery did not stay fast. Alice's calls slowed to a 2-second timeout because she was waiting on Bob. With the Queue, Alice's writes stayed fast and the Queue handled the unreachable subscriber on her behalf.",
            ],
            correct_index=0,
        )

        self.ask_multiple_choice(
            "Which kinds of decoupling does the Queue give you between Alice and Bob?",
            [
                "Time decoupling, speed decoupling, and identity decoupling. Alice does not wait, does not slow down to Bob's pace, and does not need to know who Bob is.",
                "Only time decoupling. Alice still needs to know Bob exists, and she still slows down when Bob is slow.",
                "None really. The Queue is just a buffer that delays the message slightly before it goes through the same path.",
            ],
            [
                "Exactly. The Queue does three jobs at once. Time: Alice does not wait for Bob. Speed: Alice's throughput is not capped by Bob's processing rate. Identity: Alice publishes to a channel, not to a person. New recipients can subscribe later without Alice changing a line of code.",
                "Speed and identity decoupling are real and observable in what you just ran. Alice's latency did not depend on Bob's processing time. Alice never had to call Bob by name. The Queue is the meeting point that hides Bob's existence from Alice.",
                "The Queue is not a delay. It is the contract that lets sender and receiver change independently. Without it, every chat product would need its sender to know every receiver's address and availability in real time. The pattern only scales because of the Queue in between.",
            ],
            correct_index=0,
        )

        if self.ask_yes_no("Ready to see what happens when one writer has many subscribers?"):
            self.experiment_2_fanout()

    # =======================================================================
    # EXPERIMENT 2: Fanout - one writer, many subscribers
    # =======================================================================

    def experiment_2_fanout(self):
        self.print_experiment("2 - FANOUT (ONE WRITER, MANY SUBSCRIBERS)")

        self.print_info("""
A real chat channel does not have one Bob. It has every member of the
channel. A real social media post does not have one follower. It has
thousands. The shape changes when the audience grows.

You'll write a single message and deliver it to 1 subscriber, then 10,
then 100. Two paths:

Direct fanout: Alice's Service loops through every recipient and pushes
the message individually. Cost scales linearly with audience size.

Queue fanout: Alice writes once. The Queue dispatches to every
subscriber. Alice's cost is constant.

Watch what happens to Alice's send time as the audience grows.
""")
        self.wait_for_enter()

        start_time = time.perf_counter()
        audience_sizes = [1, 10, 100]

        # -------------------------------------------------------------------
        # PART A: Direct fanout
        # -------------------------------------------------------------------
        self.print_header("Part A: Direct Fanout (sender pushes to each recipient)",
                          style="sub")

        direct_results = {}

        for size in audience_sizes:
            # Build N recipient Services. Each one is a fake Bob.
            recipients = []
            inboxes = []
            for i in range(size):
                inbox = []
                inboxes.append(inbox)
                rcv = Service(f"recipient_{i}")

                # Closure captures the inbox for this specific recipient
                def make_handler(target_inbox):
                    def handler(data):
                        time.sleep(0.005)  # 5ms per recipient: small, realistic
                        target_inbox.append(data["text"])
                        return {"delivered": True}
                    return handler

                rcv.route("/receive")(make_handler(inbox))
                recipients.append(rcv)

            # Alice loops and pushes
            alice = Service(f"alice_direct_{size}")

            @alice.route("/broadcast")
            def alice_broadcast(data):
                # Walk every recipient, push individually, wait for each.
                for rcv in recipients:
                    rcv.handle_request("/receive", data={"text": data["text"]})
                return {"delivered_to": len(recipients)}

            t0 = time.perf_counter()
            alice.handle_request("/broadcast", data={"text": "hi everyone"})
            elapsed = time.perf_counter() - t0

            received_count = sum(1 for ib in inboxes if ib)
            direct_results[size] = {
                "send_time_ms": elapsed * 1000,
                "received": received_count,
            }

            self.typewriter_print(
                f"📊 Direct fanout to {size:>3} recipients: "
                f"Alice's send took {elapsed*1000:.0f}ms, "
                f"{received_count}/{size} delivered.",
                speed=self.fast_typewriter_speed,
            )

        # -------------------------------------------------------------------
        # PART B: Queue fanout
        # -------------------------------------------------------------------
        self.print_header("Part B: Queue Fanout (sender writes once, Queue dispatches)",
                          style="sub")

        queue_results = {}

        for size in audience_sizes:
            inboxes = []

            # Each recipient subscribes to a shared channel Queue.
            # We use one Queue per audience size to keep the experiment clean.
            channel = Queue(f"channel_queue_{size}", max_size=10000)

            # The Queue building block delivers to ONE registered subscriber per
            # message_type. To simulate fanout we use a Worker that processes a
            # job per recipient. The architectural shape (one write, many deliveries
            # downstream) is the same as a real pub/sub broker.
            fanout_worker = Worker(f"fanout_worker_{size}", max_concurrent_jobs=size)

            for i in range(size):
                inbox = []
                inboxes.append(inbox)

                def make_job(target_inbox):
                    def deliver(data):
                        time.sleep(0.005)
                        target_inbox.append(data["text"])
                        return {"delivered": True}
                    return deliver

                fanout_worker.register_job_type(f"deliver_to_{i}", make_job(inbox))

            @channel.subscriber("broadcast")
            def channel_dispatcher(message):
                # One enqueue, N parallel delivery jobs. Alice never sees this.
                for i in range(size):
                    fanout_worker.submit_job(f"deliver_to_{i}", message)

            fanout_worker.start()

            alice = Service(f"alice_queue_{size}")

            @alice.route("/broadcast")
            def alice_broadcast(data):
                # Alice writes ONCE. The Queue and Worker handle the fanout.
                channel.enqueue({"text": data["text"]}, message_type="broadcast")
                return {"alice_returned": True}

            t0 = time.perf_counter()
            alice.handle_request("/broadcast", data={"text": "hi everyone"})
            alice_return_ms = (time.perf_counter() - t0) * 1000

            # Wait for the background fanout to complete so we can confirm delivery
            deadline = time.perf_counter() + 10
            while time.perf_counter() < deadline:
                received_count = sum(1 for ib in inboxes if ib)
                if received_count >= size:
                    break
                time.sleep(0.05)

            received_count = sum(1 for ib in inboxes if ib)
            queue_results[size] = {
                "alice_return_ms": alice_return_ms,
                "received": received_count,
            }

            self.typewriter_print(
                f"📊 Queue fanout to {size:>3} recipients: "
                f"Alice returned in {alice_return_ms:.1f}ms, "
                f"{received_count}/{size} delivered in the background.",
                speed=self.fast_typewriter_speed,
            )

            fanout_worker.stop()
            channel.stop()

        # -------------------------------------------------------------------
        # Comparison
        # -------------------------------------------------------------------
        self.experiment_times['experiment_2'] = time.perf_counter() - start_time

        print()
        print("📊 Comparison: Alice's send/return time as audience grows")
        print(f"   {'Audience':<10} {'Direct (ms)':<14} {'Queue (ms)':<12} {'Ratio':<8}")
        for size in audience_sizes:
            d = direct_results[size]["send_time_ms"]
            q = queue_results[size]["alice_return_ms"]
            ratio = d / max(q, 0.1)
            print(f"   {size:<10} {d:<14.1f} {q:<12.1f} {ratio:<8.1f}x")

        self.print_result(
            "Direct fanout: Alice's cost grew linearly with audience size. "
            "Queue fanout: Alice's cost stayed flat. The Queue absorbed the fanout work."
        )

        # -------------------------------------------------------------------
        # Reflection questions
        # -------------------------------------------------------------------
        self.print_header("EXPERIMENT 2 REFLECTIONS", style="sub")

        self.ask_multiple_choice(
            "Why did Alice's direct-fanout send time grow linearly with audience size?",
            [
                "Because she had to make one push per recipient and wait for each one in turn.",
                "Because the network got slower with more recipients connected.",
                "Because more recipients means more total data, and Alice's bandwidth is the bottleneck.",
            ],
            [
                "Exactly. Alice's work in the direct shape is one HTTP call per recipient, executed sequentially. Ten recipients means ten calls. A thousand recipients means a thousand calls. The audience size has become Alice's problem, and Alice does not scale.",
                "The network is the same speed in both shapes. The bottleneck is purely structural: Alice is doing the dispatching work herself instead of delegating it to a Queue. Replace Alice's loop with a Queue write and the linear scaling disappears.",
                "Bandwidth is not the limit here. The message is tiny. The limit is that Alice's send call cannot return until she has finished pushing to every recipient. That is a serialization problem, not a bandwidth problem.",
            ],
            correct_index=0,
        )

        self.ask_multiple_choice(
            "In the Queue-fanout shape, who actually does the work of delivering to N recipients?",
            [
                "The Queue's dispatcher and the downstream Workers. Alice writes once and walks away.",
                "Alice still does the work, but the Queue makes it look faster.",
                "The recipients themselves, because they pull from Alice instead of being pushed to.",
            ],
            [
                "Right. This is the architectural property the Queue is buying you. The fanout work still has to happen, but it has moved off Alice's response path. Alice's user-perceived latency now depends on one Queue write, not on the audience size. The dispatcher and Workers absorb the scaling pressure.",
                "Alice genuinely does less work in the Queue shape. Her code does one enqueue and returns. The dispatching and delivering happens after she has already returned to her caller. That is real work reduction on Alice's path, not an illusion.",
                "Recipients do not pull from Alice in this design. They subscribe to the Queue. The Queue is the meeting point. Alice never knows who is on the other side, and the recipients never know Alice sent the message.",
            ],
            correct_index=0,
        )

        self.ask_multiple_choice(
            "What real systems use exactly this shape for fanout?",
            [
                "Slack channels, Twitter timeline fanout, YouTube live chat, Discord servers, and every push notification service.",
                "Only legacy enterprise systems with message brokers like IBM MQ.",
                "Mostly read-heavy systems like static blogs, since they have many readers.",
            ],
            [
                "Yes. Anywhere one event needs to reach many subscribers, the Queue-fanout shape shows up. The block names change (Kafka, RabbitMQ, SNS, NATS, Redis Streams), but the architectural shape is identical. Once you see it, you will see it everywhere.",
                "It is far more common than that. Modern messaging products, social platforms, IoT command and control, multiplayer games, and live dashboards all use Queue-routed fanout. The pattern is the default, not a niche.",
                "Static blogs do not need fanout because there is no event to broadcast. The Queue-fanout pattern shines for systems where a single event triggers many downstream deliveries: posts, messages, presence updates, live scoreboards.",
            ],
            correct_index=0,
        )

        if self.ask_yes_no("Ready to see what happens when consumers cannot keep up?"):
            self.experiment_3_backpressure()

    # =======================================================================
    # EXPERIMENT 3: Backpressure - slow consumers, growing queue depth
    # =======================================================================

    def experiment_3_backpressure(self):
        self.print_experiment("3 - BACKPRESSURE (WHEN CONSUMERS SLOW DOWN)")

        self.print_info("""
The Queue feels like magic in experiments 1 and 2. Senders return
instantly, audiences scale for free, and life is good. Reality, of course,
is not so kind.

In this experiment, the producer writes 100 messages per second. The
consumer can only process 10 messages per second. The Queue is bounded.
Watch what the Queue tells you about the imbalance:

- Queue depth (how many messages are waiting)
- Message age (how long the oldest message has been sitting there)
- Whether the Queue starts rejecting writes when it fills up

The Queue is not failing. The Queue is telling you the consumer needs
help. That is what backpressure is.
""")
        self.wait_for_enter()

        start_time = time.perf_counter()

        # Bounded Queue: capacity 200. At 100 in/sec and 10 out/sec, this
        # fills up fast.
        bounded_queue = Queue("backpressure_queue", max_size=200)

        # Track delivery state
        delivered = []
        message_ages = []

        # We deliberately do NOT use the auto-dispatch subscriber here, because
        # we want to manually simulate a slow consumer that processes messages
        # at a rate we control. We register a subscriber that does the slow work.

        def slow_consumer(message):
            # Slow processing: 100ms per message means a sustained throughput of
            # roughly 10 messages per second. The producer below writes ten times
            # faster, so the Queue will start backing up immediately.
            time.sleep(0.1)
            age = time.time() - message["enqueued_at"]
            message_ages.append(age)
            delivered.append(message)

        bounded_queue.register_subscriber("ticker", slow_consumer)

        # -------------------------------------------------------------------
        # Lossy mode: producer keeps writing fast, watch depth + drops
        # -------------------------------------------------------------------
        self.print_header("Part A: Producer at 100/sec, Consumer at 10/sec",
                          style="sub")

        producer_target_rate = 100  # messages per second
        producer_interval = 1.0 / producer_target_rate
        total_attempts = 300
        accepted = 0
        rejected = 0
        depth_samples = []

        self.typewriter_print(
            f"\n🚀 Producer attempting {total_attempts} messages "
            f"at {producer_target_rate}/sec into a bounded Queue (capacity 200)...\n"
        )

        producer_start = time.perf_counter()
        for i in range(total_attempts):
            ok = bounded_queue.enqueue(
                {"seq": i, "enqueued_at": time.time(), "text": f"msg_{i}"},
                message_type="ticker",
            )
            if ok:
                accepted += 1
            else:
                rejected += 1

            if i % 30 == 0:
                depth_samples.append(bounded_queue.size())

            # pace the producer
            time.sleep(producer_interval)

        producer_elapsed = time.perf_counter() - producer_start

        self.typewriter_print(
            f"\n📊 Producer finished in {producer_elapsed:.1f}s. "
            f"Accepted: {accepted}. Rejected (queue full): {rejected}.",
            speed=self.fast_typewriter_speed,
        )
        self.typewriter_print(
            f"   Queue depth samples during the run: {depth_samples}",
            speed=self.fast_typewriter_speed,
        )
        self.typewriter_print(
            f"   Current queue depth: {bounded_queue.size()} "
            f"(the consumer is still draining)",
            speed=self.fast_typewriter_speed,
        )

        # Let the consumer drain a bit so we can show message age growing
        self.typewriter_print("\n⏳ Letting the slow consumer drain for 5 more seconds...")
        time.sleep(5)

        if message_ages:
            avg_age = sum(message_ages) / len(message_ages)
            max_age = max(message_ages)
            self.typewriter_print(
                f"\n📊 So far the consumer delivered {len(delivered)} messages.",
                speed=self.fast_typewriter_speed,
            )
            self.typewriter_print(
                f"   Average message age at delivery: {avg_age:.2f}s",
                speed=self.fast_typewriter_speed,
            )
            self.typewriter_print(
                f"   Oldest delivered message age:    {max_age:.2f}s",
                speed=self.fast_typewriter_speed,
            )
            self.typewriter_print(
                f"   Queue depth still pending:       {bounded_queue.size()}",
                speed=self.fast_typewriter_speed,
            )

        self.print_warning(
            "The Queue did its job. It told you, loudly, that the consumer is "
            "too slow. The signals: rising depth, rejected writes, growing message age."
        )

        # -------------------------------------------------------------------
        # PART B: Three real responses to backpressure
        # -------------------------------------------------------------------
        self.print_header("Part B: Three Real Responses to Backpressure", style="sub")

        self.print_info("""
A senior engineer reads queue depth, rejection rate, and message age the
same way a doctor reads vital signs. The Queue is reporting a problem
upstream of itself. Three legitimate responses:

1. Add more consumers (horizontal scale): more Workers draining the
   same Queue. Each consumer still does 10/sec, but five of them do
   50/sec together.

2. Make the consumer batch: process 10 messages per call instead of one.
   Same Worker, 10x effective throughput. Cheap, but only works if your
   downstream tolerates batching.

3. Shed load deliberately: at very high overload, reject new writes
   instead of letting the Queue grow forever. The Queue going lossy is
   sometimes the right answer. Better to drop new messages than to deliver
   every message ten minutes late.

We will simulate response 1: scale the consumer pool by 5x.
""")
        self.wait_for_enter()

        scaled_queue = Queue("scaled_queue", max_size=500)
        scaled_delivered = []
        scaled_ages = []
        scaled_lock = threading.Lock()

        worker_pool = Worker("scaled_workers", max_concurrent_jobs=5)

        def scaled_job(message):
            time.sleep(0.1)
            age = time.time() - message["enqueued_at"]
            with scaled_lock:
                scaled_ages.append(age)
                scaled_delivered.append(message)
            return {"ok": True}

        worker_pool.register_job_type("scaled_deliver", scaled_job)

        @scaled_queue.subscriber("ticker")
        def scaled_dispatcher(message):
            # Hand off to the Worker pool, which has 5 concurrent slots
            worker_pool.submit_job("scaled_deliver", message)

        worker_pool.start()
        time.sleep(0.2)

        self.typewriter_print(
            f"\n🚀 Same producer load (100/sec, 300 messages) into a Queue with "
            f"5 parallel consumers...\n"
        )
        scaled_accepted = 0
        scaled_rejected = 0
        scaled_depth_samples = []
        scaled_start = time.perf_counter()
        for i in range(300):
            ok = scaled_queue.enqueue(
                {"seq": i, "enqueued_at": time.time(), "text": f"msg_{i}"},
                message_type="ticker",
            )
            if ok:
                scaled_accepted += 1
            else:
                scaled_rejected += 1
            if i % 30 == 0:
                scaled_depth_samples.append(scaled_queue.size())
            time.sleep(producer_interval)

        scaled_elapsed = time.perf_counter() - scaled_start

        # Allow drain
        self.typewriter_print("\n⏳ Draining the scaled pipeline...")
        deadline = time.perf_counter() + 10
        while time.perf_counter() < deadline:
            if len(scaled_delivered) >= scaled_accepted:
                break
            time.sleep(0.2)

        self.typewriter_print(
            f"\n📊 With 5 parallel consumers:",
            speed=self.fast_typewriter_speed,
        )
        self.typewriter_print(
            f"   Accepted: {scaled_accepted}. Rejected: {scaled_rejected}.",
            speed=self.fast_typewriter_speed,
        )
        self.typewriter_print(
            f"   Queue depth samples: {scaled_depth_samples}",
            speed=self.fast_typewriter_speed,
        )
        if scaled_ages:
            avg_age = sum(scaled_ages) / len(scaled_ages)
            max_age = max(scaled_ages)
            self.typewriter_print(
                f"   Average message age at delivery: {avg_age:.2f}s",
                speed=self.fast_typewriter_speed,
            )
            self.typewriter_print(
                f"   Oldest delivered message age:    {max_age:.2f}s",
                speed=self.fast_typewriter_speed,
            )

        self.print_result(
            "Adding more consumers drained the same producer load with far less "
            "depth growth and far younger messages at delivery. The Queue shape "
            "did not change. Only the consumer count did."
        )

        worker_pool.stop()
        scaled_queue.stop()
        bounded_queue.stop()

        self.experiment_times['experiment_3'] = time.perf_counter() - start_time

        # -------------------------------------------------------------------
        # Reflection questions
        # -------------------------------------------------------------------
        self.print_header("EXPERIMENT 3 REFLECTIONS", style="sub")

        self.ask_multiple_choice(
            "What is the Queue telling you when its depth grows and writes start being rejected?",
            [
                "The consumer cannot keep up with the producer. The Queue is signaling backpressure, not failing.",
                "The Queue is broken. You should pick a different building block.",
                "The producer is too slow. Speed up the producer to drain the Queue.",
            ],
            [
                "Exactly right. Backpressure is a signal, not a failure. The Queue is the only block in the system positioned to see the imbalance between producer rate and consumer rate. Rising depth and rejected writes are the Queue doing its job: telling you the consumer side needs more capacity.",
                "The Queue is working perfectly. It is doing the only thing it can do when the producer outruns the consumer: hold messages, and at some point refuse to take more so it does not consume unbounded memory. Switching building blocks would not change the underlying imbalance.",
                "Speeding up the producer is the opposite of the fix. The producer is already too fast for the consumer. The right responses are scaling the consumer, batching at the consumer, or accepting that some messages will be shed. The Queue is reporting reality, not creating it.",
            ],
            correct_index=0,
        )

        self.ask_multiple_choice(
            "When you added 5 parallel consumers, why did message age and queue depth drop so much?",
            [
                "Total consumer throughput grew 5x, so the consumer side could keep up with (or nearly keep up with) the producer.",
                "Because the producer slowed down automatically once it noticed multiple consumers.",
                "Because the messages got smaller when consumed in parallel.",
            ],
            [
                "Right. The producer's rate did not change. The Queue's design did not change. The only thing that changed was the consumer pool size. Five parallel consumers at 10/sec each is 50/sec, which is much closer to the 100/sec producer rate. Depth grows much more slowly, and messages spend much less time waiting.",
                "Producers do not auto-throttle in this design. The producer wrote at the same rate in both runs. The Queue absorbed the imbalance differently because the consumer side was now five times bigger.",
                "Message size is irrelevant here. The bytes are identical. What changed is how many of them can be processed in parallel on the consumer side. Parallelism on the consumer is the lever, not message size.",
            ],
            correct_index=0,
        )

        self.ask_multiple_choice(
            "When is deliberately shedding load (rejecting new messages) the right answer?",
            [
                "When delivering every message 10 minutes late is worse than delivering 90% of messages on time.",
                "Never. Losing messages is always wrong.",
                "Only when the Queue is full to the absolute limit and there is no other choice.",
            ],
            [
                "Right. This is the senior engineer's call. For some workloads (live ticker, real-time metrics, presence updates), a 10-minute-old message is worthless. Dropping new writes under extreme overload preserves recency for the messages you do deliver. For other workloads (chat, payments, audit logs) every message must be delivered, and shedding is unacceptable. The system's requirements decide.",
                "It depends on the system. For chat or financial events, yes, losing messages is wrong, and the answer is to scale consumers, add disk-backed queues, or apply backpressure all the way back to the producer. For metrics and live tickers, delivering every message late is worse than dropping some. There is no universal answer.",
                "Capacity is not the only deciding factor. Even a Queue with plenty of room left might benefit from shedding if the producer rate has overshot what downstream can ever process. Deliberate load shedding is a design choice, not a last-resort failure mode.",
            ],
            correct_index=0,
        )

        if self.ask_yes_no("Ready to see your discovery summary?"):
            self.show_summary()

    # =======================================================================
    # Summary
    # =======================================================================

    def show_summary(self):
        self.print_header("DISCOVERY SUMMARY")

        self.print_info("""
You have now experienced, not just read about, the foundational pattern
for every real-time messaging product on the planet.

What you discovered:

• Direct delivery couples senders to receivers. Alice waits for Bob. When
  Bob is slow or offline, Alice feels it directly. This breaks at any real
  scale.
• The Queue decouples sender and receiver in three ways at once: time
  (the sender does not wait), speed (the sender does not slow to match
  the receiver), and identity (the sender does not need to know who is
  listening).
• Fanout: with the Queue in the middle, one write delivers to many
  subscribers without the sender doing any extra work. The fanout cost
  moves off the sender's response path and onto the Queue plus its
  downstream Workers.
• Backpressure is the Queue telling you the consumer is too slow.
  Depth growth, rising message age, and rejected writes are signals, not
  failures. The fixes are real: add consumers, batch, or shed load
  deliberately.
""")

        print(f"\n📊 Your results:")
        print(f"   Correct answers: {self.correct_answers}/{self.total_questions}")
        if self.total_questions > 0:
            pct = (self.correct_answers / self.total_questions) * 100
            print(f"   Accuracy: {pct:.0f}%")

        print(f"\n📊 Time spent per experiment:")
        for name, t in self.experiment_times.items():
            print(f"   {name}: {t:.1f}s")

        self.print_info("""
The next three case studies (Social Media, Collaborative Documents, and
Messaging Apps) all sit on top of the pattern you just felt in your
hands. When you read those architecture diagrams, you will not be
memorizing a new shape. You will be recognizing the one you already own.

Service writes to Queue. Queue dispatches to subscribers. Subscribers
process at their own pace. That is the whole pattern. The rest is detail.
""")

    # =======================================================================
    # Entry points
    # =======================================================================

    def run_full(self):
        self.run_welcome()
        self.experiment_1_direct_vs_queue()
        self.experiment_2_fanout()
        self.experiment_3_backpressure()
        self.show_summary()

    def run_one(self, experiment_num: int):
        mapping = {
            1: self.experiment_1_direct_vs_queue,
            2: self.experiment_2_fanout,
            3: self.experiment_3_backpressure,
        }
        fn = mapping.get(experiment_num)
        if fn is None:
            print(f"Unknown experiment: {experiment_num}. Choose 1-3.")
            return
        print(f"\n  Running Experiment {experiment_num} directly...\n")
        fn()

    def run_non_interactive(self):
        """Run all experiments without prompts. Useful for CI / smoke tests."""
        # Patch the input-driven helpers so the lab can run unattended.
        self.instant_print = True

        def _auto_enter(prompt=""):
            return ""

        def _auto_yes(question):
            return True

        def _auto_mc(question, choices, responses, correct_index=0):
            # Always pick the correct answer in non-interactive mode.
            self.total_questions += 1
            self.correct_answers += 1
            return choices[correct_index]

        original_input = __builtins__.input if hasattr(__builtins__, "input") else input
        # Replace the bound methods so prompts disappear.
        self.wait_for_enter = _auto_enter
        self.ask_yes_no = _auto_yes
        self.ask_multiple_choice = _auto_mc

        # Provide a default name without prompting.
        self.student_name = "Tester"
        self.print_info("Running in non-interactive mode (--no-interactive).")
        self.experiment_1_direct_vs_queue()
        self.experiment_2_fanout()
        self.experiment_3_backpressure()
        self.show_summary()


def main():
    parser = argparse.ArgumentParser(
        description="Course 3 Lab 1: Service + Queue Real-Time Messaging Discovery"
    )
    parser.add_argument("experiment", nargs="?", type=int,
                        help="Optional experiment number (1-3) to run directly")
    parser.add_argument("--instant", action="store_true",
                        help="Disable typewriter effect (faster output)")
    parser.add_argument("--skip-typewriter", action="store_true",
                        help="Alias for --instant: disable typewriter effect")
    parser.add_argument("--no-interactive", action="store_true",
                        help="Run all experiments without prompts (for CI)")
    args = parser.parse_args()

    lab = LabExperience()
    if args.instant or args.skip_typewriter:
        lab.instant_print = True

    if args.no_interactive:
        lab.run_non_interactive()
    elif args.experiment is None:
        lab.run_full()
    else:
        lab.run_one(args.experiment)


if __name__ == "__main__":
    main()
