# Netspeedy GitHub Profile

This repository owns the public GitHub organization profile for Netspeedy.

It exists to present Netspeedy as a professional infrastructure, automation and platform engineering umbrella without exposing private services, repository inventory, topology detail or operational data.

## Purpose

The rendered organization profile lives in `profile/README.md`. GitHub displays that file on the public Netspeedy organization page.

The profile should make the public operating story clear:

- Netspeedy covers infrastructure engineering, automation, networking, Kubernetes, Ansible, services and operations.
- KuberTech is the Kubernetes and GitOps platform slice of Netspeedy, not the whole identity.
- Public references should be intentional, safe to share and backed by public links.
- Private repositories, private service URLs and sensitive operational details belong in `.github-private`, not here.

## Repository Layout

| Path | Purpose |
| --- | --- |
| `profile/README.md` | Public GitHub organization profile shown by GitHub. |
| `profile/assets/netspeedy-banner.svg` | Self-contained public organization banner. |
| `AGENTS.md` | Maintainer and agent guidance for safe profile updates. |
| `README.md` | Repository-level overview for this special GitHub profile repository. |

## Public Content Rules

Keep this repository public-safe at all times.

- Do not list private repositories, internal service names, private URLs, hostnames, IP addresses, credentials, secret paths or copied command output.
- Do not publish generated private inventory or operational runbooks.
- Do not imply that KuberTech is all of Netspeedy.
- Prefer direct infrastructure language over generic marketing copy.
- Keep public claims tied to public references or established professional background.
- Keep tables short enough to scan on GitHub.

## Update Workflow

Use a narrow edit path for profile changes.

1. Read `profile/README.md` and check the current public narrative.
2. Check linked public sources before changing claims or adding references.
3. Edit `profile/README.md` for profile copy changes.
4. Edit `profile/assets/netspeedy-banner.svg` only for deliberate public brand or visual changes.
5. Review the rendered Markdown shape and confirm all links are public-safe.

There is no build pipeline for this repository. Changes are plain Markdown and SVG.

## Review Checklist

Before merging or pushing changes, confirm:

- `profile/README.md` still reads as a professional public organization profile.
- Netspeedy remains the umbrella brand.
- KuberTech remains positioned as the Kubernetes and GitOps platform slice.
- All links are public and intentional.
- No private repository names, service URLs, credentials, topology detail, raw inventory or sensitive operational output have been added.

For the member-only operations dashboard, use the private special repository: `netspeedy/.github-private`.
