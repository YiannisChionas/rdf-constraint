# Experiment 1 Report: Agent Answer -> RDF

## Config

```yaml
ollama:
  host: http://localhost:11434
agent:
  model: qwen3:14b
  temperature: null
  think: true
  system_prompt: 'You are a concise biomedical assistant. Answer the question in plain
    prose (no JSON, no bullet lists required), mentioning specific genes, drugs and
    diseases by name whenever relevant.

    '
converter:
  model: qwen3:14b
  temperature: 0.0
  think: false
  num_few_shot: 2
paths:
  schema_file: schema.yaml
  few_shot_file: few_shot.json
  questions_file: data/questions.jsonl
  runs_dir: runs
```

## Automatic metrics

- Answers evaluated: 20
- Converter JSON parse success rate: 1.0
- JSON-schema-valid rate: 1.0
- Domain/range correctness rate: 0.9049773755656109
- Dangling references: 0
- Duplicate nodes: 0
- Turtle round-trip parse success rate: 1.0
- Nodes per answer: {'mean': 10.95, 'min': 5, 'max': 25}
- Triples per answer: {'mean': 11.05, 'min': 1, 'max': 25}
- Relation counts: {'treats': 83, 'associatedWith': 57, 'binds': 57, 'interactsWith': 24}
- % answers with zero extracted relationships: 0.0
- Agent latency (s): {'mean': 14.71119554500001, 'min': 7.650375699999131, 'max': 92.58574000000044}
- Converter latency (s): {'mean': 10.551119649999873, 'min': 4.594356700001299, 'max': 21.69262990000061}

## Example answers and extractions

### q01
**Question:** Which drugs are used to treat type 2 diabetes and what are their molecular targets?

**Answer:** Drugs used to treat type 2 diabetes include metformin, which activates AMP-activated protein kinase (AMPK) to enhance glucose uptake and reduce hepatic glucose production. Sulfonylureas like glipizide stimulate insulin secretion by closing ATP-sensitive potassium channels in pancreatic beta cells. DPP-4 inhibitors (e.g., sitagliptin) increase GLP-1 levels by inhibiting the enzyme dipeptidyl peptidase-4, thereby enhancing insulin release and reducing glucagon. SGLT2 inhibitors (e.g., empagliflozin) block sodium-glucose cotransporter 2 in the kidneys, promoting glucose excretion in urine. GLP-1 receptor agonists (e.g., liraglutide) mimic GLP-1, improving insulin secretion and reducing appetite. Thiazolidinediones (e.g., pioglitazone) activate peroxisome proliferator-activated receptor gamma (PPAR-γ), enhancing insulin sensitivity in adipose and muscle tissues. Alpha-glucosidase inhibitors (e.g., acarbose) delay carbohydrate digestion, reducing postprandial glucose spikes. Meglitinides (e.g., repaglinide) also target ATP-sensitive potassium channels but act more rapidly than sulfonylureas. These drugs collectively address insulin resistance, secretion, and glucose reabsorption to manage hyperglycemia.

**Extracted JSON:**
```json
{
  "nodes": [
    {
      "id": "n1",
      "type": "Compound",
      "name": "metformin"
    },
    {
      "id": "n2",
      "type": "Disease",
      "name": "type 2 diabetes"
    },
    {
      "id": "n3",
      "type": "Compound",
      "name": "glipizide"
    },
    {
      "id": "n4",
      "type": "Compound",
      "name": "sitagliptin"
    },
    {
      "id": "n5",
      "type": "Compound",
      "name": "empagliflozin"
    },
    {
      "id": "n6",
      "type": "Compound",
      "name": "liraglutide"
    },
    {
      "id": "n7",
      "type": "Compound",
      "name": "pioglitazone"
    },
    {
      "id": "n8",
      "type": "Compound",
      "name": "acarbose"
    },
    {
      "id": "n9",
      "type": "Compound",
      "name": "repaglinide"
    }
  ],
  "relationships": [
    {
      "source": "n1",
      "relation": "treats",
      "target": "n2"
    },
    {
      "source": "n3",
      "relation": "treats",
      "target": "n2"
    },
    {
      "source": "n4",
      "relation": "treats",
      "target": "n2"
    },
    {
      "source": "n5",
      "relation": "treats",
      "target": "n2"
    },
    {
      "source": "n6",
      "relation": "treats",
      "target": "n2"
    },
    {
      "source": "n7",
      "relation": "treats",
      "target": "n2"
    },
    {
      "source": "n8",
      "relation": "treats",
      "target": "n2"
    },
    {
      "source": "n9",
      "relation": "treats",
      "target": "n2"
    }
  ]
}
```

### q02
**Question:** Which genes are associated with breast cancer?

**Answer:** Breast cancer is associated with several genes, including **BRCA1** and **BRCA2**, which are tumor suppressor genes involved in DNA repair; mutations in these genes significantly increase hereditary breast and ovarian cancer risk. **TP53** (linked to Li-Fraumeni syndrome) and **HER2** (a receptor tyrosine kinase amplified in some aggressive breast cancers) are also key. Other genes include **PTEN** (associated with Cowden syndrome), **CHEK2**, **ATM**, **BRIP1**, and **PALB2**, which are involved in DNA repair pathways. Mutations in these genes may predispose individuals to breast cancer but are not deterministic; environmental and hormonal factors also play roles.

**Extracted JSON:**
```json
{
  "nodes": [
    {
      "id": "n1",
      "type": "Disease",
      "name": "breast cancer"
    },
    {
      "id": "n2",
      "type": "Gene",
      "name": "BRCA1"
    },
    {
      "id": "n3",
      "type": "Gene",
      "name": "BRCA2"
    },
    {
      "id": "n4",
      "type": "Gene",
      "name": "TP53"
    },
    {
      "id": "n5",
      "type": "Gene",
      "name": "HER2"
    },
    {
      "id": "n6",
      "type": "Gene",
      "name": "PTEN"
    },
    {
      "id": "n7",
      "type": "Gene",
      "name": "CHEK2"
    },
    {
      "id": "n8",
      "type": "Gene",
      "name": "ATM"
    },
    {
      "id": "n9",
      "type": "Gene",
      "name": "BRIP1"
    },
    {
      "id": "n10",
      "type": "Gene",
      "name": "PALB2"
    },
    {
      "id": "n11",
      "type": "Disease",
      "name": "ovarian cancer"
    }
  ],
  "relationships": [
    {
      "source": "n2",
      "relation": "associatedWith",
      "target": "n1"
    },
    {
      "source": "n3",
      "relation": "associatedWith",
      "target": "n1"
    },
    {
      "source": "n4",
      "relation": "associatedWith",
      "target": "n1"
    },
    {
      "source": "n5",
      "relation": "associatedWith",
      "target": "n1"
    },
    {
      "source": "n6",
      "relation": "associatedWith",
      "target": "n1"
    },
    {
      "source": "n7",
      "relation": "associatedWith",
      "target": "n1"
    },
    {
      "source": "n8",
      "relation": "associatedWith",
      "target": "n1"
    },
    {
      "source": "n9",
      "relation": "associatedWith",
      "target": "n1"
    },
    {
      "source": "n10",
      "relation": "associatedWith",
      "target": "n1"
    },
    {
      "source": "n1",
      "relation": "associatedWith",
      "target": "n11"
    }
  ]
}
```

### q03
**Question:** What is the molecular target of imatinib and which diseases does it treat?

**Answer:** Imatinib targets the BCR-ABL tyrosine kinase fusion protein, which drives the uncontrolled proliferation of leukemic cells in chronic myeloid leukemia (CML). It also inhibits other tyrosine kinases, including c-KIT and PDGFRA, making it effective in treating gastrointestinal stromal tumors (GISTs) with mutations in these genes. Additionally, it is used for Philadelphia chromosome-positive acute lymphoblastic leukemia (ALL) and, less commonly, for dermatofibrosarcoma protuberans.

**Extracted JSON:**
```json
{
  "nodes": [
    {
      "id": "n1",
      "type": "Compound",
      "name": "imatinib"
    },
    {
      "id": "n2",
      "type": "Gene",
      "name": "BCR-ABL"
    },
    {
      "id": "n3",
      "type": "Disease",
      "name": "chronic myeloid leukemia"
    },
    {
      "id": "n4",
      "type": "Gene",
      "name": "c-KIT"
    },
    {
      "id": "n5",
      "type": "Gene",
      "name": "PDGFRA"
    },
    {
      "id": "n6",
      "type": "Disease",
      "name": "gastrointestinal stromal tumors"
    },
    {
      "id": "n7",
      "type": "Disease",
      "name": "Philadelphia chromosome-positive acute lymphoblastic leukemia"
    },
    {
      "id": "n8",
      "type": "Disease",
      "name": "dermatofibrosarcoma protuberans"
    }
  ],
  "relationships": [
    {
      "source": "n1",
      "relation": "binds",
      "target": "n2"
    },
    {
      "source": "n1",
      "relation": "treats",
      "target": "n3"
    },
    {
      "source": "n1",
      "relation": "binds",
      "target": "n4"
    },
    {
      "source": "n1",
      "relation": "binds",
      "target": "n5"
    },
    {
      "source": "n1",
      "relation": "treats",
      "target": "n6"
    },
    {
      "source": "n1",
      "relation": "treats",
      "target": "n7"
    },
    {
      "source": "n1",
      "relation": "treats",
      "target": "n8"
    }
  ]
}
```

### q04
**Question:** Which proteins interact with TP53?

**Answer:** TP53 interacts with numerous proteins, including MDM2 (a key negative regulator that ubiquitinates and promotes TP53 degradation), p21 (a downstream target involved in cell cycle arrest), BAX (a pro-apoptotic protein activated by TP53), ATM (a kinase that phosphorylates TP53 in response to DNA damage), 14-3-3 (which modulates TP53 stability and localization), and E2F family members (involved in cell cycle regulation). It also interacts with proteins like GADD45 (involved in DNA repair) and TRADD (linked to apoptosis pathways). These interactions are context-dependent and critical for TP53's roles in tumor suppression, DNA repair, and apoptosis.

**Extracted JSON:**
```json
{
  "nodes": [
    {
      "id": "n1",
      "type": "Gene",
      "name": "TP53"
    },
    {
      "id": "n2",
      "type": "Gene",
      "name": "MDM2"
    },
    {
      "id": "n3",
      "type": "Gene",
      "name": "p21"
    },
    {
      "id": "n4",
      "type": "Gene",
      "name": "BAX"
    },
    {
      "id": "n5",
      "type": "Gene",
      "name": "ATM"
    },
    {
      "id": "n6",
      "type": "Gene",
      "name": "14-3-3"
    },
    {
      "id": "n7",
      "type": "Gene",
      "name": "E2F"
    },
    {
      "id": "n8",
      "type": "Gene",
      "name": "GADD45"
    },
    {
      "id": "n9",
      "type": "Gene",
      "name": "TRADD"
    }
  ],
  "relationships": [
    {
      "source": "n1",
      "relation": "interactsWith",
      "target": "n2"
    },
    {
      "source": "n1",
      "relation": "interactsWith",
      "target": "n3"
    },
    {
      "source": "n1",
      "relation": "interactsWith",
      "target": "n4"
    },
    {
      "source": "n1",
      "relation": "interactsWith",
      "target": "n5"
    },
    {
      "source": "n1",
      "relation": "interactsWith",
      "target": "n6"
    },
    {
      "source": "n1",
      "relation": "interactsWith",
      "target": "n7"
    },
    {
      "source": "n1",
      "relation": "interactsWith",
      "target": "n8"
    },
    {
      "source": "n1",
      "relation": "interactsWith",
      "target": "n9"
    }
  ]
}
```

### q05
**Question:** What drugs are used to treat chronic myeloid leukemia?

**Answer:** Chronic myeloid leukemia (CML) is primarily treated with tyrosine kinase inhibitors (TKIs), which target the BCR-ABL fusion protein caused by the Philadelphia chromosome. First-line therapies include **imatinib** (Gleevec), **dasatinib** (Sprycel), and **nilotinib** (Tasigna). These drugs are effective in the chronic phase of CML and have improved outcomes compared to older treatments like interferon or chemotherapy.  

For patients resistant to or intolerant of first-generation TKIs, **bosutinib** (Bosulif), **ponatinib** (Iclusig) — particularly effective against the T315I mutation — and **asciminib** (Blincyto) are used. **Omacetaxine mepesuccinate** (Mylophore) is another option for resistant or relapsed cases. In advanced stages or when TKIs fail, allogeneic stem cell transplantation may be considered. Treatment selection depends on disease phase, genetic mutations, and patient factors.

**Extracted JSON:**
```json
{
  "nodes": [
    {
      "id": "n1",
      "type": "Disease",
      "name": "chronic myeloid leukemia"
    },
    {
      "id": "n2",
      "type": "Compound",
      "name": "imatinib"
    },
    {
      "id": "n3",
      "type": "Compound",
      "name": "dasatinib"
    },
    {
      "id": "n4",
      "type": "Compound",
      "name": "nilotinib"
    },
    {
      "id": "n5",
      "type": "Compound",
      "name": "bosutinib"
    },
    {
      "id": "n6",
      "type": "Compound",
      "name": "ponatinib"
    },
    {
      "id": "n7",
      "type": "Compound",
      "name": "asciminib"
    },
    {
      "id": "n8",
      "type": "Compound",
      "name": "omacetaxine mepesuccinate"
    },
    {
      "id": "n9",
      "type": "Gene",
      "name": "BCR-ABL"
    }
  ],
  "relationships": [
    {
      "source": "n2",
      "relation": "treats",
      "target": "n1"
    },
    {
      "source": "n3",
      "relation": "treats",
      "target": "n1"
    },
    {
      "source": "n4",
      "relation": "treats",
      "target": "n1"
    },
    {
      "source": "n5",
      "relation": "treats",
      "target": "n1"
    },
    {
      "source": "n6",
      "relation": "treats",
      "target": "n1"
    },
    {
      "source": "n7",
      "relation": "treats",
      "target": "n1"
    },
    {
      "source": "n8",
      "relation": "treats",
      "target": "n1"
    },
    {
      "source": "n9",
      "relation": "binds",
      "target": "n2"
    },
    {
      "source": "n9",
      "relation": "binds",
      "target": "n3"
    },
    {
      "source": "n9",
      "relation": "binds",
      "target": "n4"
    },
    {
      "source": "n9",
      "relation": "binds",
      "target": "n5"
    },
    {
      "source": "n9",
      "relation": "binds",
      "target": "n6"
    },
    {
      "source": "n9",
      "relation": "binds",
      "target": "n7"
    },
    {
      "source": "n9",
      "relation": "binds",
      "target": "n8"
    }
  ]
}
```

## Failures

- none