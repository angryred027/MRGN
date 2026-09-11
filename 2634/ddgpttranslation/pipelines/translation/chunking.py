import pysbd
import spacy
from pysbd.languages import LANGUAGE_CODES
from spacy.language import Language
from spacy.util import compile_infix_regex

from .tokens import count_tokens

FALLBACK_LANG = "xx"
CJK_PUNCT = "[。！？；]"

_pipelines = {}


class PySBD:
    def __init__(self, lang):
        self.segmenter = pysbd.Segmenter(language=lang, clean=False, char_span=True)

    def __call__(self, doc):
        if not len(doc):
            return doc

        starts = set()
        for span in self.segmenter.segment(doc.text):
            sent = doc.char_span(span.start, span.end, alignment_mode="contract")
            if sent is not None:
                starts.add(sent[0].idx)

        doc[0].is_sent_start = True
        for token in doc[1:]:
            token.is_sent_start = token.idx in starts
        return doc


@Language.factory("pysbd", default_config={"lang": "en"})
def create_pysbd(nlp, name, lang):
    return PySBD(lang)


def pipeline(lang):
    nlp = _pipelines.get(lang)
    if nlp is None:
        try:
            nlp = spacy.blank(lang)
        except ImportError:
            nlp = spacy.blank(FALLBACK_LANG)
        if hasattr(nlp.tokenizer, "infix_finditer"):
            infixes = list(nlp.Defaults.infixes) + [CJK_PUNCT]
            nlp.tokenizer.infix_finditer = compile_infix_regex(infixes).finditer
        if lang in LANGUAGE_CODES:
            nlp.add_pipe("pysbd", config={"lang": lang})
        else:
            nlp.add_pipe("sentencizer")
        _pipelines[lang] = nlp
    return nlp


def split(text, lang):
    return [sent.text_with_ws for sent in pipeline(lang)(text).sents]


def group(sentences, limit):
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


def chunk(message, lang, limit):
    if count_tokens(message) <= limit:
        return [message]
    return group(split(message, lang), limit)


def merge(sources, translations):
    return "".join(
        translated.strip() + source[len(source.rstrip()):]
        for source, translated in zip(sources, translations)
    )
