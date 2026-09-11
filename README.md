# persona-forge
 
Modular generator of layered synthetic OSINT datasets.
 
## Structure
 
```
population_gen/   persona-generation code
populations/      frozen population files (population_n<N>_seed<S>.json)
modules/          contract.py · footprint.py · <module>/ (chirp)
compose.py        orchestrator (flags → footprint → module emit)
verify.py         boundary check (no identity in observations)
output/<run>/     observations/ · answer_key/ · manifest.json
```
 
## Setup
 
```bash
pip install -r requirements.txt
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env   # omit to run offline (template stubs)
```
 
## 1 · Build a population
 
```bash
cd population_gen
python build_personas.py --n {population size} --seed {rng}
python build_bibles.py --n {population size} --seed {rng} --model claude-haiku-4-5
python validate_population.py --n {population size} --seed {rng} --today {current date}
```
 
Script
`build_personas.py` | seeded skeletons: identity, attributes, geo, schedule, linkability |
`build_bibles.py` | LLM enrich in place: backstory, voice, tells, topics, timeline |
`validate_population.py` | gate: vocab / consistency / bible integrity |
 
## 2 · Compose a dataset
 
```bash
cd ..
python compose.py --input populations/population_n50_seed42.json --chirp --seed 7 --today 2026-09-11
python verify.py output/run_seed7_chirp
```
 
Output per run: `observations/` (adversary sees), `answer_key/` (scorer only, incl. `footprint.json`), `manifest.json`.
 
## Modules
 
| Flag | Module | Output |
|---|---|---|
| `--chirp` | Twitter/X-like microblog | `chirp_profiles.jsonl` · `chirp_posts.jsonl` |
 
## Reproducibility
 
A dataset = **population seed + compose seed + `--today`**. Record all three.
 
## Principle
 
Observations carry **no identity**. Truth lives only in `answer_key/`. `verify.py` enforces