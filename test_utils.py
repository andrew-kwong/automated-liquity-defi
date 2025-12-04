from typing import NamedTuple, Optional

import pytest

from automated_defi.utils import camel_to_snake, merge_dict, merge_params


class TestCamelToSnake:
    class Case(NamedTuple):
        inp: str
        exp: str

        def __str__(self) -> str:
            return self.inp

    testcases = [
        Case(
            inp="",
            exp="",
        ),
        Case(
            inp="HelloWorld",
            exp="hello_world",
        ),
        Case(
            inp="helloWorld",
            exp="hello_world",
        ),
        Case(
            inp="helloworld",
            exp="helloworld",
        ),
        Case(
            inp="Hello World",
            exp="hello _world",
        ),
    ]

    @pytest.mark.parametrize("case", testcases, ids=lambda case: str(case))
    def test_camel_to_snake(self, case: Case):
        assert camel_to_snake(case.inp) == case.exp


class TestMergeDict:
    class Case(NamedTuple):
        base: Optional[dict]
        other: Optional[dict]
        keep_extra_in_other: bool
        exp: dict

    testcases = [
        Case(
            base=None,
            other=None,
            keep_extra_in_other=True,
            exp={},
        ),
        Case(
            base={},
            other=None,
            keep_extra_in_other=True,
            exp={},
        ),
        Case(
            base=None,
            other={},
            keep_extra_in_other=True,
            exp={},
        ),
        Case(
            base={},
            other={},
            keep_extra_in_other=True,
            exp={},
        ),
        Case(
            base={
                "v": 5,
                "d": {"a": "a", "b": "b"},
            },
            other={},
            keep_extra_in_other=True,
            exp={
                "v": 5,
                "d": {
                    "a": "a",
                    "b": "b",
                },
            },
        ),
        Case(
            base={
                "v": 5,
                "d": {"a": "a", "b": "b"},
            },
            other={
                "extra": "extra value",
                "d": {"inner extra": "inner extra value"},
            },
            keep_extra_in_other=True,
            exp={
                "v": 5,
                "d": {"a": "a", "b": "b", "inner extra": "inner extra value"},
                "extra": "extra value",
            },
        ),
        Case(
            base={"v": 5, "d": {"a": "a", "b": "b"}},
            other={"extra": "extra value", "d": {"inner extra": "inner extra value"}},
            keep_extra_in_other=False,
            exp={"v": 5, "d": {"a": "a", "b": "b"}},
        ),
    ]

    @pytest.mark.parametrize("case", testcases, ids=lambda case: str(case))
    def test_merge_dict(self, case: Case):
        actual = merge_dict(
            case.base, case.other, keep_extra_in_other=case.keep_extra_in_other
        )
        assert actual == case.exp


class TestMergeParams:
    class Case(NamedTuple):
        base: Optional[dict]
        other: Optional[dict]
        exp: dict

    testcases = [
        Case(
            base={
                "same_type": 5,
                "diff_type": 10,
                "d": {"a": "a", "b": "b", "diff_type": 10},
            },
            other={
                "same_type": 5,
                "diff_type": "20",
                "d": {"a": "a", "b": "b", "diff_type": "10"},
            },
            exp={
                "same_type": 5,
                "diff_type": 10,
                "d": {"a": "a", "b": "b", "diff_type": 10},
            },
        ),
    ]

    @pytest.mark.parametrize("case", testcases, ids=lambda case: str(case))
    def test_merge_params(self, case: Case):
        actual = merge_params(case.base, case.other)
        assert actual == case.exp
