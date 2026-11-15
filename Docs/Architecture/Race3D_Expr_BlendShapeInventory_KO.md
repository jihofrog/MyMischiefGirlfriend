# Race3D v1 표정 통합 — BlendShape 메시별 목록 (2026-11-15)
정식 통합 후 기준. Basis 키는 제외. Unity 채널 = SkinnedMeshRenderer.sharedMesh.blendShapeCount 합.
## 과거 보고서 수치 대응

| 보고서 수치 | 의미 (당시 집계) | 현재 측정과의 관계 |
|---|---|---|
| REPORT_20: Unity 47 | v1 눈·시점 키 중심 (메시 채널 합의 일부 보고) | 현재 백업 v1 Blender 키 합 **71** (Basis 제외). 눈 4메시(Lids/Lash×2)만 보면 **32** |
| REPORT_21: Blender 99 보존 +59 | v2 표정 추가분 (중간 실험 blend 기준) | 현 백업 v1에는 표정 Ex* 없음. 99는 당시 다른 집계(Basis·중복·비스키닝 포함 가능) |
| REPORT_23: Blender 99 유지 +98, Unity FBX **137** | v3b 실험 FBX 스키닝 채널 합 | **현재 정식 FBX/프리팹도 Unity 137** 로 일치 |
| REPORT_24: 137 | 실기기 메모리 로그의 메시 BlendShape 합 | 동일 |

## 요약
| 출처 | 키/채널 합 | 메시 수 |
|---|---|---|
| Blender 백업 v1 (표정 전) | 71 | 28 |
| Blender v3b / 정식 .blend | 161 | 36 |
| Unity 정식 FBX (스키닝 채널) | 137 | 20 |

Blender 161 vs Unity 137 차이: TearStream 등 비스키닝·키 0 메시, 하이라이트/홍채 등 일부 메시가 Unity 스키닝 목록에서 빠지거나 합쳐진 것이 아니라, **스키닝으로 들어온 메시의 키 합이 137**이다. Blender 쪽 161은 스키닝 여부 없이 shape key가 있는 모든 메시 합이다.

## Unity 정식 FBX 메시별 (137 채널)

| 메시 | 개수 | 키 |
|---|---|---|
| `Blockout_Head` | 5 | `EyeSmile`, `Smile`, `ExHappy`, `ExAngry`, `ExAngry2` |
| `Eye_Lash.L` | 16 | `Blink`, `EyeSmile`, `Smile`, `Surprise`, `ViewFarL`, `ViewFarL_GO`, `ViewFarL_GI`, `ViewSideL`, `ExHappyB`, `ExHappyA`, `ExHappyC`, `ExAngry`, `ExAngry2`, `ExSad`, `ExCry`, `ExSurprise` |
| `Eye_Lash.R` | 16 | `Blink`, `EyeSmile`, `Smile`, `Surprise`, `ViewFarR`, `ViewFarR_GO`, `ViewFarR_GI`, `ViewSideR`, `ExHappyB`, `ExHappyA`, `ExHappyC`, `ExAngry`, `ExAngry2`, `ExSad`, `ExCry`, `ExSurprise` |
| `Eye_Lids.L` | 16 | `Blink`, `EyeSmile`, `Smile`, `Surprise`, `ViewFarL`, `ViewFarL_GO`, `ViewFarL_GI`, `ViewSideL`, `ExHappyB`, `ExHappyA`, `ExHappyC`, `ExAngry`, `ExAngry2`, `ExSad`, `ExCry`, `ExSurprise` |
| `Eye_Lids.R` | 16 | `Blink`, `EyeSmile`, `Smile`, `Surprise`, `ViewFarR`, `ViewFarR_GO`, `ViewFarR_GI`, `ViewSideR`, `ExHappyB`, `ExHappyA`, `ExHappyC`, `ExAngry`, `ExAngry2`, `ExSad`, `ExCry`, `ExSurprise` |
| `Face_Blush.L` | 6 | `ExHappy`, `ExAngry`, `ExAngry2`, `ExSad`, `ExCry`, `ExSurprise` |
| `Face_Blush.R` | 6 | `ExHappy`, `ExAngry`, `ExAngry2`, `ExSad`, `ExCry`, `ExSurprise` |
| `Face_Brow.L` | 10 | `Blink`, `EyeSmile`, `Smile`, `Surprise`, `ExHappy`, `ExAngry`, `ExAngry2`, `ExSad`, `ExCry`, `ExSurprise` |
| `Face_Brow.R` | 10 | `Blink`, `EyeSmile`, `Smile`, `Surprise`, `ExHappy`, `ExAngry`, `ExAngry2`, `ExSad`, `ExCry`, `ExSurprise` |
| `Face_BrowCard.L` | 10 | `Blink`, `EyeSmile`, `Smile`, `Surprise`, `ExHappy`, `ExAngry`, `ExAngry2`, `ExSad`, `ExCry`, `ExSurprise` |
| `Face_BrowCard.R` | 10 | `Blink`, `EyeSmile`, `Smile`, `Surprise`, `ExHappy`, `ExAngry`, `ExAngry2`, `ExSad`, `ExCry`, `ExSurprise` |
| `Face_Mouth_ExO` | 1 | `ExSurprise` |
| `Face_Mouth_ExSmile` | 1 | `ExHappy` |
| `Face_Mouth_Smile_Inside` | 1 | `MouthOpen` |
| `Face_Mouth_Smile_Line` | 1 | `MouthOpen` |
| `Face_Mouth_Smile_Teeth` | 1 | `MouthOpen` |
| `Face_Mouth_Smile_Tongue` | 1 | `MouthOpen` |
| `Face_Tear.L` | 2 | `ExSad`, `ExCry` |
| `Face_Tear.R` | 2 | `ExSad`, `ExCry` |
| `TT_Mouth_Closed` | 6 | `Smile`, `ExHappy`, `ExAngry`, `ExSad`, `ExCry`, `ExSurprise` |

## Blender 정식(v3b) — Unity에 없는 키 보유 메시

- `Eye_Highlight.L`: 2 — Blink, Smile
- `Eye_Highlight.R`: 2 — Blink, Smile
- `Eye_Iris.L`: 2 — Blink, Smile
- `Eye_Iris.R`: 2 — Blink, Smile
- `Eye_OuterLine.L`: 1 — Blink
- `Eye_OuterLine.R`: 1 — Blink
- `Eye_Pupil.L`: 2 — Blink, Smile
- `Eye_Pupil.R`: 2 — Blink, Smile
- `Eye_UpperLashes.L`: 1 — Blink
- `Eye_UpperLashes.R`: 1 — Blink
- `Eye_UpperLid.L`: 1 — Blink
- `Eye_UpperLid.R`: 1 — Blink
- `Eye_White.L`: 2 — Blink, Smile
- `Eye_White.R`: 2 — Blink, Smile
- `Face_UpperLashes.L`: 1 — Blink
- `Face_UpperLashes.R`: 1 — Blink

## 혼합 규칙 (정식)

- Happy: 0..0.6 A, 0.6..0.85 A→C, 0.85..1.0 C→B (`ExHappyA/C/B`).
- **Angry2가 Angry를 억제:** `angryStrong=angry2`, `angryWeak=angry×(1−angry2)`. 동일 메시 이중 변형 방지.
- Cry가 Sad 얼굴 키를 대체: `ExSad = sad×(1−cry)`.
- 눈 감정 키는 `(1−Blink)` 스케일. 시점 키는 EyeViewController가 `(1−Blink)(1−EyeSmile)(1−Happy)`.
- Cry `_Flow` API 유지. 뺨 곡선 메쉬는 추후 애니메이션 단계.
