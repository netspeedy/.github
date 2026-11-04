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
profile/README.md                         Public GitHub organization profile README
profile/assets/                           Generated profile graphics and the social preview
scripts/readme/build_profile_graphics.py  Builds every graphic and the README's project grid
scripts/readme/projects.json              The public projects shown in Selected Public Work
scripts/readme/icons.json                 simple-icons logos the cards use (CC0)
scripts/readme/land.ts                    Land bitmap for the dotted Earth (copy of soakes/cv)
Makefile                                  make readme-graphics, make check
AGENTS.md                                 Maintainer and agent guidance
```

The prose in `profile/README.md` is written by hand. Every image in `profile/assets/`, and the Selected Public Work grid between the `<!-- projects:start -->` and `<!-- projects:end -->` markers, is generated. Never edit those by hand: change `projects.json` or the generator and rebuild.

The generator is a copy of `soakes/soakes` `scripts/readme/build_profile_graphics.py` with the Netspeedy content and the netspeedy colours the org's project heroes use. Fixes to the shared parts (fonts, text measuring, the Earth, the terminal, the cards) belong in both copies.

## Profile Update Workflow

Use this workflow when improving the public profile, changing positioning or adding public references.

1. Read `profile/README.md` and check the current public narrative.
2. Check any linked public source before changing claims, especially `kubertech.io`, `kubertech.dev`, `oakes.me.uk` and public `soakes` repositories.
3. Keep Netspeedy as the umbrella brand for infrastructure, automation, networking, Kubernetes, Ansible, services and operations.
4. Keep KuberTech described as the Kubernetes and GitOps platform slice only.
5. Edit `profile/README.md` directly for prose changes, outside the generated project grid.
6. Change graphics by editing `scripts/readme/build_profile_graphics.py` (banner copy, figures, focus areas, principles, KuberTech sites, links) or `scripts/readme/projects.json`, then run `make readme-graphics`.
7. Run `make check`, review the rendered profile, and check that links are public-safe before committing.

The public profile should read like a polished professional showcase, not an internal operations dashboard, raw repo dump or generic marketing page. It should make the operating maturity visible without leaking private implementation detail.

## Adding or Changing a Public Project

Selected Public Work, the tool tiles in the signals graphic and both tool counts all come from `scripts/readme/projects.json`, so a new public repository is one entry there and a rebuild.

1. Add an entry to `projects` in the order it should appear. Each entry has:
   - `name`: the repository name, also used for the card's file name.
   - `repo`: `netspeedy/<name>`, which the card links to.
   - `kicker`: the category, in capitals, for example `S3 PROVISIONING`.
   - `accent`: the accent colour from that repository's own README hero, so the card matches it.
   - `lang`: `[label, simple-icons slug, colour]`, for example `["Go", "go", "#00add8"]`.
   - `body`: what it does, in no more than two lines on the card. The build stops if it's longer.
   - `facts`: two `[label, value]` pairs, usually `BUILT IN` and `SHIPS AS`.
   - `install`: the two commands the repository's own README documents, for example `brew tap netspeedy/s3ctl` then `brew install s3ctl`. Never `brew install netspeedy/s3ctl/s3ctl`.
   - `tap` (optional): `netspeedy/homebrew-<name>`, which adds a badge under the grid.
2. If `lang` uses a logo that isn't in `icons.json`, add its path from simple-icons with the same version as the others.
3. Run `make readme-graphics`. It writes `project-<name>.svg`, rewrites the grid in `profile/README.md`, and updates the signals graphic and the figures band.
4. Run `make check`, look at the rendered profile, and commit the data file, the README and the changed graphics together.

To remove a project, delete its entry, rebuild, and delete its `project-<name>.svg`. With an odd number of projects the last card sits alone on its row, which is fine.

The other graphics change in `build_profile_graphics.py`: `FOCUS_AREAS`, `PRINCIPLES`, `SITES`, `LINKS`, `figures()` and the banner's `PILL`, `ROLE`, `TAGLINE`, `FOCUS` and `BANNER_SESSION`. Text is measured as it's built, so anything that won't fit stops the build with a message naming it. `NOW` is where the years ruler ends; move it on when the profile is next refreshed.

Every rebuild also regenerates `profile/assets/social-preview.png` (1280x640) from the banner. GitHub has no API for social previews, so after the banner changes, upload it under Settings, General, Social preview.

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

Rebuild every graphic and the README's project grid (needs `uv`, network access for the fonts on the first run, and Chrome or Chromium for the social preview; set `CHROME` if it isn't found):

```bash
make readme-graphics
```

Check that nothing is out of date, without writing:

```bash
make check
```

A rebuild with unchanged content leaves every file byte-identical.

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
- Keep every graphic self-contained so GitHub can render it without external assets; the generator refuses to write one with an external reference.
- Keep private organization dashboard content in `netspeedy/.github-private`, not here.
- Do not add generated private inventory to this public repository.
- Do not add private service URLs or internal operational runbooks.
- Use ASCII in Markdown. The generated SVGs use a few typographic characters (a middle dot, an em dash and the terminal prompt), embedded with their fonts.

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

- `make check` passes.
- `profile/README.md` renders as a professional public organization profile.
- Netspeedy is presented as the umbrella brand.
- KuberTech is presented only as the Kubernetes/GitOps platform slice.
- All links are public and intentional.
- No private service URLs, credentials, topology detail, raw inventory or sensitive operational output are staged.
- Commit messages use the required conventional prefix.
