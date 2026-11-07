# MainGirlfriend Blender 참조 이미지 설정

`MainGirlfriend_Reference.png` 디자인 시트에서 정면·측면·후면 이미지를 잘라내고, Blender에 모델링용 참조 이미지로 배치하는 도구입니다.

## 폴더 구성

```
MainGirlfriend/
├── MainGirlfriend_Reference.png     # 원본 디자인 시트 (1536x1024)
├── prepare_reference_images.py      # 1단계: 참조 이미지 추출 (Pillow)
├── setup_blender_references.py      # 2단계: Blender 배치 (bpy)
├── References/                      # 1단계 결과물
│   ├── Front.png
│   ├── Side.png
│   ├── Back.png
│   └── reference_layout.json        # 머리 꼭대기·발바닥 픽셀 위치 (2단계에서 사용)
├── Models/                          # .blend 원본
├── Textures/
├── Animations/
└── Exports/                         # Unity용 FBX
```

## 1단계: 참조 이미지 추출

Pillow가 필요합니다.

```bash
python3 -m pip install pillow
```

스크립트 위치 기준으로 경로를 찾으므로 어느 폴더에서 실행해도 됩니다.

```bash
python3 BlenderSource/Characters/MainGirlfriend/prepare_reference_images.py
```

동작 방식:

- 디자인 시트 상단 중앙의 턴어라운드(정면 | 3/4 정면 | 측면 | 3/4 후면 | 후면) 중 정면·측면·후면만 사용합니다. 왼쪽 큰 포즈 일러스트와 오른쪽 정보 영역은 사용하지 않습니다.
- 스크립트 상단 `CROP_BOXES`의 영역 안에서 배경과 다른 픽셀을 찾아 캐릭터만 자동으로 잘라냅니다(`AUTO_TRIM = True`). 바닥의 옅은 그림자는 제외됩니다.
- 세 이미지의 캐릭터 높이(머리 꼭대기 ~ 발바닥)를 같은 픽셀 수로 맞춥니다. 가로세로를 같은 배율로만 조정하므로 비율이 바뀌지 않습니다.
- 모든 이미지는 위아래 여백이 같아서 머리 꼭대기와 발바닥이 같은 행에 놓입니다.

### 크롭 좌표 조정

디자인 시트를 교체했거나 결과가 잘못 잘렸다면 `prepare_reference_images.py` 상단의 값을 수정하세요.

| 설정 | 설명 |
|---|---|
| `CROP_BOXES` | 각 뷰의 검색 영역 `(left, top, right, bottom)`, 원본 픽셀 기준. 영역 안에 캐릭터 하나만 있어야 합니다. |
| `EXPECTED_SOURCE_SIZE` | 좌표를 측정한 원본 크기. 원본 크기가 다르면 스크립트가 중단됩니다. |
| `AUTO_TRIM` | `False`로 두면 `CROP_BOXES`를 그대로 사용합니다. 이때 박스의 위쪽 = 머리 꼭대기, 아래쪽 = 발바닥이어야 합니다. |
| `BACKGROUND_THRESHOLD` | 배경 판정 기준. 머리카락 끝이 잘리면 낮추고, 그림자가 포함되면 높이세요. |
| `PADDING_PX` | 결과 이미지의 여백(픽셀). |

현재 원본(1536x1024)에서 측정한 캐릭터 영역:

| 뷰 | x | y (머리 꼭대기 ~ 발바닥) |
|---|---|---|
| Front | 400–551 | 52–370 |
| Side | 739–859 | 48–369 |
| Back | 1026–1179 | 48–369 |

## 2단계: Blender에 배치

Blender 4.x / 5.x에서 동작합니다. 먼저 1단계를 실행해 `References` 폴더를 만들어 두세요.

### 방법 A: Blender 안에서 실행

1. `Models/MainGirlfriend_Base.blend`를 엽니다.
2. **Scripting** 워크스페이스 → 텍스트 에디터에서 **Text > Open** → `setup_blender_references.py` 선택
3. **Run Script** (▶) 클릭
4. 결과를 유지하려면 `.blend` 파일을 저장합니다 (Cmd+S).

### 방법 B: 터미널에서 실행

```bash
cd BlenderSource/Characters/MainGirlfriend
/Applications/Blender.app/Contents/MacOS/Blender Models/MainGirlfriend_Base.blend --python setup_blender_references.py
```

Blender가 열리고 참조 이미지가 배치됩니다. 저장은 직접 하세요.

### 배치 결과

| 오브젝트 | 평면 | 위치 | 보는 방법 |
|---|---|---|---|
| `REF_Front` | XZ | Y = +1.0 | 정면 뷰 (Numpad 1) |
| `REF_Side` | YZ | X = −1.0 | 오른쪽 뷰 (Numpad 3) |
| `REF_Back` | XZ | Y = −1.0 | 후면 뷰 (Ctrl + Numpad 1) |

- 캐릭터는 **−Y 방향**을 바라봅니다. 발바닥은 Z = 0, 머리 꼭대기는 Z = 1.65 m입니다.
- 정면·후면 이미지는 X = 0, 측면 이미지는 Y = 0을 캐릭터 중심으로 맞춥니다.
- 모든 참조 이미지는 `Reference_Images` 컬렉션에 들어갑니다.
- 모델링 방해를 줄이기 위한 표시 설정:
  - 투명도 50%, 메시 뒤에 그림 (`Depth: Back`)
  - 정사법(Orthographic) 뷰에서, 해당 축을 정면으로 볼 때만 표시
  - 앞면에서만 보임 → 정면 뷰에서 후면 이미지가 가리지 않음
  - 선택 불가, 렌더링 제외
- 스크립트를 다시 실행하면 기존 참조 오브젝트와 이미지를 갱신합니다. 중복 생성되지 않습니다.
- 기존 메시, 카메라, 조명, 다른 컬렉션은 건드리지 않습니다.
- `.blend` 파일이 저장되어 있으면 이미지 경로를 상대 경로(`//../References/Front.png`)로 저장합니다.

### Blender 스크립트 설정

`setup_blender_references.py` 상단에서 조정할 수 있습니다.

| 설정 | 기본값 | 설명 |
|---|---|---|
| `CHARACTER_HEIGHT` | `1.65` | 캐릭터 전체 높이 (m) |
| `FRONT_BACK_DISTANCE` | `1.0` | 정면/후면 이미지의 원점으로부터 거리 (m) |
| `SIDE_DISTANCE` | `1.0` | 측면 이미지의 원점으로부터 거리 (m) |
| `HORIZONTAL_OFFSETS` | 모두 `0.0` | 뷰별 좌우 미세 조정 (m) |
| `OPACITY` | `0.5` | 참조 이미지 불투명도 |
| `LOCK_SELECTION` | `True` | 뷰포트에서 클릭 선택 방지 |
| `SHOW_IN_PERSPECTIVE` | `False` | 원근 뷰에서도 표시할지 여부 |
| `ONLY_AXIS_ALIGNED` | `True` | 축 정렬 뷰에서만 표시 |
| `REFERENCE_DIR_OVERRIDE` | `""` | `References` 폴더를 자동으로 못 찾을 때 경로 지정 |

## 참고

- 측면 이미지의 가로 중심은 캐릭터 영역(머리카락 포함)의 중앙입니다. 몸통 중심과 약간 다를 수 있으니 필요하면 `HORIZONTAL_OFFSETS["Side"]`로 맞추세요.
- 측면 이미지는 오른쪽 뷰(Numpad 3)용입니다. 왼쪽 뷰(Ctrl + Numpad 3)에서는 표시되지 않습니다.
- 원본 턴어라운드의 캐릭터 높이가 약 320픽셀이라 확대하면 흐릿합니다. 세부 묘사는 원본 디자인 시트를 함께 참고하세요.
- 참조 이미지를 옮기거나 수정하려면 `LOCK_SELECTION = False`로 다시 실행하거나, 아웃라이너의 필터에서 "선택 가능(화살표 아이콘)" 열을 켜고 해당 오브젝트의 선택 잠금을 해제하세요.
