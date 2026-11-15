# REPORT 25 — Race3D v3b 표정 정식 통합 (2026-11-15)

## 결론

- **v3b 표정을 `MainGirlfriend_Race3D_v1`에 정식 통합했다.** 표정 전 v1은 백업으로 보존했고, 실험 `Race3D_v3b` 파일도 그대로 두었다.
- Unity: `ExpressionController` + `EyeViewController.viewSuppress(Happy)` + `HairBrowPullTable`(Unity 외형, Admin 비연동).
- Editor 검증·Galaxy S24 정식 프리팹 실행·**12명 13분 연속(soak)** 측정까지 완료. 짧은 12초 측정과 구분해서 기록했다.
- **얼굴·눈·표정은 현 단계 베이스라인으로 확정.** 다음은 몸체 정교화·리깅·의상·애니메이션. 얼굴 재설계는 하지 않는다.
- 커밋은 하지 않았다 (별도 승인 대기).

## 1. 백업 경로

| 대상 | 경로 | md5 (통합 직전) |
|---|---|---|
| Blender v1 | `Models/_backup_v1_20261115_pre_expr/MainGirlfriend_Race3D_v1.blend` | e782f9f0… |
| Blender 사이드카 | `Models/MainGirlfriend_Race3D_v1_pre_expr_20261115.blend` | 동일 |
| Unity FBX·프리팹·Materials·Textures | `Assets/_Game/Art/Characters/MainGirlfriend/Model3D/_backup_v1_20261115_pre_expr/` | fbx 1d7263e7… / prefab 2ba1a33e… |
| Mobile_RPAsset | 빌드 전후 동일 | 0cf0b513… (변경 없음) |

실험 보존: `Models/Race3D/experiments/MainGirlfriend_Race3D_v3b_Expressions.blend`, `Assets/_Experiments/Race3D_v3b/` 전부.

## 2. 변경·추가 파일

### Blender / 데이터
- `Models/MainGirlfriend_Race3D_v1.blend` ← v3b 표정 내용으로 갱신 (백업 후)
- `Model3D/MainGirlfriend_Race3D_v1.fbx` / `.prefab` 재생성
- `Model3D/HairBrowPullTable_bob.asset` (bob 0.030 m)
- `Model3D/Textures/T_MainGirlfriend_EyeSparkle_{L,R}.png`
- `Model3D/Materials/` 표정·스파클·스텐실·BrowCard·TearStream 재질
- `Model3D/Spec/blendshape_inventory_unity.txt`, `editor_verify_log.txt`
- `Race3D/spec/race3d_v1_expr_unity_proj.json`

### Unity 코드·셰이더
- `Assets/_Game/Scripts/Characters/Avatar3D/ExpressionController.cs` (신규)
- `Assets/_Game/Scripts/Characters/Avatar3D/HairBrowPullTable.cs` (신규)
- `EyeViewController.cs` — `viewSuppress` 추가, 시점 키 `(1−Blink)(1−EyeSmile)(1−viewSuppress)`
- 셰이더 신규: `MMG/Character/{EyeBallSparkle,ToonHairStencil,BrowCard,TearStream}`
- 검증용(실험): `Assets/_Experiments/Race3D_FormalVerify/`

### 문서
- `Docs/Architecture/Race3D_Expr_BlendShapeInventory_KO.md`
- `Docs/Architecture/Race3D_Expr_v3b_DesignNotes_KO.md` / `00_Architecture.md` 갱신
- 본 보고서 REPORT_25

### 건드리지 않음
- Live2D, Localization, Cubism, Admin DB, 다른 캐릭터, `Mobile_RPAsset` MSAA/RS
- `Assets/_Experiments/Race3D_v3b/` 원본

## 3. BlendShape 대응 (99 / +59 / 137)

상세: `Docs/Architecture/Race3D_Expr_BlendShapeInventory_KO.md`

| 집계 | 값 | 설명 |
|---|---|---|
| 백업 v1 Blender (표정 전) | **71** 키 / 28 메시 | Basis 제외. 과거 “99”와 집계 단위가 다름 |
| 정식/v3b Blender | **161** 키 / 36 메시 | TearStream 등 키 0 메시 포함 가능 |
| **Unity 정식 FBX** | **137** 채널 / 20 스키닝 메시 | REPORT_23·24와 **동일**. 프리팹 검증 일치 |
| 과거 REPORT_21 “99+59” | 중간 실험 blend 기준 서술 | 현 백업 v1·정식 137과 1:1 숫자 동일은 아님. **운영 기준은 Unity 137** |

눈 Lids/Lash 4메시: 각 16키 (기존 8 + ExHappyA/B/C, ExAngry, ExAngry2, ExSad, ExCry, ExSurprise).

## 4. 혼합 규칙 (정식)

- **Angry2 ≫ Angry:** `angryWeak = angry × (1 − angry2)`. 동시 1.0이어도 약한 키는 0.
- Sad ≪ Cry: `ExSad = sad × (1 − cry)`
- Happy A→C→B (0.6 / 0.85 경계) 보존
- 시점: EyeView만 View*·Blink·EyeSmile·Smile·Surprise(레거시) 기록. Expression은 Ex*·재질·`viewSuppress=Happy`
- Cry `_Flow` 유지. **뺨 곡선 흐름 = 추후 애니메이션 단계 작업 항목**

## 5. Editor 검증

`Spec/editor_verify_log.txt`:

- CONFLICT Angry+Angry2 → weak=0 / strong=1 → ok
- ISOLATION ok (스파클·Flow·Pull·재질 인스턴스)
- Happy 0.8 → viewSuppress=0.8
- blendshape_channels=137
- Blink=1 때 ExSurprise=0

## 6. Galaxy S24 정식 프리팹 검증

| 항목 | 값 |
|---|---|
| 패키지 | `com.mmg.formalexprtest` (임시) |
| 씬 | `Assets/_Experiments/Race3D_FormalVerify/FormalExprAndroidTest.unity` |
| 프리팹 | 정식 `MainGirlfriend_Race3D_v1.prefab` |
| 캡처 | 33장 (`experiments/android_formal/screens/`) |
| 격리 | ok=True |
| Mobile_RPAsset | 빌드 후 md5 복원·일치 |

### 6.1 짧은 성능 (12초, REPORT_24와 동일 계열)

설정 C: MSAA 4×, RS 0.8

| 조건 | FPS | frame avg/P95 | CPU main avg/P95 | GPU avg/P95 | expr | alloc |
|---|---|---|---|---|---|---|
| 1명 | 120.0 | 8.33 / 8.75 | 3.21 / 3.86 | 2.90 / 3.07 | 77 µs | 74.5 MB |
| 12명 | 119.9 | 8.34 / 8.76 | 4.53 / 5.76 | 6.48 / 7.25 | 376 µs | 77.2 MB |

### 6.2 12명 연속 soak (**13분 = 780초**, 짧은 측정과 구분)

| 항목 | 값 |
|---|---|
| 프레임 | 93,524 |
| FPS | **119.9** |
| frame avg / P95 | 8.34 / 8.70 ms |
| CPU main avg / P95 | 4.53 / 5.66 ms |
| GPU avg / P95 | 6.77 / 7.36 ms |
| expr avg | 369 µs |
| alloc | 77.0 → **77.8 MB** (누수 징후 없음) |
| 16.7 ms 초과 | 8 프레임 / 93,524 (~0.009 %) |

**발열 (호스트 15초 샘플, 825초):**

| | min | max | avg | 종료 |
|---|---|---|---|---|
| Thermal Status | 0 | **3** | 2.2 | 3 |
| AP °C | 41.9 | 52.8 | 49.7 | 52.7 |
| Skin °C | 35.8 | 43.7 | 41.4 | 43.7 |
| Battery % | 55 | 58 | 57 | 58 (충전) |

- Development 빌드·120 Hz 고정·13분 연속이라 Thermal Status 3까지 오른 것은 기록한다. **FPS·프레임 예산은 유지**됐다. Release/실플레이 부하와는 다를 수 있다.

## 7. 베이스라인 (이후 개발)

확정:
- 얼굴 비율, 홍채·눈 구조, bob 헤어 형상, 3/4 시점 보정, Happy/Angry/Angry2/Sad/Cry/Surprise, Blink, 시선 ±0.25 rad, Pull 표

이후 단계 (얼굴 재설계 금지):
1. 몸체 모델링 정교화
2. 공통 리깅
3. 의상 장착 시스템
4. 레이스 애니메이션
5. Cry 눈물 **뺨 곡선** 메시 (API `_Flow`/UV v 유지)

리깅·애니 중 발견된 얼굴 문제만 별도 수정 티켓으로 다룬다.

## 8. 남은 문제 / 참고

- Soak 중 Thermal Status 3 (Development·장시간). 실기기 튜닝 시 Release 빌드로 재확인 권장.
- Cry 줄기는 아직 직선에 가깝다 → 애니 단계 개선 항목.
- 과거 문서의 “99 / +59” 숫자는 중간 실험 집계. **현재 운영 기준은 Unity 137 채널.**
- 커밋·푸시 없음.

## 9. 질문 (필요 시)

없음. 통합·검증 완료. 커밋을 원하시면 승인해 주세요.
