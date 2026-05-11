from rubik_solver.model.group import lehmer_encode, mixed_radix, compose_perm, invert_perm

def test_lehmer_identity():
    assert lehmer_encode([0, 1, 2, 3]) == 0

def test_lehmer_last_perm():
    # [3,2,1,0] = 마지막 순열, 4!-1 = 23
    assert lehmer_encode([3, 2, 1, 0]) == 23

def test_lehmer_example():
    # [1,0,2,3]: 1이 0보다 앞 → code[0]=1, 나머지 0 → 1*3! = 6
    assert lehmer_encode([1, 0, 2, 3]) == 6

def test_mixed_radix_all_zero():
    assert mixed_radix([0, 0, 0], base=3) == 0

def test_mixed_radix_example():
    # [1, 2, 0] base 3: 1*9 + 2*3 + 0 = 15
    assert mixed_radix([1, 2, 0], base=3) == 15

def test_compose_perm_identity():
    p = [2, 0, 1]
    identity = [0, 1, 2]
    assert compose_perm(p, identity) == p
    assert compose_perm(identity, p) == p

def test_compose_perm():
    # p=[1,2,0], q=[2,0,1] → compose_perm(p,q): result[i] = q[p[i]]
    p = [1, 2, 0]
    q = [2, 0, 1]
    result = compose_perm(p, q)
    assert result == [q[p[i]] for i in range(3)]

def test_invert_perm():
    p = [1, 2, 0]
    inv = invert_perm(p)
    identity = compose_perm(p, inv)
    assert identity == list(range(len(p)))
