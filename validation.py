import re


def validate_name(name: str) -> bool:
    return bool(re.match("^[А-Яа-яA-Za-z]+$", name))


def validate_medical_policy(policy: str) -> bool:
    return bool(re.match("^[0-9]{10,}$", policy))


def validate_passport(passport: str) -> bool:
    return bool(re.match("^[0-9]{4}\s?[0-9]{6}$", passport))