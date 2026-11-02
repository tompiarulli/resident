# Repository settings

GitHub settings that enforce the conventions in [AGENTS.md](../../AGENTS.md#git), kept here so
they're reviewable. Apply them with the GitHub CLI as a repository admin.

Merge settings: squash only, with the PR title and description as the commit, and delete
branches after merging:

```bash
gh api -X PATCH repos/tompiarulli/resident \
  -F allow_squash_merge=true -F allow_merge_commit=false -F allow_rebase_merge=false \
  -f squash_merge_commit_title=PR_TITLE -f squash_merge_commit_message=PR_BODY \
  -F delete_branch_on_merge=true
```

The `main` ruleset (create once, then update by id):

```bash
gh api -X POST repos/tompiarulli/resident/rulesets --input .github/rulesets/main.json
gh api repos/tompiarulli/resident/rulesets   # find the id
gh api -X PUT repos/tompiarulli/resident/rulesets/<id> --input .github/rulesets/main.json
```

The required check `Conventional Commit title` comes from `.github/workflows/pr-title.yml`. That
workflow runs from `main`, so it must be merged before the ruleset requires it.
