# Rubik's Cube Solver

IDA* 알고리즘과 패턴 데이터베이스를 활용한 루빅스 큐브 최적 풀이기.

## 특징

- **최적 풀이**: IDA* + 패턴 DB(admissible 휴리스틱)로 항상 최단 수순 보장
- **3D 시각화**: Three.js 기반 웹 뷰어로 단계별 풀이 애니메이션 제공
- **ASCII 출력**: 터미널에서 전개도 형태로 단계별 확인 가능
- **랜덤 스크램블**: 원하는 수만큼 랜덤으로 섞어서 풀기

## 구조

```
rubik_solver/
├── model/
│   ├── cube.py        # CubeState 모델 (corner/edge perm + orient)
│   ├── moves.py       # 18가지 이동 변환 테이블
│   └── group.py       # Lehmer 인코딩, mixed-radix 유틸리티
├── solver/
│   ├── pattern_db.py  # BFS 패턴 DB (코너 88M, 엣지×2 42M 항목)
│   └── ida_star.py    # IDA* 탐색 + 이동 가지치기
├── display/
│   ├── ascii_cube.py  # ANSI 컬러 터미널 전개도
│   ├── solution.py    # 단계별 풀이 출력
│   └── web_export.py  # Three.js HTML 생성
├── templates/
│   └── cube_template.html  # 3D 뷰어 템플릿
└── main.py            # CLI 진입점
```

## 설치

```bash
git clone https://github.com/GivMeInJ/rubik-solver.git
cd rubik-solver
pip install -e .
```

## 사용법

### 데모 실행 (R U R' U' 고정 스크램블)
```bash
python3 -m rubik_solver.main --demo --no-db
```

### 랜덤 스크램블
```bash
# 5수 랜덤 섞기 (패턴 DB 없이 빠르게)
python3 -m rubik_solver.main --random 5 --no-db

# 15수 랜덤 섞기 (처음 실행 시 DB 빌드 약 3~5분 소요)
python3 -m rubik_solver.main --random 15
```

### 3D 웹 시각화
```bash
python3 -m rubik_solver.main --random 5 --no-db --export solution.html
open solution.html
```

### 직접 큐브 상태 입력
```bash
python3 -m rubik_solver.main WWWWWWWWWRRRRRRRRRGGGGGGGGGYYYYYYYYYBBBBBBBBBOOOOOOOO
```

입력 형식: U면 9칸 → R → F → D → L → B (각 9칸, 총 54자)  
색상: `W`(흰) `Y`(노랑) `R`(빨강) `O`(주황) `B`(파랑) `G`(초록)

## 알고리즘

### 패턴 데이터베이스

SOLVED 상태에서 BFS로 역방향 탐색해 각 부분 상태까지의 최소 이동 수를 저장합니다.

| DB | 추적 대상 | 크기 |
|---|---|---|
| Corner DB | 코너 8개 위치+방향 | 88,179,840 항목 |
| Edge1 DB | 엣지 cubelet 0~5 위치+방향 | 42,577,920 항목 |
| Edge2 DB | 엣지 cubelet 6~11 위치+방향 | 42,577,920 항목 |

휴리스틱 `h = max(corner_db, edge1_db, edge2_db)` — admissible 보장.

> **핵심**: 엣지 DB는 슬롯 추적이 아닌 **cubelet 추적** 방식으로 BFS의 Markov 성질을 보장합니다. 슬롯 추적 시 특정 이동(R+U 조합 등)에서 BFS가 상태를 누락해 휴리스틱이 inadmissible해지는 버그가 있었습니다.

### IDA*

- 역방향 이동 제거 (R 다음 R' 불가)
- 같은 면 연속 이동 제거
- 반대 면 순서 고정 (U/D, R/L, F/B 쌍)

## 테스트

```bash
pytest
```

## 요구사항

- Python 3.10+
- 브라우저 (3D 시각화 시)
