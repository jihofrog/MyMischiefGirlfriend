# REPORT 20 — MainGirlfriend Race3D v1 정식 베이스라인 통합 (2026-11-13)

## 결론

- 새 정식 베이스라인 `MainGirlfriend_Race3D_v1` 을 만들었다.
  - 기준: 사용자가 승인한 v6j (v5g 헤어 + v6j 눈·얼굴)
  - Blender: `Models/MainGirlfriend_Race3D_v1.blend`
  - Unity: `Art/Characters/MainGirlfriend/Model3D/` (FBX·프리팹), `Scripts/Characters/Avatar3D/` (EyeViewController), `Art/Shaders/Character/` (셰이더 5종)
- 속눈썹 1 px 점선을 고쳤다. v6j 와 다른 곳은 `Eye_Lash.L/R` 두 메시뿐이다. 헤어·눈꺼풀·안구·머리·셰이프 키 구성은 v6j 그대로다.
- Blender 와 Unity 에서 정면, ±35°, ±45°, Blink, EyeSmile, 시선을 v6j 와 비교했다.
  - 바뀐 곳은 속눈썹 뿌리 줄뿐이다.
  - 닫힌 눈(Blink 35°)의 틈은 거의 사라졌다.
  - 먼 눈의 점선은 약 70 % 줄었다.
  - 정면 점선은 확대 화면에서 사라졌다.
- 기존 Blender 원본, v5g·v6j 실험 파일, Unity 메인 씬·프리팹·아이템 시스템, `Mobile_RPAsset` 은 바뀌지 않았다 (해시 확인).
- 이 베이스라인은 얼굴·헤어 중심이다. 몸은 블록아웃이고 리그가 없다. 전신과 공통 리깅은 별도 단계다.

## 1. 속눈썹 1 px 점선: 원인과 수정

**원인 확인:**
- Unity 에서 눈꺼풀·머리·안구를 단색으로 바꿔 렌더했다 (`EyeViewDeviceTest` 의 `debugmats` 옵션).
- 속눈썹 텍스처의 알파를 띠의 행·열별로 쟀다.

| 장면 | 원인 |
|---|---|
| Blink (닫힌 눈) | 밝은 틈 108개 중 거의 전부가 눈꺼풀 피부다. 띠 맨 아래 행(뿌리)이 가리키는 텍스처 알파가 많은 열에서 0.02~0.42 였다. 그래서 띠 아래쪽 약 12~25 % 가 투명했다. |
| 정면 | 띠의 실제 아래 끝이 안구의 검은 테두리보다 약 0.3 mm (이 화면 배율에서 1 px) 위에서 끝난다. 그 사이로 안구의 밝은 부분이 보였다. |

REPORT_19 에서 제안한 "0.1~0.2 mm 겹침" 은 화면 1 px(약 0.33 mm)보다 작아 부족했다.

**수정 (`Models/Race3D/scripts/race3d_v1_build.py`):**

| 단계 | 내용 | 결과 |
|---|---|---|
| UV 보정 | 뿌리 행 UV 를 띠 위쪽으로, 텍스처 알파 0.9 이상인 첫 위치 + 1/32 까지 옮긴다. 이웃 열 사이 구간도 검사한다. 범위는 u −1.0~1.6 이다 (u = 홍채 반지름 단위, 눈꼬리 flick 제외). | 왼쪽 59열·오른쪽 52열 수정. 뿌리 가장자리 투명 비율 약 24 % → 1.2 % |
| 겹침 | 뿌리·덧단 행을 모든 셰이프 키에서 각 키의 띠 방향(2행 → 1행)으로 0.4 mm 내린다. 양 끝에서 줄어든다. | 정면 점선 제거. 안구 테두리(약 2.6 mm) 안에 머문다. |

0.6 mm 에 범위를 눈꼬리(u 2.0)까지 넓힌 조건도 시험했다. 추가 효과가 없고 꼬리 모양만 더 바뀌어 0.4 mm 로 정했다.

## 2. Blender 검증 (v6j 와 같은 카메라·조명·포즈, t48)

![Blender v6j 대 Race3D_v1](/Users/jjeong/UnityProjects/MyMischiefGirlfriend/BlenderSource/Characters/MainGirlfriend/Experiments/ToonTest_01/renders/compare_race3d_v1_blender.png)

| 항목 | 결과 |
|---|---|
| 렌더 | 222장 (정면·±15~±90°, 시선 6종, Blink·Blink50·EyeSmile·Surprise). 모두 v6j 와 짝을 맞춰 비교했다. |
| 4배 확대 눈 렌더의 밝은 점 | 78장 합계 752 → 431 |
| Blink 35° 가까운 눈 | 55 → 8 |
| 얼굴 전체(1배) 평균 차이 | 0.04 / 255 이하. 차이는 속눈썹 뿌리 줄에만 있다. |
| 형상·셰이프 키 | `Eye_Lash.L/R` 외에는 v6j 와 같다 (정점·키·UV·재질·변환 해시 비교) |

수치: `Models/Race3D/spec/race3d_v1_blender_vs_v6j.json`

## 3. Unity 검증 (플레이 모드, 실제 PlayerLoop 경로)

**조건:**
- 검증 장면: `Assets/_Experiments/ToonTest_01/Race3DCheck/Race3DCheck.unity`
- 실험 v6j 프리팹과 정식 Race3D_v1 프리팹을 같은 카메라로 찍었다 (1080×2340, MSAA 4×).
- 재질은 캐릭터마다 인스턴스로 만들었다. 그래서 재질 에셋은 바뀌지 않는다.

![Race3D_v1 Unity 검증](/Users/jjeong/UnityProjects/MyMischiefGirlfriend/BlenderSource/Characters/MainGirlfriend/Experiments/ToonTest_01/renders/race3d_v1_unity_sheet.png)

![속눈썹 경계 v6j 대 Race3D_v1](/Users/jjeong/UnityProjects/MyMischiefGirlfriend/BlenderSource/Characters/MainGirlfriend/Experiments/ToonTest_01/renders/compare_race3d_v1_unity_lash.png)

| 항목 | 결과 |
|---|---|
| 컨트롤러 | 정식 `MMG.Characters.Avatar3D.EyeViewController` 가 매 프레임 합성했다. 루프는 DirectorLateUpdate 뒤에 설치됐고, 대체 합성 0, 외부 덮어쓰기 0 이었다. |
| 각도 보정 | ±35°·±45° 에서 먼 눈 보정 1.00, 가까운 눈 0, 정면 0. v6j 와 같다. |
| 속눈썹 아래 밝은 틈이 있는 열 | 정면 13 → 10, +35° 66 → 18, −35° 60 → 16 |
| Blink 35° 경계 밝은 화소 | 124 → 40 |
| 바뀐 영역 | 모든 장면에서 속눈썹 뿌리 줄(y 1076~1218)뿐이다. 평균 차이 0.06 / 255 이하 |
| 메시 | 정점 75,725 → 75,727 (UV 분리 2개), 삼각형 146,366 그대로, BlendShape 47개 |

수치: `Models/Race3D/spec/race3d_v1_unity_vs_v6j.json`, `race3d_v1_unity_lash_sliver.json`

## 4. 남은 문제

| 항목 | 내용 |
|---|---|
| 먼 눈 꼬리 쪽 세로 점선 | ±35° 먼 눈의 눈꼬리 쪽에 v6j 와 같은 1 px 세로 점선이 남아 있다. 각도 보정 키가 눈꺼풀을 덮을 때 눈꺼풀 가장자리와 안구 사이에서 생긴다. 속눈썹 수정과 관계없다. 새 눈 구조를 만들지 않는다는 지시에 따라 고치지 않았다. |
| 안구 재질 공유 | 컨트롤러가 시선 값을 재질 에셋에 직접 쓴다. 같은 프리팹을 여러 명 쓰면 시선이 같아진다. 조립 단계에서 인스턴스 재질이나 MaterialPropertyBlock 으로 바꿔야 한다. |
| 실험 폴더 의존 | 다음 스크립트가 실험 폴더의 공통 모듈(`eye_v6_common.py`)과 스펙 JSON 을 읽기 전용으로 쓴다. 정식 파이프라인으로 옮길 때 함께 옮긴다. |
| Android | 이번 변경은 속눈썹 UV 와 정점 2개뿐이다. 그래서 Android 성능은 REPORT_19 와 같다고 보고 실기기 재측정은 하지 않았다. 리그가 들어간 전신 모델에서 다시 잰다. |
| MSAA | 사용자 지시대로 `Mobile_RPAsset` 은 MSAA 끔, RS 0.8 그대로다 (권장값은 REPORT_19). |
| 이름 규칙 | 오브젝트 이름은 실험 이름(`Blockout_*`, `Eye_*`)을 그대로 쓴다. 05 문서 10장의 스켈레톤·몸 부위 이름은 전신·리깅 단계에서 적용한다. |

## 5. 변경 파일 목록

### 새로 만든 파일 (Blender)

| 경로 | 내용 |
|---|---|
| `BlenderSource/Characters/MainGirlfriend/Models/MainGirlfriend_Race3D_v1.blend` | 정식 베이스라인 |
| `Models/Race3D/textures/*.png` (5) | v6j 텍스처 사본 (.blend 가 상대 경로로 참조) |
| `Models/Race3D/scripts/race3d_v1_build.py` | v6j → Race3D_v1 (속눈썹 수정, 텍스처 이전, 참조 이미지 경로 수정) |
| `Models/Race3D/scripts/race3d_v1_export_fbx.py` | FBX 내보내기 (t29 규칙 그대로) |
| `Models/Race3D/scripts/race3d_v1_render_check.py` | Blender 검증 렌더 (t48 그대로) |
| `Models/Race3D/scripts/race3d_v1_unity_assets.cs` | Unity 재질·텍스처 설정·프리팹 생성 |
| `Models/Race3D/spec/race3d_v1_*.json` | 빌드 기록, Blender·Unity 비교 수치 |

### 새로 만든 파일 (Unity)

| 경로 | 내용 |
|---|---|
| `Assets/_Game/Art/Characters/MainGirlfriend/Model3D/MainGirlfriend_Race3D_v1.fbx` | 정식 FBX |
| `Model3D/MainGirlfriend_Race3D_v1.prefab` | FBX 의 변형 프리팹. 재질 16개, `EyeViewController`, `EyeCentre.L/R` |
| `Model3D/Materials/*.mat` (16) | `M_MainGirlfriend_*`, `M_hair_bob_01_01`, `M_acc_head_hairclip_x_01_01` |
| `Model3D/Textures/*.png` (5) | 속눈썹·안구 좌우, 볼 터치 |
| `Assets/_Game/Scripts/Characters/Avatar3D/` | `MMG.Characters.Avatar3D.asmdef`, `EyeViewController.cs`, `EyeViewLoop.cs` |
| `Assets/_Game/Art/Shaders/Character/` | `MMG/Character/Toon`, `ToonHair`, `Unlit`, `EyeBall`, `EyeLash` |

### 새로 만든 파일 (실험·검증용)

| 경로 | 내용 |
|---|---|
| `Assets/_Experiments/ToonTest_01/Runtime/TestOnly/Race3DCheck.cs` | 실험 v6j 와 Race3D_v1 비교 드라이버 |
| `Assets/_Experiments/ToonTest_01/Race3DCheck/Race3DCheck.unity` | 검증 장면 |
| `renders/race3d_v1_f6_*.png`, `renders/race3d_v1_unity/`, `renders/compare_race3d_v1_*.png`, `renders/race3d_v1_unity_sheet.png` | 검증 렌더·시트 |
| `renders/android/editor_rt*/` | Unity Editor 대 Android 비교 렌더, 단색 진단 렌더 |

### 수정한 기존 파일

| 경로 | 수정 |
|---|---|
| `Docs/Architecture/00_Architecture.md` | 로드맵 8단계에 얼굴·헤어 베이스라인 결정 추가 |
| `Docs/Architecture/05_CharacterItemSystem.md` | 10장에 Race3D_v1 베이스라인 메모 추가 |
| `EYE_V6J_INTEGRATION_KO.md` | 통합 결과·수정 방식·위험 갱신 |
| `REPORT_19_EYE_V6J_ANDROID_KO.md` | 0.1~0.2 mm 제안 정정 메모, 사용자 결정 기록 |
| `Assets/_Experiments/ToonTest_01/Runtime/MMG.Experiments.EyeView.asmdef` | `MMG.Characters.Avatar3D` 참조 추가 (검증 드라이버용) |
| `Runtime/TestOnly/EyeViewDeviceTest.cs` | 다음 세 가지를 추가했다. 기기 테스트 동작은 그대로다. |

`EyeViewDeviceTest.cs` 에 추가한 것:
- `rtcapture`: Editor 비교 캡처
- `debugmats`: 단색 진단
- 종료 시 URP MSAA·RS 원래 값으로 복원

**참고:** 에디터에서 Android 테스트 장면을 실행하는 동안, 실험 재질 `AndroidTest/Materials/MMGExp_AnimeToonEyeV6d*.mat` 에 시선·조명 값이 저장됐다. 테스트가 매 프레임 다시 쓰는 값이라 결과에는 영향이 없다.

### 바뀌지 않은 것 (해시 확인)
- `MG_ToonTest_01_v6j.blend`, `MG_ToonTest_01_v5g_temple.blend`
- `Models/MainGirlfriend_Base/Body_v1/Face_v1/Face_v2/Modeling.blend`
- `Assets/Settings/Mobile_RPAsset.asset`, `PC_RPAsset.asset`
- `Assets/_Game/Scenes/*`, `Assets/_Game/Prefabs/*`
- Cubism·PSD·아이템 시스템(`Scripts/Data`, `Scripts/Appearance`)·DB

## 6. 다음 단계 (별도 승인)

1. 전신 제작과 공통 리깅. 05 문서 10장 `skel_chibi_f_v1`. 머리 본에 `EyeViewController.head` 를 연결하고 ±35° 먼 눈 판정을 확인한다.
2. 조립 단계(`Avatar3DRenderer`)에서 안구 재질을 인스턴스나 MaterialPropertyBlock 으로 바꾼다.
3. 재생 단계에서 MSAA 를 결정하고 Timeline 패키지를 설치한다. 리그 모델로 Android 를 다시 잰다.
