url: https://docs.example.test/langgraph/persistence
title: LangGraph persistence (fake class copy)

# LangGraph persistence

> Fake teaching copy written for the Session 08 lab. It paraphrases the LangGraph persistence docs and is not the official page.

LangGraph can save the state of a graph after every step. The saved snapshot is called a **checkpoint**. A checkpointer is the object that stores checkpoints.

## Threads
Every run that should remember earlier steps needs a `thread_id` in the config: `{"configurable": {"thread_id": "brief-1"}}`. All checkpoints of one conversation share the thread id. A new thread id starts from an empty state.

## Checkpointers
- `InMemorySaver` keeps checkpoints in process memory. Use it for tests and notebooks.
- `SqliteSaver` (package `langgraph-checkpoint-sqlite`) stores checkpoints in a SQLite file and survives a restart.
- `PostgresSaver` is the production choice for many workers.
Pass the checkpointer when you compile the graph or when you call `create_agent(..., checkpointer=saver)`.

## Reading state
`graph.get_state(config)` returns the latest snapshot. `graph.get_state_history(config)` lists earlier checkpoints, newest first. You can resume or fork from any checkpoint, which is how human-in-the-loop `interrupt` works: the graph stops, the checkpoint keeps the state, and a later call with `Command(resume=...)` continues.

## What persistence is not
A checkpointer stores the **thread** state. Long-term facts that must be shared between threads (user preferences, profiles) belong in a store, not in a checkpoint.
