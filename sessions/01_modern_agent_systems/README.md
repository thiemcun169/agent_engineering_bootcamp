# Session 01 — Modern Agent Systems and Harness

## Goal
Watch modern agents complete a real task end to end and learn to read what the **harness** does around the model:
what context it loads, which tools it calls, where it asks for approval and how it checks its own work.
No code in this session.

## Setup
No code and no environment in this session. You need an account on one coding agent (Codex, Claude Code or Cursor)
and one work agent (ChatGPT or Claude).

## What you do
- **Demo A — coding agent** (Codex, Claude Code or Cursor): build a small course microsite from an empty folder, run it,
  open the preview and fix issues after feedback.
- **Demo B — work agent** (ChatGPT Work or Claude): read four sources and produce a one-page brief with citations,
  then update it after one piece of feedback.

## Demo prompts
**Demo A**: "In a new empty folder `demo-course-site/`, build from scratch a microsite for the 10-session AI Agent Engineering
program. Use the course outline I give you as the content source; create the data and every file needed. The site lists the
10 sessions by stage, filters by stage, opens the details of each session and works on desktop and mobile. Pick a light stack,
run the app, open the preview, check and fix issues before handing over."

**Demo B**: "Read the four sources provided about agents and harnesses. Write a one-page brief for beginners: what an agent is,
what the model and the harness each do, one coding-agent example and three discussion questions. Link a source for every main
point, export a file for me to review, then update it after one piece of feedback."

At one tool call, pause and ask: **what did the model decide, what did the harness do, how did the tool result change the next step?**
At the end, open the real artifact, not only the final answer.

## Observation checklist
For every item, write one piece of evidence you saw in the run (file name, tool call, test line…).

| Item | Question |
|---|---|
| Goal | What counts as done? |
| Context | Which files, pages or instructions did the agent read? |
| Tool choice | Which tool, with which arguments? |
| Feedback | How did a tool result change the next step? |
| Control | Where did it ask for approval? How can you stop or steer it? |
| Verification | How did it check its work (tests, preview, sources)? |
| Artifact | Where is the result, can you open it? |
| Continuity | Where is progress kept (plan, AGENTS.md / CLAUDE.md, session)? |

## After class
Try one agent on a real task of yours and fill the checklist. Write one sentence for your capstone:
"An agent that helps **[who]** do **[task]** from **[sources]** and produces **[artifact]**."

## References
- Anthropic — Building effective agents: https://www.anthropic.com/engineering/building-effective-agents
- LangChain — The anatomy of an agent harness: https://www.langchain.com/blog/the-anatomy-of-an-agent-harness
- Claude Code — How it works: https://code.claude.com/docs/en/how-claude-code-works
- Codex as a platform: https://developers.openai.com/blog/codex-as-a-platform
- Cursor Agent: https://cursor.com/docs/agent/overview
- Prompting (Goal, Context, Output, Boundaries): https://learn.chatgpt.com/docs/prompting
