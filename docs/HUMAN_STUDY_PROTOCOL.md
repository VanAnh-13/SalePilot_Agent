# Human Study Protocol — SalePilot RIVF Track 2

## Overview

This protocol governs the human evaluation of SalePilot's recommendation quality,
following the CRS-Que construct framework (Jin et al., 2024). The study involves
two Vietnamese domain annotators evaluating a blinded annotation pool.

**Study goal:** Assess explanation quality, recommendation usefulness, and 
response understanding from the perspective of Vietnamese retail customers.

---

## Annotators

- **N = 2** Vietnamese domain annotators
- **Domain knowledge:** Vietnamese retail / appliance category (1+ year experience)  
- **Language:** Native or C2 Vietnamese; basic English for rubric reading
- **Independence:** Annotations submitted independently before adjudication
- **Conflicts:** Annotators must not be authors or co-developers of SalePilot

---

## Annotation Pool Construction

### Source Conversations
- Real conversation templates from `C:\Downloads\DMX_product\chat_history_buy_product.json`
- Supplemented with synthesized multi-turn dialogues matching the 12 benchmark categories

### Blinding Protocol
1. Remove all system metadata (agent turn IDs, backend source, timestamps)
2. Remove SKU codes — replace with `Sản phẩm A`, `Sản phẩm B`, `Sản phẩm C`
3. Keep price, brand, and specifications visible
4. Do NOT indicate which condition generated the recommendation

### Pool Size
- **Target:** 30–50 conversations (minimum 10 per category for top-5 categories)
- **Turn structure:** Include single-turn, multi-turn, and clarification cases

---

## CRS-Que Constructs (Jin et al., 2024)

Each conversation is rated on 5 constructs (7-point Likert scale):

| Construct | Vietnamese Label | Definition |
|---|---|---|
| **Understanding** | Hiểu nhu cầu | Does the system understand the customer's need? |
| **Response Quality** | Chất lượng trả lời | Is the response clear, complete, and well-structured? |
| **Usefulness** | Tính hữu ích | Would you find these recommendations useful in real life? |
| **Satisfaction** | Hài lòng tổng thể | Overall satisfaction with the conversation |
| **Trust** | Tin tưởng | Do you trust the recommendations and explanations? |

**Scale:** 1 (strongly disagree) → 7 (strongly agree)

---

## Annotation Instructions

### Session Setup
- Each annotator receives the blinded pool in randomized order
- Each session should take 60–90 minutes maximum
- Annotators work independently with no communication during annotation

### Per-Conversation Task
For each blinded conversation:

1. Read the full conversation from customer start to system recommendation
2. Rate each of the 5 CRS-Que constructs (1–7)
3. Mark any **hard constraint violation** visible to the customer:
   - Did a recommended product clearly exceed the stated budget?
   - Did a product fail a dimension/size constraint mentioned by the customer?
4. Optional free-text comment (Vietnamese preferred, max 100 words)

### Rubric Card (give to annotators)

```
Mỗi hội thoại: đọc kỹ từ đầu đến cuối, rồi đánh giá:

1. Hiểu nhu cầu (1-7): Hệ thống hiểu đúng yêu cầu của khách không?
   1=Không hiểu gì  7=Hiểu hoàn toàn chính xác

2. Chất lượng trả lời (1-7): Câu trả lời rõ ràng, đầy đủ, dễ hiểu?
   1=Rất kém  7=Rất tốt

3. Tính hữu ích (1-7): Bạn sẽ dùng gợi ý này thực tế không?
   1=Hoàn toàn vô dụng  7=Rất hữu ích

4. Hài lòng tổng thể (1-7): Bạn hài lòng với cuộc trò chuyện này không?
   1=Rất không hài lòng  7=Rất hài lòng

5. Tin tưởng (1-7): Bạn tin vào các gợi ý và giải thích được đưa ra không?
   1=Không tin chút nào  7=Hoàn toàn tin tưởng

Ràng buộc cứng: Có sản phẩm nào vượt ngân sách/kích thước khách đã nêu? (Có/Không)
```

---

## Inter-Annotator Agreement

Following Artstein & Poesio (2008):

- **Ordinal scale (Likert 1–7):** Use weighted Cohen's κ (quadratic weights)
- **Nominal binary (hard constraint):** Use Cohen's κ  
- **Target agreement:** κ ≥ 0.60 (substantial) before aggregation
- **If κ < 0.40 (fair):** Adjudication session required; record adjudicated values

### Adjudication Process
1. Present both annotations to adjudicator (third party or authors)
2. Adjudicator reads conversation and both annotations
3. Records final consensus value with brief rationale
4. Documents disagreement cases in `human_study/adjudication_log.jsonl`

---

## Data Format

### Annotation Output (`human_study/annotations_raw.jsonl`)
One line per annotator per conversation:
```json
{
  "conv_id": "hs-001",
  "annotator_id": "A1",
  "understanding": 6,
  "response_quality": 5,
  "usefulness": 7,
  "satisfaction": 6,
  "trust": 5,
  "hard_constraint_violation": false,
  "comment": "Gợi ý phù hợp, giải thích rõ ràng về giá và kích thước."
}
```

### Aggregated Output (`human_study/annotations_aggregated.jsonl`)
After adjudication:
```json
{
  "conv_id": "hs-001",
  "kappa": 0.72,
  "understanding_mean": 5.5,
  "response_quality_mean": 5.0,
  "usefulness_mean": 7.0,
  "satisfaction_mean": 6.0,
  "trust_mean": 5.0,
  "hard_constraint_violation": false
}
```

---

## Statistical Analysis

1. **Descriptive stats:** Mean ± SD per construct across all conversations
2. **Constraint violation rate:** Compare annotator-labeled vs. system-computed
3. **Bootstrap CIs:** 1,000 bootstrap resamples of conversations (not turns)
4. **Effect sizes:** Cohen's d for condition differences if multiple conditions annotated

---

## Ethics and Privacy

- No real customer data collected during the study
- All conversations use synthetic/template-based dialogues or heavily paraphrased real queries
- Annotator identities are pseudonymized in any publication (A1, A2)
- No personally identifiable information in annotation outputs
- Annotation files not committed to public repository without full IRB clearance

---

## Timeline

| Step | Target |
|---|---|
| Pool construction and blinding | Session 012 |
| Annotator briefing | Session 012 |
| Independent annotation | Sessions 012–013 |
| Agreement computation | Session 013 |
| Adjudication (if needed) | Session 013 |
| Results integrated into paper | Session 014 |

---

## References

- Jin et al. (2024). CRS-Que. ACM TORS. doi:10.1145/3631534
- Artstein & Poesio (2008). Inter-Coder Agreement. Computational Linguistics. doi:10.1162/coli.07-034-R2
- Efron (1979). Bootstrap Methods. Annals of Statistics. doi:10.1214/aos/1176344552
