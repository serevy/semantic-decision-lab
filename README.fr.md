# semantic-decision-lab

[English](README.md) | [日本語](README.ja.md) | [简体中文](README.zh-CN.md) | [한국어](README.ko.md) | **Français**

> **Expériences indépendantes des fournisseurs sur les couches de décision sémantique :** transformer un état ambigu en décisions typées et probabilistes que les systèmes déterministes peuvent exploiter.

La question fondamentale n’est pas « un LLM peut-il tout faire ? », mais plutôt :

> **Le jugement sémantique peut-il être isolé sous forme de petit composant logiciel testable, tandis que du code déterministe conserve le contrôle de l’exécution, des politiques et de la sécurité ?**

Ce dépôt explore cette question à travers l’orchestration, la sélection du contexte, les transmissions typées, l’interprétation de l’état, les contrôles de domaine, les systèmes en temps réel et les fournisseurs interchangeables de décisions sémantiques.

## Idée centrale

Une couche sémantique doit répondre à **ce que signifie l’état actuel**. Les systèmes déterministes restent responsables de **ce qui se passe ensuite**.

![Architecture du cœur décisionnel sémantique](docs/assets/semantic-decision-core.svg)

Cette séparation nous permet de tester le jugement sémantique indépendamment de la logique d’exécution. Elle rend également explicites l’incertitude, l’abstention, l’escalade et le remplacement du fournisseur, au lieu de les dissimuler dans un agent monolithique.

## Carte de recherche

| Domaine | Question de recherche | Principaux fils conducteurs |
|---|---|---|
| Orchestration | Le routage sémantique peut-il réduire les coûts ou la latence sans dégrader les résultats obtenus ? | [#1 AI Work Routing](https://github.com/serevy/semantic-decision-lab/issues/1) |
| Contexte et mémoire | Pouvons-nous sélectionner un contexte plus restreint tout en préservant les informations essentielles à la prise de décision ? | [#2 Sélection du contexte PDDR](https://github.com/serevy/semantic-decision-lab/issues/2), [#74 évaluation de la réussite de la tâche en aval](https://github.com/serevy/semantic-decision-lab/issues/74) |
| Transmissions | L’état libre d’un agent peut-il devenir une transmission typée et compacte sans perdre de contraintes importantes&nbsp;? | [#3 Transmission typée](https://github.com/serevy/semantic-decision-lab/issues/3) |
| Interprétation de l’état | Pouvons-nous représenter l’état décisionnel, l’état pragmatique et les trajectoires sémantiques sans inventer de certitude non étayée ? | [#4](https://github.com/serevy/semantic-decision-lab/issues/4), [#5](https://github.com/serevy/semantic-decision-lab/issues/5), [#9](https://github.com/serevy/semantic-decision-lab/issues/9) |
| Portes de domaine et découverte | Où la classification sémantique, la notation, la récupération et le classement sont-ils utiles dans les flux de travail de domaines délimités ? | [#6 Portes de stratégie de trading](https://github.com/serevy/semantic-decision-lab/issues/6), [#7 Découverte de VTubers](https://github.com/serevy/semantic-decision-lab/issues/7), [#8 Découverte des goûts](https://github.com/serevy/semantic-decision-lab/issues/8) |
| Temps réel / incarné | Des décisions sémantiques à faible latence peuvent-elles améliorer les systèmes interactifs tout en maintenant la sécurité matérielle indépendante ? | [#10 Couche de décision temps réel / incarnée](https://github.com/serevy/semantic-decision-lab/issues/10) |
| Portabilité du fournisseur | La même application de décisions typées peut-elle passer d’un fournisseur hébergé à un fournisseur local, et inversement, sans transmettre en aval des hypothèses spécifiques au fournisseur&nbsp;? | [#81 Portabilité du fournisseur System One](https://github.com/serevy/semantic-decision-lab/issues/81) |

Le dépôt considère des formes de tâches établies telles que la classification, la notation, le routage, la recherche d’informations et la vérification comme des éléments constitutifs. L’axe de recherche porte sur la manière dont ces primitives se composent en architectures logicielles fiables et sur leur comportement dans des conditions d’évaluation réelles.

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

Les résultats stables et figés pourront être présentés ici ultérieurement sous forme de petits graphiques ou de figures récapitulatives. Les ventilations détaillées des résultats, la provenance, les diagnostics et les vues interactives doivent figurer dans les artefacts d’expérimentation, `docs/`, ou sur un futur site GitHub Pages.

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

Ce dépôt utilise [PDDR Kit](https://github.com/serevy/pddr-kit) `v0.2.1`. [`PDDR-0001`](docs/records/PDDR-0001-separate-experiments-from-decisions.md) définit la limite entre le travail expérimental et les enregistrements de décisions durables.
