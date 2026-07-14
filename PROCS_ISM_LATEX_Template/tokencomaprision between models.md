| Model | Metric | No-RAG | Catalog RAG | Delta |
|:---|:---|:---|:---|:---|
| **DeepSeek-V4-Flash** | Prompt tokens | ~1,310 | ~1,774 | +464 (35%) |
| | Completion tokens | ~2,183 | ~2,362 | +179 (8%) |
| | Total tokens | ~3,493 | ~4,136 | +643 (18%) |
| | RAG context (chars) | 0 | ~2,542 | — |
| **DeepSeek-V4-Pro** | Prompt tokens | ~1,310 | ~1,774 | +464 (35%) |
| | Completion tokens | ~2,407 | ~2,609 | +202 (8%) |
| | Total tokens | ~3,717 | ~4,383 | +666 (18%) |
| | RAG context (chars) | 0 | ~2,542 | — |

#### Architectural Takeaways from the Token Metrics
Input Determinism: 
Both models incur the exact same $35\%$ input penalty when target-side RAG is activated. This confirms that the retrieval pipeline behaves deterministically, injecting the exact same contextual schema payload regardless of the underlying LLM's architecture.
Reasoning Overhead in the Pro Model: 
The Pro model inherently generates roughly $10\%$ more completion tokens than Flash across the board (e.g., $2,407$ vs. $2,183$ in No-RAG). This quantifies the "heavy reasoning" overhead. Pro utilizes deeper internal Chain-of-Thought (CoT) traces and more verbose structural mapping to resolve ambiguity, which directly translates to higher token costs and slower inference times (the root cause of the timeouts observed in your earlier data).
Retrieval-Induced Verbosity: 
Supplying the model with RAG context slightly inflates output generation for both models by approximately $8\%$. While the models pull from the injected catalog to anchor their responses, RAG does not cause a runaway explosion in completion tokens. The cost of RAG is almost entirely localized to the input prompt phase ($O(n)$ context processing).