# expv2-1: qwen alone vs. qwen+ToG (over local KQA Pro kb.json)

- Model: qwen3:14b
- Sample size: 30 questions from val.json (open-ended, 'choices' field ignored)
- Questions with no linkable topic entity (ToG falls back to no-KG): 4/30

## Overall (all questions)

| | EM | F1 |
|---|---|---|
| Baseline (qwen alone) | 0.3 | 0.372 |
| qwen + ToG | 0.2 | 0.332 |

## Subset with a linkable topic entity (n=26) — the only questions where ToG could actually use the KG

| | EM | F1 |
|---|---|---|
| Baseline (qwen alone) | 0.346 | 0.429 |
| qwen + ToG | 0.192 | 0.345 |

- Baseline latency (s): {'mean': 0.432, 'min': 0.103, 'max': 1.686}
- ToG LLM calls per question: {'mean': 119.767, 'min': 1.0, 'max': 711.0}

## Per-question detail

- Q: Which person who did not die in 30 BC is identified by ISNI 0000 0000 3228 1047?
  gold='Jon Anderson' | baseline='Johann Wolfgang von Goethe' (EM=False) | tog='Johann Wolfgang von Goethe' (EM=False, no_topic=True)
- Q: How many US cities have the demonym Angeleno or have a founding year besides 1830?
  gold='478' | baseline='0' (EM=False) | tog='1' (EM=False, no_topic=False)
- Q: Is the Twitter username of a person, who is the presenter of  American Idol (the one that received 59th Primetime Emmy Awards), DwayneWade (the subscription number of this statement is 17045544) ?
  gold='no' | baseline='No' (EM=True) | tog='No' (EM=True, no_topic=False)
- Q: What number of unitary states have an inflation rate higher than the 6800 percentage?
  gold='1' | baseline='0' (EM=False) | tog='0' (EM=False, no_topic=True)
- Q: Was Bolt (the one whose Nintendo GameID is RLUR4Q) not published in Europe in 2019 ?
  gold='yes' | baseline='Yes' (EM=True) | tog='Yes, Bolt was not published in Europe in 2019' (EM=False, no_topic=False)
- Q: how many philosophy belong to either the work field of Arthur Schopenhauer or that is a part of ethics
  gold='2' | baseline="It is not possible to provide a specific number as both Schopenhauer's philosophy and ethics are broad and overlapping areas" (EM=False) | tog='25' (EM=False, no_topic=False)
- Q: What is the one with the larger duration, In the Name of the King or The Phantom (which was produced by Paramount Pictures)
  gold='In the Name of the King' | baseline='In the Name of the King' (EM=True) | tog='In the Name of the King' (EM=True, no_topic=False)
- Q: For the animated-feature film that has Chris Evans (the one that was born in Boston) as a voice actor (the character role of this statement is Casey Jones), where is it published on its 2008-02-08 publication date?
  gold='Japan' | baseline='The animated feature film is "WALL-E," and it was published by Pixar Animation Studios and released by Walt Disney Studios' (EM=False) | tog='TMNT' (EM=False, no_topic=False)
- Q: Which has less cost, Seven Psychopaths or Home Alone starring Hope Davis?
  gold='Seven Psychopaths' | baseline='Home Alone starring Hope Davis has less cost' (EM=False) | tog='Seven Psychopaths has less cost' (EM=False, no_topic=False)
- Q: How many names given to females match the name given to Helen Hunt or the name given to Boston-born William Morris ?
  gold='2' | baseline='2' (EM=True) | tog='2' (EM=True, no_topic=False)
- Q: What national association football team is located in Belgium?
  gold='Belgium national football team' | baseline='The Belgium national football team' (EM=True) | tog='La Unió fa la força' (EM=False, no_topic=False)
- Q: Was the association football club with the website of http://www.uniaodeleiria.pt/ founded after 1694?
  gold='yes' | baseline='No' (EM=False) | tog='No' (EM=False, no_topic=False)
- Q: How many rivers are not 59.6 km long?
  gold='8' | baseline='It is not possible to determine without knowing the total number of rivers and how many are 59.6 km long' (EM=False) | tog='The question cannot be answered with the given information' (EM=False, no_topic=True)
- Q: What was the work that Laurence Mark was nominated for the Academy Award for Best Picture about?
  gold='69th Academy Awards' | baseline='"The Last Emperor," which tells the story of Pu Yi, the last emperor of China, and his life through the fall of the Qing Dynasty and the rise of the People\'s Republic of China' (EM=False) | tog='Laurence Mark was nominated for the Academy Award for Best Picture for his work on the film "Ted."' (EM=False, no_topic=False)
- Q: Regarding Chester—which is the HQ site of Philadelphia Union—what's the language pertaining to its http://www.chestercity.com website?
  gold='English' | baseline='English' (EM=True) | tog='English' (EM=True, no_topic=False)
- Q: Since when has Harare been the twinned administrative body of Munich (the one whose ISNI is 0000 0001 2189 3141)?
  gold='1996-01-01' | baseline='Harare has been twinned with Munich since 1994' (EM=False) | tog='Since 2005/1/1' (EM=False, no_topic=False)
- Q: Which has lower elevation above sea level, Zürich or Luxembourg whose population is 75399?
  gold='Luxembourg' | baseline='Luxembourg' (EM=True) | tog='Luxembourg has a lower elevation above sea level than Zürich' (EM=False, no_topic=False)
- Q: Does El Paso County (whose FIPS 6-4 for US counties is 08041) or Nye County have the larger area?
  gold='Nye County' | baseline='El Paso County' (EM=False) | tog='Nye County has the larger area' (EM=False, no_topic=False)
- Q: Who has more children, Jon Favreau, who began his career in 1992, or Warren G. Harding, who died after a myocardial infarction?
  gold='Jon Favreau' | baseline='Jon Favreau has more children' (EM=False) | tog='Jon Favreau has more children' (EM=False, no_topic=False)
- Q: Does Yiddish or Dutch (whose GOST 7.75–97 code is нид 495) have more speakers?
  gold='Dutch' | baseline='Dutch' (EM=True) | tog='Dutch has more speakers than Yiddish' (EM=False, no_topic=False)
- Q: How many crimes are in country of France or have Iconclass notation 44G544?
  gold='2' | baseline='Not available without specific data sources' (EM=False) | tog='France, officially known as the French Republic, has a nominal GDP of approximately $2.855 trillion and a PPP GDP of around $2.871 trillion. Its GDP per capita (PPP) is about $39,328, and the nominal GDP per capita is approximately $36,205.57. The country\'s motto is "Liberté, égalité, fraternité," and its official language is French. The mains voltage is 230 V, and the country\'s mobile country code is 208. The unemployment rate is 10%' (EM=False, no_topic=False)
- Q: Is the Munzinger IBA of the person that lives in the Cork the same as 00000018201?
  gold='no' | baseline='No' (EM=True) | tog='No' (EM=True, no_topic=False)
- Q: How is John Bailey (the one whose CANTIC-ID is a11706788) connected to Santa Clara University?
  gold='educated at' | baseline='John Bailey is connected to Santa Clara University as a faculty member or staff member' (EM=False) | tog='John Bailey was educated at Santa Clara University' (EM=False, no_topic=False)
- Q: Who is taller, Stevie Nicks or Tim Robbins?
  gold='Tim Robbins' | baseline='Tim Robbins is taller' (EM=False) | tog='Tim Robbins is taller' (EM=False, no_topic=False)
- Q: Was the person with ISNI 0000 0001 1953 270X born after 1942?
  gold='yes' | baseline='No' (EM=False) | tog='Yes' (EM=True, no_topic=True)
- Q: How is How I Met Your Mother related to Ernie Hudson?
  gold='cast member' | baseline='Ernie Hudson guest-starred in "How I Met Your Mother" as Mr. Peanutbutter\'s Dad in Season 5, Episode 13' (EM=False) | tog='How I Met Your Mother is not directly related to Ernie Hudson based on the provided information' (EM=False, no_topic=False)
- Q: How many non-metro district comprise an enclave within Woking (the one whose OS grid reference is TQ0040358550) or consist of an area of less than 690,000 hectares ?
  gold='2' | baseline='0' (EM=False) | tog='0' (EM=False, no_topic=False)
- Q: What is the determination method of 79, the ranking of the national association football team that has member Ben Sahar?
  gold='FIFA World Rankings' | baseline='The determination method of 79 refers to the FIFA World Ranking system, which evaluates teams based on results from international matches. Ben Sahar is a player from the Israeli national association football team' (EM=False) | tog='The determination method of 79 is not directly related to the ranking of the national association football team with member Ben Sahar, as the provided information does not specify the ranking method or the team associated with Ben Sahar' (EM=False, no_topic=False)
- Q: What is the connection between Akshay Kumar to Amritsar?
  gold='place of birth' | baseline='Akshay Kumar was born in Amritsar' (EM=False) | tog='Akshay Kumar was born in Amritsar' (EM=False, no_topic=False)
- Q: Is The Adventures of Pluto Nash or The Rose the longer work?
  gold='The Rose' | baseline='The Rose is the longer work' (EM=False) | tog='The Rose is the longer work' (EM=False, no_topic=False)