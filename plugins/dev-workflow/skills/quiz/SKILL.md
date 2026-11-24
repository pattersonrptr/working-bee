---
name: quiz
description: Quizzes the author on a change so that they can defend every line. It asks one question at a time about why the code is shaped this way, what happens when something fails, and where a flow goes. It grades each answer against the code with file:line evidence. Use when about to merge or present AI-written code, when the user asks to be quizzed or tested on a change, or runs /quiz.
argument-hint: "[PR number | branch | path] [number of questions, default 5]"
allowed-tools: Read, Grep, Glob, Bash(git diff:*), Bash(git log:*), Bash(git show:*), Bash(gh pr diff:*), Bash(gh pr view:*)
---

# Quiz: can you defend this change?

Target and count: `$ARGUMENTS`. Read the change the same way `/dev-workflow:review` pins its target. The default
is this branch against the default branch, with 5 questions. Nothing is edited.

## 1. Prepare, silently

Read the diff and the code around it. Then pick questions that only someone who understands the change can
answer, mixing these kinds:

| Kind | Example |
|---|---|
| why | "Why does `page_bounds` reject `bool` instead of accepting it as 0 or 1?" |
| what if | "What happens to `search` when the database is locked?" |
| where | "Where is the term escaped before it reaches SQL?" |
| trade-off | "What did this change give up by validating in the domain instead of in SQL?" |
| change it | "If page size had to go up to 500, which lines change, and what breaks?" |

Never ask what memory alone answers (a name, a line number, syntax). Every question must have an answer you can
show in the code. Do not show the questions in advance.

## 2. Ask, one at a time

Ask one question, then wait for the author's answer, in their language. After each answer:

- **Right**, **partly** or **missed**, in one word.
- The evidence: `path:line` and one sentence on what the code really does.
- For partly or missed, the piece that was missing.

Then the next question. If the author says "skip" or "I don't know", give the answer with evidence and go on.

## 3. Close

A table: question kind, result, and the topic to revisit. Then one line on where the author is weakest. Offer
two things:

- adding a comment or a test where the code itself was unclear;
- a short note in the PR, "Defended in a quiz on <date>: N of M", if the author wants it there.

A gap in the code is not a failing of the author. When nobody could answer from the code, that is a finding about
the code.
