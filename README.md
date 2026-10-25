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
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env   # omit to run offline (template stubs)
```
 
## 1. build a population
 
```bash
cd population_gen
python build_personas.py --n {population size} --seed {rng}
python build_bibles.py --n {population size} --seed {rng} --model claude-haiku-4-5
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
 
```bash
python compose.py --input populations/population_n50_seed32.json --chirp --seed 13 --today 2026-10-25 --strict
python verify.py output/run_seed13_chirp --freeze
```
 
`verify.py` alone is the identity-boundary check. `--freeze` additionally requires that every
account was LLM-generated, carries no template-stub text, and is not short on posts.
 
## Modules
 
| Flag | Module | Output |
|---|---|---|
| `--chirp` | Twitter/X-like microblog | `chirp_profiles.jsonl` · `chirp_posts.jsonl` |
 
## Reproducibility
 
A dataset = **population seed + compose seed + `--today`**. Record all three.
