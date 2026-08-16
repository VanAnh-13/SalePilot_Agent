# Audited literature: conversational recommendation and multi-agent/tool-grounded LLMs

Tra cứu ngày: **2026-07-21**. Phạm vi này được đóng băng cho bài SalePilot/RIVF: conversational recommender systems (CRS), preference elicitation nhiều lượt, grounding bằng retrieval/tool, và orchestration LLM đa-agent. Tất cả nguồn dưới đây là bài **đã qua peer review** trên trang publisher/proceedings chính thức; không dùng blog và không dùng bản arXiv-only làm nguồn chính. Các mô tả “supports” chỉ giới hạn ở kết quả mà bài gốc báo cáo, không phải bằng chứng SalePilot đạt cùng kết quả và không phải tuyên bố novelty.

## Citation map và claim được phép dùng

| ID | Nguồn đã kiểm tra | Claim có thể dùng trong bài SalePilot | Biên diễn giải bắt buộc |
|---|---|---|---|
| S1 | Jannach, Manzoor, Cai, and Chen, “A Survey on Conversational Recommender Systems,” *ACM Computing Surveys*, 54(5), Article 105, 1–36, 2021. DOI: [10.1145/3453154](https://doi.org/10.1145/3453154). | CRS mở rộng recommendation một chiều bằng preference elicitation, hỏi đáp về đề xuất và feedback; survey cũng phân loại hệ theo intents, knowledge và cách đánh giá. Dùng để định nghĩa bài toán và taxonomy. | Là survey, không chứng minh một kiến trúc cụ thể tốt hơn hay SalePilot hiệu quả. |
| S2 | Jannach, “Evaluating Conversational Recommender Systems: A Landscape of Research,” *Artificial Intelligence Review*, 56(3), 2365–2400, 2023. DOI: [10.1007/s10462-022-10229-x](https://doi.org/10.1007/s10462-022-10229-x). | CRS là hệ đa thành phần; đánh giá recommendation cô lập thường không đủ và nên kết hợp objective/component metrics với subjective/user perception. Dùng để biện minh thiết kế benchmark ngoài và human evaluation. | Không được trình bày offline metrics hiện có như bằng chứng UX hoặc deployment effectiveness. |
| S3 | Wang, Tang, Zhao, Wang, and Wen, “Rethinking the Evaluation for Conversational Recommendation in the Era of Large Language Models,” *EMNLP 2023*, 10052–10065. DOI: [10.18653/v1/2023.emnlp-main.621](https://doi.org/10.18653/v1/2023.emnlp-main.621). | Giao thức chỉ khớp ground-truth item có thể bỏ qua tính tương tác của CRS; bài đề xuất iEvaLM dùng user simulator để mô phỏng nhiều kịch bản tương tác. Dùng để giải thích vì sao cần đánh giá turn-level/action-level thay vì chỉ item hit. | LLM simulator không tự động thay thế user study; SalePilot không được claim “realistic” nếu chưa kiểm định simulator với người thật. |
| S4 | Manzoor, Ziegler, Pirker Garcia, and Jannach, “ChatGPT as a Conversational Recommender System: A User-Centric Analysis,” *UMAP 2024*, 267–272. DOI: [10.1145/3627043.3659574](https://doi.org/10.1145/3627043.3659574). | Trong user-centric study ở miền phim, information adequacy và recommendation accuracy là các yếu tố mạnh đối với perceived meaningfulness; BLEU/METEOR/ROUGE chỉ tương quan yếu (không metric nào vượt 0.2) với đánh giá meaningfulness. Dùng để biện minh annotation bởi người và rubric về adequacy/accuracy. | Kết quả chỉ trên ChatGPT và miền phim; không được chuyển con số hay kết luận thắng hệ khác sang điện máy/SalePilot. |
| S5 | Chen and Pu, “Critiquing-based Recommenders: Survey and Emerging Trends,” *User Modeling and User-Adapted Interaction*, 22(1–2), 125–150, 2012. DOI: [10.1007/s11257-011-9108-6](https://doi.org/10.1007/s11257-011-9108-6). | Feedback dạng critique qua nhiều vòng giúp cập nhật user profile và cải tiến đề xuất kế tiếp; survey tổng hợp natural-language, system-suggested và user-initiated critiques. Dùng cho state update khi người dùng nói “rẻ hơn/nhỏ hơn/không hãng này”. | Không suy ra memory implementation hiện tại là tối ưu; các user studies và domain trong survey khác SalePilot. |
| S6 | Christakopoulou, Radlinski, and Hofmann, “Towards Conversational Recommender Systems,” *KDD 2016*, 815–824. DOI: [10.1145/2939672.2939746](https://doi.org/10.1145/2939672.2939746). | Bài hình thức hóa chọn câu hỏi để nhanh chóng elicitate preference trong cold start. Tác giả báo cáo cải thiện recommendation 25% sau hai câu hỏi trong thiết lập của họ. Dùng làm động lực cho câu hỏi làm rõ có chọn lọc. | Con số 25% không phải baseline hay kỳ vọng cho SalePilot; domain, dữ liệu và model đều khác. |
| S7 | Zhang, Chen, Ai, Yang, and Croft, “Towards Conversational Search and Recommendation: System Ask, User Respond,” *CIKM 2018*, 177–186. DOI: [10.1145/3269206.3271776](https://doi.org/10.1145/3269206.3271776). | Paradigm System Ask–User Respond chủ động hỏi thuộc tính để thu preference qua nhiều lượt; phù hợp để mô tả slot acquisition và decision “clarify hay recommend”. | Không được gọi SalePilot là implementation hoặc reproduction của SAUR nếu chưa dùng cùng model/protocol. |
| S8 | Lei, He, Miao, Wu, Hong, Kan, and Chua, “Estimation–Action–Reflection: Towards Deep Interaction Between Conversational and Recommender Systems,” *WSDM 2020*, 304–312. DOI: [10.1145/3336191.3371769](https://doi.org/10.1145/3336191.3371769). | EAR tách ba vấn đề: ước lượng preference item/attribute, chọn hỏi hay recommend dựa trên history, và cập nhật sau rejection. Đây là prior gần cho vòng `state → action → feedback update` của SalePilot. | SalePilot không dùng EAR training/model; chỉ được so sánh ở mức decomposition và cần baseline thực nghiệm nếu muốn so hiệu quả. |
| S9 | Li, Ebrahimi Kahou, Schulz, Michalski, Charlin, and Pal, “Towards Deep Conversational Recommendations,” *NeurIPS 2018*, 9748–9758. Proceedings: [official NeurIPS page](https://proceedings.neurips.cc/paper/2018/hash/800de15c79c8d840f4e78d3af937d4d4-Abstract.html). DOI: không được NeurIPS gán. | Giới thiệu ReDial với hơn 10.000 hội thoại recommendation thực và kiến trúc kết hợp dialogue, sentiment và recommendation components. Dùng làm precedent cho benchmark hội thoại và multi-component CRS. | ReDial là miền phim; không thể dùng score ReDial để đối chiếu trực tiếp với synthetic appliance scenarios. |
| S10 | Moon, Shah, Kumar, and Subba, “OpenDialKG: Explainable Conversational Reasoning with Attention-based Walks over Knowledge Graphs,” *ACL 2019*, 845–854. DOI: [10.18653/v1/P19-1081](https://doi.org/10.18653/v1/P19-1081). | OpenDialKG nối utterance với entity/path KG và tạo walk path cho entity được retrieve, cung cấp một cơ chế giải thích reasoning hội thoại. Dùng để đặt provenance/path-based explanation trong related work. | SalePilot hiện cung cấp source/tool trace, không phải KG-walk explanation; không được đánh đồng hai dạng giải thích. |
| S11 | Lewis et al., “Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks,” *NeurIPS 2020*, 9459–9474. Proceedings: [official NeurIPS page](https://proceedings.neurips.cc/paper/2020/hash/6b493230-Abstract.html). DOI: không được NeurIPS gán. | RAG kết hợp parametric generator với explicit non-parametric memory; trong các task được thử nghiệm, output factual hơn parametric-only baseline. Dùng làm nền cho việc tách LLM khỏi catalog/knowledge store có thể cập nhật và lưu provenance. | Không được claim retrieval của SalePilot “eliminates hallucination” nếu chưa đo factuality trên dữ liệu SalePilot. |
| S12 | Shuster, Poff, Chen, Kiela, and Weston, “Retrieval Augmentation Reduces Hallucination in Conversation,” *Findings of EMNLP 2021*, 3784–3803. DOI: [10.18653/v1/2021.findings-emnlp.320](https://doi.org/10.18653/v1/2021.findings-emnlp.320). | Neural-retrieval-in-the-loop giảm knowledge hallucination theo human evaluation trong hai knowledge-grounded conversation tasks của bài. Dùng để biện minh grounded response generation và factuality evaluation. | Hiệu ứng phụ thuộc task/model của bài; source retrieval sai vẫn có thể làm SalePilot trả lời sai. |
| S13 | Yao et al., “ReAct: Synergizing Reasoning and Acting in Language Models,” *ICLR 2023*. Official paper: [OpenReview](https://openreview.net/forum?id=WE_vluYUL-X). DOI: không được ICLR gán. | ReAct xen kẽ reasoning và task actions để mô hình lấy thông tin từ external sources/environments rồi cập nhật kế hoạch. Dùng làm prior cho vòng orchestrator → tool → observation → next action. | Chỉ viện dẫn design pattern; không công bố hidden chain-of-thought và không claim SalePilot tái lập benchmark ReAct. |
| S14 | Guo et al., “Large Language Model Based Multi-agents: A Survey of Progress and Challenges,” *IJCAI 2024 Survey Track*, 8048–8057. DOI: [10.24963/ijcai.2024/890](https://doi.org/10.24963/ijcai.2024/890). | Survey tổ chức LLM multi-agent theo domain/settings, agent profiling, communication và skill development, đồng thời chỉ ra các thách thức. Dùng để đặt Lead–specialist orchestration trong taxonomy multi-agent. | Survey không chứng minh nhiều agent luôn tốt hơn một agent; SalePilot cần ablation single-agent/tool-only. |
| S15 | Nie et al., “A Hybrid Multi-Agent Conversational Recommender System with LLM and Search Engine in E-commerce,” *RecSys 2024*, 745–747. DOI: [10.1145/3640457.3688061](https://doi.org/10.1145/3640457.3688061). | Prior gần nhất về domain/architecture: central LLM agent phối hợp search agent trong e-commerce. Tác giả báo cáo giảm khoảng 70% first-token latency và giảm LLM inferences/request từ 2 xuống 1, được kiểm tra bằng online A/B trong hệ của họ. Dùng làm related system và động lực đo latency/cost. | Đây là industry paper 3 trang và hệ độc quyền khác SalePilot; không được claim tương đương hoặc vượt nếu chưa reproduce một baseline công bằng. |
| S16 | Huang, Lian, Lei, Yao, Lian, and Xie, “Recommender AI Agent: Integrating Large Language Models for Interactive Recommendations,” *ACM Transactions on Information Systems*, 43(4), Article 96, 1–33, 2025. DOI: [10.1145/3731446](https://doi.org/10.1145/3731446). | InteRecAgent dùng LLM làm planner/interface và domain recommender models làm tools; có short/long-term profiles, task planning và reflection. Bài đánh giá trên ba public datasets. Đây là comparator kiến trúc mạnh cho SalePilot. | Muốn claim đóng góp hơn InteRecAgent phải có khác biệt được formalize và benchmark/ablation công bằng; hiện chỉ có thể nói SalePilot áp dụng pattern vào catalog constrained Vietnamese appliance decision support với safety/provenance boundaries. |

## Citation spine đề xuất cho bài 6 trang

- **Định nghĩa và research gap:** S1, S2.
- **Multi-turn state/preference elicitation:** S5, S7, S8.
- **Grounded and explainable responses:** S10, S11, S12.
- **Tool/multi-agent architecture và comparator gần nhất:** S13, S14, S15, S16.
- **Evaluation protocol:** S2, S3, S4. Nếu thiếu chỗ, giữ S2 và S3; S4 dùng để biện minh human rubric.
- **Dataset precedent:** S9 chỉ dùng khi thảo luận vì sao cần corpus hội thoại ngoài; không dùng ReDial như một baseline trực tiếp cho điện máy.

Một câu positioning an toàn, chưa phải novelty claim:

> SalePilot studies a tool-grounded, role-specialized conversational decision-support architecture for Vietnamese appliance recommendation, combining explicit multi-turn constraint state, catalog-bounded actions, provenance-bearing responses, and lifecycle/privacy controls. Its scientific value must be established against single-agent, stateless, and retrieval/ranking baselines through grouped conversational evaluation and human assessment.

## BibTeX đã chuẩn hóa

```bibtex
@article{jannach2021survey,
  author    = {Dietmar Jannach and Ahtsham Manzoor and Wanling Cai and Li Chen},
  title     = {A Survey on Conversational Recommender Systems},
  journal   = {ACM Computing Surveys},
  volume    = {54},
  number    = {5},
  articleno = {105},
  pages     = {1--36},
  year      = {2021},
  publisher = {Association for Computing Machinery},
  doi       = {10.1145/3453154},
  url       = {https://doi.org/10.1145/3453154}
}

@article{jannach2023evaluating,
  author  = {Dietmar Jannach},
  title   = {Evaluating Conversational Recommender Systems: A Landscape of Research},
  journal = {Artificial Intelligence Review},
  volume  = {56},
  number  = {3},
  pages   = {2365--2400},
  year    = {2023},
  doi     = {10.1007/s10462-022-10229-x},
  url     = {https://doi.org/10.1007/s10462-022-10229-x}
}

@inproceedings{wang2023rethinking,
  author    = {Xiaolei Wang and Xinyu Tang and Xin Zhao and Jingyuan Wang and Ji-Rong Wen},
  title     = {Rethinking the Evaluation for Conversational Recommendation in the Era of Large Language Models},
  booktitle = {Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing},
  pages     = {10052--10065},
  year      = {2023},
  publisher = {Association for Computational Linguistics},
  doi       = {10.18653/v1/2023.emnlp-main.621},
  url       = {https://aclanthology.org/2023.emnlp-main.621/}
}

@inproceedings{manzoor2024chatgpt,
  author    = {Ahtsham Manzoor and Samuel C. Ziegler and Klaus Maria Pirker Garcia and Dietmar Jannach},
  title     = {{ChatGPT} as a Conversational Recommender System: A User-Centric Analysis},
  booktitle = {Proceedings of the 32nd ACM Conference on User Modeling, Adaptation and Personalization},
  pages     = {267--272},
  year      = {2024},
  publisher = {Association for Computing Machinery},
  doi       = {10.1145/3627043.3659574},
  url       = {https://doi.org/10.1145/3627043.3659574}
}

@article{chen2012critiquing,
  author  = {Li Chen and Pearl Pu},
  title   = {Critiquing-based Recommenders: Survey and Emerging Trends},
  journal = {User Modeling and User-Adapted Interaction},
  volume  = {22},
  number  = {1--2},
  pages   = {125--150},
  year    = {2012},
  doi     = {10.1007/s11257-011-9108-6},
  url     = {https://doi.org/10.1007/s11257-011-9108-6}
}

@inproceedings{christakopoulou2016towards,
  author    = {Konstantina Christakopoulou and Filip Radlinski and Katja Hofmann},
  title     = {Towards Conversational Recommender Systems},
  booktitle = {Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining},
  pages     = {815--824},
  year      = {2016},
  publisher = {Association for Computing Machinery},
  doi       = {10.1145/2939672.2939746},
  url       = {https://doi.org/10.1145/2939672.2939746}
}

@inproceedings{zhang2018systemask,
  author    = {Yongfeng Zhang and Xu Chen and Qingyao Ai and Liu Yang and W. Bruce Croft},
  title     = {Towards Conversational Search and Recommendation: System Ask, User Respond},
  booktitle = {Proceedings of the 27th ACM International Conference on Information and Knowledge Management},
  pages     = {177--186},
  year      = {2018},
  publisher = {Association for Computing Machinery},
  doi       = {10.1145/3269206.3271776},
  url       = {https://doi.org/10.1145/3269206.3271776}
}

@inproceedings{lei2020ear,
  author    = {Wenqiang Lei and Xiangnan He and Yisong Miao and Qingyun Wu and Richang Hong and Min-Yen Kan and Tat-Seng Chua},
  title     = {Estimation--Action--Reflection: Towards Deep Interaction Between Conversational and Recommender Systems},
  booktitle = {Proceedings of the 13th International Conference on Web Search and Data Mining},
  pages     = {304--312},
  year      = {2020},
  publisher = {Association for Computing Machinery},
  doi       = {10.1145/3336191.3371769},
  url       = {https://doi.org/10.1145/3336191.3371769}
}

@inproceedings{li2018redial,
  author    = {Raymond Li and Samira Ebrahimi Kahou and Hannes Schulz and Vincent Michalski and Laurent Charlin and Chris Pal},
  title     = {Towards Deep Conversational Recommendations},
  booktitle = {Advances in Neural Information Processing Systems},
  volume    = {31},
  pages     = {9748--9758},
  year      = {2018},
  url       = {https://proceedings.neurips.cc/paper/2018/hash/800de15c79c8d840f4e78d3af937d4d4-Abstract.html}
}

@inproceedings{moon2019opendialkg,
  author    = {Seungwhan Moon and Pararth Shah and Anuj Kumar and Rajen Subba},
  title     = {{OpenDialKG}: Explainable Conversational Reasoning with Attention-based Walks over Knowledge Graphs},
  booktitle = {Proceedings of the 57th Annual Meeting of the Association for Computational Linguistics},
  pages     = {845--854},
  year      = {2019},
  publisher = {Association for Computational Linguistics},
  doi       = {10.18653/v1/P19-1081},
  url       = {https://aclanthology.org/P19-1081/}
}

@inproceedings{lewis2020rag,
  author    = {Patrick Lewis and Ethan Perez and Aleksandra Piktus and Fabio Petroni and Vladimir Karpukhin and Naman Goyal and Heinrich K{\"u}ttler and Mike Lewis and Wen-tau Yih and Tim Rockt{\"a}schel and Sebastian Riedel and Douwe Kiela},
  title     = {Retrieval-Augmented Generation for Knowledge-Intensive {NLP} Tasks},
  booktitle = {Advances in Neural Information Processing Systems},
  volume    = {33},
  pages     = {9459--9474},
  year      = {2020},
  url       = {https://proceedings.neurips.cc/paper/2020/hash/6b493230-Abstract.html}
}

@inproceedings{shuster2021retrieval,
  author    = {Kurt Shuster and Spencer Poff and Moya Chen and Douwe Kiela and Jason Weston},
  title     = {Retrieval Augmentation Reduces Hallucination in Conversation},
  booktitle = {Findings of the Association for Computational Linguistics: EMNLP 2021},
  pages     = {3784--3803},
  year      = {2021},
  publisher = {Association for Computational Linguistics},
  doi       = {10.18653/v1/2021.findings-emnlp.320},
  url       = {https://aclanthology.org/2021.findings-emnlp.320/}
}

@inproceedings{yao2023react,
  author    = {Shunyu Yao and Jeffrey Zhao and Dian Yu and Nan Du and Izhak Shafran and Karthik Narasimhan and Yuan Cao},
  title     = {{ReAct}: Synergizing Reasoning and Acting in Language Models},
  booktitle = {The Eleventh International Conference on Learning Representations},
  year      = {2023},
  url       = {https://openreview.net/forum?id=WE_vluYUL-X}
}

@inproceedings{guo2024multiagents,
  author    = {Taicheng Guo and Xiuying Chen and Yaqi Wang and Ruidi Chang and Shichao Pei and Nitesh V. Chawla and Olaf Wiest and Xiangliang Zhang},
  title     = {Large Language Model Based Multi-agents: A Survey of Progress and Challenges},
  booktitle = {Proceedings of the Thirty-Third International Joint Conference on Artificial Intelligence},
  pages     = {8048--8057},
  year      = {2024},
  publisher = {International Joint Conferences on Artificial Intelligence Organization},
  doi       = {10.24963/ijcai.2024/890},
  url       = {https://www.ijcai.org/proceedings/2024/890}
}

@inproceedings{nie2024hybrid,
  author    = {Guangtao Nie and Rong Zhi and Xiaofan Yan and Yufan Du and Xiangyang Zhang and Jianwei Chen and Mi Zhou and Hongshen Chen and Tianhao Li and Ziguang Cheng and Sulong Xu and Jinghe Hu},
  title     = {A Hybrid Multi-Agent Conversational Recommender System with {LLM} and Search Engine in E-commerce},
  booktitle = {Proceedings of the 18th ACM Conference on Recommender Systems},
  pages     = {745--747},
  year      = {2024},
  publisher = {Association for Computing Machinery},
  doi       = {10.1145/3640457.3688061},
  url       = {https://doi.org/10.1145/3640457.3688061}
}

@article{huang2025interecagent,
  author    = {Xu Huang and Jianxun Lian and Yuxuan Lei and Jing Yao and Defu Lian and Xing Xie},
  title     = {Recommender {AI} Agent: Integrating Large Language Models for Interactive Recommendations},
  journal   = {ACM Transactions on Information Systems},
  volume    = {43},
  number    = {4},
  articleno = {96},
  pages     = {1--33},
  year      = {2025},
  publisher = {Association for Computing Machinery},
  doi       = {10.1145/3731446},
  url       = {https://doi.org/10.1145/3731446}
}
```

## Audit notes

- DOI và metadata được đối chiếu trên ACM Digital Library, SpringerLink, ACL Anthology, IJCAI Proceedings, NeurIPS Proceedings hoặc OpenReview chính thức; URL trong BibTeX trỏ trực tiếp tới version of record/proceedings.
- S9, S11 và S13 không có DOI do proceedings tương ứng không gán DOI cho record; URL proceedings là locator chính, không thay bằng DOI arXiv.
- S15 là nguồn tương đồng trực tiếp nhất với e-commerce multi-agent CRS nhưng quá ngắn để làm duy nhất một technical baseline. S16 là comparator method đầy đủ hơn cho tool orchestration và memory.
- Chưa có nguồn nào trong danh mục chứng minh tổ hợp cụ thể của SalePilot là mới. Novelty chỉ có thể nêu sau khi contrast kiến trúc chi tiết, chạy ablation/baselines và hoàn tất external human benchmark.
