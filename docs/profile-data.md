# GitHub contribution data

The profile displays one measure: **GitHub contributions in the last 30 days**, computed from the daily counts on the [public GitHub contribution calendar](https://github.com/users/130U/contributions).

The generator first checks GitHub's displayed annual total against the sum of all daily counts. It then sums the latest 30 calendar dates, including the most recent date in GitHub's calendar and the preceding 29 dates. Zero-contribution dates remain part of this rolling window. The SVG description records the exact inclusive date range. This follows GitHub's profile contribution rules; it is not a repository-scoped commit count. The calendar's intensity levels are retained in the saved data for verification, but no additional calendar is displayed in the README. A thin line shows the same 30 daily counts in chronological order, with zero on a fixed baseline and the window maximum at the top; a dot marks the latest day. Zero days are included. This is activity data, not a performance metric.

The rolling window advances with each daily update. The [daily workflow](https://github.com/130U/130U/actions/workflows/update-profile.yml) refreshes both the drawings and the verified data saved in config/profile.json. If the public calendar cannot be fetched or validated, the generator retains that saved data and its original collection date. The line labels this as **Saved snapshot**.

The contribution line is a static image, drawn at the page's three widths for a light and a dark page. Its type is Inter, set from the outlines, advances and kerning in config/type.json. The generator uses Python's standard library, requires no repository token, and makes no changes to GitHub's native contribution graph.

The page itself is built by scripts/build_readme.py from config/profile.json, which lists the five sections and, for every work, its repository, title and the bold lead of its README. Each section head and each work is one line of a ledger, drawn under assets/ledger in Inter and Source Serif 4 at the same three widths and in the same two themes. A head links to the list of the same name, a work to its repository. scripts/validate_profile.py checks that README.md equals that build and that every drawing carries the text of the configuration.

[GitHub contribution reference](https://docs.github.com/en/account-and-profile/reference/profile-contributions-reference)
