from spacy.language import Language
from transformers import AutoTokenizer


class SentenceSplitter:
    def __init__(self, nlp):
        self.name_or_path = nlp.get_pipe("span_marker_tunable").model.name_or_path
        self.sm_tokenizer = AutoTokenizer.from_pretrained(
            self.name_or_path, cls_token=None, sep_token=None
        )

    def __call__(self, doc):
        """
        Add additional sentence boundaries if a sentence exceeds the subtoken
        limit of the SpanMarker tokenizer.
        """
        for sen in doc.sents:
            # Offset for start/end tokens
            n_subtokens = 2
            for idx, tok in enumerate(sen):
                # Ignore start/end tokens on the word level
                n_subtokens += len(self.sm_tokenizer(tok.text).tokens()[1:-1])
                if n_subtokens >= self.sm_tokenizer.model_max_length:
                    tok.is_sent_start = True
                    n_subtokens = 2
        return doc


@Language.factory("max_sen_len_splitter")
def max_sen_len_splitter(nlp, name):
    return SentenceSplitter(nlp)
