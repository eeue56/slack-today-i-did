def levenshtein(current_word: str, next_word: str) -> int:
    ''' Returns how similar a word is to the next word as a number

        no changes return 0
        >>> levenshtein('a', 'a')
        0

        Add a character adds 1 for each character added
        >>> levenshtein('a', 'ab')
        1
        >>> levenshtein('a', 'abc')
        2

        Removing a character adds 1 for each character
        >>> levenshtein('a', '')
        1
        >>> levenshtein('abc', '')
        3

        Replacing a character adds 1 for each character
        >>> levenshtein('abcdf', 'zxcvb')
        4
    '''

    if current_word == '':
        return len(next_word)

    if len(current_word) < len(next_word):
        current_word, next_word = next_word, current_word

    previous_row = list(range(len(next_word) + 1))

    for i, current_character in enumerate(current_word):
        current_row = [i + 1]

        for j, next_character in enumerate(next_word):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (current_character != next_character)
            current_row.append(min(insertions, deletions, substitutions))

        previous_row = current_row[:]
    return previous_row[-1]
