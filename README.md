# Focus Monitor

웹캠과 온디바이스 AI를 활용해 사용자의 집중 상태를 실시간으로 확인하고 기록하는 데스크톱 애플리케이션입니다.

Focus Monitor는 자리 비움, 졸음, 휴대폰 사용을 감지해 화면 알림과 효과음으로 안내합니다. 집중·휴식 시간과 상태 변화는 시간표 형태로 기록되며, 사용자는 원하는 시점에 독립 실행형 HTML 리포트로 내보낼 수 있습니다.

## 주요 기능

- **실시간 카메라 모니터링**: 연결된 웹캠 영상을 PySide6 UI에 표시하고 일정 주기로 AI 추론을 실행합니다.
- **자리 비움 감지**: 등록된 얼굴과 현재 얼굴을 비교하고, 얼굴이 보이지 않을 때 주변의 사람 객체를 한 번 더 확인합니다.
- **졸음 감지**: 얼굴 랜드마크에서 양쪽 눈의 EAR(Eye Aspect Ratio)를 계산해 눈 감김 상태를 판정합니다.
- **휴대폰 사용 감지**: 휴대폰 객체와 얼굴 사이의 정규화 거리를 이용해 실제 사용 가능성이 높은 상황을 감지합니다.
- **안정적인 상태 전환**: 순간적인 오탐이 바로 알림으로 이어지지 않도록 상태별 진입·해제 시간을 적용합니다.
- **실시간 알림**: 집중 시작, 휴식, 자리 비움, 졸음, 휴대폰 사용 및 정상 복귀를 알림 카드와 효과음으로 안내합니다.
- **집중 타이머**: 실제 모니터링 시간만 `HH:MM:SS` 형식으로 누적하며 휴식 중에는 정지합니다.
- **기록 초기화**: 타이머, 상태 기록, 알림 카드를 한 번에 초기화합니다.
- **HTML 리포트**: 집중, 휴식, 자리 비움, 졸음, 휴대폰 사용 구간과 상태별 누적 시간, 집중률을 어두운 테마의 시간표로 생성합니다.
- **감지 설정**: 감지 주기, 얼굴 유사도, 눈 감김 기준, 휴대폰 신뢰도 및 상태 전환 시간을 UI에서 조절할 수 있습니다.
- **CPU/GPU 자동 선택**: NVIDIA CUDA 환경을 사용할 수 있으면 GPU를 사용하고, 사용할 수 없으면 CPU로 동작합니다.

## 사용 모델

| 모델 | 담당 기능 | 적용 방식 |
| --- | --- | --- |
| **Ultralytics YOLO11n** (`yolov11n.pt`) | 사람 및 휴대폰 객체 감지 | 한 번의 YOLO 추론 결과를 자리 비움 감지기와 휴대폰 감지기가 공유합니다. |
| **InsightFace buffalo_l** | 얼굴 검출 및 얼굴 임베딩 | 처음 확인된 얼굴을 기준 얼굴로 자동 등록하고, 이후 얼굴과 코사인 유사도를 비교합니다. |
| **MediaPipe Face Landmarker V2** (`face_landmarker_v2_with_blendshapes.task`) | 얼굴 랜드마크 및 눈 감김 분석 | 양쪽 눈 랜드마크로 EAR을 계산하고 설정된 임계값보다 낮으면 눈 감김으로 판정합니다. |

### 감지 흐름

```text
웹캠 프레임
    ├─ YOLO11n ────────────── 사람 / 휴대폰 객체
    ├─ InsightFace ────────── 얼굴 검출 / 사용자 유사도
    └─ MediaPipe Landmarker ─ 눈 랜드마크 / EAR
                    ↓
             상태 전환 필터
                    ↓
      집중 / 휴대폰 / 졸음 / 자리 비움
                    ↓
          UI 알림 + 시간표 기록
```

동시에 여러 상태가 관찰되면 상태 머신은 `자리 비움 → 졸음 → 휴대폰 → 집중` 순서로 대표 상태를 선택합니다. 각 이상 상태는 설정된 시간 동안 연속으로 관찰되어야 확정되며, 정상 복귀에도 별도의 해제 시간이 적용됩니다.

## 실행 환경

- Windows
- Python 및 pip
- 웹캠
- NVIDIA GPU는 선택 사항이며, GPU가 없어도 CPU 모드로 실행할 수 있습니다.

## 설치 및 실행

### 1. 라이브러리 설치

프로젝트 루트에서 다음 배치 파일을 실행합니다.

```powershell
.\library_installer.bat
```

설치 스크립트는 `libraries.txt`의 공통 패키지를 설치하고 NVIDIA GPU 유무에 따라 PyTorch와 ONNX Runtime의 GPU 또는 CPU 버전을 선택합니다.

### 2. VS Code에서 실행

저장소에 포함된 `.vscode/launch.json`을 사용합니다.

1. VS Code에서 프로젝트 폴더를 엽니다.
2. `실행 및 디버그` 메뉴로 이동합니다.
3. `OnDevice AI: Main.py` 구성을 선택합니다.
4. `F5`를 눌러 실행합니다.

터미널에서는 다음 명령으로 직접 실행할 수 있습니다.

```powershell
py src\Main.py
```

### 3. 실행 파일 빌드

```powershell
.\builder.bat
```

빌드 결과는 `dist/OnDeviceAI/`에 생성되며, 실행에 필요한 `config/`와 `res/` 리소스도 함께 복사됩니다.

추론에 사용하지 않는 개발·시각화 모듈을 제외한 최적화 빌드는 다음 명령으로 생성합니다.

```powershell
.\builder_optimized.bat
```

최적화 결과는 `dist_optimized/OnDeviceAI/`에 별도로 생성됩니다. 이 빌드는 Pandas, Polars, scikit-learn, pytest 및 사용하지 않는 InsightFace GUI·face3d 모듈을 제외합니다.

## 사용 방법

1. 프로그램을 실행하면 기본 카메라를 연결하고 모니터링을 시작합니다.
2. 감지된 상태는 오른쪽 알림 목록에서 확인합니다.
3. `쉬는 시간` 버튼을 누르면 카메라와 집중 타이머가 멈추고 리포트에 휴식 구간이 기록됩니다.
4. `시작` 버튼을 누르면 모니터링과 타이머가 이어서 진행됩니다.
5. 초기화 아이콘을 누르면 타이머, 현재 리포트 기록, 알림 목록이 모두 초기화됩니다.
6. 리포트 아이콘을 누르면 `reports/schedule_YYYYMMDD_HHMMSS.html` 파일을 생성하고 기본 브라우저로 엽니다.
7. 설정 아이콘에서 AI 감지 기준, 상태 전환 시간과 음량을 변경할 수 있습니다.

## 리포트와 개인정보 처리

- 카메라 영상과 AI 추론은 사용 중인 기기 안에서 처리됩니다.
- HTML 리포트에는 원본 영상, 얼굴 이미지, 바운딩 박스, 신뢰도 및 AI 파라미터를 저장하지 않습니다.
- 리포트에는 상태 종류와 각 구간의 시작·종료 시각, 지속 시간만 기록합니다.
- 생성된 리포트는 프로젝트의 `reports/` 폴더에 로컬 파일로 저장됩니다.
- 리포트를 생성하지 않고 프로그램을 종료하면 메모리에 있던 세션 기록은 유지되지 않습니다.

## 프로젝트 구조

```text
Focus-Monitor/
├─ .vscode/
│  └─ launch.json                 # VS Code 실행 및 디버그 구성
├─ config/
│  └─ Settings.json               # UI, 오디오, AI 및 상태 전환 설정
├─ res/
│  ├─ ai/                         # YOLO 및 MediaPipe 모델 파일
│  ├─ audio/                      # 알림 효과음
│  └─ ui/                         # 앱·기능 아이콘과 Qt 스타일시트
├─ src/
│  ├─ AI/
│  │  └─ Detector.py              # 모델 로딩과 감지 파이프라인
│  ├─ Singleton/
│  │  ├─ Camera.py                # 카메라 프레임 관리
│  │  ├─ Events.py                # 애플리케이션 이벤트 발행·구독
│  │  ├─ Report.py                # 세션 기록과 HTML 리포트 생성
│  │  ├─ Settings.py              # 설정 로딩·저장
│  │  ├─ Singleton.py             # 스레드 안전 싱글턴 기반 클래스
│  │  └─ Timer.py                 # 프레임 및 예약 콜백 관리
│  ├─ System/
│  │  ├─ Application.py           # 애플리케이션 생명주기와 전체 흐름
│  │  ├─ Define.py                # 이벤트, 상태 및 공용 자료형
│  │  ├─ FunctionLibrary.py       # 경로와 로그 유틸리티
│  │  └─ StateMachine.py          # 집중 상태 전환 및 알림 판정
│  ├─ UI/
│  │  ├─ UIHandler.py             # UI 이벤트와 알림 애니메이션
│  │  ├─ UIMainWindow.py          # 메인 화면 구성
│  │  ├─ UIPopupDialog.py         # 공용 팝업
│  │  └─ UISettingsDialog.py      # 설정 화면
│  └─ Main.py                     # 프로그램 진입점
├─ reports/                       # 실행 중 생성되는 HTML 리포트
├─ builder.bat                    # PyInstaller 빌드 스크립트
├─ builder_optimized.bat          # 추론 전용 모듈만 포함하는 최적화 빌드
├─ libraries.txt                  # Python 패키지 목록
└─ library_installer.bat          # CPU/GPU 환경별 설치 스크립트
```

## 주요 기술

- **UI**: PySide6, Qt Multimedia
- **영상 처리**: OpenCV, NumPy
- **객체 감지**: Ultralytics YOLO11n, PyTorch
- **얼굴 분석**: InsightFace, ONNX Runtime
- **랜드마크 분석**: MediaPipe Tasks
- **패키징**: PyInstaller

## 사용 시 참고사항

- 첫 번째로 정상 검출된 얼굴이 현재 세션의 기준 얼굴로 자동 등록됩니다.
- 얼굴이 너무 작거나 어둡게 보이면 자리 비움 또는 졸음 판정 정확도가 낮아질 수 있습니다.
- 카메라가 얼굴 정면과 상체를 함께 볼 수 있도록 배치하면 휴대폰 감지에 유리합니다.

## 프로젝트 인원

총 2명

- 변한빛
- 박진하
