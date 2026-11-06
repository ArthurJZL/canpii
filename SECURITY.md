# Security policy

## Never share real personal information

This project handles detection of **sensitive identifiers**. Please:

* **Do not paste real identifiers** (health numbers, SINs, licence numbers, passport
  numbers, bank details, Business Numbers of sole proprietors) into issues, discussions,
  pull requests, commit messages, test fixtures or screenshots — not even partially
  masked ones.
* To report a false positive or a missed detection, reproduce it with a synthetic value
  (`canpii generate <kind>`) or replace every digit and letter with a
  different one of the same kind while keeping separators.
* If you accidentally post real data, tell a maintainer right away (see below) so the
  content and any history can be removed.

## Reporting a vulnerability

Examples: a regex with catastrophic backtracking (ReDoS), an exporter that produces a
configuration which silently disables redaction, or a detection bypass for a
documented format.

Please report privately via
[GitHub private vulnerability reporting](https://github.com/ArthurJZL/canpii/security/advisories/new)
or by email to arthurjin1998@gmail.com with the subject `canpii security`.
Do not open a public issue for vulnerabilities.

We aim to acknowledge reports within 5 business days. This is a volunteer-maintained
project; there is no bug bounty.

## Supported versions

Only the latest released minor version receives fixes while the project is in `0.x`.
