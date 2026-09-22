# Simplify recall and management

## Current and target

Recall currently searches current and optional historical Memory, then deep can widen the limit and mix a separate Raw BM25 corpus into current results. Trace already reads only evidence cited by a named Memory. The target read path searches Memory only, with an explicit limit and optional vector fusion; trace remains a separate bounded evidence read.

Store already preserves replaced and deleted files for historical queries. `valid_from` and `invalid_at` define the necessary validity interval; `status` repeats the latter. The target keeps those files and intervals, derives current eligibility from `invalid_at`, and accepts legacy status on read. Current agent operations continue through Store; explicit delete and replacement are available through both adapters. Sleep keeps its proposals and caps for unattended decisions.

## Work units

1. Update read and management design contracts and acceptance tests.
2. Remove deep, Raw BM25 projection, and obsolete configuration while retaining archived sessions and bounded trace.
3. Remove stored status, migrate rebuildable indexes, and tighten direct Store operation boundaries.
4. Align CLI, MCP, skill, prompts, and README; run targeted and full checks, then commit and open one PR.
