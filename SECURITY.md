# Security Policy

> [!IMPORTANT]
> Please report a security problem privately to contact@isaacadjei.me or with the "Report a vulnerability" button on this repository's Security tab. Do not open a public issue or pull request.

## Scope

- The card generator, `profile/generate_card.py`
- The workflows in [`.github/workflows`](.github/workflows) and how they handle the two repository secrets. `ACCESS_TOKEN` is a classic token with public_repo scope that reads stats and resets the forks. `SIGNING_KEY` is the SSH key that signs the card refresh commits

## Out of scope

- The forks this account owns: report the issue to the upstream project instead
- Third party services, GitHub itself included: report those to the provider

## What to include

A description of the problem, the steps to reproduce it and the impact you expect. A report is acknowledged within 72 hours.

## The full policy

The account's default policy is in [zaccesssbot/.github](https://github.com/zaccesssbot/.github/blob/main/SECURITY.md). The owner's full policy covers the disclosure process and response times. It is in [zaccesss/security-policy](https://github.com/zaccesss/security-policy) and on [the website](https://isaacadjei.me/security-policy). This file takes precedence where they differ.
