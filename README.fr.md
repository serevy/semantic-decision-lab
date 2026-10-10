# semantic-decision-lab

[English](README.md) | [日本語](README.ja.md) | [简体中文](README.zh-CN.md) | [한국어](README.ko.md) | **Français**

[![PDDR validation](https://github.com/serevy/semantic-decision-lab/actions/workflows/pddr.yml/badge.svg?branch=main)](https://github.com/serevy/semantic-decision-lab/actions/workflows/pddr.yml)
[![README structure](https://github.com/serevy/semantic-decision-lab/actions/workflows/readme-i18n.yml/badge.svg?branch=main)](https://github.com/serevy/semantic-decision-lab/actions/workflows/readme-i18n.yml)
[![GitHub Pages](https://github.com/serevy/semantic-decision-lab/actions/workflows/pages.yml/badge.svg?branch=main)](https://github.com/serevy/semantic-decision-lab/actions/workflows/pages.yml)
[![CodeRabbit Pull Request Reviews](https://img.shields.io/coderabbit/prs/github/serevy/semantic-decision-lab?utm_source=oss&utm_medium=github&utm_campaign=serevy%2Fsemantic-decision-lab&labelColor=171717&color=FF570A&link=https%3A%2F%2Fcoderabbit.ai&label=CodeRabbit+Reviews)](https://coderabbit.ai)

> **Expériences indépendantes des fournisseurs sur les couches de décision sémantique :** transformer un état ambigu en décisions typées et probabilistes que les systèmes déterministes peuvent exploiter.

La question fondamentale n’est pas « un LLM peut-il tout faire ? », mais plutôt :

> **Le jugement sémantique peut-il être isolé sous forme de petit composant logiciel testable, tandis que du code déterministe conserve le contrôle de l’exécution, des politiques et de la sécurité ?**

Ce dépôt explore cette question à travers l’orchestration, la sélection du contexte, les transmissions typées, l’interprétation de l’état, les contrôles de domaine, les systèmes en temps réel et les fournisseurs interchangeables de décisions sémantiques.

## Idée centrale

Une couche sémantique doit répondre à **ce que signifie l’état actuel**. Les systèmes déterministes restent responsables de **ce qui se passe ensuite**.

![Architecture du cœur décisionnel sémantique](docs/assets/semantic-decision-core.svg)

Cette séparation nous permet de tester le jugement sémantique indépendamment de la logique d’exécution. Elle rend également explicites l’incertitude, l’abstention, l’escalade et le remplacement du fournisseur, au lieu de les dissimuler dans un agent monolithique.

## Périmètre de recherche

Une revue de l’état de l’art menée en 2026 a relevé de nombreux travaux existants sur le routage et les cascades de modèles, la compression du contexte et des invites, les transmissions structurées entre agents, le suivi des états du dialogue et des actions, l’évaluation pragmatique, la supervision de trajectoires et de processus, la planification incarnée de haut niveau et les représentations intermédiaires.

Le laboratoire traite donc ces techniques comme **des composants et des références de comparaison**, sans revendiquer leur nouveauté intrinsèque. Son périmètre de recherche commun est plus précis :

> **Peut-on représenter un jugement sémantique ambigu sous forme d’états et de transitions typés, tenant compte de l’incertitude, qui préservent le comportement en aval, restent portables entre fournisseurs lorsque c’est réalisable, et demeurent subordonnés à l’exécution déterministe, à l’autorisation, aux politiques et aux garanties de sécurité impératives ?**

Les expériences devraient réutiliser autant que possible les méthodes existantes et concentrer les développements spécifiques sur la fidélité sémantique, l’étalonnage, l’abstention, les transitions d’état, les effets en aval et les limites d’autorité.

Pour les éléments probants et la décision de périmètre, voir [PDDR-0007](docs/records/PDDR-0007-focus-typed-semantic-state.md) et [#70 Radar des références externes](https://github.com/serevy/semantic-decision-lab/issues/70).
## Carte de recherche

| Domaine | Question de recherche | Principaux fils conducteurs |
|---|---|---|
| Orchestration | Le routage sémantique peut-il améliorer conjointement la réussite des tâches de bout en bout, les coûts, la latence et les besoins d’escalade ou de reprise ? | [#1 AI Work Routing](https://github.com/serevy/semantic-decision-lab/issues/1) |
| Contexte et mémoire | Dans quelle mesure peut-on réduire le contexte de l’historique des décisions tout en préservant le comportement décisionnel en aval ? | [#2 Sélection du contexte PDDR](https://github.com/serevy/semantic-decision-lab/issues/2), [#74 évaluation de la réussite de la tâche en aval](https://github.com/serevy/semantic-decision-lab/issues/74) |
| Transmissions | Quelle est la plus petite transmission typée qui préserve les contraintes, l’incertitude, la provenance des preuves et la prochaine action requise ? | [#3 Transmission typée](https://github.com/serevy/semantic-decision-lab/issues/3) |
| Interprétation de l’état | Peut-on représenter les états décisionnels, les états pragmatiques et les transitions sémantiques sans inventer de certitude ou d’autorisation non étayée ? | [#4](https://github.com/serevy/semantic-decision-lab/issues/4), [#5](https://github.com/serevy/semantic-decision-lab/issues/5), [#9](https://github.com/serevy/semantic-decision-lab/issues/9) |
| Portes de domaine et découverte | Où la classification, la notation, la recherche et le classement sémantiques sont-ils utiles dans des processus métier délimités ? | [#6 Portes de stratégie de trading](https://github.com/serevy/semantic-decision-lab/issues/6), [#7 Découverte de VTubers](https://github.com/serevy/semantic-decision-lab/issues/7), [#8 Découverte des goûts](https://github.com/serevy/semantic-decision-lab/issues/8) |
| Temps réel / incarné | Un état sémantique à faible latence peut-il améliorer l’interaction tout en gardant indépendante la sécurité déterministe impérative malgré les retards, les dérives ou les changements de politique du modèle ? | [#10 Couche de décision temps réel / incarnée](https://github.com/serevy/semantic-decision-lab/issues/10) |
| Portabilité du fournisseur | Un contrat de décision typée peut-il préserver le sens sémantique, l’étalonnage et les capacités observables entre fournisseurs hébergés et locaux, et pas seulement le format de l’API ? | [#81 Portabilité du fournisseur System One](https://github.com/serevy/semantic-decision-lab/issues/81) |

Le dépôt traite les méthodes établies — classification, notation, routage, recherche d’informations, compression, transmission structurée, vérification, analyse des trajectoires et représentations intermédiaires typées — comme des composants réutilisables. L’étude porte sur la capacité des états et transitions sémantiques typés à préserver le comportement en aval lorsque ces éléments sont assemblés en architectures logicielles fiables.

## Neutre vis-à-vis des fournisseurs par conception

Jev est un fournisseur et un point de référence importants dans ce travail, mais ce n’est **pas la définition de la recherche**. Les expériences visent à maintenir, dans la mesure du possible, la logique applicative derrière une frontière commune de décisions typées.

![Architecture décisionnelle sémantique indépendante des fournisseurs](docs/assets/provider-neutral-architecture.svg)

Les comparaisons entre fournisseurs maintiennent séparées les différentes dimensions :

- **compatibilité du contrat** — la même structure de requête/réponse peut-elle être utilisée ?
- **qualité sémantique** — les décisions sont-elles correctes pour la tâche ?
- **étalonnage** — les probabilités correspondent-elles à ce que l’automatisation en aval suppose qu’elles signifient ?
- **robustesse** — ordre des options, longueur du contexte, empaquetage, abstention et comportement en cas d’échec
- **coût des systèmes** — latence, mémoire, matériel, débit et coût des API externes

**La compatibilité des API n’est pas une équivalence sémantique.** Un fournisseur peut être facile à remplacer tout en se comportant suffisamment différemment pour nécessiter des seuils ou des contraintes de déploiement différents.

## Fonctionnement des expériences

Le laboratoire privilégie les preuves. La conception des expériences et les données probantes brutes restent séparées des décisions durables du projet.

![Preuves d’expérimentation et flux de travail PDDR](docs/assets/experiment-evidence-pddr.svg)

Règles communes :

- figez les conditions d’évaluation avant la sortie du fournisseur évalué ;
- préserver les éléments probants de la première exécution plutôt que de les réécrire après la découverte d’échecs ;
- indiquez explicitement les changements de version du protocole, de conditionnement, de jeu de données ou d’invite ;
- comparer aux références déterministes et/ou conventionnelles, le cas échéant ;
- distinguer la couverture de la correction lorsqu’un fournisseur rejette ou tronque les entrées ;
- considérez les affirmations des références comparatives en amont comme des éléments de preuve de l’état de l’art jusqu’à leur reproduction ;
- respectez les conditions du fournisseur avant de publier des résultats de référence propres au fournisseur.

## Résultats et visualisations

Le README n’est volontairement **pas** un classement en temps réel.

Les résultats stables et figés pourront être présentés ici ultérieurement sous forme de petits graphiques ou de figures récapitulatives. Les ventilations détaillées des résultats, la provenance, les diagnostics et les vues interactives doivent figurer dans les artefacts d’expérimentation, `docs/`, ou sur le [site GitHub Pages](https://serevy.github.io/semantic-decision-lab/).

Cela permet de garder la page d’accueil lisible tout en évitant un problème courant : des graphiques attrayants qui survivent silencieusement à la version de l’expérience qui les a produits.

## Structure du dépôt

| Chemin | Objectif |
|---|---|
| `experiments/` | Code d’expériences reproductibles, jeux de données, évaluateurs et ressources axées sur les éléments probants |
| `docs/records/` | Enregistrements de décisions PDDR acceptés |
| `.pddr/` | Outillage, schéma, validation et prise en charge des points de contrôle du PDDR Kit |
| `docs/` | Documentation complémentaire et notes de recherche qui ne figurent pas sur la page d’accueil |
| GitHub Issues | Hypothèses, protocoles, observations intermédiaires, résultats bruts, échecs et suivis |

Pour les implémentations et les articles externes susceptibles d’influencer les futures expériences, consultez [#70 Radar des références externes](https://github.com/serevy/semantic-decision-lab/issues/70).

## Dossiers de recherche

Les détails de l’expérimentation en cours restent dans GitHub Issues. Un PDDR n’est créé que lorsque les éléments probants aboutissent à une décision durable concernant un projet, un produit ou un processus, qui mérite d’être conservée au-delà de l’expérimentation elle-même.

| Artefact | Rôle |
|---|---|
| GitHub Issue | Hypothèse, protocole, observations, éléments probants bruts, échecs et suivis |
| PDDR | Adoption, rejet, report, périmètre, conséquences et conditions de réexamen fondés sur des données probantes |

Ce dépôt utilise la version `v0.3.0` du cœur géré de [PDDR Kit](https://github.com/serevy/pddr-kit/releases/tag/v0.3.0) (mise à jour dans la [PR #145](https://github.com/serevy/semantic-decision-lab/pull/145)) ; les Evidence expérimentales, les enregistrements de décision et les Skills facultatives ne faisaient pas partie de cette migration du cœur. [`PDDR-0001`](docs/records/PDDR-0001-separate-experiments-from-decisions.md) définit la limite entre le travail expérimental et les décisions durables.
