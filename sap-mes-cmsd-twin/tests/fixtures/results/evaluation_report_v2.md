# Paper Evaluation Report v2 (n=20)

**Generated:** 2026-05-29T15:43:23.506675+00:00

**Models:** deepseek-flash

**Total experiments:** 640

## RAG Ablation by Model

| Model | RAG Mode | Experiments | Avg Accuracy | String Acc | Numeric Acc |
|---|---|---|---|---|---|
| deepseek-flash | full_rag | 16 | 95.2% | 98.1% | 94.4% |
| deepseek-flash | no_rag | 16 | 95.2% | 98.1% | 94.6% |

## Accuracy by Field Type (Single-instance, Full RAG)

| Model | Entity | Overall | String | Numeric | Null-prone |
|---|---|---|---|---|---|
| deepseek-flash | Order | 100.0% | 100.0% | None% | None% |
| deepseek-flash | Order | 100.0% | 100.0% | None% | None% |
| deepseek-flash | Order | 100.0% | 100.0% | None% | None% |
| deepseek-flash | Order | 100.0% | 100.0% | None% | None% |
| deepseek-flash | PartType | 97.0% | 100.0% | 100.0% | None% |
| deepseek-flash | PartType | 98.0% | 100.0% | 100.0% | None% |
| deepseek-flash | PartType | 97.0% | 100.0% | 100.0% | None% |
| deepseek-flash | PartType | 99.0% | 100.0% | 100.0% | None% |
| deepseek-flash | Resource | 94.8% | 100.0% | 100.0% | 100.0% |
| deepseek-flash | Resource | 98.8% | 100.0% | 100.0% | 100.0% |
| deepseek-flash | Resource | 97.5% | 85.7% | 100.0% | 100.0% |
| deepseek-flash | Resource | 44.8% | 100.0% | 57.1% | 0.0% |
| deepseek-flash | ResourceClass | 100.0% | 100.0% | 100.0% | None% |
| deepseek-flash | ResourceClass | 100.0% | 100.0% | 100.0% | None% |
| deepseek-flash | ResourceClass | 99.2% | 100.0% | 100.0% | None% |
| deepseek-flash | ResourceClass | 96.7% | 100.0% | 100.0% | None% |

## Field Type Classification

| Entity | String Fields | Numeric Fields | Null-prone Fields |
|---|---|---|---|
| Resource | 7 | 7 | 6 |
| ResourceClass | 5 | 1 | 0 |
| Order | 4 | 0 | 0 |
| PartType | 4 | 1 | 0 |
