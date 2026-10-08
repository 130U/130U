# GitHub contribution data

The profile displays one measure: **GitHub contributions in the last 30 days**, computed from the daily counts on the [public GitHub contribution calendar](https://github.com/users/130U/contributions).

The generator first checks GitHub's displayed annual total against the sum of all daily counts. It then sums the latest 30 calendar dates, including the most recent date in GitHub's calendar and the preceding 29 dates. Zero-contribution dates remain part of this rolling window. The SVG description records the exact inclusive date range. This follows GitHub's profile contribution rules; it is not a repository-scoped commit count. The calendar's intensity levels are retained in the saved data for verification, but no additional calendar is displayed in the README.

The rolling window advances with each daily update. The daily workflow refreshes both the SVG and the verified data saved in profile.config.json. If the public calendar cannot be fetched or validated, the generator retains that saved data and its original collection date. The panel labels this as **Saved snapshot**.

The assets provide static desktop, mobile, light, and dark variants. The generator uses Python's standard library, requires no repository token, and makes no changes to GitHub's native contribution graph.

[GitHub contribution reference](https://docs.github.com/en/account-and-profile/reference/profile-contributions-reference)
