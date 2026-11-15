# expv2-1: Think-on-Graph (ToG) πάνω στο KQA Pro

## Τι κάναμε

Συγκρίναμε δύο τρόπους να απαντήσει το **qwen3:14b** σε ερωτήσεις γνώσης:

1. **Baseline**: το μοντέλο απαντάει μόνο του, χωρίς knowledge graph.
2. **qwen + ToG**: το μοντέλο εξερευνά ένα knowledge graph βήμα-βήμα (prune
   relations → score entities → ελέγχει αν έχει αρκετά στοιχεία → απαντάει),
   σύμφωνα με τη μέθοδο Think-on-Graph (ICLR 2024,
   [DataArcTech/ToG](https://github.com/DataArcTech/ToG)).

## Τι χρησιμοποιήσαμε

- **Dataset**: [KQA Pro](https://arxiv.org/abs/2007.03875) — 117,970 ερωτήσεις
  πάνω σε ένα πυκνό υποσύνολο του Wikidata. Κατεβάσαμε `kb.json`
  (knowledge graph) + `train/val/test.json` (ερωτήσεις) από το HuggingFace
  mirror `drt/kqa_pro` (το επίσημο Tsinghua link είναι dead — επιβεβαιωμένο
  από ανοιχτό GitHub issue χωρίς απάντηση).
- **KB στατιστικά**: 794 concepts, 16,960 entities, 415,334 relation edges,
  174,539 attribute facts. Entity IDs είναι πραγματικά Wikidata QIDs.
- **Δείγμα**: 30 ερωτήσεις από το `val.json` (έχει gold answers· το
  `test.json` όχι — είναι κρυφές, για leaderboard submission).
- **Μοντέλο**: qwen3:14b (Ollama, τοπικά, `think=False`, `temperature=0`).

## Τροποποιήσεις που χρειάστηκαν (δεν ήταν plug-and-play)

1. **Αγνοήσαμε το multiple-choice format του KQA Pro.** Κάθε ερώτηση έχει
   10 `choices` (1 σωστή + 9 distractors) — αλλά αυτό κάνει εύκολο το
   "μάντεμα" μέσω αποκλεισμού, χωρίς να χρειάζεται πραγματικά το KG. Δεν
   δείξαμε ποτέ τα choices στο μοντέλο· του ζητήσαμε ελεύθερη απάντηση,
   σκοράρισμα με SQuAD-style **EM/F1** κόντρα στο μοναδικό gold `answer`.
2. **Δεν χρησιμοποιήσαμε το native backend του ToG** (`freebase_func.py`/
   `wiki_func.py`, live Freebase/Wikidata server) — αυτό ταιριάζει μόνο στα
   δικά τους benchmarks (CWQ/WebQSP). Γράψαμε δικό μας λεπτό lookup layer
   (`src/kb.py`) πάνω στο τοπικό `kb.json`.
3. **Entity linking from scratch.** Το KQA Pro δεν δίνει "topic entity" ανά
   ερώτηση· χτίσαμε ντετερμινιστικό linker (ταίριασμα substring ονόματος
   entity μέσα στο κείμενο της ερώτησης). Σε 4/30 ερωτήσεις δεν βρέθηκε
   καμία — εκεί το ToG πέφτει πίσω σε απάντηση χωρίς KG (ίδιο με baseline).
4. **Prompts ξαναγραμμένα για το δικό μας plain-English predicate naming**
   (το kb.json έχει ήδη φυσική γλώσσα στις σχέσεις, π.χ. "shares border
   with" — όχι Freebase-style codes, άρα όχι μετάφραση, μόνο reformatting).
5. **Format compliance**: αρχικό prompt ("answer concisely") άφηνε το
   μοντέλο να γράφει ολόκληρες προτάσεις στο answer slot, χτυπώντας άδικα
   το EM/F1. Σφίξαμε το prompt να ζητάει ρητά "ΜΟΝΟ τη γυμνή απάντηση".
6. **Traceability χωρίς κόστος ακρίβειας.** Δοκιμάσαμε να ζητήσουμε από το
   μοντέλο να δηλώσει ρητά ποιο triplet χρησιμοποίησε (`CITED:`) — αυτό
   **χειροτέρεψε** το σκορ (0.567→0.433 EM). Ελέγξαμε πώς το κάνει το
   πραγματικό ToG repo: δεν ρωτάει ποτέ το μοντέλο — ο ίδιος ο orchestrating
   κώδικας καταγράφει το μονοπάτι (`cluster_chain_of_entities`). Το κάναμε
   κι εμείς έτσι (`tog_trace`, δομημένο ανά hop) — μηδενικό κόστος ακρίβειας.

## Αποτελέσματα (n=30, qwen3:14b)

| | EM | F1 |
|---|---|---|
| Baseline (qwen σκέτο) | 0.367 | 0.380 |
| qwen + ToG | **0.567** | **0.567** |

Στο subset όπου βρέθηκε topic entity (n=26 — εκεί που το ToG έχει πράγματι
ευκαιρία να χρησιμοποιήσει το KG):

| | EM | F1 |
|---|---|---|
| Baseline (qwen σκέτο) | 0.423 | 0.438 |
| qwen + ToG | **0.615** | **0.615** |

8/30 ερωτήσεις διορθώθηκαν (baseline λάθος → ToG σωστό). 2/30 πήγαν προς τα
πίσω (baseline σωστό → ToG λάθος) — και τα δύο είναι ήδη γνωστά μοτίβα
αποτυχίας (βλ. "Γνωστά όρια" παρακάτω): ένα aggregation/counting ερώτημα
("how many philosophy belong to..." → gold 2, ToG απάντησε 26, παρασυρμένο
από θόρυβο στα συγκεντρωμένα triplets) και ένα όπου ο entity linker/
pruning επέστρεψε άσχετα στοιχεία (ερώτηση για "Belgium national football
team", το evidence ήταν για άλλες ποδοσφαιρικές ομάδες άσχετες με Βέλγιο —
το μοντέλο απάντησε με έναν τυχαίο αριθμό, 471821105940.323, πιθανόν
παρασυρμένο από μια attribute τιμή).

## Ρητό παράδειγμα: πώς η ανάκτηση από το γράφο διόρθωσε ένα λάθος

**Ερώτηση**: *"What is the connection between Akshay Kumar to Amritsar?"*
**Gold answer**: `place of birth`

**Baseline (qwen σκέτο)**:
> "Akshay Kumar is not directly connected to Amritsar in a notable way"

Το μοντέλο **αρνείται ρητά** ότι υπάρχει σύνδεση — λάθος, όχι απλά ασαφές.

**qwen + ToG**: Στο hop 0, ο entity linker βρήκε `Akshay Kumar` ως topic
entity, το ToG ζήτησε τις σχέσεις του, και ανάμεσα στα triplets που
συγκεντρώθηκαν ήταν:

```
Akshay Kumar -- place of birth --> Amritsar
```

Με αυτό το triplet μπροστά του, το μοντέλο απάντησε σωστά: `place of birth`.

Το ίδιο μοτίβο (baseline αρνείται/επινοεί, ToG βρίσκει το πραγματικό γεγονός
απευθείας στο γράφο) φαίνεται και στο:

**Ερώτηση**: *"How is John Bailey (the one whose CANTIC-ID is a11706788)
connected to Santa Clara University?"*
**Gold**: `educated at`
**Baseline**: "John Bailey is connected to Santa Clara University as a
professor in the Department of Electrical Engineering" — επινοημένο
(hallucinated) ρόλο, καμία σχέση με το gold.
**ToG**: βρήκε απευθείας `John Bailey -- educated at --> Santa Clara
University` στα triplets, απάντησε σωστά `educated at`.

## Γνωστά όρια

- **Aggregation/counting ερωτήσεις** (π.χ. "πόσες πόλεις έχουν...") δεν
  ταιριάζουν στη μεθοδολογία path-based evidence του ToG — χρειάζονται
  μέτρηση πάνω σε χιλιάδες entities, όχι εξερεύνηση μονοπατιού.
- Ο δικός μας entity linker είναι απλό substring matching σε ονόματα — δεν
  πιάνει ερωτήσεις που ορίζονται αποκλειστικά από attribute values (π.χ.
  "TOID 4000000074573917") χωρίς κανένα όνομα entity μέσα στο κείμενο.
- Δείγμα μόνο 30 ερωτήσεων — αρκεί για πρώτο σήμα, όχι για στατιστικά
  ισχυρό συμπέρασμα.
