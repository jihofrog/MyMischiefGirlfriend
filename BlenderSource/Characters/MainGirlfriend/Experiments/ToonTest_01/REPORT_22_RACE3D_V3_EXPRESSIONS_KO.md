# REPORT 22 — Race3D 표정 2차 수정 (v3 실험, 2026-11-13)

## 결론

- 새 실험 파일 `Models/Race3D/experiments/MainGirlfriend_Race3D_v3_Expressions.blend` 에서 네 가지 피드백을 반영했다.
- **보존:**
  - v1 베이스라인(.blend 해시 e782f9f0… 동일), v6j, Unity 정식 FBX·프리팹은 수정하지 않았다.
  - v2 파일은 수정 전 비교용으로 그대로 두었다.
  - v1 의 기존 셰이프 키 99개는 v3 안에서도 바뀌지 않았다.
- **Happy:**
  - 아래 눈꺼풀이 가운데로 솟지 않고, 홍채 아래를 얕게 받쳐 주는 형태가 됐다.
  - 감은 단계는 더 둥근 ∩ 아치다.
  - 볼은 앞으로 덜 나온다.
- **Angry:**
  - 눈썹: 안쪽이 7.2 mm 내려가고 2.8 mm 모이며, 바깥은 2.4 mm 올라간다.
  - 눈: 위 눈꺼풀이 안쪽부터 사선으로 눌리고, 시선은 0.8 mm 위로 간다.
  - 입 변화는 줄였다.
- **Sad / Cry:**
  - Sad: 눈썹·눈꼬리가 더 처지고, 얇은 눈물막이 생긴다.
  - Cry: 고인 눈물과 뺨으로 흐르는 줄기(마스크 `Flow`)를 더했다.
- **Surprise:**
  - 위 눈꺼풀이 v1 Surprise 의 1.6배 열린다.
  - 홍채는 0.92배로 작아지고, 별·점 반짝임이 더해지며, 눈썹은 5.5 mm 올라간다.
- **검증:**
  - 감은 상태는 다섯 각도 모두 안구 노출 0 화소다.
  - 혼합 상태 3,600개에서 새 표정 때문에 생긴 눈꺼풀-안구 간섭은 0이다.
  - 속눈썹-눈꺼풀은 6점이 0.24 mm 이상 앞에 있다 (기준 0.3 mm, 겹침 없음).
- 정식 Unity 통합, 프리팹 교체, 최종 확정은 하지 않았다.

## 제출 자료 (`Models/Race3D/experiments/sheets_v3/`)

| 시트 | 내용 |
|---|---|
| `eyes.png` | 눈·눈썹 확대. 행: Neutral, Happy 0.3 / 0.6 / 1.0, Angry 1.0, Sad 1.0, Sad + Cry 1.0, Surprise 1.0. 열: 0°, +35°, −35°, +45°, −45° |
| `faces.png` | 얼굴 전체, 같은 행과 열 |
| `transition_strip.png`, `transition_0.gif`, `transition_35.gif` | Neutral → Happy → Angry → Sad(+Cry 0.6) → Surprise, 단계마다 8프레임 |
| `before_after_eyes.png`, `before_after_face.png` | 수정 전(v2) → 수정 후(v3), 0° / 35° |
| `tear_flow.png` | Cry 1.0 의 흐름 마스크 Flow 0 → 1 |

![눈·눈썹](/Users/jjeong/UnityProjects/MyMischiefGirlfriend/BlenderSource/Characters/MainGirlfriend/Models/Race3D/experiments/sheets_v3/eyes.png)

![얼굴 전체](/Users/jjeong/UnityProjects/MyMischiefGirlfriend/BlenderSource/Characters/MainGirlfriend/Models/Race3D/experiments/sheets_v3/faces.png)

![수정 전 → 수정 후](/Users/jjeong/UnityProjects/MyMischiefGirlfriend/BlenderSource/Characters/MainGirlfriend/Models/Race3D/experiments/sheets_v3/before_after_eyes.png)

![전환](/Users/jjeong/UnityProjects/MyMischiefGirlfriend/BlenderSource/Characters/MainGirlfriend/Models/Race3D/experiments/sheets_v3/transition_strip.png)

![눈물 흐름 마스크](/Users/jjeong/UnityProjects/MyMischiefGirlfriend/BlenderSource/Characters/MainGirlfriend/Models/Race3D/experiments/sheets_v3/tear_flow.png)

## 감정별 변경 요약

눈 키는 v2 와 같은 방식이다. 열마다 Blink 비율을 달리하고, 안구 표면 좌표에서 보간한 뒤, 혼합 상태 보정을 한다. 표의 % 는 그 열에서 Blink 를 적용한 비율이다.

### Happy (키: 눈 `ExHappyA` / `ExHappyB`, 머리·볼 터치·눈썹·입 `ExHappy`, 입 `Face_Mouth_ExSmile`)

| 항목 | v2 | v3 |
|---|---|---|
| A 단계 (0~0.6) 아래 눈꺼풀 | 두 눈꼬리를 잇는 ∩ 아치로 가운데가 크게 솟음 (가운데에 눈 높이의 40 % 만 남김). 돌출돼 보임 | 원래 U자 가장자리를 가운데 위주로 눈 높이의 24 % 만 올림 (얕은 요람 모양). 홍채 아래를 받쳐 줌 |
| A 단계 위 눈꺼풀 | 감은 선까지의 15 % | 24 % (눈매를 위에서 조금 더 감쌈) |
| B 단계 (1.0) 감긴 선 | ∩ 아치 높이 15 %, 지수 0.8 (윗부분이 평평함) | 아치 17 %, 지수 1.2 (더 둥근 꼭짓점, 부드러운 끝), 4 px 아래 |
| 볼 (`Blockout_Head`) | 위 1.3 mm, 앞 0.6 mm | 위 1.0 mm, 앞 0.2 mm (앞으로 덜 나와 볼록함이 줄어듦) |
| 0.6~1.0 | A → B 선형 | 같음. A 가 열린 초승달이라 0.8 에서 가는 눈웃음이 된다 |

### Angry (키: 눈 `ExAngry`, 눈썹 `ExAngry`, 눈썹 카드, 볼·볼 터치 `ExAngry`, 입 선 `ExAngry`, 재질 시선)

| 항목 | v2 | v3 |
|---|---|---|
| 위 눈꺼풀 | 안쪽 42 % → 바깥 8 %, 안쪽에만 몰림 | 안쪽 55 % → 바깥 3 %, 안쪽 모서리부터 곧은 사선 (`(1-u)^1.3`) |
| 아래 눈꺼풀 | 20 % | 12 % + 바깥쪽 8 % (눈매를 가늘게) |
| 눈썹 안쪽 끝 | 5.5 mm 아래, 1.5 mm 안쪽 | 7.2 mm 아래, 2.8 mm 안쪽, 2배 굵게 |
| 눈썹 바깥 끝 | 1.2 mm 위 | 2.4 mm 위 |
| 시선 | — | 안구 텍스처 투영을 0.8 mm 위로 (`_Proj` tv) |
| 입 | へ 높이 4.6 px, 폭 72 % | へ 3.0 px, 폭 66 % (입의 역할 축소) |

### Sad / Cry (키: 눈 `ExSad` / `ExCry`, 눈썹 `ExSad` / `ExCry`, 눈물 `Face_Tear` `ExSad` / `ExCry`, 줄기 `Face_TearStream` + 재질 `Flow`)

| 항목 | v2 | v3 |
|---|---|---|
| Sad 위 눈꺼풀 | 바깥 32 %, 안쪽 −6 % | 바깥 36 %, 안쪽 −8 % (`tail^0.8`, 바깥 처짐이 더 넓음) |
| Sad 아래 눈꺼풀 | 14 % | 18 % (울먹이며 차오름) |
| Sad 눈썹 | 안쪽 5.0 mm 위 | 안쪽 6.2 mm 위, 바깥 1.8 mm 아래 |
| Sad 눈물 | 없음 | 아래 눈꺼풀을 따라 얇은 눈물막 (Cry 고임의 30 %) |
| Sad 입 | ︵ | ︵ + 작은 떨림 |
| Cry 아래 눈꺼풀 | 38 % | 40 % |
| Cry 눈물 | 고임만 (흐름 줄기는 거의 보이지 않음) | 고임 + 시작점 방울 + 뺨 줄기 (정지 시트는 Flow 0.5) |

**눈물 구조 (향후 애니메이션 전제):**

| 부품 | 구조 |
|---|---|
| `Face_Tear.<s>` (고임) | 아래 눈꺼풀 가장자리를 따라가는 띠, 4행 + 하이라이트 2행. 키 `ExSad` (얇은 막, 눈꺼풀을 따라감), `ExCry` (최대 6 mm 고임). 재질 `M_Tear` (반투명 하늘색), `M_TearHighlight` (흰 줄) |
| `Face_TearStream.<s>` (줄기) | 바깥 아래 눈꺼풀(u 0.8)의 고임에서 시작해 뺨을 따라 24 mm 내려가는 리본 (36분할). 시작 방울 4.8 mm → 끝 2 mm 폭. 정점마다 "피부와 울먹임 상태 눈꺼풀 중 앞쪽 면"에서 0.8~2 mm 띄움 |
| UV | u = 폭 방향 (0~1), v = 눈에서 아래로 (0~1) |
| 재질 `M_TearStream` | 알파 = (v < Flow, 끝 0.08 부드럽게) × (폭 가장자리 감쇠 1 − \|2u−1\|⁴) × 0.85, u 0.38 에 흰 반사선. 값 노드 `Flow` 가 애니메이션 변수 |
| Unity 대응 (설계만) | `MMG/Character/Tear` 셰이더. `_Flow` (흐름), `_Width`, 반사선. 고임은 BlendShape `ExSad` / `ExCry`. 줄기는 메시 고정 + `_Flow` 를 시간으로 올림. 여러 줄기는 v 오프셋으로 반복 |

### Surprise (키: 눈 `ExSurprise`, 눈썹 `ExSurprise`, `Eye_Sparkle.<s>` `ExSurprise`, 입 `Face_Mouth_ExO`, 재질 홍채 크기)

| 항목 | v2 | v3 |
|---|---|---|
| 위 눈꺼풀 | v1 Surprise 키 그대로 | v1 Surprise × 1.6. 속눈썹 띠가 테두리 피부 위에 놓이는 곳은 피부보다 0.4 mm 앞으로 (v2 의 흰 줄무늬 원인 제거) |
| 홍채 | 그대로 | 0.92배 (안구 텍스처 투영을 홍채 중심 기준으로 확대, 재질 값) |
| 하이라이트 | 원화 그대로 | 홍채 왼쪽 위 4각 별 + 오른쪽 아래 작은 점 (`Eye_Sparkle`, 안구 표면 0.25 mm 앞, 기본 크기 0) |
| 눈썹 | 4.2 mm 위 | 5.5 mm + 아치 1.5 mm 위 |
| 입 | o 입 | 같음 |

- 3/4 에서 안구가 튀어나와 보이지 않는다. 안구 위치는 바뀌지 않았고, 눈꺼풀만 연다.
- 반짝임 메시는 시선을 따라가지 않는다. Unity 에서는 안구 셰이더의 하이라이트 층으로 넣는 것을 권장한다.

### 앞머리에 가려지는 눈썹 — 정식 구조 제안

**v3 에서 만든 것:**
- `Face_BrowCard.L/R`: 눈썹 복사본에 같은 키 10개를 두고, 재질은 어두운 눈썹색 `M_BrowCard` 다.
- 렌더에서는 눈썹이 실제로 보이는 화소(눈썹을 초록 단색으로 바꾼 패스)를 빼고, 가려진 부분에만 카드를 겹친다.
- 겹침 투명도는 0.8 × 감정 강도다.

**Unity 제안 (지금은 구현하지 않음):**
1. 헤어 재질이 스텐실 값 1 을 쓴다.
2. 눈썹 카드는 `MMG/Character/BrowOverHair` 셰이더를 쓴다.
   - Stencil Equal 1 이라 헤어 화소에만 그려진다.
   - ZTest Always, Cull Back 이다. 뒤에서 볼 때는 카드가 뒷면이라 그려지지 않는다.
   - `_Reveal` = 0.8 × max(Angry, Sad, Cry, Surprise, Happy/2) 를 컨트롤러가 넣는다.
3. 일반 눈썹은 지금처럼 피부 위에만 그린다. 무표정은 `_Reveal` 0 이라 r30 처럼 가려진다.

## 조합 규칙 (`expr_mix_v3.py`, v2 규칙에 추가)

- 재질 값:
  - 홍채 크기 1 − 0.08 × Surprise
  - 시선 위 0.8 mm × Angry
  - 반짝임 = Surprise
  - 눈물 줄기 Flow (기본 0.5 × Cry)
- 눈물은 Sad 또는 Cry 가 0.05 를 넘으면 보이고, Blink 가 눈을 닫는 동안 사라진다.
- 나머지 규칙은 v2 와 같다.
  - 눈 감정 키 × (1 − Blink)
  - 시점 보정 키 × (1 − Blink)(1 − EyeSmile)(1 − Happy)
  - Happy 2단계

## 검증

| 항목 | 결과 |
|---|---|
| 기존 키 (v1 99개) | 변경 0 |
| 혼합 상태 보정 (빌드) | 2,970 상태, 3회 만에 기준 미달 점 0 |
| 독립 검사 (3,600 상태: 프리셋 + 전환 × Blink 3 × 시선 3 × 카메라 5) | 새 표정 때문에 생긴 눈꺼풀-안구 간섭 0. 속눈썹-눈꺼풀 6점 (Happy 0.125, +45°, 최소 0.24 mm 앞, 겹침 없음) |
| 감은 상태 안구 노출 | Happy 1.0, Happy 1.0 + Blink 0.5, Angry / Cry / Surprise + Blink 1, Blink 1: 0°·±35°·±45° 모두 0 화소 |

## 남은 점

1. **Angry 의 정도:** 눈썹과 눈매로 화남이 분명해졌다. 다만 r30 의 가는 눈썹이라 참고 이미지만큼 강하지는 않다.
2. **Happy 0.8:** A(열린 초승달)와 B(감은 아치)의 중간이라 아주 가는 눈이 된다. 더 일찍 감기게 할지 결정이 필요하다 (현재 0.6 에서 A 가 최대).
3. **눈물 줄기:** 35° 에서는 뺨 굴곡 때문에 짧게 보인다. 흐름 애니메이션 단계에서 경로를 각도별로 확인해야 한다.
4. **새 오브젝트가 Unity 에 들어갈 때 필요한 것:**
   - 셰이프 키 77개 추가 (Basis 제외)
   - 새 메시 8개: 눈썹 카드 2, 반짝임 2, 눈물 고임 2, 눈물 줄기 2 (v2 의 입 2개는 별도)
   - 셰이더 3종: 눈썹 카드, 눈물, 안구 하이라이트

## 파일

| 경로 | 내용 |
|---|---|
| `Models/Race3D/experiments/MainGirlfriend_Race3D_v3_Expressions.blend` | 2차 수정 실험 파일 (v1 에서 빌드) |
| `Models/Race3D/scripts/expr_design_v3.py` | 눈꺼풀 곡선 (v3 변수) |
| `Models/Race3D/scripts/expr_mix_v3.py` | 조합 규칙 (재질 값 추가) |
| `Models/Race3D/scripts/race3d_v3_expr_build.py` | v1 → v3 빌드 |
| `Models/Race3D/scripts/race3d_v3_expr_render.py` | 렌더 (안구 투영, 반짝임, 눈물 Flow, 눈썹 카드 겹침) |
| `Models/Race3D/scripts/race3d_v3_expr_check.py` | 간섭 검사 |
| `Models/Race3D/scripts/race3d_v3_expr_sheets.py` | 검토 시트 (v2 대비 포함) |
| `Models/Race3D/experiments/renders_v3/`, `sheets_v3/` | 렌더와 시트 |
| `Models/Race3D/spec/race3d_v3_expr_build.json`, `race3d_v3_expr_check_v3.json`, `race3d_v3_expr_eyeball_px.json` | 빌드 기록과 검사 결과 |

v2 파일·스크립트·렌더(`renders/`, `sheets/`)는 비교 기준으로 그대로 두었다.
