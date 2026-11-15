# REPORT 23 — Race3D 표정 v3 추가 검증·최소 수정 (v3b 실험, 2026-11-13)

## 결론

- v3 를 기준으로 새 실험 파일 `Models/Race3D/experiments/MainGirlfriend_Race3D_v3b_Expressions.blend` 에서 추가 검증과 최소 수정만 했다.
- **보존:**
  - v1 베이스라인(.blend md5 e782f9f0…), v2(efc043e4…), v3(b03f303c…), v6j 파일, 정식 FBX(1d7263e7…)·프리팹(2ba1a33e…)은 바뀌지 않았다.
  - v1 의 기존 셰이프 키 99개는 v3b 에서도 그대로다(추가 98개).
- **Happy:** 0.7–0.8 의 일자 컷을 고쳤다.
  - 원인: v3 는 0.6→1.0 을 아래 눈꺼풀 U(받침) → ∩(감은 아치)로 직접 보간해, 중간에 일자를 지났다.
  - 수정: 중간 단계 C(0.85, 위아래 곡선을 유지한 렌즈 모양)를 넣었다.
  - 1.0 아치는 그대로다.
- **Angry 눈썹:** 30 mm 당김 + 스텐실 방식을 권장안으로 정했다.
  - 동작: 앞머리 바로 뒤에 있는 눈썹만 머리카락 위로 보인다.
  - ±35°/±45° 의 옆머리·먼 쪽 이마 뒤 눈썹은 가려진다. v3 의 "모든 머리카락 위" 방식에서 보이던 떠 보임이 없다.
  - 기존 Angry 는 보존했고, 더 강한 후보 Angry2 를 추가했다.
- **Cry 눈물:** 시작점에서 볼 중간까지 정면·±35° 에서 분명히 보이게 고쳤다.
  - 형태: 폭 3.4 → 7.5 mm, 길이 24 → 48 mm.
  - 위치: 피부·눈꺼풀·속눈썹·눈물방울 앞 0.5 mm.
  - 측정: 가려진 표본 0%, 피부와의 간격 중앙값 0.50 mm(최대 1.5 mm, 눈물방울 위).
- **Surprise:** v3 의 눈 크기, 홍채 0.92배, 반짝임을 유지했다.
  - 시선 ±0.25 × Surprise 0.5/1.0 에서 반짝임과 홍채 축소가 시선을 따라간다.
  - 눈꺼풀 관통은 없다.
  - Blender 와 Unity 의 결과가 같다.
- **v6j 시점 보정:**
  - 각 감정·Blink·시선 조합에서 시점 보정을 켜면, 먼 눈 흰자가 ±35/45/60° 모두 줄거나 같다.
  - 예외는 Cry ±45° 의 +4~5% 이며, 원인은 눈물방울의 밝은 화소다.
  - 혼합 상태 2,961개(±60° 포함, 양쪽 눈 5,922회 측정)에서 눈꺼풀-안구·속눈썹-눈꺼풀 간섭은 0이다.
- **Unity 플레이 모드:**
  - 245개 상태(촬영 213 + 연속 재생 캡처 32)에서 블렌드셰이프 가중치가 Blender 규칙과 4×10⁻⁷ 이내로 일치한다.
  - 16초 연속 재생(감정 교차·깜박임·시선·카메라 ±60°)에서 NaN 이나 범위 밖 값은 0이다.
- **권장:** v3b 를 표정 시스템의 정식 통합 후보로 올린다. 다만 통합에는 정식 코드·셰이더 변경이 필요해, 승인 전에는 하지 않았다(아래 "정식 통합 권고").

## 이번 수정 (v3 → v3b)

1. **Happy 중간 단계 C**
   - 키: 눈 키 `ExHappyC` 를 Happy 0.85 에 둔다.
   - 보간: 0–0.6 A, 0.6–0.85 A→C, 0.85–1.0 C→B.
   - C 의 모양: 위 눈꺼풀은 B 쪽으로 92%, 아래 눈꺼풀은 받침 곡선을 유지한 채 0.34 만큼 올린다. 그래서 0.7–0.9 가 일자가 아닌 렌즈·초승달 모양이 된다.
2. **Angry2**(`ExAngry2`): 기존 `ExAngry` 옆에 둔 더 강한 후보다.
   - 눈썹: 안쪽 하강 9.0 mm(기존 7.2), 굵기 ×2.3.
   - 눈꺼풀: 안쪽 누름 0.66.
   - 시선: 위로 1.0 mm.
   - 볼·홍조: 1.25배.
3. **눈썹 표시 방식**
   - 렌더 기본값: `pull` = 눈썹 카드를 카메라 쪽으로 30 mm 당긴 뒤 깊이 검사한다.
   - Unity 구조: 머리카락이 스텐실 1을 쓰고, 카드는 스텐실 1인 화소에만 그린다.
4. **눈물 줄기**
   - 폭 7.5 mm, 길이 48 mm, 가로 5열.
   - 각 면을 표본 추출해, 표면 아래로 들어가는 곳만 그 깊이만큼 꼭짓점을 앞으로 옮긴다.
5. **면 방향**
   - 문제: Unity 검증에서 열린 미소 입(`Face_Mouth_ExSmile`)이 보이지 않았다.
   - 원인: 미소 입·눈물 줄기·눈물방울 일부 면이 뒤(머리 안쪽)를 향했다. Blender 는 양면을 렌더해 드러나지 않았지만, Unity 는 뒷면을 버린다.
   - 수정: 보이는 포즈 기준으로 모든 면을 앞으로 맞췄다.
   - 영향: Blender 렌더 변화는 최대 4화소(투명 겹침 순서)뿐이다.
6. **보정 루프 확장**
   - 혼합 상태 보정에 ±60°, Angry2 조합, Happy+Surprise, 전환 중간값(Happy 0.125/0.375)을 넣었다.
   - 결과: 점검 위반이 0으로 수렴했다(이전 v3 는 ±45° 까지만 점검).

## 1. Happy 0.6 – 1.0

![Happy 단계](/Users/jjeong/UnityProjects/MyMischiefGirlfriend/BlenderSource/Characters/MainGirlfriend/Models/Race3D/experiments/sheets_v3b/happy_steps.png)

- 결과:
  - 0.7 과 0.8 은 위 ∩, 아래 U 의 렌즈 모양이고, 아래 눈꺼풀이 튀어나오지 않는다.
  - 0.9 는 가는 틈이고, 1.0 아치는 v3 와 같다.
- 노출 검사(안구 초록 ID 렌더, 다섯 각도):
  - Happy 1.0, Happy 1.0 + Blink 0.5 는 0 화소다.
  - Happy 0.95 는 515–989 화소의 틈이다. C→B 로 닫히는 의도한 틈이다.
- GIF: `sheets_v3b/happy_steps_0.gif`, `happy_steps_35.gif`(0.6→1.0→0.6, 0.025 간격).
- Unity: 같은 단계를 같은 카메라로 비교했다(`happy_steps_unity.png`).

![Happy Unity](/Users/jjeong/UnityProjects/MyMischiefGirlfriend/BlenderSource/Characters/MainGirlfriend/Models/Race3D/experiments/sheets_v3b/happy_steps_unity.png)

## 2. Angry 눈썹: 가림 / 모두 위 / 당김

| 방식 | 내용 | 정면 | ±35° / ±45° |
|---|---|---|---|
| hide (r30) | 머리카락이 그대로 가림 | 앞머리 사이로 조각만 보여 Angry 가 약하다 | 대부분 가려진다 |
| over (v3) | 머리카락 화소 전체 위에 카드 | 눈썹이 다 보인다 | 먼 쪽 눈썹이 옆머리 위에 떠 보인다 |
| **pull 30 mm (v3b 권장)** | 카드를 30 mm 당겨 깊이 검사 | 앞머리 위로 눈썹이 이어진다 | 옆머리·먼 쪽 뒤는 가려져 떠 보이지 않는다 |

- 당김 거리 비교:
  - 20 mm: 정면 바깥 앞머리에서 끊긴다.
  - 30 mm: 정면에서 이어진다.
  - 45 mm: 30 mm 와 차이가 없다.
- Unity 실험 셰이더(스텐실 + 뷰 공간 30 mm 당김)가 Blender 합성과 같은 결과를 낸다.

![눈썹 확대](/Users/jjeong/UnityProjects/MyMischiefGirlfriend/BlenderSource/Characters/MainGirlfriend/Models/Race3D/experiments/sheets_v3b/angry_brow_zoom.png)

![Angry / Angry2 얼굴](/Users/jjeong/UnityProjects/MyMischiefGirlfriend/BlenderSource/Characters/MainGirlfriend/Models/Race3D/experiments/sheets_v3b/angry_face.png)

- 전체 비교: `angry_brow.png`(Angry/Angry2 × hide/over/pull/Unity × 다섯 각도).

## 3. Cry 눈물 흐름

![Cry Flow 확대](/Users/jjeong/UnityProjects/MyMischiefGirlfriend/BlenderSource/Characters/MainGirlfriend/Models/Race3D/experiments/sheets_v3b/cry_flow_zoom.png)

- 흐름: Flow 0 → 0.25 → 0.5 → 0.75 → 1.0 에서 줄기가 눈물방울에서 시작해 아래로 늘어난다. 1.0 은 볼 중간이다.
- 각도별 보임:
  - 정면: 양쪽 다 끝까지 보인다.
  - ±35°: 가까운 쪽은 끝까지 보인다. 먼 쪽은 볼 윤곽에 가려 시작 부분만 보인다(실제 얼굴과 같은 가림).
  - +35° 아래 끝: 옆머리 가닥 뒤로 지나간다.
- 수치(Sad 1 + Cry 1, 외곽선 쉘 제외, 면당 16표본):

| | 가려진 표본 | 간격 중앙값 | 95% | 최대 |
|---|---|---|---|---|
| 수정 전 (3.4 × 24 mm) | 22% (위쪽 0–0.4 구간 34–71%) | – | – | – |
| v3b L | 0% | 0.50 mm | 0.69 mm | 1.54 mm (눈물방울 위) |
| v3b R | 0% | 0.49 mm | 0.71 mm | 1.47 mm |

- 전체 얼굴 시트: `cry_flow.png`, 눈 확대: `cry_eyes.png`.

## 4. Surprise × 시선

![Surprise 시선](/Users/jjeong/UnityProjects/MyMischiefGirlfriend/BlenderSource/Characters/MainGirlfriend/Models/Race3D/experiments/sheets_v3b/surprise_gaze.png)

- 반짝임: 별·점은 눈알 텍스처 공간의 층이라 시선 ±0.25 에서 홍채와 함께 움직이고, 홍채 0.92배 축소에도 같이 줄어든다.
- 눈꺼풀: 시선 끝에서도 흰자·홍채가 위 눈꺼풀을 뚫지 않는다(간섭 점검 0).
- Blender ↔ Unity:
  - 반짝임 위치·홍채 크기·눈꺼풀이 같다(행별 Blender / Unity).
  - Unity 의 `_Proj`(홍채 크기·시선 높이 반영)는 Blender 노드 값과 8×10⁻⁷ 이내로 같다.

## 5. v6j 시점 보정 × 감정 × Blink × 시선 (0 / ±35 / ±45 / ±60)

먼 눈 흰자 화소(머리카락 끔, 먼 쪽 120 px 띠, 배경·순백 반짝임 제외), 보정 끔 / 켬 / Unity:

| 상태 | +35 | −35 | +45 | −45 | +60 | −60 |
|---|---|---|---|---|---|---|
| Neutral | 1186/832/800 | 1607/1198/1163 | 497/451/428 | 772/727/744 | 253/196/176 | 269/190/165 |
| Happy 0.6 | 822/744/729 | 1155/1057/997 | 433/424/360 | 645/638/640 | 230/211/184 | 267/188/170 |
| Angry 1.0 | 912/524/504 | 1260/855/791 | 349/311/285 | 573/531/518 | 227/185/151 | 224/168/144 |
| Sad 1.0 | 1264/960/915 | 1657/1307/1259 | 593/549/542 | 884/843/858 | 252/199/165 | 287/188/161 |
| Cry 1.0 | 1390/1355/1288 | 1868/1781/1690 | 785/818/782 | 1094/1142/1132 | 268/199/169 | 328/216/180 |
| Surprise 1.0 | 2268/1921/2044 | 1939/1586/2037 | 1019/983/1000 | 966/920/1050 | 267/221/198 | 372/246/232 |
| Surprise + 시선 R | 6614/6561/6596 | 2711/2173/2327 | 4245/4238/4244 | 1475/1352/1452 | 847/636/577 | 286/209/187 |
| Angry + Blink 0.5 | 431/263/247 | 588/398/329 | 247/225/212 | 335/321/288 | 197/179/145 | 190/157/131 |

- 보정 효과: 보정을 켜면 모든 감정에서 흰자가 줄거나 같다. Cry ±45° 의 +4~5% 는 눈물방울 가장자리의 밝은 화소이며, 확대 시트(`view_fareye_45.png`)에서 눈꺼풀 이상은 없다.
- Unity: 값이 Blender "켬" 과 같은 수준이다. Surprise 의 Unity 값이 약간 큰 것은 흰자 음영 차이다.
- 간섭 점검(`race3d_v3b_expr_check.py`, 순수 블렌드셰이프 합 = GPU 와 같은 계산):
  - 범위: 프리셋 19개 + 전환 28개 × Blink 0/0.5/1 × 시선 0/±0.25 × 0/±35/±45/±60 = 2,961 상태(양쪽 눈 5,922회).
  - 결과: 새 표정 때문에 생긴 눈꺼풀-안구(0.1 mm)·속눈썹-눈꺼풀(0.3 mm) 위반 0.
  - 참고: v1 키만 쓴 기준선(EyeSmile/Surprise)은 원래부터 위반이 있다(`race3d_v3b_expr_check_v1.json`).
- 감은 상태(Blink, Cry + Blink, Surprise + Blink, Angry2 + Blink, Happy 1.0): 다섯 각도 모두 안구 노출 0 화소.

![먼 눈 ±60](/Users/jjeong/UnityProjects/MyMischiefGirlfriend/BlenderSource/Characters/MainGirlfriend/Models/Race3D/experiments/sheets_v3b/view_fareye_60.png)

- 상태별 전체: `view_35.png`, `view_45.png`, `view_60.png`(끔 / 켬 / Unity), 먼 눈 확대 `view_fareye_{35,45,60}.png`, 수치 `view_fareye_white.json`.

## 6. Unity 검증 (실험 폴더만, 정식 자산 변경 없음)

**구성** (`Assets/_Experiments/Race3D_v3b/`):

| 파일 | 내용 |
|---|---|
| `MainGirlfriend_Race3D_v3b_Expressions.fbx` | v3b 내보내기(46 렌더러, 블렌드셰이프 137) |
| `Shaders/MMGX_EyeBallSparkle.shader` | 정식 EyeBall 복사본 + `_SparkleTex` / `_Sparkle` |
| `Shaders/MMGX_ToonHairStencil.shader` | 정식 ToonHair 복사본, 색 패스가 스텐실 1 기록(큐 2010, 머리 다음) |
| `Shaders/MMGX_BrowCard.shader` | 스텐실 1 위에만, 뷰 공간 30 mm 당김, `_Reveal` |
| `Shaders/MMGX_TearStream.shader` | Blender `M_TearStream` 이식, `_Flow` |
| `Runtime/Race3DExprCheck.cs` (+ asmdef) | 시험 전용 드라이버. 아래 설명 |
| `Race3DExprCheck.unity`, `Spec/`, `Textures/` | 시험 씬, Blender 촬영 구도·투영값, 반짝임 텍스처 |

- 드라이버 동작:
  - `expr_mix_v3b` 규칙과 v6j 시점 키 공식을 그대로 옮겼다.
  - 정식 프리팹의 재질은 실행 중 복사본으로만 쓴다.
  - Blender 와 같은 직교 카메라로 촬영한다.

**결과:**
- 좌표: Unity 와 Blender 의 눈알 위치 차이 0.0000 m(Blender (x, y, z) = Unity (−x, z, −y)), 카메라 각도 오차 < 0.00001°.
- 가중치:
  - 245개 상태(촬영 213 + 연속 재생 캡처 32)에서 눈꺼풀 키 7,840개의 최대 차이는 3.8×10⁻⁷ 이다.
  - 재질 값(반짝임·홍채·시선 높이·Flow·눈썹 카드)의 최대 차이는 8×10⁻⁷ 이다.
  - 표시 전환(입 선·o·미소·눈물·흐름) 불일치는 0 이다.
- 연속 재생(16초, 60 fps, 960 프레임):
  - 입력: Neutral → Happy → Angry → Angry2 → Sad+Cry → Surprise → Happy 0.7 → Neutral 교차, 2.7초마다 깜박임, 시선 ±0.25, 카메라 ±60° 왕복.
  - NaN·범위 밖 가중치 0.
  - 깜박임 밖의 눈 키 최대 변화는 1/60초당 5.4% 다. 카메라 회전 속도에 따른 ViewFar 의 이론값(5.9%)과 같은 수준이라, 튀는 값이 없다.
- 전환 비교: Blender 와 같은 33단계를 0° / 35° 에서 촬영했다(`transition_{0,35}_unity_blender.png`).
- 이번 검증에서 찾은 문제: 열린 미소 입이 Unity 에서 안 보였다. 면 방향 문제였고, 위 수정 5로 해결했다.

![Unity 연속 재생](/Users/jjeong/UnityProjects/MyMischiefGirlfriend/BlenderSource/Characters/MainGirlfriend/Models/Race3D/experiments/sheets_v3b/unity_play_sweep.png)

![전환 35°](/Users/jjeong/UnityProjects/MyMischiefGirlfriend/BlenderSource/Characters/MainGirlfriend/Models/Race3D/experiments/sheets_v3b/transition_35_unity_blender.png)

- 재생 GIF: `sheets_v3b/unity_play_sweep.gif`.
- 원본 캡처·로그: `Models/Race3D/experiments/unity_v3b/`(`log.txt`, `weights.jsonl`).
- 설정 복원:
  - 플레이 모드 종료 후 Run In Background 를 프로젝트 값(off)으로 되돌렸다.
  - URP 자산(MSAA 1, Render Scale 0.8)은 건드리지 않았다.
  - git 에 보이는 `Mobile_RPAsset`/`PC_RPAsset` 변경은 이번 작업 전(13:01 이전)부터 있던 직렬화 필드·렌더러 목록 항목이다.

## 7. v3 → v3b 비교

![v3 vs v3b](/Users/jjeong/UnityProjects/MyMischiefGirlfriend/BlenderSource/Characters/MainGirlfriend/Models/Race3D/experiments/sheets_v3b/compare_v3_v3b_eyes.png)

- Happy 0.8: v3 아래 눈꺼풀 일자 → v3b 렌즈.
- Angry: v3 "모두 위" → v3b 당김(떠 보임 없음). Angry2 행을 추가했다.
- Cry: v3b 줄기가 볼 중간까지 보인다.
- Surprise: 같다.
- 얼굴 전체: `compare_v3_v3b_face.png`.

## 정식 통합 권고

**권고:**
- v3b 를 Race3D 표정의 정식 기준으로 통합한다.
- 방식: v1 베이스라인에 98개 키와 새 메시를 더하고, 기존 99개 키는 그대로 둔다. 기존 프리팹·EyeViewController 동작은 표정 0 에서 동일하다.
- 단, 아래 결정과 정식 코드 변경이 필요해 승인 전에는 하지 않았다.

1. **EyeViewController 입력 추가 (정식 코드 변경)**
   - 현재: 시점 키를 (1 − Blink)(1 − EyeSmile) 로만 줄인다.
   - 필요: v3b 는 Happy 도 곱한다. 이번 시험은 전용 드라이버가 같은 공식을 대신 계산했다.
   - 제안: `EyeViewController` 에 시점 억제 입력(예: `viewSuppress` = Happy)을 더한다. 표정 키(Ex*)·재질 값은 별도 `ExpressionController` 가 쓴다. 쓰기 시점은 기존 EyeViewLoop 와 같다.
2. **셰이더 (정식 셰이더 변경)**
   - EyeBall: 반짝임 층, `_Proj` 실행 중 변경.
   - ToonHair: 스텐실 기록 패스, 큐 2010.
   - 새 셰이더: BrowCard, TearStream.
3. **Angry 기본값 선택 (사용자 결정):** 기존 Angry(약) / Angry2(강) 중 기본값. 둘 다 키로 남길 수 있다.
4. **눈썹 당김 30 mm 는 현재 bob 헤어에 맞춘 값이다.** 헤어 아이템마다 앞머리 두께가 달라 아이템별 값이 필요할 수 있다. 헤어 외형 데이터(Unity 원본)에 둘지는 미정 사항으로 남긴다.
5. **실기기 확인:** Android 실기기에서 스텐실·투명 순서와 비용(눈썹 카드 2, 줄기 2 draw)을 확인하는 단계가 남았다.

## 변경·생성 파일

- Blender (`BlenderSource/Characters/MainGirlfriend/Models/Race3D/`):
  - `experiments/MainGirlfriend_Race3D_v3b_Expressions.blend`(새로 생성), `experiments/textures/eye_sparkle_{L,R}.png`
  - `experiments/renders_v3b/`, `experiments/unity_v3b/`, `experiments/sheets_v3b/`
  - `scripts/expr_design_v3b.py`, `scripts/expr_mix_v3b.py`
  - `scripts/race3d_v3b_expr_{build,render,check,sheets}.py`, `scripts/race3d_v3b_export_fbx.py`, `scripts/race3d_v3b_unity_setup.cs`
  - `spec/race3d_v3b_expr_build.json`, `spec/race3d_v3b_expr_check_{v3b,v1}.json`, `spec/race3d_v3b_unity_{proj,shots}.json`
- Unity: `Assets/_Experiments/Race3D_v3b/` 전체(위 표).
- 바꾸지 않음:
  - v1·v2·v3·v6j 의 .blend, FBX, 프리팹, 렌더, 스크립트(v3 스크립트 포함).
  - `Assets/_Game` 전체(정식 Model3D, 셰이더, `MMG.Characters.Avatar3D`), 열린 씬(`Live2DTest_MainGirlfriend.unity`, dirty 아님), URP 자산.
