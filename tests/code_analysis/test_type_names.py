# SPDX-License-Identifier: MIT

from sciona.code_analysis.core.extract.languages.type_names import type_base_name


def test_type_base_name_strips_generic_wrapper() -> None:
    assert type_base_name("Partial<UserSvc>") == "UserSvc"


def test_type_base_name_strips_array_optional_and_generics() -> None:
    assert type_base_name(": Optional[UserRepo[]]?") == "UserRepo"
