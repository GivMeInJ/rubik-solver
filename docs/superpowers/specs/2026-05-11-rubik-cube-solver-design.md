# 루빅스 큐브 솔버 설계 문서

**날짜:** 2026-05-11  
**언어:** Python  
**알고리즘:** IDA* + 패턴 DB (군론 기반)

---

## 1. 개요

3×3 루빅스 큐브를 수학적으로 모델링하고, IDA* 알고리즘 + 패턴 데이터베이스로 최적해를 구하는 Python 솔버 구현. 풀이 결과는 ASCII 전개도(색상 포함)와 단계별 이동 과정으로 터미널에 출력한다.

---

## 2. 수학적 모델

### 2.1 큐브의 군론적 구조

루빅스 큐브는 **군(Group)** 으로 모델링한다. 큐브의 상태 집합 G는 합성 연산 아래 군을 이루며, 각 이동(face turn)은 군의 원소다.

**물리적 구성 요소:**
- **코너 큐비 (Corner cubies):** 8개, 꼭짓점에 위치, 3가지 색깔 보유
- **엣지 큐비 (Edge cubies):** 12개, 모서리에 위치, 2가지 색깔 보유
- **센터 큐비 (Center cubies):** 6개, 면 중앙에 고정 (기준 좌표계 역할)

### 2.2 상태 표현 (CubeState)

```
CubeState:
  corner_perm[8]    # 코너 큐비의 위치 순열: S₈의 원소 (값 0~7)
  corner_orient[8]  # 코너 큐비의 방향: Z₃ (값 0, 1, 2)
  edge_perm[12]     # 엣지 큐비의 위치 순열: S₁₂의 원소 (값 0~11)
  edge_orient[12]   # 엣지 큐비의 방향: Z₂ (값 0, 1)
```

**코너 번호 부여 (URF 기준):**
```
0=URF, 1=UFL, 2=ULB, 3=UBR, 4=DFR, 5=DLF, 6=DBL, 7=DRB
```

**엣지 번호 부여:**
```
0=UR, 1=UF, 2=UL, 3=UB, 4=DR, 5=DF, 6=DL, 7=DB, 8=FR, 9=FL, 10=BL, 11=BR
```

### 2.3 군 제약 조건 (Group Constraints)

물리적으로 도달 가능한 상태는 다음 3가지 제약을 동시에 만족해야 한다:

| 제약 | 수식 | 의미 |
|------|------|------|
| 코너 방향 보존 | `Σ corner_orient[i] ≡ 0 (mod 3)` | 코너 3개를 임의로 비틀 수 없음 |
| 엣지 방향 보존 | `Σ edge_orient[i] ≡ 0 (mod 2)` | 엣지 1개를 임의로 뒤집을 수 없음 |
| 순열 패리티 | `sgn(corner_perm) × sgn(edge_perm) = +1` | 단일 교환(swap) 불가 |

**전체 도달 가능 상태 수:**
```
|G| = (8! × 3⁷ × 12! × 2¹¹) / 2 = 43,252,003,274,489,856,000 ≈ 4.3 × 10¹⁹
```

### 2.4 목표 상태 (Solved State)

```python
SOLVED = CubeState(
    corner_perm   = [0, 1, 2, 3, 4, 5, 6, 7],   # 항등 순열
    corner_orient = [0, 0, 0, 0, 0, 0, 0, 0],   # 모두 방향 0
    edge_perm     = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
    edge_orient   = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
)
```

---

## 3. 이동 연산 (Move Operations)

### 3.1 18가지 이동

```
{U, D, R, L, F, B} × {시계방향(1), 180°(2), 반시계방향(3)}
```

표기법: `R` = 오른쪽 면 시계방향, `R'` = 반시계방향, `R2` = 180°

### 3.2 이동의 구현

각 이동은 **코너/엣지 순열 + 방향의 변환 테이블**로 정의한다. 예시 (R 이동):

```python
R_MOVE = Move(
    corner_perm_map   = [4, 1, 2, 0, 7, 5, 6, 3],   # 코너 위치 변환
    corner_orient_delta = [2, 0, 0, 1, 1, 0, 0, 2],  # 방향 변화량
    edge_perm_map     = [8, 1, 2, 3, 11, 5, 6, 7, 4, 9, 10, 0],
    edge_orient_delta = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # R은 엣지 방향 불변
)
```

이동 합성: `state2 = move.apply(state1)` → 순열 합성 + 방향 덧셈 (mod 3 또는 mod 2)

---

## 4. IDA* 알고리즘

### 4.1 알고리즘 개요

IDA* (Iterative Deepening A*): 임계값(threshold)을 점진적으로 증가시키며 DFS 탐색.

```
f(n) = g(n) + h(n)
  g(n): 시작 상태에서 현재까지의 이동 수
  h(n): 패턴 DB 기반 admissible 휴리스틱 (하한)
```

```python
def ida_star(start):
    threshold = h(start)
    path = [start]
    while True:
        result = dfs(path, 0, threshold)
        if result == FOUND:
            return path
        threshold = result  # 최소 초과값으로 갱신

def dfs(path, g, threshold):
    state = path[-1]
    f = g + h(state)
    if f > threshold:
        return f                      # 가지치기
    if is_solved(state):
        return FOUND
    min_t = infinity
    for move in applicable_moves(path):  # 4.2절 가지치기 규칙 적용
        new_state = move.apply(state)
        path.append(new_state)
        result = dfs(path, g + 1, threshold)
        if result == FOUND:
            return FOUND
        min_t = min(min_t, result)
        path.pop()
    return min_t
```

### 4.2 이동 가지치기 최적화

- **역방향 이동 제거:** 직전 이동의 역이 되는 이동 제외 (18 → 최대 15개)
- **연속 같은 면 정렬:** 같은 면의 이동이 연속되면 `face1 < face2` 순서만 허용 (중복 탐색 방지)

---

## 5. 패턴 데이터베이스 (Pattern Database)

### 5.1 구조

목표 상태에서 BFS로 역방향 탐색하여 각 부분 상태의 최소 이동 수를 저장. admissible heuristic 보장.

| DB | 인덱싱 대상 | 상태 수 | 예상 크기 |
|----|-----------|--------|---------|
| 코너 DB | 코너 8개의 위치 + 방향 | 8! × 3⁷ = 88,179,840 | ~84 MB |
| 엣지 DB 1 | 엣지 0~5번의 위치 + 방향 | P(12,6) × 2⁶ = 42,577,920 | ~42 MB |
| 엣지 DB 2 | 엣지 6~11번의 위치 + 방향 | P(12,6) × 2⁶ = 42,577,920 | ~42 MB |

### 5.2 인덱스 계산

```python
def corner_index(state) -> int:
    # 코너 순열의 Lehmer code + 방향을 정수로 인코딩
    perm_idx = lehmer_encode(state.corner_perm)   # 0 ~ 8!-1
    orient_idx = mixed_radix(state.corner_orient, base=3)  # 0 ~ 3⁷-1
    return perm_idx * (3**7) + orient_idx
```

### 5.3 휴리스틱 합산

```python
def h(state) -> int:
    return max(
        corner_db[corner_index(state)],
        edge_db1[edge1_index(state)],
        edge_db2[edge2_index(state)],
    )
```

`max()` 사용으로 admissible을 유지하면서 강력한 하한 제공.

### 5.4 생성 및 캐시

```python
# 최초 실행 시 BFS로 DB 생성 (수 분 소요)
# 이후 pickle 파일로 저장/로드
pattern_db.generate_and_save("corner_db.pkl", "edge_db1.pkl", "edge_db2.pkl")
pattern_db.load("corner_db.pkl", "edge_db1.pkl", "edge_db2.pkl")
```

---

## 6. 시각화

### 6.1 ASCII 전개도 (ANSI 색상)

```
          W W W
          W W W
          W W W
O O O  B B B  R R R  G G G
O O O  B B B  R R R  G G G
O O O  B B B  R R R  G G G
          Y Y Y
          Y Y Y
          Y Y Y
```

면 순서: `U(위) / L F R B(중간 4면) / D(아래)` (표준 전개도)  
색상: ANSI 이스케이프 코드로 배경색 적용 (W=흰, Y=노랑, R=빨강, O=주황, B=파랑, G=초록)

### 6.2 단계별 풀이 출력

```
풀이 수열 (N수): R U R' U' ...

[Step 1/N]  이동: R  (오른쪽 면 시계방향)
            [큐브 전개도]

[Step 2/N]  이동: U  (윗면 시계방향)
            [큐브 전개도]
...
[완성!] 총 N수 | 탐색 노드: X | 소요 시간: X.XXs
```

---

## 7. 시스템 구조

```
rubik_solver/
├── model/
│   ├── cube.py          # CubeState 클래스, 상태 생성/비교/해시
│   ├── moves.py         # 18개 이동 변환 테이블 정의, apply()
│   └── group.py         # Lehmer 인코딩, 순열 합성, 방향 덧셈 유틸
├── solver/
│   ├── ida_star.py      # IDA* 탐색 (dfs, 가지치기 최적화)
│   └── pattern_db.py    # BFS DB 생성, 인덱스 계산, pickle 저장/로드
├── display/
│   ├── ascii_cube.py    # 전개도 렌더링 (ANSI 색상)
│   ├── solution.py      # 단계별 풀이 과정 출력
│   └── web_export.py    # solution.html 생성 (Three.js 3D 애니메이션)
├── templates/
│   └── cube_template.html  # Three.js 3D 큐브 애니메이션 템플릿
└── main.py              # CLI 진입점 (입력 파싱, 흐름 조율)
```

### 데이터 흐름

```
입력 (큐브 면 색상 54칸 문자열)
        ↓
  CubeState 변환 (면 배열 → 코너/엣지 순열+방향)
        ↓
  패턴 DB 로드 (캐시 hit → 즉시, miss → BFS 생성)
        ↓
  IDA* 탐색 → 최적 이동 수열
        ↓
  단계별 CubeState 재현 → ASCII 전개도 출력 (터미널)
        ↓
  web_export.py → solution.html 생성 (Three.js 3D 애니메이션)
        ↓
  브라우저에서 열기 → 3D 큐브 회전 애니메이션 재생
```

---

## 8. 3D 웹 시각화 (Three.js 기반)

### 8.1 개요

Python 솔버가 풀이 수열을 계산한 뒤, Three.js 기반 3D 큐브 애니메이션을 포함한 **단일 HTML 파일**을 자동 생성한다. 브라우저에서 열면 큐브가 실제로 돌아가며 풀리는 애니메이션을 재생한다. 별도 서버나 외부 의존성 없이 동작한다.

### 8.2 HTML 파일 구조

Python이 생성하는 `solution.html`은 아래를 포함한다:

```
solution.html (단일 파일)
├── <script src="three.js CDN">    # Three.js 라이브러리 (CDN)
├── 초기 큐브 상태 데이터 (JSON)   # Python이 인라인 삽입
├── 풀이 수열 데이터 (JSON)         # Python이 인라인 삽입
└── 3D 렌더링 + 애니메이션 JS 코드  # 고정 템플릿
```

### 8.3 3D 큐브 모델링

- **큐비 표현:** 27개 큐비를 각각 `THREE.BoxGeometry(0.95, 0.95, 0.95)` 메시로 생성
- **색상:** 각 큐비의 6면에 `THREE.MeshStandardMaterial` 색상 지정 (내부 면은 검정)
- **배치:** 3D 좌표 `(x, y, z)` ∈ {-1, 0, 1}³에 배치

### 8.4 회전 애니메이션

각 이동(R, U, F 등)을 큐비 그룹의 부드러운 90° 회전으로 표현:

```javascript
function animateMove(move, onComplete) {
    const group = new THREE.Group();
    const affected = getCubiesForMove(move);   // 해당 면의 큐비 9개
    affected.forEach(c => scene.remove(c), group.add(c));
    scene.add(group);

    const axis = getMoveAxis(move);            // 회전축 벡터
    const angle = getMoveAngle(move);          // ±90° 또는 180°
    animateRotation(group, axis, angle, 400ms, () => {
        dissolveGroup(group);                  // 그룹 해체 후 좌표 갱신
        onComplete();
    });
}
```

- 애니메이션 속도: 기본 400ms/수, 슬라이더로 조절 가능
- 재생/일시정지/단계별 이동 버튼 제공

### 8.5 UI 컨트롤

```
[ ◀ 이전 ]  [ ▶ 재생 ]  [ ▶▶ 다음 ]    속도: [=====|---]
Step 3 / 7 : R  (오른쪽 면 시계방향)
```

- OrbitControls로 마우스 드래그 시 큐브 자유 회전 가능
- 현재 스텝 표시 및 이동 기호+설명 표기

### 8.6 Python 생성 모듈

```
rubik_solver/
└── display/
    └── web_export.py    # solution.html 생성 (템플릿 + 데이터 인라인 삽입)
```

```python
def export_html(initial_state: CubeState, moves: list[str], output_path: str):
    template = load_template("cube_template.html")
    data = {
        "initial": state_to_facelets(initial_state),  # 54칸 색상 배열
        "moves": moves,                                 # ["R", "U", "R'", ...]
    }
    html = template.replace("__CUBE_DATA__", json.dumps(data))
    Path(output_path).write_text(html)
```

---

## 9. 제약 및 비고

- **패턴 DB 생성 시간:** 최초 실행 시 수 분 소요, 이후 캐시 재사용
- **최악 탐색 깊이:** 20수 (God's Number), 패턴 DB 품질에 따라 탐색 속도 결정
- **입력 형식:** 54칸 색상 문자열 (U면 9칸 → R → F → D → L → B 순), 색상 문자: `W`(흰), `Y`(노랑), `R`(빨강), `O`(주황), `B`(파랑), `G`(초록)
- **외부 의존성 없음:** 순수 Python 표준 라이브러리만 사용 (numpy 선택적)
