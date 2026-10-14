# LCAE Practice Exam — LangSmith Data

Companion data for the **LangChain Certified Agent Engineer (LCAE) practice test** course on Udemy.

A few Monitoring questions in each practice test can't be answered from the question alone — they
ask you to read a real LangSmith dashboard, the same way the actual certification exam does. This
repo loads a fixed set of traces, feedback, and experiments into **your own** LangSmith workspace
so those questions have a real dashboard to read.

The data is identical for everyone who runs it unmodified, so every question has one correct
answer.

**Prefer to watch?** A short silent walkthrough of the whole setup (clone, create an API key, add it
to `.env`, upload, and check LangSmith) is here:
[**docs/setup-tutorial.mp4**](docs/setup-tutorial.mp4) (about 68 seconds). The written steps below
are the same.

---

## Before you start

You need three things:

1. **Python 3.10 or newer.** Check with `python3 --version`.
2. **`uv`** — the package manager that runs this project.
   ```sh
   curl -LsSf https://astral.sh/uv/install.sh | sh     # macOS / Linux
   ```
   ```powershell
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"   # Windows
   ```
   Then restart your terminal and confirm with `uv --version`.
3. **A LangSmith account and API key** — free at [smith.langchain.com](https://smith.langchain.com).
   Sign in, then go to **Settings → API Keys → Create API Key**. Copy it now; LangSmith only shows
   it once.

> Everything below uploads into your own workspace. Nothing is sent anywhere else, and no data
> leaves your account.

---

## Setup — step by step

### 1. Get the code

```sh
git clone https://github.com/MBehtemam/lcae-practice-exam-data.git
cd lcae-practice-exam-data
```

No git? Click the green **Code** button on GitHub → **Download ZIP**, unzip it, and `cd` into the
folder.

### 2. Add your API key

```sh
cp .env.example .env
```

Open `.env` in any editor and paste your key after the `=`:

```
LANGSMITH_API_KEY=lsv2_pt_your_actual_key_here
```

No quotes, no spaces around the `=`. Your `.env` is gitignored, so your key stays local.

### 3. Install dependencies

```sh
uv sync
```

### 4. Upload the data

Always run all three scripts, in this exact order — every time, including your very first upload:

```sh
uv run python reset.py
uv run python upload_traces.py
uv run python upload_experiments.py
```

`reset.py` clears anything left over from a previous attempt, so the two uploads start from a
clean workspace. On a first run it just reports that there is nothing to delete — that is normal,
not an error.

Order matters: `upload_traces.py` must finish before `upload_experiments.py` starts.

Each upload script prints a LangSmith URL when it finishes. Open them to confirm the data arrived.

### 5. Check it worked

In LangSmith you should now see:

- A tracing project named **`lcae-udemy-practice`** containing ~225 traces across five customer
  accounts, with feedback, errors, latency, and token usage attached.
- A dataset named **`support-faq-eval`** with two experiments to compare.

If both exist, you're ready. **Start the practice test now** — see the timing note below.

---

## Important: upload right before you take the test

The traces are timestamped **relative to the moment you run `upload_traces.py`**, spanning the
previous 20 hours. The exam questions ask about the "last 6 hours" and the "last 24 hours", so
those windows only line up while your upload is fresh:

| Time since you ran `upload_traces.py` | What happens |
|---|---|
| **Under 4 hours** | Everything answers correctly. |
| **Around 6 hours** | The *last-6-hours* questions break — that window is now empty, so the charts show nothing. |
| **Over 8 hours** | A *last-24-hours* question changes its correct answer as the oldest traces age out. |

**Run the upload immediately before you sit the test — not the night before.** If more time has
passed, reset and re-upload using the next section.

---

## Retaking a test, or re-running the upload

Run the same three commands from step 4 again — `reset.py`, then `upload_traces.py`, then
`upload_experiments.py`. There is no separate procedure for a repeat attempt.

This is why the reset is not optional: the upload scripts **only add data — they never overwrite
or de-duplicate.** Uploading twice would stack a fresh copy on top of what's already there,
doubling the counts the questions measure and making the answers wrong. Both scripts now refuse to
run when their data is already present and tell you to reset, so you can't hit this by accident —
but resetting first is still the habit to keep.

`reset.py` deletes the `lcae-udemy-practice` project, the `support-faq-eval` dataset, and its two
experiment projects — everything these scripts create, and nothing else in your workspace.

---

## Finding answers in LangSmith

Several questions compare a metric across all five accounts — highest error rate, highest token
use, highest negative-sentiment rate. Filtering one account at a time is slow. Build a chart
instead:

1. **Monitoring → Dashboards → + Dashboard → Create Chart**
2. Choose your metric and aggregation (**Count** for occurrences, **Average** for a mean).
3. Under **Filter & group**, group by **Metadata → account**. This also lists every account name
   in the data, so you never have to guess them.
4. Visualize as **Ranked bar** to read the ordering directly.

Two things to watch:

- **Count ranks by raw number, not rate.** Accounts don't all have the same number of runs, so for
  a true percentage divide each account's count by its own total.
- **For a single account's percentage**, use the **Ratio** metric type — it gives you separate
  Numerator and Denominator boxes, each with its own filter. Scope both to the same account, and
  make sure the denominator filters to the same feedback key as the numerator. Leaving the
  denominator as a bare unfiltered count pulls in unrelated runs and gives a wrong answer.

Feedback-based filters can also undercount briefly right after a bulk upload while LangSmith
indexes. If a filtered count looks suspiciously low, open a couple of individual traces and check
their **Feedback** tab directly.

---

## Troubleshooting

**`uv: command not found`** — restart your terminal after installing `uv`, or add it to your PATH.

**`LANGSMITH_API_KEY` errors** — check `.env` sits in the repo root, the key has no surrounding
quotes, and you copied the whole value.

**"Already exists in this workspace" / `409 Conflict`** — the data from a previous attempt is
still there. Run the full three-command sequence from step 4, starting with `reset.py`.

**`409 Conflict ... dataset id does not match example's dataset id`** — fixed. Older versions of
`upload_experiments.py` reused fixed example ids, which can already belong to a dataset elsewhere
in LangSmith. The script now mints fresh example ids on every upload. If you still see this, run
`git pull` and try again.

**Numbers look doubled** — you uploaded twice without resetting. Run `reset.py`, then upload again.

**Charts are empty** — either the upload hasn't run, or too much time has passed since it did. See
the timing table above.

**`reset.py` says nothing to delete** — the workspace is already clean. Go ahead and upload.

---

## What's in here

- `upload_traces.py` — uploads the traces, feedback, errors, latency, and token usage
- `upload_experiments.py` — creates the `support-faq-eval` dataset and its two experiments
- `reset.py` — deletes everything the two upload scripts create; run it first, every time
- `traces.json`, `experiments.json` — the fixed, pre-generated data both scripts replay

Neither upload script calls an LLM or generates anything new — they replay static files, so the
result is identical every time.
