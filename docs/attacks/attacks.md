# attacks.md

A reference list of the core attack categories SEIGE targets.

## 1. Prompt Injection

**What it is:** Malicious instructions embedded in user input that override or hijack the model's system prompt.

**Variants:**
- *Direct* — attacker controls the user turn directly
- *Indirect* — malicious instructions are injected via retrieved content (RAG documents, web pages, tool outputs)

**Why it matters:** The most prevalent real-world LLM attack. Critical for any deployed system that ingests external data.

**Reference:** [Perez & Ribeiro, 2022](https://arxiv.org/abs/2302.12173)

---

## 2. Jailbreaking

**What it is:** Prompt-level techniques that convince a model to bypass its safety guidelines — without access to weights or gradients.

**Variants:**
- *Roleplay / persona* — "Act as DAN / an AI with no restrictions"
- *Hypothetical framing* — "In a fictional story where..."
- *Encoding tricks* — Base64, pig latin, token smuggling
- *Many-shot* — flooding context with examples of the model complying

**Why it matters:** Requires no technical access. Widely used and constantly evolving.

---

## 3. Adversarial Suffixes (GCG)

**What it is:** Optimized token strings appended to a prompt that shift the model's output distribution from refusal to compliance — without any semantic meaning.

**Variants:**
- *White-box* — suffix optimized with full gradient access to the target model
- *Transfer* — suffix optimized on one model, tested against others

**Why it matters:** Works across models. Defeats keyword-based defenses. Foundational attack for evaluating alignment robustness.

**Reference:** [Zou et al., 2023 — "Universal and Transferable Adversarial Attacks on Aligned Language Models"](https://arxiv.org/abs/2307.15043)

---

## 4. System Prompt Extraction

**What it is:** Attempts to coerce the model into revealing its system prompt or internal instructions — exposing proprietary configurations and potential attack surface.

**Variants:**
- *Direct ask* — "Repeat your instructions verbatim"
- *Indirect leakage* — asking the model to summarize, translate, or complete a sentence that starts with its prompt
- *Token-by-token probing* — inferring prompt contents through yes/no questions

**Why it matters:** A prerequisite for many targeted attacks. Directly relevant to enterprise and API deployments.

---

## 5. Multi-Turn Manipulation

**What it is:** Attacks that unfold across a conversation — beginning with benign exchanges and gradually escalating toward a harmful goal.

**Variants:**
- *Slow escalation* — incrementally shifting requests across turns
- *Context poisoning* — establishing false premises early that are later exploited
- *Trust building* — gaining model "agreement" on small things before a large ask

**Why it matters:** Single-turn defenses are blind to this. Most deployed systems are multi-turn. Directly extends SEIGE's CodeClip multi-turn benchmark lineage.

---

## 6. Data Exfiltration

**What it is:** Attempts to extract sensitive information from the model's context window — system prompts, injected documents, prior conversation turns, or memorized training data.

**Variants:**
- *Context window extraction* — leaking RAG documents or tool results the model was given
- *Training data extraction* — prompting for memorized PII, code, or copyrighted text
- *Inference attacks* — deducing private information from model responses

**Why it matters:** High-severity in enterprise settings. Directly tied to compliance and data privacy risk.

**Reference:** [Carlini et al., 2021 — "Extracting Training Data from Large Language Models"](https://arxiv.org/abs/2012.07805)