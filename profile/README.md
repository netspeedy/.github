<p align="center">
  <img src="./assets/netspeedy-banner.svg" width="100%" alt="Netspeedy, infrastructure and platform engineering. Automation, networking and platforms, built from real systems. A terminal pushes to main and the change is validated, reviewed, reconciled by Argo CD and applied by Ansible, above the dotted Earth with London lit." />
</p>

<div align="center">

[![Linux](https://img.shields.io/badge/Linux-111827?style=for-the-badge&logo=linux&logoColor=white)](#)
[![Ansible](https://img.shields.io/badge/Ansible-ee0000?style=for-the-badge&logo=ansible&logoColor=white)](#)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-326ce5?style=for-the-badge&logo=kubernetes&logoColor=white)](#)
[![Argo CD](https://img.shields.io/badge/Argo_CD-ef7b4d?style=for-the-badge&logo=argo&logoColor=white)](#)
[![Vault](https://img.shields.io/badge/Vault-111827?style=for-the-badge&logo=vault&logoColor=FFEC6E)](#)
[![Cloudflare](https://img.shields.io/badge/Cloudflare-f38020?style=for-the-badge&logo=cloudflare&logoColor=white)](#)
[![MikroTik](https://img.shields.io/badge/MikroTik-293239?style=for-the-badge&logo=mikrotik&logoColor=white)](#)

</div>

<p align="center">
  <img src="./assets/netspeedy-highlights.svg" width="100%" alt="Netspeedy in four figures: 25+ years in production; GitOps on K3s and Argo CD; edge, with DNS, BGP and certificates; and the open-source public tools." />
</p>

> Infrastructure engineering, automation, networking and platform operations, built from real systems and run with production habits.

## What Netspeedy Is

Netspeedy is a long-running infrastructure engineering environment covering Linux systems, automation, Kubernetes, GitOps, DNS, certificates, networking, storage, CI/CD, self-hosted services and operational tooling.

The point is practical engineering, not isolated demo content. The work behind Netspeedy is built around the same habits expected in production environments: clear ownership, repeatable change, source-controlled intent, careful automation, observable behaviour and recovery paths that are understood before they are needed.

This public profile focuses on the engineering approach, selected public work and platform story that represent Netspeedy externally.

## Operational Signals

<p align="center">
  <img src="./assets/netspeedy-signals.svg" width="100%" alt="Operational signals: 25+ years in production, 2,500 VMs under automation, 300+ DNS zones managed and the public tools. Engineering focus. Infrastructure as code: hosts, services, routing and runners managed as reviewable desired state. Kubernetes and GitOps: K3s, Argo CD, platform services and environment overlays. Automation: Ansible, GitHub Actions, scripts and CLIs. Networking and edge: DNS, routing, VPNs, certificates and ingress. Service ownership: upgrades, backups and failure handling. Recovery discipline: backup, rollback, unseal and restore designed in." />
</p>

## Selected Public Work

Operator-facing tools built and maintained under Netspeedy, each solving one production problem cleanly.

<!-- projects:start -->
<p align="center">
  <a href="https://github.com/netspeedy/blackhole-threats"><img src="./assets/project-blackhole-threats.svg" width="49%" alt="blackhole-threats: Network defence automation. Turns threat feeds into BGP blackhole routes through GoBGP, and keeps a feed&#x27;s last good routes when it fails. built in Go, with GoBGP; ships as Signed APT repository and a GHCR image. Install: sudo apt install blackhole-threats, then sudo systemctl enable --now blackhole-threats." /></a>
  <a href="https://github.com/netspeedy/s3ctl"><img src="./assets/project-s3ctl.svg" width="49%" alt="s3ctl: S3 provisioning. Provisions S3 buckets, each with its own IAM user and key scoped to that bucket alone, and plans every change first. built in Go; ships as Homebrew tap, signed APT repository and GHCR. Install: brew tap netspeedy/s3ctl, then brew install s3ctl." /></a>
  <a href="https://github.com/netspeedy/s3mirror"><img src="./assets/project-s3mirror.svg" width="49%" alt="s3mirror: Bucket mirroring. Mirrors every bucket between S3-compatible endpoints, copying only new or changed objects, in parallel. built in Python, with boto3; ships as Homebrew tap and a GHCR image. Install: brew tap netspeedy/s3mirror, then brew install s3mirror." /></a>
  <a href="https://github.com/netspeedy/zquota"><img src="./assets/project-zquota.svg" width="49%" alt="zquota: Quota monitoring. Shows Z.ai quota use and exactly when each window resets, with exit codes cron can act on. built in Python, standard library only; ships as Homebrew tap, signed APT repository and pip. Install: brew tap netspeedy/zquota, then brew install zquota." /></a>
  <a href="https://github.com/netspeedy/joflux"><img src="./assets/project-joflux.svg" width="49%" alt="joflux: Repository migration. Moves a whole GitHub organisation into Forgejo or Codeberg in five stages, and never deletes the originals. built in Python, standard library only; ships as Homebrew tap. Install: brew tap netspeedy/joflux, then brew install joflux." /></a>
  <a href="https://github.com/netspeedy/odysseusai"><img src="./assets/project-odysseusai.svg" width="49%" alt="odysseusai: Container images. Independent images of the Odysseus AI workspace, built from upstream and booted with the full stack before they&#x27;re tagged. built from Upstream Odysseus, rebuilt nightly; ships as GHCR images and Compose files. Install: git clone https://github.com/netspeedy/odysseusai.git, then cd odysseusai &amp;&amp; cp .env.example .env &amp;&amp; docker compose up -d." /></a>
</p>

<div align="center">

Each card opens its repository. Homebrew taps for the tools above:

[![homebrew-s3ctl](https://img.shields.io/badge/homebrew--s3ctl-FBB040?style=for-the-badge&logo=homebrew&logoColor=black)](https://github.com/netspeedy/homebrew-s3ctl)
[![homebrew-s3mirror](https://img.shields.io/badge/homebrew--s3mirror-FBB040?style=for-the-badge&logo=homebrew&logoColor=black)](https://github.com/netspeedy/homebrew-s3mirror)
[![homebrew-zquota](https://img.shields.io/badge/homebrew--zquota-FBB040?style=for-the-badge&logo=homebrew&logoColor=black)](https://github.com/netspeedy/homebrew-zquota)
[![homebrew-joflux](https://img.shields.io/badge/homebrew--joflux-FBB040?style=for-the-badge&logo=homebrew&logoColor=black)](https://github.com/netspeedy/homebrew-joflux)

</div>
<!-- projects:end -->

## How We Work

Good infrastructure work is not just about deploying things. It is about making change understandable, repeatable and safe enough that future maintenance is not a gamble.

<p align="center">
  <img src="./assets/netspeedy-how-we-work.svg" width="100%" alt="How we work: six habits, one pipeline. Source of truth first. Automate the repeatable. Keep changes reviewable. Design for recovery. Document the surprising. Communicate clearly." />
</p>

## KuberTech

KuberTech is the Kubernetes and GitOps platform part of Netspeedy. It shows how workloads, platform services, environment separation and promotion paths are handled, as one part of a wider infrastructure and automation environment rather than the whole of it.

<p align="center">
  <a href="https://kubertech.io"><img src="./assets/site-kubertech-io.svg" width="49%" alt="kubertech.io: production platform. The public production view of the GitOps platform: real services, controlled change and practical infrastructure automation. Runs on K3s, reconciled by Argo CD." /></a>
  <a href="https://kubertech.dev"><img src="./assets/site-kubertech-dev.svg" width="49%" alt="kubertech.dev: development platform. The development side of the same platform, where GitOps changes are proven behind production-style guardrails before release." /></a>
</p>

## Background

Netspeedy is maintained by Simon Oakes, a UK-based Senior Linux, DevOps and Platform Engineer with 25+ years of experience across ISP infrastructure, media platforms, CI/CD systems, virtualisation, networking, storage, automation and production operations.

<p align="center">
  <a href="https://oakes.me.uk"><img src="./assets/link-oakes.svg" width="49%" alt="oakes.me.uk: Simon Oakes' public CV and professional profile." /></a>
  <a href="https://github.com/soakes"><img src="./assets/link-github.svg" width="49%" alt="github.com/soakes: personal tools and projects, outside the org." /></a>
</p>

---

<div align="center">

**Infrastructure should be boring for the right reasons: clear state, controlled change and recovery paths that work.**

</div>
