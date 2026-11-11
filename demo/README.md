---
title: canpii
emoji: 🍁
colorFrom: red
colorTo: gray
sdk: gradio
sdk_version: 6.31.0
python_version: "3.12"
app_file: app.py
pinned: false
license: apache-2.0
short_description: Canadian PII recognizers for Microsoft Presidio
---

# canpii demo

A small [Gradio](https://www.gradio.app/) app for
[canpii](https://github.com/ArthurJZL/canpii), the Canadian PII recognizers for
Microsoft Presidio. Paste text, pick a language (English or French), a policy preset
(all entities, PIPEDA, PHIPA or Québec Law 25) and a score threshold. The app shows the
detected entities, the anonymized text and a table of findings.

**Demo only.** Do not paste real personal data. Every example in the app uses synthetic
identifiers. Detection is pattern-based and probabilistic: a clean result is not a
compliance guarantee and not legal advice.

The YAML block at the top of this file is the Hugging Face Space configuration. It is
only read when this file is the `README.md` at the root of a Space.

## Run it locally

```bash
pip install -r demo/requirements.txt
python demo/app.py
```

Then open <http://127.0.0.1:7860>.

## How to publish this Space

1. Sign in at <https://huggingface.co>, open <https://huggingface.co/new-space>, choose
   owner `ArthurJZL`, name `canpii`, SDK **Gradio**, hardware **CPU basic** (free),
   visibility **Public**, and create the Space.
2. Clone the empty Space next to this repository:
   `git clone https://huggingface.co/spaces/ArthurJZL/canpii canpii-space`
   (use a Hugging Face access token with write permission as the password).
3. Copy the three files from this folder into it:
   `cp demo/app.py demo/requirements.txt demo/README.md canpii-space/`
4. Commit and push: `cd canpii-space && git add . && git commit -m "Add canpii demo" && git push`.
   The Space builds for a few minutes; watch the **Logs** tab until it says *Running*.
5. Open <https://huggingface.co/spaces/ArthurJZL/canpii>, click each example once to
   check the output, then un-comment the "Try it in your browser" line in the main
   `README.md` of the canpii repository.

When a new canpii version is released, bump `canpii==` in `requirements.txt` and push
again. If the build fails on the Gradio version, set `sdk_version` in this file and
`gradio==` in `requirements.txt` to the same supported release.

## Notes

* "All entities" runs every Presidio recognizer plus canpii, including spaCy NER labels
  such as `DATE_TIME` and `ORGANIZATION`. Those are noisy on bare numbers, which is why
  the default is the PIPEDA preset.
* Where two findings overlap, the app keeps the one with the higher score (then the
  longer one), the same preference Presidio's anonymizer applies.
* The app uses the small spaCy models (`en_core_web_sm`, `fr_core_news_sm`) so that it
  fits on free CPU hardware.
