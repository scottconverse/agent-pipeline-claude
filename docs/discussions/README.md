# Discussion board seed posts

This directory holds the seed content for the project's GitHub Discussions board. Each file maps to one Discussions category and contains the announcement / starter post text. Paste the body of each file into the corresponding category on https://github.com/scottconverse/agentic-pipeline/discussions when announcing v0.4 (or any future release that meaningfully changes the project's shape).

These are source-controlled because:

- The categories below are the project's stable Discussions shape — not a one-off announcement.
- Future maintainers (or future you, in another session) need to be able to re-seed the board if a category is archived or the org is moved.
- The text in each file is the canonical announcement text; the GitHub Discussions copy is a deploy artifact, not the source of truth.

## Categories and files

| File | GitHub Discussions category | Format on github.com |
| :--- | :--- | :--- |
| [`announcements-v0.4.md`](announcements-v0.4.md) | Announcements | Pinned post announcing v0.4 |
| [`q-and-a-seed.md`](q-and-a-seed.md) | Q&A | Seed FAQ thread |
| [`show-and-tell-seed.md`](show-and-tell-seed.md) | Show and tell | Seed post inviting case studies |
| [`ideas-seed.md`](ideas-seed.md) | Ideas | Seed post for v0.5+ proposals |
| [`roadmap-v0.5.md`](roadmap-v0.5.md) | Roadmap | Pinned post describing the v0.5 candidate set |

## When to update

Add a new `announcements-v0.X.md` file for every minor release that meaningfully changes the plugin's user-facing shape (a new layer, a new pipeline type, a new slash command, or a deprecation). Leave older announcements in place — they're the public history.

Update the roadmap file when the next-minor candidate set changes. Leave older roadmap files in place as `roadmap-v0.X-historical.md` so future readers can see what shipped vs. what slipped.

The Q&A, show-and-tell, and ideas seeds are evergreen — update them when the question shape changes (e.g., when a recurring v0.4 question deserves a permanent FAQ entry), not on every release.

## How to use

When announcing v0.4:

1. Open https://github.com/scottconverse/agentic-pipeline/discussions
2. For each file above whose category exists on the board, create a new discussion in that category and paste the file's body. Pin the announcement and the roadmap.
3. If a category doesn't exist yet, create it under Discussions → Manage categories first.
4. Link back to this directory in each seeded post so future contributors can find the source.

The seed-post text is intentionally written to read well both in the repo (as documentation of what the project is) and on github.com (as actual Discussion content). Edit either, but keep them in sync — the repo file is the source of truth.
