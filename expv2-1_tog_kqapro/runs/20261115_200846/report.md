# expv2-1: qwen alone vs. qwen+ToG (over local KQA Pro kb.json)

- Model: qwen3:14b
- Sample size: 30 questions from val.json (open-ended, 'choices' field ignored)
- Questions with no linkable topic entity (ToG falls back to no-KG): 4/30

## Overall (all questions)

| | EM | F1 |
|---|---|---|
| Baseline (qwen alone) | 0.367 | 0.38 |
| qwen + ToG | 0.567 | 0.567 |

## Subset with a linkable topic entity (n=26) — the only questions where ToG could actually use the KG

| | EM | F1 |
|---|---|---|
| Baseline (qwen alone) | 0.423 | 0.438 |
| qwen + ToG | 0.615 | 0.615 |

- Baseline latency (s): {'mean': 0.365, 'min': 0.109, 'max': 3.532}
- ToG LLM calls per question: {'mean': 120.233, 'min': 1.0, 'max': 711.0}

## Per-question detail

- Q: Which person who did not die in 30 BC is identified by ISNI 0000 0000 3228 1047?
  gold='Jon Anderson' | baseline='Leonardo da Vinci' (EM=False) | tog='Leonardo da Vinci' (EM=False, no_topic=True)
- Q: How many US cities have the demonym Angeleno or have a founding year besides 1830?
  gold='478' | baseline='1' (EM=False) | tog='1' (EM=False, no_topic=False)
- Q: Is the Twitter username of a person, who is the presenter of  American Idol (the one that received 59th Primetime Emmy Awards), DwayneWade (the subscription number of this statement is 17045544) ?
  gold='no' | baseline='No' (EM=True) | tog='No' (EM=True, no_topic=False)
- Q: What number of unitary states have an inflation rate higher than the 6800 percentage?
  gold='1' | baseline='0' (EM=False) | tog='0' (EM=False, no_topic=True)
- Q: Was Bolt (the one whose Nintendo GameID is RLUR4Q) not published in Europe in 2019 ?
  gold='yes' | baseline='No' (EM=False) | tog='yes' (EM=True, no_topic=False)
- Q: how many philosophy belong to either the work field of Arthur Schopenhauer or that is a part of ethics
  gold='2' | baseline='2' (EM=True) | tog='26' (EM=False, no_topic=False)
- Q: What is the one with the larger duration, In the Name of the King or The Phantom (which was produced by Paramount Pictures)
  gold='In the Name of the King' | baseline='In the Name of the King' (EM=True) | tog='In the Name of the King' (EM=True, no_topic=False)
- Q: For the animated-feature film that has Chris Evans (the one that was born in Boston) as a voice actor (the character role of this statement is Casey Jones), where is it published on its 2008-02-08 publication date?
  gold='Japan' | baseline='Walt Disney Studios Home Entertainment' (EM=False) | tog='TMNT' (EM=False, no_topic=False)
- Q: Which has less cost, Seven Psychopaths or Home Alone starring Hope Davis?
  gold='Seven Psychopaths' | baseline='Home Alone starring Hope Davis' (EM=False) | tog='Seven Psychopaths' (EM=True, no_topic=False)
- Q: How many names given to females match the name given to Helen Hunt or the name given to Boston-born William Morris ?
  gold='2' | baseline='1' (EM=False) | tog='2' (EM=True, no_topic=False)
- Q: What national association football team is located in Belgium?
  gold='Belgium national football team' | baseline='Belgium national football team' (EM=True) | tog='471821105940.323' (EM=False, no_topic=False)
- Q: Was the association football club with the website of http://www.uniaodeleiria.pt/ founded after 1694?
  gold='yes' | baseline='yes' (EM=True) | tog='yes' (EM=True, no_topic=False)
- Q: How many rivers are not 59.6 km long?
  gold='8' | baseline='0' (EM=False) | tog='Infinite' (EM=False, no_topic=True)
- Q: What was the work that Laurence Mark was nominated for the Academy Award for Best Picture about?
  gold='69th Academy Awards' | baseline='The work was "The Last Emperor"' (EM=False) | tog='Ted' (EM=False, no_topic=False)
- Q: Regarding Chester—which is the HQ site of Philadelphia Union—what's the language pertaining to its http://www.chestercity.com website?
  gold='English' | baseline='English' (EM=True) | tog='English' (EM=True, no_topic=False)
- Q: Since when has Harare been the twinned administrative body of Munich (the one whose ISNI is 0000 0001 2189 3141)?
  gold='1996-01-01' | baseline='1991' (EM=False) | tog='2005/1/1' (EM=False, no_topic=False)
- Q: Which has lower elevation above sea level, Zürich or Luxembourg whose population is 75399?
  gold='Luxembourg' | baseline='Luxembourg' (EM=True) | tog='Luxembourg' (EM=True, no_topic=False)
- Q: Does El Paso County (whose FIPS 6-4 for US counties is 08041) or Nye County have the larger area?
  gold='Nye County' | baseline='El Paso County' (EM=False) | tog='Nye County' (EM=True, no_topic=False)
- Q: Who has more children, Jon Favreau, who began his career in 1992, or Warren G. Harding, who died after a myocardial infarction?
  gold='Jon Favreau' | baseline='Jon Favreau' (EM=True) | tog='Jon Favreau' (EM=True, no_topic=False)
- Q: Does Yiddish or Dutch (whose GOST 7.75–97 code is нид 495) have more speakers?
  gold='Dutch' | baseline='Yiddish' (EM=False) | tog='Dutch' (EM=True, no_topic=False)
- Q: How many crimes are in country of France or have Iconclass notation 44G544?
  gold='2' | baseline='Not applicable' (EM=False) | tog='France' (EM=False, no_topic=False)
- Q: Is the Munzinger IBA of the person that lives in the Cork the same as 00000018201?
  gold='no' | baseline='No' (EM=True) | tog='no' (EM=True, no_topic=False)
- Q: How is John Bailey (the one whose CANTIC-ID is a11706788) connected to Santa Clara University?
  gold='educated at' | baseline='John Bailey is connected to Santa Clara University as a professor in the Department of Electrical Engineering' (EM=False) | tog='educated at' (EM=True, no_topic=False)
- Q: Who is taller, Stevie Nicks or Tim Robbins?
  gold='Tim Robbins' | baseline='Tim Robbins' (EM=True) | tog='Tim Robbins' (EM=True, no_topic=False)
- Q: Was the person with ISNI 0000 0001 1953 270X born after 1942?
  gold='yes' | baseline='No' (EM=False) | tog='Yes' (EM=True, no_topic=True)
- Q: How is How I Met Your Mother related to Ernie Hudson?
  gold='cast member' | baseline='Ernie Hudson guest-starred in an episode of How I Met Your Mother' (EM=False) | tog='No' (EM=False, no_topic=False)
- Q: How many non-metro district comprise an enclave within Woking (the one whose OS grid reference is TQ0040358550) or consist of an area of less than 690,000 hectares ?
  gold='2' | baseline='0' (EM=False) | tog='0' (EM=False, no_topic=False)
- Q: What is the determination method of 79, the ranking of the national association football team that has member Ben Sahar?
  gold='FIFA World Rankings' | baseline='79' (EM=False) | tog='79' (EM=False, no_topic=False)
- Q: What is the connection between Akshay Kumar to Amritsar?
  gold='place of birth' | baseline='Akshay Kumar is not directly connected to Amritsar in a notable way' (EM=False) | tog='place of birth' (EM=True, no_topic=False)
- Q: Is The Adventures of Pluto Nash or The Rose the longer work?
  gold='The Rose' | baseline='The Rose' (EM=True) | tog='The Rose' (EM=True, no_topic=False)