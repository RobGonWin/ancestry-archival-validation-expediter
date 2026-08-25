# Public longevity source register

This register supports source classification and contradiction tracking. It is
not a pedigree, genetic analysis, medical assessment, or claim about any
maintainer's family. Machine-readable records are in
[`data/longevity-sources.json`](../../data/longevity-sources.json) and
[`data/longevity-cluster-public.json`](../../data/longevity-cluster-public.json).

## Scope and terminology

- `centenarian` means age 100 or older; use `centenarian_100_104` when
  mutually exclusive categories are required.
- `semi-supercentenarian` means ages 105 through 109 inclusive.
- `supercentenarian` means age 110 or older.
- Store the exact attained age and validation status, then derive an age-band
  label. A study that loosely recruits people aged `105+` must not be relabeled
  as a pure 105--109 cohort.
- `longevity cluster` means a study grouping until validated ages, denominators,
  geography, migration, ascertainment, and alternative explanations have been
  evaluated. It never implies a shared gene by itself.

The [International Database on Longevity](https://www.supercentenarians.org/en)
is the principal international research resource in this register for
systematically validated deaths at the highest ages. Media lists and family
trees are discovery sources, not substitutes for age validation.

## Historical age validation and case documentation

| ID | Source and role | Narrow support | Cannot support |
| --- | --- | --- | --- |
| `YOUNG-2008-AALA-THESIS` | Robert Douglas Young, [*African American Longevity Advantage: Myth or Reality? A Racial Comparison of Supercentenarian Data*](https://doi.org/10.57709/1062194), M.A. thesis, 2008; [official PDF](https://scholarworks.gsu.edu/bitstreams/61ab0001-a793-4ad1-bf66-5555b565bdd4/download) | Historical population comparison of validated supercentenarian cases. | It is not a peer-reviewed journal article and contains no genotyping, pedigree, family-cluster, or causal analysis. |
| `YOUNG-2010-AGE115` | Robert Young, ["Age 115 or more in the United States: Fact or fiction?"](https://doi.org/10.1007/978-3-642-11520-2_15), 2010; [open chapter](https://www.demogr.mpg.de/books/drm/007/3-3.pdf) | Documentary age-validation methods; the Bettie Wilson case; preservation of a reported birth-year conflict. | It does not prove inherited longevity or resolve every family-reported date. |
| `YOUNG-2004-BETTIE-VISIT` | Robert Young, ["Bettie Wilson Visit; November 28, 2004"](https://grg.org/BWilson.htm) | Primary-observer account of that visit and observed functioning. | It cannot establish the presence, memory, or identity of an unlisted person. |
| `YOUNG-ETAL-2010-MYTHS` | Young et al., ["Typologies of Extreme Longevity Myths"](https://doi.org/10.1155/2010/423087) | Skeptical, document-first validation methodology. | It does not establish a family-specific biological mechanism. |

The separate 2010 biographical chapter ["Jeanne Calment and her
successors"](https://doi.org/10.1007/978-3-642-11520-2_16) is coauthored by
Jeune, Robine, Young, Desjardins, Skytthe, and Vaupel; it must not be
attributed to Young alone.

## Global exceptional-longevity research

| Research lane | Representative sources | What the lane can support | Main limit |
| --- | --- | --- | --- |
| Scope and harmonization | [Abdelraheem et al. 2026 scoping review](https://doi.org/10.1155/jare/1605361) | Maps a large body of literature and documents inconsistent terminology and measurement across semi- and supercentenarian research. | The paper itself reports differing included-study counts in its abstract and body; a scoping review does not make every included result causal or comparable. |
| Familial aggregation | [Perls et al. 2002](https://doi.org/10.1073/pnas.122587599); [NIA Long Life Family Study design](https://doi.org/10.1093/gerona/glab333) | Long-lived families and siblings can show group-level survival and healthy-aging advantages. | Shared environment, cohort, selection, and assortative mating remain alternatives to a purely genetic explanation. |
| Heritability calibration | [Ruby et al. 2018](https://doi.org/10.1534/genetics.118.301613) | Lifespan correlations among in-laws show why assortative mating can inflate conventional heritability estimates. | It does not rule out rare variants or mechanisms in particular families. |
| Biomarkers | [Hirata et al. 2020](https://doi.org/10.1038/s41467-020-17636-0) | Longitudinal biomarker associations in 1,427 oldest-old participants, including semi- and supercentenarians. | Association is not a personal diagnostic, intervention, or proof of cause. |
| Immune-cell studies | [Hashimoto et al. 2019](https://doi.org/10.1073/pnas.1907883116); [Plaza-Florido et al. 2026 review](https://doi.org/10.1038/s41577-026-01291-5) | Cytotoxic immune-cell expansion and broader immune-homeostasis hypotheses are active research directions. | Cohorts are often small, heterogeneous, and observational. |
| Longevity GWAS/WGS | [Deelen et al. 2019](https://doi.org/10.1038/s41467-019-11558-2); [Garagnani et al. 2021](https://doi.org/10.7554/eLife.57849) | `APOE` is the most consistently replicated common locus; other common and rare findings are candidates with varying replication. | Population associations do not predict an individual's lifespan or identify an ancestor of origin. |
| Polygenic scores | [Gunn et al. 2022](https://doi.org/10.1007/s11357-022-00518-2); [Ding et al. 2023](https://doi.org/10.1038/s41586-023-06079-4) | Group-level score distributions and ancestry-related portability limits can be studied. | A score needs exact weights, quality control, ancestry-matched calibration, and independent validation; it is not kinship proof. |

### 2026 cytotoxic CD4 T-cell study and news coverage

Hashimoto et al., ["CD4 CTLs in Supercentenarians: Signs of Adaptive
Expansion in Healthy Aging"](https://doi.org/10.1016/j.celrep.2026.117728),
reported expanded cytotoxic CD4 T-cell populations in a small cross-sectional
cohort that included 10 supercentenarians, 10 centenarians, and 8 participants
aged 70--99, with additional machine-learning analysis of a larger dataset.
This supports an association and a hypothesis about persistent-antigen
adaptation. It does **not** show that the cells caused exceptional longevity,
prevented cancer, or can be inferred from a consumer genotype.

[Scientific American coverage](https://www.scientificamerican.com/article/supercentenarians-have-a-cellular-superpower/)
and [New Scientist coverage](https://www.newscientist.com/article/2585352-supercentenarians-have-an-abundance-of-immune-cells-that-ward-off-cancer/)
are useful discovery and communication sources. Claims in those stories must
be traced back to the Cell Reports study; headlines are not causal evidence.

## Geographic longevity clusters

The 2025 review ["Blue Zones, an Analysis of Existing Evidence through a
Scoping Review"](https://doi.org/10.14336/AD.2025.0461) found published work
covering ten areas. The list records what has been studied, not a guarantee that
each location is a validated or causal longevity zone.

| Area reviewed | Evidence state reported by the review |
| --- | --- |
| Ogliastra, Sardinia, Italy | Higher longevity than the national comparison; comparatively well characterized. |
| Okinawa, Japan | Higher longevity than the national comparison; comparatively well characterized. |
| Nicoya, Costa Rica | Higher longevity than the national comparison; comparatively well characterized. |
| Ikaria, Greece | Studies reported high life expectancy; causal attribution remains unresolved. |
| Cilento, Italy | Studies reported high life expectancy; causal attribution remains unresolved. |
| One municipality in the Netherlands | A higher proportion of exceptional longevity than other municipalities was reported. |
| Martinique and Guadeloupe | A higher prevalence of supercentenarian deaths than metropolitan France was reported. |
| Menorca, Spain | Evidence was inconclusive. |
| Rugao, China | The review reported fewer centenarians than stronger candidate zones. |
| Loma Linda, California, United States | The review found no eligible scientific studies of a naturally occurring zone. |

A nationwide Danish registry scan found that the result changes with the
geographic question: a rural-island birth hotspot had 222 centenarians, 1.37
times the expected count, while late-life residence hotspots were affected by
migration and socioeconomic selection. See [Hansen et al.
2018](https://doi.org/10.1016/j.exger.2018.09.020). "Place associated with a
birth cohort" is therefore not equivalent to "place that makes a person live
longer," and a modern map cannot reconstruct historic exposure.

## Population heterogeneity

Ouellette and Perls, ["Race and ethnicity dynamics in survival to 100 years in
the United States"](https://doi.org/10.1111/joim.20031), used national NCHS
period life tables and reported late-age mortality differences across broad
administrative categories.

Evidence role: `population_context` only. The study is not a recruited family
cohort, geographic-cluster study, pedigree analysis, or genomic study. Census
race categories are not DNA ancestry, and the analysis cannot connect a
particular family to a national mortality pattern or separate genes from
shared environment.

Kestenbaum and Ferguson's [historical U.S. supercentenarian
chapter](https://www.demogr.mpg.de/books/drm/007/2-1.pdf) is useful demographic
context, but historical tables require later validation checks.

## Consumer DNA and SNP guardrail

Evidence tiers must remain explicit:

- **Replicated population association:** `APOE`; `FOXO3` has repeated but
  smaller and phenotype-dependent support.
- **Candidate or cohort-specific findings:** `GPR78`, `CDKN2B-AS1`, and
  individual DNA-repair, clonal-hematopoiesis, or rare-variant findings.
- **Unsupported personal inference:** "I carry SNP X, therefore I inherited
  exceptional longevity from ancestor Y."

A consumer DNA array samples an incomplete marker set. Even a valid longevity
association is probabilistic and population-level. Direct-to-consumer raw-data
findings can also require laboratory confirmation; [Tandy-Connor et al.
2018](https://doi.org/10.1038/gim.2018.38) studied a referral-enriched sample,
so its reported false-positive fraction must not be generalized to every
consumer result. Allele presence does not identify the transmitting ancestor
without appropriately phased relatives. Pedigree/kinship proof and longevity
mechanism research are separate evidence tracks.

## Public Wilson/Rogers research grouping

The public registry groups Bettie Rutherford Wilson, Willie Rogers, Dewey
Wilson, and Elder Roma Wilson because public sources report family or in-law
connections and unusual longevity. "Cluster" here means a research grouping,
not a proven genetic cluster.

- Bettie's validated age is `documentarily_supported`.
- Young's 2004 visit details are `primary_observer_supported`.
- Willie's birth year remains `conflicting_public_reports`.
- Dewey's reported age at death remains `conflicting_secondary_reports`.
- Roma's brother-in-law relationship to Bettie is
  `secondary_source_reported_needs_primary_document`.
- Any inherited-longevity explanation is `unsupported_hypothesis`.

Elder Roma Wilson's 1994 National Heritage Fellowship is independently listed
by the [National Endowment for the Arts](https://www.arts.gov/honors/heritage/elder-roma-wilson),
and a later [Soul Bag obituary](https://www.soulbag.fr/elder-roma-wilson-1910-2018/)
reports that he remained musically active at age 107. Those sources document
public biography and age context, not kinship or genetics. On that reported
age, 107 falls in the semi-supercentenarian band; applying the band label does
not upgrade the underlying age-validation status.

## Registry rule

Every source record must state both `supports` and `cannot_support`. Secondary
coverage must point to its underlying study where available. Contradictory
dates, validation states, and cohort definitions remain visible rather than
being silently reconciled.
