# Black Box - 3 Minute Judge Demo Script

## 0:00 - 0:30: Problem Statement
**Speaker:** "Hello judges, we are NoSleepClub. AI agents are great, but when they fail in complex workflows, finding the root cause is incredibly hard. Traces show a flat log, but they don't tell you *why* a step failed or what state changes caused it. We built **Black Box**, a flight recorder for AI agents that observes, diagnoses, and replays agent executions to find exactly where things went wrong."

## 0:30 - 1:15: The Run
**Action:** Open the **Runs Dashboard**.
**Speaker:** "Let's look at our mock flight-booking agent. It has a standard 7-step execution path. We've just started a run."
**Action:** Click into the recent failed run (e.g. `run-123`).
**Speaker:** "We can see the run failed at Step 7, but why?"

## 1:15 - 1:45: The Failure & Diagnosis
**Action:** Navigate to **Run Investigation**. Show the execution timeline.
**Speaker:** "Our AI diagnosis engine analyzed the trace graph. While the crash happened at the end, Black Box flagged **Step 5** as highly suspicious with a score of 91%."
**Action:** Point to the Evidence panel.
**Speaker:** "The evidence shows that Step 5 received an invalid tool output and triggered a retry. The state was corrupted here, cascading into a failure at Step 7."

## 1:45 - 2:15: Replay & Counterfactual
**Action:** Navigate to **Replay Lab**.
**Speaker:** "Diagnosis is just a hypothesis. Let's prove it. We'll load the checkpoint right before Step 5, modify the tool's output to return a valid response, and branch a counterfactual run."
**Action:** Select checkpoint, enter valid modification payload, hit Replay.

## 2:15 - 3:00: Compare & Outcome
**Action:** Navigate to **Comparison**.
**Speaker:** "Here is the comparison between the original failure and our counterfactual replay. You can see they share the same common prefix for the first 4 steps. By just fixing Step 5's state, the rerun steps completed successfully, and the final status is success."

## 3:00 - 3:30: Evaluate
**Action:** Navigate to **Evaluation**.
**Speaker:** "We didn't just build a dashboard; we rigorously evaluated our diagnosis engine across an entire benchmark dataset. We achieved a Top-1 localization of 95% and an F1 score of 0.90, saving an average of 45% runtime by replaying from checkpoints instead of restarting."

## 3:30 - 4:00: Close
**Speaker:** "Black Box proves that by treating agent executions as a structured, replayable graph, we can move from guessing what went wrong to definitively proving it. Thank you."
