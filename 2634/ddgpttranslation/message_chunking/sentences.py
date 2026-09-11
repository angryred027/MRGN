import pysbd
import spacy
from pysbd.languages import LANGUAGE_CODES
from spacy.language import Language
from spacy.util import compile_infix_regex

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


def add_cjk_infix(nlp):
    if hasattr(nlp.tokenizer, "infix_finditer"):
        infixes = list(nlp.Defaults.infixes) + [CJK_PUNCT]
        nlp.tokenizer.infix_finditer = compile_infix_regex(infixes).finditer
    return nlp


def pipeline(lang):
    nlp = _pipelines.get(lang)
    if nlp is None:
        try:
            nlp = spacy.blank(lang)
        except ImportError:
            nlp = spacy.blank(FALLBACK_LANG)
        add_cjk_infix(nlp)
        if lang in LANGUAGE_CODES:
            nlp.add_pipe("pysbd", config={"lang": lang})
        else:
            nlp.add_pipe("sentencizer")
        _pipelines[lang] = nlp
    return nlp


def split(text, lang):
    return [sent.text_with_ws for sent in pipeline(lang)(text).sents]
