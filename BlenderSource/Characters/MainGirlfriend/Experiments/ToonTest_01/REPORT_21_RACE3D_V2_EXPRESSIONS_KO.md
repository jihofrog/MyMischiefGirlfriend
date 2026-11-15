# REPORT 21 — Race3D v2 표정 시제품 (2026-11-13)

## 결론

- 실험 파일 `Models/Race3D/experiments/MainGirlfriend_Race3D_v2_Expressions.blend` 에서 다섯 가지를 시제품으로 만들었다.
  - 새 EyeSmile(Happy)
  - Angry
  - Sad + Cry
  - Surprise
  - 강도 0~1 조합 규칙
- 기존 셰이프 키 99개는 하나도 바뀌지 않았다 (해시 비교). 새 셰이프 키 59개와 새 오브젝트 6개만 추가했다 (새 오브젝트의 Basis 8개 제외).
  - 기존 키에는 v6j 눈 구조, BlendShape 47개, 각도 보정 키가 포함된다.
- `MainGirlfriend_Race3D_v1.blend` 와 Unity 정식 FBX·프리팹은 수정하지 않았다. 정식 통합과 최종 확정은 하지 않았다.
- 감은 웃음과 각 감정에 Blink 를 더한 상태는 정면·±35°·±45° 모두에서 안구가 보이지 않는다 (0 화소).
- 간섭 검사: 표정 프리셋, 감정 간 전환, Blink·시선·시점 보정을 조합한 3,600 상태를 검사했다. 새 표정 때문에 생긴 간섭은 다음과 같다.
  - 눈꺼풀이 안구 0.1 mm 안으로 들어간 점: 0
  - 속눈썹이 눈꺼풀 0.3 mm 안으로 들어간 점: 8개 (모두 0.19 mm 이상 앞에 있어 묻히지 않음)
- 먼 눈 1 px 세로 점선은 원인을 확인했다. 국소 후보 3개 중 B안은 ±35° 에서 약 50 % 줄지만 ±45° 에서는 줄지 않는다.

## 1. 보존

| 항목 | 상태 |
|---|---|
| `Models/MainGirlfriend_Race3D_v1.blend` | 해시 동일 (e782f9f0…) |
| Unity `Model3D/MainGirlfriend_Race3D_v1.fbx` / `.prefab` | 이번 작업에서 수정하지 않음 (Unity 작업 없음) |
| 기존 셰이프 키 99개 (v6j 눈 47개 포함) | v2 파일 안에서도 변경 0 |
| 정면 r30 눈매 | Neutral 은 v1 과 같다 (새 키는 모두 0) |

## 2. EyeSmile 재설계 → 새 Happy

**현재 EyeSmile 의 문제:**
- 아래 눈꺼풀이 거의 직선으로 올라와 눈 아래를 자른다.
- 위 눈꺼풀은 10 % 만 내려온다.

**새 방식:**
- 기본 원리: 눈 모양 하나는 "열마다 Blink 를 다른 양만큼" 움직인 것이다.
  - 눈꺼풀은 안구 표면 좌표에서 Basis 와 Blink 사이를 보간한다.
  - 그래서 안구를 따라 미끄러지고, Blink 에서 검증한 간격과 속눈썹 따라가기를 그대로 물려받는다.
- 두 단계로 나눴다 (Unity 에서 키 2개를 조합한다):
  - **ExHappyA (0~0.6):** 초승달 단계. 위 눈꺼풀은 조금 내려온다. 아래 눈꺼풀 가장자리는 두 눈꼬리를 잇는 선에서 가운데가 솟은 아치(∩)다.
    - 열린 U자 가장자리와 감은 선을 단순히 섞으면 직선이 되어 지금 EyeSmile 처럼 잘린다. 그래서 아치를 따로 정의했다.
  - **ExHappyB (0.6~1):** 감은 웃음. 감긴 선이 가운데가 눈 높이의 15 % 솟은 매끈한 아치다.
- 눈꼬리:
  - 바깥 끝은 3 px(약 1.6 mm) 올린다.
  - 눈꼬리 바깥의 속눈썹 띠는 Blink 보다 45 % 덜 내려간다. 그래서 끝이 처지지 않는다.
- 볼: 머리 메시가 눈 밑에서 1.3 mm 올라온다. 볼 터치는 1.1배로 커지고 볼을 따라간다.

![현재 EyeSmile 대 새 Happy](/Users/jjeong/UnityProjects/MyMischiefGirlfriend/BlenderSource/Characters/MainGirlfriend/Models/Race3D/experiments/sheets/compare_eyesmile.png)

| 강도 | 모습 |
|---|---|
| 0.3 | 눈이 살짝 가늘어진다. 입은 닫힌 미소 선 |
| 0.6 | 위·아래가 함께 휜 초승달 눈웃음. 작은 D자 웃는 입 |
| 1.0 | 감은 ∩ 아치 눈 (^ ^). 눈꼬리가 살짝 올라간다. 활짝 웃는 입 |

![Happy 얼굴](/Users/jjeong/UnityProjects/MyMischiefGirlfriend/BlenderSource/Characters/MainGirlfriend/Models/Race3D/experiments/sheets/happy_face.png)

## 3. 감정 4종

참고 이미지 4장에서는 특징만 가져왔다. 얼굴 비율, 눈 크기, 홍채 디자인은 r30 그대로다. 가져온 특징은 다음과 같다.
- 감은 ∩ 눈과 벌린 입
- 안쪽이 내려간 눈썹과 뾰로통한 입
- 안쪽이 올라간 눈썹과 고인 눈물
- 올라간 눈썹과 작은 o 입

| 감정 | 눈 | 눈썹 | 입 | 볼 |
|---|---|---|---|---|
| Happy | 위 2단계 | 0.6~1.8 mm 올라감 | 닫힌 미소 → D자 웃는 입이 커짐 | 볼 올라감, 볼 터치 ×1.1 |
| Angry | 위 눈꺼풀 안쪽이 내려감 (안쪽 Blink 42 %, 바깥 8 %), 아래 눈꺼풀 20 % 올라감 | 안쪽 끝 5.5 mm 내려가고 1.5 mm 안으로 모임, 바깥 1.2 mm 올라감, 안쪽 1.8배 굵어짐 | へ 모양 | 볼 1.8 mm 부풀림, 볼 터치 ×1.4 |
| Sad | 바깥 위 눈꺼풀이 처짐 (32 %), 안쪽은 살짝 올라감, 아래 눈꺼풀 14 % | 안쪽 끝 5 mm 올라감, 바깥 1.5 mm 내려감 | 작은 ︵ | 볼 터치 ×1.15 |
| Cry (Sad 와 별도 강도) | 아래 눈꺼풀 38 % 올라감, 위 12 % | 안쪽 1.2 mm 더 올라감 | 물결 모양 울먹이는 입 | 눈물 고임 (아래 참고) |
| Surprise | v1 Surprise 눈 키 그대로 | 4.2 mm + 아치 올라감 | 일자 입이 0.4 에서 사라지고 o 입이 커짐 | 볼 터치 ×0.92 |

- Surprise 에서 위 눈꺼풀을 더 여는 시도는 속눈썹 띠가 위 테두리 피부와 겹쳐 흰 줄무늬가 생겼다. 그래서 눈은 v1 키를 쓰고, 놀람은 눈썹과 입으로 표현했다. 홍채 크기는 그대로이고, 3/4 에서 안구가 튀어나오지 않는다.
- **눈썹:** r30 눈썹은 앞머리에 대부분 가려지고, 색(120,66,56)이 머리카락(124,68,59)과 거의 같다.
  - 렌더에서는 앞머리에 가려진 부분만 어두운 눈썹색(×0.62)으로 겹쳐 그렸다.
  - 겹침 투명도는 0.8 × 감정 강도(Happy 는 절반)다. Neutral 은 r30 처럼 가려진 채다.
  - Unity 에서는 같은 동작을 하는 "앞머리 위 눈썹" 셰이더(스텐실 또는 별도 패스)가 필요하다.
- **눈물:** 독립 메시 `Face_Tear.L/R` (재질 `M_Tear` 반투명 하늘색, `M_TearHighlight` 흰 줄)를 만들었다.
  - `ExSad` 키에서는 0 두께로 아래 눈꺼풀을 따라간다.
  - `ExCry` 키에서는 최대 6 mm 고임이 된다.
  - 뺨을 따라 흐르는 `Face_TearStream.L/R` (키 `ExTearFlow`)는 구조만 만들었다. 지금 재질로는 피부 위에서 잘 보이지 않는다. 흐름 애니메이션 단계에서 외곽선·하이라이트 재질이 필요하다.

![Angry 얼굴](/Users/jjeong/UnityProjects/MyMischiefGirlfriend/BlenderSource/Characters/MainGirlfriend/Models/Race3D/experiments/sheets/angry_face.png)

![Angry 눈·눈썹 확대](/Users/jjeong/UnityProjects/MyMischiefGirlfriend/BlenderSource/Characters/MainGirlfriend/Models/Race3D/experiments/sheets/angry_eyes.png)

![Sad·Cry 얼굴](/Users/jjeong/UnityProjects/MyMischiefGirlfriend/BlenderSource/Characters/MainGirlfriend/Models/Race3D/experiments/sheets/sad_face.png)

![Surprise 얼굴](/Users/jjeong/UnityProjects/MyMischiefGirlfriend/BlenderSource/Characters/MainGirlfriend/Models/Race3D/experiments/sheets/surprise_face.png)

입 확대 시트:
- `sheets/happy_mouth.png`, `angry_mouth.png`, `sad_mouth.png`, `surprise_mouth.png`
- 눈·눈썹 확대: `*_eyes.png`

![Happy 입](/Users/jjeong/UnityProjects/MyMischiefGirlfriend/BlenderSource/Characters/MainGirlfriend/Models/Race3D/experiments/sheets/happy_mouth.png)

**입 관련 결정:**
- v1 의 벌린 입(`Face_Mouth_Smile_*`, MouthOpen)은 중간값에서 이·혀·입 안이 따로 떠서 깨진다.
- 그래서 새 입 두 개(`Face_Mouth_ExSmile`, `Face_Mouth_ExO`)는 선 위의 점에서 같은 모양 그대로 커지게 만들었다. 어느 강도에서도 작은 같은 입이다.
- 닫힌 입 선(`TT_Mouth_Closed`)에는 감정별 키를 추가했다. Basis 는 그대로다.

## 4. 조합 규칙과 충돌 방지 (`Models/Race3D/scripts/expr_mix.py`)

- **강도:** 각 감정은 0~1 이다. 전환은 두 감정을 선형으로 섞는다.
- **Happy 눈:** h ≤ 0.6 에서는 A = h/0.6. h > 0.6 에서는 A 가 B 로 넘어간다.
- **Blink:** 눈의 감정 키에 모두 (1 − Blink) 를 곱한다. 그래서 Blink 가 항상 이기고, 100 % 를 넘어 감기지 않는다.
- **시점 보정 키:** (1 − Blink)(1 − EyeSmile)(1 − Happy) 를 곱한다. 감은 웃음에서 먼 눈 보정이 겹치지 않는다.
- **시선:** 기존 GO/GI 분배를 그대로 쓴다. 검사 조합에 ±0.25 rad 를 포함했다.
- **입:**
  - Happy 는 0.35 까지 미소 선, 그 위로는 D자 입이 커진다.
  - Cry 는 Sad 선을 대신한다.
  - Surprise 는 선이 0.4 에서 사라지고 o 입이 커진다.
- **빌드 단계 보정:** 혼합 상태 2,970개를 검사했다.
  - 조합: 감정 쌍 전환 + Blink 0/0.5/1 + 시선 + 카메라 5각도
  - 같은 조건의 무표정보다 나빠지는 점만 대상으로, 새 키(Ex)만 앞으로 밀었다. 3회 만에 0 이 됐다.
  - v1 키만으로도 엄격한 기준(0.1 / 0.3 mm)에 미달하는 조합이 많다 (`spec/race3d_v2_expr_check_v1.json`). 그래서 "무표정보다 나빠지지 않음"을 기준으로 삼았다.

**전환 검증** (Neutral → Happy → Angry → Sad(+Cry 0.6) → Surprise, 각 8단계):
- GIF: `sheets/transition_0.gif`, `transition_35.gif`

![전환](/Users/jjeong/UnityProjects/MyMischiefGirlfriend/BlenderSource/Characters/MainGirlfriend/Models/Race3D/experiments/sheets/transition_strip.png)

**감은 눈 노출 (안구를 초록 단색으로 렌더한 화소 수):**

| 상태 | 0° | 35° | −35° | 45° | −45° |
|---|---|---|---|---|---|
| Blink 1 (기준) | 0 | 0 | 0 | 0 | 0 |
| Happy 1.0 | 0 | 0 | 0 | 0 | 0 |
| Happy 1.0 + Blink 0.5 | 0 | 0 | 0 | 0 | 0 |
| Angry / Cry / Surprise + Blink 1 | 0 | 0 | 0 | 0 | 0 |
| Happy 0.9 (덜 감긴 단계, 참고) | 342 | 313 | 178 | 289 | 119 |

## 5. 먼 눈 1 px 세로 점선

**위치와 원인:**
- 위치: ±35°·±45° 먼 눈의 바깥쪽, 속눈썹 덧단(띠 0행)과 안구 사이.
- 메시 구분 렌더로 확인한 해당 화소: 위 눈꺼풀 시트 180, 흰자 88, 아래 눈꺼풀 50 등 (45° 기준).
- 원인: v6j 의 각도 보정은 눈꼬리 쪽 속눈썹 띠를 그대로 두고 눈꺼풀만 닫는다 (t81 keep 방식). 그래서 바깥쪽에서 눈꺼풀 가장자리 피부와 흰자 일부가 띠 밑으로 드러난다.

**국소 후보 (v1 사본, `Models/Race3D/experiments/MainGirlfriend_Race3D_v1_farline_*.blend`, 스크립트 `race3d_v2_farline.py`):**

| 후보 | 변경 | +35° | −35° | +45° | −45° | 정면 변화 |
|---|---|---|---|---|---|---|
| v1 | — | 248 | 207 | 495 | 242 | — |
| A | 바깥쪽 위 눈꺼풀 덧단 면에 어두운 재질 (형상 변경 없음) | 250 | 207 | 471 | 231 | 0 화소 |
| B | 각도 보정 키 4개에서만 바깥 속눈썹 덧단을 눈꺼풀 가장자리까지 내림 | **109** | **118** | 547 | 254 | 0 화소 |
| B2 | B + 0.8 mm 더 내림, 범위 넓힘 | 109 | 112 | 567 | 258 | 0 화소 |

(가는 밝은 세로선 화소 수, Blender 4배 확대 렌더)

- B 는 ±35° 에서 절반 이하로 줄인다. ±45° 에서는 줄지 않는다.
- ±45° 에 남는 성분은 덧단만으로는 덮이지 않는다. 다음 조사 대상은 ViewSide 시작 각도(50°)와의 사이 구간이다.
- 새 눈 구조를 만들지 말라는 지시에 따라 여기서 멈췄다.

![점선 후보](/Users/jjeong/UnityProjects/MyMischiefGirlfriend/BlenderSource/Characters/MainGirlfriend/Models/Race3D/experiments/sheets/farline_candidates.png)

## 6. 남은 문제·검토 요청

1. **Angry 의 강도:** 눈썹·눈매·입·볼을 함께 조절해 화남으로 읽힌다. 다만 r30 의 작은 입과 가는 눈썹 때문에 참고 이미지보다 약하다. 더 강하게 할지 결정이 필요하다.
2. **입 크기:** Happy 1.0 의 D자 입은 r30 비율에 맞춰 작게 했다 (폭 약 18 mm). 더 크게 열지 결정이 필요하다.
3. **눈썹:** 앞머리 위 눈썹 겹침 방식(투명도, 색)을 채택할지 결정이 필요하다.
4. **눈물 흐름:** 재질과 애니메이션은 후속 단계다.
5. **Unity 반영 시 필요한 것 (지금은 하지 않음):**
   - BlendShape 가 47개에서 106개로 늘어난다 (새 키 59개, 이 중 눈 메시 4개에 각 6개).
   - 컨트롤러에 `expr_mix` 규칙을 넣어야 한다.
   - 앞머리 위 눈썹 셰이더, 눈물 반투명 재질, 새 입 메시 2개가 필요하다.
6. **보정 목록 밖의 상태:** Happy 0.125 / 0.625 같은 상태에서 속눈썹-눈꺼풀 간격이 0.19 mm 인 점 8개가 남았다 (기준 0.3 mm, 겹침은 아님).

## 7. 파일

| 경로 | 내용 |
|---|---|
| `Models/Race3D/experiments/MainGirlfriend_Race3D_v2_Expressions.blend` | 표정 실험 파일 (v1 에서 키·오브젝트만 추가) |
| `Models/Race3D/experiments/MainGirlfriend_Race3D_v1_farline_{A,B,B2}.blend` | 먼 눈 점선 후보 |
| `Models/Race3D/scripts/expr_common.py` | 안구 회전타원체, 눈꺼풀 표면 좌표 변환 |
| `Models/Race3D/scripts/expr_design.py` | 눈꺼풀 곡선 설계 (감정별 변수) |
| `Models/Race3D/scripts/expr_mix.py` | 강도 → 키 값 조합 규칙 |
| `Models/Race3D/scripts/race3d_v2_expr_build.py` | v1 → v2 빌드 (키 추가, 혼합 보정, 기존 키 해시 확인) |
| `Models/Race3D/scripts/race3d_v2_expr_render.py` | 렌더 (compare, express, transition, idcheck, flow) |
| `Models/Race3D/scripts/race3d_v2_expr_check.py` | 간섭 검사 (v2 / v1 기준선) |
| `Models/Race3D/scripts/race3d_v2_expr_sheets.py` | 검토 시트·GIF |
| `Models/Race3D/scripts/race3d_v2_farline.py` | 점선 후보 A / B / B2 |
| `Models/Race3D/experiments/renders/`, `sheets/` | 렌더 원본과 검토 시트 |
| `Models/Race3D/spec/race3d_v2_*.json` | 빌드 기록, 간섭 검사, 안구 노출, 점선 측정 |
| `Experiments/ToonTest_01/renders/farline_*` | 점선 후보 Blender 렌더 |
