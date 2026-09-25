#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from sentence_transformers import SentenceTransformer

ROOT=Path(__file__).resolve().parent
CASES=ROOT/"downstream-cases.v0.4.json"
SNAPSHOTS=ROOT/"downstream-snapshots.v0.4.json"
FIXTURES=ROOT/"downstream-counterfactual-fixtures.v0.3.json"
CONTRACT=ROOT/"downstream-retrieval-contract.v0.4.json"

STOP={
    "a","an","and","are","as","at","be","by","for","from","in","into","is","it",
    "of","on","or","that","the","their","this","to","using","we","which","with",
    "without","wants","need","needs","new","prior","decision","context","project",
    "which","did","adopt","adopted"
}

def tokens(text:str)->set[str]:
    return {t for t in re.findall(r"[a-z0-9]+",text.lower()) if len(t)>=3 and t not in STOP}

def render_query(case:dict)->str:
    return case["scenario"]+"\n\n"+case["question"]

def render_passage(card:dict)->str:
    return f"Status: {card['status']}\nDecision: {card['decision']}\nRationale: {card['rationale']}"

def sha256_json(value)->str:
    raw=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
    return hashlib.sha256(raw).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()

    cases=json.loads(CASES.read_text())
    snapshots=json.loads(SNAPSHOTS.read_text())["snapshots"]
    fixtures=json.loads(FIXTURES.read_text())
    contract=json.loads(CONTRACT.read_text())

    cards={}
    for pair in fixtures["pairs"]:
        for card in pair["cards"]:
            cards[card["card_id"]]=card

    selectors=contract["selectors"]
    model_name=selectors["embedding_top1"]["model"]
    revision=selectors["embedding_top1"]["model_revision"]
    model=SentenceTransformer(model_name,revision=revision)

    snapshot_embedding={}
    for snapshot_id,card_ids in snapshots.items():
        passages=[
            selectors["embedding_top1"]["passage_prefix"]+render_passage(cards[cid])
            for cid in card_ids
        ]
        embs=model.encode(passages,normalize_embeddings=True,convert_to_numpy=True,show_progress_bar=False)
        snapshot_embedding[snapshot_id]=(card_ids,embs)

    out={
        "schema_version":1,
        "version":"v0.4",
        "contract_sha256":sha256_json(contract),
        "embedding":{
            "model":model_name,
            "model_revision":revision,
            "sentence_transformers":selectors["embedding_top1"]["sentence_transformers"]
        },
        "selectors":{}
    }

    for selector_name in ["keyword_top1","keyword_top2","embedding_top1","embedding_top2"]:
        top_k=selectors[selector_name]["top_k"]
        selections={}
        scores={}
        required_hits=0

        for case in cases:
            snapshot_id=case["snapshot_id"]
            card_ids=snapshots[snapshot_id]
            query=render_query(case)
            ranked=[]

            if selector_name.startswith("keyword"):
                q=tokens(query)
                for cid in card_ids:
                    overlap=sorted(q & tokens(render_passage(cards[cid])))
                    ranked.append({
                        "card_id":cid,
                        "score":len(overlap),
                        "overlap":overlap
                    })
                ranked.sort(key=lambda row:(-row["score"],row["card_id"]))
                selected=[row["card_id"] for row in ranked[:top_k] if row["score"]>0]
            else:
                ids,embs=snapshot_embedding[snapshot_id]
                qemb=model.encode(
                    [selectors[selector_name]["query_prefix"]+query],
                    normalize_embeddings=True,
                    convert_to_numpy=True,
                    show_progress_bar=False
                )[0]
                for idx,cid in enumerate(ids):
                    ranked.append({
                        "card_id":cid,
                        "score":float(qemb @ embs[idx])
                    })
                ranked.sort(key=lambda row:(-row["score"],row["card_id"]))
                selected=[row["card_id"] for row in ranked[:top_k]]

            required=case["gold"]["required_card"]
            hit=required in selected
            required_hits+=int(hit)
            selections[case["case_id"]]=selected
            scores[case["case_id"]]={
                "snapshot_id":snapshot_id,
                "required_card":required,
                "required_hit":hit,
                "ranking":ranked
            }

        out["selectors"][selector_name]={
            "top_k":top_k,
            "required_hits":required_hits,
            "required_hit_rate":required_hits/len(cases),
            "selections":selections,
            "scores":scores
        }

    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(f"wrote {args.output}")
    for name,s in out["selectors"].items():
        print(f"{name}: required hit {s['required_hits']}/{len(cases)}")

if __name__=="__main__":
    main()
