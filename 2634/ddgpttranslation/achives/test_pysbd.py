import spacy
import pysbd
from spacy.language import Language


@Language.component("pysbd_sentence_boundaries")
def pysbd_sentence_boundaries(doc):
    segmenter = pysbd.Segmenter(language="en", clean=False)

    sentences = segmenter.segment(doc.text)

    # Map sentence boundaries back onto spaCy's tokens
    start = 0

    for sentence in sentences:
        start_char = doc.text.find(sentence, start)
        end_char = start_char + len(sentence)

        # Find the token containing the sentence start
        start_token = None
        end_token = None

        for token in doc:
            if token.idx >= start_char and start_token is None:
                start_token = token.i

            if token.idx + len(token.text) <= end_char:
                end_token = token.i

        if start_token is not None:
            doc[start_token].is_sent_start = True

        start = end_char

    return doc


nlp = spacy.blank("en")

nlp.add_pipe("pysbd_sentence_boundaries")

doc = nlp("My name is Jonas E. Smith. Please turn to p. 55.")

print(list(doc.sents))