# Generation, cohort, memory, and event-presence source register

This register audits claims raised in public discussions of rare
intergenerational encounters. It does not identify a private person, reproduce
a recollection, or conclude that anyone attended a historical event. The
machine-readable source records are in
[`data/generation-cohort-sources.json`](../../data/generation-cohort-sources.json).

## Bottom-line verdict

| Claim lane | Verdict | Defensible statement |
| --- | --- | --- |
| Generation membership | Convention-dependent | Use birth year first and name the convention. Pew, Census, and McCrindle boundaries differ. |
| Number of people who could meet a very old relative | Estimable only as a scenario | Births, survival, household structure, relationship opportunity, and contact are separate filters. No complete global meeting registry was found. |
| A unique or single-digit cohort | Not verified | Earlier values such as “hundreds,” “low tens,” or “single digits” are Fermi estimates unless every factor and sensitivity range is supplied. |
| Familial longevity | Supported at group level | Selected centenarian and supercentenarian families show survival aggregation; this does not prove a mechanism or predict an individual lifespan. |
| Family or community connection | Associated with health and survival | Social-relationship studies do not establish genetic longevity, closeness to a specific relative, or attendance at an event. |
| Infant memory encoding | Supported | Memory-related hippocampal activity appears around age one in the 2025 infant fMRI study. Encoding is not proof of adult autobiographical access. |
| Childhood amnesia | Supported as a forgetting process | Prospective work shows increasing loss of early-life events across childhood, with substantial variation. |
| ACEs as a memory advantage | Not supported | ACEs are a health-risk framework; a 2024 review more often found negative or mixed autobiographical-memory associations. |
| Presence during a named event | Requires person-specific evidence | A public scene, census co-residence, kinship, date overlap, or recollection alone is not a complete attendee record. |

## Generation labels are not one shared measurement system

- Pew's historical convention places Gen X in 1965--1980 and the Greatest
  Generation in 1927 or earlier. Pew now recommends narrower age cohorts when
  broad labels add more noise than value.
- A 2025 Census report used Gen Z 1997--2012 and Gen Alpha 2013 onward for its
  geographic-mobility analysis. This is a report convention, not a universal
  legal definition.
- McCrindle uses Gen Z 1995--2009, Gen Alpha 2010--2024, and Gen Beta
  2025--2039. Gen Beta is therefore a named private-research convention, not a
  Census or scientific standard.
- The Census Bureau is an authority for the 1946--1964 baby-boom interval, but
  generational labels such as Gen X, Gen Z, Alpha, and Beta remain analytical
  choices.

For cross-generation encounter research, store exact birth years and ages on
the event date. Add labels only as display metadata with a convention URL.

## Building a `likely_cohort` scenario

The starting denominator can come from [UN World Population Prospects
2024](https://www.un.org/development/desa/pd/content/World-Population-Prospects-2024)
or an official national source. Each later filter needs its own evidence role:

1. birth-year and geographic denominator;
2. age overlap between the younger and older people;
3. survival to the relevant ages;
4. existence of the stated kin relationship;
5. opportunity for contact or co-residence;
6. attendance at the particular event;
7. retention and later report of a memory.

Those filters are correlated and are rarely measured in one dataset. ACS table
[B10001](https://api.census.gov/data/2024/acs/acs5/groups/B10001.html) and
[B10051](https://api.census.gov/data/2024/acs/acs5/groups/B10051.html) describe
aggregate child-grandparent co-residence. They do not count great-grandparent
meetings, non-household contact, or event attendance. Consequently, multiplying
point estimates without dependency bounds creates false precision.

Use [`scripts/estimate_likely_cohort.py`](../../scripts/estimate_likely_cohort.py)
to expose low/high assumptions and correlation warnings. Its output is a
sensitivity interval, not an observed count. Infant-memory, ACE, genetic, and
recollection-accuracy factors are prohibited as numeric multipliers.

## Longevity families and social connection

[Perls et al. 2007](https://pubmed.ncbi.nlm.nih.gov/17895443/) studied 29
supercentenarian families. Conditional on survival to age 20, sisters had 2.9
times and brothers 4.3 times the comparison probability of surviving to 90.
The sample was small, and the measured outcome was survival to 90—not a
descendant reaching 110 or retaining an early memory.

The NIA Long Life Family Study deliberately selects exceptional families and
studies descendants. Its selectivity makes it useful for mechanism research,
not for estimating how common every reported family cluster is.

[Holt-Lunstad et al. 2010](https://doi.org/10.1371/journal.pmed.1000316)
reported a pooled association between stronger social relationships and
survival across 148 studies and 308,849 participants. The authors also noted
heterogeneity and the limits of causal inference. This supports family and
community connection as a health-research lane, not as kinship, genetic, or
attendance evidence.

[Ouellette and Perls 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC11636438/)
analyzed U.S. life tables and late-age survival across broad administrative
race and ethnicity categories. The paper is population context. It does not
establish a family cluster, convert race to DNA ancestry, or predict an
individual outcome.

## Childhood amnesia, earliest memories, and ACEs

[Yates et al. 2025](https://pubmed.ncbi.nlm.nih.gov/40112047/) found that
hippocampal activity during encoding predicted later memory-based looking
beginning around age one. The experiment measured infant behavior over a short
delay; it did not test an adult's autobiographical account of an infancy event.

[Bauer and Larkina 2014](https://pubmed.ncbi.nlm.nih.gov/24236647/) followed
events first discussed at age three. Children aged five to seven recalled at
least 60% of the events, while children aged eight to nine recalled fewer than
40%. This supports childhood amnesia as progressive forgetting and does not
validate or invalidate one adult account.

[Bauer's 2015 developmental review](https://pmc.ncbi.nlm.nih.gov/articles/PMC4669902/)
examines how episodic and autobiographical memories can be formed early yet
become disproportionately inaccessible through accelerated forgetting. It is
a framework for childhood amnesia, not a tool for authenticating one memory
or recovering historical truth through cueing.

A 2019 scholarly comment argued that reported age alone is not enough to call
an earliest memory fictional. That caution is symmetric: the same paper does
not prove that a specific memory is accurate.

The [CDC ACE framework](https://www.cdc.gov/aces/about/index.html) concerns
adverse exposures and later health risks. A [2024 systematic
review](https://pubmed.ncbi.nlm.nih.gov/38298520/) found mixed results and a
prevalent negative relationship between interpersonal childhood trauma and
autobiographical memory. ACEs therefore must not be used as an accuracy boost
or rarity multiplier.

## Public event scene versus attendee proof

Robert Young's [November 28, 2004 visit
report](https://grg.org/BWilson.htm) documents the date, setting, observations,
and his recorder accident. It names some people but does not claim to be a
complete roster. It supports `public_scene_context`, not the presence of an
unlisted person.

Young's [public gallery](https://grg.org/Gallery/ryounggallery.html) also
records a September 13, 2005 visit with Bettie. Together the pages support two
dated visits; they do not establish each visit's purpose or every attendee.

The historical GRG notice that the oldest-living-American title passed to
Bettie Wilson on December 1, 2004 and the April 2005 newspaper report of
Guinness acceptance establish title chronology. Neither source establishes who
was at the November visit. A registry of validated ages is also not a registry
of meetings between relatives.

Use [`scripts/assess_present_during_event.py`](../../scripts/assess_present_during_event.py)
to keep these states separate:

- `confirmed`: authenticated person-specific direct evidence or a human-reviewed complete roster;
- `supported`: a reviewed contemporaneous named record plus an independent report;
- `reported`: first-person or family report without qualifying corroboration;
- `unknown`: scene or opportunity context only;
- `contradicted`: reviewed person-specific contrary evidence;
- `contested`: qualifying direct evidence and qualifying contradiction coexist.

The classifier is an evidence-routing aid. It cannot authenticate media or
decide identity on its own.

Census, kinship, geography, age overlap, and a public scene never prove attendance.

## Historical intergenerational comparison

Young's [age-validation chapter](https://doi.org/10.1007/978-3-642-11520-2_15)
discusses Sarah Knauss, her daughter Kathryn “Kitty” Knauss Sullivan, and a
multi-generation family setting. This is a useful historical comparison for
the opportunity that extreme longevity can create for unusual generational
overlap. It is not a rate estimate, a meeting registry, or evidence that the
same family structure, inheritance, cognition, or event history applies to a
different family. The Kathryn Sullivan in this comparison is Sarah Knauss's
daughter; the name should not be conflated with an unrelated public figure.
