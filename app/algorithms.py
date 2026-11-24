"""algorithms.py - hand-written merge sort and binary search (used by the GUI)."""


def merge_sort(items, key=lambda x: x, reverse=False):
    """
    Return a new sorted list. key picks the value to sort by,
    e.g. key=lambda row: row["Food_Name"]. reverse=True sorts high to low.
    """
    if len(items) <= 1:
        return list(items)
    middle = len(items) // 2
    left = merge_sort(items[:middle], key, reverse)
    right = merge_sort(items[middle:], key, reverse)

    # Merge: repeatedly take the smaller (or larger, if reverse) front item.
    merged, i, j = [], 0, 0
    while i < len(left) and j < len(right):
        take_left = key(left[i]) >= key(right[j]) if reverse else key(left[i]) <= key(right[j])
        if take_left:
            merged.append(left[i])
            i += 1
        else:
            merged.append(right[j])
            j += 1
    return merged + left[i:] + right[j:]


def binary_search(sorted_items, target, key=lambda x: x):
    """
    Find target in a list sorted (low to high) by key.
    Returns the index, or -1 if it is not there.
    """
    low, high = 0, len(sorted_items) - 1
    while low <= high:
        middle = (low + high) // 2
        value = key(sorted_items[middle])
        if value == target:
            return middle
        if value < target:
            low = middle + 1       # target is in the right half
        else:
            high = middle - 1      # target is in the left half
    return -1
