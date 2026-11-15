# ToonTest_01 — v6j 마무리 검증 (2026-11-13)

v6j 의 형상과 각도 보정 구조는 바꾸지 않았다. `MG_ToonTest_01_v6j.blend`(10:59)·`MG_ToonTest_01_v6j_eye.fbx` 그대로이며, 별도 승인 후보로 보존한다.

이번에 바꾼 것은 모두 `Assets/_Experiments/ToonTest_01/` 안의 실험 파일이다:
- Unity 쪽 렌더 재질 (새 셰이더 사본 `MMGExp_AnimeToonEyeV6j.shader`)
- 런타임 드라이버 (`Runtime/`)

원본, 기존 셰이더, 프리팹, 씬, 아이템 시스템, URP 설정은 그대로다.

통합용 정리는 `EYE_V6J_INTEGRATION_KO.md` 에 있다.

## 1. Unity 가 Blender 보다 거칠게 보이던 원인과 수정

| 증상 | 원인 (확인 방법) | 수정 (실험 재질만) |
|---|---|---|
| 속눈썹 띠 안의 살색 점 | 속눈썹만, 눈꺼풀 제외, 머리 제외 렌더로 좁혔다. 머리 피부가 속눈썹 앞으로 나온다. 깊이를 1 mm 당기면 사라진다. v6d_3·v6f_A Unity 에도 있던 문제다. | `_ViewPull` 1 mm: 속눈썹 깊이만 카메라 쪽으로 당긴다. 화면 위치는 그대로다. |
| 눈꺼풀 경계의 가는 갈색 선 | 스킨 툰 셰이더의 외곽선 패스가 눈꺼풀 시트에도 그려졌다. Blender 는 머리에만 외곽선이 있다. | 눈꺼풀 시트는 외곽선 폭 0 인 스킨 재질 |
| 속눈썹 가장자리 계단, 반투명 텍셀 | 알파를 커버리지로 쓰는 방식(A2C)에서 반투명 텍셀이 부분적으로만 덮었다. | A2C 알파를 0.5 기준으로 한 픽셀 폭 안에서만 부드럽게 했다 (안쪽은 불투명). 알파는 mip 0 에서 읽는다. 양면 렌더도 켰다. |
| 전반적인 계단 | 프로젝트 URP 설정이 MSAA 꺼짐(`m_MSAA: 1`), 모바일 렌더 스케일 0.8 이다. | 바꾸지 않았다. 통합 위험 항목에 넣었다. |

- **이미지:**
  - `renders/compare_eye_v6j_unity_fix_detail.png` (Blender / Unity 기존 / Unity 수정)
  - `compare_eye_v6j_unity_fix_tail.png`
  - `compare_eye_v6j_speck_debug.png`
  - `compare_eye_v6j_msaa.png` (Blender / Unity MSAA 4 / Unity MSAA 없음)
- **수치 (4배 확대 26장, Blender 대비 평균 차):** 0.0131 → 0.0088. 강한 차이 픽셀(합 > 0.6)은 193,604 → 57,247 (−70 %).
- **정면:** 형상 변경이 없으므로 Blender 정면은 그대로다. Unity 정면 이미지 차이 0.005~0.006 은 재질 변경(외곽선 제거, 속눈썹 가장자리)에서 온다. r30 눈 모양, 홍채, 속눈썹 형태, 쌍꺼풀 선은 같다.
- **60°·90°:** 깊이를 당겨도 속눈썹이 머리를 뚫고 보이지 않았다.

## 2. 실제 Unity 플레이 회전 영상 (0 → +60 → 0 → −60 → 0, 0.5°/프레임, 30 fps)

| 파일 | 내용 |
|---|---|
| `renders/unity_final_v6j_face_turn.mp4` / `.gif` | 얼굴 전체 |
| `renders/unity_final_v6j_eye_turn.mp4` / `.gif` | 눈 확대 |
| `renders/unity_final_AB_face_turn.mp4`, `unity_final_AB_eye_turn.mp4` | A v6f_A 와 나란히 |
| `compare_eye_v6j_final_face_turn.png`, `compare_eye_v6j_final_eye_turn.png` | 0~60° 양방향 프레임 |

- **촬영 조건:** 보정 재질 적용. 새 컨트롤러(PlayerLoop 합성)로 실제 SkinnedMeshRenderer 스키닝과 정상 렌더 루프에서 촬영했다.
- **육안 확인:** 15~45° 에서 눈 폭과 속눈썹 끝이 갑자기 바뀌는 프레임이 없었다. 먼 눈의 흰자가 20° 부터 서서히 줄고, 가까운 눈은 A 와 같다.
- **수치:**

| 시퀀스 | A 자체 프레임 변화 최대 | v6j 초과분 최대 | 15~45° 구간 초과분 | 보정 가중치 변화 최대 (프레임당) |
|---|---|---|---|---|
| 얼굴 전체 | 0.033 | 0.0013 | 0.0012 | 0.037 |
| 눈 확대 | 0.035 | 0.0017 | 0.0017 | 0.035 |

## 3. 컨트롤러 충돌 검증과 명시적 실행 순서

**구조:**
- **실행 지점 (`Runtime/EyeViewLoop.cs`):** PlayerLoop 의 PostLateUpdate 안, DirectorLateUpdate 바로 다음에 합성 단계를 넣었다. 그 뒤는 ScriptRunDelayedDynamicFrameRate 이고, 이어서 렌더러·스키닝 갱신이다.
  - 모든 LateUpdate(실행 순서 무관), Animator, Timeline 이 값을 쓴 뒤에 한 번 실행된다.
  - MonoBehaviour 실행 순서를 바꿔도 결과가 같다.
- **입력 방식 (`EyeViewController.inputSource`):**
  - `Fields` (권장): Animator 가 컨트롤러의 blink / eyeSmile / smile / surprise / gaze 필드를 애니메이션한다. 컨트롤러가 눈 키 전부를 쓴다.
  - `BlendShapes` (기존 클립 호환): 클립이 BlendShape 를 직접 쓰면, 컨트롤러는 그 값을 입력으로 읽고 보정 키만 쓴다.
- **다른 작성자 감지:** 지난 프레임에 쓴 보정 키 값이 바뀌어 있으면 `ForeignWrites` 를 센다.

**검증:**
- Unity 플레이 모드, `Runtime/TestOnly/EyeViewRobustnessTest.cs`, 경우마다 150 프레임, 렌더 직전에 4개 렌더러를 검사했다.
- Animator 는 Playables 로 메모리 내 클립을 돌렸다.
- 방해 스크립트는 실행 순서 −30000 / +30000 의 LateUpdate 에서 보정 키와 Blink 를 100 으로 쓴다.
- 결과 원본: `renders/unity_play/robustness.jsonl`

| 경우 | 보정 키 덮어씀 | Blink 100 % 초과 닫힘 | Blink ≠ 애니메이션 값 | 감지한 외부 쓰기 |
|---|---|---|---|---|
| PlayerLoop, Animator→필드 | 0 | 0 | 0 | 0 |
| PlayerLoop, Animator→필드, 앞뒤 방해 (보정 키 + Blink) | 0 | 0 | 0 | 152 |
| PlayerLoop, Animator→BlendShape | 0 | 0 | 0 | 0 |
| PlayerLoop, Animator→BlendShape, 앞뒤 방해 (보정 키) | 0 | 0 | 0 | 152 |
| PlayerLoop, Animator→BlendShape, 뒤에서 Blink 덮어씀 | 0 | 0 | **600** (한계) | 152 |
| (비교) 기존 LateUpdate 합성, 앞 방해 | 0 | 0 | 0 | 152 |
| (비교) 기존 LateUpdate 합성, 뒤 방해 | **600** | **600** (최대 4배) | **600** | 151 |

- **기존 구조의 문제:** 이전의 LateUpdate 합성은 뒤에 실행되는 스크립트가 있으면 무너진다 (마지막 줄).
- **새 구조:** 실행 순서와 무관하다.
- **남은 한계:** `BlendShapes` 입력에서는, 다른 스크립트가 LateUpdate 에서 Blink 를 쓰면 그것이 입력이 된다. 이 경우에도 닫힘이 Blink 100 % 를 넘지는 않는다. 그래서 `Fields` 를 기본으로 권한다.

## 4. 성능

**Android 실기기: 미검증.** `adb devices` 에 연결된 기기가 없다 (SDK·AndroidPlayer 모듈은 설치되어 있음).

**참고 (데스크톱 Editor 플레이 모드, Apple M5 Pro, 기기 측정 아님, `TestOnly/EyeViewPerfProbe.cs`):**

| 캐릭터 | 보정 | 컨트롤러 µs/프레임 평균 (최대) | 프레임 ms 평균 (Editor) |
|---|---|---|---|
| 1 | 켬 | 19.9 (875, 첫 프레임 포함) | 2.95 |
| 1 | 끔 | 12.7 (21) | 2.57 |
| 12 | 켬 | 151 (226) | 3.79 |
| 12 | 끔 | 128 (183) | 2.96 |

- **메모리:** REPORT_17 측정값 그대로다. 눈 메시 +320 KB, BlendShape 31→47. 같은 모델의 인스턴스끼리는 공유된다.
- **모바일 추정 (미검증):**
  - 12명이면 컨트롤러가 약 0.45~0.75 ms/프레임 (모바일 CPU 를 3~5배 느리다고 가정).
  - 모바일에서는 화면에 작게 보이는 캐릭터의 보정을 끄거나 간격을 두고 갱신하고, 바뀐 값만 쓰는 최적화가 필요하다.

## 5. 파일

| 파일 | 내용 |
|---|---|
| `Assets/_Experiments/ToonTest_01/MMGExp_AnimeToonEyeV6j.shader` | 속눈썹 셰이더 사본 (A2C 선명화, mip0 알파, 양면, `_ViewPull`) |
| `Runtime/EyeViewController.cs`, `Runtime/EyeViewLoop.cs` | 드라이버 (PlayerLoop 합성, 입력 방식, 외부 쓰기 감지) |
| `Runtime/EyeViewTestRig.cs` | 테스트 시퀀스 (`sequenceSet` = final 추가) |
| `Runtime/TestOnly/EyeViewRobustnessTest.cs`, `EyeViewPerfProbe.cs` | 충돌·성능 테스트 전용 |
| `scripts/u15` (보정 재질 정적 렌더), `u16`·`u17` (점 원인 디버그) | |
| `scripts/u18` (충돌 테스트), `u19` (최종 영상), `u20` (성능), `u21` (MSAA 없음) | |
| `scripts/t86_eye_v6j_final_videos.py` | 최종 영상·튐 지표 |
| `EYE_V6J_INTEGRATION_KO.md` | 최종 모델 통합 정리 |
