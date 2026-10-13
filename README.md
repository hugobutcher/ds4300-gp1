# DS4300 · Fall 2026 · Practical 1: Index It (Spotify edition)

**Due:** Nov 3, 2026 @ 11:59 pm EST. **Teams:** 3 - 4 students; teams of 5 have one extra requirement (E7).

## The scenario

You've just joined the data platform team at a music streaming startup. The product team wants four features, and each one needs an *index*: a data structure that answers a particular kind of question without scanning every track.

This isn't the first attempt. In **summer 2024**, a team of interns got this same assignment: find the best index structure for each feature and back the choice with data. They vibe coded it. They prompted an AI assistant, accepted what it produced, and moved on as soon as the tests went green. Then the summer ended, and the project has sat untouched since.

| Feature | The question it asks | Key column | Query type |
|---|---|---|---|
| **F1 Track page** | "Show me track `5SuOikwiRyPMVoIQDJUgSV`." Some links are stale, so some IDs don't exist. | `track_id` | point lookup (hits and misses) |
| **F2 Search-as-you-type** | The user has typed `lov`. Which titles start with that? | `track_name` | prefix |
| **F3 Workout mode** | "Songs between 125 and 135 BPM." | `tempo` | range |
| **F4 Catalog import** | Every night, new tracks are added. How long does that take, and does the order they arrive in matter? | any | insert / build |

The interns were supposed to recommend an index for each feature and back each recommendation with data. They never got there. The candidates they were comparing:

| Index | File | One-line idea |
|---|---|---|
| Unsorted list (baseline) | `indexes/unsorted_list.py` | No index at all: append everything, scan everything |
| Sorted list | `indexes/sorted_list.py` | Keep keys sorted; binary search |
| Hash table | `indexes/hash_table.py` | Like a Python `dict`: jump straight to a bucket |
| AVL tree | `indexes/avl_tree.py` | Self-balancing binary search tree |
| B+ tree | `indexes/bplus_tree.py` | Short, wide tree with linked leaves; what databases use |
| *Reference:* `dict` | `indexes/reference.py` | Python's built-in hash table (written in C) |
| *Reference:* `bisect` | `indexes/reference.py` | Sorted list using Python's C binary search |

The reference indexes are not candidates. They show what the same ideas cost when the code runs in C rather than Python, which is part of your analysis.

### What the interns left behind

Their handoff note, verbatim:

> "Indexes are done, all tests pass. Didn't get to most of the benchmarks, but there's one example experiment. The B+ tree is the one real databases use, so it's probably the answer for everything? Datagen is stubbed out. Good luck!"
> — Summer 2024 intern team

Here's what's actually in the repo:

- **An index library** (`indexes/`) that returns correct answers: every test in `tests/test_indexes.py` passes. Nobody ever measured how fast it is, and nobody on the team could explain all of it.
- **A synthetic data generator** (`datagen/synthetic.py`) that is only function signatures and docstrings.
- **One benchmark experiment** (`bench/experiments.py`) out of the six they planned. No results, no analysis, no recommendations.

Your team is picking up where they left off: **review their work, fix what's wrong, finish what's missing, and make the recommendations they never made.** Treat their handoff note as a set of claims to test, not facts.

> **Don't trust the interns' index code.** It contains bugs that affect performance but not correctness. Every index returns the right answers, but some are slower than they should be. We are not telling you how many bugs there are or where they are. Finding them through your data is part of the assignment (Part D).

## Getting started

You need [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine on Linux) and `git`. Everything else runs inside the container, so every team member and every grader has the same Python, packages, and settings.

```bash
make build      # build the image (once, and again if requirements.txt changes)
make data       # download the Spotify dataset into data/ (checksum verified)
make test       # run the tests; tests/test_synthetic.py fails until you finish Part B
make lab        # JupyterLab at http://127.0.0.1:8888 for your analysis
make shell      # a bash shell inside the container
```

No `make` (e.g. Windows PowerShell)? Every target in the `Makefile` is a single `docker compose run --rm app ...` command you can paste.

Your code lives on your laptop and is mounted into the container at `/project`, so edit with any editor and rerun. **Never commit `data/`**; it is git-ignored.

### The dataset

The [Spotify Tracks Dataset](https://www.kaggle.com/datasets/maharshipandya/-spotify-tracks-dataset) has 114,000 tracks across 114 genres, with 20 columns. `make data` downloads a pinned copy from the Hugging Face mirror. `loaders/spotify.py` reads it and turns any column into `(key, row_id)` pairs:

```python
from loaders.spotify import load_tracks, key_value_pairs
tracks = load_tracks()
pairs = key_value_pairs(tracks, "tempo")      # [(87.917, 0), (77.489, 1), ...]
```

Read the docstring of `loaders/spotify.py`: some of these columns behave in ways that matter for your results.

## What's in the repo

| Path | Who wrote it | Purpose |
|---|---|---|
| `indexes/` | the interns, **contains bugs** | The index library. You will fix bugs here (Part D). `reference.py` and `base.py` are fine; do not modify them. |
| `loaders/` | provided | Download and load the Spotify data |
| `bench/timing.py`, `bench/results.py` | provided | Timing and memory helpers; CSV writer that enforces the results format |
| `bench/core_suite.py` | provided, do not modify | The CORE suite every member runs for the hardware comparison (Part E) |
| `bench/experiments.py` | the interns, **you finish** | Their one experiment (`example_point_lookups`) works; the rest is up to you. |
| `datagen/synthetic.py` | the interns' stub, **you implement** | Synthetic keys and query workloads (Part B) |
| `tests/` | provided | `test_indexes.py` (correctness), `test_synthetic.py` (your generator's spec) |
| `analysis/` | **you write** | Notebook(s) for analysis and figures. `starter.ipynb` shows the basics. |
| `incident_reports/` | **you write** | One performance incident report per bug (Part D) |
| `machines.csv` | **you fill in** | One row per computer used |
| `results/timings.csv` | **generated** | All measurements; commit it |
| `report/REPORT_TEMPLATE.md` | provided | Structure for the PDF report |

## Part A: Review the interns' code

The interns couldn't explain their own code. Your team has to. You don't need to be able to write these data structures from scratch, but you do need to understand the code well enough to explain it. Read `indexes/base.py` first, then each index. Your report answers these questions, citing file and line numbers:

1. For each index, what work does `search` do as the number of keys *n* grows? Give the expected big-O, and say which lines do the work.
2. Why can't the hash table answer a range query without looking at every key?
3. Trace inserting the keys `10, 20, 30` (in that order) into an empty AVL tree. Which rotation runs, at which line, and what does the tree look like afterwards?
4. In the B+ tree, what is `next` on a leaf for, and which methods use it?
5. What does each counter in `Stats` count, for each index? Why are the counters useful when you already have timings?

## Part B: Finish the synthetic data generator

Real data is messy; synthetic data lets you change one thing at a time. The interns wrote the docstrings and stopped. Implement the five functions in `datagen/synthetic.py`:

| Function | Produces |
|---|---|
| `random_keys(n, length, alphabet, seed)` | *n* distinct random strings |
| `arrange(keys, order, seed)` | the keys in `random`, `sorted`, `reversed`, or `nearly_sorted` order |
| `point_queries(keys, n_queries, hit_rate, seed)` | lookups where an exact fraction hit and the rest miss |
| `range_queries(keys, n_queries, selectivity, seed)` | ranges covering an exact fraction of the distinct keys |
| `prefix_queries(keys, n_queries, prefix_length, seed)` | prefixes guaranteed to match something |

The docstrings are the spec; `tests/test_synthetic.py` checks it. All randomness must come from `random.Random(seed)` so experiments are reproducible. Each function is about 5–15 lines.

## Part C: Run the experiments they never ran

Add your experiments to `bench/experiments.py`, following the interns' `example_point_lookups`, and run them with:

```bash
make experiments MEMBER=alice MACHINE=alice-mbp            # all registered experiments
make experiments MEMBER=alice MACHINE=alice-mbp ONLY=E3_range   # just one
```

Every measurement goes to `results/timings.csv` through `ResultsWriter`, which checks the row format (see [Results format](#results-format)). **Name each experiment starting with its ID**, e.g. `E3_range_tempo`. Run every configuration at least **5 times** (`REPS=5`, the default).

Required experiments (all five main indexes plus both references unless noted):

| ID | Question | Minimum design |
|---|---|---|
| **E1** | How does build cost grow with *n*? How much memory does each index use? | `track_id` in file order; at least 6 sizes from 1,000 to 114,000; record `memory_bytes` |
| **E2** | How does point-lookup cost grow with *n*, for hits and for misses? | `track_id`; the same sizes as E1; `point_queries` with hit rates 1.0 and 0.0 |
| **E3** | How does range-query cost depend on how much of the data the range covers? | `tempo`, all 114k rows; selectivities 0.0001, 0.001, 0.01, 0.05, 0.1, 0.25 |
| **E4** | How does prefix-search cost depend on prefix length? | `track_name`; prefix lengths 1 through 5 |
| **E5** | Does the order keys arrive in matter? | Synthetic keys from `random_keys`, at least 3 sizes up to 100,000; all four `arrange` orders. Record build time, lookup time, `height`, rotations and splits. |
| **E6** | What B+ tree order is best, and does the answer depend on the operation? | `bplus_tree` only; orders 3, 4, 8, 16, 32, 64, 128, 256, 512; build, point lookups (E2 design), and ranges (E3 design at selectivity 0.01) |
| **E7** *(teams of 4)* | What happens when many rows share a key? | `track_genre` and `popularity` (few distinct keys) vs `track_id`: build, point lookups, and range queries on `popularity` |

Measurement rules:

- Generate keys and queries **before** you start the timer. `time_batch` and `time_build` already handle the timer and the garbage collector.
- Build a **fresh** index for each replicate of a build measurement.
- Call `index.reset_stats()` before each batch you record.
- Time **batches** (hundreds or more operations), not single operations, then divide.
- Close other heavy apps while benchmarking, and keep laptops plugged in. Note anything unusual in the `notes` column.

## Part D: Performance incident reports

"All tests pass" was where the interns stopped checking. You start there. Write one report per bug you find, in `incident_reports/INC-01.md`, `INC-02.md`, … using `incident_reports/TEMPLATE.md`. Hunt for bugs the way an analyst would:

1. **Compare to theory.** Plot each index's cost against *n* (log-log axes help). Does the slope match the big-O from Part A? Do the counters match what the code *should* do?
2. **Compare indexes that should behave alike.** If two structures have the same big-O but very different curves, find out why.
3. **Use the counters and `structure_info()`.** They are deterministic and point at *which* work is excessive.
4. **Then read the code**, with an AI assistant if you want, to find the line responsible. You must be able to explain the bug and your fix in your own words.

To fix a bug, edit the index file, run `make test` (correctness must not change), **commit**, and rerun the affected experiments. Every row records `code_version` (the git commit, with `-dirty` if `indexes/`, `datagen/` or `bench/` had uncommitted changes), so your before and after measurements stay side by side in `results/timings.csv`. Commit before every run you intend to report.

Your final recommendations (Part F) must be based on the fixed code. Also test the interns' claim that the B+ tree is "the answer for everything."

## Part E: Hardware comparison

Each team member runs the provided CORE suite on their own computer, once on the interns' original code and once after all your fixes:

```bash
make core MEMBER=alice MACHINE=alice-mbp
```

It takes a few minutes. First add a row for your computer to `machines.csv`, taking the specs from *About This Mac* / *System Information* / `lscpu`:

| Column | Example |
|---|---|
| `machine_id` | `alice-mbp` (letters, digits, `-`, `_`, `.`) |
| `member` | `alice` |
| `computer_model` | `MacBook Air 13" 2024` |
| `cpu_model` | `Apple M3` / `Intel Core i7-1360P` / `AMD Ryzen 7 7840U` |
| `cpu_cores` | `8` |
| `ram_gb` | `16` |
| `os` | `macOS 26.0` |
| `docker_cpus`, `docker_memory_gb` | from Docker Desktop → Settings → Resources |
| `power` | `plugged in` or `battery` |

Docker means everyone runs the same software (Python version, packages, settings), so differences in the CORE results come from the hardware and its load. In your report, answer:

1. Are the operation counters identical across machines for the same `code_version`? They should be. If they aren't, explain why.
2. For each index and operation, how much faster is the fastest machine than the slowest? Is that ratio the same across indexes and operations, or do some workloads benefit more from faster hardware?
3. Does the *ranking* of the indexes change from machine to machine?
4. How variable are repeated runs on each machine (e.g. coefficient of variation)? Is any machine noticeably noisier, and why might that be?
5. Using your E1 `memory_bytes`, how much RAM does each index need for the Spotify data? Could the RAM differences between your machines affect these results? At what dataset size would they start to?

Note: on macOS and Windows, Docker runs inside a Linux virtual machine. Inside the container, `cpu_count` and `mem_total_gb` describe that VM, which is why `machines.csv` records the real hardware.

## Part F: Report

Submit a PDF to Gradescope following `report/REPORT_TEMPLATE.md`. Write it as the report the interns should have delivered. Expectations for a data science course:

- **Show variability, not just averages.** Report medians with intervals or interquartile ranges across replicates.
- **Estimate how cost grows, don't eyeball it.** Fit log-log slopes, or regress against log *n*, and compare with theory.
- **Identify crossovers.** At what *n*, selectivity, or prefix length does the best index change?
- **Make a recommendation per feature (F1–F4)**, with the evidence and the trade-offs: build cost, memory, and whether the index can answer the query at all.
- Discuss what the C-backed reference indexes tell you about Python-level constant factors versus big-O.

## Results format

`ResultsWriter` writes one row per timed batch to `results/timings.csv`. You supply:

| Column | Meaning |
|---|---|
| `experiment` | `CORE`, or your experiment name starting with its ID (`E3_range_tempo`) |
| `dataset` | `spotify` or `synthetic` |
| `key_column` | Spotify column, or a label for synthetic keys |
| `insert_order` | `file`, `random`, `sorted`, `reversed`, `nearly_sorted` |
| `n_keys` | (key, value) pairs inserted |
| `operation` | `build`, `point_hit`, `point_miss`, `point_mixed`, `range`, `prefix` |
| `operation_param` | hit rate, selectivity, or prefix length (blank for builds) |
| `n_ops` | operations in the batch (= `n_keys` for builds) |
| `rep` | replicate number |
| `total_ns` | elapsed nanoseconds for the batch |
| `height`, `memory_bytes`, `notes` | optional |

Filled in automatically: `session_id`, `timestamp_utc`, `member`, `machine_id`, `code_version`, `python_version`, `os`, `arch`, `cpu_model_detected`, `cpu_count`, `mem_total_gb`, `in_docker`, `pythonhashseed`, `index_type`, `index_param`, and the counters `comparisons`, `nodes_visited`, `rotations`, `splits`, `resizes` (blank for the reference indexes).

## Deliverables

1. **GitHub repository** (GitHub Classroom) containing:
   - your `datagen/synthetic.py`, `bench/experiments.py`, and bug fixes in `indexes/`
   - `results/timings.csv`: every measurement, including CORE runs from every member before and after your fixes
   - `machines.csv`
   - `incident_reports/INC-*.md`
   - `analysis/`: the notebook(s) that produce every figure and table in your report
2. **PDF report** on Gradescope. (structure and format forthcoming)

Before submitting, run `make check`. It runs the tests and checks that the results file, machines, CORE runs, required experiments, and incident reports are all present and well formed. Graders run the same command.

## Working on the Project

One team member will need to create a new repo based on this template repo.  Then add your team members as collaborators.  Add Dr. Fontenot (MarkFontenot on Github) as a collaborator.  We will send out info for how TAs will access your code. 

## Rules

- I expect you to fully understand, line by line, and *be able to explain in person* anything you submit with your name on it.
  - What does this mean for coding assistants and LLMs? Used well, they are great tools for understanding material and for help with coding and debugging. Blindly pasting assistant output is no more acceptable than pasting code from GitHub or a textbook. If you can't explain it, don't submit it.
  - If you're struggling to understand code you found or that an assistant produced, ask me or a TA. We're glad to help.
- Do not modify `indexes/base.py`, `indexes/reference.py`, `bench/core_suite.py`, `bench/timing.py`, `bench/results.py`, or the tests. Fixing bugs means changing code in the five index files.
- All measurements must be taken inside the provided Docker container.
