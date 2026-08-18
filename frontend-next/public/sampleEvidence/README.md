# Sample Evidence Fixtures

Synthetic placeholder files used purely for **demo and UI development** of the
assessment form's evidence upload flow.

| File | Type | Purpose |
|------|------|---------|
| `lorem-policy.pdf` | PDF (≤50 KB) | Hand-written minimal PDF containing lorem-ipsum text. Stands in for an "information security policy" document. |
| `screenshot-generic-1.png` | PNG (≤50 KB) | Solid-color banded image. Stands in for a generic configuration screenshot. |
| `screenshot-generic-2.png` | PNG (≤50 KB) | Simple geometric image. Stands in for a dashboard / monitoring screenshot. |

## Important

- **Not real evidence.** Do not present these files as compliance evidence in
  any audit or production report.
- Generated programmatically from short Node one-liners — no external
  downloads, no third-party imagery, no PII.
- Manifest exposed via [`frontend-next/src/data/sampleEvidence.js`](../../src/data/sampleEvidence.js)
  for use by later UI steps (drawer "Load sample" affordance, etc.).
- Each file is intentionally tiny (a few KB) so it loads instantly and is safe
  to commit to git.
