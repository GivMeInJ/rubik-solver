from typing import List


def lehmer_encode(perm: List[int]) -> int:
    """순열을 Lehmer code(팩토리진법 수)로 인코딩 → 0 ~ n!-1"""
    n = len(perm)
    used = [False] * n
    result = 0
    for i in range(n):
        cnt = sum(1 for j in range(perm[i]) if not used[j])
        result = result * (n - i) + cnt
        used[perm[i]] = True
    return result


def mixed_radix(digits: List[int], base: int) -> int:
    """digits를 고정 진수(base)로 인코딩된 정수로 변환"""
    result = 0
    for d in digits:
        result = result * base + d
    return result


def compose_perm(p: List[int], q: List[int]) -> List[int]:
    """순열 합성: result[i] = q[p[i]]  (p 먼저 적용, 그 다음 q)"""
    return [q[p[i]] for i in range(len(p))]


def invert_perm(p: List[int]) -> List[int]:
    """순열의 역원: inv[p[i]] = i"""
    inv = [0] * len(p)
    for i, v in enumerate(p):
        inv[v] = i
    return inv
