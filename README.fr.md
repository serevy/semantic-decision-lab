# semantic-decision-lab

[English](README.md) | [日本語](README.ja.md) | [简体中文](README.zh-CN.md) | [한국어](README.ko.md) | **Français**

Expériences sur les couches de décision sémantique pour l’orchestration de l’IA, la sélection du contexte, le routage, les transferts et les systèmes en temps réel.

## Modèle de fonctionnement

Ce dépôt sépare le travail expérimental des décisions de projet destinées à être conservées durablement.

| Artefact | Objectif | Contenu typique |
|---|---|---|
| GitHub Issue | Backlog d’expériences et fil de travail | Hypothèse, configuration, tâches, observations intermédiaires, résultats bruts, suivi |
| PDDR | Enregistrement durable d’une décision importante | Adoption, rejet, report, périmètre, conséquences et conditions de réexamen étayés par des éléments probants |

L’exécution ou l’achèvement d’une expérience ne crée pas automatiquement de PDDR. Créez ou mettez à jour un PDDR uniquement lorsque les éléments probants conduisent à une décision importante de type Project, Product ou Process, dont la justification doit rester disponible au-delà du cycle de vie de l’Issue.

Lorsqu’une décision est prise, l’Issue et le PDDR doivent se référencer mutuellement, tandis que les détails expérimentaux bruts restent dans l’Issue.

## PDDR

Ce dépôt utilise [PDDR Kit](https://github.com/serevy/pddr-kit) `v0.2.1`.

Il utilise également le hardened optional checkpoint CI. Le signal workflow qui observe le PR head est en lecture seule, tandis que les écritures de marker sont effectuées par un trusted default-branch writer. Un checkpoint signal demande une bounded review ; il n’impose pas la création d’un PDDR et ne transforme pas automatiquement la fin d’une expérience routinière en PDDR.

Créez un enregistrement à partir de `.pddr/template.md`, enregistrez-le dans `docs/records/`, puis validez-le avant la revue :

```bash
cp .pddr/template.md docs/records/PDDR-0002-short-title.md
python .pddr/pddr.py validate
```

Le premier enregistrement, [`PDDR-0001`](docs/records/PDDR-0001-separate-experiments-from-decisions.md), définit la frontière entre les Issues et les enregistrements de décision.
