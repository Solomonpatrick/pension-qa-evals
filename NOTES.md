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
