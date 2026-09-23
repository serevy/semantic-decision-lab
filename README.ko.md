# semantic-decision-lab

[English](README.md) | [日本語](README.ja.md) | [简体中文](README.zh-CN.md) | **한국어** | [Français](README.fr.md)

AI 오케스트레이션, 컨텍스트 선택, 라우팅, 핸드오프, 실시간 시스템을 위한 시맨틱 의사결정 레이어 실험.

## 운영 모델

이 저장소에서는 실험 작업과 장기적으로 보존해야 할 프로젝트 의사결정을 분리합니다.

| 산출물 | 목적 | 주요 내용 |
|---|---|---|
| GitHub Issue | 실험 백로그 및 작업 스레드 | 가설, 설정, 작업, 중간 관찰, 가공하지 않은 결과, 후속 조치 |
| PDDR | 중요한 의사결정을 장기 보존하는 기록 | 근거에 따른 채택, 거부, 보류, 범위, 영향, 재검토 조건 |

실험을 실행하거나 완료했다는 이유만으로 PDDR이 자동 생성되지는 않습니다. 실험의 근거를 바탕으로, 그 이유를 Issue 수명 주기를 넘어 보존해야 하는 중요한 Project, Product 또는 Process 의사결정에 도달한 경우에만 PDDR을 생성하거나 업데이트합니다.

의사결정을 내린 경우 Issue와 PDDR을 서로 연결하고, 가공하지 않은 실험 세부 정보는 Issue에 남깁니다.

## PDDR

이 저장소에서는 [PDDR Kit](https://github.com/serevy/pddr-kit) `v0.2.1`을 사용합니다.

또한 hardened optional checkpoint CI를 도입했습니다. PR head를 관찰하는 signal workflow는 read-only이며, marker 쓰기는 trusted default-branch writer가 담당합니다. checkpoint signal은 bounded review를 요청하는 신호일 뿐 PDDR 생성을 의무화하지 않으며, routine 실험 완료를 자동으로 PDDR로 승격하지 않습니다.

`.pddr/template.md`을 바탕으로 기록을 만들고, `docs/records/` 아래에 저장한 뒤 검토 전에 검증합니다.

```bash
cp .pddr/template.md docs/records/PDDR-0002-short-title.md
python .pddr/pddr.py validate
```

첫 번째 기록인 [`PDDR-0001`](docs/records/PDDR-0001-separate-experiments-from-decisions.md)은 Issue와 의사결정 기록의 경계를 정의합니다.
