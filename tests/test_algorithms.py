"""Tests for the hand-written merge sort and binary search."""

from app.algorithms import binary_search, merge_sort


def test_merge_sort_numbers():
    assert merge_sort([5, 2, 9, 1, 5, 6]) == [1, 2, 5, 5, 6, 9]
    assert merge_sort([5, 2, 9], reverse=True) == [9, 5, 2]
    assert merge_sort([]) == []


def test_merge_sort_by_key():
    rows = [{"name": "Samosa", "sold": 70}, {"name": "Chai", "sold": 110}, {"name": "Dosa", "sold": 35}]
    assert [r["name"] for r in merge_sort(rows, key=lambda r: r["sold"])] == ["Dosa", "Samosa", "Chai"]


def test_binary_search():
    names = ["Chai", "Dosa", "Samosa", "Thali"]
    assert binary_search(names, "Samosa") == 2
    assert binary_search(names, "Chai") == 0
    assert binary_search(names, "Pizza") == -1
    assert binary_search([], "Chai") == -1
