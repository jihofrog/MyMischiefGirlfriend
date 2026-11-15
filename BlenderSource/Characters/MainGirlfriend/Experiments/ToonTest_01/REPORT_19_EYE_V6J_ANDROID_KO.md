# REPORT 19 — v6j 눈 Android 실기기 검증 (2026-11-13)

## 결론

- **기기·빌드:** v6j 눈은 Galaxy S24(SM-S921U, Android 14, Adreno 750 Vulkan)에서 빌드·설치·실행에 성공했다.
- **화질:** 네 가지 렌더 설정이 모두 실제로 적용됐다. 기기 화면은 Unity Editor 렌더와 색이 같았다.
- **성능:** 1명과 12명 모두 120 fps 를 유지했다. 눈 보정 컨트롤러 비용은 12명일 때 0.19 ms 다.
- **안정성:** 아래 항목 전부에서 오류 0건이다.
  - 앱 시작·종료, 씬 재진입, 백그라운드 복귀
  - Animator, PlayableDirector, 카메라 전환, 위·아래 카메라
  - 중복 컨트롤러, PlayerLoop 교체
- **남은 결함:** 속눈썹 아래 경계의 1 px 밝은 점선 하나다. Editor 에서도 같아서 Android 고유 문제가 아니다.
- **권장 설정:** MSAA 4×, Render Scale 0.8.
- **LOD:** 눈 보정 LOD 는 이득이 15 µs 안팎이라 적용하지 않는다.
- **원본 보존:** 원본 Blender, 메인 씬, 프리팹, Cubism, PSD, 아이템 시스템, DB 는 수정하지 않았다. 빌드 때문에 바뀐 프로젝트 설정은 모두 되돌렸다.

## 1. 기기와 연결

| 항목 | 값 |
|---|---|
| 기기 | Samsung Galaxy S24 `SM-S921U` (e1q), 시리얼 `RFCX70D90WJ`, USB |
| OS | Android 14 / API 34 (`UP1A.231005.007`) |
| GPU | Adreno 750, Vulkan 1.1 |
| CPU / RAM | ARM64 8코어 / 7.1 GB |
| 화면 | 1080×2340, 120 Hz |
| ADB | `/Users/jjeong/Library/Android/sdk/platform-tools/adb`, 1.0.41 (35.0.2). `adb devices -l` 에 `device` 상태로 1대 |
| 환경 변수 | `ANDROID_HOME=/Users/jjeong/Library/Android/sdk`, `ANDROID_SDK_ROOT` 는 비어 있다 (ADB 사용에는 영향 없음) |

- ADB 서버는 처음부터 정상이었다. 그래서 종료하거나 다시 시작하지 않았다.
- zsh 변수에 넣은 `-s` 옵션이 나뉘지 않는 문제가 있었다. 대신 `ANDROID_SERIAL` 로 기기를 지정했다.

## 2. 빌드와 실행

| 항목 | 값 |
|---|---|
| 씬 | `Assets/_Experiments/ToonTest_01/AndroidTest/EyeViewAndroidTest.unity` (독립 테스트 씬) |
| 내용 | v6j 프리팹 사본, 수정된 눈 셰이더, `EyeViewController` + `EyeViewLoop`, 카메라 자동 회전, 표정 테스트, 12명 배치 |
| 패키지 ID | `com.mmg.eyeviewtest` (본 게임 ID 와 별도) |
| 결과 | 첫 빌드 성공 (147 s, 오류 0), 수정 후 재빌드 성공 (22 s, 오류 0). Development 빌드 |
| APK | `/Users/jjeong/UnityProjects/EyeViewTestBuild/eyeviewtest.apk` (프로젝트 밖) |
| 실행 | 설치·실행 성공. 시작·종료 3회 반복에서 크래시 0 |

**빌드 중 잠시 바꾼 설정 (모두 복원 확인):**
- 바꾼 항목:
  - 빌드 대상 macOS → Android
  - Android 패키지 ID → `com.mmg.eyeviewtest`
  - FrameTimingStats 켬
  - Development 켬
- 씬은 `BuildPlayerOptions` 로만 지정했고 `EditorBuildSettings` 는 건드리지 않았다.
- 빌드가 다음 파일을 다시 쓰거나 새로 만들었다. 전부 빌드 전 상태로 되돌렸다.
  - `GraphicsSettings`
  - `UnityConnectSettings`
  - URP 전역 설정
  - `Mobile_RPAsset` 프리필터 값
  - NotoSansKR SDF 동적 아틀라스
  - Addressables `Android/` 폴더
  - `ScriptableBuildPipeline.json`
- 확인 방법:
  - `ProjectSettings.asset`, `Mobile_RPAsset.asset`, `EditorBuildSettings.asset` 의 해시가 빌드 전 백업과 같다.
  - Unity 에서 읽은 값도 원래와 같다: macOS 대상, 원래 패키지 ID, FrameTimingStats 끔, Development 끔, Mobile MSAA 1 / RS 0.8.
  - 기록: `spec/android_build_temp_settings.json`
- `Mobile_RPAsset` 의 렌더러 목록과 `PC_RPAsset` 은 이번 작업 전부터 바뀌어 있던 사용자 변경이라 그대로 두었다.

## 3. 화질 비교 (네 가지 설정)

**캡처 방법:**
- 앱이 촬영 준비 파일을 쓰면 호스트가 `adb exec-out screencap` 으로 실제 화면(1080×2340)을 받는다.
- 앱 안의 `ScreenCapture` 는 Vulkan 에서 색이 어둡게 틀어져 쓰지 않았다 (배경 150 vs 실제 237).

**설정 적용 확인:**

| 설정 | 앱이 읽은 URP 값 | 실제 렌더 해상도 | 지원 여부 |
|---|---|---|---|
| A | MSAA 1, RS 0.80 | 864×1872 | 지원 |
| B | MSAA 2, RS 0.80 | 864×1872 | 2× 지원 |
| C | MSAA 4, RS 0.80 | 864×1872 | 4× 지원 |
| D | MSAA 4, RS 1.00 | 1080×2340 | 4× 지원 |

- 지원하지 않는 조합은 없었다.
- MSAA 가 실제로 켜졌는지는 머리 윤곽에서 확인했다. 배경과 머리 사이 경계 화소 중 중간색 화소의 비율을 셌다.
  - MSAA 없이 원래 해상도로 렌더한 Editor 렌더: 6 %
  - 기기 D: 62 %
  - Editor D: 63 %
- A~C 는 0.8 배율을 화면 크기로 늘리는 과정에서 모든 윤곽이 부드러워진다. 그래서 이 방법으로는 MSAA 효과만 따로 떼어 볼 수 없다.

![눈 비교](/Users/jjeong/UnityProjects/MyMischiefGirlfriend/BlenderSource/Characters/MainGirlfriend/Experiments/ToonTest_01/renders/compare_eye_v6j_android_eyes.png)

![표정·머리 비교](/Users/jjeong/UnityProjects/MyMischiefGirlfriend/BlenderSource/Characters/MainGirlfriend/Experiments/ToonTest_01/renders/compare_eye_v6j_android_expr_hair.png)

(200×200 px 영역을 2배 확대했고, 화소를 보간하지 않았다. 원본 캡처: `renders/android/screens_r2/`, Editor 참조: `renders/android/editor_rt/`)

| 항목 | 결과 |
|---|---|
| 정면 눈·속눈썹 | A 는 속눈썹 윗선이 흐리고 끝이 약간 계단진다. B·C 는 흐림이 같고 계단이 줄어든다. D 가 가장 선명하고 윤곽이 매끄럽다. |
| ±35° 먼 눈 | 네 설정 모두 보정 키가 정상 동작한다. 먼 쪽 흰자가 덮이고 가까운 눈은 그대로다. 테두리 선명도만 다르다. |
| ±45° 먼 눈 | +45° 는 정상이다. −45° 는 먼 눈 일부가 옆머리에 가려진다 (머리 배치 때문이며 눈 결함이 아니다). |
| Blink / EyeSmile | 35°에서 닫힌 속눈썹 띠와 EyeSmile 곡선이 네 설정 모두 정상이다. 안구는 드러나지 않는다. |
| 앞머리·쌍꺼풀 선 | A 는 쌍꺼풀 선이 뭉개진다. C·D 는 1 px 선이 끊기지 않는다. 머리 가닥 끝의 계단은 D 에서 가장 적다. |
| 속눈썹 안 살색 점 | 아래 "남은 결함" 참고. 띠 내부의 큰 살색 점은 다시 생기지 않았다. 속눈썹 **아래 경계**에 1 px 밝은 점선이 남는다. |

**설정별 차이 (D 대비, 경계 화소 중 차이 > 24 인 비율):**

| 설정 | 비율 |
|---|---|
| A | 6.2~7.6 % |
| B | 6.4~7.7 % |
| C | 6.1~7.4 % |

차이는 대부분 0.8 배율 보간에서 온다. 0.8 배율에서 MSAA 2× 와 4× 의 차이는 작다.

### Unity 셰이더와 Android GPU 의 차이 (D, 같은 카메라)

- 색은 같다.
  - 배경: (237,237,242) / (237,237,240)
  - 피부: (240,186,168) / 같음
  - 홍채: (63,26,24) / 같음
- 전체 평균 차이는 1.5~1.8 / 255 다. 차이가 큰 화소는 세 종류뿐이다.
  - 머리 정수리 하이라이트의 고주파 줄무늬 패턴 (머리 하이라이트 셰이더의 정밀도 차이로 추정)
  - 속눈썹 A2C 윤곽의 샘플 패턴
  - 기기 화면 오른쪽 아래의 "Development Build" 표시
- 위 세 가지 외에 셰이더 결과가 달라지는 곳은 보이지 않았다.

## 4. 성능 (1명 / 12명)

**측정 조건:**
- Development 빌드, 수직 동기 120 Hz, 각 조건 20 초 (2,400 프레임). 기기는 충전 중이었다 (배터리 29~31 %).
- 측정 도구:
  - CPU·GPU 시간: `FrameTimingManager`
  - 눈 보정 컨트롤러: 컨트롤러 안의 `Stopwatch`
  - 스키닝: `ProfilerRecorder` 마커
- 1명은 카메라가 머리 둘레를 ±60° 로 돈다.
- 12명은 3×4 격자에 배치하고 머리를 ±60° 로 돌린다. 카메라 거리 4.2 m, 화면 폭 3.0 m 로 고정했다. 이때 화면상 두 눈 사이 거리는 53 px 다.

### 1명

| 설정 | FPS | 프레임 평균 / P95 (ms) | CPU 메인 평균 / P95 | GPU 평균 / P95 | 눈 보정 컨트롤러 | UpdateAllSkinnedMeshes | 12.5 ms 초과 프레임 |
|---|---|---|---|---|---|---|---|
| A | 120.0 | 8.33 / 8.83 | 2.66 / 3.45 | 2.54 / 2.74 | 45.9 µs | 0.055 ms | 1 |
| B | 120.0 | 8.33 / 8.77 | 2.77 / 3.60 | 2.80 / 3.03 | 51.6 µs | 0.073 ms | 0 |
| C | 120.0 | 8.33 / 8.71 | 2.52 / 3.42 | 3.30 / 3.54 | 45.9 µs | 0.066 ms | 0 |
| D | 120.0 | 8.33 / 8.70 | 2.58 / 3.47 | 4.11 / 4.35 | 47.0 µs | 0.067 ms | 1 |

### 12명

| 조건 | FPS | 프레임 평균 / P95 | CPU 메인 평균 / P95 | GPU 평균 / P95 | 눈 보정 컨트롤러 12개 | GPU 일괄 BlendShape | UpdateAllSkinnedMeshes | 16.7 ms 초과 프레임 |
|---|---|---|---|---|---|---|---|---|
| 보정 켬, A | 120.0 | 8.34 / 9.45 | 4.56 / 5.74 | 6.65 / 7.34 | 194 µs | 0.102 ms | 0.111 ms | 1 |
| 보정 켬, C | 119.9 | 8.34 / 8.87 | 4.33 / 5.64 | 6.80 / 7.36 | 187 µs | 0.087 ms | 0.114 ms | 1 |
| 보정 끔, C | 120.0 | 8.34 / 8.68 | 4.50 / 5.60 | 6.93 / 8.28 | 172 µs | 0.033 ms | 0.091 ms | 1 |
| 4프레임마다 갱신, C | 120.0 | 8.33 / 8.61 | 4.46 / 5.63 | 6.96 / 7.37 | 179 µs | 0.095 ms | 0.120 ms | 0 |

- 12명의 D 조건은 측정하지 않았다.
- `MeshSkinning.Skin` 마커는 1명일 때 0.18~0.28 ms, 12명일 때 1.6~2.0 ms 다. 이 값은 워커 스레드를 포함한 합계라서 메인 스레드 시간과 다르다.

### 메모리 (캐릭터 1종)
- 메시 38개 = 5,180 KB. 이 중 눈꺼풀·속눈썹이 1,030 KB 다 (BlendShape 47개).
- 텍스처 5개 = 1,835 KB.
- 앱 전체: 할당 72.9 MB, 예약 540.7 MB, 그래픽 드라이버 132.8 MB.
- 12명은 같은 메시와 텍스처를 공유한다. 인스턴스별 스키닝 버퍼 메모리는 따로 측정하지 않았다 (미측정).

### 발열 (12명, C, 300 초)
- 5초 단위 FPS 최저 117.4, P95 최대 9.77 ms 였다. GPU 시간은 7.12 → 7.14 ms 로 거의 변하지 않았고, 프레임 저하로 이어지지 않았다.
- 기기 온도 (`dumpsys thermalservice` 의 현재 HAL 값):
  - 피부: 38.7 → 44.1 °C
  - AP: 43.0 → 53.2 °C
  - 열 상태: 2 (moderate) → 270 초 부근에서 3 (severe)
- 충전 중 측정이라 발열이 실제 사용보다 높게 나왔을 수 있다.
- 전력은 얻을 방법이 없어 **미측정**이다. 추정값으로 바꾸지 않았다.

## 5. 눈 보정 LOD (12명)

![LOD 비교](/Users/jjeong/UnityProjects/MyMischiefGirlfriend/BlenderSource/Characters/MainGirlfriend/Experiments/ToonTest_01/renders/compare_eye_v6j_android_lod12.png)

- **화면 차이:** 12명 거리에서 보정을 켜고 끈 차이는 캐릭터당 먼 눈 몇 화소뿐이다 (전체 차이 > 24 화소 300개).
- **성능 이득:**
  - 컨트롤러 시간은 15 µs (보정 끔), 8 µs (4프레임마다 갱신) 줄었다.
  - GPU 일괄 BlendShape 는 0.05 ms 줄었다.
  - 하지만 CPU 메인 평균과 GPU 프레임 시간은 줄지 않았다 (측정 오차 범위).
- Blink·기본 표정은 세 조건 모두 정상이다.
- **판정:** 실제 화면 차이와 성능 차이가 모두 의미 없을 정도로 작다. 최적화를 권장하지 않는다. 기본값은 항상 켬이다 (`lodMinEyePixels` 0, `viewUpdateInterval` 1). 기능은 코드에 남겨 저사양 기기 측정 후 다시 판단한다.

## 6. PlayerLoop 와 안정성 (실기기)

**실행 순서:**
- 실행 순서는 `PostLateUpdate: … DirectorLateUpdate > EyeViewLoop > ScriptRunDelayedDynamicFrameRate …` 로 확인했다.
- 모든 LateUpdate·Animator·Director 뒤이고, 스키닝 전이다.

**판정 기준:** 각 항목은 렌더 직전 검사로 판정했다. 검사 항목은 다음 네 가지이고, 아래 모든 경우에서 네 값 모두 0 이었다.
- 보정 키 덮어씀
- Blink 100 % 를 넘는 닫힘
- 합성 없이 지나간 프레임
- Blink 불일치

| 시험 | 결과 |
|---|---|
| 기준 상태 | 정상 |
| 다른 스크립트가 보정 키·Blink 를 매 프레임 덮어씀 (실행 순서 −30000 / +30000) | 120회 덮어쓰기를 감지했고 결과는 컨트롤러 값 유지 |
| Animator → 컨트롤러 필드 | Blink 0~1 정상 |
| PlayableDirector (Timeline 대체) | 재생 중 Blink 0~1 정상 |
| 카메라 전환 (35° 카메라 / −45° 카메라 / 없음 → Camera.main) | 먼 눈 판정이 카메라마다 맞음 |
| 카메라 위·아래 (pitch −80~+80, yaw 35) | ±40° 까지 보정 유지, ±60° 에서 0.74 / 0.83, ±80° 에서 0 (서서히 꺼짐) |
| 같은 렌더러에 컨트롤러 2개 | 두 번째는 등록 거부·비활성화, 활성 드라이버 1개 |
| 켜기/끄기 200회 | 활성 드라이버 1개 |
| 외부에서 PlayerLoop 교체 | 감시 장치가 다시 설치했다. 그 사이 2프레임은 LateUpdate 대체 합성으로 처리됐다. 합성 없이 지나간 프레임은 1 |
| 씬 재진입 3회 | 설치 횟수 2 로 고정, 활성 드라이버 1 |
| 백그라운드 → 복귀 | 루프 유지, 정상 |
| 앱 시작·종료 3회 | 크래시 0, 매번 DirectorLateUpdate 뒤에 설치 |

- Timeline 패키지(`com.unity.timeline`)는 프로젝트에 설치되어 있지 않다. 그래서 같은 실행 경로를 쓰는 `PlayableDirector` + 사용자 PlayableAsset 으로 대신 시험했다. 패키지 설치는 재생 단계에서 사용자 확인 후 진행한다.
- 이번에 추가한 안전 장치:
  - 렌더러 소유권 확인. 중복 컨트롤러를 거부하고 오류를 로그로 남긴다.
  - PlayerLoop 감시 후 다시 설치하고, 그 사이는 LateUpdate 로 대신 합성한다.
  - 정해진 카메라가 꺼지면 `Camera.main` 을 쓴다.
  - NaN 방지.
  - 씬·도메인 재시작 시 정적 상태를 초기화한다.

## 7. v6j 에 남은 화면 결함

1. **속눈썹 아래 경계의 1 px 밝은 점선.** 위 속눈썹 띠와 안구 사이에서 가끔 밝은 화소가 보인다 (정면·먼 눈·닫힌 눈).
   - 측정값: 아래위가 어두운 1 px 밝은 화소 수

     | 장면 | A | C | D | Editor D |
     |---|---|---|---|---|
     | 정면 | 36 | 21 | 85 | 79 |
     | Blink 35° | 61 | 39 | 109 | 111 |

   - Editor 와 같으므로 Android GPU 문제가 아니라 모델·셰이더 경계 문제다.
   - RS 1.0 에서 더 선명하게 보이고, RS 0.8 에서는 흐려져 덜 보인다.
   - 원래 크기에서는 겨우 보이는 수준이다.
   - 새 눈 구조 없이 통합 단계에서 고칠 수 있다. 방법은 두 가지 중 하나다.
     - 속눈썹 띠 아래쪽을 0.1~0.2 mm 더 내려 겹치게 한다. (이후 정정: 이 화면 배율에서 1 px 은 약 0.33 mm 라 부족했다. 실제 수정은 뿌리 행 UV 보정과 0.4 mm 겹침이다. REPORT_20 참고)
     - 눈꺼풀 피부의 띠 뒤쪽 면을 어둡게 한다.
2. **A (MSAA 끔) 의 계단·흐림.** 설정 문제다. 4× 로 해결된다.
3. **머리 하이라이트 줄무늬.** 기기와 Editor 의 패턴이 조금 다르다. 머리 셰이더 문제이고 눈과는 관계없다.

## 8. 권장 렌더 설정

| 용도 | MSAA | Render Scale | 근거 |
|---|---|---|---|
| 레이스 기본 | **4×** | **0.8** | 12명에서 A 대비 GPU 차이는 +0.15 ms 다. 쌍꺼풀·속눈썹 끝 계단이 줄고, 1 px 점선은 가장 덜 보인다 (정면 기준 A 36, B 28, C 21). |
| 저사양 대안 | 2× | 0.8 | 1명 기준으로 4× 보다 GPU 0.5 ms 적다. 0.8 배율에서는 4× 와 화질 차이가 작다. |
| 근접 1명 연출 (선택) | 4× | 1.0 | 가장 선명하다 (1명 GPU 4.1 ms). 12명 D 는 미측정이라 기본값으로는 권하지 않는다. |

- 실제 적용은 `Mobile_RPAsset` 의 MSAA 1 → 4 변경이다. 프로젝트 설정 변경이므로 승인 후 진행한다.
- 이번 기기는 상위 기종이다. 중·저가 Adreno·Mali 기기는 측정하지 않았다.

## 9. 최종 캐릭터 통합 가능 여부

통합할 수 있다고 판단한다. 근거는 다음과 같다.
- 성능, 안정성, 설정 적용, Unity 와 Android 일치를 실기기에서 확인했다.
- 남은 결함은 1 px 경계 하나다. 통합 단계에서 처리할 수 있다.

**조건:**
- 위의 MSAA 4× 설정을 승인받아야 한다.
- 최종 모델에 머리 본을 연결한 직후 ±35° 먼 눈 방향을 확인해야 한다.

**사용자 결정 (2026-11-13):**
- 최종 통합을 승인했다. 속눈썹 1 px 점선 수정을 포함한다.
- MSAA 변경은 재생 단계에서 결정한다. 지금은 `Mobile_RPAsset` 을 바꾸지 않는다.

## 10. 통합 때 바꿀 파일

### Blender (최종 캐릭터 원본, 승인 후)
1. `scripts/t51_eye_v6f.py`: 눈꺼풀 경계를 만든다 (v6f_A 기반이면 이미 들어 있다).
2. `scripts/t72_eye_v6i_close.py`: `ViewFar*`·`ViewSide*` 보정 키를 만든다.
3. `scripts/t81_eye_v6j_lash.py` (`V6J_MODE=keep`): 보정 키 안의 속눈썹 꼬리를 처리한다.
4. 1 px 점선 처리: 속눈썹 띠 아래 가장자리를 겹치게 하거나 피부 뒤쪽 면을 어둡게 한다. 작은 수정이고 새 구조를 만들지 않는다.
5. `scripts/t29_eye_export_fbx.py` 규칙으로 FBX 를 내보낸다.

### Unity (승인 후)

| 실험 파일 | 최종 위치 |
|---|---|
| `Runtime/EyeViewController.cs`, `Runtime/EyeViewLoop.cs` | `Assets/_Game/Scripts/Characters/Avatar3D/` (아키텍처 문서의 `MMG.Characters.Avatar3D` 모듈, URP Runtime 참조) |
| `MMGExp_AnimeToonEyeV6j.shader` (속눈썹 A2C) | 정식 눈 셰이더 |
| `MMGExp_AnimeToonEyeV6d` (안구), 눈꺼풀 피부 재질 | 정식 재질 |
| 최종 캐릭터 FBX | BlendShapes 켬, 노멀·BlendShape 노멀 가져오기 |
| 캐릭터 프리팹 | 머리 본에 `EyeViewController` 를 추가한다. 렌더러, 안구, 카메라 연결 |
| 레이스 카메라 전환기 | 전환 때 `viewCamera` 를 지정한다 (없으면 Camera.main) |
| `Assets/Settings/Mobile_RPAsset.asset` | MSAA 1 → 4 (사용자 확인 후) |

`Runtime/TestOnly/*`, `EyeViewTestRig.cs`, `AndroidTest/` 는 옮기지 않는다. 이 실험 폴더에 남긴다.

## 11. 산출물

| 경로 | 내용 |
|---|---|
| `renders/compare_eye_v6j_android_eyes.png` | 눈 화질 비교 |
| `renders/compare_eye_v6j_android_expr_hair.png` | 표정·머리 화질 비교 |
| `renders/compare_eye_v6j_android_lod12.png` | LOD 비교 |
| `renders/android/screens_r2/` | 실기기 화면 캡처 42장 |
| `renders/android/editor_rt/` | Editor 참조 캡처 40장 |
| `renders/android/eyeview_r2/` | 성능 로그·CSV·발열 |
| `renders/android/eyeview/log.txt` | 안정성 로그 |
| `renders/android/host_thermal_r2.csv` | 기기 온도 |
| `renders/android/startstop_log.txt` | 시작·종료 로그 |
| `Assets/_Experiments/ToonTest_01/AndroidTest/` | 테스트 씬·프리팹 사본·재질 |
| `Assets/_Experiments/ToonTest_01/Runtime/TestOnly/EyeViewDeviceTest.cs`, `EyeViewDirectorAsset.cs` | 기기 테스트 코드 |
| `scripts/u22_unity_android_test_assets.cs` | 테스트 에셋 생성 |
| `spec/android_build_temp_settings.json` | 임시 설정 기록 |
