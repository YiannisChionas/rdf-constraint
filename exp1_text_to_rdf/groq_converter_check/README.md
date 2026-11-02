# Groq converter check: πόσα από τα 43 missed facts οφείλονται στο qwen3:14b;

Ο agent (qwen3:14b) απάντησε στις 20 ερωτήσεις, και ο converter (ίδιο μοντέλο,
qwen3:14b, μέσω Ollama) εξήγαγε 234 σχέσεις αλλά παρέλειψε 43 γεγονότα που
υπήρχαν στο κείμενο (καταγεγραμμένα χειροκίνητα στο
`../runs/20261102_125528/missed_facts.csv`).

Εδώ ξανατρέχουμε **μόνο το converter βήμα**, πάνω στις **ίδιες, ήδη
αποθηκευμένες απαντήσεις** (`../runs/20261102_125528/answers.jsonl` — δεν
ξαναρωτάμε τον agent, το κείμενο μένει αναλλοίωτο), αλλά με converter
**Groq** (cloud, όχι τοπικό GPU) αντί για qwen3:14b. Ίδιο schema.yaml/
few_shot.json, ίδιο JSON-schema-constrained prompt — η μόνη μεταβλητή που
αλλάζει είναι το μοντέλο του converter.

Σκοπός: να δούμε πόσα από τα 43 missed facts πιάνονται τώρα από ένα
ισχυρότερο μοντέλο — αυτό θα έδειχνε ότι ήταν περιορισμός του qwen3:14b
συγκεκριμένα, όχι του prompt/σχήματος.

## Usage

```
python -m src.run_check
```

Χρειάζεται `GROK_API_KEY` στο environment. Γράφει:
- `extractions_groq.jsonl` — οι νέες εξαγωγές
- `comparison.md` — ανά missed fact, αν πιάστηκε τώρα από το Groq (αυτόματος,
  heuristic έλεγχος ονομάτων — χρειάζεται ανθρώπινη επιβεβαίωση στα ασαφή)
