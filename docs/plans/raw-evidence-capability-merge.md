# Raw evidence capability merge

Historical implementation plan. The current read policy is defined in
[explicit raw evidence reads](../design/raw-evidence-reads.md); the deep Raw search
described below has since been removed.

## Goal

Land the explicit provenance-based Trace capability and read-side measurement
support while preserving the current default exam and generated skill policy.

## Acceptance

1. Document the explicit read and default-policy boundary.
2. Assert the default exam prompt and generated skill still use the existing deep
   Raw search, while explicit Trace reads remain bounded and read-only.
3. Restore default prompt and skill rendering; keep the CLI/API capability and
   reused-store index projection.
4. Verify CLI behavior, lint, types, and full tests against current main.
5. Push the branch, confirm green CI, and merge the PR.
