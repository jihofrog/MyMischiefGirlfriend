# v6j 눈 — 최종 모델 통합 정리 (2026-11-13)

v6j 는 얼굴·헤어 정식 베이스라인 `MainGirlfriend_Race3D_v1` 에 통합했다 (REPORT_20). 실험 파일은 그대로 남아 있다.

승인 후보였던 파일: `MG_ToonTest_01_v6j.blend` / `Assets/_Experiments/ToonTest_01/MG_ToonTest_01_v6j_eye.fbx`.

근거 보고서: REPORT_13 (v6f_A), 16 (v6i), 17 (v6j), 18 (마무리 검증), 19 (Android 실기기 검증), 20 (Race3D_v1 통합).

**상태 (2026-11-13):**
- 사용자가 형상, 눈꺼풀 구조, 각도 보정, 런타임 드라이버를 조건부 승인했다.
- Android 실기기 검증을 마쳤다 (REPORT_19).
- 사용자가 최종 통합을 승인했다. 범위는 B안이다: 새 정식 파일을 만들고, 속눈썹 아래 1 px 점선 수정을 포함한다.
- 통합 결과:
  - Blender: `Models/MainGirlfriend_Race3D_v1.blend`
  - Unity: `Art/Characters/MainGirlfriend/Model3D/` (FBX·프리팹), `Scripts/Characters/Avatar3D/`, `Art/Shaders/Character/`
- 점선 수정은 두 가지다. 정점 이동 외에는 v6j 와 같다.
  - 속눈썹 뿌리 행 UV 를 불투명한 위치로 옮긴다.
  - 뿌리 행을 띠 방향으로 0.4 mm 내려 안구 테두리와 겹친다.
  - 처음 제안한 "0.1~0.2 mm" 는 화면 1 px(약 0.33 mm)보다 작아 부족했다. 실제 값은 0.4 mm 다.
- `Mobile_RPAsset` 의 MSAA 변경은 보류했다. 재생 단계에서 결정하므로 지금은 MSAA 끔, RS 0.8 그대로다.
- 이 베이스라인은 얼굴·헤어 중심이다. 몸은 블록아웃이고 리그가 없다. 전신 제작과 공통 리깅은 별도 단계다.

## 1. 변경 파일 목록

### Blender (최종 캐릭터 원본에 할 일)

| 순서 | 실험 스크립트 | 최종 모델에서 할 일 |
|---|---|---|
| 1 | `scripts/t51_eye_v6f.py` (V6F_A) | 눈꺼풀 경계. v6f_A 에 이미 들어 있다. 최종 모델이 v6f_A 기반이 아니면 같은 단계를 실행한다. |
| 2 | `scripts/t72_eye_v6i_close.py` | 보정 키 `ViewFar*`, `ViewSide*` 를 만든다 (Basis·기존 키 불변). |
| 3 | `scripts/t81_eye_v6j_lash.py` (V6J_MODE=keep) | 보정 키 안의 속눈썹 꼬리 처리 |
| 4 | `Models/Race3D/scripts/race3d_v1_build.py` (적용함) | 속눈썹 1 px 점선: 뿌리 행 UV 를 텍스처 알파 0.9 이상 위치로 옮기고, 뿌리·덧단 행을 모든 셰이프 키에서 띠 방향으로 0.4 mm 내린다. 범위는 u −1.0~1.6 이고 양 끝에서 줄어든다. v6j 에서 바뀌는 것은 `Eye_Lash.L/R` 뿐이다. |
| 5 | `scripts/t29_eye_export_fbx.py` 규칙 (`race3d_v1_export_fbx.py` 가 그대로 실행) | FBX 내보내기: Blender TT_Outline 끄기, 머리 정점색 R = 외곽선 가중치, 모디파이어를 키와 함께 굽기 |

**전제 조건 (스크립트가 의존하는 구조):**
- `Eye_Lids.<s>` 는 위·아래 각 nc×7 격자다 (열 우선, 행 0 = 접힘, 행 1 = 가장자리).
- `Eye_Lash.<s>` 는 띠 nb×nr, 아래 속눈썹, 쌍꺼풀 줄 순서다. 커스텀 속성 `mmg_band_cols`, `mmg_band_rows`, `mmg_crease_start` 가 있다.
- 두 메시 모두 `Blink` 키가 있고, 그 중간값이 안구 위 0.1 mm 이상으로 검증되어 있다 (t51 blend_lift).
- 안구는 재질 `Gaze` 회전 방식이다. r30 홍채 상자는 `spec/r30_eye_targets.json` 에 있다.

### Unity

| 실험 파일 | 정식 위치 (적용함) | 비고 |
|---|---|---|
| `Runtime/EyeViewController.cs`, `Runtime/EyeViewLoop.cs` | `Assets/_Game/Scripts/Characters/Avatar3D/` (asmdef `MMG.Characters.Avatar3D`, 참조 없음) | 네임스페이스만 바뀌었고 코드는 같다. 테스트 전용 `Runtime/TestOnly/*`, `EyeViewTestRig.cs` 는 옮기지 않았다. |
| `MMGExp_AnimeToonEyeV6j.shader` (속눈썹) | `Art/Shaders/Character/MMG_Character_EyeLash.shader` (`MMG/Character/EyeLash`) | 내용은 같다. A2C 알파 선명화, 알파 mip 0, `Cull Off`, `_ViewPull` 0.001 m |
| `MMGExp_AnimeToonEyeV6d` (안구) | `MMG_Character_EyeBall.shader` (`MMG/Character/EyeBall`) | `_GazeYaw` 로 시선 |
| `MMGExp_AnimeToonV6`, `AnimeToonHairV2`, `UnlitTex` | `MMG_Character_Toon`, `MMG_Character_ToonHair`, `MMG_Character_Unlit` | 피부·눈꺼풀(외곽선 0)·헤어·얼굴 선 |
| `MG_ToonTest_01_v6j_eye.fbx` | `Art/Characters/MainGirlfriend/Model3D/MainGirlfriend_Race3D_v1.fbx` | 가져오기: BlendShapes 켬, Normals·BlendShape Normals = Import, Generic, 카메라·조명·애니메이션 끔 |
| AndroidTest 재질·텍스처 | `Model3D/Materials/` (16개), `Model3D/Textures/` (5개) | 값은 실기기 검증 재질과 같다. `_LightDir` 기본값은 (0.30, 0.50, 0.81) 이다. |
| 캐릭터 프리팹 | `Model3D/MainGirlfriend_Race3D_v1.prefab` (FBX 의 변형 프리팹) | `EyeViewController` (Fields), `EyeCentre.L/R` |
| `Assets/Settings/Mobile_RPAsset.asset` | (보류) 권장 MSAA 4×, Render Scale 0.8 | 실기기 권장값 (REPORT_19 8장). 재생 단계에서 사용자가 결정 |
| 레이스 카메라 전환기 | (미구현) 전환 때 `viewCamera` 지정 | 비어 있거나 꺼져 있으면 `Camera.main` 을 쓴다 |

## 2. BlendShape 이름

| 메시 | 키 | 기능 |
|---|---|---|
| `Eye_Lids.L`, `Eye_Lash.L` | `Blink`, `EyeSmile`, `Smile`, `Surprise` | 기존 (그대로) |
| | `ViewFarL` | 왼눈이 먼 눈일 때 바깥 흰자를 눈꺼풀로 덮는다 (시선 0) |
| | `ViewFarL_GO` | 같은 보정, 시선이 바깥으로 0.25 rad 일 때의 홍채에 맞춤 |
| | `ViewFarL_GI` | 같은 보정, 시선이 안쪽으로 0.12 rad 일 때의 홍채에 맞춤 |
| | `ViewSideL` | 60° 이상에서 왼눈 일부 감기 (Blink 복사본) |
| `Eye_Lids.R`, `Eye_Lash.R` | 위와 같고 끝 글자만 `R` | |
| `Blockout_Head` | `EyeSmile`, `Smile` | 기존 |

- 전체 47개 (기존 31 + 16).
- 보정 키는 컨트롤러만 쓴다. 애니메이션 클립에 넣지 않는다.
- `ViewSide*` 는 각 눈 렌더러의 `Blink` 를 컨트롤러가 직접 올리면 없앨 수 있다 (−4개, 약 −133 KB). 통합 때 선택한다.

## 3. 드라이버 연결

컨트롤러는 캐릭터마다 하나, 머리 계층에 둔다.

| 필드 | 연결 |
|---|---|
| `head` | 머리 본 (리그가 있는 최종 모델). 실험에서는 모델 루트였다. |
| `faceForwardLocal`, `characterLeftLocal` | 머리 본 로컬 축 기준의 얼굴 앞 / 캐릭터 왼쪽. 실험 FBX 는 (0,0,front), (sx,0,0) 이다. |
| `eyeL`, `eyeR` | 안구 중심 Transform. 머리 본의 자식이다 (실험: `Eye_Ball.*` 범위 중심에 빈 오브젝트). |
| `viewCamera` | 현재 화면 카메라. 레이스 연출의 카메라 전환기가 전환할 때마다 넣어 준다. |
| `renderers` | `Blink`·`EyeSmile`·`Smile`·`Surprise`·보정 키가 있는 SkinnedMeshRenderer 전부 |
| `eyeMaterials` | 안구 재질 인스턴스 (`_GazeYaw`) |
| `inputSource` | `Fields` (권장). Animator 는 컨트롤러의 `blink`, `eyeSmile`, `smile`, `surprise`, `gaze` 필드를 애니메이션한다. 기존 클립이 BlendShape 를 직접 쓰면 `BlendShapes`. |
| `composeAt` | `PlayerLoop` (기본, 변경 금지). `LateUpdate` 는 비교 테스트용이다. |
| `smoothTime` / `cutDegrees` | 0 / 20 으로 시험했다. 감쇠를 넣으면 컷(20° 이상 변화)에서는 즉시 적용된다. |
| 각도 상수 | `farFrom` 20, `farTo` 40, `sideFrom` 50, `sideTo` 65, `sideMax` 0.8, `gazeOut` 0.25, `gazeIn` 0.12, `pitchFadeFrom` 50, `pitchFadeTo` 75 (Blender `eye_v6_common.view_key_values` 와 같다) |

**실행 순서:**
- `EyeViewLoop` 가 PlayerLoop 의 `PostLateUpdate.DirectorLateUpdate` 바로 뒤에 합성 단계를 넣는다 (처음 활성화될 때 1회).
- 이 지점은 모든 LateUpdate·Animator·Timeline 뒤이고, 스키닝·렌더 전이다.
- 다른 시스템이 PlayerLoop 를 교체하면 이 단계가 사라질 수 있다. 이 경우 컨트롤러의 `LateUpdate` 감시가 처리한다.
  - 이전 프레임에 합성 단계가 실행되지 않았으면 `EnsureInstalled()` 로 다시 설치한다.
  - 다시 설치될 때까지는 그 프레임을 직접 합성하고, 횟수를 `FallbackComposes` 에 센다.
  - 실기기 결과: 교체 후 다시 설치됨, 대체 합성 2회, 합성 없이 지나간 프레임 1.
  - 상태 확인은 `EyeViewLoop.Describe()` 로 한다.
- 렌더러 소유권: 같은 SkinnedMeshRenderer 를 다른 활성 컨트롤러가 이미 쓰고 있으면 등록을 거부한다.
  - 거부된 컨트롤러는 오류 로그를 남기고 꺼진다.
  - 렌더러를 나중에 넣어도 합성 때마다 다시 확인한다.
- LOD 필드 `lodMinEyePixels` (0 = 끔), `viewUpdateInterval` (1 = 매 프레임)는 기본값 그대로 쓴다.
  - Android 12명 측정에서 이득이 컨트롤러 15 µs 이하였고, 프레임 시간은 줄지 않았다 (REPORT_19 5장).

**공식 (요약):**
- 눈마다 그 눈에서 카메라로 가는 방향을 머리 공간의 yaw·pitch 로 바꾼다.
- 먼 쪽 눈에만 다음을 적용한다:
  - 가중치 = smoothstep((|yaw| − 20)/20) × pitch 감쇠
  - side = smoothstep((|yaw| − 50)/15) × 0.8 × pitch 감쇠
- k = (1 − Blink)(1 − EyeSmile)
- ViewFar 계열 합 = 가중치 · k · (1 − side). 시선에 따라 `_GO`·`_GI` 로 나눈다.
- ViewSide = side · k

## 4. 예상 위험 요소

| 위험 | 내용 | 대응 |
|---|---|---|
| MSAA 꺼짐 | 프로젝트 URP `m_MSAA: 1`, 모바일 렌더 스케일 0.8 이다. A2C 가 단순 알파 컷이 되어 속눈썹·쌍꺼풀 선·머리카락 가장자리가 계단진다 (`renders/compare_eye_v6j_msaa.png`). | 실기기 권장 MSAA 4× / RS 0.8. 12명 GPU 비용은 +0.15 ms 다 (REPORT_19). RP 설정 변경은 사용자 확인 후. |
| 속눈썹 아래 1 px 점선 | 위 속눈썹 띠와 안구 경계에 밝은 화소가 점선처럼 보였다. Editor·기기에서 같았고, RS 1.0 에서 더 잘 보였다. | Race3D_v1 에서 수정했다 (UV + 0.4 mm 겹침, REPORT_20). 먼 눈 꼬리 쪽 세로 점선은 눈꺼풀 가장자리 문제라 남아 있다. |
| 안구 재질 공유 | 컨트롤러가 `_GazeYaw` 를 `eyeMaterials` 에 직접 쓴다. 프리팹 재질 에셋을 그대로 쓰면 같은 프리팹의 모든 캐릭터가 시선을 공유한다. 에디터에서는 재질 에셋 값이 바뀐다. | 조립 단계(`Avatar3DRenderer`)에서 안구 재질을 인스턴스로 만들거나 MaterialPropertyBlock 으로 바꾼다. 검증 드라이버는 인스턴스 재질을 쓴다. |
| 속눈썹 깊이 당김 | 1 mm 당김은 머리 피부가 비치는 점을 없앤다. 다만 속눈썹 1 mm 안에 있는 다른 물체(앞머리 끝 등)보다 앞에 그려질 수 있다. | 헤어 가까운 장면을 통합 후 확인. 필요하면 0.5 mm. |
| 카메라 여러 대 | 메시 상태는 프레임마다 하나뿐이다. 분할 화면, 미러, 썸네일 렌더는 주 카메라 기준이다. | 보조 카메라 렌더 때는 보정 0 으로 별도 처리하거나 주 카메라만 지원. |
| 근접 원근 카메라 | 눈마다 각도가 달라 줌인 중 먼 눈 보정이 서서히 강해진다 (0.32 m 에서 설정 35° → 44°). | 의도한 동작. 연출에서 확인. |
| 위·아래 카메라 | 실기기에서 pitch −80~+80 을 확인했다. 보정은 ±40° 까지 유지되고 ±60° 에서 줄며 ±80° 에서 0 이 된다. | 연출 각도에서 한 번 더 확인. |
| BlendShapes 입력 방식 | LateUpdate 에서 Blink 를 쓰는 다른 스크립트가 있으면 그 값이 입력이 된다. | `Fields` 방식 사용 |
| 시선 범위 | 안쪽 0.12 rad 를 넘으면 바깥 흰자가 다시 보인다 (의도). 0.25 rad 를 넘는 시선은 검증하지 않았다. | 시선 상한을 0.25 rad 로 유지 |
| 리그 통합 | 실험 모델에는 머리 본이 없었다. 최종 모델에서는 머리 본 축 설정이 틀리면 좌우가 뒤바뀐다. | 통합 직후 ±35° 에서 먼 눈 쪽이 맞는지 테스트 (`EyeViewController.YawL/YawR`) |
| PlayerLoop 교체 | 다른 패키지가 `PlayerLoop.SetPlayerLoop` 으로 덮어쓰면 합성 단계가 빠진다. | 감시 후 다시 설치하고 그 사이는 LateUpdate 대체 합성 (실기기 확인) |
| 성능 (Galaxy S24 실측) | 1명: 컨트롤러 46 µs, GPU 3.3 ms (C). 12명: 컨트롤러 187 µs, CPU 메인 4.3 ms, GPU 6.8 ms, 120 fps 유지. | 중·저가 기기는 미측정. LOD 는 그때 다시 판단 |
| Timeline | 프로젝트에 `com.unity.timeline` 이 없다. PlayableDirector 경로로만 시험했다. | 재생 단계에서 패키지 설치 후 다시 확인 |
| 메모리 | 눈 메시 +320 KB (모델 종류당) | `ViewSide*` 제거 시 −133 KB |
| 기존 BlendShape 클립 | 보정 키 이름이 클립에 들어가면 컨트롤러와 충돌한다 (`ForeignWrites` 증가). | 클립 검사 스크립트로 `View*` 커브 금지 |

## 5. 통합 후 확인 목록

1. 정면 0° 에서 실험 v6f_A 와 픽셀 비교가 같은지 (보정 0).
2. ±35° 먼 눈 흰자 감소, 가까운 눈 불변.
3. Blink 100 % 에서 안구 노출 0 (0°, ±35°).
4. `EyeViewRobustnessTest` 와 같은 검사로 보정 키 덮어씀 0, Blink 100 % 초과 0.
5. 0 → ±60° 회전 영상에서 튐 없음.
6. Android 실기기 1명 / 12명 프레임 시간: 실험 모델로 완료 (REPORT_19). 리그가 들어간 전신 모델에서는 같은 테스트 씬(`AndroidTest/`)과 `EyeViewDeviceTest` 로 다시 잰다.
7. 머리 본 연결 직후 ±35° 에서 먼 눈 쪽 판정 (`YawL/YawR`).
8. Race3D_v1 확인 (REPORT_20): Blender 와 Unity 에서 정면·±35°·±45°·Blink·EyeSmile·시선을 v6j 와 비교했다. 바뀐 곳은 속눈썹 뿌리 줄뿐이다.
   - Unity 검증 장면: `Assets/_Experiments/ToonTest_01/Race3DCheck/Race3DCheck.unity`
   - 검증 드라이버: `Runtime/TestOnly/Race3DCheck.cs`
