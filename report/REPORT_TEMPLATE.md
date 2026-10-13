# Practical 1 report: <team name>

Submit as a PDF on Gradescope. Aim for 10–15 pages of content plus appendices. Every figure needs
labeled axes with units, a caption saying what to notice, and a pointer to the notebook cell
that made it.

## 1. Executive summary (≤ 1 page)

One recommendation per feature (F1 track page, F2 search-as-you-type, F3 workout mode, F4 catalog
import), each with the single strongest piece of evidence. Name the incidents you found.

## 2. How the indexes work (Part A)

Answers to the Part A questions, citing file and line numbers. Include a table of the expected
big-O for build, point lookup, range, and prefix, per index.

## 3. Methods

- Experiments E1–E6 (and E7 if required): what you varied, what you held fixed, number of replicates.
- How you generated synthetic data and queries (Part B).
- How you summarized results: which statistic, which interval, how you estimated growth rates.
- Machines used (summarize `machines.csv`).

## 4. Results

One subsection per experiment. For each: the figure(s), the numbers that matter, how they compare
with theory, and any crossover points. Use the fixed code for this section.

## 5. Performance incidents (Part D)

A one-paragraph summary per incident with its key before/after figure. The full reports stay in
`incident_reports/`.

## 6. Hardware comparison (Part E)

Answers to the five Part E questions, using the CORE rows from every member.

## 7. Recommendations

Per feature: the recommended index, the runner-up, the trade-offs (build cost, memory, query types
it cannot serve), and what would change your answer (much larger data, a different query mix, data
on disk instead of in memory). Discuss what the reference indexes reveal.

## 8. Limitations

What your experiments cannot tell you, and what you would measure next.

## Appendix

- Team contributions: who did what.
- AI assistance: which tools, for what, and what you verified yourselves.
