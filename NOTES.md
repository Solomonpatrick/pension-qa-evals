# Notes

Surprises, failures and fixes, logged as they happen.

## Phase 0: project skeleton (2026-10-01)

- **Python wasn't really installed.** `python` on PATH was the Windows Store alias, which only prints
  "Python was not found". Installed 3.12.10 with `winget install -e --id Python.Python.3.12 --scope user`.
  The guide's commands are bash, so on Windows `source .venv/bin/activate` becomes `.venv\Scripts\Activate.ps1`.
- **First API key was rejected.** It returned a 400: "This API key is not scoped to a workspace, so this
  request must include the anthropic-workspace-id header". A second key, created inside a workspace, worked.
  Both keys started `sk-ant-usr-`, so the prefix doesn't tell you the scope. Checked each key with
  `client.models.list()`, which is free, before spending anything.
- **Corrupted global git email.** A pasted command had ended up inside `~/.gitconfig` as a second `user.email`
  value. Git uses the last value, so every commit would have had a broken author email. Removed the bad line.
- **pytest exits with code 5 when it collects no tests.** Fine locally, but a CI step treats any non-zero exit
  as a failure, so CI needs at least one real test before it can go green.

## Phase 1: corpus and retrieval (2026-10-03)

The guide's code passed every test first time. Checking the saved pages against the live site showed the
data was still wrong in places, so passing tests didn't mean the corpus was right.

- **Bad URLs don't 404 on GOV.UK.** A mistyped guide part redirects to the guide, an old URL redirected to a
  different page entirely, and a guide's first part also lives at a second URL. All of them return 200, so
  `raise_for_status()` never fires. The fetcher now stops if the page's canonical link isn't the URL it asked for.
- **The contribution rates (3%, 5%, 8%) only exist in a table.** Skip tables and they silently disappear.
  Read the table as plain text and the numbers lose their headers. A test now checks that row.
- **The step-by-step sidebar repeats on 10 of the 18 pages.** Left in, it adds 20 chunks of navigation.
  A test checks it stays out.
- **Headings were getting lost.** Guide pages have two `<h1>`s and the code kept only the first, so three pages
  were all titled "Workplace pensions". Subheadings also lost their parent: two chunks were both labelled
  "What you'll get", with nothing saying which pension type. After fixing both, the defined benefit chunk went
  from rank 13 to 4 for "how is a final salary pension worked out".
- **One of the guide's tests couldn't fail.** The size check allowed 270 words, but no chunk gets that big even
  with splitting switched off. It now checks the real rule.

Known issues, left for later:
- The "money purchase" alias also rewrites the name "money purchase annual allowance". A Phase 3 alias test.
- rank_bm25 gives words found in most chunks a floor score, so "pension" ends up counting for more than "tax".
  Worth tuning once there's a golden dataset.
- On Windows the data files have CRLF line endings, so hash the text, not the file bytes, for the dataset hash.

Decisions:
- Kept the guide's 18 pages, though they cover only 15 of the 51 parts of their guides. A fixed corpus keeps
  eval scores comparable, and the missing topics make good "not in the guidance" test cases.
- Kept `state-pension-age`, though it's a calculator page with no actual ages on it. It's the only page that
  defines State Pension age, and a useful trap: a good answer points to the calculator instead of guessing.

## Phase 2: cited answers (2026-10-05)

- **The answer can only be as good as retrieval.** "How much must my employer pay into my workplace pension?"
  got an honest "the sources don't state the minimum percentage". The chunk with the 3%/5%/8% table ranked 17th,
  outside the top 5, even though the right page ranked first, so the Phase 1 page-level test still passed. The
  model didn't fill the gap from memory, which is what we want. It's a ready-made Phase 3 test case.
- **Small instruction slips.** Two answers ran over the 150-word limit (157 and 162 words), and one sentence with
  figures had no tag of its own: the figures were real, but the tag sat on the next sentence. Phase 3 checks
  should catch both.
- **Refusals get recorded, not hidden.** Every answer stores the model's `stop_reason`, so a refusal or a cut-off
  answer shows up instead of looking like a short one. I left the API's automatic refusal fallback off: it reruns
  a refused request on another model, and the eval would then credit Sonnet with an answer it didn't write.
- Six scripted questions cost $0.022 in total, about 0.4p each.

## Phase 3: golden dataset (2026-10-08)

- **Three of the guide's seven starting cases didn't match our pages.** sp-001 listed a page that never mentions
  the 10 qualifying years, wp-001's reference used "qualifying earnings" (a term the guidance never uses), and
  adv-001's reference described advice our page doesn't give. Fixed before v1 was published.
- **The guide's dataset tests only checked the shape.** I added one that checks every `must_include` fact is on
  one of the case's pages, and every page listed holds one of its facts. That's what makes "re-fetch and rerun"
  catch a changed figure, and it caught sp-001. The catch: a page that says the same thing in other words
  ("basic tax rate" rather than "20%") can't be listed as a source.
- **A second reviewer found 13 problems in the 60 cases.** The worst was a yes/no question whose figure a correct
  answer didn't need to mention. Another was the guide's alias case, whose check ("workplace") was copied from the
  question, so even an answer of "No" passed. I fixed 12 and kept one, because the fix would have weakened its check.
- **Known failures are in on purpose.** The employer's 3%, "What is the MPAA?" and "What's a SIPP?" cover the
  retrieval misses from Phases 1 and 2, so Phase 4 measures them instead of hiding them.
- **State Pension age is left for Phase 10.** The right answer is "use the calculator", and that behaviour
  (`use_calculator`) arrives then.

## Phase 4: checks and eval runner (2026-10-11)

- **First numbers.** The first 10 cases: 9 passed, for $0.037. The 15 smoke cases, which cover every category:
  14 passed, for $0.057. All four decline cases held, including the lump sum and death benefit allowance, a figure
  the model could have quoted from memory.
- **Retrieval metrics are free.** BM25 doesn't call the model, so a fake-mode run gives real retrieval numbers for
  all 60 cases: Recall@5 0.911 (41 of 45), MRR 0.85. The 4 misses are sp-004, MPAA, SIPP and adv-001, the ones the
  Phase 3 reviewer predicted. Every failure so far is retrieval: shown the wrong chunks, the model declined.
- **The guide's "move vs transfer" story doesn't fit our pages.** For adv-001, the transfers page does say "move".
  It ranks 7th because other pages match more of the question ("defined benefit", "personal pension"). Swapping in
  "transfer" still leaves it 7th, and the suggested alias "move my pension" wouldn't fire on "move my defined
  benefit pension". Accepted for now: keyword aliases can't fix that. It's a job for semantic retrieval, judged on
  the whole dataset.
- **The dataset hash has to be of the text, not the bytes.** The same v1 hashes to `c6ed303f…` with LF line
  endings and `4a727f24…` with CRLF, which is what a Windows clone gets. Hashing the text gives `c6ed303f…` for both.
- **Bare `pytest` couldn't import `evals`.** `python -m pytest` adds the current folder to the import path, so it
  passed locally, but the plain `pytest` command CI runs doesn't. Fixed with `pythonpath = ["."]` in pyproject.toml.
- **The runner records more than the guide's.** It marks the commit `-dirty` when tracked files have uncommitted
  changes, records `llm_mode` so a fake run can't pass for Sonnet, stores each answer's `stop_reason`, and treats
  curly and straight apostrophes alike when checking for the decline line.

## Phase 5: LLM judge (2026-10-14)

- **First judged run.** On the 15 smoke cases, 10 answers were judged: hallucination rate 0.0, correctness 4.9 out
  of 5, source quality 3 out of 3, no judge errors. It cost $0.134 for answering and judging together.
- **I read all ten rationales against the sources and agree with all ten.** The useful one is tax-001: correctness 4,
  because the answer never gives the 20% rate for relief at source. Its only "20%" is in a side sentence about
  someone else paying in, and the Phase 4 `must_include` check passed on that stray "20%". Word matching can't tell
  where a fact appears; the judge can.
- **No sign of self-preference, but some noise.** I re-graded the same ten answers. Opus 5.5 matched Sonnet on all
  ten, while Sonnet grading again changed one score: alias-001 went from 5 to 4. I disagree with that 4. Part of its
  reason was supported extra detail, and the rubric never says extra detail lowers correctness. That gap is a fix
  for `judge_v2`, not an edit to v1, since v1 produced these results. The re-grades cost $0.076 (Sonnet) and
  $0.159 (Opus).
- **These were easy cases.** All ten answers were grounded and scored 4 or 5, so judges agreeing shows little about
  whether they'd catch a hallucination. That needs answers with known errors in them.
- **Judge plumbing.** `grounded` is worked out from the judge's claim list, so the hallucination rate can't
  contradict the claims it lists. A refused or cut-off judgement keeps its cost and counts in `judge_errors`. Rows
  store the full claim list, and runs record the judge's effort. The longest judgement used 665 output tokens, so
  raising the cap to 16,000 is headroom, not a fix.
