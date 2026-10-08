# Profile activity data

The profile activity panel is a dated snapshot, refreshed by the daily GitHub Actions workflow. It displays public development activity.

- **Engineering commits:** commits returned by each selected repository's GitHub commits endpoint with `author=130U`, using the repository's default branch.
- **Pull requests:** pull requests opened by `130U` in the selected repositories, including open and closed requests.
- **Public repositories:** the account's public repository count from the GitHub user API.

The engineering scope is `agent-evaluation-methodology`, `reserach-portfolio-since2026`, `bazi-context-agent`, and `info-collector-2026`, as listed in `profile.config.json`. The two mathematical-finance repositories are presented separately from these activity counts.

GitHub search links below the panel open the broader account activity. They are navigation links rather than the source of the panel's scoped totals.

If GitHub's public API is unavailable, the generator uses the saved values in `profile.config.json`. The panel labels this as **Saved snapshot** and displays the saved collection date, rather than the rendering date. GitHub may cache README images, so the dated snapshot and [workflow history](https://github.com/130U/130U/actions/workflows/update-profile.yml) provide the update context.

The visual assets are static SVGs with separate desktop, mobile, light, and dark variants. The generator uses Python's standard library and does not send a repository token to public telemetry endpoints.
