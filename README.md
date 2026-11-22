# Skill extraction from job advertisements (SkillSpan): dictionary vs BERT token labelling

Exam project 4 of the Computational Linguistics course (project description: `exercises.pdf`, p. 4).
Research question: how much does a token-labelling model improve over a dictionary-based approach in extracting skills from job advertisements?

Everything reported in this repository comes from real runs; every run stores its command, seed, library versions and time (`runs/*/metrics.json`, `runs/*_meta.json`). A chronological work log is in `LOG_LAVORO.md` (Italian).

## Repository layout
```
src/01_load_data.py            load SkillSpan (JSON Lines), dataset statistics, BIO <-> span helpers
src/02_dictionary_baseline.py  dictionary baseline (train only), dev tuning; --test = final test evaluation
src/03_train_bert.py           fine-tuning for BIO token classification (one run = model, layer, lr, seed)
src/04_evaluate.py             span metrics (exact + partial) and the test report (mean/std over seeds)
src/05_error_analysis.py       boundary errors, spurious/missed spans, seen/unseen recall, 24 examples
src/06_extra_checks.py         checks on stored test predictions: per-gold boundary errors, I-tag rule, t-test and bootstrap, span length, duplicates
src/run_lr_search.sh, run_lr_probe.sh, run_final.sh   the three groups of GPU runs
src/summarize_lr_search.py     dev table of the learning-rate search
data/                          SkillSpan files copied unchanged (see data/SOURCE.txt, data/LICENSE_SkillSpan)
runs/                          per-run outputs (metrics.json, predictions)
results/                       CSV/Markdown tables and error examples
report/                        the written report (report.docx, report.pdf) and the scripts that build its figures and text from results/
```

## Install and run
Python 3.12; the GPU runs used torch 2.8.0+cu128 (not pinned in `requirements.txt`: use the CUDA build of your machine).
```bash
pip install -r requirements.txt            # plus a torch build, e.g. pip install torch
python src/01_load_data.py                 # dataset statistics -> results/dataset_stats.*
python src/02_dictionary_baseline.py       # dictionary, tuned on dev -> results/dictionary_dev*.csv
# GPU (the scripts pick cuda automatically if available, otherwise cpu):
bash src/run_lr_search.sh                  # 12 dev runs: lr 2e-5, 3e-5, 5e-5 x {bert, jobbert} x {skill, knowledge}
bash src/run_lr_probe.sh bert; bash src/run_lr_probe.sh jobbert    # extra dev probe at 7e-5
python src/summarize_lr_search.py          # -> results/lr_search_dev.csv
bash src/run_final.sh bert; bash src/run_final.sh jobbert          # 20 final runs (5 seeds), predicts test
python src/02_dictionary_baseline.py --test    # dictionary on test, with the settings chosen on dev
python src/04_evaluate.py                  # -> results/test_results_*.{csv,md}
python src/05_error_analysis.py            # -> results/error_*.{csv,md}, recall_seen_unseen.csv
python src/06_extra_checks.py              # -> results/extra_checks.csv (used by the report; needs scipy)
```
A run whose `metrics.json` already exists is skipped, so interrupted groups can be resumed. Smoke test: `python src/03_train_bert.py --model distilbert --layer skill --max_train 500 --max_dev 300 --epochs 1`.

## Experimental setup
**Data.** SkillSpan (Zhang et al., NAACL 2022), public part: sources `house` and `tech`; official train/dev/test splits. 11,543 sentences and 9,618 annotated spans (the 14.5k/12.5k of the paper include a third, non-public source). Two independent BIO layers per sentence: `Skill` and `Knowledge` (a Knowledge span can lie inside a Skill span), so each layer is a separate experiment. 67% of the training sentences contain no span. Statistics: `results/dataset_stats.md`.

| split | sentences | Skill spans | Knowledge spans |
|---|---|---|---|
| train | 4,800 | 2,221 | 2,969 |
| dev | 3,174 | 1,070 | 1,093 |
| test | 3,569 | 1,091 | 1,174 |

**Dictionary baseline.** For each layer, every span annotated in the training set becomes an entry (a sequence of tokens), together with its training "annotation rate" = times annotated as a span / times the token sequence occurs in the training text. Prediction: left-to-right scan, longest match, non-overlapping spans. Two settings are chosen on the **dev** set by exact-match F1: case handling (cased or lowercased) and a minimum annotation rate (grid: 9 values from 0 to 0.8) that removes ambiguous words such as "design". Selected: Skill cased, rate >= 0.1 (1,922 entries); Knowledge lowercased, rate >= 0.2 (1,709 entries). Both the "tuned" and the "pure" (rate 0) dictionaries are reported. An automatic check at every run asserts that no expression that appears only in the test set is in the dictionary and that every entry is annotated in the training set. The dictionary is deterministic (no seed).

**Token classification.** `AutoModelForTokenClassification` (3 labels O/B/I), one model per layer, for `google-bert/bert-base-cased` (109M parameters) and `jjzha/jobbert-base-cased` (108M; bert-base-cased further pre-trained on ~3.2M job-posting sentences). The label of a word is placed on its first sub-token; the other sub-tokens are ignored (loss and prediction); spans are rebuilt from the word-level B/I/O tags. Max length 256 sub-tokens (a few sentences are truncated; the count is stored in each `metrics.json`).

**Hyperparameters.** AdamW, batch size 16, weight decay 0.01, linear schedule with 10% warm-up, gradient clipping 1.0, mixed precision on GPU, at most 10 epochs with early stopping after 3 epochs without dev improvement; the epoch with the best dev exact-match F1 is kept. The learning rate was chosen on the dev set (1 seed) among 2e-5, 3e-5, 5e-5, plus a probe at 7e-5 with a decision rule fixed beforehand (adopt 7e-5 only if the mean dev F1 over the four configurations improves by at least 0.005 and it wins in at least three of them). **Outcome of the probe (negative result):** 7e-5 beat 5e-5 in only 1 of the 4 configurations (JobBERT Skill, +0.004 dev exact F1) and lowered the mean dev F1 by about 0.011, so the rule was not met and the learning rate stays 5e-5 for all final runs; with 7e-5 included, 5e-5 is no longer at the edge of the searched range (2e-5 to 7e-5). All 16 dev runs are in `results/lr_search_dev.csv`.

| layer | model | 5e-5 | 7e-5 |
|---|---|---|---|
| Skill | BERT-base | 0.527 | 0.514 |
| Skill | JobBERT | 0.555 | 0.560 |
| Knowledge | BERT-base | 0.604 | 0.590 |
| Knowledge | JobBERT | 0.634 | 0.611 |

(dev exact-match F1, seed 3477689.) Final runs: lr 5e-5. The batch size, epoch limit, warm-up and weight decay were set by us and not tuned.

**Seeds.** 3477689, 4213916, 8749520, 6828303, 9364029 (the seeds of the SkillSpan repository); the test set is touched only by the final runs (`--predict_test`).

**Metrics.** Span-level micro-averaged precision, recall and F1 on complete spans (exact match) per layer, also per source; secondary partial-match metric: a predicted span is correct if it overlaps at least one gold span, a gold span is found if at least one predicted span overlaps it (precision and recall therefore have different numerators). Mean and sample standard deviation over the 5 seeds for the BERT models. Per-word accuracy is not used: about 92% of the tags are `O`.

**Compute.** Rented GPU on Runpod (RTX 3090 for a smoke test, RTX 4090 for all experiments; roughly 2 USD in total, estimated), the code copied to the pod over SSH; the local PC was used only for scripts, the dictionary and the analyses.

## Declaration of external code and resources
- No code was copied from the SkillSpan repository (which uses MaChAmp); the training and evaluation code is written for this project with PyTorch and Hugging Face Transformers. From the SkillSpan repository we use the **data**, the **splits** and the **seed values** (https://github.com/kris927b/SkillSpan, commit `2ccf3de`, MIT licence).
- Libraries: PyTorch, Hugging Face Transformers, pandas, numpy, tabulate.
- Pre-trained models from the Hugging Face Hub: `google-bert/bert-base-cased`, `jjzha/jobbert-base-cased` (the SkillSpan authors' JobBERT), `distilbert/distilbert-base-cased` (debug only).
- Reference: Mike Zhang, Kristian Nørgaard Jensen, Sif Dam Sonniks, Barbara Plank. *SkillSpan: Hard and Soft Skill Extraction from English Job Postings.* NAACL 2022.

## Limitations
- Skill/Knowledge are the dataset's two layers. Following the SkillSpan paper (Zhang et al., 2022, Section 3, based on ESCO), *Knowledge* components are what is usually called hard skills (e.g. a programming language), while *Skill* components are the ability to apply knowledge to tasks and include soft skills (ESCO "attitudes"). So the mapping to the project text's "technical vs interpersonal" skills is not one-to-one: Knowledge is roughly technical, Skill mixes applied and interpersonal skills.
- The minimum annotation rate, the case handling, the training hyperparameters and the definition of partial match are our choices.
- Annotation noise (inconsistent span boundaries) caps the achievable F1; train and test differ in sentence length for the `tech` source.
- Some sentences are truncated at 256 sub-tokens.
- The learning-rate selection used a single seed.

## Results
Test set, all sources, span-level micro F1. BERT-base and JobBERT: mean ± sample standard deviation over 5 seeds (lr 5e-5, same settings); the dictionary is deterministic. Full tables (precision, recall, per source, per run): `results/test_results_summary.md`, `results/test_results_summary.csv`, `results/test_results_per_run.csv`.

| layer | system | exact F1 | partial F1 |
|---|---|---|---|
| Skill | dictionary, pure (no threshold) | 0.121 | 0.384 |
| Skill | dictionary, tuned on dev | 0.161 | 0.291 |
| Skill | BERT-base | 0.478 ± 0.015 | 0.764 ± 0.014 |
| Skill | JobBERT | 0.518 ± 0.006 | 0.799 ± 0.006 |
| Knowledge | dictionary, pure (no threshold) | 0.207 | 0.299 |
| Knowledge | dictionary, tuned on dev | 0.508 | 0.612 |
| Knowledge | BERT-base | 0.651 ± 0.005 | 0.819 ± 0.003 |
| Knowledge | JobBERT | 0.673 ± 0.012 | 0.840 ± 0.006 |

What the numbers show:
- Both token-classification models are far above the dictionary baseline (Skill 0.161 to 0.518, Knowledge 0.508 to 0.673 for JobBERT vs. the tuned dictionary).
- JobBERT is above BERT-base in both layers (Skill +0.040, Knowledge +0.021), as it was on dev. No significance test was run; the Skill gap is much larger than the standard deviation, the Knowledge gap is about two standard deviations.
- Skill is harder than Knowledge for every system. The gap between exact and partial F1 is large for the models (Skill about 0.52 vs 0.80), so much of the error concerns span boundaries.
- Per source (exact F1, JobBERT): Skill house 0.526 / tech 0.507; Knowledge house 0.594 / tech 0.710.

**Error analysis** (`results/error_taxonomy.md`, mean over seeds; `results/recall_seen_unseen.csv`; 24 side-by-side examples in `results/error_examples.md`).
- Skill, JobBERT: 1,140 predicted spans: 578 exact, 201 shorter than the gold span they overlap, 116 longer, 5 shifted, 239 with no overlap (spurious). Of the 1,091 gold spans, 210 get no overlapping prediction and 303 overlap a prediction but are never matched exactly (28%). The tuned Skill dictionary predicts 448 spans, 124 exact.
- Wrong boundaries are more often too short than too long (Skill JobBERT 201 vs 116; dictionary 87 vs 14).
- Gold spans whose text never appears as an annotated span in the training set are 84% of the Skill and 44% of the Knowledge test spans. The dictionary cannot find any of them by construction. On spans seen in training, JobBERT is on par with the dictionary (exact recall Skill 0.703 vs 0.705, Knowledge 0.858 vs 0.848) and BERT-base slightly lower (0.643, 0.820); the gain of the models comes from unseen expressions (exact recall Skill 0.445 BERT-base and 0.497 JobBERT; Knowledge 0.547 and 0.560).

Additional limitations seen in the runs: for JobBERT Skill the best epoch was 9 or 10 out of a maximum of 10, so it could improve with longer training.
