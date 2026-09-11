from .sentences import split


def group(sentences, limit, count_tokens):
    groups = []
    current = ""
    for sentence in sentences:
        if current and count_tokens(current + sentence) > limit:
            groups.append(current)
            current = sentence
        else:
            current += sentence
    if current:
        groups.append(current)
    return groups


def merge(sources, translations):
    return "".join(
        translated.strip() + source[len(source.rstrip()):]
        for source, translated in zip(sources, translations)
    )


def translate_message(message, lang, limit, count_tokens, translate):
    if count_tokens(message) <= limit:
        return translate(message)

    groups = group(split(message, lang), limit, count_tokens)
    return merge(groups, [translate(text) for text in groups])
