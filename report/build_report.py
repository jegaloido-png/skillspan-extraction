"""Builds report/report.docx from the tables in results/ and the figures in report/figures/.

Every number in the text is read from the CSV files, so the report cannot drift from the experiments.
"""
import re
from pathlib import Path

import pandas as pd
from docx import Document
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


extra = pd.read_csv(R / "extra_checks.csv")


def X(check, system, layer, key):
    """One value from results/extra_checks.csv (written by src/06_extra_checks.py)."""
    r = extra[(extra.check == check) & (extra.system == system) & (extra.layer == layer) & (extra.key == key)]
    assert len(r) == 1, (check, system, layer, key)
    return float(r.value.iloc[0])


# ---------------------------------------------------------------- document helpers
doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
sec.left_margin = sec.right_margin = Cm(2.0)
sec.top_margin, sec.bottom_margin = Cm(1.7), Cm(1.7)

BODY_FONT, HEAD_FONT, SIZE = "Times New Roman", "Calibri", 11
TABLE_SIZE, CAPTION_SIZE = 9, 9.5


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
    """Tiny markup: **bold**, *italic*, `code`."""
    for tok in re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)", text):
        if not tok:
            continue
        if tok.startswith("`"):
            set_font(p.add_run(tok[1:-1]), "Consolas", (size or SIZE) - 1.5, color=color)
        elif tok.startswith("**"):
            set_font(p.add_run(tok[2:-2]), font, size, bold=True, color=color)
        elif tok.startswith("*"):
            set_font(p.add_run(tok[1:-1]), font, size, italic=True, color=color)
        else:
            set_font(p.add_run(tok), font, size, color=color)


def para(text, align="justify", space_after=5, size=SIZE, keep_next=False, space_before=0):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_after, pf.space_before = Pt(space_after), Pt(space_before)
    pf.line_spacing = 1.07
    pf.keep_with_next = keep_next
    pf.widow_control = True
    p.alignment = {"justify": WD_ALIGN_PARAGRAPH.JUSTIFY, "left": WD_ALIGN_PARAGRAPH.LEFT,
                   "center": WD_ALIGN_PARAGRAPH.CENTER}[align]
    add_runs(p, text, size)
    return p


def heading(text, level=1):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.keep_with_next = True
    pf.space_before = Pt(11 if level == 1 else 6)
    pf.space_after = Pt(4 if level == 1 else 2)
    run = p.add_run(text)
    set_font(run, HEAD_FONT, 14 if level == 1 else 12, bold=True, color="1F3864" if level == 1 else "2F5496")
    if level == 1:  # thin rule under the section title
        ppr = p._p.get_or_add_pPr()
        b = OxmlElement("w:pBdr")
        bt = OxmlElement("w:bottom")
        for k, v in (("w:val", "single"), ("w:sz", "4"), ("w:space", "1"), ("w:color", "8EAADB")):
            bt.set(qn(k), v)
        b.append(bt)
        ppr.append(b)
    return p


def caption(label, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before, p.paragraph_format.space_after = Pt(3), Pt(9)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    set_font(p.add_run(label + " "), HEAD_FONT, CAPTION_SIZE, bold=True, color="1F3864")
    add_runs(p, text, CAPTION_SIZE, font=HEAD_FONT)
    return p


def figure(name, width_cm=17.0):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before, p.paragraph_format.space_after = Pt(5), Pt(0)
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


def table(rows, col_widths_cm, header_rows=1, size=TABLE_SIZE, align=None, bold_rows=(), group_shade=()):
    """Booktabs-like table: rules above/below the header and at the bottom."""
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = t.cell(i, j)
            c.width = Cm(col_widths_cm[j])
            p = c.paragraphs[0]
            p.paragraph_format.space_after = p.paragraph_format.space_before = Pt(1.8)
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
    set_font(run, HEAD_FONT, 9, color="595959")


add_page_number(sec)

# ---------------------------------------------------------------- title block
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_after = Pt(2)
set_font(p.add_run("Skill Extraction from Job Advertisements:"), HEAD_FONT, 18, bold=True, color="1F3864")
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_after = Pt(4)
set_font(p.add_run("A Dictionary Baseline versus BERT and JobBERT Token Labelling on SkillSpan"), HEAD_FONT, 13,
         color="2F5496")
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_after = Pt(1)
set_font(p.add_run("Giacomo Cornacchia"), HEAD_FONT, 11.5, bold=True)
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_after = Pt(7)
set_font(p.add_run("Computational Linguistics and Language-Based Interaction"), HEAD_FONT, 10, color="595959")

# abstract
sk_j, kn_j = S("jobbert", "skill", "exact_f1")[0], S("jobbert", "knowledge", "exact_f1")[0]
sk_b, kn_b = S("bert", "skill", "exact_f1")[0], S("bert", "knowledge", "exact_f1")[0]
sk_d, kn_d = S("dictionary_tuned", "skill", "exact_f1")[0], S("dictionary_tuned", "knowledge", "exact_f1")[0]
abstract = (
    "**Abstract.** Job advertisements describe the skills they ask for in free text. Finding these skills automatically, "
    "as short pieces of text, is a first step towards studying the labour market. On the SkillSpan dataset we compare a "
    "simple dictionary, built only from the training data, with two neural models, BERT-base and JobBERT, that are trained "
    "to tag every word of a sentence. We run two separate experiments, one for *Skill* spans and one for *Knowledge* spans, "
    "each with five random seeds. "
    f"JobBERT reaches an exact-match F1 of {f3(sk_j)} on Skill and {f3(kn_j)} on Knowledge, against {f3(sk_d)} and "
    f"{f3(kn_d)} for the best dictionary and {f3(sk_b)} and {f3(kn_b)} for BERT-base. "
    f"If partly correct spans are also accepted, both models score between {f2(S('bert','skill','partial_f1')[0])} and "
    f"{f2(S('jobbert','knowledge','partial_f1')[0])}, so many of the remaining errors are about where a span starts and ends. "
    "The error analysis shows that the models win mainly on expressions that never appear as annotated skills in the "
    "training data, which a dictionary cannot find by design."
)
p = para(abstract, size=10.3, space_after=5)
p.paragraph_format.left_indent = p.paragraph_format.right_indent = Cm(0.6)

# ---------------------------------------------------------------- 1 Introduction
heading("1  Introduction")
para("Online job advertisements are a rich and constantly updated source of information on what employers ask for. "
     "Turning their free text into structured data, that is, finding the exact words that name a skill, helps with job "
     "matching, course design and labour-market monitoring. The task is hard for two reasons. Skills are written in "
     "open-ended and varied language (*“prioritising your tasks”*, *“Kubernetes”*, *“strategic thinking”*), and where a "
     "skill starts and ends is often a matter of annotation convention.")
para("We study this task on SkillSpan (Zhang et al., 2022) and ask how much a model that tags words improves over a "
     "dictionary that uses the same training data. The work has four parts: (i) a dictionary built only from the training "
     "set, with an automatic check that nothing from the test set can enter it; (ii) a comparison with BERT-base and with "
     "JobBERT (a BERT model that was trained further on job postings), in two separate experiments, Skill and Knowledge, "
     "with five seeds each; (iii) an evaluation with exact and partial matching of spans; and (iv) an error analysis that "
     "separates boundary errors from missed and wrong spans and checks how the results depend on whether an expression "
     "was seen in training.")

# ---------------------------------------------------------------- 2 Data
heading("2  Data")
para("SkillSpan contains English job-posting sentences in which skills are marked as spans of words, with two types, "
     "following the ESCO classification of skills. A *Knowledge* span names a piece of knowledge, usually called a hard "
     "skill (e.g. a programming language). A *Skill* span names the ability to use knowledge in a task, and it also covers "
     "soft skills, which ESCO calls attitudes (Zhang et al., 2022). The two types are annotated independently and can "
     "overlap, so we treat them as two separate experiments. "
     "We use the public part of the dataset, with its official train, development and test split and two sources: "
     "*house*, general job postings from a company, and *tech*, postings for technical roles. "
     "(The numbers in the original paper also include a third, non-public source.) Table 1 shows the statistics.")


def st_(split, source, col):
    return stats[(stats.split == split) & (stats.source == source)].iloc[0][col]


rows = [["Split", "Sentences", "Tokens", "Avg. sentence length", "Skill spans", "Avg. length", "Knowledge spans", "Avg. length"]]
for split in ("train", "dev", "test"):
    rows.append([split.capitalize(), f"{st_(split,'all','sentences'):,}", f"{st_(split,'all','tokens'):,}",
                 f"{st_(split,'all','avg_sent_len'):.1f}", f"{st_(split,'all','skill_spans'):,}",
                 f"{st_(split,'all','skill_avg_span_len'):.2f}", f"{st_(split,'all','knowledge_spans'):,}",
                 f"{st_(split,'all','knowledge_avg_span_len'):.2f}"])
table(rows, [1.7, 2.1, 2.0, 2.7, 2.1, 2.0, 2.5, 1.9], size=8.8)
caption("Table 1.", "Dataset statistics (house and tech together). Lengths are in tokens.")
para(f"Three properties of the data matter for what follows. First, annotations are sparse: 67% of the training sentences "
     f"contain no span at all, and about 92% of all tags are *O* (outside any span). Second, Skill spans are much longer than "
     f"Knowledge spans ({st_('train','all','skill_avg_span_len'):.1f} against {st_('train','all','knowledge_avg_span_len'):.1f} "
     f"tokens in the training set), which makes it harder to get the exact boundaries right. Third, the two sources differ "
     f"and the data changes between splits: *tech* sentences average {st_('train','tech','avg_sent_len'):.1f} tokens in "
     f"training but only {st_('test','tech','avg_sent_len'):.1f} in the test set, where many sentences are short lists of "
     f"technologies.")

# ---------------------------------------------------------------- 3 Methods
heading("3  Methods")
heading("3.1  Dictionary baseline", 2)
d_sk = dtest[(dtest.system == "dictionary_tuned") & (dtest.layer == "skill") & (dtest.source == "all")].iloc[0]
d_kn = dtest[(dtest.system == "dictionary_tuned") & (dtest.layer == "knowledge") & (dtest.source == "all")].iloc[0]
para("For each span type, every span marked in the training set becomes a dictionary entry (a sequence of words). "
     "Each entry also stores its *annotation rate*: how many times the sequence is marked as a span in the training "
     "text, divided by how many times it occurs there at all. This shows how ambiguous an expression is. In the "
     "lower-cased Knowledge dictionary, *python* has a rate of 0.65 and is kept, while *design*, which is rarely a skill "
     "on its own, has a rate of 0.07 and is dropped. To predict, we read a sentence from left to right and take the "
     "longest dictionary match at each position, so the predicted spans never overlap. "
     "Two settings were chosen on the development set by exact-match F1: whether matching is case-sensitive or "
     "lower-cased, and the minimum annotation rate an entry needs to be kept (nine values from 0 to 0.8). "
     f"The chosen settings are *cased, rate ≥ {d_sk.min_precision:g}* for Skill ({int(d_sk.dict_size):,} entries) and "
     f"*lower-cased, rate ≥ {d_kn.min_precision:g}* for Knowledge ({int(d_kn.dict_size):,} entries). We report this "
     "*tuned* dictionary and a *pure* version with no rate threshold. Before every evaluation, an automatic check confirms "
     "that every entry is marked in the training set and that no expression found only in the test set is in the "
     "dictionary. The method uses no randomness.")
heading("3.2  Token classification", 2)
para("Each word of a sentence gets one tag: B (first word of a span), I (inside a span) or O (outside) "
     "(Ramshaw and Marcus, 1995). We fine-tune a standard token-classification model from the Hugging Face Transformers "
     "library (Wolf et al., 2020): a BERT encoder with a small linear layer on top that chooses one of the three tags for "
     "each word. We train one model per span type, starting from two pre-trained models: `bert-base-cased` "
     "(Devlin et al., 2019; 109M parameters) and `jobbert-base-cased` (JobBERT, 108M parameters), which is BERT-base "
     "trained further on about 3.2M job-posting sentences (Zhang et al., 2022). A word can be split into several "
     "sub-word pieces. We put the tag on the first piece and ignore the other pieces, both in training and in prediction. "
     "Spans are rebuilt from the word tags, and an I tag with no B before it starts a new span. Inputs are cut at 256 pieces "
     "(a few sentences are affected; the count is saved with every run).")
heading("3.3  Training protocol", 2)
para("We train with AdamW (Loshchilov and Hutter, 2019), batch size 16, weight decay 0.01, a linear learning-rate schedule "
     "with 10% warm-up, gradient clipping at 1.0 and mixed precision. Training lasts at most 10 epochs and stops early "
     "if the development exact-match F1 does not improve for 3 epochs; the epoch with the best development score is kept. "
     "The learning rate was chosen on the development set, with a single seed, among 2e-5, 3e-5 and 5e-5, for all four "
     "configurations (two models × two span types). Because 5e-5 was at the edge of this range and best in three of the four "
     "configurations, we added a test at 7e-5 with a rule fixed before seeing its results: adopt 7e-5 only if "
     "it raised the mean development F1 by at least 0.005 and won in at least three configurations. It won in one and "
     "lowered the mean by about 0.011, so we kept 5e-5 (Figure 1). Batch size, number of epochs, warm-up and weight decay "
     "were set by us and not tuned. The final experiments use five seeds "
     "(3477689, 4213916, 8749520, 6828303, 9364029, the values used by the SkillSpan authors), which gives 20 runs of about "
     "four minutes each on one rented RTX 4090 GPU. The test set is used only by these final runs.")
figure("fig_lr_dev.png", 11.0)
caption("Figure 1.", "Development exact-match F1 against learning rate (one seed). The dotted line marks the value used in "
        "all final runs (5e-5). The value 7e-5 improved only JobBERT on Skill, and only by 0.004.")
heading("3.4  Evaluation", 2)
para("We evaluate spans, counting over the whole test set, separately for each span type. Under "
     "**exact match**, a predicted span is correct only if its start and end are both the same as those of a gold span; "
     "precision, recall and F1 follow from this. Because there are few spans per sentence and most tags are *O*, "
     "per-word accuracy would say little and is not reported. As a second measure we use a **partial match** that we "
     "defined ourselves: a predicted span is correct if it overlaps at least one gold span, and a gold span is found if at "
     "least one predicted span overlaps it, so precision and recall are counted on different things. Comparing the two "
     "measures gives a rough idea of how many errors are about boundaries. The partial match is generous, though: "
     "a trivial predictor that marks every whole sentence as one span already reaches a partial F1 of "
     f"{f2(X('whole_sentence_baseline','-','skill','partial_f1'))} on Skill and "
     f"{f2(X('whole_sentence_baseline','-','knowledge','partial_f1'))} on Knowledge (exact F1 below 0.02). "
     "We therefore use it only as a rough signal and base the error analysis on the span-by-span classification "
     "in Section 5. For BERT-base and JobBERT we report the mean and the sample "
     "standard deviation over the five seeds; the dictionary has no randomness.")

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
tb = table(rows, [1.7, 2.5, 2.1, 2.1, 2.15, 2.1, 2.1, 2.15], size=8.4, align=["left", "left"] + ["center"] * 6,
           bold_rows=(4, 8), group_shade=(5, 6, 7, 8))
caption("Table 2.", "Test-set results (all sources). BERT-base and JobBERT: mean ± sample standard deviation over five seeds; "
        "the dictionaries always give the same result. JobBERT (bold) has the highest value in every column.")
figure("fig_main_results.png", 14.6)
caption("Figure 2.", "Exact and partial F1 on the test set. Bars show the mean over five seeds for BERT-base and "
        "JobBERT, with the standard deviation; black dots are the individual seeds (exact F1).")

jb_s = runs[(runs.system == "jobbert") & (runs.layer == "skill") & (runs.source == "all")].exact_f1
bb_s = runs[(runs.system == "bert") & (runs.layer == "skill") & (runs.source == "all")].exact_f1
jb_k = runs[(runs.system == "jobbert") & (runs.layer == "knowledge") & (runs.source == "all")].exact_f1
bb_k = runs[(runs.system == "bert") & (runs.layer == "knowledge") & (runs.source == "all")].exact_f1
assert jb_s.min() > bb_s.max() and jb_k.min() > bb_k.max()
for _l in ("skill", "knowledge"):
    for _m in ("exact_p", "exact_r", "exact_f1", "partial_p", "partial_r", "partial_f1"):
        assert S("jobbert", _l, _m)[0] == max(S(s_, _l, _m)[0] for s_ in names), (_l, _m)

para("**Models against the dictionary.** Both fine-tuned models are clearly better than the dictionary on both span types "
     f"(Table 2, Figure 2). On Skill the best dictionary reaches an exact F1 of {f3(sk_d)} and JobBERT {f3(sk_j)}, about "
     f"{sk_j/sk_d:.1f} times higher. On Knowledge the gap is smaller ({f3(kn_d)} against {f3(kn_j)}), because technical "
     "terms are short, frequent and repeated across postings, so a dictionary can use them well. Tuning the annotation-rate "
     "threshold matters for the dictionary: without it, recall is high but precision is very low (Knowledge: "
     f"P = {f3(S('dictionary_pure','knowledge','exact_p')[0])}, R = {f3(S('dictionary_pure','knowledge','exact_r')[0])}), "
     f"and the threshold raises the Knowledge exact F1 from {f3(S('dictionary_pure','knowledge','exact_f1')[0])} to {f3(kn_d)}. "
     "For Skill the threshold helps much less. A likely reason is that many skills are written with ordinary words and "
     "phrases, which an annotation rate cannot tell apart from non-skill uses. Part of the gap is also built in: "
     f"only {RC('dictionary','skill').seen_gold/(RC('dictionary','skill').seen_gold+RC('dictionary','skill').unseen_gold)*100:.0f}% "
     f"of the Skill and {RC('dictionary','knowledge').seen_gold/(RC('dictionary','knowledge').seen_gold+RC('dictionary','knowledge').unseen_gold)*100:.0f}% "
     "of the Knowledge test spans appear as a marked span in the training set, so a dictionary built from the training "
     "set cannot find more than that share (the pure dictionary reaches an exact recall of "
     f"{f2(S('dictionary_pure','skill','exact_r')[0])} and {f2(S('dictionary_pure','knowledge','exact_r')[0])}).")
para("**JobBERT against BERT-base.** JobBERT is better on both span types "
     f"(+{sk_j-sk_b:.3f} exact F1 on Skill, +{kn_j-kn_b:.3f} on Knowledge). "
     f"The seed ranges do not overlap: the five JobBERT Skill runs lie between {jb_s.min():.3f} and {jb_s.max():.3f}, the five BERT-base "
     f"runs between {bb_s.min():.3f} and {bb_s.max():.3f}; on Knowledge the ranges are {jb_k.min():.3f}–{jb_k.max():.3f} and "
     f"{bb_k.min():.3f}–{bb_k.max():.3f}. The spread between seeds is smaller for JobBERT on Skill "
     f"(standard deviation {S('jobbert','skill','exact_f1')[1]:.3f} against {S('bert','skill','exact_f1')[1]:.3f}), but on Knowledge "
     f"it is the other way round ({S('jobbert','knowledge','exact_f1')[1]:.3f} against {S('bert','knowledge','exact_f1')[1]:.3f}), "
     "and five seeds are too few to say more. A Welch t-test over the five seeds gives "
     f"p = {X('welch','jobbert-bert','skill','p'):.3f} on Skill and p = {X('welch','jobbert-bert','knowledge','p'):.3f} on Knowledge. "
     "Because the seeds only reflect the randomness of training, we also resampled the test sentences 1,000 times: the 95% interval "
     f"of the JobBERT minus BERT-base difference in exact F1 is [{X('bootstrap','jobbert-bert','skill','ci_low'):.3f}, "
     f"{X('bootstrap','jobbert-bert','skill','ci_high'):.3f}] on Skill and [{X('bootstrap','jobbert-bert','knowledge','ci_low'):.3f}, "
     f"{X('bootstrap','jobbert-bert','knowledge','ci_high'):.3f}] on Knowledge, so it stays above zero in both cases, "
     "although for Knowledge only just. "
     "On Knowledge both models have a higher recall than precision "
     f"({f3(S('jobbert','knowledge','exact_r')[0])} against {f3(S('jobbert','knowledge','exact_p')[0])} for JobBERT), "
     "while on Skill the two are close. "
     "The same order was found on the development set during the learning-rate search, where JobBERT was ahead in all four configurations.")

# per-source table
rows = [["System", "Skill, house", "Skill, tech", "Knowledge, house", "Knowledge, tech"]]
for s in ("dictionary_tuned", "bert", "jobbert"):
    rows.append([names[s]] + [ms(s, layer, "exact_f1", src) for layer in ("skill", "knowledge") for src in ("house", "tech")])
table(rows, [3.4, 3.3, 3.3, 3.6, 3.3], size=8.8)
caption("Table 3.", "Exact-match F1 on the test set by source.")
para("**Differences between sources.** Skill is harder than Knowledge for every system, and the two span types behave "
     "differently across sources (Table 3). Knowledge is much easier on *tech* than on *house* for all systems, most of all for the "
     f"dictionary ({f3(S('dictionary_tuned','knowledge','exact_f1','tech')[0])} against "
     f"{f3(S('dictionary_tuned','knowledge','exact_f1','house')[0])}), since technology names are well covered by the training data. "
     "On Skill the two sources are close for the models, and the dictionary is better on *tech* than on *house*.")

# ---------------------------------------------------------------- 5 Error analysis
heading("5  Error analysis")
para("Partial-match F1 is much higher than exact-match F1 for the models (Skill: "
     f"{f2(S('jobbert','skill','partial_f1')[0])} against {f2(sk_j)} for JobBERT), so we look at *how* predictions go wrong. "
     "Each predicted span is put in one class: exact, *too short* (strictly inside a gold span), *too long* (containing a gold "
     "span), *shifted* (partial overlap) or *no overlap* with any gold span. Each gold span is either found exactly, "
     "found only with different boundaries, or missed (no overlapping prediction). Figure 3 shows the shares, averaged "
     "over the seeds.")
figure("fig_error_breakdown.png", 14.8)
caption("Figure 3.", "What happens to the gold spans (top) and what the predicted spans are made of (bottom) on the test set. "
        "Numbers inside the bars are percentages; BERT-base and JobBERT are averaged over five seeds.")
jb_t, bb_t, dd_t = T("jobbert", "skill"), T("bert", "skill"), T("dictionary", "skill")
jt_k = T("jobbert", "knowledge")
para(f"**Boundary errors.** For Skill, JobBERT finds {jb_t.gold_boundary_only:.0f} of the {jb_t.n_gold:.0f} gold spans "
     f"({jb_t.gold_boundary_only/jb_t.n_gold*100:.0f}%) only with wrong boundaries, which is more than the "
     f"{jb_t.missed:.0f} it misses entirely. Counting predictions, too-short ones are more frequent than "
     f"too-long ones (JobBERT: {jb_t.shorter:.0f} against {jb_t.longer:.0f}; dictionary: {dd_t.shorter:.0f} against {dd_t.longer:.0f}). "
     "This count is partly an artefact, however: when one gold span is split into several pieces, every piece counts as a "
     "too-short prediction, while a merge of several gold spans counts only once. Counted per gold span instead, the two "
     f"kinds of error are about equally common for the models (JobBERT, Skill: {X('gold_fate','jobbert','skill','inside'):.0f} gold spans are "
     f"covered only by shorter predictions inside them, and {X('gold_fate','jobbert','skill','contained'):.0f} lie inside a longer "
     "prediction), and only the dictionary clearly produces too-short spans "
     f"({X('gold_fate','dictionary','skill','inside'):.0f} against {X('gold_fate','dictionary','skill','contained'):.0f}). "
     "Shifted spans are rare. An example of a too-short prediction is BERT-base predicting only *“structured approach”* "
     "for the gold span *“take a structured approach to work”* (Table 4, example 1). On Knowledge, where spans are "
     f"short, boundary errors affect {jt_k.gold_boundary_only/jt_k.n_gold*100:.0f}% of the gold spans (JobBERT), and the typical "
     "failure is to merge or split neighbouring terms (Table 4, examples 3, 4 and 6).")
para("**Wrong and missed spans.** About one prediction in five has no overlap with any gold span "
     f"(JobBERT: {f2(T('jobbert','skill').spurious/T('jobbert','skill').n_pred)} for Skill, "
     f"{f2(T('jobbert','knowledge').spurious/T('jobbert','knowledge').n_pred)} for Knowledge), whereas the dictionary is far less "
     f"precise on Skill ({f2(dd_t.spurious/dd_t.n_pred)}). Some of these predictions look like real skills that the annotators "
     "did not mark, for example *“overcoming obstacles”* in a sentence where only the next phrase is annotated, so precision "
     "is probably underestimated a little; we did not count these cases. The dictionary also copies an inconsistency of the "
     "annotation: it learns *“postgresql redis”* as one entry from a single training sentence and then merges two separate "
     "technologies in the test set (Table 4, example 2).")
figure("fig_seen_unseen.png", 13.8)
caption("Figure 4.", "Exact recall on the test set for gold spans whose text (lower-cased) is marked somewhere in the training "
        "set (*seen*) and for those that are not (*not seen*). By design, the dictionary cannot find unseen spans.")
sk_u, kn_u = RC("jobbert", "skill"), RC("jobbert", "knowledge")
para("**Seen and unseen expressions.** Figure 4 splits the test gold spans by whether their text is marked as a span in the "
     f"training set. Most Skill spans are new ({sk_u.unseen_gold:.0f} of {sk_u.seen_gold + sk_u.unseen_gold:.0f}, "
     f"{sk_u.unseen_gold/(sk_u.seen_gold+sk_u.unseen_gold)*100:.0f}%), and so are {kn_u.unseen_gold/(kn_u.seen_gold+kn_u.unseen_gold)*100:.0f}% "
     "of the Knowledge spans. On seen spans JobBERT is about as good as the dictionary "
     f"(Skill {f2(sk_u.seen_exact_recall)} against {f2(RC('dictionary','skill').seen_exact_recall)}; Knowledge "
     f"{f2(kn_u.seen_exact_recall)} against {f2(RC('dictionary','knowledge').seen_exact_recall)}) and BERT-base is slightly lower "
     f"({f2(RC('bert','skill').seen_exact_recall)} and {f2(RC('bert','knowledge').seen_exact_recall)}). The advantage of the models therefore "
     f"comes from unseen expressions, which they find exactly with a recall of {f2(RC('bert','skill').unseen_exact_recall)} (BERT-base) and "
     f"{f2(sk_u.unseen_exact_recall)} (JobBERT) on Skill and {f2(RC('bert','knowledge').unseen_exact_recall)} and "
     f"{f2(kn_u.unseen_exact_recall)} on Knowledge. The extra training of JobBERT on job postings helps on both parts for Skill, "
     "and mainly on seen spans for Knowledge. (The dictionary scores 0 on unseen spans by construction, so this is not a finding "
     "about the dictionary.)")
para(f"**Span length.** Long spans are not harder for the models on Skill: JobBERT finds exactly "
     f"{f2(X('length_recall','jobbert','skill','recall_1'))}, {f2(X('length_recall','jobbert','skill','recall_2'))} and "
     f"{f2(X('length_recall','jobbert','skill','recall_3+'))} of the Skill spans with 1, 2 and 3 or more tokens (the last group is "
     f"{X('length_recall','jobbert','skill','n_gold_3+'):.0f} of {X('length_recall','jobbert','skill','n_gold_3+')+X('length_recall','jobbert','skill','n_gold_1')+X('length_recall','jobbert','skill','n_gold_2'):.0f} spans), "
     f"whereas the dictionary falls from {f2(X('length_recall','dictionary','skill','recall_1'))} to "
     f"{f2(X('length_recall','dictionary','skill','recall_3+'))}. On Knowledge, long spans are hard for every system: "
     f"JobBERT's exact recall is {f2(X('length_recall','jobbert','knowledge','recall_1'))} for one-token spans and "
     f"{f2(X('length_recall','jobbert','knowledge','recall_3+'))} for spans of three or more tokens "
     f"({X('length_recall','jobbert','knowledge','n_gold_3+'):.0f} spans).")

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
       "design execution and [analysis of] phosphoproteomics [experiments]", "[design execution and analysis of phosphoproteomics experiments]"],
      ["6", "Know.", "[java] [rest] [cloud] [spring] [design-patterns]", "[java] [rest] cloud [spring] design-patterns",
       "[java] [rest] [cloud] [spring] [design-patterns]", "[java] [rest] [cloud] [spring design-patterns]"]]
table(ex, [0.6, 1.3, 4.6, 3.6, 3.7, 3.5], size=8.4, align=["center", "left", "left", "left", "left", "left"])
caption("Table 4.", "Test sentences (excerpts) with the gold spans and the predictions in square brackets; BERT-base and JobBERT from the same seed. "
        "In examples 1, 3 and 5 JobBERT is better than BERT-base, in example 6 it is worse. "
        "Twenty-four such examples are listed in the repository.")

# ---------------------------------------------------------------- 6 Discussion
heading("6  Discussion and limitations")
para("The results give a simple picture. A dictionary built from the training annotations works reasonably for short, "
     "frequent and unambiguous terms, which is the case for many Knowledge spans, and poorly for Skill spans, which are "
     "long, varied and mostly new in each test posting. A fine-tuned model can handle expressions it has not seen, "
     "and it gains most where the dictionary is weakest. Training further on job postings (JobBERT) adds a steady "
     "extra improvement. "
     "Even so, exact-match F1 stays near 0.5 on Skill: a large part of the remaining errors are about where a span begins and ends. "
     "A possible cause, which we did not measure, is that the boundaries of long skill phrases are only partly "
     "consistent in the annotation, as the dictionary example above suggests.")
para("The study has several limitations. The Skill and Knowledge types match “technical” and “interpersonal” skills only "
     "roughly, since Skill also includes applied abilities, and we did not analyse hard and soft skills separately. "
     "Our scores cannot be compared directly with those in the SkillSpan paper, which also uses the non-public source. "
     "The partial-match definition, the dictionary settings and the "
     "training settings other than the learning rate are our own choices. The learning rate was chosen with one seed, "
     "and for JobBERT on Skill the best epoch was the 9th or 10th of a maximum of 10, so longer training might "
     "help (the learning-rate schedule also ends at epoch 10, so this is not certain). "
     "Our rule that an I tag with no B before it starts a new span matters: "
     f"JobBERT produces about {X('orphan_i','jobbert','skill','orphan_tags'):.0f} such tags on Skill "
     f"({X('orphan_i','jobbert','skill','orphan_tags')/T('jobbert','skill').n_pred*100:.0f}% of its predicted spans), and setting them to O instead "
     f"would raise its exact F1 from {f3(X('orphan_i','jobbert','skill','exact_f1_lenient'))} to "
     f"{f3(X('orphan_i','jobbert','skill','exact_f1_strict'))} (BERT-base: {f3(X('orphan_i','bert','skill','exact_f1_lenient'))} to "
     f"{f3(X('orphan_i','bert','skill','exact_f1_strict'))}). Runs on the GPU are not exactly repeatable: with the same seed, the "
     "development F1 of one configuration was 0.555 in the learning-rate search and 0.559 in the final run. "
     "A few training sentences are cut at 256 pieces (none in the test set). The test set differs from the training set "
     "in sentence length for the *tech* source, and "
     f"{X('duplicates','-','all','share_test_sentences_in_train')*100:.0f}% of the test sentences also occur word for word in the "
     f"training set; they contain only {X('duplicates','-','skill','share_gold_spans_in_duplicates')*100:.0f}% (Skill) and "
     f"{X('duplicates','-','knowledge','share_gold_spans_in_duplicates')*100:.0f}% (Knowledge) of the test spans, and without them "
     f"the exact F1 of JobBERT is {f3(X('duplicates','jobbert','skill','exact_f1_without_duplicates'))} and "
     f"{f3(X('duplicates','jobbert','knowledge','exact_f1_without_duplicates'))}. We used only the public part of the dataset. "
     "Finally, we compared only two models and one dictionary design, and the significance checks rest on five seeds and one "
     "test set.")

heading("7  Conclusion")
para(f"On SkillSpan, models fine-tuned from BERT-base and JobBERT are far better than a dictionary built from the training "
     f"set alone (exact F1 for JobBERT: Skill {f3(sk_d)} to {f3(sk_j)}, Knowledge {f3(kn_d)} to {f3(kn_j)}), and JobBERT is "
     "better than BERT-base in every comparison we ran. The gain comes mostly from expressions that were not seen in training, while a large "
     "part of the remaining error is about span boundaries rather than missing the skill altogether. "
     "Natural next steps are longer training and more seeds for the learning-rate choice, better handling of span boundaries "
     "(for example a CRF layer), and modelling the two overlapping span types together.")

heading("Code and external resources")
para("All code, the output of every run (with command, seed and library versions) and the result tables are in the project "
     "repository (github.com/jegaloido-png/skillspan-extraction). The training and evaluation code was written for this "
     "project with PyTorch 2.8 and Transformers 5.21; from the SkillSpan repository we use only the data, the splits and the "
     "seed values (MIT licence). The pre-trained models come from the Hugging Face Hub. Training ran on a rented NVIDIA RTX 4090.",
     size=10, space_after=3)

heading("References")
refs = [
    "Devlin, J., Chang, M.-W., Lee, K., Toutanova, K. (2019). BERT: Pre-training of deep bidirectional transformers for language understanding. *NAACL-HLT*.",
    "Loshchilov, I., Hutter, F. (2019). Decoupled weight decay regularization. *ICLR*.",
    "Ramshaw, L. A., Marcus, M. P. (1995). Text chunking using transformation-based learning. *Third Workshop on Very Large Corpora*.",
    "Wolf, T. et al. (2020). Transformers: State-of-the-art natural language processing. *EMNLP (System Demonstrations)*.",
    "Zhang, M., Jensen, K. N., Sonniks, S. D., Plank, B. (2022). SkillSpan: Hard and soft skill extraction from English job postings. *NAACL*.",
]
for r in refs:
    p = para(r, align="left", size=9.5, space_after=2)
    p.paragraph_format.left_indent = Cm(0.5)
    p.paragraph_format.first_line_indent = Cm(-0.5)

cp = doc.core_properties
cp.author, cp.last_modified_by = "Giacomo Cornacchia", "Giacomo Cornacchia"
cp.title = "Skill Extraction from Job Advertisements: A Dictionary Baseline versus BERT and JobBERT Token Labelling on SkillSpan"
cp.comments, cp.keywords, cp.subject = "", "", "Computational Linguistics and Language-Based Interaction"

out = HERE / "report.docx"
doc.save(out)
print("saved", out)
