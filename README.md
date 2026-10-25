# persona-forge
 
Modular generator of layered synthetic OSINT datasets.
 
## Structure
 
```
population_gen/   persona-generation code
populations/      frozen population files (population_n<N>_seed<S>.json)
modules/          contract.py footprint.py <module>/ (chirp)
compose.py        orchestrator (flags → footprint → module emit)
verify.py         boundary check (no identity in observations)
output/{run}/     observations/ answer_key/ manifest.json
```
 
## Setup
 
```bash
pip install -r requirements.txt
```
 
`.env` holds the gateway credentials:
 
```
PATAI_BASE_URL=https://apim-n1ai-use-gmun1.azure-api.net/
PATAI_API_KEY=<subscription key>
```
 
Set `LLM_OFFLINE=1` on any command to run without the API (template stubs).
 
## Models
 
One gateway, one key, two upstream routes. `llm/registry.py` owns the mapping; call sites
name a **role**, not a model.
 
| alias | route | resolved deployment |
|---|---|---|
| `sonnet-4.5` | `/anthropic` | `claude-sonnet-4-5` |
| `sonnet-4.6` | `/anthropic` | `claude-sonnet-4-6` |
| `gpt-5.4` | `/openai/v1` | `gpt-5.4` |
| `gpt-4.1` | `/openai/v1` | `gpt-4.1` |
| `gpt-4o` | `/openai/v1` | `gpt-4o` |
| `llama-4-maverick` | `/openai/v1` | `Llama-4-Maverick-17B-128E-Instruct-FP8` |
 
| role | used by | default |
|---|---|---|
| `writer` | chirp posts and bios | `sonnet-4.5` |
| `bible` | persona backstories | `sonnet-4.5` |
| `handle` | footprint handles | `gpt-4o` |
| `profiler` | (reserved) | `sonnet-4.6` |
 
Override a role per run with `--model ROLE=ALIAS`, or persistently in `.env` with
`LLM_ROLE_WRITER=gpt-4.1`. Per-model ids, paths, auth headers and token budgets are all
env-overridable (`LLM_ID_*`, `LLM_PATH_*`, `LLM_AUTH_*`, `LLM_TPM_*`, `LLM_TPM_DEFAULT`).
Rate limiting is a sliding 60s window per model at 90% of its budget.
 
## 1. build a population
 
```bash
cd population_gen
python build_personas.py --n {population size} --seed {rng}
python build_bibles.py --n {population size} --seed {rng} --model {alias, optional}
python validate_population.py --n {population size} --seed {rng} --today {current date}
```
 
## 2. compose a dataset
 
```bash
cd ..
python compose.py --input populations/population_n{pop size}_seed{seed num}.json --chirp --seed {new seed for composition} --today {date}
python verify.py output/run_seed{compose seed}_chirp
```
 
Add `--strict` to abort the run on any LLM failure instead of silently falling back to
offline template stubs. Use it for any dataset you intend to freeze as a benchmark.
`--model ROLE=ALIAS` is repeatable and pins a role for the whole run.
 
```bash
python compose.py --input populations/population_n50_seed32.json --chirp --seed 13 --today 2026-10-25   --strict --model writer=sonnet-4.6 --model handle=gpt-4o
python verify.py output/run_seed13_chirp --freeze
```
 
`verify.py` alone is the identity-boundary check. `--freeze` additionally requires that every
account was LLM-generated, carries no template-stub text, and is not short on posts.
 
## Modules
 
| Flag | Module | Output |
|---|---|---|
| `--chirp` | Twitter/X-like microblog | `chirp_profiles.jsonl` · `chirp_posts.jsonl` |
 
## Reproducibility
 
A dataset = **population seed + compose seed + `--today`**. Record all three. The resolved
model for every role is written to `manifest.json` under `llm`.
