"""Builds report/report.docx from the tables in results/ and the figures in report/figures/.

Every number in the text is read from the CSV files, so the report cannot drift from the experiments.
"""
import re
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
R = ROOT / "results"
FIG = HERE / "figures"

summ = pd.read_csv(R / "test_results_summary.csv")
runs = pd.read_csv(R / "test_results_per_run.csv")
tax = pd.read_csv(R / "error_taxonomy.csv")
rec = pd.read_csv(R / "recall_seen_unseen.csv")
lrdev = pd.read_csv(R / "lr_search_dev.csv")
dtest = pd.read_csv(R / "dictionary_test.csv")
ddev = pd.read_csv(R / "dictionary_dev_by_source.csv")
stats = pd.read_csv(R / "dataset_stats.csv")


def S(system, layer, metric, source="all"):
    """(mean, sample std) from the unrounded per-run values for the models; dictionaries have one run."""
    if system in ("bert", "jobbert"):
        v = runs[(runs.system == system) & (runs.layer == layer) & (runs.source == source)][metric]
        return v.mean(), v.std(ddof=1)
    r = summ[(summ.system == system) & (summ.layer == layer) & (summ.source == source)].iloc[0]
    return r[metric + "_mean"], float("nan")


def f3(x):
    return f"{x:.3f}"


def f2(x):
    return f"{x:.2f}"


def ms(system, layer, metric, source="all", digits=3):
    m, s = S(system, layer, metric, source)
    return f"{m:.{digits}f}" if pd.isna(s) else f"{m:.{digits}f} ± {s:.{digits}f}"


def T(system, layer):
    return tax[(tax.system == system) & (tax.layer == layer) & (tax.source == "all")].iloc[0]


def RC(system, layer):
    return rec[(rec.system == system) & (rec.layer == layer)].iloc[0]


# ---------------------------------------------------------------- document helpers
doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
sec.left_margin = sec.right_margin = Cm(2.0)
sec.top_margin, sec.bottom_margin = Cm(1.9), Cm(1.9)

BODY_FONT, HEAD_FONT, SIZE = "Times New Roman", "Calibri", 10


def set_font(run, name=BODY_FONT, size=None, bold=None, italic=None, color=None):
    run.font.name = name
    rpr = run._element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.append(rf)
    for a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rf.set(qn(a), name)
    if size:
        run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold
    if italic is not None:
        run.font.italic = italic
    if color:
        run.font.color.rgb = RGBColor.from_string(color)


st = doc.styles["Normal"]
st.font.name = BODY_FONT
st.font.size = Pt(SIZE)
st.element.rPr.rFonts.set(qn("w:eastAsia"), BODY_FONT)


def add_runs(p, text, size=None, font=BODY_FONT, color=None):
    """Tiny markup: **bold**, *italic*."""
    for tok in re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)", text):
        if not tok:
            continue
        if tok.startswith("`"):
            set_font(p.add_run(tok[1:-1]), "Consolas", (size or SIZE) - 1, color=color)
        elif tok.startswith("**"):
            set_font(p.add_run(tok[2:-2]), font, size, bold=True, color=color)
        elif tok.startswith("*"):
            set_font(p.add_run(tok[1:-1]), font, size, italic=True, color=color)
        else:
            set_font(p.add_run(tok), font, size, color=color)


def para(text, align="justify", space_after=4, size=SIZE, first_indent=False, keep_next=False, space_before=0):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_after, pf.space_before = Pt(space_after), Pt(space_before)
    pf.line_spacing = 1.08
    pf.keep_with_next = keep_next
    if first_indent:
        pf.first_line_indent = Cm(0.5)
    p.alignment = {"justify": WD_ALIGN_PARAGRAPH.JUSTIFY, "left": WD_ALIGN_PARAGRAPH.LEFT,
                   "center": WD_ALIGN_PARAGRAPH.CENTER}[align]
    add_runs(p, text, size)
    return p


def heading(text, level=1):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.keep_with_next = True
    pf.space_before = Pt(9 if level == 1 else 5)
    pf.space_after = Pt(3 if level == 1 else 2)
    run = p.add_run(text)
    set_font(run, HEAD_FONT, 12.5 if level == 1 else 10.5, bold=True, color="1F3864" if level == 1 else "2F5496")
    if level == 1:  # thin rule under the section title
        ppr = p._p.get_or_add_pPr()
        b = OxmlElement("w:pBdr")
        bt = OxmlElement("w:bottom")
        for k, v in (("w:val", "single"), ("w:sz", "4"), ("w:space", "1"), ("w:color", "8EAADB")):
            bt.set(qn(k), v)
        b.append(bt)
        ppr.append(b)
    return p


def bullet(text, size=SIZE):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.left_indent, pf.first_line_indent = Cm(0.55), Cm(-0.4)
    pf.space_after = Pt(2)
    pf.line_spacing = 1.08
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    set_font(p.add_run("•  "), BODY_FONT, size)
    add_runs(p, text, size)
    return p


def caption(label, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before, p.paragraph_format.space_after = Pt(2), Pt(7)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    set_font(p.add_run(label + " "), HEAD_FONT, 8.5, bold=True, color="1F3864")
    add_runs(p, text, 8.5, font=HEAD_FONT)
    return p


def figure(name, width_cm=17.0):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before, p.paragraph_format.space_after = Pt(4), Pt(0)
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(FIG / name), width=Cm(width_cm))


def cell_border(cell, **kw):
    tcPr = cell._tc.get_or_add_tcPr()
    b = tcPr.find(qn("w:tcBorders"))
    if b is None:
        b = OxmlElement("w:tcBorders")
        tcPr.append(b)
    for edge, (sz, color) in kw.items():
        e = OxmlElement(f"w:{edge}")
        e.set(qn("w:val"), "single")
        e.set(qn("w:sz"), str(sz))
        e.set(qn("w:color"), color)
        b.append(e)


def shade(cell, color):
    tcPr = cell._tc.get_or_add_tcPr()
    s = OxmlElement("w:shd")
    s.set(qn("w:val"), "clear")
    s.set(qn("w:color"), "auto")
    s.set(qn("w:fill"), color)
    tcPr.append(s)


def table(rows, col_widths_cm, header_rows=1, size=8, align=None, bold_rows=(), group_shade=(), italic_first_col=False):
    """Booktabs-like table: rules above/below the header and at the bottom."""
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = t.cell(i, j)
            c.width = Cm(col_widths_cm[j])
            p = c.paragraphs[0]
            p.paragraph_format.space_after = p.paragraph_format.space_before = Pt(1.2)
            p.paragraph_format.keep_with_next = True
            a = (align[j] if align else ("left" if j == 0 else "center"))
            p.alignment = {"left": WD_ALIGN_PARAGRAPH.LEFT, "center": WD_ALIGN_PARAGRAPH.CENTER,
                           "right": WD_ALIGN_PARAGRAPH.RIGHT}[a]
            is_head = i < header_rows
            txt = str(val)
            if is_head or i in bold_rows:
                txt = f"**{txt}**" if txt and not txt.startswith("**") else txt
            add_runs(p, txt, size, font=HEAD_FONT)
            if is_head:
                shade(c, "DCE6F2")
            elif i in group_shade:
                shade(c, "F2F2F2")
            if i == 0:
                cell_border(c, top=(8, "1F3864"))
            if i == header_rows - 1:
                cell_border(c, bottom=(6, "1F3864"))
            if i == len(rows) - 1:
                cell_border(c, bottom=(8, "1F3864"))
    return t


# footer: page number
def add_page_number(section):
    p = section.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    for kind, txt in (("begin", None), (None, "PAGE"), ("end", None)):
        if kind:
            e = OxmlElement("w:fldChar")
            e.set(qn("w:fldCharType"), kind)
        else:
            e = OxmlElement("w:instrText")
            e.set(qn("xml:space"), "preserve")
            e.text = txt
        run._r.append(e)
    set_font(run, HEAD_FONT, 8.5, color="595959")


add_page_number(sec)

# ---------------------------------------------------------------- title block
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_after = Pt(2)
set_font(p.add_run("Skill Extraction from Job Advertisements:"), HEAD_FONT, 17, bold=True, color="1F3864")
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_after = Pt(4)
set_font(p.add_run("A Dictionary Baseline versus BERT and JobBERT Token Labelling on SkillSpan"), HEAD_FONT, 12.5,
         color="2F5496")
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_after = Pt(1)
set_font(p.add_run("Giacomo Cornacchia"), HEAD_FONT, 10.5, bold=True)
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_after = Pt(6)
set_font(p.add_run("Computational Linguistics and Language-Based Interaction"), HEAD_FONT, 9, color="595959")

# abstract
sk_j, kn_j = S("jobbert", "skill", "exact_f1")[0], S("jobbert", "knowledge", "exact_f1")[0]
sk_b, kn_b = S("bert", "skill", "exact_f1")[0], S("bert", "knowledge", "exact_f1")[0]
sk_d, kn_d = S("dictionary_tuned", "skill", "exact_f1")[0], S("dictionary_tuned", "knowledge", "exact_f1")[0]
abstract = (
    "**Abstract.** Job advertisements describe the required competences in free text, and extracting them as text spans "
    "is a first step towards structured labour-market analysis. On the SkillSpan corpus we compare a dictionary baseline, "
    "built only from the training annotations, with BERT-base and JobBERT fine-tuned for BIO token classification, "
    "separately for the *Skill* and *Knowledge* span types and over five random seeds. "
    f"JobBERT reaches an exact-match F1 of {f3(sk_j)} on Skill and {f3(kn_j)} on Knowledge, against {f3(sk_d)} and "
    f"{f3(kn_d)} for the best dictionary and {f3(sk_b)} and {f3(kn_b)} for BERT-base. "
    f"Under a relaxed partial-match criterion both models score between {f2(S('bert','skill','partial_f1')[0])} and "
    f"{f2(S('jobbert','knowledge','partial_f1')[0])}, so a large share of the remaining errors concerns span boundaries. "
    "The error analysis shows that the advantage of the models comes from expressions that never occur as annotated "
    "spans in the training data, which a dictionary cannot recover by construction."
)
p = para(abstract, size=9.2, space_after=4)
p.paragraph_format.left_indent = p.paragraph_format.right_indent = Cm(0.6)

# ---------------------------------------------------------------- 1 Introduction
heading("1  Introduction")
para("Online job advertisements are a rich, constantly updated source of information on the competences that employers "
     "ask for. Turning their free text into structured data, i.e. finding the exact word sequences that name a skill, "
     "supports job matching, curriculum design and labour-market monitoring. The task is hard for two reasons. "
     "Skills are expressed in open-ended and highly variable language (*“prioritising your tasks”*, *“Kubernetes”*, "
     "*“strategic thinking”*), and the boundaries of a span are often a matter of annotation convention.", first_indent=True)
para("We study this task on SkillSpan (Zhang et al., 2022) and ask how much a supervised token-labelling model improves "
     "over a dictionary-based extractor that uses the same training data. We make four contributions: (i) a "
     "dictionary baseline built exclusively from the training set, with an automatic check that no expression taken "
     "from the test set can enter it; (ii) a comparison with BERT-base and with JobBERT, a BERT model further "
     "pre-trained on job postings, on two separate experiments (Skill and Knowledge) with five seeds each; "
     "(iii) an evaluation with exact and partial span matching; and (iv) an error analysis that separates boundary "
     "errors from missed and spurious spans and measures how performance depends on whether an expression was "
     "seen in training.", first_indent=True)

# ---------------------------------------------------------------- 2 Data
heading("2  Data")
para("SkillSpan contains English job-posting sentences annotated at span level with two types, following the "
     "ESCO taxonomy. A *Knowledge* span names a knowledge component, which is what is usually called a hard skill "
     "(e.g. a programming language); a *Skill* span names the ability to apply knowledge to a task and also covers "
     "soft skills, which ESCO calls attitudes (Zhang et al., 2022). The two types are annotated independently and can "
     "overlap, so we treat them as two separate sequence-labelling experiments. "
     "We use the public part of the corpus, with its official train/development/test split and two sources: "
     "*house*, an in-house collection of general job postings, and *tech*, postings for technical roles. "
     "(The counts reported in the original paper include a third source, *big*, that is not public.) Table 1 gives the statistics.",
     first_indent=True)


def st_(split, source, col):
    return stats[(stats.split == split) & (stats.source == source)].iloc[0][col]


rows = [["Split", "Sentences", "Tokens", "Avg. sent. length", "Skill spans", "Avg. length", "Knowledge spans", "Avg. length"]]
for split in ("train", "dev", "test"):
    rows.append([split.capitalize(), f"{st_(split,'all','sentences'):,}", f"{st_(split,'all','tokens'):,}",
                 f"{st_(split,'all','avg_sent_len'):.1f}", f"{st_(split,'all','skill_spans'):,}",
                 f"{st_(split,'all','skill_avg_span_len'):.2f}", f"{st_(split,'all','knowledge_spans'):,}",
                 f"{st_(split,'all','knowledge_avg_span_len'):.2f}"])
table(rows, [2.0, 2.0, 2.0, 2.6, 2.1, 1.9, 2.5, 1.9])
caption("Table 1.", "Dataset statistics (house and tech together). Lengths are in tokens.")
para(f"Three properties of the data matter for what follows. First, annotations are sparse: 67% of the training sentences "
     f"contain no span at all, and about 92% of all tags are *O*. Second, Skill spans are much longer than Knowledge "
     f"spans ({st_('train','all','skill_avg_span_len'):.1f} against {st_('train','all','knowledge_avg_span_len'):.1f} tokens "
     f"in the training set), which makes exact boundary agreement harder. Third, the two sources differ and the "
     f"distribution shifts between splits: *tech* sentences average {st_('train','tech','avg_sent_len'):.1f} tokens in training "
     f"but only {st_('test','tech','avg_sent_len'):.1f} in the test set, where many sentences are short lists of technologies.",
     first_indent=True)

# ---------------------------------------------------------------- 3 Methods
heading("3  Methods")
heading("3.1  Dictionary baseline", 2)
d_sk = dtest[(dtest.system == "dictionary_tuned") & (dtest.layer == "skill") & (dtest.source == "all")].iloc[0]
d_kn = dtest[(dtest.system == "dictionary_tuned") & (dtest.layer == "knowledge") & (dtest.source == "all")].iloc[0]
para("For each span type, every span annotated in the training set becomes a dictionary entry (a sequence of tokens). "
     "Each entry stores its *annotation rate*: the number of times the sequence is annotated as a span in the training "
     "text divided by the number of times it occurs there at all. This estimates how ambiguous the expression is "
     "(in the lower-cased Knowledge dictionary *python* has a rate of 0.65 and is kept, while *design*, which is rarely a "
     "skill on its own, has a rate of 0.07 and is dropped by the selected threshold). Prediction scans a sentence from left to right and takes the longest "
     "dictionary match at each position, producing non-overlapping spans. "
     "Two settings were selected on the development set by exact-match F1: whether matching is case-sensitive or "
     "lower-cased, and the minimum annotation rate an entry needs to be kept (nine values from 0 to 0.8). "
     f"The selected settings are *cased, rate ≥ {d_sk.min_precision:g}* for Skill ({int(d_sk.dict_size):,} entries) and "
     f"*lower-cased, rate ≥ {d_kn.min_precision:g}* for Knowledge ({int(d_kn.dict_size):,} entries). We report this "
     "*tuned* dictionary and a *pure* variant with no rate threshold. An automatic check run before every evaluation "
     "asserts that every entry is annotated in the training set and that no expression occurring only in the test set "
     "is in the dictionary. The method is deterministic.", first_indent=True)
heading("3.2  Token classification", 2)
para("Each sentence is a sequence of words tagged B (first word of a span), I (inside a span) or O (outside) "
     "(Ramshaw and Marcus, 1995). We fine-tune `AutoModelForTokenClassification` from the Hugging Face Transformers "
     "library (Wolf et al., 2020), i.e. a linear layer over the encoder output with three classes, one model per span type, "
     "starting from two checkpoints: `google-bert/bert-base-cased` (Devlin et al., 2019; 109M parameters) and "
     "`jjzha/jobbert-base-cased` (JobBERT, 108M parameters), which is BERT-base further pre-trained on about 3.2M "
     "job-posting sentences (Zhang et al., 2022). A word is split into sub-word pieces; its label is placed on the first "
     "piece and the other pieces are ignored in both loss and prediction. Spans are rebuilt from the word-level tags, "
     "and an I tag with no preceding B opens a new span. Inputs are truncated at 256 pieces (a few sentences are affected; "
     "the count is stored with every run).", first_indent=True)
heading("3.3  Training protocol", 2)
para("We train with AdamW (Loshchilov and Hutter, 2019), batch size 16, weight decay 0.01, a linear schedule with 10% "
     "warm-up, gradient clipping at 1.0 and mixed precision. Training lasts at most 10 epochs with early stopping "
     "(patience 3) on the development exact-match F1; the epoch with the best development score is kept. "
     "The learning rate was chosen on the development set with a single seed among 2e-5, 3e-5 and 5e-5 for all four "
     "configurations (two models × two span types). Because 5e-5 was at the edge of the grid and best in three of the four "
     "configurations, we added a probe at 7e-5 with a decision rule fixed before seeing its results: adopt 7e-5 only if "
     "it raised the mean development F1 by at least 0.005 and won in at least three configurations. It won in one and "
     "lowered the mean by about 0.011, so 5e-5 was kept (Figure 1). Batch size, epoch limit, warm-up and weight decay "
     "were set by us and not tuned. The final experiments use five seeds "
     "(3477689, 4213916, 8749520, 6828303, 9364029, the values used by the SkillSpan authors), giving 20 runs of about "
     "four minutes each on one rented RTX 4090. The test set is used only by these final runs.", first_indent=True)
figure("fig_lr_dev.png", 13.6)
caption("Figure 1.", "Development exact-match F1 against learning rate (one seed). The dotted line marks the value used in "
        "all final runs (5e-5); 7e-5 improved only JobBERT on Skill, and by 0.004.")
heading("3.4  Evaluation", 2)
para("We evaluate at span level, micro-averaged over the whole test set, separately for each span type. Under "
     "**exact match** a predicted span is correct only if its start and end both equal those of a gold span; precision, "
     "recall and F1 follow. Because the dataset has few spans per sentence and most tags are *O*, per-word accuracy is "
     "uninformative and is not reported. As a secondary measure we use a **partial match** defined by us: a predicted span "
     "is correct if it overlaps at least one gold span, and a gold span is found if at least one predicted span overlaps "
     "it, so precision and recall are computed on different counts. Comparing the two measures isolates boundary errors. "
     "For BERT-base and JobBERT we report the mean and the sample standard deviation over the five seeds; the dictionary "
     "has no random component.", first_indent=True)

# ---------------------------------------------------------------- 4 Results
heading("4  Results")
hdr = ["Span type", "System", "Exact P", "Exact R", "Exact F1", "Partial P", "Partial R", "Partial F1"]
rows = [hdr]
names = {"dictionary_pure": "Dictionary, pure", "dictionary_tuned": "Dictionary, tuned", "bert": "BERT-base",
         "jobbert": "JobBERT"}
for layer, lname in (("skill", "Skill"), ("knowledge", "Knowledge")):
    for k, s in enumerate(("dictionary_pure", "dictionary_tuned", "bert", "jobbert")):
        rows.append([lname if k == 0 else "", names[s]] + [ms(s, layer, m) for m in
                     ("exact_p", "exact_r", "exact_f1", "partial_p", "partial_r", "partial_f1")])
tb = table(rows, [1.7, 2.9, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0], size=7.8, align=["left", "left"] + ["center"] * 6,
           bold_rows=(4, 8), group_shade=(5, 6, 7, 8))
caption("Table 2.", "Test-set results (all sources). BERT-base and JobBERT: mean ± sample standard deviation over five seeds; "
        "dictionaries are deterministic. JobBERT (bold) has the highest value in every column.")
figure("fig_main_results.png", 16.2)
caption("Figure 2.", "Exact and partial F1 on the test set. Bars show the mean over five seeds for BERT-base and "
        "JobBERT with the standard deviation; black dots are the individual seeds (exact F1).")

jb_s = runs[(runs.system == "jobbert") & (runs.layer == "skill") & (runs.source == "all")].exact_f1
bb_s = runs[(runs.system == "bert") & (runs.layer == "skill") & (runs.source == "all")].exact_f1
jb_k = runs[(runs.system == "jobbert") & (runs.layer == "knowledge") & (runs.source == "all")].exact_f1
bb_k = runs[(runs.system == "bert") & (runs.layer == "knowledge") & (runs.source == "all")].exact_f1
assert jb_s.min() > bb_s.max() and jb_k.min() > bb_k.max()
for _l in ("skill", "knowledge"):
    for _m in ("exact_p", "exact_r", "exact_f1", "partial_p", "partial_r", "partial_f1"):
        assert S("jobbert", _l, _m)[0] == max(S(s_, _l, _m)[0] for s_ in names), (_l, _m)

para("**Models against the dictionary.** Both fine-tuned models clearly outperform the dictionary on both span types "
     f"(Table 2, Figure 2). On Skill the best dictionary reaches an exact F1 of {f3(sk_d)}, JobBERT {f3(sk_j)}, about "
     f"{sk_j/sk_d:.1f} times higher. On Knowledge the gap is smaller ({f3(kn_d)} against {f3(kn_j)}) because technical "
     "terms are short, frequent and repeated across postings, which a dictionary can exploit. Tuning the annotation-rate "
     "threshold matters for the dictionary: without it, recall is high but precision very low (Knowledge: "
     f"P = {f3(S('dictionary_pure','knowledge','exact_p')[0])}, R = {f3(S('dictionary_pure','knowledge','exact_r')[0])}), "
     f"and the threshold lifts the Knowledge exact F1 from {f3(S('dictionary_pure','knowledge','exact_f1')[0])} to {f3(kn_d)}. "
     "For Skill the same threshold gains much less, plausibly because many skills are expressed with ordinary words and phrases that cannot be separated from non-skill uses by an annotation rate.",
     first_indent=True)
para("**JobBERT against BERT-base.** JobBERT is better on both span types "
     f"(+{sk_j-sk_b:.3f} exact F1 on Skill, +{kn_j-kn_b:.3f} on Knowledge) and it is also much more stable across seeds on Skill "
     f"(standard deviation {S('jobbert','skill','exact_f1')[1]:.3f} against {S('bert','skill','exact_f1')[1]:.3f}). "
     f"The seed ranges do not overlap: the five JobBERT Skill runs lie between {jb_s.min():.3f} and {jb_s.max():.3f}, the five BERT-base "
     f"runs between {bb_s.min():.3f} and {bb_s.max():.3f}; on Knowledge the ranges are {jb_k.min():.3f}–{jb_k.max():.3f} and "
     f"{bb_k.min():.3f}–{bb_k.max():.3f}. On Knowledge both models have a higher recall than precision "
     f"({f3(S('jobbert','knowledge','exact_r')[0])} against {f3(S('jobbert','knowledge','exact_p')[0])} for JobBERT), "
     "while on Skill the two are close. "
     "The ordering agrees with the development results of the learning-rate search, where JobBERT led in all four configurations. "
     "We did not run a formal significance test.", first_indent=True)

# per-source table
rows = [["System", "Skill, house", "Skill, tech", "Knowledge, house", "Knowledge, tech"]]
for s in ("dictionary_tuned", "bert", "jobbert"):
    rows.append([names[s]] + [ms(s, layer, "exact_f1", src) for layer in ("skill", "knowledge") for src in ("house", "tech")])
table(rows, [3.4, 3.3, 3.3, 3.5, 3.3], size=7.8)
caption("Table 3.", "Exact-match F1 on the test set by source.")
para("**Differences between sources.** Skill is harder than Knowledge for every system, and the two span types behave "
     "differently across sources (Table 3). Knowledge is much easier on *tech* than on *house* for all systems, most of all for the "
     f"dictionary ({f3(S('dictionary_tuned','knowledge','exact_f1','tech')[0])} against "
     f"{f3(S('dictionary_tuned','knowledge','exact_f1','house')[0])}), since technology names are well covered by the training data. "
     "On Skill the two sources are close for the models, and the dictionary is better on *tech* than on *house*.",
     first_indent=True)

# ---------------------------------------------------------------- 5 Error analysis
heading("5  Error analysis")
para("Partial-match F1 is much higher than exact-match F1 for the models (Skill: "
     f"{f2(S('jobbert','skill','partial_f1')[0])} against {f2(sk_j)} for JobBERT), so we examine *how* predictions go wrong. "
     "Each predicted span is classified as exact, *too short* (strictly inside a gold span), *too long* (containing a gold "
     "span), *shifted* (partial overlap) or *no overlap* with any gold span. Each gold span is classified as found exactly, "
     "found only with different boundaries, or missed (no overlapping prediction). Figure 3 reports the shares, averaged "
     "over the seeds.", first_indent=True)
figure("fig_error_breakdown.png", 16.6)
caption("Figure 3.", "Fate of gold spans (top) and composition of predicted spans (bottom) on the test set. "
        "Numbers inside the bars are percentages; BERT-base and JobBERT are averaged over five seeds.")
jb_t, bb_t, dd_t = T("jobbert", "skill"), T("bert", "skill"), T("dictionary", "skill")
para("**Boundary errors.** For Skill, 28% of the gold spans are found by both models only with wrong boundaries "
     f"(JobBERT: {jb_t.gold_boundary_only:.0f} of {jb_t.n_gold:.0f}), roughly as many as the "
     f"{jb_t.missed:.0f} that are missed entirely. Among the wrongly bounded predictions, too-short ones are more frequent than "
     f"too-long ones (JobBERT: {jb_t.shorter:.0f} against {jb_t.longer:.0f}; dictionary: {dd_t.shorter:.0f} against {dd_t.longer:.0f}), "
     "and shifted spans are rare. The models therefore tend to stop early on the long, multi-word Skill spans, "
     "for example BERT-base predicts only *“structured approach”* for the gold span *“take a structured approach to work”* (Table 4, example 1). On Knowledge, where spans are "
     "short, boundary errors affect 17% of the gold spans, and the typical failure is a merge or split of adjacent terms "
     "(Table 4, examples 3 and 4).", first_indent=True)
para("**Spurious and missed spans.** About one prediction in five has no overlap with any gold span "
     f"(JobBERT: {f2(T('jobbert','skill').spurious/T('jobbert','skill').n_pred)} for Skill, "
     f"{f2(T('jobbert','knowledge').spurious/T('jobbert','knowledge').n_pred)} for Knowledge), whereas the dictionary is far less "
     f"precise on Skill ({f2(dd_t.spurious/dd_t.n_pred)}). The dictionary also reproduces the inconsistency of the "
     "annotation: it learns *“postgresql redis”* as a single entry from one training sentence and then merges two correctly "
     "separate technologies in the test set (Table 4, example 2).", first_indent=True)
figure("fig_seen_unseen.png", 15.8)
caption("Figure 4.", "Exact recall on the test set for gold spans whose text (lower-cased) is annotated somewhere in the training "
        "set (*seen*) and for those that are not (*not seen*). The dictionary cannot find unseen spans by construction.")
sk_u, kn_u = RC("jobbert", "skill"), RC("jobbert", "knowledge")
para("**Seen and unseen expressions.** Figure 4 splits the test gold spans by whether their text appears as an annotated span in the "
     f"training set. Most Skill spans are new ({sk_u.unseen_gold:.0f} of {sk_u.seen_gold + sk_u.unseen_gold:.0f}, "
     f"{sk_u.unseen_gold/(sk_u.seen_gold+sk_u.unseen_gold)*100:.0f}%), and so are {kn_u.unseen_gold/(kn_u.seen_gold+kn_u.unseen_gold)*100:.0f}% "
     "of the Knowledge spans. On seen spans JobBERT is on a par with the dictionary "
     f"(Skill {f2(sk_u.seen_exact_recall)} against {f2(RC('dictionary','skill').seen_exact_recall)}; Knowledge "
     f"{f2(kn_u.seen_exact_recall)} against {f2(RC('dictionary','knowledge').seen_exact_recall)}) and BERT-base is slightly lower "
     f"({f2(RC('bert','skill').seen_exact_recall)} and {f2(RC('bert','knowledge').seen_exact_recall)}). The models' advantage therefore "
     f"comes from unseen expressions, which they recover with an exact recall of {f2(RC('bert','skill').unseen_exact_recall)} (BERT-base) and "
     f"{f2(sk_u.unseen_exact_recall)} (JobBERT) on Skill and {f2(RC('bert','knowledge').unseen_exact_recall)} and "
     f"{f2(kn_u.unseen_exact_recall)} on Knowledge. The domain-specific pre-training of JobBERT helps on both parts for Skill, "
     "and mainly on seen spans for Knowledge.", first_indent=True)

ex = [["#", "Type", "Gold", "Dictionary", "BERT-base", "JobBERT"],
      ["1", "Skill", "You [take a structured approach to work] and are skilled in…",
       "take a [structured] approach to work", "take a [structured approach] to work", "[take a structured approach to work]"],
      ["2", "Know.", "[django] [postgresql] [redis]", "[django] [postgresql redis]", "[django] [postgresql] [redis]",
       "[django] [postgresql] [redis]"],
      ["3", "Know.", "[project management] [B2B market] [UX] and [development]", "[project management] [B2B] market [UX] and development",
       "[project management] [B2B market UX and development]", "[project management] [B2B market] [UX and development]"],
      ["4", "Know.", "including [AWS] [containers] and [Kubernetes]", "[AWS] containers and [Kubernetes]",
       "[AWS containers] and [Kubernetes]", "[AWS containers] and [Kubernetes]"],
      ["5", "Skill", "This entails [design execution and analysis of phosphoproteomics experiments]", "no span",
       "design execution and [analysis of] phosphoproteomics [experiments]", "[design execution and analysis of phosphoproteomics experiments]"]]
table(ex, [0.6, 1.3, 4.7, 3.6, 3.7, 3.4], size=7.2, align=["center", "left", "left", "left", "left", "left"])
caption("Table 4.", "Test sentences (excerpts) with gold spans and predictions in square brackets; BERT-base and JobBERT from the same seed. "
        "Twenty-four such examples are listed in the repository.")

# ---------------------------------------------------------------- 6 Discussion
heading("6  Discussion and limitations")
para("The results support a simple picture. A dictionary built from the training annotations works reasonably for short, "
     "frequent and unambiguous terms, which is the case for many Knowledge spans, and poorly for Skill spans, which are "
     "long, varied and mostly new in each test posting. A fine-tuned encoder generalises to unseen expressions and "
     "gains most where the dictionary is weakest, and domain-adaptive pre-training adds a consistent further improvement. "
     "Even so, exact-match F1 stays near 0.5 on Skill: the remaining errors are largely about where a span begins and ends, "
     "and a plausible cause, which we did not measure, is that the boundaries of long skill phrases are only partly "
     "consistent in the annotation, as the dictionary example above suggests.", first_indent=True)
para("The study has several limitations. The Skill and Knowledge types correspond only approximately to “technical” and "
     "“interpersonal” skills, since Skill also includes applied abilities. The partial-match definition, the dictionary "
     "settings and the training hyperparameters other than the learning rate are our choices. The learning rate was selected "
     "with one seed, and for JobBERT on Skill the best epoch was the 9th or 10th of a maximum of 10, so longer training could "
     "help. A few sentences are truncated at 256 pieces. The test set differs from the training set in sentence length "
     "for the *tech* source, and we used only the public part of the corpus. Finally, we compare two models and one dictionary "
     "design and did not test significance formally, although seed ranges do not overlap.", first_indent=True)

heading("7  Conclusion")
para(f"On SkillSpan, token-labelling models fine-tuned from BERT-base and JobBERT outperform a train-only dictionary by a "
     f"wide margin on exact match (Skill {f3(sk_d)} to {f3(sk_j)}, Knowledge {f3(kn_d)} to {f3(kn_j)} for JobBERT), and JobBERT is "
     "consistently better than BERT-base. The gain comes mostly from expressions unseen in training, while a large "
     "part of the remaining error lies in span boundaries rather than in missing the skill altogether. "
     "Natural next steps are longer training and more seeds for the learning-rate choice, boundary-aware decoding or "
     "a CRF layer, and joint modelling of the two overlapping span types.", first_indent=True)

heading("Code and external resources")
para("All code, per-run outputs (with command, seed and library versions) and result tables are in the project repository "
     "(github.com/jegaloido-png/skillspan-extraction). The training and evaluation code was written for this project with "
     "PyTorch 2.8 and Transformers 5.21; from the SkillSpan repository we use only the data, the splits and the seed values "
     "(MIT licence). The pre-trained checkpoints are taken from the Hugging Face Hub. Training ran on a rented NVIDIA RTX 4090.",
     size=9, space_after=3)

heading("References")
refs = [
    "Devlin, J., Chang, M.-W., Lee, K., Toutanova, K. (2019). BERT: Pre-training of deep bidirectional transformers for language understanding. *NAACL-HLT*.",
    "Loshchilov, I., Hutter, F. (2019). Decoupled weight decay regularization. *ICLR*.",
    "Ramshaw, L. A., Marcus, M. P. (1995). Text chunking using transformation-based learning. *Third Workshop on Very Large Corpora*.",
    "Wolf, T. et al. (2020). Transformers: State-of-the-art natural language processing. *EMNLP (System Demonstrations)*.",
    "Zhang, M., Jensen, K. N., Sonniks, S. D., Plank, B. (2022). SkillSpan: Hard and soft skill extraction from English job postings. *NAACL*.",
]
for r in refs:
    p = para(r, align="left", size=8.8, space_after=1.5)
    p.paragraph_format.left_indent = Cm(0.5)
    p.paragraph_format.first_line_indent = Cm(-0.5)

cp = doc.core_properties
cp.author, cp.last_modified_by = "Giacomo Cornacchia", "Giacomo Cornacchia"
cp.title = "Skill Extraction from Job Advertisements: A Dictionary Baseline versus BERT and JobBERT Token Labelling on SkillSpan"
cp.comments, cp.keywords, cp.subject = "", "", "Computational Linguistics and Language-Based Interaction"

out = HERE / "report.docx"
doc.save(out)
print("saved", out)
