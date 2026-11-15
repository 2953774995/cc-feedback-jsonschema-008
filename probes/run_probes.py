#!/usr/bin/env python3
"""校验错误聚合报表验收探针。

契约：
  from jsonschema.report import summarize
  rep = summarize(schema, instance)
  rep.ok            全部通过时为 True
  rep.errors        ErrorItem 列表，每项含 .pointer（JSON Pointer，如 "/age"）、.validator、.message
  rep.by_pointer    {pointer: [ErrorItem, ...]}
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

FAILED = 0
PASSED = 0


def check(code, desc, fn):
    global FAILED, PASSED
    try:
        fn()
        print(f"[PASS] {code} {desc}")
        PASSED += 1
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] {code} {desc}")
        print(f"        {type(exc).__name__}: {exc}")
        FAILED += 1


SCHEMA = {
    "type": "object",
    "required": ["name", "age"],
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer", "minimum": 0},
        "tags": {"type": "array", "items": {"type": "string"}},
    },
}


def main():
    try:
        from jsonschema.report import summarize  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] P0 导入 jsonschema.report 失败：{type(exc).__name__}: {exc}")
        print("-" * 60)
        print("探针汇总：0/7 通过")
        return 1

    def p1():
        r = summarize(SCHEMA, {"name": "a", "age": 3})
        assert r.ok is True, r.errors
        assert r.errors == []

    def p2():
        r = summarize(SCHEMA, {"name": "a", "age": "x"})
        assert r.ok is False
        assert len(r.errors) == 1, [e.validator for e in r.errors]
        assert r.errors[0].pointer == "/age", r.errors[0].pointer
        assert r.errors[0].validator == "type", r.errors[0].validator

    def p3():
        r = summarize(SCHEMA, {"age": -1})
        assert len(r.errors) >= 2, [e.validator for e in r.errors]
        vals = {e.validator for e in r.errors}
        assert "required" in vals and ("minimum" in vals), vals

    def p4():
        schema = {"type": "object", "properties": {"a": {"type": "object", "properties": {"b": {"type": "string"}}}}} 
        r = summarize(schema, {"a": {"b": 5}})
        assert r.errors[0].pointer == "/a/b", r.errors[0].pointer

    def p5():
        r = summarize(SCHEMA, {"age": "x", "tags": [1, 2]})
        assert "/age" in r.by_pointer, r.by_pointer
        assert "/tags/0" in r.by_pointer, list(r.by_pointer)

    def p6():
        try:
            summarize({"type": "nope"}, {})
        except Exception as exc:  # noqa: BLE001
            assert "SchemaError" in type(exc).__name__, type(exc).__name__
            return
        raise AssertionError("非法 schema 没有抛 SchemaError")

    def p7():
        from jsonschema import validate
        validate(instance={"name": "a", "age": 1}, schema=SCHEMA)
        try:
            validate(instance={"name": "a", "age": "x"}, schema=SCHEMA)
        except Exception:
            return
        raise AssertionError("原 validate 行为被改动")

    check("P1", "合法实例通过", p1)
    check("P2", "单错误定位到 pointer 与 validator", p2)
    check("P3", "多错误聚合", p3)
    check("P4", "嵌套 pointer 拼接", p4)
    check("P5", "按 pointer 分组", p5)
    check("P6", "非法 schema 抛错", p6)
    check("P7", "原 validate 行为不变", p7)

    print("-" * 60)
    print(f"探针汇总：{PASSED}/{PASSED + FAILED} 通过")
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
