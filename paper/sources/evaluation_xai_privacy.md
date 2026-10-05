# Audited sources: evaluation, explainability, privacy, and reproducibility

Last audited: 2026-07-21  
Scope: SalePilot / RIVF 2026 paper, Track 2 (AI Applications)  
Evidence policy: publisher pages, official proceedings, standards, or original peer-reviewed papers only. ArXiv links are not used as the canonical citation when a proceedings version exists.

## Claim map for the paper

| Paper claim or design choice | Strongest sources | Safe wording | Boundary that must remain explicit |
|---|---|---|---|
| Report P@1, Hit@3, Recall@3, and nDCG@3 rather than one aggregate score | [E1], [E2] | Ranking metrics capture different properties; nDCG discounts lower-ranked items and supports graded relevance. | These metrics do not by themselves measure user satisfaction, explanation quality, or deployment impact. |
| Treat the synthetic fixture as functional evidence only | [E3], [E4], [E5] | Logged/offline evaluation is vulnerable to selection bias and protocol flaws; strong claims require realistic external data and fair baselines. | Do not call an eight-scenario synthetic fixture evidence of real-world superiority or generalization. |
| Compare stateful SalePilot with stateless and popularity baselines under the same protocol | [E5], [R1] | Strong baselines, identical data splits, and documented configurations are necessary for a meaningful comparison. | A baseline win is not a novelty or SOTA claim. |
| Add an external human evaluation for conversational quality | [H1], [H2], [H3], [H4], [H5] | Accuracy is only one part of user experience; conversational systems should also assess understanding, response quality, usefulness, satisfaction, and behavioral intention using clearly defined constructs. | `n = 80` conversations and two annotators are project design targets, not sample-size prescriptions from these sources; justify sample size separately. |
| Report agreement for human labels | [H4] | Chance-corrected agreement should be chosen to match the annotation scale and missing-data properties. | Do not report raw percent agreement alone, and do not interpret a coefficient without its assumptions and confidence interval. |
| Separate claim support from explanation quality and faithfulness | [X1], [X2], [X3], [X4] | Explanation goals differ and may conflict; human usefulness/plausibility and model faithfulness are separate evaluation targets. | Catalog-grounded reasons are traceable claim support, not proof that an LLM explanation faithfully exposes the model's internal causal process. |
| Keep research telemetry content-off by default and pseudonymous | [P1], [P2], [P3] | Data-minimized logs, retention/deletion controls, reduced linkability, and PII filtering are risk-reduction measures. | HMAC pseudonyms are not anonymity, differential privacy, or regulatory compliance. |
| Isolate untrusted retrieval/tool content | [P3], [P4] | LLM-integrated applications are exposed to direct and indirect prompt injection; deterministic authorization and tool boundaries are warranted. | Existing controls reduce attack surface but do not prove complete prompt-injection resistance. |
| Release manifests, code, exact commands, and immutable artifacts | [R1], [R2], [R3] | Documented, complete, exercisable artifacts make results more auditable and reproducible. | A self-run verifier is repeatability evidence; it is not an ACM badge or independent reproduction. |
| Report uncertainty and paired comparisons | [S1], [S2] | Bootstrap resampling can estimate sampling uncertainty; significance procedures must match the task, metric, and paired experimental design. | Resample at the independent experimental unit (here, conversation), not individual turns; do not present a confidence interval as an effect-size substitute. |

## A. Recommender metrics and offline-evaluation limitations

### [E1] Järvelin and Kekäläinen: cumulative gain and nDCG

- **Reference:** Kalervo Järvelin and Jaana Kekäläinen. “Cumulated Gain-Based Evaluation of IR Techniques.” *ACM Transactions on Information Systems*, 20(4):422–446, 2002.
- **Venue/year:** ACM TOIS, 2002 (peer-reviewed journal).
- **DOI:** [10.1145/582415.582418](https://doi.org/10.1145/582415.582418)
- **Canonical URL:** https://doi.org/10.1145/582415.582418
- **Exactly supported:** Cumulative-gain measures incorporate graded relevance and rank; normalized discounted cumulative gain enables comparison while discounting relevant material appearing lower in the ranking.
- **Use in SalePilot:** Cite when defining DCG/nDCG and explaining why the ordering of top-3 products matters.
- **Does not support:** That nDCG@3 alone represents conversational success, business value, or satisfaction.

```bibtex
@article{jarvelin2002cumulated,
  author  = {J{\"a}rvelin, Kalervo and Kek{\"a}l{\"a}inen, Jaana},
  title   = {Cumulated Gain-Based Evaluation of {IR} Techniques},
  journal = {ACM Transactions on Information Systems},
  year    = {2002},
  volume  = {20},
  number  = {4},
  pages   = {422--446},
  doi     = {10.1145/582415.582418}
}
```

### [E2] Herlocker et al.: recommender evaluation is multi-dimensional

- **Reference:** Jonathan L. Herlocker, Joseph A. Konstan, Loren G. Terveen, and John T. Riedl. “Evaluating Collaborative Filtering Recommender Systems.” *ACM Transactions on Information Systems*, 22(1):5–53, 2004.
- **Venue/year:** ACM TOIS, 2004 (peer-reviewed journal).
- **DOI:** [10.1145/963770.963772](https://doi.org/10.1145/963770.963772)
- **Canonical URL:** https://dl.acm.org/doi/10.1145/963770.963772
- **Exactly supported:** Evaluation choices depend on user task, dataset and analysis design, accuracy metric, non-accuracy attributes, and user-based evaluation; different metrics can form correlated groups rather than being interchangeable.
- **Use in SalePilot:** Justifies a metric panel and the separation of system-centric evaluation from human evaluation.
- **Does not support:** Any particular threshold for P@1, Recall@3, or nDCG@3.

```bibtex
@article{herlocker2004evaluating,
  author  = {Herlocker, Jonathan L. and Konstan, Joseph A. and Terveen, Loren G. and Riedl, John T.},
  title   = {Evaluating Collaborative Filtering Recommender Systems},
  journal = {ACM Transactions on Information Systems},
  year    = {2004},
  volume  = {22},
  number  = {1},
  pages   = {5--53},
  doi     = {10.1145/963770.963772}
}
```

### [E3] Schnabel et al.: selection bias in logged recommendation data

- **Reference:** Tobias Schnabel, Adith Swaminathan, Ashudeep Singh, Navin Chandak, and Thorsten Joachims. “Recommendations as Treatments: Debiasing Learning and Evaluation.” In *Proceedings of the 33rd International Conference on Machine Learning*, PMLR 48:1670–1679, 2016.
- **Venue/year:** ICML, 2016 (peer-reviewed proceedings).
- **DOI:** No DOI assigned by PMLR.
- **Canonical URL:** https://proceedings.mlr.press/v48/schnabel16.html
- **Exactly supported:** Recommender training and evaluation data are subject to selection bias from user self-selection and prior recommender actions; causal-inference estimators can correct bias under their assumptions.
- **Use in SalePilot:** Supports the limitation that historical interactions are not an unbiased relevance sample and that external evaluation needs a declared collection protocol.
- **Does not support:** Applying inverse propensity scoring when exposure propensities were not logged or cannot be defensibly estimated.

```bibtex
@inproceedings{schnabel2016recommendations,
  author    = {Schnabel, Tobias and Swaminathan, Adith and Singh, Ashudeep and Chandak, Navin and Joachims, Thorsten},
  title     = {Recommendations as Treatments: Debiasing Learning and Evaluation},
  booktitle = {Proceedings of the 33rd International Conference on Machine Learning},
  series    = {Proceedings of Machine Learning Research},
  volume    = {48},
  pages     = {1670--1679},
  year      = {2016},
  publisher = {PMLR},
  url       = {https://proceedings.mlr.press/v48/schnabel16.html}
}
```

### [E4] Hidasi and Czapp: common offline-protocol flaws

- **Reference:** Balázs Hidasi and Ádám Tibor Czapp. “Widespread Flaws in Offline Evaluation of Recommender Systems.” In *Proceedings of the 17th ACM Conference on Recommender Systems*, pp. 848–855, 2023.
- **Venue/year:** ACM RecSys, 2023 (peer-reviewed proceedings).
- **DOI:** [10.1145/3604915.3608839](https://doi.org/10.1145/3604915.3608839)
- **Canonical URL:** https://dl.acm.org/doi/10.1145/3604915.3608839
- **Exactly supported:** Offline evaluation is an imperfect proxy for interactive online performance; dataset–task mismatch, claims made from heavily preprocessed data, temporal leakage, and negative-item sampling can invalidate conclusions.
- **Use in SalePilot:** Cite in limitations and protocol design: group by conversation, freeze manifests, avoid leaked gold labels, and avoid extrapolating from the synthetic fixture.
- **Does not support:** That all offline evaluation is useless or that online A/B tests are automatically unbiased or reproducible.

```bibtex
@inproceedings{hidasi2023widespread,
  author    = {Hidasi, Bal{\'a}zs and Czapp, {\'A}d{\'a}m Tibor},
  title     = {Widespread Flaws in Offline Evaluation of Recommender Systems},
  booktitle = {Proceedings of the 17th ACM Conference on Recommender Systems},
  year      = {2023},
  pages     = {848--855},
  publisher = {ACM},
  doi       = {10.1145/3604915.3608839}
}
```

### [E5] Ferrari Dacrema et al.: baseline strength and reproducibility

- **Reference:** Maurizio Ferrari Dacrema, Paolo Cremonesi, and Dietmar Jannach. “Are We Really Making Much Progress? A Worrying Analysis of Recent Neural Recommendation Approaches.” In *Proceedings of the 13th ACM Conference on Recommender Systems*, pp. 101–109, 2019.
- **Venue/year:** ACM RecSys, 2019 (peer-reviewed proceedings).
- **DOI:** [10.1145/3298689.3347058](https://doi.org/10.1145/3298689.3347058)
- **Canonical URL:** https://dl.acm.org/doi/10.1145/3298689.3347058
- **Exactly supported:** In the authors' study of 18 recent neural top-N methods, only seven were reproducible with reasonable effort; six of those were often beaten by comparatively simple heuristics, and the remaining method did not consistently beat a tuned non-neural linear ranker.
- **Use in SalePilot:** Justifies the popularity and stateless baselines, identical evaluation conditions, and cautious language around improvements.
- **Does not support:** A universal conclusion that neural recommenders are inferior, or that SalePilot is superior because it beats one baseline.

```bibtex
@inproceedings{ferraridacrema2019progress,
  author    = {Ferrari Dacrema, Maurizio and Cremonesi, Paolo and Jannach, Dietmar},
  title     = {Are We Really Making Much Progress? A Worrying Analysis of Recent Neural Recommendation Approaches},
  booktitle = {Proceedings of the 13th ACM Conference on Recommender Systems},
  year      = {2019},
  pages     = {101--109},
  publisher = {ACM},
  doi       = {10.1145/3298689.3347058}
}
```

## B. Human evaluation of conversational recommendation

### [H1] Pu, Chen, and Hu: ResQue user-centric framework

- **Reference:** Pearl Pu, Li Chen, and Rong Hu. “A User-Centric Evaluation Framework for Recommender Systems.” In *Proceedings of the 5th ACM Conference on Recommender Systems*, pp. 157–164, 2011.
- **Venue/year:** ACM RecSys, 2011 (peer-reviewed proceedings).
- **DOI:** [10.1145/2043932.2043962](https://doi.org/10.1145/2043932.2043962)
- **Canonical URL:** https://dl.acm.org/doi/10.1145/2043932.2043962
- **Exactly supported:** ResQue uses psychometrically validated constructs spanning recommendation quality, usability, usefulness, interaction/interface quality, satisfaction, and behavioral intentions; the reported final model contains 15 constructs and 32 questions.
- **Use in SalePilot:** Provides a defensible source when selecting and adapting user-study constructs.
- **Does not support:** Copying all questions without translation validation, pilot testing, or context adaptation for Vietnamese appliance advice.

```bibtex
@inproceedings{pu2011usercentric,
  author    = {Pu, Pearl and Chen, Li and Hu, Rong},
  title     = {A User-Centric Evaluation Framework for Recommender Systems},
  booktitle = {Proceedings of the 5th ACM Conference on Recommender Systems},
  year      = {2011},
  pages     = {157--164},
  publisher = {ACM},
  doi       = {10.1145/2043932.2043962}
}
```

### [H2] Knijnenburg et al.: objective accuracy only partially explains experience

- **Reference:** Bart P. Knijnenburg, Martijn C. Willemsen, Zeno Gantner, Hakan Soncu, and Chris Newell. “Explaining the User Experience of Recommender Systems.” *User Modeling and User-Adapted Interaction*, 22(4–5):441–504, 2012.
- **Venue/year:** UMUAI, 2012 (peer-reviewed journal).
- **DOI:** [10.1007/s11257-011-9118-4](https://doi.org/10.1007/s11257-011-9118-4)
- **Canonical URL:** https://link.springer.com/article/10.1007/s11257-011-9118-4
- **Exactly supported:** Objective system aspects influence behavior through subjective perceptions and experience; the framework was examined using four field trials and two controlled experiments, and accuracy alone only partially constitutes user experience.
- **Use in SalePilot:** Supports measuring effort, perceived effectiveness, recommendation quality/variety, and choice satisfaction separately from ranking accuracy.
- **Does not support:** Treating subjective ratings as replacements for objective correctness and constraint checks.

```bibtex
@article{knijnenburg2012experience,
  author  = {Knijnenburg, Bart P. and Willemsen, Martijn C. and Gantner, Zeno and Soncu, Hakan and Newell, Chris},
  title   = {Explaining the User Experience of Recommender Systems},
  journal = {User Modeling and User-Adapted Interaction},
  year    = {2012},
  volume  = {22},
  number  = {4--5},
  pages   = {441--504},
  doi     = {10.1007/s11257-011-9118-4}
}
```

### [H3] Jin et al.: CRS-Que for conversational recommenders

- **Reference:** Yucheng Jin, Li Chen, Wanling Cai, and Xianglin Zhao. “CRS-Que: A User-Centric Evaluation Framework for Conversational Recommender Systems.” *ACM Transactions on Recommender Systems*, 2(1), Article 2, 1–34, 2024.
- **Venue/year:** ACM TORS, 2024 (peer-reviewed journal).
- **DOI:** [10.1145/3631534](https://doi.org/10.1145/3631534)
- **Canonical URL:** https://dl.acm.org/doi/10.1145/3631534
- **Exactly supported:** CRS-Que extends ResQue with conversation constructs such as understanding, response quality, and humanness; two studies reported evidence for construct validity/reliability and relationships between conversation, recommendation, and overall user experience.
- **Use in SalePilot:** Primary framework for a human evaluation of Vietnamese multi-turn advice; pre-register a small set of constructs rather than inventing an opaque “quality” score.
- **Does not support:** Automated LLM-as-judge as an equivalent substitute for human evaluation.

```bibtex
@article{jin2024crsque,
  author  = {Jin, Yucheng and Chen, Li and Cai, Wanling and Zhao, Xianglin},
  title   = {{CRS-Que}: A User-Centric Evaluation Framework for Conversational Recommender Systems},
  journal = {ACM Transactions on Recommender Systems},
  year    = {2024},
  volume  = {2},
  number  = {1},
  pages   = {1--34},
  articleno = {2},
  doi     = {10.1145/3631534}
}
```

### [H4] Artstein and Poesio: annotator agreement

- **Reference:** Ron Artstein and Massimo Poesio. “Survey Article: Inter-Coder Agreement for Computational Linguistics.” *Computational Linguistics*, 34(4):555–596, 2008.
- **Venue/year:** Computational Linguistics, 2008 (peer-reviewed journal).
- **DOI:** [10.1162/coli.07-034-R2](https://doi.org/10.1162/coli.07-034-R2)
- **Canonical URL:** https://aclanthology.org/J08-4004/
- **Exactly supported:** Agreement coefficients have different mathematical assumptions; alpha-like weighted coefficients may be more suitable than kappa-like measures for some annotation tasks, but their values remain context-dependent and nontrivial to interpret.
- **Use in SalePilot:** Choose agreement by measurement scale: nominal action labels versus ordinal Likert or relevance labels; state unit, missing-label handling, and uncertainty.
- **Does not support:** A universal “acceptable” kappa/alpha threshold.

```bibtex
@article{artstein2008agreement,
  author  = {Artstein, Ron and Poesio, Massimo},
  title   = {Survey Article: Inter-Coder Agreement for Computational Linguistics},
  journal = {Computational Linguistics},
  year    = {2008},
  volume  = {34},
  number  = {4},
  pages   = {555--596},
  doi     = {10.1162/coli.07-034-R2},
  url     = {https://aclanthology.org/J08-4004/}
}
```

### [H5] Howcroft et al.: human-evaluation reporting and definitions

- **Reference:** David M. Howcroft et al. “Twenty Years of Confusion in Human Evaluation: NLG Needs Evaluation Sheets and Standardised Definitions.” In *Proceedings of the 13th International Conference on Natural Language Generation*, pp. 169–182, 2020.
- **Venue/year:** INLG/ACL, 2020 (peer-reviewed proceedings).
- **DOI:** [10.18653/v1/2020.inlg-1.23](https://doi.org/10.18653/v1/2020.inlg-1.23)
- **Canonical URL:** https://aclanthology.org/2020.inlg-1.23/
- **Exactly supported:** Across 165 NLG papers with human evaluations, highly diverse terminology and under-specified methods harmed comparison and reproducibility; the authors call for standardized definitions and evaluation reporting.
- **Use in SalePilot:** Define every criterion operationally and report participant recruitment, prompts, presentation order, rating instrument, exclusions, compensation, annotation protocol, and analysis.
- **Does not support:** A particular evaluator count or universal questionnaire.

```bibtex
@inproceedings{howcroft2020confusion,
  author    = {Howcroft, David M. and Belz, Anya and Clinciu, Miruna-Adriana and Gkatzia, Dimitra and Hasan, Sadid A. and Mahamood, Saad and Mille, Simon and van Miltenburg, Emiel and Santhanam, Sashank and Rieser, Verena},
  title     = {Twenty Years of Confusion in Human Evaluation: {NLG} Needs Evaluation Sheets and Standardised Definitions},
  booktitle = {Proceedings of the 13th International Conference on Natural Language Generation},
  year      = {2020},
  pages     = {169--182},
  publisher = {Association for Computational Linguistics},
  doi       = {10.18653/v1/2020.inlg-1.23},
  url       = {https://aclanthology.org/2020.inlg-1.23/}
}
```

## C. Explainable recommendation and faithfulness

### [X1] Zhang and Chen: explainable recommendation taxonomy

- **Reference:** Yongfeng Zhang and Xu Chen. “Explainable Recommendation: A Survey and New Perspectives.” *Foundations and Trends in Information Retrieval*, 14(1):1–101, 2020.
- **Venue/year:** Foundations and Trends in Information Retrieval, 2020 (peer-reviewed monograph/journal survey).
- **DOI:** [10.1561/1500000066](https://doi.org/10.1561/1500000066)
- **Canonical URL:** https://www.nowpublishers.com/article/Details/INR-066
- **Exactly supported:** Explainable recommendation includes post-hoc and intrinsically interpretable approaches and targets multiple stakeholders and purposes, including transparency, trust, effectiveness, satisfaction, and debugging.
- **Use in SalePilot:** Positions catalog-grounded natural-language reasons within explainable recommendation, while distinguishing user-facing justification from internal model interpretation.
- **Does not support:** That any fluent natural-language reason is faithful or correct.

```bibtex
@article{zhang2020explainable,
  author  = {Zhang, Yongfeng and Chen, Xu},
  title   = {Explainable Recommendation: A Survey and New Perspectives},
  journal = {Foundations and Trends in Information Retrieval},
  year    = {2020},
  volume  = {14},
  number  = {1},
  pages   = {1--101},
  doi     = {10.1561/1500000066}
}
```

### [X2] Tintarev and Masthoff: explanation design goals

- **Reference:** Nava Tintarev and Judith Masthoff. “Explaining Recommendations: Design and Evaluation.” In *Recommender Systems Handbook*, 2nd ed., pp. 353–382, Springer, 2015.
- **Venue/year:** Recommender Systems Handbook, 2015 (peer-reviewed scholarly chapter).
- **DOI:** [10.1007/978-1-4899-7637-6_10](https://doi.org/10.1007/978-1-4899-7637-6_10)
- **Canonical URL:** https://link.springer.com/chapter/10.1007/978-1-4899-7637-6_10
- **Exactly supported:** Explanation evaluation should be tied to explicit goals, commonly including transparency, scrutability, trust, effectiveness, efficiency, persuasiveness, and satisfaction.
- **Use in SalePilot:** Pre-register which goals are evaluated. Recommended minimum: transparency/claim support, effectiveness, efficiency, trust, and satisfaction; do not collapse them without validation.
- **Does not support:** Optimizing persuasiveness at the expense of correctness or user autonomy.

```bibtex
@incollection{tintarev2015explaining,
  author    = {Tintarev, Nava and Masthoff, Judith},
  title     = {Explaining Recommendations: Design and Evaluation},
  booktitle = {Recommender Systems Handbook},
  edition   = {2},
  year      = {2015},
  pages     = {353--382},
  publisher = {Springer},
  doi       = {10.1007/978-1-4899-7637-6_10}
}
```

### [X3] Balog and Radlinski: explanation goals conflict

- **Reference:** Krisztian Balog and Filip Radlinski. “Measuring Recommendation Explanation Quality: The Conflicting Goals of Explanations.” In *Proceedings of the 43rd International ACM SIGIR Conference on Research and Development in Information Retrieval*, pp. 329–338, 2020.
- **Venue/year:** ACM SIGIR, 2020 (peer-reviewed proceedings).
- **DOI:** [10.1145/3397271.3401032](https://doi.org/10.1145/3397271.3401032)
- **Canonical URL:** https://dl.acm.org/doi/10.1145/3397271.3401032
- **Exactly supported:** The seven common explanation goals are structured and not independent; an explanation effective for one goal may be poor for another, and measurement design matters.
- **Use in SalePilot:** Report goal-specific results rather than a single “explainability score”; include item-wise or list-wise presentation details.
- **Does not support:** Inferring faithfulness from perceived trust, satisfaction, or persuasiveness.

```bibtex
@inproceedings{balog2020explanation,
  author    = {Balog, Krisztian and Radlinski, Filip},
  title     = {Measuring Recommendation Explanation Quality: The Conflicting Goals of Explanations},
  booktitle = {Proceedings of the 43rd International ACM SIGIR Conference on Research and Development in Information Retrieval},
  year      = {2020},
  pages     = {329--338},
  publisher = {ACM},
  doi       = {10.1145/3397271.3401032}
}
```

### [X4] Jacovi and Goldberg: faithfulness is a separate criterion

- **Reference:** Alon Jacovi and Yoav Goldberg. “Towards Faithfully Interpretable NLP Systems: How Should We Define and Evaluate Faithfulness?” In *Proceedings of the 58th Annual Meeting of the Association for Computational Linguistics*, pp. 4198–4205, 2020.
- **Venue/year:** ACL, 2020 (peer-reviewed proceedings).
- **DOI:** [10.18653/v1/2020.acl-main.386](https://doi.org/10.18653/v1/2020.acl-main.386)
- **Canonical URL:** https://aclanthology.org/2020.acl-main.386/
- **Exactly supported:** Interpretability criteria must be distinguished; faithfulness concerns correspondence to the model's actual process, its evaluation depends on assumptions, and a graded rather than binary treatment can be more useful.
- **Use in SalePilot:** Use precise language: `claim support` verifies that stated product facts occur in approved evidence; it does not expose the LLM's internal causal reasoning.
- **Does not support:** Calling provenance links or human-plausible explanations “faithful” without an intervention-based or otherwise justified faithfulness test.

```bibtex
@inproceedings{jacovi2020faithfulness,
  author    = {Jacovi, Alon and Goldberg, Yoav},
  title     = {Towards Faithfully Interpretable {NLP} Systems: How Should We Define and Evaluate Faithfulness?},
  booktitle = {Proceedings of the 58th Annual Meeting of the Association for Computational Linguistics},
  year      = {2020},
  pages     = {4198--4205},
  publisher = {Association for Computational Linguistics},
  doi       = {10.18653/v1/2020.acl-main.386},
  url       = {https://aclanthology.org/2020.acl-main.386/}
}
```

## D. Privacy and security for telemetry and LLM-integrated agents

### [P1] NIST Privacy Framework 1.0: minimized and disassociated logs

- **Reference:** National Institute of Standards and Technology. *NIST Privacy Framework: A Tool for Improving Privacy through Enterprise Risk Management, Version 1.0*. NIST CSWP 01162020, 2020.
- **Publisher/year:** NIST, 2020 (consensus-based government framework; not a peer-reviewed experiment).
- **DOI:** [10.6028/NIST.CSWP.01162020](https://doi.org/10.6028/NIST.CSWP.01162020)
- **Canonical URL:** https://doi.org/10.6028/NIST.CSWP.01162020
- **Exactly supported:** The framework calls for retention/deletion policy, audit/log records designed with data minimization (CT.DM-P8), reduced observability/linkability and identification (CT.DP-P1/P2), selective collection/disclosure, protection against leakage, and lifecycle alignment.
- **Use in SalePilot:** Maps directly to content-off telemetry, PII filtering, HMAC-based linkage reduction, restricted file permissions, retention policy, and deletion procedures.
- **Does not support:** A claim of NIST certification, legal compliance, anonymization, or zero privacy risk.

```bibtex
@techreport{nist2020privacy,
  author      = {{National Institute of Standards and Technology}},
  title       = {{NIST} Privacy Framework: A Tool for Improving Privacy through Enterprise Risk Management, Version 1.0},
  institution = {National Institute of Standards and Technology},
  year        = {2020},
  number      = {NIST CSWP 01162020},
  doi         = {10.6028/NIST.CSWP.01162020}
}
```

### [P2] Narayanan and Shmatikov: pseudonymous sparse records can be re-identified

- **Reference:** Arvind Narayanan and Vitaly Shmatikov. “Robust De-anonymization of Large Sparse Datasets.” In *Proceedings of the 2008 IEEE Symposium on Security and Privacy*, pp. 111–125, 2008.
- **Venue/year:** IEEE Symposium on Security and Privacy, 2008 (peer-reviewed proceedings).
- **DOI:** [10.1109/SP.2008.33](https://doi.org/10.1109/SP.2008.33)
- **Canonical URL:** https://ieeexplore.ieee.org/document/4531148
- **Exactly supported:** High-dimensional sparse preference records can be re-identified by linkage with limited auxiliary knowledge; removing direct identifiers does not necessarily make behavioral data anonymous.
- **Use in SalePilot:** Justifies minimizing quasi-identifiers and content, separating research telemetry from operational data, and avoiding an “anonymous telemetry” claim.
- **Does not support:** That SalePilot telemetry has been de-anonymized, or that HMAC pseudonymization provides no benefit.

```bibtex
@inproceedings{narayanan2008deanonymization,
  author    = {Narayanan, Arvind and Shmatikov, Vitaly},
  title     = {Robust De-anonymization of Large Sparse Datasets},
  booktitle = {Proceedings of the 2008 IEEE Symposium on Security and Privacy},
  year      = {2008},
  pages     = {111--125},
  publisher = {IEEE},
  doi       = {10.1109/SP.2008.33}
}
```

### [P3] NIST AI 600-1: GenAI privacy, provenance, and security actions

- **Reference:** Chloe Autio, Reva Schwartz, Jesse Dunietz, Shomik Jain, Martin Stanley, Elham Tabassi, Patrick Hall, and Kamie Roberts. *Artificial Intelligence Risk Management Framework: Generative Artificial Intelligence Profile*. NIST AI 600-1, 2024.
- **Publisher/year:** NIST, 2024 (government risk-management profile; not a peer-reviewed experiment).
- **DOI:** [10.6028/NIST.AI.600-1](https://doi.org/10.6028/NIST.AI.600-1)
- **Canonical URL:** https://doi.org/10.6028/NIST.AI.600-1
- **Exactly supported:** GenAI risks include PII leakage, unauthorized disclosure, de-anonymization, prompt injection, and component/value-chain risks. Suggested actions include monitoring PII exposure, defining collection/retention policy, tracking provenance with privacy/security considerations, removing PII where appropriate, representative human evaluation, empirical claim validation, source verification, and red-teaming prompt injection.
- **Use in SalePilot:** Supports the privacy-by-default telemetry, provenance manifest, PII tests, guarded web retrieval, source checks, red-team tests, and explicit generalization limits.
- **Does not support:** Treating a checklist mapping as evidence that all risks are controlled.

```bibtex
@techreport{autio2024genai,
  author      = {Autio, Chloe and Schwartz, Reva and Dunietz, Jesse and Jain, Shomik and Stanley, Martin and Tabassi, Elham and Hall, Patrick and Roberts, Kamie},
  title       = {Artificial Intelligence Risk Management Framework: Generative Artificial Intelligence Profile},
  institution = {National Institute of Standards and Technology},
  year        = {2024},
  number      = {NIST AI 600-1},
  doi         = {10.6028/NIST.AI.600-1}
}
```

### [P4] Greshake et al.: indirect prompt injection in LLM applications

- **Reference:** Kai Greshake, Sahar Abdelnabi, Shailesh Mishra, Christoph Endres, Thorsten Holz, and Mario Fritz. “Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection.” In *Proceedings of the 16th ACM Workshop on Artificial Intelligence and Security*, pp. 79–90, 2023.
- **Venue/year:** ACM AISec, co-located with CCS, 2023 (peer-reviewed workshop; Best Paper award).
- **DOI:** [10.1145/3605764.3623985](https://doi.org/10.1145/3605764.3623985)
- **Canonical URL:** https://dl.acm.org/doi/10.1145/3605764.3623985
- **Exactly supported:** Adversarial instructions placed in content likely to be retrieved can remotely manipulate LLM-integrated applications, including tool/API behavior and data disclosure; the paper demonstrates practical attack paths and a threat taxonomy.
- **Use in SalePilot:** Motivates treating retrieved web/knowledge content as untrusted data, enforcing allowlists and network restrictions outside the model, and authorizing each tool against server-side identity and scope.
- **Does not support:** A claim that allowlists, sanitization, or system prompts alone eliminate indirect prompt injection.

```bibtex
@inproceedings{greshake2023indirect,
  author    = {Greshake, Kai and Abdelnabi, Sahar and Mishra, Shailesh and Endres, Christoph and Holz, Thorsten and Fritz, Mario},
  title     = {Not What You've Signed Up For: Compromising Real-World {LLM}-Integrated Applications with Indirect Prompt Injection},
  booktitle = {Proceedings of the 16th ACM Workshop on Artificial Intelligence and Security},
  year      = {2023},
  pages     = {79--90},
  publisher = {ACM},
  doi       = {10.1145/3605764.3623985}
}
```

## E. Reproducibility and artifact claims

### [R1] Beel et al.: reproducibility in recommender research

- **Reference:** Jöran Beel, Corinna Breitinger, Stefan Langer, Andreas Lommatzsch, and Bela Gipp. “Towards Reproducibility in Recommender-Systems Research.” *User Modeling and User-Adapted Interaction*, 26(1):69–101, 2016.
- **Venue/year:** UMUAI, 2016 (peer-reviewed journal).
- **DOI:** [10.1007/s11257-016-9174-x](https://doi.org/10.1007/s11257-016-9174-x)
- **Canonical URL:** https://link.springer.com/article/10.1007/s11257-016-9174-x
- **Exactly supported:** Recommender results are often difficult to compare and reproduce because of inconsistent definitions, incomplete experiment reporting, varied platforms/datasets, and publication practices; the authors recommend more comprehensive experiments, frameworks, and best-practice guidance.
- **Use in SalePilot:** Supports frozen catalog/scenario manifests, dataset provenance, exact commands, versioned results, and explicit comparison boundaries.
- **Does not support:** That deterministic execution on one machine establishes external reproducibility.

```bibtex
@article{beel2016reproducibility,
  author  = {Beel, J{\"o}ran and Breitinger, Corinna and Langer, Stefan and Lommatzsch, Andreas and Gipp, Bela},
  title   = {Towards Reproducibility in Recommender-Systems Research},
  journal = {User Modeling and User-Adapted Interaction},
  year    = {2016},
  volume  = {26},
  number  = {1},
  pages   = {69--101},
  doi     = {10.1007/s11257-016-9174-x}
}
```

### [R2] Pineau et al.: reproducibility programs and checklists

- **Reference:** Joelle Pineau, Philippe Vincent-Lamarre, Koustuv Sinha, Vincent Larivière, Alina Beygelzimer, Florence d'Alché-Buc, Emily Fox, and Hugo Larochelle. “Improving Reproducibility in Machine Learning Research: A Report from the NeurIPS 2019 Reproducibility Program.” *Journal of Machine Learning Research*, 22(164):1–20, 2021.
- **Venue/year:** JMLR, 2021 (peer-reviewed journal).
- **DOI:** No DOI assigned by JMLR.
- **Canonical URL:** https://www.jmlr.org/papers/v22/20-303.html
- **Exactly supported:** Reproducibility aids reliability and robust workflows; the NeurIPS program combined a code-submission policy, a community reproducibility challenge, and a submission checklist, and the paper reports lessons from that intervention.
- **Use in SalePilot:** Supports a claim checklist, code/artifact release, and independently executable evaluation instructions.
- **Does not support:** That checklist completion guarantees a correct result.

```bibtex
@article{pineau2021reproducibility,
  author  = {Pineau, Joelle and Vincent-Lamarre, Philippe and Sinha, Koustuv and Larivi{\`e}re, Vincent and Beygelzimer, Alina and d'Alch{\'e}-Buc, Florence and Fox, Emily and Larochelle, Hugo},
  title   = {Improving Reproducibility in Machine Learning Research: A Report from the {NeurIPS} 2019 Reproducibility Program},
  journal = {Journal of Machine Learning Research},
  year    = {2021},
  volume  = {22},
  number  = {164},
  pages   = {1--20},
  url     = {https://www.jmlr.org/papers/v22/20-303.html}
}
```

### [R3] ACM Artifact Review and Badging policy

- **Reference:** Association for Computing Machinery. *Artifact Review and Badging, Version 1.1*. 24 August 2020.
- **Publisher/year:** ACM, 2020 (publisher standard/policy; not a peer-reviewed paper).
- **DOI:** No DOI assigned.
- **Canonical URL:** https://www.acm.org/publications/policies/artifact-review-and-badging-current
- **Exactly supported:** ACM distinguishes repeatability (same team/setup), reproducibility (different team using author artifacts), and replicability (different team and independently developed artifacts). “Artifacts Evaluated—Functional” requires documented, consistent, complete, exercisable artifacts with verification/validation evidence; “Artifacts Available” requires a permanent archival repository; independent validation is separately badged.
- **Use in SalePilot:** Describe the current verifier as same-team repeatability/functional evidence. Archive the released artifact with a persistent identifier and invite independent reproduction.
- **Does not support:** Claiming an ACM badge without ACM review, or calling a GitHub-only snapshot permanently archived.

```bibtex
@misc{acm2020artifact,
  author       = {{Association for Computing Machinery}},
  title        = {Artifact Review and Badging, Version 1.1},
  year         = {2020},
  howpublished = {ACM Publications Policy},
  url          = {https://www.acm.org/publications/policies/artifact-review-and-badging-current},
  note         = {Accessed 2026-07-21}
}
```

## F. Uncertainty and statistical comparison

### [S1] Efron: bootstrap resampling

- **Reference:** Bradley Efron. “Bootstrap Methods: Another Look at the Jackknife.” *The Annals of Statistics*, 7(1):1–26, 1979.
- **Venue/year:** Annals of Statistics, 1979 (peer-reviewed journal).
- **DOI:** [10.1214/aos/1176344552](https://doi.org/10.1214/aos/1176344552)
- **Canonical URL:** https://projecteuclid.org/journals/annals-of-statistics/volume-7/issue-1/Bootstrap-Methods-Another-Look-at-the-Jackknife/10.1214/aos/1176344552.full
- **Exactly supported:** Introduces bootstrap resampling as a general method for estimating the sampling distribution of a statistic from observed data.
- **Use in SalePilot:** Supports bootstrap uncertainty intervals. The paper protocol must independently justify conversation-level resampling as the unit that approximates independent sampling.
- **Does not support:** Arbitrary bootstrap validity with very small samples, dependent turn-level observations, or an undocumented interval construction.

```bibtex
@article{efron1979bootstrap,
  author  = {Efron, Bradley},
  title   = {Bootstrap Methods: Another Look at the Jackknife},
  journal = {The Annals of Statistics},
  year    = {1979},
  volume  = {7},
  number  = {1},
  pages   = {1--26},
  doi     = {10.1214/aos/1176344552}
}
```

### [S2] Dror et al.: tests must fit task, setup, and metric

- **Reference:** Rotem Dror, Gili Baumer, Segev Shlomov, and Roi Reichart. “The Hitchhiker's Guide to Testing Statistical Significance in Natural Language Processing.” In *Proceedings of the 56th Annual Meeting of the Association for Computational Linguistics*, pp. 1383–1392, 2018.
- **Venue/year:** ACL, 2018 (peer-reviewed proceedings).
- **DOI:** [10.18653/v1/P18-1128](https://doi.org/10.18653/v1/P18-1128)
- **Canonical URL:** https://aclanthology.org/P18-1128/
- **Exactly supported:** Significance-test selection depends on task, experimental setup, metric properties, and test assumptions; statistical testing is often omitted or misused in empirical NLP.
- **Use in SalePilot:** Use paired comparisons on the same conversations, state assumptions, report effect sizes and uncertainty, and avoid multiple uncorrected metric-wise declarations.
- **Does not support:** A blanket recommendation of one statistical test for every SalePilot metric.

```bibtex
@inproceedings{dror2018significance,
  author    = {Dror, Rotem and Baumer, Gili and Shlomov, Segev and Reichart, Roi},
  title     = {The Hitchhiker's Guide to Testing Statistical Significance in Natural Language Processing},
  booktitle = {Proceedings of the 56th Annual Meeting of the Association for Computational Linguistics},
  year      = {2018},
  pages     = {1383--1392},
  publisher = {Association for Computational Linguistics},
  doi       = {10.18653/v1/P18-1128},
  url       = {https://aclanthology.org/P18-1128/}
}
```

## Recommended citation placement in the six-page paper

1. **Introduction:** [E2], [X1], [H3] to motivate multi-turn conversational recommendation, multi-dimensional evaluation, and explainable advice.
2. **Related work:** [E3]–[E5] for evaluation limits/fair baselines; [H1]–[H3] for user-centric CRS evaluation; [X2]–[X4] for explanation goals versus faithfulness; [P3]–[P4] for GenAI risk and prompt injection.
3. **Method:** [P1], [P3], [P4] next to telemetry minimization, provenance, identity/tool authorization, and untrusted-content boundaries.
4. **Evaluation protocol:** [E1]–[E5], [H3]–[H5], [S1]–[S2]. State that conversations, not turns, are the independent resampling/split unit.
5. **Results:** avoid significance stars without assumptions; report metric value, paired delta, 95% interval, denominator, and number of conversations.
6. **Limitations:** [E3], [E4], [P2], [X3], [X4], [R3]. Explicitly separate synthetic repeatability, external human evidence, real-world deployment impact, privacy risk reduction, and independent reproduction.

## Claims currently prohibited by this evidence set

- “SalePilot is state of the art,” “novel,” or “superior in real-world deployment.”
- “The synthetic benchmark proves customer satisfaction, business benefit, or generalization.”
- “The explanations are faithful” when only catalog claim support or human plausibility was measured.
- “Telemetry is anonymous,” “NIST compliant/certified,” or “privacy guaranteed.”
- “The system is secure against prompt injection”; use “implements tested risk-reduction boundaries.”
- “Results are reproduced” before an independent team obtains them; current local verification is repeatability evidence.
- “Two annotators and 80 conversations are statistically sufficient” without a power/precision analysis and a declared sampling population.
