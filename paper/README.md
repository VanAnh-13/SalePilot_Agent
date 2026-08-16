# SalePilot — IEEE RIVF 2026 Track 2 paper package

**Track:** 2 — AI Applications  
**Venue:** IEEE-RIVF 2026, VinUniversity, Hanoi, 18–20 Dec 2026  
**CFP:** https://rivf2026.org/call-for-papers.html  
**Submit:** https://edas.info/N35414  
**Deadline (tentative):** 31 July 2026  

## Deliverable

| File | Role |
|------|------|
| `main.pdf` | **Submission draft PDF** (IEEE conference, A4, 6 pages; venue limit: 6) |
| `main.tex` | LaTeX source |
| `ref.bib` | Peer-reviewed / official primary sources (separate BibTeX database) |
| `SOURCE_LEDGER.md` | One audited DOI/proceedings row for every citation used |
| `figures/*.png` | Workflow figures embedded in the PDF |
| `figures/*.svg` | Editable figure sources |
| `artifacts/` | Frozen evaluator outputs (metrics + hashes) |
| `salepilot-anonymous-artifact.zip` | Prepared code/data supplement; upload only if the review policy permits |
| `sources/` | Audited literature notes and claim boundaries |
| `research_campaign.json` | Frozen candidate-only research anchor and budget |
| `analysis_outputs/`, `explore_outputs/` | Eval contract and scientific/comparability audit |

## Paper claim (honest scope)

This manuscript is a **system + executable evaluation protocol** paper with
same-team functional repeatability evidence:

- Stateful multi-turn need accumulation vs stateless ablation
- Constraint-aware ranking vs oracle-category popularity baseline
- Auditable identity, provenance, privacy, and tool boundaries
- Manifest-verified offline evaluator

It does **not** claim real-world recommendation efficacy, conversion lift, or SOTA over prior CRS systems. External dual-annotated benchmark (≥80 conversations) remains the next scientific gate (`docs/RIVF2026_PAPER_READINESS.md`).

## Rebuild PDF

```bash
# From paper/
~/.local/bin/tectonic -X compile main.tex --keep-logs
# RIVF requires PDF 1.6. Tectonic/XeTeX emits a PDF 1.5-compatible subset;
# changing the same-length version header declares that subset as PDF 1.6
# without rewriting fonts, text maps, or content streams.
perl -pi -e 'if ($. == 1) { s/%PDF-1\.5/%PDF-1.6/ }' main.pdf
# or, if TeX Live is installed:
# pdflatex main && bibtex main && pdflatex main && pdflatex main
```

Requirements: `main.tex`, `ref.bib`, and PNGs under `figures/`.
The source follows the IEEE conference template dated 6/27/2024; the
venue-specific `a4paper` option is retained and unused template packages are
omitted.

## Rebuild evaluation artifacts (do not hand-edit metrics)

```bash
# From repo root, with backend venv
cd backend
.venv/bin/python -m evaluation.cli \
  --json-out ../paper/artifacts/evaluation_deterministic.json \
  --markdown-out ../paper/artifacts/evaluation_deterministic.md \
  --deterministic-latency

.venv/bin/python -m evaluation.cli \
  --json-out ../paper/artifacts/evaluation_timed.json \
  --markdown-out ../paper/artifacts/evaluation_timed.md
```

Numbers in §Results must match these artifacts.

## Workflow figures

1. `system_architecture.png` — role-scoped architecture + provenance + safety boundaries
2. `request_workflow.png` — nominal turn ordering (not an atomic transaction)
3. `evaluation_workflow.png` — frozen fixtures, three systems, metrics, scope gate
4. `ranking_decision_workflow.png` — action policy + ranking pipeline (supplement; source in package)

## References policy

Every citation in `ref.bib` is drawn from audited notes in `sources/`:

- CRS / multi-agent: ACM CSUR, WSDM, KDD, RecSys, TOIS, IJCAI, ICLR, NeurIPS, COLM, ACL/EMNLP Findings
- Metrics / reproducibility: TOIS, RecSys, UMUAI, JMLR, Annals of Statistics
- Privacy / security: NIST Privacy Framework, ACM AISec

Do not replace publisher DOIs with blog posts or arXiv-only secondary summaries when a peer-reviewed version of record exists.

## Pre-submit checklist

- [ ] Confirm CFP dates/rules on rivf2026.org (still marked tentative)
- [ ] Confirm single- vs double-blind; set `\anonymousfalse` and authors if single-blind
- [ ] Replace the anonymous author block with final metadata if required
- [x] Current draft PDF = 6 pages, A4, PDF 1.6, `\documentclass[conference,a4paper]{IEEEtran}`
- [ ] Run the final submitted file through the conference's PDF checks when announced
- [x] Metrics regenerated from evaluator; hashes match fixture manifests
- [ ] Human authors attest that the AI-assistance disclosure matches actual use
- [ ] Confirm originality and no simultaneous submission
- [ ] Upload the anonymous artifact supplement or insert an allowed anonymous archive URL
- [ ] No third-party product branding the authors forbade
- [ ] Optional: archive code/data with persistent ID before camera-ready
- [ ] Present at conference if accepted (IEEE may drop non-presented papers from Xplore)

## Track 2 fit

- AI-based decision support for Vietnamese appliance consultation  
- Real-world deployment concerns: identity, provenance, privacy, tool safety  
- Explainable application layer: catalog-grounded claims and trade-offs (not model faithfulness)  
