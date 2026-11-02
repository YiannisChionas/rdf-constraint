# Groq converter check: missed facts re-extraction

- Total missed facts (qwen3:14b run): 43
- Caught by Groq (openai/gpt-oss-120b): 16
- Still missing (Groq too): 27
- Unparseable fact string (skipped): 0

## Caught by Groq (likely a qwen3:14b converter limitation, not fixed prompt/data — heuristic match, verify manually)

- q02: TP53 associatedWith breast cancer
- q02: PTEN associatedWith breast cancer
- q02: BRCA1 associatedWith ovarian cancer
- q02: BRCA2 associatedWith ovarian cancer
- q10: adalimumab binds TNF
- q10: etanercept binds TNF
- q12: FBXO7 associatedWith Parkinson's disease
- q12: ATP13A3 associatedWith Parkinson's disease (λάθος της απάντησης: το PARK9 είναι ATP13A2)
- q15: APC associatedWith colorectal cancer
- q15: MLH1 associatedWith colorectal cancer
- q15: MSH2 associatedWith colorectal cancer
- q15: MSH6 associatedWith colorectal cancer
- q15: PMS2 associatedWith colorectal cancer
- q15: EPCAM associatedWith colorectal cancer
- q17: BRCA2 associatedWith breast cancer
- q17: BRCA2 associatedWith ovarian cancer

## Still missing with Groq too (needs closer look — may be genuinely hard to extract)

- q01: glipizide binds KATP channel
- q01: sitagliptin binds DPP4
- q01: empagliflozin binds SLC5A2
- q01: liraglutide binds GLP1R
- q01: acarbose binds alpha-glucosidase
- q01: repaglinide binds KATP channel
- q03: BCR-ABL associatedWith chronic myeloid leukemia
- q03: KIT associatedWith gastrointestinal stromal tumors
- q03: PDGFRA associatedWith gastrointestinal stromal tumors
- q05: BCR-ABL associatedWith chronic myeloid leukemia
- q08: EGFR associatedWith non-small cell lung cancer
- q10: tocilizumab binds IL6R
- q10: tofacitinib binds JAK
- q14: omalizumab binds IgE
- q14: mepolizumab binds IL5
- q14: dupilumab binds IL4R
- q18: lamotrigine binds Nav1.1
- q18: lamotrigine binds Nav1.2
- q18: lamotrigine binds Nav1.3
- q18: oxcarbazepine binds Nav1.1
- q18: oxcarbazepine binds Nav1.2
- q18: oxcarbazepine binds Nav1.3
- q18: diazepam binds GABA-A receptor
- q18: lorazepam binds GABA-A receptor
- q18: phenobarbital binds GABA-A receptor
- q18: perampanel binds AMPA receptor
- q18: topiramate binds AMPA/kainate receptor