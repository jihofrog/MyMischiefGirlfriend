# Race3D 표정 v3b — 설계 메모 (실험, 2026-11-15)

정식 통합 전 실험 결정만 적는다. 00 문서 8장 미정은 여기서 확정하지 않는다.

## 1. Angry / Angry2

| 키 | 역할 | 사용 |
|---|---|---|
| `ExAngry` / emotion `angry` | 약한 화남·불만 | 독립 입력 |
| `ExAngry2` / emotion `angry2` | **강한 화남의 기본** | 독립 입력 |

둘을 동시에 켜도 혼합 규칙(`expr_mix_v3b`)이 각각 `(1−Blink)` 로 눈 키에 넣고, 입선·볼은 합산한다. 한쪽만 써도 된다.

## 2. 눈썹 Pull 거리 (헤어스타일별)

- Blender 검증 기본값: bob 앞머리 → **0.03 m**.
- **고정 전역 상수로 확정하지 않는다.**
- 계약 (실험):
  - 드라이버는 `HairBrowPullTable.Resolve(hairItemId)` → `_Pull` (카드 재질 인스턴스).
  - 표에 없으면 `defaultPullMeters`(bob 0.03).
  - 캐릭터마다 인스턴스 재질이라 다른 헤어를 쓴 캐릭터가 서로 `_Pull` 을 덮어쓰지 않는다.
- 정식 원본 위치(Unity 헤어 외형 필드 vs Admin)는 미정. 통합 때 외형 데이터에 필드를 둘지 결정한다.

## 3. Cry 눈물 줄기 — 현재 유지, 곡선 확장 여지

- 현재: 정적 메시 `Face_TearStream`, UV `u`=가로, `v`=눈→볼(0..1), 재질 `_Flow`=드러나는 길이.
- **지금 구조·API는 유지**한다 (실기기 검증 대상).
- 최종 애니메이션 단계에서 뺨을 따라 휘는 곡선으로 바꿀 때:
  - 메시 경로만 곡선 샘플로 다시 만들거나 BlendShape로 경로를 추가한다.
  - `_Flow`·UV 계약은 그대로 둔다 (`v` = 경로 진행).
  - Blender `race3d_v3b_expr_build.py` 의 stream 생성 루프가 경로 샘플의 원본이다.

## 4. 재질 공유 금지

- 눈알(`_Sparkle`, `_Proj`, `_GazeYaw`), 눈썹 카드(`_Pull`, `_Reveal`), 눈물(`_Flow`)은 **캐릭터마다 Material 인스턴스**.
- 에셋 `sharedMaterial` 을 직접 쓰지 않는다. 12명 동시 표정이 서로 영향을 주면 안 된다.

## 5. 통합 상태

- 사용자 결정(2026-11-15): v3b 정식 통합 **승인**.
- 실기기 후보 검증: REPORT_24. 정식 통합 보고: REPORT_25.
- 정식 경로: `MainGirlfriend_Race3D_v1` (.blend / FBX / prefab) + `ExpressionController` + `EyeViewController.viewSuppress` + `HairBrowPullTable` (Unity 외형, Admin 비연동).
- 백업: `Models/_backup_v1_20261115_pre_expr/`, `Model3D/_backup_v1_20261115_pre_expr/`, `Models/MainGirlfriend_Race3D_v1_pre_expr_20261115.blend`.
- 실험 `Assets/_Experiments/Race3D_v3b/` 및 v3b .blend 는 보존.
- BlendShape 목록: `Docs/Architecture/Race3D_Expr_BlendShapeInventory_KO.md`.
- Cry 뺨 곡선·몸체 정교화·리깅·의상·애니는 **이후 단계**. 얼굴·눈·표정은 현 베이스라인.

## 6. 충돌 표정 혼합 (정식)

| 입력 | 규칙 |
|---|---|
| Angry + Angry2 | `angryStrong=angry2`, `angryWeak=angry×(1−angry2)` — 강한 쪽이 약한 쪽을 억제 |
| Sad + Cry | 얼굴 `ExSad=sad×(1−cry)` |
| Happy A/C/B | 구간이 서로 배타 (합 ≤ 1) |
| 입선 ExAngry | `max(angryWeak, angryStrong)` (가산 금지) |
