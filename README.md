<picture>
  <source media="(max-width: 767px) and (prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/130U/130U/main/assets/generated/hero-mobile-dark-v5.svg">
  <source media="(max-width: 767px) and (prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/130U/130U/main/assets/generated/hero-mobile-light-v5.svg">
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/130U/130U/main/assets/generated/hero-dark-v5.svg">
  <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/130U/130U/main/assets/generated/hero-light-v5.svg">
  <img src="assets/generated/hero-light-v5.svg" alt="Theodore Ouyang — AI Engineering & Finance. Models, agents, and mathematical research." width="100%">
</picture>

I build AI systems and develop mathematical methods for financial decisions.

<p>
<a href="#user-content-ai-engineering"><img src="assets/layout/nav-ai-v2.svg" width="168" height="38" alt="01 / AI Engineering"></a>
<a href="#user-content-finance"><img src="assets/layout/nav-finance-v2.svg" width="120" height="38" alt="02 / Finance"></a>
</p>

<br>

<a id="ai-engineering"></a>
<table width="100%"><tr><td>

<picture>
  <source media="(prefers-color-scheme: dark) and (max-width: 767px)" srcset="https://raw.githubusercontent.com/130U/130U/main/assets/layout/sheet-ai-mobile-dark-v2.svg">
  <source media="(max-width: 767px)" srcset="https://raw.githubusercontent.com/130U/130U/main/assets/layout/sheet-ai-mobile-light-v2.svg">
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/130U/130U/main/assets/layout/sheet-ai-dark-v2.svg">
  <img src="assets/layout/sheet-ai-light-v2.svg" width="1200" alt="AI Engineering — models, agents, and research tools">
</picture>

<h3><sub>01</sub> &nbsp; Agent Evaluation Methodology</h3>
<p>I develop <strong>ICFA</strong>, a method for deciding which evaluation feedback belongs in an agent’s prompt update. It connects the diagnosis to what the agent knew, who produced the behavior, and what the optimizer can change.</p>
<p><a href="https://github.com/130U/agent-evaluation-methodology"><img src="assets/layout/button-repository-v2.svg" width="100" height="32" alt="Repository — Agent Evaluation Methodology"></a></p>

<hr>

<h3><sub>02</sub> &nbsp; 130U-FinLLM</h3>
<p><strong>24.26M parameters · 42.47M additional training tokens prepared</strong></p>
<p>I built a native PyTorch system for asset-specific financial language modeling from random initialization, with a self-trained tokenizer, complete checkpoint recovery, and separate data partitions for selection, calibration, and testing. <em>Financial stance accuracy remains unevaluated.</em></p>
<p><a href="https://github.com/130U/130U-FinLLM"><img src="assets/layout/button-repository-v2.svg" width="100" height="32" alt="Repository — 130U-FinLLM"></a>
<a href="https://github.com/130U/130U-FinLLM/blob/main/docs/MODEL_CARD.md"><img src="assets/layout/button-model-v2.svg" width="76" height="32" alt="Model card — 130U-FinLLM"></a>
<a href="https://github.com/130U/130U-FinLLM/blob/main/docs/STATUS.md"><img src="assets/layout/button-training-v2.svg" width="80" height="32" alt="Training — 130U-FinLLM"></a></p>
<details>
<summary>Method &amp; evidence</summary>
<br>
<p>I built <strong>130U-FinLLM</strong>, a native PyTorch training and evaluation system for financial language modeling from random initialization. Its <strong>24.26M-parameter decoder</strong> and self-trained 8K tokenizer address a precise problem: identifying bearish, neutral, or bullish stance toward a specified asset. I implemented corpus preparation, pretraining, supervised fine-tuning, and preference-training experiments, with separate data partitions for model selection, probability calibration, review thresholds, and final testing.</p>
<p>The pipeline prepared <strong>42.47 million additional training tokens</strong>, with seed and candidate evaluation documents excluded. Training recovery restores the optimizer, scheduler, random state, and corpus position; calibration artifacts remain tied to their checkpoint and tokenizer. This brings data engineering, model training, and evaluation into a working research system. The public records document pretraining progress; financial stance accuracy has not yet been evaluated.</p>
</details>

<hr>

<h3><sub>03</sub> &nbsp; Research Portfolio</h3>
<p>Technical analysis of robotics and world models: how language becomes continuous robot action, what architectures learn, and what delivery models mean for adoption.</p>
<p><a href="https://github.com/130U/reserach-portfolio-since2026"><img src="assets/layout/button-analysis-v2.svg" width="96" height="32" alt="Analysis — Research Portfolio"></a></p>

<hr>

<h3><sub>04</sub> &nbsp; BaZi Context Agent</h3>
<p>An interactive interpretation system that compares uncertain birth-hour candidates, fixes a working selection, and introduces personal context through a separate reporting layer.</p>
<p><a href="https://github.com/130U/bazi-context-agent"><img src="assets/layout/button-repository-v2.svg" width="100" height="32" alt="Repository — BaZi Context Agent"></a></p>

<hr>

<h3><sub>05</sub> &nbsp; Info Collector</h3>
<p>A reading application that turns saved webpages into translations, summaries, and a searchable local library, with a weekly review of what was read.</p>
<p><a href="https://github.com/130U/info-collector-2026"><img src="assets/layout/button-repository-v2.svg" width="100" height="32" alt="Repository — Info Collector"></a></p>

</td></tr></table>

<br>
<br>

<a id="finance"></a>
<table width="100%"><tr><td>

<picture>
  <source media="(prefers-color-scheme: dark) and (max-width: 767px)" srcset="https://raw.githubusercontent.com/130U/130U/main/assets/layout/sheet-finance-mobile-dark-v2.svg">
  <source media="(max-width: 767px)" srcset="https://raw.githubusercontent.com/130U/130U/main/assets/layout/sheet-finance-mobile-light-v2.svg">
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/130U/130U/main/assets/layout/sheet-finance-dark-v2.svg">
  <img src="assets/layout/sheet-finance-light-v2.svg" width="1200" alt="Finance — mathematical research in valuation and risk">
</picture>

<h3><sub>01</sub> &nbsp; Arithmetic Asian Options</h3>
<p>I connect payoff analysis, stochastic dynamics, and validated computation to certify discretization error. A shared Gaussian factor yields a weighted payoff-remainder bound. The paper’s one-year Heston Asian call spread with twelve monthly fixings has a complete discretization-error bound below <strong>0.011025 price units</strong>.</p>
<p><a href="https://github.com/130U/certified-valuation-arithmetic-asian-options/blob/main/manuscript/report.md"><img src="assets/layout/button-paper-v2.svg" width="72" height="32" alt="Paper — Arithmetic Asian Options"></a>
<a href="https://github.com/130U/certified-valuation-arithmetic-asian-options"><img src="assets/layout/button-repository-v2.svg" width="100" height="32" alt="Repository — Arithmetic Asian Options"></a>
<a href="https://github.com/130U/certified-valuation-arithmetic-asian-options/blob/main/EVIDENCE.md"><img src="assets/layout/button-results-v2.svg" width="80" height="32" alt="Results — Arithmetic Asian Options"></a></p>
<details>
<summary>Method &amp; evidence</summary>
<br>
<p>I develop a mathematical framework for certifying discretization error in arithmetic Asian valuation. Its core is a weighted payoff-remainder bound derived from a Gaussian factor shared across observation dates. This connects the payoff’s nonsmooth structure to computable moment bounds, which I combine with validated transforms for the original projected Euler scheme under Heston stochastic volatility.</p>
<p>In the paper’s one-year Heston Asian call-spread example with twelve monthly fixings, the framework establishes a complete discretization-error bound below <strong>0.011025 price units</strong>. The contribution connects payoff analysis, stochastic dynamics and validated computation to give a rigorous monetary guarantee for the discrete valuation.</p>
</details>

<hr>

<h3><sub>02</sub> &nbsp; Joint Pricing Errors in Rough Heston</h3>
<p>I establish joint pricing-error bounds that retain Fourier perturbations shared across strikes, using a finite-history theorem for fractional Riccati residuals. For the paper’s quarter-year 4400–4500 call spread, the stored output has a complete error upper bound of <strong>0.233318843 index points</strong>, meeting a <strong>0.25-point budget</strong>.</p>
<p><a href="https://github.com/130U/certified-rough-heston-valuation/blob/main/ARTICLE.md"><img src="assets/layout/button-paper-v2.svg" width="72" height="32" alt="Paper — Joint Pricing Errors in Rough Heston"></a>
<a href="https://github.com/130U/certified-rough-heston-valuation"><img src="assets/layout/button-repository-v2.svg" width="100" height="32" alt="Repository — Joint Pricing Errors in Rough Heston"></a>
<a href="https://github.com/130U/certified-rough-heston-valuation/blob/main/EVIDENCE.md"><img src="assets/layout/button-results-v2.svg" width="80" height="32" alt="Results — Joint Pricing Errors in Rough Heston"></a></p>
<details>
<summary>Method &amp; evidence</summary>
<br>
<p>I establish a deterministic framework for joint pricing-error certification in rough Heston. A finite-history theorem carries continuous fractional Riccati residuals into the pricing exponent, while a joint error set preserves the Fourier perturbations shared across strikes. Together, these results provide rigorous bounds for spreads and portfolio valuations sharing the same model and maturity.</p>
<p>For the paper’s quarter-year <strong>4400–4500 call spread</strong>, the framework certifies the stored numerical output with a complete error upper bound of <strong>0.233318843 index points</strong>, meeting a <strong>0.25-point accuracy budget</strong>. The certificate includes quadrature, omitted frequencies, the infinite tail and arithmetic, connecting fractional dynamics to a checkable guarantee for the valuation.</p>
</details>

<hr>

<h3><sub>03</sub> &nbsp; Critical Dependence Stress</h3>
<p>For small reallocations in an exchangeable box model, I derive a <strong>common quadratic law</strong> for the dependence-stress budgets that erase or reverse diversification gains under fixed marginals. In the independent uniform benchmark with median Expected Shortfall, equal exposures, and transport weights (1, 1, 2), the critical coefficient is <strong>at least 30% above</strong> the tangent prediction.</p>
<p><a href="https://github.com/130U/mathematical-finance-project/blob/main/paper/paper.pdf"><img src="assets/layout/button-paper-v2.svg" width="72" height="32" alt="Paper — Critical Dependence Stress"></a>
<a href="https://github.com/130U/mathematical-finance-project"><img src="assets/layout/button-repository-v2.svg" width="100" height="32" alt="Repository — Critical Dependence Stress"></a>
<a href="https://github.com/130U/mathematical-finance-project/blob/main/docs/results.md"><img src="assets/layout/button-results-v2.svg" width="80" height="32" alt="Results — Critical Dependence Stress"></a></p>
<details>
<summary>Method &amp; evidence</summary>
<br>
<p>I develop a reverse stress-testing theory for a precise portfolio decision: how much can dependence change before a diversification gain disappears, with every marginal loss distribution held fixed? For small reallocations in an exchangeable box model, I derive a <strong>common quadratic law</strong> for the stress budgets that produce a tie or a strict reversal. The analysis connects a variational limit with exact marginal restoration and identifies the extra cost that local sensitivity alone misses.</p>
<p>In the independent uniform benchmark with median Expected Shortfall, equal exposures, and transport weights (1, 1, 2), I bound the critical coefficient between <strong>0.203125 and 0.302083...</strong>, <strong>at least 30% above</strong> the tangent prediction of 0.15625. The paper also characterizes when the restoration premium vanishes and uses continuous maximum-flow/minimum-cut duality to explain how the background portfolio absorbs stress.</p>
</details>

</td></tr></table>

<br>

<!-- PROFILE_ACTIVITY -->

---

<picture>
  <source media="(max-width: 767px) and (prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/130U/130U/main/assets/generated/telemetry-mobile-dark-v5.svg">
  <source media="(max-width: 767px) and (prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/130U/130U/main/assets/generated/telemetry-mobile-light-v5.svg">
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/130U/130U/main/assets/generated/telemetry-dark-v5.svg">
  <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/130U/130U/main/assets/generated/telemetry-light-v5.svg">
  <img src="assets/generated/telemetry-light-v5.svg" alt="GitHub contributions in the last 30 days, with a daily contribution trace. Updated from the public GitHub calendar." width="100%">
</picture>

<sub>[Activity updates](https://github.com/130U/130U/actions/workflows/update-profile.yml) · [Data sources](docs/profile-data.md)</sub>
