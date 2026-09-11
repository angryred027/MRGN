from .chunking import chunk, merge


class TranslationAgent:
    def __init__(self, llm, token_limit):
        self.llm = llm
        self.token_limit = token_limit

    def query(self, prompt):
        return [self.translate(text, prompt.target_language) for text in prompt.texts]

    def translate(self, text, target):
        parts = chunk(text.message, text.source, self.token_limit)
        return merge(parts, [self.llm(part, text.source, target) for part in parts])
