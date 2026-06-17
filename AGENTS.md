# AGENTS.md

Guidance for agents and maintainers working in the Netspeedy public GitHub organization profile repository.

## Purpose

This repository owns the public Netspeedy organization profile shown from `netspeedy/.github`.

Primary goals:

- Present Netspeedy as a professional infrastructure, automation and platform engineering umbrella.
- Keep KuberTech positioned as the Kubernetes and GitOps platform slice, not the whole Netspeedy identity.
- Link public-safe proof points such as KuberTech, Simon Oakes' public CV and selected public tools.
- Avoid exposing private service URLs, repository inventory, topology detail, credentials or copied operational output.

## Important Files

```text
profile/README.md                    Public GitHub organization profile README
profile/assets/netspeedy-banner.svg  Hand-maintained public organization banner
AGENTS.md                            Maintainer and agent guidance
```

This repository is intentionally static for now. Do not add a generator until there is enough public repository inventory or repeated publishing work to justify it.

## Profile Update Workflow

Use this workflow when improving the public profile, changing positioning or adding public references.

1. Read `profile/README.md` and check the current public narrative.
2. Check any linked public source before changing claims, especially `kubertech.io`, `kubertech.dev`, `oakes.me.uk` and public `soakes` repositories.
3. Keep Netspeedy as the umbrella brand for infrastructure, automation, networking, Kubernetes, Ansible, services and operations.
4. Keep KuberTech described as the Kubernetes and GitOps platform slice only.
5. Edit `profile/README.md` directly for profile copy changes.
6. Edit `profile/assets/netspeedy-banner.svg` only when changing public brand wording or visual presentation.
7. Review the rendered Markdown shape and check that links are public-safe before committing.

The public profile should read like a polished professional showcase, not an internal operations dashboard, raw repo dump or generic marketing page. It should make the operating maturity visible without leaking private implementation detail.

## Content Standards

- Lead with Netspeedy as the public brand.
- Use direct, practical infrastructure language.
- Prefer claims that are backed by public links or by Simon Oakes' public CV.
- Keep the tone professional and confident without vague filler.
- Explain public-safe operating principles: source of truth, automation, reviewable change, recovery and careful exposure.
- Keep tables short enough to scan on GitHub.
- Do not list private repositories, internal service names, private URLs, hostnames, IPs, topology, credentials, secret paths or copied command output.
- Do not imply that KuberTech is all of Netspeedy.

## Common Commands

There is no build pipeline for this repository yet.

Review the working tree:

```bash
rtk git status --short
rtk git diff -- profile/README.md profile/assets/netspeedy-banner.svg AGENTS.md
```

Check GitHub CLI authentication if repository metadata is needed:

```bash
gh auth status
```

List public Netspeedy repositories when deciding whether a public repo map is justified:

```bash
gh repo list netspeedy --visibility public --json name,description,isArchived,url,primaryLanguage,repositoryTopics --limit 100
```

## Editing Rules

- Keep `profile/README.md` public-safe at all times.
- Keep `profile/assets/netspeedy-banner.svg` self-contained so GitHub can render it without external assets.
- Keep private organization dashboard content in `netspeedy/.github-private`, not here.
- Do not add generated private inventory to this public repository.
- Do not add private service URLs or internal operational runbooks.
- Use ASCII in Markdown and SVG unless there is a clear reason not to.

## Commit Style

Use conventional commit-style prefixes.

Examples:

```text
docs: add public organization profile
docs: refine Netspeedy public positioning
chore: add repository agent guidance
fix: correct public profile link
feat: add public project showcase section
```

Preferred types:

- `docs`: profile README, AGENTS and documentation content
- `chore`: repository housekeeping and maintainer guidance
- `fix`: corrections to links, wording or public-safe claims
- `feat`: new public profile section or capability
- `ci`: GitHub Actions or automation changes if added later

Keep commit messages concise and factual. Do not use non-prefixed messages.

## Review Checklist

Before pushing, check:

- `profile/README.md` renders as a professional public organization profile.
- Netspeedy is presented as the umbrella brand.
- KuberTech is presented only as the Kubernetes/GitOps platform slice.
- All links are public and intentional.
- No private service URLs, credentials, topology detail, raw inventory or sensitive operational output are staged.
- Commit messages use the required conventional prefix.
