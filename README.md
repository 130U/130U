# Theodore Ouyang

**AI research, software engineering, and mathematical finance.**

<div align="center">
  <picture>
    <source media="(max-width: 767px) and (prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/130U/130U/main/assets/generated/hero-mobile-dark-v3.svg">
    <source media="(max-width: 767px) and (prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/130U/130U/main/assets/generated/hero-mobile-light-v3.svg">
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/130U/130U/main/assets/generated/hero-dark-v3.svg">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/130U/130U/main/assets/generated/hero-light-v3.svg">
    <img src="assets/generated/hero-light-v3.svg" alt="130U — Artificial Intelligence and Engineering. Agent evaluation, applied AI, and research tools; earlier research in mathematical finance." width="100%">
  </picture>
</div>

I study how numerical errors affect option prices and how evaluation feedback should guide changes to AI agents. I also build software for financial text analysis and personal research, and write about robotics and technology adoption.

My projects combine mathematical research with working software. The links below lead to the papers, implementations, and results.

<p align="center">
  <a href="#artificial-intelligence-and-engineering">Artificial Intelligence and Engineering</a>
  &nbsp;&middot;&nbsp;
  <a href="#mathematical-finance">Mathematical Finance</a>
</p>

## Artificial Intelligence and Engineering

| Project | Contribution |
| --- | --- |
| [Agent Evaluation Methodology](https://github.com/130U/agent-evaluation-methodology) | **ICFA**, a method for deciding which evaluation feedback belongs in an agent's prompt update. It connects the diagnosis to what the agent knew, who produced the behavior, and what the optimizer can change. |
| [Research Portfolio](https://github.com/130U/reserach-portfolio-since2026) | Technical analysis of robotics and world models: how language becomes continuous robot action, what different model architectures learn, and what their delivery models mean for adoption. |
| [BaZi Context Agent](https://github.com/130U/bazi-context-agent) | An interactive interpretation system that compares uncertain birth-hour candidates, fixes a working selection, and introduces personal context through a separate reporting layer. |
| [Info Collector](https://github.com/130U/info-collector-2026) | A reading application that turns saved webpages into translations, summaries, and a searchable local library, with a weekly review of what was read. |
| [130U-FinLLM](https://github.com/130U/130U-FinLLM) | A native PyTorch system for training a **24.26M-parameter financial language model from random initialization**, with asset-specific stance supervision, corpus preparation, recoverable training, and calibrated evaluation. |

### 130U-FinLLM: Financial Language Modeling from Scratch

I built **130U-FinLLM**, a native PyTorch training and evaluation system for financial language modeling from random initialization. Its **24.26M-parameter decoder** and self-trained 8K tokenizer address a precise problem: identifying bearish, neutral, or bullish stance toward a specified asset. I implemented corpus preparation, pretraining, supervised fine-tuning, and preference-training experiments, with separate data partitions for model selection, probability calibration, review thresholds, and final testing.

The pipeline prepared **42.47 million additional training tokens**, with seed and candidate evaluation documents excluded. Training recovery restores the optimizer, scheduler, random state, and corpus position; calibration artifacts remain tied to their checkpoint and tokenizer. This brings data engineering, model training, and evaluation into a working research system. The public records document pretraining progress; financial stance accuracy has not yet been evaluated.

[Research repository](https://github.com/130U/130U-FinLLM) · [Model specification](https://github.com/130U/130U-FinLLM/blob/main/docs/MODEL_CARD.md) · [Training and validation](https://github.com/130U/130U-FinLLM/blob/main/docs/STATUS.md)

## Mathematical Finance

### Certified Valuation of Arithmetic Asian Options

I develop a mathematical framework for certifying discretization error in arithmetic Asian valuation. Its core is a weighted payoff-remainder bound derived from a Gaussian factor shared across observation dates. This connects the payoff’s nonsmooth structure to computable moment bounds, which I combine with validated transforms for the original projected Euler scheme under Heston stochastic volatility.

In the paper’s one-year Heston Asian call-spread example with twelve monthly fixings, the framework establishes a complete discretization-error bound below **0.011025 price units**. The contribution connects payoff analysis, stochastic dynamics and validated computation to give a rigorous monetary guarantee for the discrete valuation.

[Paper](https://github.com/130U/certified-valuation-arithmetic-asian-options/blob/main/manuscript/report.md) · [Research repository](https://github.com/130U/certified-valuation-arithmetic-asian-options) · [Results](https://github.com/130U/certified-valuation-arithmetic-asian-options/blob/main/EVIDENCE.md)

### Certified Joint Pricing Errors in Rough Heston

I establish a deterministic framework for joint pricing-error certification in rough Heston. A finite-history theorem carries continuous fractional Riccati residuals into the pricing exponent, while a joint error set preserves the Fourier perturbations shared across strikes. Together, these results provide rigorous bounds for spreads and portfolio valuations sharing the same model and maturity.

For the paper’s quarter-year **4400–4500 call spread**, the framework certifies the stored numerical output with a complete error upper bound of **0.233318843 index points**, meeting a **0.25-point accuracy budget**. The certificate includes quadrature, omitted frequencies, the infinite tail and arithmetic, connecting fractional dynamics to a checkable guarantee for the valuation.

[Paper](https://github.com/130U/certified-rough-heston-valuation/blob/main/ARTICLE.md) · [Research repository](https://github.com/130U/certified-rough-heston-valuation) · [Results](https://github.com/130U/certified-rough-heston-valuation/blob/main/EVIDENCE.md)

### Critical Dependence Stress for Diversification Gains

I develop a reverse stress-testing theory for a precise portfolio decision: how much can dependence change before a diversification gain disappears, with every marginal loss distribution held fixed? For small reallocations in an exchangeable box model, I derive a **common quadratic law** for the stress budgets that produce a tie or a strict reversal. The analysis connects a variational limit with exact marginal restoration and identifies the extra cost that local sensitivity alone misses.

In the independent uniform benchmark with median Expected Shortfall, equal exposures, and transport weights (1, 1, 2), I bound the critical coefficient between **0.203125 and 0.302083...**, **at least 30% above** the tangent prediction of 0.15625. The paper also characterizes when the restoration premium vanishes and uses continuous maximum-flow/minimum-cut duality to explain how the background portfolio absorbs stress.

[Paper](https://github.com/130U/mathematical-finance-project/blob/main/paper/paper.pdf) · [Research repository](https://github.com/130U/mathematical-finance-project) · [Results](https://github.com/130U/mathematical-finance-project/blob/main/docs/results.md)

## GitHub Contributions

<div align="center">
  <picture>
    <source media="(max-width: 767px) and (prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/130U/130U/main/assets/generated/telemetry-mobile-dark-v4.svg?v=pink-20261011">
    <source media="(max-width: 767px) and (prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/130U/130U/main/assets/generated/telemetry-mobile-light-v4.svg?v=pink-20261011">
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/130U/130U/main/assets/generated/telemetry-dark-v4.svg?v=pink-20261011">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/130U/130U/main/assets/generated/telemetry-light-v4.svg?v=pink-20261011">
    <img src="assets/generated/telemetry-light-v4.svg?v=pink-20261011" alt="GitHub contributions in the last 30 days, sourced from the public GitHub profile and refreshed daily." width="100%">
  </picture>
</div>

<sub>Updated daily from GitHub's public contribution calendar. [Update history](https://github.com/130U/130U/actions/workflows/update-profile.yml) · [Data sources](docs/profile-data.md)</sub>
