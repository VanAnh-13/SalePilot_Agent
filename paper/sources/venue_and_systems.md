# RIVF 2026 venue requirements and systems/agent sources

Verified on **2026-07-21**. This note separates requirements explicitly stated by
RIVF from general IEEE guidance and from author-side planning assumptions. It is
not evidence that the current SalePilot manuscript is scientifically complete.

## 1. RIVF 2026: requirements stated by the venue

Primary source: [RIVF 2026 Call for Papers](https://rivf2026.org/call-for-papers.html).

| Item | Verified requirement |
|---|---|
| Venue and dates | Hanoi, Vietnam, at VinUniversity, **18--20 December 2026**. |
| Intended track | Track 2, **AI Applications**, explicitly includes real-world AI deployment, AI-based decision support, explainability/interpretability, and scaling/integration challenges. |
| Submission deadline | **31 July 2026**, labelled **tentative** by the CFP. Recheck immediately before submission. |
| Notification | **15 October 2026**, tentative. |
| Camera-ready deadline | **11 November 2026**, tentative. |
| Language and file | English, PDF. |
| Length | Up to **6 pages**. The page does not state that references or appendices are exempt, so the safe planning assumption is that the complete submitted PDF must fit in six pages; this is an inference, not an explicit exemption rule. |
| Format | IEEE standard, **A4** paper size. LaTeX configuration given verbatim by the CFP: `\documentclass[conference,a4paper]{IEEEtran}` and `\pdfminorversion=6`. |
| Originality | Original contribution, not previously published, and not simultaneously under consideration elsewhere. |
| Submission system | [EDAS paper N35414](https://edas.info/N35414). |
| Publication condition | Accepted **and presented** papers are published in the proceedings and submitted to IEEE Xplore and other indexing databases; the CFP qualifies Xplore inclusion as subject to IEEE quality review. IEEE may exclude a non-presented paper after the conference. |

### Items not specified on the current CFP page

Do **not** invent rules for the following. Confirm them with the organizer or a
later author guide before final submission:

- whether review is single-blind or double-blind and whether author names must be removed;
- whether the six-page limit includes references, and whether paid overlength pages exist;
- supplementary-material policy and whether external anonymous repositories are allowed;
- PDF eXpress conference ID, copyright footer wording, and camera-ready checks;
- mandatory artifact, code, data, ethics, or model-provider disclosure beyond IEEE-wide policies.

Conference contact shown by the CFP: `rivf2026@vinuni.edu.vn`.

## 2. First-party IEEE formatting and integrity guidance

These are IEEE-wide author instructions. The RIVF CFP remains authoritative
where it is more specific.

1. [IEEE conference authoring tools and templates](https://conferences.ieeeauthorcenter.ieee.org/write-your-paper/authoring-tools-and-templates/)
   recommends the official Word or LaTeX conference templates. For this paper,
   RIVF has already selected the A4 `IEEEtran` conference mode.
2. [IEEE guidance on paper structure](https://conferences.ieeeauthorcenter.ieee.org/write-your-paper/structure-your-paper/)
   says the title should be specific, concise, and descriptive. Its abstract
   guidance is one self-contained paragraph of at most 250 words, without
   footnotes, references, equations, or undefined abbreviations, followed by
   3--5 keywords. Methods should contain enough detail to support replication;
   results should be interpreted without exaggeration and limitations should be
   acknowledged.
3. [IEEE research reproducibility guidance](https://conferences.ieeeauthorcenter.ieee.org/write-your-paper/research-reproducibility/)
   encourages detailed methods and sharing data, code, and other research
   outputs. This is strong author guidance, **not a requirement stated on the
   current RIVF CFP**.
4. [IEEE final-paper guidance](https://conferences.ieeeauthorcenter.ieee.org/get-published/finalize-your-paper/)
   says to remove all template guidance text and use PDF eXpress **if instructed
   by the conference committee**. The current RIVF CFP does not provide a PDF
   eXpress ID, so do not guess one.
5. [IEEE guidance for AI-generated content](https://open.ieee.org/author-guidelines-for-artificial-intelligence-ai-generated-text/)
   requires AI-generated content, including text, figures, images, or code, to
   be disclosed in the acknowledgments. The AI system, affected sections, and
   level of assistance should be identified. Editing/grammar assistance is
   outside the main intent of the policy, though disclosure is recommended.

Because this manuscript is being drafted with an AI system, a truthful disclosure
is required. A template to customize rather than copy blindly is:

> The authors used OpenAI Codex to assist with drafting [name the sections] and
> producing the source of [name the figures]. The authors independently verified
> the technical claims, references, implementation mapping, experimental results,
> and final wording, and retain full responsibility for the manuscript.

## 3. High-trust papers for the systems argument

The five papers below were selected because each supports a distinct part of the
SalePilot argument. They are not a claim that the literature search is globally
complete, nor evidence that SalePilot is novel or superior.

### S1. ReAct: interleaving reasoning and environment actions

- Shunyu Yao, Jeffrey Zhao, Dian Yu, Nan Du, Izhak Shafran, Karthik Narasimhan,
  and Yuan Cao. "ReAct: Synergizing Reasoning and Acting in Language Models."
  ICLR 2023.
- Official records: [ICLR page](https://iclr.cc/virtual/2023/poster/11003),
  [OpenReview paper](https://openreview.net/forum?id=WE_vluYUL-X).
- Appropriate use: motivate an orchestrator that alternates model reasoning with
  constrained tool calls and observations.
- Boundary: ReAct does not prove that a particular multi-agent decomposition is
  better than a single agent, and its benchmark results are not directly
  comparable with SalePilot's domain evaluator.

### S2. AutoGen: programmable multi-agent conversations

- Qingyun Wu, Gagan Bansal, Jieyu Zhang, Yiran Wu, Beibin Li, Erkang Zhu, Li
  Jiang, Xiaoyun Zhang, Shaokun Zhang, Jiale Liu, Ahmed Hassan Awadallah, Ryen
  W. White, Doug Burger, and Chi Wang. "AutoGen: Enabling Next-Gen LLM
  Applications via Multi-Agent Conversations." First Conference on Language
  Modeling (COLM), 2024.
- Official record: [OpenReview/COLM](https://openreview.net/forum?id=BAakY1hNKS).
- Appropriate use: ground the design pattern of specialized conversational agents
  composed with tools and human interaction.
- Boundary: cite it as related infrastructure and a design precedent, not as
  evidence that SalePilot's implementation or specialist roles are novel.

### S3. Retrieval-Augmented Generation: explicit external knowledge and provenance

- Patrick Lewis et al. "Retrieval-Augmented Generation for Knowledge-Intensive
  NLP Tasks." NeurIPS 2020.
- Official record: [NeurIPS proceedings](https://proceedings.neurips.cc/paper/2020/hash/6b493230-Abstract.html).
- Appropriate use: motivate grounding generation in an external, updateable
  knowledge source and retaining provenance rather than relying only on model
  parameters.
- Boundary: the original work uses a learned dense retriever and end-to-end RAG
  formulations. If SalePilot uses deterministic catalog filters, database
  queries, or lexical retrieval, call it **retrieval-grounded generation**, not
  an implementation of the original RAG method.

### S4. AgentBench: multi-turn, environment-based agent evaluation

- Xiao Liu et al. "AgentBench: Evaluating LLMs as Agents." ICLR 2024.
- Official record: [ICLR proceedings](https://proceedings.iclr.cc/paper_files/paper/2024/hash/e9df36b21ff4ee211a8b71ee8b7e9f57-Abstract-Conference.html).
- Appropriate use: support evaluating agents through multi-turn interaction with
  executable environments and reporting failure modes, not only judging final
  prose quality.
- Boundary: AgentBench covers eight heterogeneous environments and reports tests
  over 29 models in its ICLR abstract. SalePilot's domain scenarios are not an
  AgentBench score and must not be presented as one.

### S5. Conversational recommendation: preference elicitation before ranking

- Konstantina Christakopoulou, Filip Radlinski, and Katja Hofmann. "Towards
  Conversational Recommender Systems." KDD 2016, pp. 815--824.
- Official/authoritative records: [ACM DOI](https://doi.org/10.1145/2939672.2939746),
  [Google Research publication page](https://research.google/pubs/towards-conversational-recommender-systems/).
- Appropriate use: motivate clarifying questions and multi-turn preference
  elicitation for cold-start decision support. The paper evaluates question
  selection with synthetic and real-world data and reports improvement over a
  static model after limited questioning.
- Boundary: its restaurant recommendation task, latent-factor method, and metrics
  are different from SalePilot. Do not reuse the reported percentage as a
  baseline or claim direct superiority.

## 4. BibTeX records

The entries below use the accepted venue versions rather than citing only arXiv
preprints. Author spellings and venue years were checked against the linked
official proceedings records.

```bibtex
@inproceedings{yao2023react,
  title     = {{ReAct}: Synergizing Reasoning and Acting in Language Models},
  author    = {Yao, Shunyu and Zhao, Jeffrey and Yu, Dian and Du, Nan and
               Shafran, Izhak and Narasimhan, Karthik and Cao, Yuan},
  booktitle = {The Eleventh International Conference on Learning Representations},
  year      = {2023},
  url       = {https://openreview.net/forum?id=WE_vluYUL-X}
}

@inproceedings{wu2024autogen,
  title     = {{AutoGen}: Enabling Next-Gen {LLM} Applications via Multi-Agent Conversations},
  author    = {Wu, Qingyun and Bansal, Gagan and Zhang, Jieyu and Wu, Yiran and
               Li, Beibin and Zhu, Erkang and Jiang, Li and Zhang, Xiaoyun and
               Zhang, Shaokun and Liu, Jiale and Awadallah, Ahmed Hassan and
               White, Ryen W. and Burger, Doug and Wang, Chi},
  booktitle = {First Conference on Language Modeling},
  year      = {2024},
  url       = {https://openreview.net/forum?id=BAakY1hNKS}
}

@inproceedings{lewis2020retrieval,
  title     = {Retrieval-Augmented Generation for Knowledge-Intensive {NLP} Tasks},
  author    = {Lewis, Patrick and Perez, Ethan and Piktus, Aleksandra and
               Petroni, Fabio and Karpukhin, Vladimir and Goyal, Naman and
               K{\"u}ttler, Heinrich and Lewis, Mike and Yih, Wen-tau and
               Rockt{\"a}schel, Tim and Riedel, Sebastian and Kiela, Douwe},
  booktitle = {Advances in Neural Information Processing Systems},
  volume    = {33},
  pages     = {9459--9474},
  year      = {2020},
  url       = {https://proceedings.neurips.cc/paper/2020/hash/6b493230-Abstract.html}
}

@inproceedings{liu2024agentbench,
  title     = {{AgentBench}: Evaluating {LLM}s as Agents},
  author    = {Liu, Xiao and Yu, Hao and Zhang, Hanchen and Xu, Yifan and
               Lei, Xuanyu and Lai, Hanyu and Gu, Yu and Ding, Hangliang and
               Men, Kaiwen and Yang, Kejuan and Zhang, Shudan and Deng, Xiang and
               Zeng, Aohan and Du, Zhengxiao and Zhang, Chenhui and Shen, Sheng and
               Zhang, Tianjun and Su, Yu and Sun, Huan and Huang, Minlie and
               Dong, Yuxiao and Tang, Jie},
  booktitle = {The Twelfth International Conference on Learning Representations},
  year      = {2024},
  url       = {https://openreview.net/forum?id=zAdUB0aCTQ}
}

@inproceedings{christakopoulou2016towards,
  title     = {Towards Conversational Recommender Systems},
  author    = {Christakopoulou, Konstantina and Radlinski, Filip and Hofmann, Katja},
  booktitle = {Proceedings of the 22nd ACM SIGKDD International Conference on
               Knowledge Discovery and Data Mining},
  series    = {KDD '16},
  pages     = {815--824},
  year      = {2016},
  publisher = {Association for Computing Machinery},
  doi       = {10.1145/2939672.2939746},
  url       = {https://doi.org/10.1145/2939672.2939746}
}
```

## 5. Claim-safety checklist for the manuscript

- Use **"we implement and evaluate"**, not "we prove", when evidence comes from
  the repository's synthetic scenarios.
- Describe novelty as a **candidate contribution** until a broader systematic
  literature contrast and external benchmark are complete.
- Do not call an eight-scenario internal fixture a real-world deployment study.
- Keep published results from the five papers above in their original task
  contexts; do not compare percentages across incompatible datasets or metrics.
- Mark every unrun experiment, human evaluation, confidence interval, latency,
  or cost number as pending; never fabricate a result to fill the six-page paper.
- Cite primary proceedings/DOI records in the paper. Secondary summaries may
  help discovery but should not replace the archival citation.
