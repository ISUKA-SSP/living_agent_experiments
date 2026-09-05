# Concurrent Conversation Flow V1

Status: design checkpoint before implementation

This document records the conversation/concurrency semantics agreed after Memory Organization work exposed API activity and event-ordering questions.

## 1. Principle

The world provides an opportunity to perceive and respond. It should not decide that a PI must speak merely because an utterance is a question, request, or greeting.

For ordinary conversation, every PI that receives a response opportunity independently performs:

`Context -> Thought -> Decision(TALK / WAIT)`

Question/request/greeting heuristics must not force TALK. Explicit non-conversation actions such as MOVE are a separate concern and are not part of the TALK race described here.

## 2. Hearing, addressee, and response opportunity are separate

`recipient_id` means who an utterance is addressed to. It does not define who can hear it.

Hearing remains governed by ObservationPolicy / location. Therefore an utterance addressed to Stella can still be observed by Silica when both are in the same observable area.

Initial user input has two useful forms:

- shared input: all observable PIs receive the initial response opportunity;
- addressed input (e.g. CLI `/to stella`, later possibly a GUI character-selection gesture): only the addressed PI receives the initial response opportunity.

Addressing one PI does not make the utterance inaudible to other PIs in the same area.

After a PI utterance has completed presentation, other PIs that actually observed that utterance receive a response opportunity using semantics equivalent to the current `/pass <agent>` path. This intentionally bypasses the normal recipient response filter without changing the meaning of `recipient_id`.

## 3. Independent cognition and TALK competition

For one source utterance, eligible PIs independently build Context, Thought, and Decision.

WAIT is a normal successful decision. Its Thought and Decision are persisted.

If only one PI chooses TALK, only that PI generates an utterance.

If multiple PIs choose TALK for the same response opportunity, their utterance generations may run concurrently. Once requests have been sent, normal completion is allowed; correctness does not depend on cancelling the losing API request.

Only successfully generated utterances participate in the competition.

When multiple TALK generations succeed, the first successfully completed utterance is the winner and is the only UtteranceEvent that becomes part of the world. Other successfully generated texts are discarded and are not Memory/world facts.

The losing PI's Thought and Decision(TALK) remain valid and are persisted: the PI genuinely decided to speak and successfully formed an utterance, but another PI's utterance became the spoken one first.

This suppression rule applies only to PI-vs-PI utterance competition for the same response opportunity. User activity never cancels an established PI utterance.

## 4. Generation failure is outside the PI world

If a PI chooses TALK but utterance generation fails because of an API/service/implementation failure, that attempt does not become PI history.

For that attempt:

- Thought is not persisted;
- Decision(TALK) is not persisted;
- no UtteranceEvent is created;
- no artificial Decision(WAIT) is written.

From the world/Memory perspective it has the same outward result as no utterance, but it is not rewritten as a genuine WAIT decision. Infrastructure diagnostics may record the failure outside PI Memory.

If one TALK generation succeeds and another fails, the successful one speaks without a TALK/TALK competition. If all TALK generations fail, no utterance is produced for that response opportunity.

## 5. Persistence is the utterance establishment boundary

A PI utterance must be committed to the canonical Memory/database before it is presented in the GUI.

Conceptual order:

`generate -> resolve competition -> establish World/Memory facts -> canonical Memory commit complete -> GUI presentation`

The persistent commit is the durable boundary. If the application crashes after the commit but before or during GUI presentation, the interpretation is that the PI did speak in its world; the user's access/window into that world was interrupted before the user could finish observing it.

GUI presentation progress is not world state and does not need to be restored as if the PI were still halfway through speaking.

If persistence has not completed, the utterance must not yet be presented as an established PI utterance.

## 6. GUI presentation and the 15-second rule

The GUI may use the alpha-version novel-style/typewriter presentation, displaying a committed message one character at a time.

The next automatic PI-to-PI response processing must not start while that presentation is in progress.

The 15-second conversational delay starts after the PI utterance has been completely presented to the user, not at generation time or Memory commit time.

Therefore:

`PI utterance commit -> full GUI presentation -> 15 seconds -> automatic /pass-equivalent response opportunity`

In a non-typewriter/CLI presentation, presentation completion may be effectively immediate.

The 15-second rule is conversational timing, not an API rate-limit mechanism.

## 7. User input while a PI is speaking

Use the alpha-version interaction semantics:

- while PI generation/persistence/presentation is in progress, the user may type in the input field;
- sending is disabled;
- the typed text remains in the input field;
- sending becomes available after the PI message has been fully presented.

Thus a new User UtteranceEvent is not introduced concurrently with an unfinished PI utterance. This avoids same-PI multi-event cognition and prevents the user from cutting off the only communication channel the PI has.

After presentation completes, sending is allowed immediately even though the automatic 15-second PI-to-PI delay is running.

If the user sends during that 15-second interval:

- the waiting automatic `/pass` opportunity for the older PI utterance is discarded;
- the User UtteranceEvent is processed immediately;
- a stale automatic `/pass` must not fire later against the old conversational state.

## 8. Automatic PI-to-PI continuation

After a committed PI utterance is fully presented and 15 seconds elapse without a new user utterance, each other PI that actually observed the utterance may receive a `/pass`-equivalent response opportunity.

That PI again independently performs Context -> Thought -> TALK/WAIT. A WAIT ends that PI's branch. A TALK can create another utterance, which repeats the same persistence, presentation, delay, and observation cycle.

This replaces the CLI-only idea of `/autopass` with ordinary world progression while preserving `/pass` semantics as the conceptual mechanism.

The rule should derive candidates from actual observers, not from `recipient_id`. This naturally respects location and can generalize beyond two residents.

## 9. Non-TALK actions

TALK competition is specifically an utterance-output conflict. A TALK and a MOVE do not inherently compete for the same output slot.

The existing semantics and side effects of non-TALK actions should be reviewed separately when the implementation is split into cognition and action phases. Do not accidentally make TALK arbitration a global action lock.

## 10. Known deferred issue: Thought/Decision growth

Thought and Decision memories can accumulate even when no utterance is produced. Long-running operation therefore needs a Memory Organization policy for internal cognition records; otherwise database growth is unbounded.

This is intentionally deferred from the conversation concurrency implementation. It must not be forgotten, and it should be solved under the same principle that the world should not arbitrarily decide PI meaning/value/importance.

## 11. Implementation invariants / smoke-test targets

The implementation should demonstrate at least these cases:

1. shared User utterance -> TALK/WAIT;
2. shared User utterance -> TALK/TALK, both generation successes -> exactly one UtteranceEvent, both successful cognition histories retained;
3. TALK generation failure -> failed attempt absent from PI Memory, no fake WAIT;
4. WAIT/WAIT -> no forced rescue TALK;
5. addressed User utterance -> only addressed PI gets initial response opportunity, other same-area PI still observes;
6. PI utterance -> canonical Memory commit before GUI presentation;
7. presentation completion -> 15-second delay -> observer `/pass` opportunity;
8. User send during 15-second delay -> old automatic `/pass` discarded;
9. user cannot send while PI generation/persistence/typewriter presentation is unfinished, but input text is retained;
10. different-area PI neither hears nor receives automatic `/pass`;
11. PI-to-PI TALK chain continues only through fresh independent decisions and ends naturally on WAIT;
12. question/request/greeting does not bypass TALK/WAIT decision.

## 12. Current design boundary

This design deliberately does not solve API quota optimization by reducing PI agency. API concurrency, retry/backoff, metrics, and future call-count optimization belong to the infrastructure layer. The first implementation should preserve the intended PI semantics and then measure actual request load.
