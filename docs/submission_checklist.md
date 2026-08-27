# Submission Checklist

## Pre-Submission Verification

### ✅ Codebase Status
- [x] Results generated: 5 algorithms x 11 scenarios x 50-run Monte Carlo sweep (`results/comparison_table.csv`)
- [x] Figures created in `results/figures/` (PNG + SVG)
- [x] Statistical analysis completed (ANOVA, paired t-tests, Wilson-score convergence-rate CIs -- `src/analysis.py`)
- [x] Reproducibility tools ready (Dockerfile, Makefile)
- [ ] **Action Required**: Tag release (e.g. `v1.0.0-ieee-submission` per `CLAUDE.md`'s Open-Source Strategy) once ready to submit

Out of scope for this paper: metaheuristic (PSO) and ANN-based MPPT baselines
are explicitly reserved for Papers 2-3 of the research program -- see
`RESEARCH_PROGRAM.md`. Do not add them here.

### ✅ Documentation Status
- [x] `README.md` updated with latest results and reproduction commands
- [x] `main.tex` updated with new figures, tables, and statistical results
- [x] Cover letter draft created: `docs/cover_letter.md`
- [x] Data availability statement: `docs/data_availability.md`
- [ ] **Action Required**: `CLAUDE.md`'s Status/TODO section reflects the current checklist -- review before submission

### ✅ Manuscript Quality
- [ ] **Action Required**: Compile `main.tex` and verify PDF output
- [ ] **Action Required**: Check all figure references resolve correctly
- [ ] **Action Required**: Verify table formatting (IEEE two-column if required)
- [ ] **Action Required**: Proofread abstract and conclusion for clarity
- [ ] **Action Required**: Confirm all citations are complete and formatted

### ✅ Repository Hygiene
- [ ] **Action Required**: Push all changes to remote repository
  ```bash
  git push origin main
  git push origin v1.0.0-ieee-submission
  ```
- [ ] **Action Required**: Create GitHub Release from tag `v1.0.0-ieee-submission`
- [ ] **Action Required**: Connect repository to Zenodo for DOI generation
- [ ] **Action Required**: Verify repository is public (or set to public before submission)

### ✅ Journal-Specific Requirements
*Complete based on target journal selection:*

#### For IEEE Transactions:
- [ ] Format manuscript in IEEE two-column template
- [ ] Use IEEE bibliography style (`IEEEtran.bst`)
- [ ] Include biographies of all authors
- [ ] Limit manuscript to 8-10 pages (excluding references)
- [ ] Submit supplementary material separately if >10MB

#### For Applied Energy (Elsevier):
- [ ] Use Elsevier document class (`elsarticle`)
- [ ] Format references per journal guidelines
- [ ] Include highlights (3-5 bullet points)
- [ ] Prepare graphical abstract
- [ ] Suggest 5-6 potential reviewers

#### For Renewable Energy (Elsevier):
- [ ] Follow standard article structure
- [ ] Include nomenclature section if needed
- [ ] Ensure all equations are numbered
- [ ] Prepare cover letter emphasizing novelty

### ✅ Supplementary Materials
- [ ] Docker image built and tested locally (`make docker-build`)
- [ ] Full pipeline (`make run analyze plot`) verified on a clean environment
- [ ] Raw data files organized and documented
- [ ] README includes troubleshooting section

### ✅ Ethical Compliance
- [ ] Confirm no plagiarism (run iThenticate if available)
- [ ] Verify all co-authors have approved submission
- [ ] Disclose any conflicts of interest
- [ ] Confirm data does not violate privacy/security policies

## Post-Submission Actions

### After Submission:
- [ ] Record manuscript ID and submission date
- [ ] Set calendar reminder for follow-up (if no response in 4-6 weeks)
- [ ] Prepare response template for potential reviewer comments
- [ ] Monitor email for editor correspondence

### If Revision Requested:
- [ ] Address all reviewer comments point-by-point
- [ ] Update code/data if requested
- [ ] Prepare detailed response letter
- [ ] Resubmit within deadline

### Upon Acceptance:
- [ ] Complete copyright transfer form
- [ ] Pay publication fees (if applicable)
- [ ] Verify final proofs carefully
- [ ] Share preprint on arXiv/ResearchGate (per journal policy)
- [ ] Update Zenodo with final DOI
- [ ] Announce publication on professional networks

## Target Journal Recommendations

Based on the scope and contributions of this work, consider:

1. **IEEE Transactions on Energy Conversion** (IF: ~3.5)
   - Focus: Power electronics, renewable energy systems
   - Strength: Strong reputation in MPPT research

2. **Applied Energy** (IF: ~11.2)
   - Focus: Energy conversion, optimization, sustainability
   - Strength: High impact, broad readership

3. **Renewable Energy** (IF: ~8.7)
   - Focus: Renewable energy technologies and systems
   - Strength: Specific audience interested in PV systems

4. **Energy Conversion and Management** (IF: ~9.9)
   - Focus: Energy systems analysis and optimization
   - Strength: Interdisciplinary approach

5. **IEEE Journal of Emerging and Selected Topics in Power Electronics** (IF: ~4.5)
   - Focus: Novel power electronics applications
   - Strength: Open to innovative methodologies

## Timeline Estimate

| Task | Estimated Time |
|------|----------------|
| Final manuscript proofreading | 2-3 hours |
| Journal formatting adjustments | 1-2 hours |
| Repository push and Zenodo setup | 30 minutes |
| Cover letter customization | 1 hour |
| Submission process | 1 hour |
| **Total Preparation Time** | **~6-8 hours** |

---

**Next Immediate Action**: 
1. Choose target journal
2. Customize cover letter and format manuscript per journal guidelines
3. Push repository and generate Zenodo DOI
4. Submit!
