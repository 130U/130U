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
| [130U-FinLLM](https://github.com/130U/130U-FinLLM) | A training system for a compact financial language model, built around a **24.26M-parameter architecture**. Its objective is stance toward a specific asset, with training, recovery, and calibration integrated into the project. |

## Mathematical Finance

### Certified Valuation of Arithmetic Asian Options

Arithmetic averaging makes the option payoff difficult to handle analytically. I develop a weighted remainder from a Gaussian factor shared across observation dates, then connect it to validated transforms for the original projected Euler scheme.

This produces a complete discretization-error certificate below **0.011025 price units** for the paper's one-year Heston Asian call spread. A separate deterministic-variance coupling example reduces the nonlinear remainder width by **99.4%**.

The contribution brings the payoff's nonsmooth structure and the actual numerical implementation into one monetary error budget, making the accuracy of the reported valuation a mathematical claim that can be checked.

[Paper](https://github.com/130U/certified-valuation-arithmetic-asian-options/blob/main/manuscript/report.md) · [Research repository](https://github.com/130U/certified-valuation-arithmetic-asian-options) · [Results](https://github.com/130U/certified-valuation-arithmetic-asian-options/blob/main/EVIDENCE.md)

### Certified Joint Pricing Errors in Rough Heston

Prices at different strikes share the same Fourier transform. I preserve that dependence in the error calculation and propagate a continuous fractional Riccati residual into a joint certificate for the actual pricing output.

For the paper's quarter-year 4400–4500 call spread, the shared-error method reduces the complete upper bound from **0.252393939 to 0.233318843 index points**. It certifies a **0.25-point budget** that a matched marginal calculation leaves unresolved.

The work connects fractional dynamics to portfolio-level accuracy decisions. It shows why the geometry of shared numerical errors matters when a pricing method must meet an explicit tolerance.

[Paper](https://github.com/130U/certified-rough-heston-valuation/blob/main/ARTICLE.md) · [Research repository](https://github.com/130U/certified-rough-heston-valuation) · [Results](https://github.com/130U/certified-rough-heston-valuation/blob/main/EVIDENCE.md)

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
